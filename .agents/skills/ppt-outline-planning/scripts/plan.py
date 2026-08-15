#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

SKILL_ROOT = Path(__file__).resolve().parents[1]
if str(SKILL_ROOT) not in sys.path:
    sys.path.insert(0, str(SKILL_ROOT))

from ppt_outline_planning.pipeline import run_outline_pipeline


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Generate, validate and render the official PPT Outline.")
    parser.add_argument("semantic", help="Validated layer-three semantic directory")
    parser.add_argument("-o", "--output", required=True, type=Path, help="Outline directory containing outline-workpack.json")
    parser.add_argument("--authoring-spec", type=Path)
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args(argv)
    try:
        result = run_outline_pipeline(
            args.semantic,
            args.output,
            authoring_spec_path=args.authoring_spec,
            force=args.force,
        )
    except (FileNotFoundError, FileExistsError, ValueError, json.JSONDecodeError) as exc:
        print(f"[error] {exc}", file=sys.stderr)
        return 2
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["status"] == "ok" else 1


if __name__ == "__main__":
    raise SystemExit(main())
