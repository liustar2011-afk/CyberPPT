#!/usr/bin/env python3
from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path


def run(*args: str) -> None:
    result = subprocess.run(args, text=True, capture_output=True)
    if result.returncode != 0:
        print(result.stdout)
        print(result.stderr, file=sys.stderr)
        raise SystemExit(result.returncode)
    if result.stdout:
        print(result.stdout.strip())


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    py = sys.executable
    run(py, str(root / "scripts" / "validate_skill.py"), str(root))
    run(py, str(root / "scripts" / "validate_visual_spec.py"), str(root / "assets" / "example-page-spec.json"), "--strict")
    run(py, str(root / "scripts" / "validate_visual_spec.py"), str(root / "assets" / "example-deck-spec.json"), "--strict")
    run(py, str(root / "scripts" / "validate_visual_spec.py"), str(root / "assets" / "example-page-script.md"), "--strict")
    with tempfile.TemporaryDirectory() as td:
        out = Path(td) / "prompt.md"
        run(py, str(root / "scripts" / "build_generation_prompt.py"), str(root / "assets" / "example-deck-spec.json"), "--output", str(out))
        text = out.read_text(encoding="utf-8")
        required = ["Mandatory composition guidance", "Selected visual intent type", "Required on-screen body text", "external PowerPoint text layer"]
        missing = [x for x in required if x not in text]
        if missing:
            raise SystemExit(f"Prompt generation test failed, missing: {missing}")
    print("SELF TEST PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
