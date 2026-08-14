#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from business_semantic_understanding.validate import validate_semantic_outputs


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Validate layer-three semantic artifacts against layer-two evidence.")
    parser.add_argument("foundation", help="Directory containing structure.json and fact-base.json")
    parser.add_argument("semantic", help="Directory containing the four layer-three semantic artifacts")
    parser.add_argument("--report", action="store_true", help="Write semantic-report.json into the semantic directory")
    ns = parser.parse_args(argv)

    try:
        result = validate_semantic_outputs(Path(ns.foundation), Path(ns.semantic), write_report=ns.report)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"[error] {exc}", file=sys.stderr)
        return 2
    if ns.report:
        print(str(Path(ns.semantic) / "semantic-report.json"))
    else:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["status"] == "ok" else 1


if __name__ == "__main__":
    raise SystemExit(main())
