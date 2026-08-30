from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from hashlib import sha256
from pathlib import Path
from typing import Any

from scripts.imagegen_pipeline.deliverable_prompt import parse_page_blocks, parse_pages
from scripts.imagegen_pipeline.page_manifest import PRODUCTION_MODES
from scripts.imagegen_pipeline.style_library import load_style_lock, write_project_style_lock
from cyberppt.artifact_ledger import write_json_atomic
from cyberppt.stage02_input import INPUT_JSON, prepare_stage02_input, resolve_input_script

from .models import Stage02BuildContext, Stage02RunOptions


STAGE_DIR = "workbench/stages/02-imagegen"
TEMPLATE_LOCK_DIR = "workbench/locks/template_text"
LEDGER_PATH = "workbench/artifact-ledger.json"
VISUAL_SPEC_PATH = Path("visual/deck-visual-spec.json")
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


def sha256_directory(path: Path | None) -> str:
    """Hash a directory by relative path and file content in stable order."""

    if path is None or not path.is_dir():
        return ""
    digest = sha256()
    for item in sorted((candidate for candidate in path.rglob("*") if candidate.is_file()), key=lambda value: value.as_posix()):
        relative = item.relative_to(path).as_posix()
        digest.update(relative.encode("utf-8"))
        digest.update(b"\0")
        digest.update((sha256_file(item) or "").encode("ascii"))
        digest.update(b"\0")
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
        data = load_style_lock(path)
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
    style_id = (data.get("style") or {}).get("id")
    if style_id != PRODUCTION_STYLE_ID:
        raise ValueError(
            f"Stage 02 main flow only supports visual Style 09; received style id {style_id!r}"
        )
    return data


def resolved_style_contract_sha256(style_data: dict[str, Any]) -> str:
    """Return the frozen contract hash validated by ``load_style_lock``."""

    style = style_data.get("style") if isinstance(style_data.get("style"), dict) else {}
    value = str(style.get("prompt_contract_sha256") or "").strip().lower()
    if not value:
        raise ValueError("production Style 09 lock has no frozen prompt_contract_sha256")
    return value


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


def input_fingerprint_for(
    *,
    source_script_sha256: str,
    script_input_sha256: str,
    visual_spec_sha256: str,
    style_lock_sha256: str,
    resolved_style_contract_sha256: str,
    selected_pages: tuple[int, ...],
    production_mode: str,
    assembly_mode: str,
    image_model: str,
    image_quality: str,
    prompt_enrich: str,
    no_style_reference: bool,
    skip_image_text_audit: bool,
    allow_prompt_edit: bool,
    prompt_overrides_sha256: str,
    autonomous_contract_sha256: str,
) -> str:
    """Build a timestamp-free identity for meaningful Stage 02 inputs."""

    payload = {
        "schema": "cyberppt.stage02_input_fingerprint.v1",
        "source_script_sha256": source_script_sha256,
        "script_input_sha256": script_input_sha256,
        "visual_spec_sha256": visual_spec_sha256,
        "style_lock_sha256": style_lock_sha256,
        "resolved_style_contract_sha256": resolved_style_contract_sha256,
        "selected_pages": list(selected_pages),
        "production_mode": production_mode,
        "assembly_mode": assembly_mode,
        "image_model": image_model,
        "image_quality": image_quality,
        "prompt_enrich": prompt_enrich,
        "no_style_reference": no_style_reference,
        "skip_image_text_audit": skip_image_text_audit,
        "allow_prompt_edit": allow_prompt_edit,
        "prompt_overrides_sha256": prompt_overrides_sha256,
        "autonomous_contract_sha256": autonomous_contract_sha256,
    }
    material = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return sha256(material.encode("utf-8")).hexdigest()


def build_id_for(
    *,
    script: Path,
    pages_raw: str,
    production_mode: str,
    style_lock: Path | None,
    requested: str | None = None,
    input_fingerprint: str | None = None,
) -> str:
    if requested:
        return requested.strip()
    if input_fingerprint:
        digest = input_fingerprint[:10]
    else:
        # Compatibility path for callers that still invoke build_id_for
        # directly. Canonical Stage 02 preflight always supplies the explicit
        # deterministic input fingerprint.
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

    source_mode = "autonomous_contract" if autonomous_authority is not None else "script_file"

    from cyberppt.commands.visual_structure_stage import assert_visual_structure_ready
    assert_visual_structure_ready(project, script)
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
    frozen_style_contract_sha256 = resolved_style_contract_sha256(style_data)
    full_reference_images: list[Path] = []
    reference_image = None if options.no_style_reference else style_data.get("reference_image")
    if isinstance(reference_image, dict) and reference_image.get("required_for_every_page"):
        reference_path = Path(str(reference_image.get("path", ""))).expanduser().resolve()
        if not reference_path.is_file():
            raise FileNotFoundError(f"required style reference image not found: {reference_path}")
        expected_hash = str(reference_image.get("sha256") or "").lower()
        actual_hash = str(sha256_file(reference_path) or "").lower()
        if expected_hash and expected_hash != actual_hash:
            raise ValueError(
                f"style reference image hash mismatch: {reference_path}; expected {expected_hash}, got {actual_hash}"
            )
        full_reference_images.append(reference_path)

    blocks = parse_page_blocks(script)
    pages = tuple(parse_pages(options.pages_raw, set(blocks)))
    slug = page_range_slug(pages)

    script_input_path = project / INPUT_JSON
    visual_spec_path = project / VISUAL_SPEC_PATH
    source_script_sha = sha256_file(script) or ""
    script_input_sha = sha256_file(script_input_path) or ""
    visual_spec_sha = sha256_file(visual_spec_path) or ""
    style_lock_sha = sha256_file(style_lock) or ""
    prompt_overrides_path = options.prompt_overrides_dir.expanduser().resolve() if options.prompt_overrides_dir else None
    input_fingerprint = input_fingerprint_for(
        source_script_sha256=source_script_sha,
        script_input_sha256=script_input_sha,
        visual_spec_sha256=visual_spec_sha,
        style_lock_sha256=style_lock_sha,
        resolved_style_contract_sha256=frozen_style_contract_sha256,
        selected_pages=pages,
        production_mode=options.production_mode,
        assembly_mode=options.assembly_mode,
        image_model=options.image_model,
        image_quality=options.image_quality,
        prompt_enrich=options.prompt_enrich,
        no_style_reference=options.no_style_reference,
        skip_image_text_audit=options.skip_image_text_audit,
        allow_prompt_edit=options.allow_prompt_edit,
        prompt_overrides_sha256=sha256_directory(prompt_overrides_path),
        autonomous_contract_sha256=sha256_file(autonomous_contract_path) or "" if autonomous_contract_path else "",
    )
    resolved_build_id = build_id_for(
        script=script,
        pages_raw=options.pages_raw,
        production_mode=options.production_mode,
        style_lock=style_lock,
        requested=options.build_id,
        input_fingerprint=input_fingerprint,
    )
    target_dir = explicit_output_dir(options.output_dir, resolved_build_id) if options.output_dir else versioned_output_dir(project, slug, resolved_build_id)

    return Stage02BuildContext(
        project=project,
        canonical_script=script,
        selected_pages=pages,
        pages_raw=options.pages_raw,
        build_id=resolved_build_id,
        build_dir=target_dir,
        style_lock=style_lock,
        source_script_sha256=source_script_sha,
        script_input_sha256=script_input_sha,
        visual_spec_sha256=visual_spec_sha,
        style_lock_sha256=style_lock_sha,
        production_mode=options.production_mode,
        assembly_mode=options.assembly_mode,
        source_mode=source_mode,
        input_fingerprint=input_fingerprint,
        resolved_style_contract_sha256=frozen_style_contract_sha256,
        full_reference_images=tuple(full_reference_images),
        autonomous_contract=autonomous_contract_path,
        project_created=False,
    )
