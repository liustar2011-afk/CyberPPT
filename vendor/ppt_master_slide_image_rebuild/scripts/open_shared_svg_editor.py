#!/usr/bin/env python3
"""
PPT Master - Open Shared SVG Editor

Launch ppt-master's browser SVG editor for a slide-image-rebuild project.

Usage:
    python3 scripts/open_shared_svg_editor.py <project_path> --live

Examples:
    python3 scripts/open_shared_svg_editor.py projects/demo --live

Dependencies:
    ppt-master svg_editor server dependencies
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

_SCRIPTS_DIR = Path(__file__).resolve().parent
if str(_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_DIR))

from shared_ppt_resources import svg_editor_server_script  # noqa: E402


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Open ppt-master's shared SVG editor for a slide-image-rebuild project.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("project_path", type=Path, help="slide-image-rebuild project directory")
    parser.add_argument("--live", action="store_true", help="Start the editor in live mode")
    parser.add_argument("--shutdown", action="store_true", help="Forward shutdown to the shared editor")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    project = args.project_path.resolve()
    if not project.is_dir():
        print(f"Project not found: {project}", file=sys.stderr)
        return 1
    server = svg_editor_server_script()
    cmd = [sys.executable, str(server), str(project)]
    if args.live:
        cmd.append("--live")
    if args.shutdown:
        cmd.append("--shutdown")
    return subprocess.call(cmd)


if __name__ == "__main__":
    raise SystemExit(main())
