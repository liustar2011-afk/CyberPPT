from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .converter import (
    ConversionError,
    ConversionOptions,
    ConversionResult,
    convert_file,
    default_output_path,
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="source-to-markdown",
        description=(
            "Convert source documents to normalized Markdown with Microsoft MarkItDown, "
            "preserving source wording and adding provenance metadata."
        ),
    )
    parser.add_argument("input", help="Source file or directory")
    parser.add_argument(
        "-o",
        "--output",
        help="Output Markdown file for single-file input, or output directory for directory input",
    )
    parser.add_argument("--recursive", action="store_true", help="Recurse into subdirectories")
    parser.add_argument("--force", action="store_true", help="Overwrite existing Markdown files")
    parser.add_argument(
        "--report",
        action="store_true",
        help="Write a JSON sidecar report next to each generated Markdown file",
    )
    parser.add_argument(
        "--ocr",
        action="store_true",
        help="Enable the optional official markitdown-ocr plugin",
    )
    parser.add_argument(
        "--ocr-model",
        help="LLM model name used by markitdown-ocr; may also be set with MARKITDOWN_OCR_MODEL",
    )
    parser.add_argument(
        "--allow-empty",
        action="store_true",
        help="Write metadata even if conversion produces no source text",
    )
    return parser


def _is_hidden_relative(path: Path, root: Path) -> bool:
    try:
        rel = path.relative_to(root)
    except ValueError:
        rel = path
    return any(part.startswith(".") for part in rel.parts)


def collect_sources(root: Path, recursive: bool) -> list[Path]:
    root = Path(root)
    iterator = root.rglob("*") if recursive else root.glob("*")
    files: list[Path] = []
    for path in iterator:
        if not path.is_file():
            continue
        if _is_hidden_relative(path, root):
            continue
        rel_parts = path.relative_to(root).parts
        if "markdown-output" in rel_parts:
            continue
        if path.suffix.lower() == ".md" or path.name.lower().endswith(".md.report.json"):
            continue
        files.append(path)
    return sorted(files, key=lambda p: p.relative_to(root).as_posix().lower())


def destination_for(source: Path, input_root: Path, output_root: Path) -> Path:
    relative = source.relative_to(input_root)
    return (output_root / relative).with_suffix(".md")


def _write_report(result: ConversionResult, error: str | None = None) -> None:
    report_path = result.destination.with_suffix(result.destination.suffix + ".report.json")
    payload = {
        "source": str(result.source),
        "destination": str(result.destination),
        "status": "error" if error else "ok",
        "text_chars": result.text_chars,
        "warnings": result.warnings,
        "error": error,
    }
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def _emit_warnings(result: ConversionResult) -> None:
    for item in result.warnings:
        print(
            f"[{item['severity']}] {result.source}: {item['code']}: {item['message']}",
            file=sys.stderr,
        )


def _convert_one(
    source: Path,
    destination: Path,
    options: ConversionOptions,
    report: bool,
) -> tuple[bool, str | None]:
    try:
        result = convert_file(source, destination, options)
    except (OSError, ConversionError) as exc:
        print(f"[error] {source}: {exc}", file=sys.stderr)
        if report:
            failed = ConversionResult(source=source, destination=destination)
            _write_report(failed, error=str(exc))
        return False, str(exc)

    _emit_warnings(result)
    if report:
        _write_report(result)
    print(str(result.destination))
    return True, None


def main(argv: list[str] | None = None) -> int:
    ns = build_parser().parse_args(argv)
    input_path = Path(ns.input).expanduser()
    if not input_path.exists():
        print(f"[error] Input does not exist: {input_path}", file=sys.stderr)
        return 2

    options = ConversionOptions(
        force=ns.force,
        allow_empty=ns.allow_empty,
        ocr=ns.ocr,
        ocr_model=ns.ocr_model,
    )

    if input_path.is_file():
        destination = Path(ns.output).expanduser() if ns.output else default_output_path(input_path)
        success, _ = _convert_one(input_path, destination, options, ns.report)
        return 0 if success else 1

    output_root = (
        Path(ns.output).expanduser() if ns.output else input_path / "markdown-output"
    )
    sources = collect_sources(input_path, recursive=ns.recursive)
    if not sources:
        print(f"[error] No convertible source files found in: {input_path}", file=sys.stderr)
        return 1

    failures = 0
    for source in sources:
        destination = destination_for(source, input_path, output_root)
        success, _ = _convert_one(source, destination, options, ns.report)
        if not success:
            failures += 1
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
