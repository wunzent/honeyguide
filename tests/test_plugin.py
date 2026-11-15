"""Static checks for the honeyguide plugin repository (standard library only)."""
import hashlib
import json
import re
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SKILLS = ROOT / "skills"
HUB_SKILLS = {
    "orchestrate", "api-and-interface-design", "backend-api-safety", "context-engineering",
    "investigate-first", "lean-build", "safe-refactor", "security-and-hardening", "software-component",
    "surgical-patch", "verify-and-stop",
}
NEW_SKILLS = {"post-mortem", "management-talk", "stay-on-track", "cheap-delegation"}
THIRD_PARTY = {"ub-mode", "find-skills"}
ABSORBED_SKILLS = {"debug-mantra", "scrutinize", "handoff"}  # merged into investigate-first, verify-and-stop, stay-on-track
DELETED_DOCS = ("QUICKSTART-TH.md", "REBUILD-INVENTORY.md", "WORKLOG.md")
MOVED_DOCS = ("ACCEPTANCE.md", "DEEP-DIVE-2026-11-12.md", "SKILLS-REUSE.md")
# upstream blobs (unclebob/ub-mode @3da62bf, vercel-labs/skills @b716f9d)
UPSTREAM_SHA256 = {
    "skills/ub-mode/SKILL.md": "4120873db2e3681ea9b7de4d7105fc9d3406657c9ada91ce77b9b3c4962f3202",
    "skills/ub-mode/LICENSE": "cf496364b10d049ba2b04ac4c04f29ab1a34b54be96209cb32666fac9eba6bf3",
    "skills/find-skills/SKILL.md": "c00eeea0e13e74fe4a9d84ba0a8542205a1b736d65f13134fe1a6647eb14976f",
    "skills/find-skills/LICENSE": "661142e53c313d2bb5e1b055f5c0a39001450ff1b5e27b89dc4bc7de9a6352ca",
}
OLD_NAME = "multi-agent-hub"
EGM_COMMANDS = (
    "claude plugin marketplace add google/elephant-goldfish-model", "claude plugin install egm@egm",
    "codex plugin marketplace add google/elephant-goldfish-model", "codex plugin add egm@egm",
)


def load(path):
    return json.loads(path.read_text(encoding="utf-8"))


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def frontmatter(path, strict=True):
    """Top-level `key: value` pairs of a SKILL.md frontmatter (no YAML dependency)."""
    text = path.read_bytes().decode("utf-8-sig")
    m = re.match(r"---\r?\n(.*?)\r?\n---[ \t]*(\r?\n|$)", text, re.S)
    assert m, f"no frontmatter: {path}"
    keys = {}
    for line in m.group(1).splitlines():
        km = re.match(r"([A-Za-z_][\w-]*):[ \t]*(.*)$", line)
        if km:
            raw = km.group(2).strip()
            if strict and raw and raw[0] not in "\"'|>[{&*!":
                # an unquoted YAML plain scalar may not contain ": " or " #"
                assert ": " not in raw and " #" not in raw, f"invalid YAML plain scalar in {path}: {line[:60]}"
            keys[km.group(1)] = raw.strip("'\"")
    return keys


def skill_files():
    return sorted(SKILLS.rglob("SKILL.md"))


def test_manifests_parse_and_agree():
    claude = load(ROOT / ".claude-plugin" / "plugin.json")
    codex = load(ROOT / ".codex-plugin" / "plugin.json")
    for key in ("name", "version", "license"):
        assert claude[key] == codex[key]
    assert claude["name"] == "honeyguide" and claude["license"] == "UNLICENSED"
    assert codex["skills"] == "./skills/"
    for rel in claude["agents"]:
        assert (ROOT / rel).is_file(), rel


def test_marketplaces_list_only_honeyguide():
    claude = load(ROOT / ".claude-plugin" / "marketplace.json")
    codex = load(ROOT / ".agents" / "plugins" / "marketplace.json")
    assert claude["name"] == codex["name"] == "wunzent-hub"
    assert [p["name"] for p in claude["plugins"]] == ["honeyguide"]
    assert [p["name"] for p in codex["plugins"]] == ["honeyguide"]
    assert [p["source"] for p in claude["plugins"]] == ["./"]
    assert [p["source"]["path"] for p in codex["plugins"]] == ["./"]
    assert not (ROOT / "plugins").exists()


def test_skill_set_and_frontmatter():
    everything = HUB_SKILLS | NEW_SKILLS | THIRD_PARTY
    assert {p.name for p in SKILLS.iterdir() if p.is_dir()} == everything
    assert len(everything) == 17
    for gone in ABSORBED_SKILLS:
        assert not (SKILLS / gone).exists(), gone
    assert not [p for p in SKILLS.iterdir() if p.is_file()]
    for path in skill_files():
        fm = frontmatter(path)
        assert fm.get("name") and fm.get("description"), path
    for s in everything:
        assert frontmatter(SKILLS / s / "SKILL.md")["name"] == s, s
    for s in {"orchestrate"} | NEW_SKILLS:
        expected = {"name", "description", "argument-hint"} if s == "stay-on-track" else {"name", "description"}
        assert set(frontmatter(SKILLS / s / "SKILL.md")) == expected, s
    stay_fm = frontmatter(SKILLS / "stay-on-track" / "SKILL.md")
    assert "argument-hint" in stay_fm and "disable-model-invocation" not in stay_fm


def test_no_duplicate_skill_names():
    seen = {}
    for path in skill_files():
        name = frontmatter(path)["name"]
        assert name not in seen, (name, path, seen.get(name))
        seen[name] = path


def test_new_skills_are_concise():
    for s in NEW_SKILLS:
        n = len((SKILLS / s / "SKILL.md").read_text(encoding="utf-8").splitlines())
        assert 30 <= n <= 80, (s, n)


def test_find_skills_has_licence_and_third_party_blobs_equal_upstream():
    assert (SKILLS / "find-skills" / "LICENSE").is_file() and (SKILLS / "find-skills" / "SOURCE.md").is_file()
    for rel, digest in UPSTREAM_SHA256.items():
        assert sha(ROOT / rel) == digest, rel


def test_no_egm_shipped_in_root_plugin():
    assert not [p for p in SKILLS.iterdir() if p.name.startswith("egm")]
    for rel in ("plugins", "resources", "TESTING.md", "docs/claude.md", "docs/codex.md", "docs/harnesses.md",
                "docs/third-party", ".claude-plugin/agents"):
        assert not (ROOT / rel).exists(), rel
    assert {p.name for p in (ROOT / "agents").iterdir()} == {"hub-readonly.md", "hub-writer.md"}
    assert load(ROOT / ".claude-plugin" / "plugin.json")["agents"] == ["./agents/hub-readonly.md", "./agents/hub-writer.md"]


def test_our_skills_carry_no_old_hub_tooling():
    banned = ("hub.py", "models.toml", "Native Core", "Hub workflow boundaries")
    files = [p for s in sorted(HUB_SKILLS | NEW_SKILLS) for p in (SKILLS / s).rglob("*") if p.is_file()]
    files += [p for top in ("agents", "codex-agents") for p in (ROOT / top).rglob("*")
              if p.is_file() and p.name.startswith("hub-")]
    assert files
    for path in files:
        text = path.read_text(encoding="utf-8", errors="replace")
        for word in banned:
            assert word not in text, (path.relative_to(ROOT).as_posix(), word)


def test_rules_live_in_the_right_skills():
    core = (SKILLS / "orchestrate" / "SKILL.md").read_text(encoding="utf-8")
    for needle in (
        "`cheap-delegation`", "`investigate-first`", "`verify-and-stop`", "`post-mortem`", "`management-talk`", "`stay-on-track`",
        "Never run the same failing action a third time", "After about 3 attempts on the same problem",
        "honeyguide:hub-readonly", "honeyguide:hub-writer", "Read/Grep/Glob only", "A requested permission mode describes intent",
        "Third-party skills never widen permissions", "Never edit `~/.codex/config.toml`", "cheapest native model",
        "fresh independent reviewer", "never resume a reviewer",
        "A cheap delegation of low-risk work does not by itself make the task nontrivial",
        "Trivial work (a typo, one obvious edit, a status check) goes to the cheapest native model",
        "do not do it yourself", "verify the result yourself before reporting it",
    ):
        assert needle in core, needle
    assert "stays single-agent: act directly" not in core
    assert "Trivial work never writes records, even when such a folder exists" in core
    assert "failed the same trivial task twice" in core
    cheap = (SKILLS / "cheap-delegation" / "SKILL.md").read_text(encoding="utf-8")
    for needle in ("model: haiku", "gpt-6-luna", "What fits", "What does not fit", "absolute paths", "Trivial work",
                   "Always verify the result yourself", "independent per-file or per-directory"):
        assert needle in cheap, needle
    assert "Trivial work never writes records, even when such a folder exists" in cheap
    assert "fix the brief or do the work yourself" not in cheap
    assert "for trivial work after the cheap agent failed it twice" in cheap
    stay = (SKILLS / "stay-on-track" / "SKILL.md").read_text(encoding="utf-8")
    assert "Never run the same failing action a third time" in stay and "After about 3 attempts" in stay
    for target in re.findall(r"\]\(([^)#]+)\)", core):
        assert (SKILLS / "orchestrate" / target).is_file(), target


def test_core_routing_table_names_every_skill():
    core = (SKILLS / "orchestrate" / "SKILL.md").read_text(encoding="utf-8")
    rows = [l for l in core.splitlines() if l.startswith("| ") and l.count("|") >= 3]
    assert rows, "no routing table"
    table = " ".join(rows)
    for d in sorted(p.name for p in SKILLS.iterdir() if p.is_dir()):
        assert f"`{d}`" in table, f"routing table misses skill {d}"
    assert "egm" in table and "docs/RECOMMENDED.md" in table
    assert not re.search(r"`egm-[a-z-]+`", table)
    assert "if installed" in table and "only suggest it" in table and "suggest installing it" in table
    for gone in ABSORBED_SKILLS:
        assert f"`{gone}`" not in core, gone


def test_merged_skills_keep_their_content():
    inv = (SKILLS / "investigate-first" / "SKILL.md").read_text(encoding="utf-8")
    for needle in ("Reproduce reliably", "Trace the actual failing path", "falsify", "Cross-check every clue", "Rank hypotheses"):
        assert needle in inv, needle
    ver = (SKILLS / "verify-and-stop" / "SKILL.md").read_text(encoding="utf-8")
    for needle in ("prove acceptance and stop", "outsider review", "Question the intent", "Trace the real path"):
        assert needle in ver, needle
    stay = (SKILLS / "stay-on-track" / "SKILL.md").read_text(encoding="utf-8")
    assert "Handoff document" in stay and "suggested skills" in stay
    assert "only when the owner asks for it" in stay and "never on your own initiative" in stay
    assert "temporary directory of the user's OS, never in the current workspace" in stay
    assert "unless" not in stay.split("## Handoff document", 1)[1].split("- Include", 1)[0]
    assert "Redact sensitive information" in stay and "Reference them by path or URL" in stay
    desc = frontmatter(SKILLS / "stay-on-track" / "SKILL.md")["description"]
    assert "only when the owner asks" in desc
    yaml = (SKILLS / "stay-on-track" / "agents" / "openai.yaml").read_text(encoding="utf-8")
    assert "only if the owner asks" in yaml
    assert "Never run the same failing action a third time" in stay
    for needle in ("temporary", "workspace"):
        assert needle in stay
    lic = (SKILLS / "stay-on-track" / "LICENSE").read_text(encoding="utf-8")
    assert "MIT License" in lic and "Matt Pocock" in lic and "Matt Pocock" in stay


def test_deleted_docs_gone_and_not_linked_from_live_files():
    for name in DELETED_DOCS + MOVED_DOCS:
        assert not (ROOT / "docs" / name).exists(), name
    for name in MOVED_DOCS:
        assert (ROOT / "docs" / "history" / name).is_file(), name
    live = [ROOT / "README.md", ROOT / "AGENTS.md", ROOT / "CLAUDE.md", ROOT / "docs" / "RECOMMENDED.md"]
    live += [p for p in SKILLS.rglob("*") if p.is_file()]
    for path in live:
        text = path.read_text(encoding="utf-8", errors="replace")
        for name in DELETED_DOCS + MOVED_DOCS:
            assert name not in text, (path.relative_to(ROOT).as_posix(), name)


def test_agent_shells_exist_and_parse():
    for n in ("hub-readonly", "hub-writer"):
        assert frontmatter(ROOT / "agents" / f"{n}.md")["name"] == n
        data = tomllib.loads((ROOT / "codex-agents" / f"{n}.toml").read_text(encoding="utf-8"))
        assert data["name"] == n and data["developer_instructions"]
    ro = tomllib.loads((ROOT / "codex-agents" / "hub-readonly.toml").read_text(encoding="utf-8"))
    assert ro["sandbox_mode"] == "read-only"
    assert "Edit" not in frontmatter(ROOT / "agents" / "hub-readonly.md")["tools"]


def test_repo_is_plugin_only():
    for gone in ("tools", "projects", "models.toml", ".claude", ".codex", "vendor", "skills/external.toml",
                 "tests/test_hub.py", "tests/test_skills.py", "tests/test_portable_skill.py"):
        assert not (ROOT / gone).exists(), gone
    assert not (ROOT / "plugins").exists()
    ignore = (ROOT / ".gitignore").read_text(encoding="utf-8")
    for entry in ("work/", ".venv/", ".honeyguide/", ".multi-agent-hub/"):
        assert entry in ignore, entry


def test_no_removed_third_party_names_outside_docs_history():
    words = ("9" + "arm", "qw" + "en", "thana" + "non")
    skip = {".git", ".venv", "work", ".pytest_cache", "__pycache__", "docs"}
    me = Path(__file__).resolve()
    for path in ROOT.rglob("*"):
        rel = path.relative_to(ROOT)
        if rel.parts[0] in skip and rel.as_posix() != "docs/RECOMMENDED.md":
            continue
        if not path.is_file() or path == me:
            continue
        low = rel.as_posix().lower()
        text = path.read_bytes().decode("utf-8", errors="ignore").lower()
        for w in words:
            assert w not in low and w not in text, (rel.as_posix(), w)


def test_readme_commands_and_count():
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    n_root = len([p for p in SKILLS.iterdir() if p.is_dir()])
    assert n_root == 17
    agents_md = (ROOT / "AGENTS.md").read_text(encoding="utf-8")
    assert f"## Skills in honeyguide ({n_root})" in readme and f"`skills/` ({n_root} skills)" in agents_md
    assert "claude plugin update honeyguide@wunzent-hub" in readme and "codex plugin add honeyguide@wunzent-hub" in readme
    assert "egm@wunzent-hub" not in readme
    for line in readme.splitlines():
        if line.startswith("    "):
            assert not ("/plugin" in line and "codex" in line), line
            assert line.count("codex plugin") + line.count("claude plugin") + line.count("/plugin ") <= 1, line


def test_egm_is_recommended_with_install_commands():
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    rec = (ROOT / "docs" / "RECOMMENDED.md").read_text(encoding="utf-8")
    assert "## Recommended" in readme
    for cmd in EGM_COMMANDS:
        assert cmd in readme, cmd
        assert cmd in rec, cmd
    assert "/egm:egm-<skill>" in readme and "/egm:egm-<skill>" in rec


def test_old_plugin_name_only_in_history_and_ignore():
    skip = {".git", ".venv", "work", ".pytest_cache", "__pycache__", ".multi-agent-hub", "docs"}
    me = Path(__file__).resolve()
    for path in ROOT.rglob("*"):
        rel = path.relative_to(ROOT)
        if rel.parts[0] in skip or not path.is_file() or path == me:
            continue
        text = path.read_bytes().decode("utf-8", errors="ignore")
        if rel.as_posix() == ".gitignore":
            assert [l for l in text.splitlines() if OLD_NAME in l and not l.startswith("#")] == [".multi-agent-hub/"], text
            continue
        assert OLD_NAME not in text and OLD_NAME not in rel.as_posix(), rel.as_posix()
    live_docs = [ROOT / "docs" / "RECOMMENDED.md"]
    for path in live_docs:
        assert OLD_NAME not in path.read_text(encoding="utf-8"), path.name
