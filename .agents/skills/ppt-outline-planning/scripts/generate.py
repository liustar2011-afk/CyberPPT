#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

# Make the Skill executable from the repository root as documented; callers do
# not need to install the package or know the Skill's internal import path.
SKILL_ROOT = Path(__file__).resolve().parents[1]
if str(SKILL_ROOT) not in sys.path:
    sys.path.insert(0, str(SKILL_ROOT))

from ppt_outline_planning.generate import generate_outline


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Generate a source-locked layer-four PPT Outline from a validated semantic foundation."
    )
    parser.add_argument("semantic", help="Directory containing validated layer-three semantic artifacts")
    parser.add_argument("-o", "--output", required=True, help="Outline directory containing outline-workpack.json")
    parser.add_argument("--authoring-spec", type=Path, help="Complete structured authoring spec; marks output author_edited")
    parser.add_argument("--force", action="store_true", help="Overwrite deck-brief.json and page-plan.json")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    spec = None
    if args.authoring_spec:
        spec = json.loads(args.authoring_spec.expanduser().read_text(encoding="utf-8"))
    try:
        result = generate_outline(
            Path(args.semantic),
            Path(args.output),
            authoring_spec=spec,
            force=args.force,
        )
    except (FileNotFoundError, FileExistsError, ValueError, json.JSONDecodeError) as exc:
        print(f"[error] {exc}", file=sys.stderr)
        return 2
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
