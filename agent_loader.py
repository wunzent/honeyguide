from __future__ import annotations

import re
from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path
from typing import Literal

import yaml

from state_writer import read_text_retry


class TemplateError(ValueError):
    pass


@dataclass(frozen=True)
class AgentTemplate:
    role: str
    description: str
    capabilities: tuple[str, ...]
    writes: Literal["none", "worktree"]
    inputs: tuple[str, ...]
    output: str
    output_schema: str | None
    max_turns_hint: int
    body: str
    body_sha256: str
    path: Path


_REQUIRED = {"role", "description", "capabilities", "writes", "output"}
_OPTIONAL = {"inputs", "output_schema", "max_turns_hint"}
_FORBIDDEN = {"vendor", "model", "effort", "reasoning_effort", "provider"}
_CAPABILITIES = {"read", "search", "edit", "propose_patch"}


def _reject_forbidden(value: object, visited: set[int]) -> None:
    # YAML aliases can form cycles; inspect each container only once.
    if not isinstance(value, (dict, list)) or id(value) in visited:
        return
    visited.add(id(value))
    if isinstance(value, dict):
        for key, child in value.items():
            if isinstance(key, str) and key.casefold() in _FORBIDDEN:
                raise TemplateError(f"Forbidden key: {key}")
            _reject_forbidden(child, visited)
    else:
        for child in value:
            _reject_forbidden(child, visited)


def _string(value: object, name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise TemplateError(f"{name} must be a non-empty string")
    return value


def _strings(value: object, name: str) -> tuple[str, ...]:
    if not isinstance(value, list):
        raise TemplateError(f"{name} must be a list of strings")
    return tuple(_string(item, name) for item in value)


def load_template(path: Path) -> AgentTemplate:
    try:
        lines = read_text_retry(path).splitlines(keepends=True)
    except (OSError, UnicodeError) as exc:
        raise TemplateError(f"Cannot read template: {path}") from exc
    if not lines or lines[0].rstrip("\r\n") != "---":
        raise TemplateError("Template must start with YAML frontmatter")
    end = next(
        (i for i in range(1, len(lines)) if lines[i].rstrip("\r\n") == "---"), None
    )
    if end is None:
        raise TemplateError("Missing closing frontmatter delimiter")
    try:
        metadata = yaml.safe_load("".join(lines[1:end]))
    except yaml.YAMLError as exc:
        raise TemplateError("Invalid YAML frontmatter") from exc
    _reject_forbidden(metadata, set())
    if not isinstance(metadata, dict):
        raise TemplateError("Frontmatter must be a mapping")
    unknown = metadata.keys() - (_REQUIRED | _OPTIONAL)
    if unknown:
        raise TemplateError(f"Unknown key: {next(iter(unknown))}")
    missing = _REQUIRED - metadata.keys()
    if missing:
        raise TemplateError(f"Missing required key: {sorted(missing)[0]}")
    role = _string(metadata["role"], "role")
    if re.fullmatch(r"[a-z][a-z0-9-]{0,31}", role) is None:
        raise TemplateError(f"Invalid role: {role}")
    if role != path.stem:
        raise TemplateError(f"Role {role} must equal file stem {path.stem}")
    description = _string(metadata["description"], "description")
    capabilities = _strings(metadata["capabilities"], "capabilities")
    if set(capabilities) - _CAPABILITIES:
        raise TemplateError(
            "Invalid capabilities; allowed: read, search, edit, propose_patch"
        )
    writes = metadata["writes"]
    if writes not in ("none", "worktree"):
        raise TemplateError("writes must be none or worktree")
    inputs = _strings(metadata.get("inputs", []), "inputs")
    output = _string(metadata["output"], "output")
    schema = metadata.get("output_schema")
    if schema is not None:
        schema = _string(schema, "output_schema")
    turns = metadata.get("max_turns_hint", 40)
    if type(turns) is not int or turns <= 0:
        raise TemplateError("max_turns_hint must be a positive integer")
    body = "".join(lines[end + 1 :])
    return AgentTemplate(
        role,
        description,
        capabilities,
        writes,
        inputs,
        output,
        schema,
        turns,
        body,
        sha256(body.encode("utf-8")).hexdigest(),
        path,
    )


def load_all(agents_dir: Path) -> dict[str, AgentTemplate]:
    if not agents_dir.is_dir():
        raise TemplateError(f"Not an agents directory: {agents_dir}")
    templates: dict[str, AgentTemplate] = {}
    for path in sorted(agents_dir.glob("*.md")):
        template = load_template(path)
        if template.role in templates:
            raise TemplateError(f"Duplicate role: {template.role}")
        templates[template.role] = template
    return templates


def render_prompt(template: AgentTemplate, context: dict[str, str]) -> str:
    sections = [template.body, "## Inputs"]
    for name in template.inputs:
        if name not in context:
            raise TemplateError(f"Missing input: {name}")
        value = context[name]
        if not isinstance(value, str):
            raise TemplateError(f"Input {name} must be a string")
        sections.append(f"### {name}\n{value}")
    sections.append(
        "## Output contract\n"
        f"Result file: {template.output}\n"
        "The final line must be `RESULT: {json}`."
    )
    return "\n\n".join(sections) + "\n"
