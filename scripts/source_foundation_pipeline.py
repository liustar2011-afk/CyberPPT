#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CONVERTER = ROOT / ".agents" / "skills" / "source-to-markdown" / "scripts" / "convert.py"
DEFAULT_PARSER = ROOT / ".agents" / "skills" / "source-structure-factbase" / "scripts" / "parse.py"
DEFAULT_SEMANTIC_PREPARE = ROOT / ".agents" / "skills" / "business-semantic-understanding" / "scripts" / "prepare.py"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="source-material-foundation",
        description="Run source-to-markdown and source-structure-factbase as a traceable two-layer source-material pipeline.",
    )
    parser.add_argument("input", help="Local source file, Markdown file, or source directory")
    parser.add_argument("-o", "--output", help="Pipeline output root")
    parser.add_argument("--recursive", action="store_true", help="Recurse into input subdirectories")
    parser.add_argument("--force", action="store_true", help="Overwrite existing pipeline artifacts")
    parser.add_argument("--report", action="store_true", help="Request layer reports")
    parser.add_argument("--ocr", action="store_true", help="Pass OCR request to source-to-markdown for non-Markdown inputs")
    parser.add_argument("--ocr-model", help="Pass OCR model to source-to-markdown")
    parser.add_argument("--prepare-semantic", action="store_true", help="Prepare layer-three semantic workpacks after structural parsing")
    parser.add_argument("--semantic-chunk-size", type=int, default=60, help="Maximum source facts per semantic work chunk (default: 60)")
    return parser


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _hidden_relative(path: Path, root: Path) -> bool:
    try:
        rel = path.relative_to(root)
    except ValueError:
        return False
    return any(part.startswith(".") for part in rel.parts)


def _collect(input_path: Path, recursive: bool, output_root: Path) -> list[Path]:
    if input_path.is_file():
        return [input_path]
    iterator = input_path.rglob("*") if recursive else input_path.glob("*")
    files: list[Path] = []
    for path in iterator:
        if not path.is_file() or _hidden_relative(path, input_path):
            continue
        try:
            path.resolve().relative_to(output_root.resolve())
            continue
        except (ValueError, OSError):
            pass
        if path.name.lower().endswith(".md.report.json"):
            continue
        files.append(path)
    return sorted(files, key=lambda p: p.relative_to(input_path).as_posix().lower())


def _scripts() -> tuple[Path, Path, Path]:
    converter = Path(os.environ.get("SOURCE_TO_MARKDOWN_SCRIPT", str(DEFAULT_CONVERTER))).expanduser()
    parser = Path(os.environ.get("SOURCE_STRUCTURE_FACTBASE_SCRIPT", str(DEFAULT_PARSER))).expanduser()
    semantic_prepare = Path(os.environ.get("BUSINESS_SEMANTIC_PREPARE_SCRIPT", str(DEFAULT_SEMANTIC_PREPARE))).expanduser()
    return converter, parser, semantic_prepare


def _run(command: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(command, text=True, capture_output=True, check=False)


def _relative_source(source: Path, input_path: Path) -> Path:
    if input_path.is_dir():
        return source.relative_to(input_path)
    return Path(source.name)


def _artifact_paths(source: Path, input_path: Path, output_root: Path) -> tuple[Path, Path, Path]:
    relative = _relative_source(source, input_path)
    markdown = (output_root / "markdown" / relative).with_suffix(".md")
    stem = relative.with_suffix("")
    foundation = output_root / "foundation" / stem
    semantic = output_root / "semantic" / stem
    return markdown, foundation, semantic


def _copy_markdown(source: Path, destination: Path, force: bool) -> tuple[bool, str | None]:
    if destination.exists() and not force:
        return False, f"Markdown output already exists: {destination}"
    destination.parent.mkdir(parents=True, exist_ok=True)
    try:
        shutil.copyfile(source, destination)
    except OSError as exc:
        return False, str(exc)
    return True, None


def _convert_raw(
    converter_script: Path,
    source: Path,
    destination: Path,
    *,
    force: bool,
    report: bool,
    ocr: bool,
    ocr_model: str | None,
) -> tuple[bool, str | None]:
    destination.parent.mkdir(parents=True, exist_ok=True)
    command = [sys.executable, str(converter_script), str(source), "-o", str(destination)]
    if force:
        command.append("--force")
    if report:
        command.append("--report")
    if ocr:
        command.append("--ocr")
    if ocr_model:
        command.extend(["--ocr-model", ocr_model])
    completed = _run(command)
    if completed.returncode != 0:
        error = completed.stderr.strip() or completed.stdout.strip() or f"converter exited {completed.returncode}"
        return False, error
    return True, None


def _parse_markdown(
    parser_script: Path,
    markdown: Path,
    foundation: Path,
    *,
    force: bool,
    report: bool,
) -> tuple[bool, str | None]:
    command = [sys.executable, str(parser_script), str(markdown), "-o", str(foundation)]
    if force:
        command.append("--force")
    if report:
        command.append("--report")
    completed = _run(command)
    if completed.returncode != 0:
        error = completed.stderr.strip() or completed.stdout.strip() or f"parser exited {completed.returncode}"
        return False, error
    return True, None




def _prepare_semantic(
    prepare_script: Path,
    foundation: Path,
    semantic: Path,
    *,
    force: bool,
    chunk_size: int,
) -> tuple[bool, str | None]:
    command = [
        sys.executable,
        str(prepare_script),
        str(foundation),
        "-o",
        str(semantic),
        "--chunk-size",
        str(chunk_size),
    ]
    if force:
        command.append("--force")
    completed = _run(command)
    if completed.returncode != 0:
        error = completed.stderr.strip() or completed.stdout.strip() or f"semantic prepare exited {completed.returncode}"
        return False, error
    return True, None

def main(argv: list[str] | None = None) -> int:
    ns = build_parser().parse_args(argv)
    input_path = Path(ns.input).expanduser()
    if not input_path.exists():
        print(f"[error] Input does not exist: {input_path}", file=sys.stderr)
        return 2

    if ns.output:
        output_root = Path(ns.output).expanduser()
    elif input_path.is_dir():
        output_root = input_path.parent / f"{input_path.name}.pipeline-output"
    else:
        output_root = input_path.parent / "pipeline-output"
    output_root.mkdir(parents=True, exist_ok=True)

    converter_script, parser_script, semantic_prepare_script = _scripts()
    if not parser_script.is_file():
        print(f"[error] Layer-two parser script not found: {parser_script}", file=sys.stderr)
        return 2

    sources = _collect(input_path, ns.recursive, output_root)
    items: list[dict] = []
    failures = 0

    for source in sources:
        markdown, foundation, semantic = _artifact_paths(source, input_path, output_root)
        item = {
            "source": str(source),
            "markdown": str(markdown),
            "foundation": str(foundation),
            "status": "pending",
        }
        if ns.prepare_semantic:
            item["semantic"] = str(semantic)

        if source.suffix.lower() == ".md":
            ok, error = _copy_markdown(source, markdown, ns.force)
            if not ok:
                item.update(status="error", stage="markdown-copy", error=error)
                items.append(item)
                failures += 1
                print(f"[error] {source}: {error}", file=sys.stderr)
                continue
        else:
            if not converter_script.is_file():
                error = f"Layer-one converter script not found: {converter_script}"
                item.update(status="error", stage="source-to-markdown", error=error)
                items.append(item)
                failures += 1
                print(f"[error] {source}: {error}", file=sys.stderr)
                continue
            ok, error = _convert_raw(
                converter_script,
                source,
                markdown,
                force=ns.force,
                report=ns.report,
                ocr=ns.ocr,
                ocr_model=ns.ocr_model,
            )
            if not ok:
                item.update(status="error", stage="source-to-markdown", error=error)
                items.append(item)
                failures += 1
                print(f"[error] {source}: {error}", file=sys.stderr)
                continue

        ok, error = _parse_markdown(
            parser_script,
            markdown,
            foundation,
            force=ns.force,
            report=ns.report,
        )
        if not ok:
            item.update(status="error", stage="source-structure-factbase", error=error)
            failures += 1
            print(f"[error] {source}: {error}", file=sys.stderr)
            items.append(item)
            continue

        if ns.prepare_semantic:
            if ns.semantic_chunk_size < 1:
                error = "--semantic-chunk-size must be at least 1"
                item.update(status="error", stage="business-semantic-understanding-prepare", error=error)
                failures += 1
                print(f"[error] {source}: {error}", file=sys.stderr)
                items.append(item)
                continue
            if not semantic_prepare_script.is_file():
                error = f"Layer-three semantic prepare script not found: {semantic_prepare_script}"
                item.update(status="error", stage="business-semantic-understanding-prepare", error=error)
                failures += 1
                print(f"[error] {source}: {error}", file=sys.stderr)
                items.append(item)
                continue
            ok, error = _prepare_semantic(
                semantic_prepare_script,
                foundation,
                semantic,
                force=ns.force,
                chunk_size=ns.semantic_chunk_size,
            )
            if not ok:
                item.update(status="error", stage="business-semantic-understanding-prepare", error=error)
                failures += 1
                print(f"[error] {source}: {error}", file=sys.stderr)
                items.append(item)
                continue
            item.update(status="ok", stage="semantic-prepared")
        else:
            item.update(status="ok", stage="complete")
        items.append(item)

    manifest = {
        "schema_version": "1.0",
        "pipeline_version": "0.5.0",
        "input": str(input_path),
        "output_root": str(output_root),
        "items": items,
        "summary": {
            "total": len(items),
            "ok": sum(1 for item in items if item["status"] == "ok"),
            "errors": sum(1 for item in items if item["status"] == "error"),
        },
    }
    _write_json(output_root / "manifest.json", manifest)

    if not sources:
        print(f"[error] No source files found in: {input_path}", file=sys.stderr)
        return 1
    print(str(output_root / "manifest.json"))
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
