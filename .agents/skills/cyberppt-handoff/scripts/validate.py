#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from cyberppt_handoff.project import build_projection
from cyberppt_handoff.validate import validate_projection


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Validate a CyberPPT compatibility projection before writing it.")
    parser.add_argument("foundation")
    parser.add_argument("semantic")
    parser.add_argument("outline")
    ns = parser.parse_args(argv)
    try:
        result = validate_projection(build_projection(ns.foundation, ns.semantic, ns.outline))
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"[error] {exc}", file=sys.stderr)
        return 2
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["status"] == "ok" else 1


if __name__ == "__main__":
    raise SystemExit(main())
