"""Static checks for the multi-agent-hub plugin packaging (standard library only)."""
import filecmp
import json
import re
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PLUGIN = ROOT / "plugins" / "multi-agent-hub"
SKILL = PLUGIN / "skills" / "multi-agent-hub"


def load(path):
    return json.loads(path.read_text(encoding="utf-8"))


def frontmatter(path):
    text = path.read_text(encoding="utf-8")
    m = re.match(r"---\n(.*?)\n---\n", text, re.S)
    assert m, path
    return {k.strip(): v.strip() for k, v in (l.split(":", 1) for l in m.group(1).splitlines() if ":" in l)}


def test_manifests_agree():
    claude = load(PLUGIN / ".claude-plugin" / "plugin.json")
    codex = load(PLUGIN / ".codex-plugin" / "plugin.json")
    for key in ("name", "version", "license"):
        assert claude[key] == codex[key]
    assert claude["name"] == "multi-agent-hub" and claude["version"] == "0.1.0"
    assert claude["license"] == "UNLICENSED"
    assert codex["skills"] == "./skills/"
    assert (PLUGIN / "skills").is_dir()


def test_marketplaces_list_plugin():
    claude = load(ROOT / ".claude-plugin" / "marketplace.json")
    codex = load(ROOT / ".agents" / "plugins" / "marketplace.json")
    assert claude["name"] == codex["name"] == "wunzent-hub"
    assert [p["name"] for p in claude["plugins"]] == ["multi-agent-hub", "9arm-skills", "egm", "uxkin", "base44"]
    assert [p["name"] for p in codex["plugins"]] == ["multi-agent-hub"]
    assert claude["plugins"][0]["source"] == "./plugins/multi-agent-hub"
    assert codex["plugins"][0]["source"]["path"] == "./plugins/multi-agent-hub"
    assert (ROOT / claude["plugins"][0]["source"]).is_dir()
    nine = claude["plugins"][1]
    assert nine["source"] == {"source": "github", "repo": "thananon/9arm-skills",
                              "sha": "a1fc303b274ed06c32d405ba5a6db00ded6e5663"}
    assert nine["description"] and not {"skills", "agents", "commands", "hooks"} & set(nine)
    assert not (ROOT / "plugins" / "9arm-skills").exists()
    egm = claude["plugins"][2]
    assert egm["source"] == {"source": "github", "repo": "google/elephant-goldfish-model",
                             "sha": "964a4f1ecd333961375c35cb37ed09364dab5e4e"}
    assert egm["description"] and not {"skills", "agents", "commands", "hooks"} & set(egm)
    assert not (ROOT / "plugins" / "egm").exists()
    pins = {"uxkin": ("uxkin/agent", "c9425694cbf77ca13c067ae100a34eeec5a2856e"),
            "base44": ("base44/skills", "8a7fc77304c8a9ab995d68aa5cdcbce6eddb631b")}
    for entry in claude["plugins"][3:]:
        repo, sha = pins[entry["name"]]
        assert entry["source"] == {"source": "github", "repo": repo, "sha": sha}
        assert entry["description"] and not {"skills", "agents", "commands", "hooks"} & set(entry)


def test_skill_frontmatter_open_standard_only():
    fm = frontmatter(SKILL / "SKILL.md")
    assert set(fm) == {"name", "description"}
    assert fm["name"] == "multi-agent-hub"


def test_no_helper_installer_or_catalog_references():
    banned = ("models.toml", "hub.py", "run.py", "install_hub_skill", "installer")
    for path in [SKILL / "SKILL.md", SKILL / "references" / "brief.md"]:
        text = path.read_text(encoding="utf-8")
        for word in banned:
            assert word not in text, (path.name, word)
        assert "helper" not in text.replace("no cross-vendor delegation helper", "")


def test_referenced_files_exist():
    text = (SKILL / "SKILL.md").read_text(encoding="utf-8")
    for target in re.findall(r"\]\(([^)#]+)\)", text):
        assert (SKILL / target).is_file(), target
    for rel in ("README.md", "agents/hub-readonly.md", "agents/hub-writer.md",
                "codex-agents/hub-readonly.toml", "codex-agents/hub-writer.toml",
                "skills/software-component/SKILL.md"):
        assert (PLUGIN / rel).is_file(), rel


BUNDLED = ("api-and-interface-design", "backend-api-safety", "context-engineering", "handoff",
           "investigate-first", "lean-build", "safe-refactor", "security-and-hardening",
           "software-component", "surgical-patch", "verify-and-stop")


def test_bundled_skill_copies_equal_source():
    def same(a, b):
        cmp = filecmp.dircmp(a, b)
        assert not cmp.left_only and not cmp.right_only and not cmp.funny_files
        match, mismatch, errors = filecmp.cmpfiles(a, b, cmp.common_files, shallow=False)
        assert not mismatch and not errors
        for sub in cmp.common_dirs:
            same(Path(a) / sub, Path(b) / sub)
    for name in BUNDLED:
        same(ROOT / "skills" / name, PLUGIN / "skills" / name)
    assert not (PLUGIN / "skills" / "brief").exists()


def test_codex_shells_and_claude_agents():
    ro = tomllib.loads((PLUGIN / "codex-agents" / "hub-readonly.toml").read_text(encoding="utf-8"))
    wr = tomllib.loads((PLUGIN / "codex-agents" / "hub-writer.toml").read_text(encoding="utf-8"))
    assert ro["name"] == "hub-readonly" and ro["sandbox_mode"] == "read-only"
    assert wr["name"] == "hub-writer" and wr["sandbox_mode"] == "workspace-write"
    assert ro["developer_instructions"].strip() and wr["developer_instructions"].strip()
    ro_md = frontmatter(PLUGIN / "agents" / "hub-readonly.md")
    assert ro_md["tools"] == "Read, Grep, Glob"
    assert "Edit" not in frontmatter(PLUGIN / "agents" / "hub-readonly.md")["tools"]
    assert "Write" in frontmatter(PLUGIN / "agents" / "hub-writer.md")["tools"]


def test_bundled_skill_path_and_brief_fields():
    text = (SKILL / "SKILL.md").read_text(encoding="utf-8")
    assert "../software-component/SKILL.md" in text
    assert (SKILL / ".." / "software-component" / "SKILL.md").is_file()
    brief = (SKILL / "references" / "brief.md").read_text(encoding="utf-8")
    assert "CONTRACT:" in brief and "REPORT FILE:" in brief
    for rel in ("agents/hub-readonly.md", "codex-agents/hub-readonly.toml"):
        assert "run on Codex" not in (PLUGIN / rel).read_text(encoding="utf-8")


def test_bundled_skill_frontmatter_is_plain_yaml():
    """Minimal YAML check: unquoted scalar values must not contain ': ' or ' #' or start with an indicator."""
    for name in BUNDLED + ("multi-agent-hub",):
        text = (PLUGIN / "skills" / name / "SKILL.md").read_text(encoding="utf-8")
        m = re.match(r"---\r?\n(.*?)\r?\n---\r?\n", text, re.S)
        assert m, name
        for line in m.group(1).splitlines():
            key, sep, value = line.partition(":")
            assert sep and re.fullmatch(r"[A-Za-z][\w-]*", key), (name, line)
            value = value.strip()
            if value[:1] in ('"', "'"):
                assert value[-1] == value[0] and len(value) > 1, (name, line)
            else:
                assert ": " not in value and " #" not in value, (name, line)
                assert value[:1] not in "[{*&!|>%@`", (name, line)


def test_bundled_skills_are_project_neutral():
    for name in BUNDLED:
        for path in (PLUGIN / "skills" / name).rglob("*.md"):
            text = path.read_text(encoding="utf-8")
            for phrase in ("AGENTS.md section", "Native Core", "Hub workflow boundaries"):
                assert phrase not in text, (path, phrase)


def test_skill_has_cheap_delegation_guidance():
    text = (SKILL / "SKILL.md").read_text(encoding="utf-8")
    assert "Cheap delegation" in text and "model: haiku" in text and "gpt-6-luna" in text
    assert "Do not delegate this way: architecture or design" in text
    assert "other than a cheap delegation" in text
    for phrase in ("Native Core", "Hub workflow boundaries"):
        assert phrase not in text
    assert "or `hub-readonly` shell" not in text and "`multi-agent-hub:hub-readonly` shell" in text
    brief = (SKILL / "references" / "brief.md").read_text(encoding="utf-8")
    assert "any spawn other than a cheap delegation of low-risk work, or high risk" in brief
    assert "any spawn or high risk" not in brief
    assert "records written before the first spawn" in brief
    assert "Review is required before completion for high-risk changes" in brief
    assert "fresh independent reviewer" in text and "never resume a reviewer" in text


def test_ub_mode_bundled():
    ub = PLUGIN / "skills" / "ub-mode"
    for rel in ("SKILL.md", "LICENSE", "SOURCE.md"):
        assert (ub / rel).is_file(), rel
    assert not (ROOT / "skills" / "ub-mode").exists()  # third-party copy, exempt from the hub byte-copy test
    assert "3da62bf3fcfd2034de41f30d920d2739e566171f" in (ub / "SOURCE.md").read_text(encoding="utf-8")
    text = (ub / "SKILL.md").read_text(encoding="utf-8")
    m = re.match(r"---\r?\n(.*?)\r?\n---\r?\n", text, re.S)
    assert m
    lines = m.group(1).splitlines()
    assert lines[0] == "name: ub-mode"
    assert lines[1].rstrip() in ("description: >", "description: |") or lines[1].startswith("description: ")
    assert all(l.startswith((" ", "\t")) for l in lines[2:]), "folded description continuation lines must be indented"
    assert "../ub-mode/SKILL.md" in (SKILL / "SKILL.md").read_text(encoding="utf-8")


def test_recommended_listed_and_linked():
    assert "[RECOMMENDED.md](RECOMMENDED.md)" in (PLUGIN / "README.md").read_text(encoding="utf-8")
    text = (PLUGIN / "RECOMMENDED.md").read_text(encoding="utf-8")
    for name in ("engineering", "design", "claude-security", "anthropic-skills", "agent-engineering",
                 "mattpocock-skills", "design-skills", "vectorlab-ux-skills", "agent-estimate", "caveman"):
        assert name in text, name


def test_ub_mode_matches_upstream_blobs():
    import hashlib
    expected = {"SKILL.md": "9ac940b23b61d77e8e5192721d7b6066357f892c",
                "LICENSE": "28dd8b5d6311ca1aaa71276043c0e975dc9e9766"}
    for name, sha in expected.items():
        data = (PLUGIN / "skills" / "ub-mode" / name).read_bytes().replace(b"\r\n", b"\n")
        assert hashlib.sha1(b"blob %d\0" % len(data) + data).hexdigest() == sha, name
    assert "never widen permissions" in (SKILL / "SKILL.md").read_text(encoding="utf-8")
