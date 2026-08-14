"""Direct diagnostic CLI for audited image-to-editable-SVG reconstruction."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from .orchestrator import run_image_to_editable_svg


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project", type=Path, required=True)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path)
    parser.add_argument("--pages", help="comma-separated selected page numbers")
    args = parser.parse_args(argv)
    pages = [int(value) for value in args.pages.split(",") if value.strip()] if args.pages else None
    result = run_image_to_editable_svg(project=args.project, manifest_path=args.manifest, output_dir=args.output_dir, requested_pages=pages)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["status"] == "production_ready" else 2


if __name__ == "__main__":
    raise SystemExit(main())
