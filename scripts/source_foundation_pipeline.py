#!/usr/bin/env python3
from __future__ import annotations

import argparse
import importlib
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


def _import_skill_module(script_path: Path, module_name: str):
    """Import a skill's Python package directly instead of shelling out to its script.

    Layer two (source-structure-factbase) and layer three (business-semantic-
    understanding prepare) are plain, dependency-free Python with no need for an
    isolated interpreter/venv, unlike layer one which depends on MarkItDown and may
    delegate to a separate virtualenv. Running them in-process avoids one interpreter
    start-up per source file per layer.
    """
    skill_root = str(script_path.resolve().parent.parent)
    if skill_root not in sys.path:
        sys.path.insert(0, skill_root)
    return importlib.import_module(module_name)


def _run(command: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(command, text=True, capture_output=True, check=False)


def _extract_error(stdout: str, stderr: str, fallback: str, source: Path | None = None) -> str:
    """Pull the actual failure reason out of a failed subprocess's captured output.

    A failing child stage may print its own "[error] <source>: <message>" line and,
    before that, unrelated import-time warnings (e.g. a missing ffmpeg binary logged
    by pydub). Prefer the child's own last "[error]" line so the real cause is not
    buried under warning noise, and strip its "[error]"/source prefix so the caller's
    own "[error] {source}: {error}" wrapper does not duplicate either one.
    """
    text = (stderr or "").strip()
    if not text:
        text = (stdout or "").strip()
    if not text:
        return fallback
    error_lines = [line for line in text.splitlines() if line.startswith("[error]")]
    if error_lines:
        message = error_lines[-1][len("[error] "):]
        source_prefix = f"{source}: "
        if source is not None and message.startswith(source_prefix):
            message = message[len(source_prefix):]
        return message
    return text


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


def _foundation_up_to_date(foundation: Path) -> bool:
    return (foundation / "structure.json").is_file() and (foundation / "fact-base.json").is_file()


def _semantic_up_to_date(semantic: Path) -> bool:
    return (semantic / "semantic-workpack.json").is_file()


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
        error = _extract_error(completed.stdout, completed.stderr, f"converter exited {completed.returncode}", source=source)
        return False, error
    return True, None


def _parse_markdown_inprocess(
    parser_script: Path,
    markdown: Path,
    foundation: Path,
    *,
    force: bool,
    report: bool,
) -> tuple[bool, str | None]:
    try:
        cli = _import_skill_module(parser_script, "source_structure_factbase.cli")
    except ImportError as exc:
        return False, f"Failed to load source-structure-factbase from {parser_script}: {exc}"

    structure_path = foundation / "structure.json"
    fact_path = foundation / "fact-base.json"
    report_path = foundation / "parse-report.json"
    protected = [structure_path, fact_path] + ([report_path] if report else [])
    existing = [path for path in protected if path.exists()]
    if existing and not force:
        return False, "Output already exists; use --force to overwrite: " + ", ".join(str(p) for p in existing)

    try:
        markdown_text = markdown.read_text(encoding="utf-8")
    except (OSError, UnicodeError) as exc:
        return False, f"Failed to read UTF-8 Markdown: {markdown}: {exc}"

    structure = cli.parse_document(markdown_text, source_name=markdown.name)
    fact_base = cli.build_fact_base(structure)
    try:
        cli._write_json(structure_path, structure)
        cli._write_json(fact_path, fact_base)
        if report:
            report_payload = {
                "status": "ok",
                "input": str(markdown),
                "structure": str(structure_path),
                "fact_base": str(fact_path),
                "block_count": structure["document"]["block_count"],
                "fact_count": len(fact_base["entries"]),
                "warnings": structure.get("warnings", []) + fact_base.get("warnings", []),
            }
            cli._write_json(report_path, report_payload)
    except OSError as exc:
        return False, f"Failed to write outputs: {exc}"
    return True, None


def _prepare_semantic_inprocess(
    semantic_prepare_script: Path,
    foundation: Path,
    semantic: Path,
    *,
    force: bool,
    chunk_size: int,
) -> tuple[bool, str | None, dict | None]:
    try:
        prepare = _import_skill_module(semantic_prepare_script, "business_semantic_understanding.prepare")
    except ImportError as exc:
        return False, f"Failed to load business-semantic-understanding from {semantic_prepare_script}: {exc}", None
    try:
        result = prepare.prepare_foundation(foundation, semantic, chunk_size=chunk_size, force=force)
    except (OSError, ValueError) as exc:
        return False, str(exc), None
    details = {
        "upstream_changed": result["upstream_changed"],
        "invalidated_authored_artifacts": result["invalidated_authored_artifacts"],
        "foundation_digest": result["foundation_digest"],
    }
    return True, None, details


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
    try:
        _import_skill_module(parser_script, "source_structure_factbase.cli")
    except ImportError as exc:
        print(f"[error] Failed to load source-structure-factbase from {parser_script}: {exc}", file=sys.stderr)
        return 2
    if ns.prepare_semantic:
        if not semantic_prepare_script.is_file():
            print(f"[error] Layer-three semantic prepare script not found: {semantic_prepare_script}", file=sys.stderr)
            return 2
        try:
            _import_skill_module(semantic_prepare_script, "business_semantic_understanding.prepare")
        except ImportError as exc:
            print(f"[error] Failed to load business-semantic-understanding from {semantic_prepare_script}: {exc}", file=sys.stderr)
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

        stages_built: list[str] = []
        stages_skipped: list[str] = []
        failed = False

        # Stage 1: source -> Markdown.
        if markdown.exists() and not ns.force:
            stages_skipped.append("markdown")
        elif source.suffix.lower() == ".md":
            ok, error = _copy_markdown(source, markdown, ns.force)
            if not ok:
                item.update(status="error", stage="markdown-copy", error=error)
                items.append(item)
                failures += 1
                print(f"[error] {source}: {error}", file=sys.stderr)
                continue
            stages_built.append("markdown")
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
            stages_built.append("markdown")

        # Stage 2: Markdown -> structure + fact base.
        if _foundation_up_to_date(foundation) and not ns.force:
            stages_skipped.append("foundation")
        else:
            ok, error = _parse_markdown_inprocess(
                parser_script,
                markdown,
                foundation,
                force=ns.force,
                report=ns.report,
            )
            if not ok:
                item.update(status="error", stage="source-structure-factbase", error=error)
                items.append(item)
                failures += 1
                print(f"[error] {source}: {error}", file=sys.stderr)
                continue
            stages_built.append("foundation")

        # Stage 3 (optional): structure + fact base -> semantic workpack.
        if ns.prepare_semantic:
            if _semantic_up_to_date(semantic) and not ns.force:
                stages_skipped.append("semantic")
            else:
                if ns.semantic_chunk_size < 1:
                    error = "--semantic-chunk-size must be at least 1"
                    item.update(status="error", stage="business-semantic-understanding-prepare", error=error)
                    items.append(item)
                    failures += 1
                    print(f"[error] {source}: {error}", file=sys.stderr)
                    continue
                ok, error, semantic_prepare = _prepare_semantic_inprocess(
                    semantic_prepare_script,
                    foundation,
                    semantic,
                    force=ns.force,
                    chunk_size=ns.semantic_chunk_size,
                )
                if not ok:
                    item.update(status="error", stage="business-semantic-understanding-prepare", error=error)
                    items.append(item)
                    failures += 1
                    print(f"[error] {source}: {error}", file=sys.stderr)
                    continue
                item["semantic_prepare"] = semantic_prepare
                if semantic_prepare and semantic_prepare["invalidated_authored_artifacts"]:
                    print(
                        "[warning] Semantic source changed; invalidated authored artifacts: "
                        + ", ".join(semantic_prepare["invalidated_authored_artifacts"]),
                        file=sys.stderr,
                    )
                stages_built.append("semantic")
            item["stage"] = "semantic-prepared"
        else:
            item["stage"] = "complete"

        item["stages_built"] = stages_built
        item["stages_skipped"] = stages_skipped
        item["status"] = "ok" if stages_built else "skipped"
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
            "skipped": sum(1 for item in items if item["status"] == "skipped"),
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
