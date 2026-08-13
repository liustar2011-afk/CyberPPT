"""Project-level wrapper for running selected pages from a final script."""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from hashlib import sha256
from pathlib import Path
from typing import Any

from scripts.dual_image_overlay.cyberppt_pair_manifest import (
    DUAL_IMAGE_MODE,
    FULL_IMAGE_MODE,
    PRODUCTION_MODES,
    TRIPLE_IMAGE_MODE,
    build_manifest,
    output_variants_for_mode,
    require_generated,
)
from scripts.dual_image_overlay.deliverable_prompt import parse_page_blocks, parse_pages, template_title
from scripts.dual_image_overlay.imagegen_handoff import (
    IMAGEGEN_CANVAS_CONTRACT as BODY_IMAGE_CANVAS_CONTRACT,
    PresentationDecision,
    resolve_presentation_decision,
    select_image_locked_text,
    select_page_visual_intent_type,
)
from scripts.dual_image_overlay.production_readiness import build_production_readiness
from scripts.dual_image_overlay.rebuild_engine.codex_oauth_image import (
    ensure_output_size,
    run_codex_image,
)
from scripts.dual_image_overlay.style_library import write_project_style_lock
from cyberppt.artifact_ledger import append_artifacts, write_json_atomic
from cyberppt.commands.init_project import init_project
from cyberppt.script_quality_contract import (
    assert_imagegen_onscreen_readiness,
    parse_script_path,
)


STAGE_DIR = "workbench/stages/02-blueprint-dual-image"
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
        "workbench/stages/03-overlay",
        "workbench/stages/04-template-rebuild",
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
                    + f" --output-dir {output_dir} --build-id {build_id}"
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


def _template_rebuild_failure_message(project: Path, returncode: int) -> str:
    readiness_path = project / "analysis" / "template_rebuild_readiness.json"
    source_gate_path = project / "analysis" / "source_capture_gate.json"
    page_quality_path = project / "analysis" / "page_quality_report.json"
    lines = [
        f"template rebuild quality gate failed with exit code {returncode}.",
        "Stop delivery progression; generated PPTX, if any, is an intermediate artifact only.",
    ]
    if readiness_path.is_file():
        readiness = _read_json(readiness_path)
        lines.append(f"readiness: {readiness_path}")
        lines.append(f"status: {readiness.get('status')}")
        lines.append(f"valid: {readiness.get('valid')}")
        checks = readiness.get("checks")
        if isinstance(checks, dict):
            failed = [key for key, value in checks.items() if value is False]
            if failed:
                lines.append("failed_checks: " + ", ".join(failed))
        artifacts = readiness.get("artifacts")
        if isinstance(artifacts, dict) and artifacts.get("exported_pptx"):
            lines.append(f"intermediate_pptx: {artifacts['exported_pptx']}")
    else:
        lines.append(f"readiness: missing ({readiness_path})")

    if source_gate_path.is_file():
        source_gate = _read_json(source_gate_path)
        gap_counts = source_gate.get("gap_counts")
        if isinstance(gap_counts, dict) and gap_counts:
            lines.append("blocking_gap_counts: " + ", ".join(f"{key}={value}" for key, value in gap_counts.items()))
        blocking = source_gate.get("blocking_gaps")
        if isinstance(blocking, list) and blocking:
            lines.append("blocking_gaps:")
            for gap in blocking[:12]:
                if not isinstance(gap, dict):
                    continue
                page = gap.get("page_number")
                code = gap.get("code")
                message = gap.get("message")
                lines.append(f"- page {page}: {code} - {message}")
            if len(blocking) > 12:
                lines.append(f"- ... {len(blocking) - 12} more")
    else:
        lines.append(f"source_capture_gate: missing ({source_gate_path})")

    if page_quality_path.is_file():
        page_quality = _read_json(page_quality_path)
        lines.append(f"page_quality_report: {page_quality_path}")
        lines.append(f"page_quality_valid: {page_quality.get('valid')}")
        blocking = page_quality.get("blocking_errors")
        if isinstance(blocking, list) and blocking:
            lines.append("page_quality_blocking_errors:")
            for item in blocking[:12]:
                if isinstance(item, dict):
                    lines.append(f"- {item.get('id')}: {item.get('description')}")
            if len(blocking) > 12:
                lines.append(f"- ... {len(blocking) - 12} more")
    else:
        lines.append(f"page_quality_report: missing ({page_quality_path})")
    return "\n".join(lines)


def _template_rebuild_artifacts(project: Path) -> dict[str, str | None]:
    artifacts = {
        "template_rebuild_readiness": project / "analysis" / "template_rebuild_readiness.json",
        "source_capture": project / "analysis" / "source_capture.json",
        "source_capture_gate": project / "analysis" / "source_capture_gate.json",
        "template_gate": project / "analysis" / "template_gate.json",
        "page_quality_report": project / "analysis" / "page_quality_report.json",
    }
    return {key: str(path) if path.exists() else None for key, path in artifacts.items()}


def _artifact_if_file(path: Path | str | None) -> str | None:
    if path is None:
        return None
    candidate = Path(path)
    return str(candidate.resolve()) if candidate.is_file() else None


def _artifact_if_dir_has_files(path: Path | str | None, pattern: str = "*.json") -> str | None:
    if path is None:
        return None
    candidate = Path(path)
    return str(candidate.resolve()) if candidate.is_dir() and any(candidate.glob(pattern)) else None


def _first_artifact_file(*paths: Path | str | None) -> str | None:
    for path in paths:
        artifact = _artifact_if_file(path)
        if artifact:
            return artifact
    return None


def _first_artifact_dir(*paths: Path | str | None, pattern: str = "*.json") -> str | None:
    for path in paths:
        artifact = _artifact_if_dir_has_files(path, pattern)
        if artifact:
            return artifact
    return None


def _first_matching_file(directory: Path, pattern: str) -> str | None:
    matches = sorted(directory.glob(pattern)) if directory.is_dir() else []
    return str(matches[0].resolve()) if matches else None


def _stage02_production_artifacts(project: Path) -> dict[str, str | None]:
    analysis = project / "analysis"
    readiness_path = analysis / "template_rebuild_readiness.json"
    readiness = _read_json(readiness_path) if readiness_path.is_file() else {}
    readiness_artifacts = readiness.get("artifacts")
    if not isinstance(readiness_artifacts, dict):
        readiness_artifacts = {}
    exported_pptx = readiness_artifacts.get("exported_pptx")
    if not exported_pptx:
        pointer_path = analysis / "export_artifact.json"
        if pointer_path.is_file():
            try:
                pointer = _read_json(pointer_path)
            except (OSError, ValueError, json.JSONDecodeError):
                pointer = {}
            exported_pptx = pointer.get("path") if isinstance(pointer, dict) else None
            if exported_pptx and isinstance(pointer, dict):
                expected_hash = str(pointer.get("sha256") or "").lower()
                actual_hash = str(_sha256(Path(str(exported_pptx))) or "").lower()
                if expected_hash and expected_hash != actual_hash:
                    exported_pptx = None

    semantic_plan_dir = readiness_artifacts.get("semantic_plan_dir") or analysis / "semantic_plan"
    scene_graph_dir = readiness_artifacts.get("scene_graph_gate_dir") or analysis / "scene_graph_gate"
    visual_registry_dir = (
        readiness_artifacts.get("measured_visual_registry")
        or readiness_artifacts.get("draft_visual_registry")
        or analysis / "visual_registry"
    )
    return {
        "source_capture": _first_artifact_file(
            readiness_artifacts.get("source_capture"),
            analysis / "source_capture.json",
        ),
        "semantic_binding": _first_artifact_file(
            readiness_artifacts.get("semantic_binding"),
            analysis / "semantic_binding" / "semantic_binding_index.json",
        ),
        "semantic_plan": _first_artifact_dir(semantic_plan_dir, pattern="*.json"),
        "scene_graph": _first_artifact_dir(scene_graph_dir, pattern="*.json"),
        "visual_registry": _first_artifact_dir(visual_registry_dir, pattern="*.json"),
        "container_workspace": _first_artifact_file(
            readiness_artifacts.get("container_workspace"),
            analysis / "container_workspace" / "container_workspace_index.json",
        ),
        "workspace_assignment": _first_artifact_file(
            readiness_artifacts.get("workspace_assignment"),
            analysis / "workspace_assignment" / "workspace_assignment_index.json",
        ),
        "office_textbox_fit": _first_artifact_file(analysis / "office_textbox_fit.json"),
        "editable_pptx": _first_artifact_file(exported_pptx),
        "render_compare": _first_artifact_file(
            readiness_artifacts.get("render_compare"),
            _first_matching_file(analysis, "page_*_render_compare.json"),
        ),
        "qa_registry": _first_artifact_file(
            readiness_artifacts.get("page_quality_report"),
            analysis / "page_quality_report.json",
        ),
    }


def _stage02_production_reports(artifacts: dict[str, str | None]) -> dict[str, dict[str, Any]]:
    reports: dict[str, dict[str, Any]] = {}
    for name, artifact in artifacts.items():
        if not artifact or not artifact.endswith(".json"):
            continue
        try:
            reports[name] = _read_json(Path(artifact))
        except (OSError, json.JSONDecodeError, ValueError):
            continue
    return reports


def _expected_pptx(path: Path | None) -> str | None:
    return str(path) if path is not None and path.is_file() else None


def _image_ppt_artifacts(
    output_dir: Path,
    name: str,
    *,
    expected_pptx: Path | None = None,
) -> dict[str, str | None]:
    project_dir = output_dir / f"{name}_template_image_project"
    return {
        "template_image_manifest": str(output_dir / "template_image_manifest.json"),
        "template_image_prompts": str(output_dir / "template_image_prompts.md"),
        "template_image_project": str(project_dir),
        "exported_pptx": _expected_pptx(expected_pptx),
    }


def _run_image_ppt_build(
    *,
    script: Path,
    pages_raw: str,
    output_dir: Path,
    name: str,
    page_image_manifest: Path,
) -> dict[str, Any]:
    expected_pptx = output_dir / "exports" / f"{name}.pptx"
    command = [
        sys.executable,
        "-m",
        "cyberppt",
        "image-ppt",
        "run",
        "--script",
        str(script),
        "--pages",
        pages_raw,
        "--output-dir",
        str(output_dir),
        "--name",
        name,
        "--page-image-manifest",
        str(page_image_manifest),
        "--pptx-output",
        str(expected_pptx),
    ]
    # The project flow may be invoked after another stage has changed the
    # process working directory.  Keep the child CLI anchored at the repository
    # root so ``python -m cyberppt`` resolves the local package consistently.
    repository_root = Path(__file__).resolve().parents[2]
    completed = subprocess.run(command, check=False, cwd=repository_root)
    status = "completed" if completed.returncode == 0 else "failed"
    artifacts = _image_ppt_artifacts(output_dir, name, expected_pptx=expected_pptx)
    result = {
        "command": command,
        "returncode": completed.returncode,
        "status": status,
        "artifacts": artifacts,
    }
    if completed.returncode != 0:
        raise RuntimeError(
            f"image-ppt production build failed with exit code {completed.returncode}.\n"
            f"command: {' '.join(command)}"
        )
    return result


def _generate_manifest_images(
    manifest: dict[str, Any],
    *,
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
                skipped.append(str(output_path))
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
            if not dry_run:
                item["status"] = "Generated"
                item["generated_at"] = _utc_now()
                if accepted_audit is not None:
                    item["text_audit"] = accepted_audit
            generated.append(str(output_path))
    return {
        "backend": "codex_oauth_image",
        "production_mode": production_mode,
        "generated": generated,
        "skipped": skipped,
        "dry_run": dry_run,
        "text_audit_skipped": skip_text_audit,
        "full_reference_images": [str(path) for path in (full_reference_images or [])],
        "text_audits": text_audits,
        "imagegen_attempts": imagegen_attempts,
    }


def _run_editable_rebuild(
    *,
    project: Path,
    manifest_path: Path,
    semantic_plan_dir: Path | None,
    rebuild_args: list[str] | None,
) -> dict[str, Any]:
    command = [sys.executable, "-m", "cyberppt", "template-rebuild", str(manifest_path)]
    if semantic_plan_dir is not None:
        command.extend(["--semantic-plan-dir", str(semantic_plan_dir)])
    command.extend(rebuild_args or [])
    completed = subprocess.run(command, check=False)
    result = {
        "command": command,
        "returncode": completed.returncode,
        "status": "completed" if completed.returncode == 0 else "failed",
        "artifacts": _template_rebuild_artifacts(project),
    }
    if completed.returncode != 0:
        raise RuntimeError(_template_rebuild_failure_message(project, completed.returncode))
    return result


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
    project = project.expanduser().resolve()
    script = script.expanduser().resolve()
    style_lock = style_lock.expanduser().resolve() if style_lock else None
    semantic_plan_dir = semantic_plan_dir.expanduser().resolve() if semantic_plan_dir else None
    if not script.is_file():
        raise FileNotFoundError(f"final script not found: {script}")
    autonomous_contract_path = (
        autonomous_contract.expanduser().resolve()
        if autonomous_contract is not None
        else None
    )
    autonomous_authority = None
    if autonomous_contract_path is not None:
        from cyberppt.autonomous_contract import load_contract, validate_source_boundary

        if external_script:
            raise ValueError("autonomous contract cannot be combined with --external-script")
        if not lightweight_stage01_confirmed:
            raise ValueError(
                "autonomous contract requires lightweight Stage 01 confirmation"
            )
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
    if external_script and lightweight_stage01_confirmed:
        raise ValueError("--external-script cannot be combined with --lightweight-stage01-confirmed")
    source_mode = (
        "autonomous_contract"
        if autonomous_authority is not None
        else "external_script"
        if external_script
        else "interactive_lightweight_confirmation"
        if lightweight_stage01_confirmed
        else "stage01_approved_script"
    )
    project_created = False
    if external_script and not project.exists():
        init_project(project)
        project_created = True
    if not external_script:
        from cyberppt.stage01_controls import assert_escalation_resolved, assert_stage01_script_approval
        from cyberppt.commands.visual_structure_stage import assert_visual_structure_ready

        if lightweight_stage01_confirmed:
            from cyberppt.commands.script_audit import run_script_audit
            from cyberppt.stage02_handoff import load_stage02_handoff

            code, audit = run_script_audit(project, script, lightweight=True)
            if code != 0 or audit.get("status") != "passed":
                raise ValueError(
                    "lightweight Stage 01 confirmation requires a currently passed "
                    "full-script audit before final-script-pages"
                )
            handoff = load_stage02_handoff(project, required=True)
            if handoff.get("stage01_confirmation_mode") != "interactive_lightweight_confirmation":
                raise ValueError(
                    "Stage 02 handoff is not bound to interactive lightweight Stage 01 confirmation"
                )
        else:
            assert_escalation_resolved(project, "script")
            assert_stage01_script_approval(project, script)
        assert_visual_structure_ready(project, script)
    if production_mode not in PRODUCTION_MODES:
        raise ValueError(
            f"unsupported production mode: {production_mode}; "
            f"expected one of {', '.join(PRODUCTION_MODES)}"
        )
    if run_rebuild and production_mode == FULL_IMAGE_MODE:
        raise ValueError("--run-rebuild requires an editable-overlay production mode")
    if semantic_plan_dir is not None and production_mode == FULL_IMAGE_MODE:
        raise ValueError("--semantic-plan-dir requires an editable-overlay production mode")
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

    manifest, manifest_path, compiled_script, page_numbers = build_manifest(
        script=script,
        pages_raw=pages_raw,
        output_dir=target_dir,
        project_path=project,
        style_lock=style_lock,
        require_approved_prompts=(
            not external_script
            and not blueprint_only
            and autonomous_authority is None
        ),
        production_mode=production_mode,
        prompt_enrich=prompt_enrich,
        require_send_approval=require_send_approval,
        enforce_prompt_freshness=False,
        compact_blueprint=not external_script,
    )
    manifest["source_mode"] = source_mode
    manifest["source_script"] = str(script)
    manifest["source_script_sha256"] = _sha256(script)
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
    )
    image_generation = None
    if generate_images:
        image_generation = _generate_manifest_images(
            manifest,
            full_reference_images=full_reference_images,
            model=image_model,
            quality=image_quality,
            timeout=image_timeout,
            force=force_images,
            dry_run=dry_run_images,
            skip_text_audit=skip_image_text_audit,
        )
        _write_json(manifest_path, manifest)
    if require_images or (
        production_mode != FULL_IMAGE_MODE
        and (production_build or run_rebuild)
        and not dry_run_images
    ):
        require_generated(manifest)

    resume_command = (
        f"python -m cyberppt run-autonomous {autonomous_contract_path} --resume"
        if autonomous_contract_path is not None
        else (
            f"python -m cyberppt final-script-pages {project} --script {script} "
            f"--pages {pages_raw} --style-lock {style_lock} --production-mode {production_mode} "
            f"--output-dir {target_dir} --build-id {build_id}"
            + (" --external-script" if external_script else "")
            + (" --lightweight-stage01-confirmed" if lightweight_stage01_confirmed else "")
        )
    )
    production_readiness = None
    tool_consumption: dict[str, Any] = {}
    stage_name = "02-production-build" if production_build else "02-blueprint-dual-image"
    if blueprint_only:
        status = "blueprint_created"
    elif generate_images and not dry_run_images:
        status = "image_assets_generated"
    else:
        status = "ready_for_image_generation" if not require_images else "image_assets_verified"
    image_ppt_build: dict[str, Any] | None = None
    rebuild_status: dict[str, Any] | None = None
    image_ppt_output_dir = target_dir / "image_ppt"
    # The exporter appends ``_template_image_project`` plus a timestamped file
    # name.  Use a stable compact build name so Windows paths remain below the
    # legacy MAX_PATH limit even for deeply nested projects.
    image_ppt_name = f"deck_{sha256(slug.encode('utf-8')).hexdigest()[:10]}"
    if production_build and production_mode == FULL_IMAGE_MODE:
        image_ppt_build = _run_image_ppt_build(
            script=script,
            pages_raw=pages_raw,
            output_dir=image_ppt_output_dir,
            name=image_ppt_name,
            page_image_manifest=manifest_path,
        )
        status = "production_ready"
    elif production_build or run_rebuild:
        rebuild_status = _run_editable_rebuild(
            project=project,
            manifest_path=manifest_path,
            semantic_plan_dir=semantic_plan_dir,
            rebuild_args=rebuild_args,
        )
        production_readiness = build_production_readiness(
            stage=stage_name,
            artifacts=_stage02_production_artifacts(project),
            reports=_stage02_production_reports(_stage02_production_artifacts(project)),
        )
        tool_consumption = production_readiness["tool_consumption"]
        status = production_readiness["status"]
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
        "artifacts": {
            "compiled_deliverable_prompt": str(compiled_script),
            "page_image_pairs": str(manifest_path),
            "template_text_lock": str(lock_path),
            "visual_style_lock": str(style_lock),
            "output_dir": str(target_dir),
            "image_ppt_output_dir": str(image_ppt_output_dir),
            "template_image_manifest": (
                image_ppt_build["artifacts"]["template_image_manifest"] if image_ppt_build else None
            ),
            "template_image_project": (
                image_ppt_build["artifacts"]["template_image_project"] if image_ppt_build else None
            ),
            "exported_pptx": image_ppt_build["artifacts"]["exported_pptx"] if image_ppt_build else None,
            "semantic_plan_dir": str(semantic_plan_dir) if semantic_plan_dir else None,
        },
        "next_steps": [
            (
                "Generate the full image and assemble it through image-ppt."
                if production_mode == FULL_IMAGE_MODE
                else "Generate full/background assets, then rebuild editable text through OCR and semantic overlay."
            ),
            (
                "Optionally generate text_reference as an OCR-only third image."
                if production_mode == TRIPLE_IMAGE_MODE
                else "Use the selected production branch without mixing its artifacts with another branch."
            ),
        ],
        "resume_command": resume_command,
        "rebuild": rebuild_status,
        "image_ppt_build": image_ppt_build,
        "image_generation": image_generation,
        "prompt_enrich": manifest.get("prompt_enrich"),
        "tool_consumption": tool_consumption,
        "production_readiness": production_readiness,
    }
    build_context_path = target_dir / "build_context.json"
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
    if image_ppt_build:
        build_context["artifacts"]["exported_pptx"] = {
            "path": image_ppt_build["artifacts"].get("exported_pptx"),
            "sha256": (
                _sha256(Path(image_ppt_build["artifacts"]["exported_pptx"]))
                if image_ppt_build["artifacts"].get("exported_pptx")
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
    exported_pptx = image_ppt_build["artifacts"].get("exported_pptx") if image_ppt_build else None
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
