"""User-facing ``cyberppt build`` command."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .build import (
    _default_workspace,
    _project_root_for_script,
    build_presentation,
    compact_build_result,
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="cyberppt build",
        description="Build PPT from a page script with practical defaults.",
    )
    parser.add_argument("script", help="Markdown page script.")
    parser.add_argument(
        "--project",
        help=(
            "Workspace directory. If omitted, CyberPPT reuses the nearest initialized "
            "project or creates <script-name>.cyberppt beside the script."
        ),
    )
    parser.add_argument(
        "--pages",
        help="Optional page range such as 1-8 or 1,3,5. Defaults to all pages in the script.",
    )
    parser.add_argument(
        "--mode",
        choices=("image", "editable", "both"),
        default="image",
        help=(
            "Output route. image is the zero-manual-step default; editable/both reuse the "
            "same audited image and may pause for the existing local editable-page step."
        ),
    )
    parser.add_argument("--image-model", help="Optional image-model override.")
    parser.add_argument(
        "--quality",
        choices=("low", "medium", "high", "max", "auto"),
        default="max",
        help="Image quality (default: max).",
    )
    parser.add_argument("--timeout", type=int, default=600, help="Image-generation timeout in seconds.")
    parser.add_argument("--force", action="store_true", help="Redraw images instead of reusing passed pages.")
    parser.add_argument("--build-id", help=argparse.SUPPRESS)
    parser.add_argument("--json", action="store_true", help="Print the compact result as JSON.")
    return parser


def _workspace_for_args(script: Path, project: str | None) -> Path:
    if project:
        return Path(project).expanduser().resolve()
    return _project_root_for_script(script) or _default_workspace(script)


def _print_human(result: dict[str, object]) -> None:
    print(f"status: {result.get('status')}")
    print(f"mode: {result.get('mode')}")
    pptx = result.get("pptx")
    if isinstance(pptx, dict):
        for mode, path in pptx.items():
            if path:
                print(f"pptx[{mode}]: {path}")
    print(f"workspace: {result.get('workspace')}")
    if result.get("next"):
        print(f"next: {result['next']}")
    actions = result.get("actions")
    if isinstance(actions, list):
        for action in actions:
            if isinstance(action, dict):
                label = action.get("action") or action.get("type") or action.get("message")
                if label:
                    print(f"action: {label}")
            elif action:
                print(f"action: {action}")


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    script = Path(args.script).expanduser().resolve()
    workspace = _workspace_for_args(script, args.project)
    try:
        summary = build_presentation(
            script,
            project=workspace,
            pages_raw=args.pages,
            mode=args.mode,
            image_model=args.image_model,
            image_quality=args.quality,
            image_timeout=args.timeout,
            force=args.force,
            build_id=args.build_id,
        )
    except (FileNotFoundError, OSError, RuntimeError, ValueError) as exc:
        print(str(exc), file=sys.stderr)
        return 2

    result = compact_build_result(
        summary,
        script=script,
        project=workspace,
        mode=args.mode,
    )
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        _print_human(result)
    return 0 if result["status"] in {"production_ready", "needs_action"} else 1


__all__ = ["build_parser", "main"]
