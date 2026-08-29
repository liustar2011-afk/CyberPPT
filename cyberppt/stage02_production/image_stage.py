from __future__ import annotations

import http.client
import json
import re
import shutil
from hashlib import sha256
from pathlib import Path
from typing import Any

from PIL import Image

from scripts.imagegen_pipeline.page_manifest import FULL_IMAGE_MODE, output_variants_for_mode
from scripts.imagegen_pipeline.providers.codex_oauth_image import ensure_output_size, run_codex_image

from .models import ImageStageResult, ManifestStageResult, Stage02BuildContext, Stage02RunOptions
from .preflight import utc_now, write_json


def _image_size(path: Path) -> list[int] | None:
    try:
        with Image.open(path) as image:
            return list(image.size)
    except OSError:
        return None


def _attach_content_root_qa(
    *,
    pair: dict[str, Any],
    audit: dict[str, Any],
) -> None:
    """Attach diagnostic root coverage when artifact-spec binding metadata exists."""

    full = pair.get("full") if isinstance(pair.get("full"), dict) else {}
    debug_receipt = full.get("debug_receipt") if isinstance(full, dict) else None
    if not isinstance(debug_receipt, dict):
        return
    from scripts.imagegen_pipeline.content_root_qa import build_content_root_qa

    audit["content_root_qa"] = build_content_root_qa(
        page_number=int(pair.get("page_number") or 0),
        debug_receipt=debug_receipt,
        text_audit=audit,
    )


def normalize_audited_manifest_images(manifest: dict[str, Any]) -> None:
    from scripts.imagegen_pipeline.providers.codex_oauth_image import raw_output_path

    for pair in manifest.get("pairs", []):
        if not isinstance(pair, dict):
            continue
        full = pair.get("full") if isinstance(pair.get("full"), dict) else None
        audit = full.get("text_audit") if isinstance(full, dict) and isinstance(full.get("text_audit"), dict) else None
        path = Path(str(full.get("path") or "")) if isinstance(full, dict) else Path()
        if audit is None or audit.get("valid") is not True or not path.is_file():
            continue
        if "content_root_qa" not in audit:
            _attach_content_root_qa(pair=pair, audit=audit)
        if not audit.get("image_size"):
            raw_path = raw_output_path(path)
            source_size = _image_size(raw_path if raw_path.is_file() else path)
            if source_size is not None:
                audit["image_size"] = source_size
        canvas = str(full.get("canvas") or "2048x1024")
        match = re.fullmatch(r"\s*(\d+)x(\d+)\s*", canvas)
        expected_size = [int(match.group(1)), int(match.group(2))] if match else None
        if expected_size is None or _image_size(path) != expected_size:
            ensure_output_size(path, canvas)
        normalized_size = _image_size(path)
        if normalized_size is not None:
            audit["normalized_image_size"] = normalized_size


def bind_reconstruction_visual_sources(manifest: dict[str, Any]) -> list[dict[str, Any]]:
    """Hash-bind text-audited full images as editable reconstruction sources."""

    bound: list[dict[str, Any]] = []
    for pair in manifest.get("pairs", []):
        if not isinstance(pair, dict):
            continue
        full = pair.get("full") if isinstance(pair.get("full"), dict) else None
        if full is None:
            continue
        audit = full.get("text_audit") if isinstance(full.get("text_audit"), dict) else None
        full_path = Path(str(full.get("path") or ""))
        if audit is None or audit.get("valid") is not True or not full_path.is_file():
            continue
        binding = {
            "authority": "audited_full_image",
            "path": str(full_path),
            "sha256": sha256(full_path.read_bytes()).hexdigest(),
            "immutable_visual_composition": True,
        }
        full["reconstruction_visual_source"] = binding
        bound.append({"page_number": pair.get("page_number"), **binding})
    manifest["visual_truth_policy"] = {
        "authority": "audited_full_image",
        "scope": "editable_reconstruction",
        "rule": "downstream reconstruction may decompose or rebuild text but must preserve the accepted visual composition",
        "bound_pages": [item.get("page_number") for item in bound],
    }
    return bound


def _failed_text_audit_image_path(output_path: Path, attempt: int) -> Path:
    return output_path.with_name(f"{output_path.stem}.attempt-{attempt:02d}-text-audit-failed{output_path.suffix}")


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
    prompt_dir = output_path.parent / "prompts" / "attempts"
    prompt_dir.mkdir(parents=True, exist_ok=True)
    stem = f"page-{int(page_number):03d}-{variant}-attempt-{attempt:02d}"
    prompt_path = prompt_dir / f"{stem}-sent.txt"
    record_path = prompt_dir / f"{stem}-request.json"
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
        "failed_image": correction_audit.get("image") if correction_audit is not None else None,
        "correction_issues": correction_audit.get("issues", []) if correction_audit is not None else [],
    }
    record_path.write_text(json.dumps(record, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
    record["request_record_path"] = str(record_path.resolve())
    return record


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
            text_truth = pair.get("image_text_truth") if variant == "full" and not skip_text_audit else None
            has_text_receipt = (item.get("text_audit") or {}).get("valid") is True
            prompt_matches_existing_image = item.get("generated_prompt_sha256") == item.get("prompt_sha256") and bool(item.get("generated_prompt_sha256"))
            reusable_audited_full = variant == "full" and has_text_receipt
            if output_path.is_file() and not force and (prompt_matches_existing_image or reusable_audited_full) and (not isinstance(text_truth, dict) or has_text_receipt):
                if reusable_audited_full and not prompt_matches_existing_image:
                    item["prompt_reuse_warning"] = "passed_text_audit_reused_despite_prompt_hash_change"
                audit = item.get("text_audit") if isinstance(item.get("text_audit"), dict) else None
                if audit is not None:
                    if "content_root_qa" not in audit:
                        _attach_content_root_qa(pair=pair, audit=audit)
                    if not audit.get("image_size"):
                        from scripts.imagegen_pipeline.providers.codex_oauth_image import raw_output_path
                        raw_path = raw_output_path(output_path)
                        audit_source = raw_path if raw_path.is_file() else output_path
                        source_size = _image_size(audit_source)
                        if source_size is not None:
                            audit["image_size"] = source_size
                ensure_output_size(output_path, str(item.get("canvas") or "2048x1024"))
                if audit is not None:
                    normalized_size = _image_size(output_path)
                    if normalized_size is not None:
                        audit["normalized_image_size"] = normalized_size
                item["status"] = "Generated"
                item.pop("last_error", None)
                skipped.append(str(output_path))
                if checkpoint_path is not None:
                    write_json(checkpoint_path, manifest)
                continue
            input_images = list(page_reference_images or full_reference_images or []) if variant == "full" else [full_path]
            if variant != "full" and not full_path.is_file() and not dry_run:
                raise FileNotFoundError(f"page {pair.get('page_number')} {variant} requires full image: {full_path}")
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
                        _attach_content_root_qa(pair=pair, audit=audit)
                        text_audits.append(audit)
                        if not audit["valid"]:
                            if attempt < max_attempts:
                                if not output_path.is_file():
                                    raise FileNotFoundError(f"page {pair.get('page_number')} failed text audit image not found for correction retry: {output_path}")
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
                                f"page {pair.get('page_number')} image text audit failed after {max_attempts} generation attempts; regenerate before enhancement: "
                                f"{json.dumps(audit.get('issues', []), ensure_ascii=False)}"
                            )
                        accepted_audit = audit
                    ensure_output_size(output_path, canvas)
                    if accepted_audit is not None:
                        normalized_size = _image_size(output_path)
                        if normalized_size is not None:
                            accepted_audit["normalized_image_size"] = normalized_size
                    break
            except (OSError, TimeoutError, http.client.HTTPException, RuntimeError) as exc:
                item["status"] = "Failed"
                item["last_error"] = f"{type(exc).__name__}: {exc}"
                failed.append({
                    "page_number": pair.get("page_number"),
                    "variant": variant,
                    "path": str(output_path),
                    "error": item["last_error"],
                })
                if checkpoint_path is not None:
                    write_json(checkpoint_path, manifest)
                continue
            if not dry_run:
                item["status"] = "Generated"
                item["generated_at"] = utc_now()
                item["generated_prompt_sha256"] = item.get("prompt_sha256")
                item.pop("last_error", None)
                if accepted_audit is not None:
                    item["text_audit"] = accepted_audit
            generated.append(str(output_path))
            if checkpoint_path is not None:
                write_json(checkpoint_path, manifest)
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


def run_image_stage(
    context: Stage02BuildContext,
    manifest_result: ManifestStageResult,
    options: Stage02RunOptions,
) -> ImageStageResult:
    manifest = manifest_result.manifest
    generation = None
    if options.generate_images:
        generation = _generate_manifest_images(
            manifest,
            checkpoint_path=manifest_result.manifest_path,
            full_reference_images=list(context.full_reference_images),
            model=options.image_model,
            quality=options.image_quality,
            timeout=options.image_timeout,
            force=options.force_images,
            dry_run=options.dry_run_images,
            skip_text_audit=options.skip_image_text_audit,
        )
        write_json(manifest_result.manifest_path, manifest)
        failed_pages = generation.get("failed") or []
        if failed_pages:
            summary = "; ".join(
                f"page {item.get('page_number')} {item.get('variant')}: {item.get('error')}"
                for item in failed_pages
            )
            raise RuntimeError(
                f"{len(failed_pages)} of {len(failed_pages) + len(generation.get('generated') or [])} image generation attempts failed (likely transient backend/network faults); "
                f"already-generated pages were kept, re-run the same command to retry only the failed ones: {summary}"
            )
    return ImageStageResult(manifest=manifest, generation=generation)
