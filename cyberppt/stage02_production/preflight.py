from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from hashlib import sha256
from pathlib import Path
from typing import Any

from scripts.imagegen_pipeline.deliverable_prompt import parse_page_blocks, parse_pages
from scripts.imagegen_pipeline.page_manifest import PRODUCTION_MODES
from scripts.imagegen_pipeline.style_library import write_project_style_lock
from cyberppt.artifact_ledger import write_json_atomic
from cyberppt.stage02_input import INPUT_JSON, prepare_stage02_input, resolve_input_script

from .models import Stage02BuildContext, Stage02RunOptions


STAGE_DIR = "workbench/stages/02-imagegen"
TEMPLATE_LOCK_DIR = "workbench/locks/template_text"
LEDGER_PATH = "workbench/artifact-ledger.json"
PRODUCTION_STYLE_ID = 9


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def sha256_file(path: Path) -> str | None:
    if not path.is_file():
        return None
    digest = sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {"schema": "cyberppt.artifact_ledger.v1", "artifacts": []}
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"JSON root must be an object: {path}")
    return data


def write_json(path: Path, payload: dict[str, Any]) -> None:
    write_json_atomic(path, payload)


def read_style_lock(path: Path) -> dict[str, Any]:
    if not path.is_file():
        raise FileNotFoundError(f"visual style lock JSON not found: {path}")
    try:
        data = read_json(path)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValueError(
            f"--style-lock must point to a valid JSON visual style lock, not Markdown or plain text: {path}. "
            "Use --style-id/--style-name to generate the project JSON lock automatically."
        ) from exc
    if data.get("schema") != "cyberppt.visual_style_lock.v1":
        raise ValueError(
            f"--style-lock is not a CyberPPT visual style lock JSON: {path}; "
            "expected schema cyberppt.visual_style_lock.v1"
        )
    return data


def ensure_project_dirs(project: Path) -> None:
    for relative in (
        STAGE_DIR,
        TEMPLATE_LOCK_DIR,
        "workbench/stages/05-qa-delivery",
        "outputs/pages",
        "outputs/renders",
        "delivery",
    ):
        (project / relative).mkdir(parents=True, exist_ok=True)


def page_range_slug(pages: list[int] | tuple[int, ...]) -> str:
    pages = list(pages)
    if not pages:
        raise ValueError("at least one page is required")
    if pages == list(range(pages[0], pages[-1] + 1)):
        return f"pages_{pages[0]:03d}_{pages[-1]:03d}"
    explicit = "pages_" + "_".join(f"{page:03d}" for page in pages)
    if len(explicit) <= 80:
        return explicit
    digest = sha256(",".join(str(page) for page in pages).encode("ascii")).hexdigest()[:10]
    return f"pages_{pages[0]:03d}_{pages[-1]:03d}_{len(pages):02d}p_{digest}"


def build_id_for(
    *,
    script: Path,
    pages_raw: str,
    production_mode: str,
    style_lock: Path | None,
    requested: str | None = None,
) -> str:
    if requested:
        return requested.strip()
    material = "|".join(
        (
            str(script.resolve()),
            sha256_file(script) or "",
            pages_raw,
            production_mode,
            str(style_lock.resolve()) if style_lock else "",
            sha256_file(style_lock) or "" if style_lock else "",
        )
    )
    digest = sha256(material.encode("utf-8")).hexdigest()[:10]
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    return f"{stamp}-{digest}"


def versioned_output_dir(project: Path, page_slug: str, build_id: str) -> Path:
    base = project / STAGE_DIR / f"{page_slug}_{build_id}"
    if base.is_dir():
        context_path = base / "build_context.json"
        if context_path.is_file():
            try:
                context = read_json(context_path)
            except (OSError, ValueError, json.JSONDecodeError):
                context = {}
            if context.get("build_id") == build_id:
                return base
    candidate = base
    suffix = 2
    while candidate.exists():
        candidate = base.with_name(f"{base.name}_{suffix:02d}")
        suffix += 1
    return candidate


def explicit_output_dir(path: Path, build_id: str) -> Path:
    path = path.expanduser().resolve()
    if not path.exists() or not any(path.iterdir()):
        return path
    context_path = path / "build_context.json"
    if context_path.is_file():
        try:
            context = read_json(context_path)
        except (OSError, ValueError, json.JSONDecodeError):
            context = {}
        if context.get("build_id") == build_id:
            return path
    raise FileExistsError(
        f"output directory already contains another build: {path}; "
        "choose a new --build-id/--output-dir or resume the recorded build"
    )


def _require_ocr_if_needed(options: Stage02RunOptions) -> None:
    if not options.generate_images or options.skip_image_text_audit or options.dry_run_images:
        return
    try:
        import rapidocr_onnxruntime  # noqa: F401
    except ImportError as exc:
        raise RuntimeError(
            "rapidocr-onnxruntime is not importable in the current Python "
            f"environment ({sys.executable}); image generation requires it "
            "for the pre-enhancement text audit. If this repo has its own "
            ".venv, run this command with .venv/bin/python3 instead of the "
            "system python3, or pass --skip-image-text-audit to explicitly "
            "opt out of the text audit (not recommended for production)."
        ) from exc


def prepare_preflight(options: Stage02RunOptions) -> Stage02BuildContext:
    project = options.project.expanduser().resolve()
    script = options.script.expanduser().resolve()
    style_lock = options.style_lock.expanduser().resolve() if options.style_lock else None
    semantic_plan_dir = options.semantic_plan_dir.expanduser().resolve() if options.semantic_plan_dir else None
    _require_ocr_if_needed(options)

    source_script = script
    input_report = prepare_stage02_input(project, script=source_script, reuse_current=True)
    if input_report.get("status") != "passed":
        codes = ", ".join(item.get("code", "INPUT_INVALID") for item in input_report.get("blocking_issues", []))
        raise ValueError(f"Stage 02 script input is invalid: {codes}")
    script = resolve_input_script(project, source_script)

    autonomous_contract_path = options.autonomous_contract.expanduser().resolve() if options.autonomous_contract is not None else None
    autonomous_authority = None
    if autonomous_contract_path is not None:
        from cyberppt.autonomous_contract import load_contract, validate_source_boundary

        autonomous_authority = load_contract(autonomous_contract_path)
        if autonomous_authority.project != project:
            raise ValueError("autonomous contract targets another project")
        if style_lock is not None or options.style_id != autonomous_authority.style_id:
            raise ValueError("autonomous contract requires its declared --style-id and no alternate style lock")
        if options.production_mode != autonomous_authority.production_mode:
            raise ValueError("autonomous contract production mode does not match the contract")
        validate_source_boundary(autonomous_authority)

    source_mode = (
        "autonomous_contract"
        if autonomous_authority is not None
        else "external_script"
        if options.external_script
        else "script_file"
    )

    if options.production_mode not in PRODUCTION_MODES:
        raise ValueError(
            f"unsupported production mode: {options.production_mode}; expected one of {', '.join(PRODUCTION_MODES)}"
        )
    if semantic_plan_dir is not None:
        raise ValueError("--semantic-plan-dir was removed with the editable-overlay route")

    ensure_project_dirs(project)
    if style_lock is not None and (options.style_id is not None or options.style_name):
        raise ValueError("--style-lock cannot be combined with --style-id or --style-name")
    if style_lock is None:
        style_lock = write_project_style_lock(
            project=project,
            style_id=PRODUCTION_STYLE_ID,
            style_name=None,
            source_script=script,
        )
    style_data = read_style_lock(style_lock)
    full_reference_images: list[Path] = []
    reference_image = None if options.no_style_reference else style_data.get("reference_image")
    if isinstance(reference_image, dict):
        reference_path = Path(str(reference_image.get("path", ""))).expanduser().resolve()
        if reference_path.is_file():
            full_reference_images.append(reference_path)

    blocks = parse_page_blocks(script)
    pages = tuple(parse_pages(options.pages_raw, set(blocks)))
    slug = page_range_slug(pages)
    resolved_build_id = build_id_for(
        script=script,
        pages_raw=options.pages_raw,
        production_mode=options.production_mode,
        style_lock=style_lock,
        requested=options.build_id,
    )
    target_dir = explicit_output_dir(options.output_dir, resolved_build_id) if options.output_dir else versioned_output_dir(project, slug, resolved_build_id)

    script_input_path = project / INPUT_JSON
    return Stage02BuildContext(
        project=project,
        canonical_script=script,
        selected_pages=pages,
        pages_raw=options.pages_raw,
        build_id=resolved_build_id,
        build_dir=target_dir,
        style_lock=style_lock,
        source_script_sha256=sha256_file(script) or "",
        script_input_sha256=sha256_file(script_input_path) or "",
        # Stage 02 no longer has a visual-structure prerequisite. Keep the
        # field for build-context compatibility; it is intentionally empty.
        visual_spec_sha256="",
        style_lock_sha256=sha256_file(style_lock) or "",
        production_mode=options.production_mode,
        assembly_mode=options.assembly_mode,
        source_mode=source_mode,
        full_reference_images=tuple(full_reference_images),
        autonomous_contract=autonomous_contract_path,
        project_created=False,
    )
