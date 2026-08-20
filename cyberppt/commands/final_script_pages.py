"""Project-level wrapper for running selected pages from a final script."""

from __future__ import annotations

import http.client
import json
import shutil
import sys
from datetime import datetime, timezone
from hashlib import sha256
from pathlib import Path
from typing import Any

from scripts.imagegen_pipeline.page_manifest import (
    FULL_IMAGE_MODE,
    PRODUCTION_MODES,
    build_manifest,
    output_variants_for_mode,
    require_generated,
)
from scripts.imagegen_pipeline.deliverable_prompt import parse_page_blocks, parse_pages, template_title
from scripts.imagegen_pipeline.imagegen_handoff import (
    IMAGEGEN_CANVAS_CONTRACT as BODY_IMAGE_CANVAS_CONTRACT,
    PresentationDecision,
    resolve_presentation_decision,
    select_image_locked_text,
    select_page_visual_intent_type,
)
from scripts.imagegen_pipeline.production_readiness import build_production_readiness
from scripts.image_to_pptx_runtime.stage02_adapter import (
    CANONICAL_EDITABLE_PPTX_ROUTE,
    run_stage02_reconstruction,
)
from scripts.imagegen_pipeline.providers.codex_oauth_image import (
    ensure_output_size,
    run_codex_image,
)
from scripts.imagegen_pipeline.style_library import write_project_style_lock
from cyberppt.artifact_ledger import append_artifacts, write_json_atomic
from cyberppt.script_quality_contract import (
    assert_imagegen_onscreen_readiness,
    parse_script_path,
)


STAGE_DIR = "workbench/stages/02-imagegen"
TEMPLATE_LOCK_DIR = "workbench/locks/template_text"
LEDGER_PATH = "workbench/artifact-ledger.json"
def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _failed_text_audit_image_path(output_path: Path, attempt: int) -> Path:
    return output_path.with_name(
        f"{output_path.stem}.attempt-{attempt:02d}-text-audit-failed{output_path.suffix}"
    )


def _text_correction_prompt(base_prompt: str, audit: dict[str, Any]) -> str:
    issues = json.dumps(audit.get("issues", []), ensure_ascii=False, indent=2)
    return f"""{base_prompt}

文字纠错重绘（最高优先级）：
第一张输入图片是上一轮生成但文字审计未通过的原图。请以该图为基础重新生成，保持其构图、配色、视觉层级、图形关系及所有无关文字不变。
只纠正下列已确认的错字或乱码；expected 是正确写法，observed 是原图中的错误写法，bbox 是错误位置（如有）：
{issues}
不得忽略、改写或扩展纠错清单，不得借机调整其他内容。所有纠错项必须按 expected 准确呈现。
"""


def _write_imagegen_attempt_record(
    output_path: Path,
    *,
    page_number: object,
    variant: str,
    attempt: int,
    prompt: str,
    base_prompt: str,
    image_paths: list[Path],
    model: str,
    quality: str,
    size: str,
    correction_audit: dict[str, Any] | None,
) -> dict[str, Any]:
    """Persist exactly what is about to be sent for one ImageGen attempt."""
    prompt_dir = output_path.parent / "prompts" / "attempts"
    prompt_dir.mkdir(parents=True, exist_ok=True)
    stem = f"page-{int(page_number):03d}-{variant}-attempt-{attempt:02d}"
    prompt_path = prompt_dir / f"{stem}-sent.txt"
    record_path = prompt_dir / f"{stem}-request.json"
    # Keep the audit artifact byte-identical to the string passed to the
    # backend.  On Windows the default text newline translation would turn
    # LF into CRLF after the hash had already been computed.
    prompt_path.write_text(prompt, encoding="utf-8", newline="")
    record = {
        "schema": "cyberppt.imagegen_attempt_request.v1",
        "page_number": page_number,
        "variant": variant,
        "attempt": attempt,
        "prompt_path": str(prompt_path.resolve()),
        "prompt_sha256": sha256(prompt.encode("utf-8")).hexdigest(),
        "base_prompt_sha256": sha256(base_prompt.encode("utf-8")).hexdigest(),
        "prompt_chars": len(prompt),
        "model": model,
        "quality": quality,
        "size": size,
        "input_images": [str(path.resolve()) for path in image_paths],
        "correction_retry": correction_audit is not None,
        "original_prompt": base_prompt if correction_audit is not None else None,
        "failed_image": (
            correction_audit.get("image") if correction_audit is not None else None
        ),
        "correction_issues": (
            correction_audit.get("issues", []) if correction_audit is not None else []
        ),
    }
    record_path.write_text(
        json.dumps(record, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    record["request_record_path"] = str(record_path.resolve())
    return record


def _page_range_slug(pages: list[int]) -> str:
    if not pages:
        raise ValueError("at least one page is required")
    if pages == list(range(pages[0], pages[-1] + 1)):
        return f"pages_{pages[0]:03d}_{pages[-1]:03d}"
    explicit = "pages_" + "_".join(f"{page:03d}" for page in pages)
    if len(explicit) <= 80:
        return explicit
    digest = sha256(",".join(str(page) for page in pages).encode("ascii")).hexdigest()[:10]
    return f"pages_{pages[0]:03d}_{pages[-1]:03d}_{len(pages):02d}p_{digest}"


def _build_id(
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
            _sha256(script) or "",
            pages_raw,
            production_mode,
            str(style_lock.resolve()) if style_lock else "",
            _sha256(style_lock) or "" if style_lock else "",
        )
    )
    digest = sha256(material.encode("utf-8")).hexdigest()[:10]
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    return f"{stamp}-{digest}"


def _versioned_output_dir(project: Path, page_slug: str, build_id: str) -> Path:
    """Return a versioned output directory, resuming only the same build ID."""

    base = project / STAGE_DIR / f"{page_slug}_{build_id}"
    if base.is_dir():
        context_path = base / "build_context.json"
        if context_path.is_file():
            try:
                context = _read_json(context_path)
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


def _explicit_output_dir(path: Path, build_id: str) -> Path:
    """Accept an explicit output directory only when it is empty or this build."""

    path = path.expanduser().resolve()
    if not path.exists() or not any(path.iterdir()):
        return path
    context_path = path / "build_context.json"
    if context_path.is_file():
        try:
            context = _read_json(context_path)
        except (OSError, ValueError, json.JSONDecodeError):
            context = {}
        if context.get("build_id") == build_id:
            return path
    raise FileExistsError(
        f"output directory already contains another build: {path}; "
        "choose a new --build-id/--output-dir or resume the recorded build"
    )


def _read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {"schema": "cyberppt.artifact_ledger.v1", "artifacts": []}
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"JSON root must be an object: {path}")
    return data


def _read_style_lock(path: Path) -> dict[str, Any]:
    if not path.is_file():
        raise FileNotFoundError(f"visual style lock JSON not found: {path}")
    try:
        data = _read_json(path)
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


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    write_json_atomic(path, payload)


def _sha256(path: Path) -> str | None:
    if not path.is_file():
        return None
    digest = sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _ensure_project_dirs(project: Path) -> None:
    for relative in (
        STAGE_DIR,
        TEMPLATE_LOCK_DIR,
        "workbench/stages/05-qa-delivery",
        "outputs/pages",
        "outputs/renders",
        "delivery",
    ):
        (project / relative).mkdir(parents=True, exist_ok=True)


def _template_text_lock(
    *,
    project: Path,
    script: Path,
    pages: list[int],
    pages_raw: str,
    style_lock: Path | None,
    manifest_path: Path,
    output_dir: Path,
    build_id: str,
    assembly_mode: str = "editable",
) -> Path:
    blocks = parse_page_blocks(script)
    document = parse_script_path(script)
    assert_imagegen_onscreen_readiness(document, set(pages))
    script_pages = {
        int(page.page_id[1:]): page
        for page in document.pages
    }
    records: list[dict[str, Any]] = []
    prior_decisions: list[PresentationDecision] = []
    for page_number in pages:
        page = blocks[page_number]
        script_page = script_pages.get(page_number)
        presentation: PresentationDecision | None = None
        if script_page is not None and script_page.page_type == "content":
            relation = select_page_visual_intent_type(script_page, "")
            presentation = resolve_presentation_decision(
                script_page,
                relation,
                tuple(prior_decisions),
            )
            prior_decisions.append(presentation)
        record: dict[str, Any] = {
                "page": page_number,
                "title": template_title(page),
                "subtitle": script_page.subtitle if script_page is not None else "",
                "section": "",
                "template_variant": "default",
                "page_badge_enabled": False,
                "footer_enabled": False,
                "source": str(script),
                "approved": True,
                "depends_on": [str(script), str(manifest_path)],
                "resume_command": (
                    "python -m cyberppt final-script-pages "
                    f"{project} --script {script} --pages {pages_raw}"
                    + (f" --style-lock {style_lock}" if style_lock else "")
                    + f" --assembly-mode {assembly_mode} --output-dir {output_dir} --build-id {build_id}"
                ),
            }
        if presentation is not None:
            record["presentation"] = presentation.to_dict()
            record["image_locked_text"] = select_image_locked_text(script_page)
            record["editable_body_text"] = script_page.onscreen_text.strip()
        records.append(record)
    payload = {
        "schema": "cyberppt.template_text_lock.v1",
        "created_at": _utc_now(),
        "project": str(project),
        "source_script": str(script),
        "style_lock": str(style_lock) if style_lock else None,
        "pages": pages,
        "records": records,
    }
    slug = _page_range_slug(pages)
    path = project / TEMPLATE_LOCK_DIR / f"{slug}_template_text_lock.json"
    _write_json(path, payload)
    return path


def _artifact_record(
    *,
    stage: str,
    page: str,
    path: Path,
    status: str,
    depends_on: list[Path],
    resume_command: str,
    supersedes: list[str] | None = None,
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "stage": stage,
        "page": page,
        "path": str(path),
        "status": status,
        "depends_on": [str(item) for item in depends_on],
        "supersedes": supersedes or [],
        "resume_command": resume_command,
        "sha256": _sha256(path),
        "updated_at": _utc_now(),
    }
    return payload


def _append_ledger(project: Path, records: list[dict[str, Any]], *, build_id: str) -> Path:
    return append_artifacts(project / LEDGER_PATH, records, build_id=build_id)


def _run_image_to_editable_svg_build(
    *,
    project: Path,
    manifest_path: Path,
    output_dir: Path,
    pages_raw: str,
    assembly_mode: str = "editable",
) -> dict[str, Any]:
    """Run the selected 2:1 body-to-template Stage 02 assembly route."""
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    available_pages = {
        int(value)
        for value in manifest.get("requested_pages", [])
        if isinstance(value, int) or str(value).isdigit()
    }
    requested_pages = parse_pages(pages_raw, available_pages)
    content_pages = {
        int(value)
        for value in manifest.get("content_page_numbers", [])
        if isinstance(value, int) or str(value).isdigit()
    }
    return run_stage02_reconstruction(
        project=project,
        manifest_path=manifest_path,
        output_dir=output_dir / "editable_svg",
        requested_pages=requested_pages,
        assembly_mode=assembly_mode,
    )


def _generate_manifest_images(
    manifest: dict[str, Any],
    *,
    checkpoint_path: Path | None = None,
    full_reference_images: list[Path] | None = None,
    model: str,
    quality: str,
    timeout: int,
    force: bool,
    dry_run: bool,
    skip_text_audit: bool = False,
) -> dict[str, Any]:
    if skip_text_audit:
        manifest["text_audit_contract"] = {
            "required_before_enhancement": False,
            "scope": "disabled_for_visual_composition_test",
            "max_generation_attempts": 1,
            "failure_action": "not_applicable",
        }
    production_mode = str(manifest.get("production_mode") or FULL_IMAGE_MODE)
    variants = output_variants_for_mode(production_mode)
    generated: list[str] = []
    skipped: list[str] = []
    failed: list[dict[str, Any]] = []
    text_audits: list[dict[str, Any]] = []
    imagegen_attempts: list[dict[str, Any]] = []
    for pair in manifest.get("pairs", []):
        full_path = Path(str((pair.get("full") or {}).get("path", "")))
        page_reference_images = [
            Path(str(item.get("path")))
            for item in (pair.get("reference_images") or [])
            if isinstance(item, dict) and item.get("path")
        ]
        for variant in variants:
            item = pair.get(variant) or {}
            output_path = Path(str(item.get("path", "")))
            text_truth = (
                pair.get("image_text_truth")
                if variant == "full" and not skip_text_audit
                else None
            )
            has_text_receipt = (item.get("text_audit") or {}).get("valid") is True
            if output_path.is_file() and not force and (
                not isinstance(text_truth, dict) or has_text_receipt
            ):
                item["status"] = "Generated"
                item.pop("last_error", None)
                skipped.append(str(output_path))
                if checkpoint_path is not None:
                    _write_json(checkpoint_path, manifest)
                continue
            input_images = (
                list(page_reference_images or full_reference_images or [])
                if variant == "full"
                else [full_path]
            )
            if variant != "full" and not full_path.is_file() and not dry_run:
                raise FileNotFoundError(
                    f"page {pair.get('page_number')} {variant} requires full image: {full_path}"
                )
            prompt = str(item.get("prompt", ""))
            base_prompt = prompt
            attempt_input_images = list(input_images)
            canvas = str(item.get("canvas") or "2048x1024")
            max_attempts = 3 if isinstance(text_truth, dict) else 1
            accepted_audit: dict[str, Any] | None = None
            correction_audit: dict[str, Any] | None = None
            try:
                for attempt in range(1, max_attempts + 1):
                    imagegen_attempts.append(
                        _write_imagegen_attempt_record(
                            output_path,
                            page_number=pair.get("page_number"),
                            variant=variant,
                            attempt=attempt,
                            prompt=prompt,
                            base_prompt=base_prompt,
                            image_paths=attempt_input_images,
                            model=model,
                            quality=quality,
                            size=canvas,
                            correction_audit=correction_audit,
                        )
                    )
                    run_codex_image(
                        prompt=prompt,
                        output_path=output_path,
                        image_paths=attempt_input_images,
                        model=model,
                        size=canvas,
                        quality=quality,
                        timeout=timeout,
                        force=True,
                        dry_run=dry_run,
                        postprocess=False,
                    )
                    if dry_run:
                        break
                    if isinstance(text_truth, dict):
                        from cyberppt.image_text_gate import audit_generated_image_text

                        audit = audit_generated_image_text(
                            output_path,
                            script_text=str(text_truth.get("script_text") or ""),
                            timeout=timeout,
                        )
                        audit["page_number"] = pair.get("page_number")
                        audit["attempt"] = attempt
                        text_audits.append(audit)
                        if not audit["valid"]:
                            if attempt < max_attempts:
                                if not output_path.is_file():
                                    raise FileNotFoundError(
                                        f"page {pair.get('page_number')} failed text audit image "
                                        f"not found for correction retry: {output_path}"
                                    )
                                failed_image = _failed_text_audit_image_path(output_path, attempt)
                                shutil.copy2(output_path, failed_image)
                                audit["image"] = str(failed_image)
                                audit["correction_retry"] = {
                                    "next_attempt": attempt + 1,
                                    "source_image": str(failed_image),
                                    "issues": audit.get("issues", []),
                                }
                                attempt_input_images = [failed_image, *input_images]
                                prompt = _text_correction_prompt(base_prompt, audit)
                                correction_audit = audit
                                continue
                            raise RuntimeError(
                                f"page {pair.get('page_number')} image text audit failed after "
                                f"{max_attempts} generation attempts; regenerate before enhancement: "
                                f"{json.dumps(audit.get('issues', []), ensure_ascii=False)}"
                            )
                        accepted_audit = audit
                    ensure_output_size(output_path, canvas)
                    break
            except (OSError, TimeoutError, http.client.HTTPException, RuntimeError) as exc:
                # A transient backend/network fault (broken pipe, connection
                # reset, timeout) on one page must not discard already-queued
                # work for every other page in the batch -- record it and move
                # on; the existing "skip if already Generated" logic above
                # makes a plain re-run pick up only the pages that actually
                # failed, instead of forcing a full-batch retry from scratch.
                item["status"] = "Failed"
                item["last_error"] = f"{type(exc).__name__}: {exc}"
                failed.append(
                    {
                        "page_number": pair.get("page_number"),
                        "variant": variant,
                        "path": str(output_path),
                        "error": item["last_error"],
                    }
                )
                if checkpoint_path is not None:
                    _write_json(checkpoint_path, manifest)
                continue
            if not dry_run:
                item["status"] = "Generated"
                item["generated_at"] = _utc_now()
                item.pop("last_error", None)
                if accepted_audit is not None:
                    item["text_audit"] = accepted_audit
            generated.append(str(output_path))
            if checkpoint_path is not None:
                _write_json(checkpoint_path, manifest)
    return {
        "backend": "codex_oauth_image",
        "production_mode": production_mode,
        "generated": generated,
        "skipped": skipped,
        "failed": failed,
        "dry_run": dry_run,
        "text_audit_skipped": skip_text_audit,
        "full_reference_images": [str(path) for path in (full_reference_images or [])],
        "text_audits": text_audits,
        "imagegen_attempts": imagegen_attempts,
    }


def run_final_script_pages(
    *,
    project: Path,
    script: Path,
    pages_raw: str,
    style_lock: Path | None = None,
    style_id: int | None = None,
    style_name: str | None = None,
    output_dir: Path | None = None,
    semantic_plan_dir: Path | None = None,
    require_images: bool = False,
    run_rebuild: bool = False,
    rebuild_args: list[str] | None = None,
    production_build: bool = False,
    production_mode: str = FULL_IMAGE_MODE,
    assembly_mode: str = "editable",
    generate_images: bool = False,
    image_model: str = "gpt-image-2",
    image_quality: str = "high",
    image_timeout: int = 600,
    force_images: bool = False,
    dry_run_images: bool = False,
    prompt_enrich: str = "off",
    require_send_approval: bool = False,
    build_id: str | None = None,
    external_script: bool = False,
    lightweight_stage01_confirmed: bool = False,
    autonomous_contract: Path | None = None,
    blueprint_only: bool = False,
    no_style_reference: bool = False,
    skip_image_text_audit: bool = False,
) -> dict[str, Any]:
    # Kept for direct-call compatibility. It has no authorization effect.
    _ = lightweight_stage01_confirmed
    project = project.expanduser().resolve()
    script = script.expanduser().resolve()
    style_lock = style_lock.expanduser().resolve() if style_lock else None
    semantic_plan_dir = semantic_plan_dir.expanduser().resolve() if semantic_plan_dir else None
    if not script.is_file():
        raise FileNotFoundError(f"final script not found: {script}")
    if generate_images and not skip_image_text_audit and not dry_run_images:
        # A missing OCR dependency used to surface only after Codex had
        # already spent real time/money generating an image for this page --
        # first observed when this command was run under the system's global
        # python3 instead of this repo's own .venv, which has
        # rapidocr-onnxruntime installed as a declared dependency (see
        # pyproject.toml) and the global interpreter does not. Fail before
        # any image generation starts instead of mid-batch.
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
    autonomous_contract_path = (
        autonomous_contract.expanduser().resolve()
        if autonomous_contract is not None
        else None
    )
    autonomous_authority = None
    if autonomous_contract_path is not None:
        from cyberppt.autonomous_contract import load_contract, validate_source_boundary

        autonomous_authority = load_contract(autonomous_contract_path)
        if autonomous_authority.project != project:
            raise ValueError("autonomous contract targets another project")
        if style_lock is not None or style_id != autonomous_authority.style_id:
            raise ValueError(
                "autonomous contract requires its declared --style-id and no alternate style lock"
            )
        if production_mode != autonomous_authority.production_mode:
            raise ValueError("autonomous contract production mode does not match the contract")
        validate_source_boundary(autonomous_authority)
    source_mode = (
        "autonomous_contract"
        if autonomous_authority is not None
        else "external_script"
        if external_script
        else "formal_project_script"
    )
    project_created = False
    from cyberppt.commands.visual_structure_stage import assert_visual_structure_ready
    from cyberppt.commands.script_audit import run_script_audit
    from cyberppt.stage02_handoff import (
        STAGE02_WAIVABLE_ERROR_CODES,
        audit_authorizes_stage02,
        load_stage02_handoff,
    )

    _, audit = run_script_audit(project, script)
    if not audit_authorizes_stage02(audit):
        raise ValueError(
            "final-script-pages requires a currently passed full-script audit "
            "(or one whose only remaining errors are documented-disposition "
            f"{sorted(STAGE02_WAIVABLE_ERROR_CODES)})"
        )
    load_stage02_handoff(project, required=True)
    assert_visual_structure_ready(project, script)
    if production_mode not in PRODUCTION_MODES:
        raise ValueError(
            f"unsupported production mode: {production_mode}; "
            f"expected one of {', '.join(PRODUCTION_MODES)}"
        )
    if run_rebuild:
        raise ValueError("--run-rebuild was removed; use --production-build for image-to-editable-svg")
    if semantic_plan_dir is not None:
        raise ValueError("--semantic-plan-dir was removed with the editable-overlay route")
    _ensure_project_dirs(project)
    if style_lock is not None and (style_id is not None or style_name):
        raise ValueError("--style-lock cannot be combined with --style-id or --style-name")
    if style_lock is None:
        style_lock = write_project_style_lock(
            project=project,
            style_id=style_id,
            style_name=style_name,
            source_script=script,
        )
    style_data = _read_style_lock(style_lock)
    full_reference_images: list[Path] = []
    reference_image = None if no_style_reference else style_data.get("reference_image")
    if isinstance(reference_image, dict) and reference_image.get("required_for_every_page"):
        reference_path = Path(str(reference_image.get("path", ""))).expanduser().resolve()
        if not reference_path.is_file():
            raise FileNotFoundError(f"required style reference image not found: {reference_path}")
        expected_hash = str(reference_image.get("sha256") or "").lower()
        actual_hash = str(_sha256(reference_path) or "").lower()
        if expected_hash and expected_hash != actual_hash:
            raise ValueError(
                f"style reference image hash mismatch: {reference_path}; "
                f"expected {expected_hash}, got {actual_hash}"
            )
        full_reference_images.append(reference_path)

    blocks = parse_page_blocks(script)
    pages = parse_pages(pages_raw, set(blocks))
    slug = _page_range_slug(pages)
    build_id = _build_id(
        script=script,
        pages_raw=pages_raw,
        production_mode=production_mode,
        style_lock=style_lock,
        requested=build_id,
    )
    target_dir = (
        _explicit_output_dir(output_dir, build_id)
        if output_dir
        else _versioned_output_dir(project, slug, build_id)
    )

    prior_manifest_path = target_dir / "page_image_pairs.json"
    prior_manifest = _read_json(prior_manifest_path) if prior_manifest_path.is_file() else None
    manifest, manifest_path, compiled_script, page_numbers = build_manifest(
        script=script,
        pages_raw=pages_raw,
        output_dir=target_dir,
        project_path=project,
        style_lock=style_lock,
        require_approved_prompts=(
            not blueprint_only
            and autonomous_authority is None
        ),
        production_mode=production_mode,
        prompt_enrich=prompt_enrich,
        require_send_approval=require_send_approval,
        enforce_prompt_freshness=False,
        compact_blueprint=False,
        prompt_compiler="artifact-spec-v2",
    )
    manifest["source_mode"] = source_mode
    manifest["source_script"] = str(script)
    manifest["source_script_sha256"] = _sha256(script)
    if isinstance(prior_manifest, dict):
        same_source = prior_manifest.get("source_script_sha256") == manifest["source_script_sha256"]
        same_mode = prior_manifest.get("production_mode") == manifest.get("production_mode")
        if same_source and same_mode:
            prior_pairs = {
                int(pair.get("page_number")): pair
                for pair in prior_manifest.get("pairs", [])
                if isinstance(pair, dict) and pair.get("page_number") is not None
            }
            for pair in manifest.get("pairs", []):
                prior_pair = prior_pairs.get(int(pair.get("page_number")))
                if not isinstance(prior_pair, dict):
                    continue
                prior_authoring_svg = Path(str(prior_pair.get("authoring_svg") or ""))
                prior_graphic_text_policy = prior_pair.get("graphic_text_policy")
                if prior_authoring_svg.is_file():
                    pair["authoring_svg"] = str(prior_authoring_svg)
                if (
                    isinstance(prior_graphic_text_policy, dict)
                    and prior_graphic_text_policy.get("status") == "complete"
                    and prior_graphic_text_policy.get("empty_container_check") == "passed"
                ):
                    pair["graphic_text_policy"] = prior_graphic_text_policy
                for variant in output_variants_for_mode(production_mode):
                    current_item = pair.get(variant) or {}
                    prior_item = prior_pair.get(variant) or {}
                    prior_path = Path(str(prior_item.get("path") or ""))
                    if (
                        prior_path == Path(str(current_item.get("path") or ""))
                        and prior_path.is_file()
                        and (prior_item.get("text_audit") or {}).get("valid") is True
                    ):
                        current_item["status"] = "Generated"
                        current_item["generated_at"] = prior_item.get("generated_at")
                        current_item["text_audit"] = prior_item["text_audit"]
    _write_json(manifest_path, manifest)
    lock_path = _template_text_lock(
        project=project,
        script=script,
        pages=page_numbers,
        pages_raw=pages_raw,
        style_lock=style_lock,
        manifest_path=manifest_path,
        output_dir=target_dir,
        build_id=build_id,
        assembly_mode=assembly_mode,
    )
    build_context_path = target_dir / "build_context.json"
    _write_json(
        build_context_path,
        {
            "schema": "cyberppt.build_context.v1",
            "build_id": build_id,
            "created_at": _utc_now(),
            "project": str(project),
            "source_script": str(script),
            "source_script_sha256": _sha256(script),
            "style_lock": str(style_lock),
            "style_lock_sha256": _sha256(style_lock),
            "page_set": page_numbers,
            "production_mode": production_mode,
            "assembly_mode": assembly_mode,
            "stage": "02-production-build" if production_build else "02-blueprint-image-to-editable-svg",
            "status": "in_progress",
            "artifacts": {"page_image_pairs": {"path": str(manifest_path), "sha256": _sha256(manifest_path)}},
        },
    )
    image_generation = None
    if generate_images:
        image_generation = _generate_manifest_images(
            manifest,
            checkpoint_path=manifest_path,
            full_reference_images=full_reference_images,
            model=image_model,
            quality=image_quality,
            timeout=image_timeout,
            force=force_images,
            dry_run=dry_run_images,
            skip_text_audit=skip_image_text_audit,
        )
        _write_json(manifest_path, manifest)
        failed_pages = image_generation.get("failed") or []
        if failed_pages:
            # Every other page in this batch already ran and was written to
            # manifest_path with status="Generated" above; raising only now
            # (not from inside the per-page loop) means a plain re-run of the
            # same command skips those and retries only what actually failed.
            summary = "; ".join(
                f"page {item.get('page_number')} {item.get('variant')}: {item.get('error')}"
                for item in failed_pages
            )
            raise RuntimeError(
                f"{len(failed_pages)} of {len(failed_pages) + len(image_generation.get('generated') or [])} "
                f"image generation attempts failed (likely transient backend/network faults); "
                f"already-generated pages were kept, re-run the same command to retry only the "
                f"failed ones: {summary}"
            )
    if require_images or (production_build and not dry_run_images):
        require_generated(manifest)

    resume_command = (
        f"python -m cyberppt run-autonomous {autonomous_contract_path} --resume"
        if autonomous_contract_path is not None
        else (
            f"python -m cyberppt final-script-pages {project} --script {script} "
            f"--pages {pages_raw} --style-lock {style_lock} --production-mode {production_mode} "
            f"--assembly-mode {assembly_mode} --output-dir {target_dir} --build-id {build_id}"
            + (" --generate-images" if generate_images else "")
            + (" --production-build" if production_build else "")
        )
    )
    production_readiness = None
    tool_consumption: dict[str, Any] = {}
    stage_name = "02-production-build" if production_build else "02-blueprint-image-to-editable-svg"
    if blueprint_only:
        status = "blueprint_created"
    elif generate_images and not dry_run_images:
        status = "image_assets_generated"
    else:
        status = "ready_for_image_generation" if not require_images else "image_assets_verified"
    image_to_editable_svg_build: dict[str, Any] | None = None
    rebuild_status: dict[str, Any] | None = None
    image_ppt_output_dir = target_dir / "editable_svg"
    if production_build:
        image_to_editable_svg_build = _run_image_to_editable_svg_build(
            project=project,
            manifest_path=manifest_path,
            output_dir=target_dir,
            pages_raw=pages_raw,
            assembly_mode=assembly_mode,
        )
        production_readiness = image_to_editable_svg_build["delivery_readiness"]
        tool_consumption = production_readiness["tool_consumption"]
        status = image_to_editable_svg_build["status"]
    run_summary = {
        "schema": "cyberppt.final_script_pages_run.v1",
        "build_id": build_id,
        "created_at": _utc_now(),
        "project": str(project),
        "source_script": str(script),
        "source_script_sha256": _sha256(script),
        "pages": page_numbers,
        "stage": stage_name,
        "source_mode": source_mode,
        "autonomous_contract": str(autonomous_contract_path) if autonomous_contract_path else None,
        "project_created": project_created,
        "status": status,
        "production_mode": production_mode,
        "assembly_mode": assembly_mode,
        "editable_pptx_route": CANONICAL_EDITABLE_PPTX_ROUTE,
        "artifacts": {
            "compiled_deliverable_prompt": str(compiled_script),
            "page_image_pairs": str(manifest_path),
            "template_text_lock": str(lock_path),
            "visual_style_lock": str(style_lock),
            "output_dir": str(target_dir),
            "image_ppt_output_dir": str(image_ppt_output_dir),
            "reconstruction_inventory": image_to_editable_svg_build["artifacts"].get("reconstruction_inventory") if image_to_editable_svg_build else None,
            "svg_output": image_to_editable_svg_build["artifacts"].get("svg_output") if image_to_editable_svg_build else None,
            "reconstruction_quality": image_to_editable_svg_build["artifacts"].get("reconstruction_quality") if image_to_editable_svg_build else None,
            "delivery_readiness": image_to_editable_svg_build["artifacts"].get("delivery_readiness") if image_to_editable_svg_build else None,
            "exported_pptx": image_to_editable_svg_build["artifacts"].get("exported_pptx") if image_to_editable_svg_build else None,
            "exported_pptx_by_mode": image_to_editable_svg_build.get("artifacts_by_mode") if image_to_editable_svg_build else None,
            "semantic_plan_dir": str(semantic_plan_dir) if semantic_plan_dir else None,
        },
        "next_steps": [
            (
                "Generate the audited 2:1 full image, then publish the selected image, editable SVG, or both template-assembled PPTX routes."
            ),
            (
                "A page with manual_required evidence cannot be exported; complete its verified reconstruction first."
            ),
        ],
        "resume_command": resume_command,
        "rebuild": rebuild_status,
        "image_to_editable_svg_build": image_to_editable_svg_build,
        "image_generation": image_generation,
        "prompt_enrich": manifest.get("prompt_enrich"),
        "tool_consumption": tool_consumption,
        "production_readiness": production_readiness,
    }
    build_context = {
        "schema": "cyberppt.build_context.v1",
        "build_id": build_id,
        "created_at": run_summary["created_at"],
        "project": str(project),
        "source_script": str(script),
        "source_script_sha256": _sha256(script),
        "style_lock": str(style_lock),
        "style_lock_sha256": _sha256(style_lock),
        "page_set": page_numbers,
        "production_mode": production_mode,
        "editable_pptx_route": CANONICAL_EDITABLE_PPTX_ROUTE,
        "stage": stage_name,
        "source_mode": source_mode,
        "autonomous_contract": (
            {
                "path": str(autonomous_contract_path),
                "sha256": _sha256(autonomous_contract_path),
            }
            if autonomous_contract_path is not None
            else None
        ),
        "project_created": project_created,
        "status": status,
        "artifacts": {
            "compiled_deliverable_prompt": {
                "path": str(compiled_script),
                "sha256": _sha256(compiled_script),
            },
            "page_image_pairs": {
                "path": str(manifest_path),
                "sha256": _sha256(manifest_path),
            },
            "template_text_lock": {
                "path": str(lock_path),
                "sha256": _sha256(lock_path),
            },
            "visual_style_lock": {
                "path": str(style_lock),
                "sha256": _sha256(style_lock),
            },
        },
    }
    if image_to_editable_svg_build and image_to_editable_svg_build["artifacts"].get("exported_pptx"):
        build_context["artifacts"]["exported_pptx"] = {
            "path": image_to_editable_svg_build["artifacts"].get("exported_pptx"),
            "sha256": (
                _sha256(Path(image_to_editable_svg_build["artifacts"]["exported_pptx"]))
                if image_to_editable_svg_build["artifacts"].get("exported_pptx")
                else None
            ),
        }
    _write_json(build_context_path, build_context)
    run_summary["artifacts"]["build_context"] = str(build_context_path)
    summary_path = target_dir / f"{slug}_final_script_pages_run.json"
    _write_json(summary_path, run_summary)

    page_label = f"{page_numbers[0]}-{page_numbers[-1]}" if len(page_numbers) > 1 else str(page_numbers[0])
    ledger_records = [
        _artifact_record(
            stage=stage_name,
            page=page_label,
            path=compiled_script,
            status=status,
            depends_on=[script, style_lock],
            resume_command=resume_command,
        ),
        _artifact_record(
            stage=stage_name,
            page=page_label,
            path=manifest_path,
            status=status,
            depends_on=[compiled_script],
            resume_command=resume_command,
        ),
        _artifact_record(
            stage=stage_name,
            page=page_label,
            path=lock_path,
            status="approved",
            depends_on=[script, manifest_path],
            resume_command=resume_command,
        ),
        _artifact_record(
            stage=stage_name,
            page=page_label,
            path=style_lock,
            status="approved",
            depends_on=[script],
            resume_command=resume_command,
        ),
        _artifact_record(
            stage=stage_name,
            page=page_label,
            path=summary_path,
            status=status,
            depends_on=[compiled_script, manifest_path, lock_path, style_lock],
            resume_command=resume_command,
        ),
        _artifact_record(
            stage=stage_name,
            page=page_label,
            path=build_context_path,
            status=status,
            depends_on=[script, compiled_script, manifest_path, lock_path, style_lock],
            resume_command=resume_command,
        ),
    ]
    exported_pptx = image_to_editable_svg_build["artifacts"].get("exported_pptx") if image_to_editable_svg_build else None
    if exported_pptx:
        ledger_records.append(
            _artifact_record(
                stage="05-qa-delivery" if status == "production_ready" else stage_name,
                page=page_label,
                path=Path(exported_pptx),
                status="assembled" if status == "production_ready" else status,
                depends_on=[manifest_path, lock_path, style_lock],
                resume_command=resume_command,
            )
        )
    # A dry run persists reviewable prompts and request previews, but it must not
    # reserve immutable artifact ids.  The real run reuses the same build id and
    # paths with generated hashes/statuses, which would otherwise conflict with
    # the preview records written a few seconds earlier.
    if not dry_run_images:
        _append_ledger(
            project,
            ledger_records,
            build_id=build_id,
        )
    return run_summary
