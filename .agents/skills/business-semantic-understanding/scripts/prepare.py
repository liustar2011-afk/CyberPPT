#!/usr/bin/env python3
from __future__ import annotations

import argparse
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from business_semantic_understanding.prepare import prepare_foundation


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Prepare a semantic workpack from layer-two foundation artifacts.")
    parser.add_argument("foundation", help="Directory containing structure.json and fact-base.json")
    parser.add_argument("-o", "--output", help="Semantic output directory")
    parser.add_argument("--chunk-size", type=int, default=60, help="Maximum source facts per work chunk (default: 60)")
    parser.add_argument("--force", action="store_true", help="Overwrite an existing workpack/chunks")
    ns = parser.parse_args(argv)

    foundation = Path(ns.foundation).expanduser()
    output = Path(ns.output).expanduser() if ns.output else foundation.parent / f"{foundation.name}.semantic"
    try:
        result = prepare_foundation(foundation, output, chunk_size=ns.chunk_size, force=ns.force)
    except (OSError, ValueError) as exc:
        print(f"[error] {exc}", file=sys.stderr)
        return 1
    print(result["workpack"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
