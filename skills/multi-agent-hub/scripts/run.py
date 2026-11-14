"""Portable adapter for the bundled Multi-Agent Hub runtime."""
import os
from pathlib import Path
import runpy
import sys
sys.dont_write_bytecode = True


def skill_dir():
    return Path(__file__).resolve().parents[1]


def runtime_dir():
    skill = skill_dir()
    bundled = skill / "runtime"
    if (bundled / "hub.py").is_file():
        return bundled
    for parent in (skill, *skill.parents):
        candidate = parent / "tools" / "hub.py"
        if candidate.is_file() and (parent / "models.toml").is_file() and (parent / "skills/multi-agent-hub/scripts/run.py").is_file():
            return parent / "tools"
    raise SystemExit("Hub runtime is missing; native skill instructions remain usable")


def main():
    runtime = runtime_dir()
    project = Path.cwd().resolve()
    records = project / ".multi-agent-hub"
    if not records.resolve().is_relative_to(project):
        raise SystemExit("portable records path escapes current project")
    sys.path.insert(0, str(runtime))
    os.environ["HUB_WORK_ROOT"] = str(project)
    os.environ["HUB_RECORDS_ROOT"] = str(records)
    os.environ["HUB_PROJECT_ROOT"] = str(project)
    os.environ["HUB_PORTABLE"] = "1"
    model_catalog = runtime / "models.toml"
    if not model_catalog.is_file():
        model_catalog = runtime.parent / "models.toml"
    if model_catalog.is_file():
        os.environ["HUB_MODEL_CATALOG"] = str(model_catalog)
    sys.argv = [str(runtime / "hub.py"), *sys.argv[1:]]
    runpy.run_path(str(runtime / "hub.py"), run_name="__main__")


if __name__ == "__main__":
    main()
