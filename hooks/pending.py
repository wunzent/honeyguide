from __future__ import annotations

import json
from pathlib import Path
import subprocess
from typing import Callable


def main(*, root: Path | None = None, runner: Callable = subprocess.run) -> int:
    root = root or Path(__file__).resolve().parents[1]
    try:
        result = runner([str(root / ".venv" / "Scripts" / "python.exe"), str(root / "bridge.py"),
                         "pending", "--brief"], cwd=root, capture_output=True, text=True,
                        encoding="utf-8", timeout=8, check=False)
        data = json.loads(result.stdout)
        if result.returncode == 0 and data.get("ok") and data.get("summary"):
            print(data["summary"])
    except Exception:
        # A context hook must never prevent submission of the owner's prompt.
        pass
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
