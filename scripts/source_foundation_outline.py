#!/usr/bin/env python3
from __future__ import annotations

import argparse
import os
from pathlib import Path
import subprocess
import sys


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_PREPARE = ROOT / ".agents" / "skills" / "ppt-outline-planning" / "scripts" / "prepare.py"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Prepare the layer-four PPT outline workpack from validated semantic artifacts.")
    parser.add_argument("semantic", help="Directory containing validated layer-three semantic artifacts")
    parser.add_argument("-o", "--output", required=True, help="Outline planning output directory")
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--request", help="JSON file containing structured deck request metadata")
    group.add_argument("--request-text", help="Raw PPT outline request text")
    parser.add_argument("--force", action="store_true", help="Overwrite an existing outline workpack")
    return parser


def main(argv: list[str] | None = None) -> int:
    ns = build_parser().parse_args(argv)
    prepare_script = Path(os.environ.get("PPT_OUTLINE_PREPARE_SCRIPT", str(DEFAULT_PREPARE)))
    if not prepare_script.is_file():
        print(f"[error] Layer-four prepare script not found: {prepare_script}", file=sys.stderr)
        return 2
    command = [sys.executable, str(prepare_script), ns.semantic, "-o", ns.output]
    if ns.request:
        command.extend(["--request", ns.request])
    if ns.request_text:
        command.extend(["--request-text", ns.request_text])
    if ns.force:
        command.append("--force")
    completed = subprocess.run(command, text=True, capture_output=True, check=False)
    if completed.stdout:
        print(completed.stdout.rstrip())
    if completed.stderr:
        print(completed.stderr.rstrip(), file=sys.stderr)
    return completed.returncode


if __name__ == "__main__":
    raise SystemExit(main())
