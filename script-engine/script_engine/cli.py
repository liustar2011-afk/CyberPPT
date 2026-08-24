"""Command line utilities for the standalone Script Engine boundary."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .contracts import load_json, validate_deck_plan, validate_final_script, validate_foundation
from .render import render_stage02_markdown


VALIDATORS = {
    "foundation": validate_foundation,
    "plan": validate_deck_plan,
    "final": validate_final_script,
}


def _validate(kind: str, path: Path) -> int:
    payload = load_json(path)
    issues = VALIDATORS[kind](payload)
    report = {
        "kind": kind,
        "path": str(path.resolve()),
        "status": "passed" if not issues else "failed",
        "issues": issues,
    }
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if not issues else 1


def _render(input_path: Path, output_path: Path) -> int:
    payload = load_json(input_path)
    issues = validate_final_script(payload)
    if issues:
        print(json.dumps({"status": "failed", "issues": issues}, ensure_ascii=False, indent=2), file=sys.stderr)
        return 1
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(render_stage02_markdown(payload), encoding="utf-8")
    print(str(output_path.resolve()))
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="cyberppt-script")
    sub = parser.add_subparsers(dest="command", required=True)

    validate = sub.add_parser("validate", help="Validate a Script Engine JSON artifact")
    validate.add_argument("kind", choices=sorted(VALIDATORS))
    validate.add_argument("path")

    render = sub.add_parser("render-stage02", help="Render final-script JSON to Stage 02-compatible Markdown")
    render.add_argument("input")
    render.add_argument("--output", default="dist/final-script.md")

    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.command == "validate":
        return _validate(args.kind, Path(args.path))
    if args.command == "render-stage02":
        return _render(Path(args.input), Path(args.output))
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
