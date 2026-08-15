#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

SKILL_ROOT = Path(__file__).resolve().parents[1]
if str(SKILL_ROOT) not in sys.path:
    sys.path.insert(0, str(SKILL_ROOT))

from ppt_outline_planning.authoring_spec import prepare_authoring_spec


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Prepare a source-bound blank PPT Outline authoring spec.")
    parser.add_argument("semantic", help="Validated layer-three semantic directory")
    parser.add_argument("-o", "--output", required=True, type=Path, help="Authoring spec JSON path")
    parser.add_argument("--outline-dir", required=True, type=Path, help="Outline directory containing outline-workpack.json")
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args(argv)
    try:
        result = prepare_authoring_spec(args.semantic, args.outline_dir, args.output, force=args.force)
    except (FileNotFoundError, FileExistsError, ValueError, json.JSONDecodeError) as exc:
        print(f"[error] {exc}", file=sys.stderr)
        return 2
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
