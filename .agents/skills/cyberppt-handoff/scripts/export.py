#!/usr/bin/env python3
from __future__ import annotations

import argparse
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from cyberppt_handoff.write import export_projection


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Project validated Source Material Foundation artifacts into a CyberPPT-compatible project tree.")
    parser.add_argument("foundation")
    parser.add_argument("semantic")
    parser.add_argument("outline")
    parser.add_argument("-o", "--output", required=True)
    parser.add_argument("--force", action="store_true")
    parser.add_argument("--cyberppt-root", help="Optional local CyberPPT checkout; when supplied, run its lightweight outline-audit against the exported projection")
    ns = parser.parse_args(argv)
    try:
        result = export_projection(ns.foundation, ns.semantic, ns.outline, ns.output, force=ns.force, cyberppt_root=ns.cyberppt_root)
    except (OSError, ValueError) as exc:
        print(f"[error] {exc}", file=sys.stderr)
        return 2
    print(Path(ns.output).resolve() / "integration/cyberppt-handoff-report.json")
    return 0 if result.get("status") in {"projection_validated", "cyberppt_runtime_validated"} else 1


if __name__ == "__main__":
    raise SystemExit(main())
