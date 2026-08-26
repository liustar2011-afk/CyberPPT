from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

from .factbase import build_fact_base
from .parser import parse_document


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="source-structure-factbase",
        description="Parse normalized Markdown into traceable document structure and source-assertion fact base JSON.",
    )
    parser.add_argument("input", help="UTF-8 Markdown source file")
    parser.add_argument("-o", "--output", help="Output directory; defaults to <source-stem>.foundation")
    parser.add_argument("--force", action="store_true", help="Overwrite existing structure/fact-base outputs")
    parser.add_argument("--report", action="store_true", help="Write parse-report.json")
    return parser


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    ns = build_parser().parse_args(argv)
    source = Path(ns.input).expanduser()
    if not source.exists() or not source.is_file():
        print(f"[error] Input does not exist or is not a file: {source}", file=sys.stderr)
        return 2
    if source.suffix.lower() != ".md":
        print(f"[error] Layer two accepts Markdown only: {source}", file=sys.stderr)
        return 2

    out_dir = Path(ns.output).expanduser() if ns.output else source.with_name(f"{source.stem}.foundation")
    structure_path = out_dir / "structure.json"
    fact_path = out_dir / "fact-base.json"
    report_path = out_dir / "parse-report.json"
    protected = [structure_path, fact_path]
    if ns.report:
        protected.append(report_path)
    existing = [path for path in protected if path.exists()]
    if existing and not ns.force:
        print(
            "[error] Output already exists; use --force to overwrite: " + ", ".join(str(p) for p in existing),
            file=sys.stderr,
        )
        return 1

    try:
        markdown = source.read_text(encoding="utf-8")
    except (OSError, UnicodeError) as exc:
        print(f"[error] Failed to read UTF-8 Markdown: {source}: {exc}", file=sys.stderr)
        return 1

    structure = parse_document(markdown, source_name=source.name)
    fact_base = build_fact_base(structure)
    try:
        _write_json(structure_path, structure)
        _write_json(fact_path, fact_base)
        if ns.report:
            report = {
                "status": "ok",
                "input": str(source),
                "structure": str(structure_path),
                "fact_base": str(fact_path),
                "block_count": structure["document"]["block_count"],
                "fact_count": len(fact_base["entries"]),
                "warnings": structure.get("warnings", []) + fact_base.get("warnings", []),
            }
            _write_json(report_path, report)
    except OSError as exc:
        print(f"[error] Failed to write outputs: {exc}", file=sys.stderr)
        return 1

    print(str(structure_path))
    print(str(fact_path))
    if ns.report:
        print(str(report_path))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
