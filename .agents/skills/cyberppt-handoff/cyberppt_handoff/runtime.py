from __future__ import annotations

import os
from pathlib import Path
import subprocess
import sys
from typing import Any


def run_outline_audit(project_dir: Path | str, cyberppt_root: Path | str) -> dict[str, Any]:
    project = Path(project_dir).resolve()
    root = Path(cyberppt_root).resolve()
    package = root / "cyberppt"
    if not package.is_dir():
        return {"status": "failed", "reason": f"CyberPPT package directory not found: {package}", "returncode": None, "stdout": "", "stderr": ""}
    outline = project / "workbench/stages/01-analysis/outline.json"
    command = [
        sys.executable,
        "-m",
        "cyberppt",
        "outline-audit",
        str(project),
        "--input",
        str(outline),
        "--lightweight",
    ]
    env = os.environ.copy()
    current = env.get("PYTHONPATH", "")
    env["PYTHONPATH"] = str(root) + (os.pathsep + current if current else "")
    result = subprocess.run(command, cwd=root, env=env, capture_output=True, text=True, check=False)
    return {
        "status": "passed" if result.returncode == 0 else "failed",
        "returncode": result.returncode,
        "command": command,
        "stdout": result.stdout,
        "stderr": result.stderr,
    }
