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
    assert [p["name"] for p in claude["plugins"]] == ["multi-agent-hub"]
    assert [p["name"] for p in codex["plugins"]] == ["multi-agent-hub"]
    assert claude["plugins"][0]["source"] == "./plugins/multi-agent-hub"
    assert codex["plugins"][0]["source"]["path"] == "./plugins/multi-agent-hub"
    assert (ROOT / claude["plugins"][0]["source"]).is_dir()


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


def test_software_component_copy_equals_source():
    def same(a, b):
        cmp = filecmp.dircmp(a, b)
        assert not cmp.left_only and not cmp.right_only and not cmp.funny_files
        match, mismatch, errors = filecmp.cmpfiles(a, b, cmp.common_files, shallow=False)
        assert not mismatch and not errors
        for sub in cmp.common_dirs:
            same(Path(a) / sub, Path(b) / sub)
    same(ROOT / "skills" / "software-component", PLUGIN / "skills" / "software-component")


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
