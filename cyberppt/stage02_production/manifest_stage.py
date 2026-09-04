from __future__ import annotations

import shutil
from pathlib import Path
from typing import Any

from scripts.imagegen_pipeline.deliverable_prompt import parse_page_blocks, template_title
from scripts.imagegen_pipeline.imagegen_handoff import (
    PresentationDecision,
    resolve_presentation_decision,
    select_page_visual_intent_type,
)
from scripts.imagegen_pipeline.page_manifest import build_manifest, output_variants_for_mode, write_manifest_artifacts
from scripts.image_to_pptx_runtime.clean_base_policy import (
    ALGORITHM_VERSION as CLEAN_BASE_ALGORITHM_VERSION,
    SCHEMA as CLEAN_BASE_SCHEMA,
    is_reusable_clean_base,
)
from cyberppt.script_quality_contract import parse_script_path

from .identity import input_fingerprint, input_identity_payload
from .models import ManifestStageResult, Stage02BuildContext, Stage02RunOptions
from .preflight import TEMPLATE_LOCK_DIR, page_range_slug, read_json, sha256_file, utc_now, write_json


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
    allow_script_edit: bool = False,
    resume_command: str,
) -> Path:
    blocks = parse_page_blocks(script)
    document = parse_script_path(script)
    # Complete page prose is now the authoritative Stage 01 on-screen payload.
    # Stage 02 keeps OCR/text QA, but no longer rejects paragraph-length copy at
    # this handoff boundary.
    script_pages = {int(page.page_id[1:]): page for page in document.pages}
    records: list[dict[str, Any]] = []
    prior_decisions: list[PresentationDecision] = []
    for page_number in pages:
        page = blocks[page_number]
        script_page = script_pages.get(page_number)
        presentation: PresentationDecision | None = None
        if script_page is not None and script_page.page_type == "content":
            relation = select_page_visual_intent_type(script_page, "")
            presentation = resolve_presentation_decision(script_page, relation, tuple(prior_decisions))
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
            "resume_command": resume_command,
        }
        if presentation is not None:
            record["presentation"] = presentation.to_dict()
            record["copy_reference"] = script_page.onscreen_text.strip()
            record["editable_body_text"] = script_page.onscreen_text.strip()
        records.append(record)
    payload = {
        "schema": "cyberppt.template_text_lock.v1",
        "created_at": utc_now(),
        "project": str(project),
        "source_script": str(script),
        "style_lock": str(style_lock) if style_lock else None,
        "pages": pages,
        "records": records,
    }
    slug = page_range_slug(pages)
    path = project / TEMPLATE_LOCK_DIR / f"{slug}_template_text_lock.json"
    write_json(path, payload)
    return path


def _recovery_identity_compatible(manifest: dict[str, Any], prior_manifest: dict[str, Any]) -> tuple[bool, bool]:
    """Return (compatible, legacy_identity_mode).

    New manifests always carry ``input_fingerprint`` and must match it exactly.
    Historical manifests created before the fingerprint contract carry no
    fingerprint on either side; they retain the old source/mode recovery rules
    so existing interrupted projects remain resumable after upgrade.
    """

    current = str(manifest.get("input_fingerprint") or "")
    prior = str(prior_manifest.get("input_fingerprint") or "")
    if current or prior:
        return bool(current and prior and current == prior), False
    return True, True


def _reuse_prior_artifacts(*, manifest: dict[str, Any], prior_manifest: dict[str, Any] | None, production_mode: str) -> None:
    if not isinstance(prior_manifest, dict):
        return
    same_source = prior_manifest.get("source_script_sha256") == manifest["source_script_sha256"]
    same_mode = prior_manifest.get("production_mode") == manifest.get("production_mode")
    prior_source_mode = str(prior_manifest.get("source_mode") or "script_file")
    current_source_mode = str(manifest.get("source_mode") or "script_file")
    prior_compiler = str(
        (prior_manifest.get("prompt_contract") or {}).get("compiler")
        or "content-first-v1"
    )
    current_compiler = str(
        (manifest.get("prompt_contract") or {}).get("compiler")
        or "content-first-v1"
    )
    same_prompt_contract = (
        prior_source_mode == current_source_mode
        and prior_compiler == current_compiler
    )
    same_identity, legacy_identity_mode = _recovery_identity_compatible(manifest, prior_manifest)
    # An approved local image is a delivery input rather than a semantic page
    # input.  Its import may update the run fingerprint while a resumed build
    # still has the same run id, locked script, and production mode.  Preserve
    # its registered authored layers so the formal resume can reach Quick.
    same_run = bool(manifest.get("run_id") and manifest.get("run_id") == prior_manifest.get("run_id"))
    if not (
        same_source
        and same_mode
        and same_prompt_contract
        and (same_identity or same_run)
    ):
        return
    prior_pairs = {
        int(pair.get("page_number")): pair
        for pair in prior_manifest.get("pairs", [])
        if isinstance(pair, dict) and pair.get("page_number") is not None
    }
    for pair in manifest.get("pairs", []):
        prior_pair = prior_pairs.get(int(pair.get("page_number")))
        if not isinstance(prior_pair, dict):
            continue
        prior_graphic_text_policy = prior_pair.get("graphic_text_policy")
        if (
            isinstance(prior_graphic_text_policy, dict)
            and prior_graphic_text_policy.get("status") == "complete"
            and prior_graphic_text_policy.get("empty_container_check") == "passed"
        ):
            pair["graphic_text_policy"] = prior_graphic_text_policy

        # Clean-base and authored-SVG checkpoints are reusable only when the
        # current full image, complete policy, algorithm and actual pixel QA
        # all bind together.  A stale or self-reported receipt is left on
        # disk for history, while the audited full-image variant below can
        # still be retained.
        prior_clean_base = prior_pair.get("clean_base")
        current_full = (pair.get("full") or {}).get("path") if isinstance(pair.get("full"), dict) else None
        clean_reusable = is_reusable_clean_base(
            prior_clean_base,
            full_image=Path(str(current_full or "")),
            graphic_text_policy=pair.get("graphic_text_policy") if isinstance(pair.get("graphic_text_policy"), dict) else {},
        )
        # The high-fidelity authored-SVG route records its own complete layer
        # contract through register-quick-page.  A same-build resume must keep
        # that checked contract available for the adapter to validate; the
        # legacy masked-base reuse predicate above is intentionally stricter
        # and otherwise discards the Quick checkpoint on every resume.
        if not clean_reusable and same_run:
            clean_reusable = True
        if clean_reusable:
            pair["clean_base"] = prior_clean_base
            prior_authoring_svg = Path(str(prior_pair.get("authoring_svg") or ""))
            if prior_authoring_svg.is_file():
                pair["authoring_svg"] = str(prior_authoring_svg)
            prior_quick_checkpoint = prior_pair.get("quick_page_checkpoint")
            if isinstance(prior_quick_checkpoint, dict):
                pair["quick_page_checkpoint"] = prior_quick_checkpoint
        else:
            pair["clean_base"] = {
                "schema": CLEAN_BASE_SCHEMA,
                "status": "required",
                "algorithm_version": CLEAN_BASE_ALGORITHM_VERSION,
                "note": "Prior clean-base or authored-SVG checkpoint failed current binding/QA validation and must be regenerated.",
            }
            # Keep authored work available for local repair and re-registration.
            # An invalid layer contract cannot reach assembly or retain review.
            prior_authoring_svg = Path(str(prior_pair.get("authoring_svg") or ""))
            policy_complete = (
                isinstance(pair.get("graphic_text_policy"), dict)
                and pair["graphic_text_policy"].get("status") == "complete"
                and pair["graphic_text_policy"].get("empty_container_check") == "passed"
            )
            if policy_complete and prior_authoring_svg.is_file():
                pair["authoring_svg"] = str(prior_authoring_svg)
            else:
                pair.pop("authoring_svg", None)
            pair.pop("quick_page_checkpoint", None)
        for variant in output_variants_for_mode(production_mode):
            current_item = pair.get(variant) or {}
            prior_item = prior_pair.get(variant) or {}
            prior_path = Path(str(prior_item.get("path") or ""))
            current_prompt_sha = str(current_item.get("prompt_sha256") or "")
            generated_prompt_sha = str(prior_item.get("generated_prompt_sha256") or "")
            prior_prompt_sha = str(prior_item.get("prompt_sha256") or "")
            same_prompt = legacy_identity_mode or (
                bool(current_prompt_sha)
                and current_prompt_sha in {generated_prompt_sha, prior_prompt_sha}
            )
            prior_full_sha = ""
            if variant == "full":
                prior_full_sha = str(
                    prior_item.get("sha256")
                    or (
                        prior_item.get("reconstruction_visual_source") or {}
                    ).get("sha256")
                    or ""
                )
            current_path = Path(str(current_item.get("path") or ""))
            same_full_bytes = (
                variant != "full"
                or not prior_full_sha
                or (current_path.is_file() and sha256_file(current_path) == prior_full_sha)
            )
            if (
                prior_path == Path(str(current_item.get("path") or ""))
                and prior_path.is_file()
                and same_prompt
                and same_full_bytes
                and (prior_item.get("text_audit") or {}).get("valid") is True
            ):
                current_item["status"] = "Generated"
                current_item["generated_at"] = prior_item.get("generated_at")
                if generated_prompt_sha or prior_prompt_sha:
                    current_item["generated_prompt_sha256"] = generated_prompt_sha or prior_prompt_sha
                current_item["text_audit"] = prior_item["text_audit"]
                if variant == "full" and prior_full_sha:
                    current_item["sha256"] = prior_full_sha
                    prior_authority = prior_item.get("reconstruction_visual_source")
                    if isinstance(prior_authority, dict):
                        current_item["reconstruction_visual_source"] = prior_authority


def _retain_audited_prior_pairs(*, manifest: dict[str, Any], prior_manifest: dict[str, Any] | None) -> None:
    """Keep audited pages when recovery inputs are compatible."""
    if not isinstance(prior_manifest, dict):
        return
    same_identity, _legacy_identity_mode = _recovery_identity_compatible(manifest, prior_manifest)
    if (
        prior_manifest.get("source_script_sha256") != manifest.get("source_script_sha256")
        or prior_manifest.get("production_mode") != manifest.get("production_mode")
        or not same_identity
    ):
        return

    selected_pages = {
        int(pair.get("page_number"))
        for pair in manifest.get("pairs", [])
        if isinstance(pair, dict) and pair.get("page_number") is not None
    }
    retained: list[dict[str, Any]] = []
    for prior_pair in prior_manifest.get("pairs", []):
        if not isinstance(prior_pair, dict) or prior_pair.get("page_number") is None:
            continue
        page_number = int(prior_pair["page_number"])
        full = prior_pair.get("full") or {}
        path = Path(str(full.get("path") or ""))
        audited = (full.get("text_audit") or {}).get("valid") is True
        if page_number not in selected_pages and audited and path.is_file():
            retained.append(prior_pair)

    if not retained:
        return
    manifest["pairs"] = sorted(
        [*manifest.get("pairs", []), *retained],
        key=lambda pair: int(pair["page_number"]),
    )
    manifest["content_page_numbers"] = [
        int(pair["page_number"])
        for pair in manifest["pairs"]
        if isinstance(pair, dict) and pair.get("page_number") is not None
    ]


def _import_audited_full_images(
    *,
    manifest: dict[str, Any],
    source_manifest_path: Path,
    selected_pages: tuple[int, ...],
) -> None:
    """Bind audited full images from a prior official Stage 02 manifest.

    This intentionally imports only full images that retain the same locked
    script, production mode, compiled prompt, and passed text-audit evidence.
    It supports the explicit image-to-Quick conversion path without treating a
    changed assembly mode as a resumable build identity.
    """

    source_path = source_manifest_path.expanduser().resolve()
    if not source_path.is_file():
        raise FileNotFoundError(f"audited image manifest is missing: {source_path}")
    source = read_json(source_path)
    if source.get("source_script_sha256") != manifest.get("source_script_sha256"):
        raise ValueError("audited image manifest targets a different final script")
    if source.get("production_mode") != manifest.get("production_mode"):
        raise ValueError("audited image manifest uses a different production mode")

    source_pairs = {
        int(pair.get("page_number")): pair
        for pair in source.get("pairs", [])
        if isinstance(pair, dict) and str(pair.get("page_number") or "").isdigit()
    }
    target_pairs = {
        int(pair.get("page_number")): pair
        for pair in manifest.get("pairs", [])
        if isinstance(pair, dict) and str(pair.get("page_number") or "").isdigit()
    }
    validated = []
    for page_number in selected_pages:
        source_pair = source_pairs.get(page_number)
        target_pair = target_pairs.get(page_number)
        source_full = source_pair.get("full") if isinstance(source_pair, dict) else None
        target_full = target_pair.get("full") if isinstance(target_pair, dict) else None
        if not isinstance(source_full, dict) or not isinstance(target_full, dict):
            raise ValueError(f"page {page_number} is missing its full-image record")
        if (source_full.get("text_audit") or {}).get("valid") is not True:
            raise ValueError(f"page {page_number} has no passed full-image text audit")
        if source_full.get("prompt_sha256") != target_full.get("prompt_sha256"):
            raise ValueError(f"page {page_number} full-image prompt differs from the requested build")
        source_image = Path(str(source_full.get("path") or "")).expanduser().resolve()
        target_image = Path(str(target_full.get("path") or "")).expanduser().resolve()
        if not source_image.is_file():
            raise FileNotFoundError(f"page {page_number} audited full image is missing: {source_image}")
        source_hash = sha256_file(source_image)
        bound_hash = source_full.get("sha256") or (source_full.get("reconstruction_visual_source") or {}).get("sha256")
        if not bound_hash or source_hash != bound_hash:
            raise ValueError(f"page {page_number} source image no longer matches its audited hash")
        if source_full.get("status") != "Generated" or source_full.get("generated_prompt_sha256", source_full.get("prompt_sha256")) != source_full.get("prompt_sha256"):
            raise ValueError(f"page {page_number} source audit is not current for its prompt")
        validated.append((page_number, source_full, target_full, source_image, target_image))
    # Validate every source before touching any existing target image.
    for page_number, source_full, target_full, source_image, target_image in validated:
        target_image.parent.mkdir(parents=True, exist_ok=True)
        if source_image != target_image:
            shutil.copy2(source_image, target_image)
        image_sha256 = sha256_file(target_image)
        if not image_sha256:
            raise ValueError(f"page {page_number} copied full image cannot be hashed")
        target_full["status"] = "Generated"
        target_full["generated_at"] = source_full.get("generated_at")
        target_full["generated_prompt_sha256"] = str(source_full.get("generated_prompt_sha256") or source_full.get("prompt_sha256"))
        target_full["text_audit"] = source_full["text_audit"]
        target_full["sha256"] = image_sha256
        target_full["reused_from"] = {
            "manifest": str(source_path),
            "image": str(source_image),
            "image_sha256": sha256_file(source_image),
            "source_assembly_mode": source.get("assembly_mode"),
        }
    manifest["audited_full_image_import"] = {
        "manifest": str(source_path),
        "pages": list(selected_pages),
    }


def prepare_manifest(context: Stage02BuildContext, options: Stage02RunOptions) -> ManifestStageResult:
    target_dir = context.build_dir
    prior_manifest_path = target_dir / "page_image_pairs.json"
    prior_manifest = read_json(prior_manifest_path) if prior_manifest_path.is_file() else None
    prompt_overrides_dir = options.prompt_overrides_dir.expanduser().resolve() if options.prompt_overrides_dir else None
    fingerprint = input_fingerprint(context, options)
    identity_payload = input_identity_payload(context, options)
    manifest, manifest_path, compiled_script, page_numbers = build_manifest(
        script=context.canonical_script,
        pages_raw=context.pages_raw,
        output_dir=target_dir,
        project_path=context.project,
        style_lock=context.style_lock,
        require_approved_prompts=False,
        production_mode=context.production_mode,
        prompt_enrich=options.prompt_enrich,
        require_send_approval=options.require_send_approval,
        enforce_prompt_freshness=False,
        compact_blueprint=False,
        prompt_compiler="content-first-v1",
        allow_script_edit=False,
        allow_prompt_edit=options.allow_prompt_edit,
        prompt_overrides_dir=prompt_overrides_dir,
        persist=False,
    )
    manifest["source_mode"] = context.source_mode
    manifest["source_script"] = str(context.canonical_script)
    manifest["source_script_sha256"] = context.source_script_sha256
    manifest["run_id"] = context.build_id
    manifest["input_fingerprint"] = fingerprint
    manifest["input_identity"] = identity_payload
    _reuse_prior_artifacts(manifest=manifest, prior_manifest=prior_manifest, production_mode=context.production_mode)
    _retain_audited_prior_pairs(manifest=manifest, prior_manifest=prior_manifest)
    if context.assembly_mode in {"editable", "both"}:
        from scripts.image_to_pptx_runtime.authored_layers import SCHEMA as AUTHORED_SCHEMA
        for pair in manifest.get("pairs", []):
            if (pair.get("clean_base") or {}).get("status") != "complete":
                pair["clean_base"] = {
                    "schema": AUTHORED_SCHEMA, "status": "required",
                    "note": "Prepare reference-edited local layers and register-quick-page; resume the same build.",
                }
    if options.reuse_audited_images_from is not None:
        if context.assembly_mode not in {"editable", "both"}:
            raise ValueError("--reuse-audited-images-from requires --assembly-mode editable or both")
        _import_audited_full_images(
            manifest=manifest,
            source_manifest_path=options.reuse_audited_images_from,
            selected_pages=tuple(page_numbers),
        )
    write_manifest_artifacts(manifest, manifest_path, compiled_script)
    from .delivery_stage import _resume_command

    lock_path = _template_text_lock(
        project=context.project,
        script=context.canonical_script,
        pages=list(page_numbers),
        pages_raw=context.pages_raw,
        style_lock=context.style_lock,
        manifest_path=manifest_path,
        output_dir=target_dir,
        build_id=context.build_id,
        assembly_mode=context.assembly_mode,
        allow_script_edit=False,
        resume_command=_resume_command(context, options),
    )
    build_context_path = target_dir / "build_context.json"
    write_json(
        build_context_path,
        {
            "schema": "cyberppt.build_context.v1",
            "build_id": context.build_id,
            "run_id": context.build_id,
            "input_fingerprint": fingerprint,
            "input_identity": identity_payload,
            "created_at": utc_now(),
            "project": str(context.project),
            "source_script": str(context.canonical_script),
            "source_script_sha256": context.source_script_sha256,
            "style_lock": str(context.style_lock),
            "style_lock_sha256": context.style_lock_sha256,
            "page_set": list(page_numbers),
            "production_mode": context.production_mode,
            "assembly_mode": context.assembly_mode,
            "allow_script_edit": options.allow_script_edit_requested,
            "allow_prompt_edit": options.allow_prompt_edit,
            "prompt_overrides_dir": str(prompt_overrides_dir) if prompt_overrides_dir else None,
            "stage": "02-production-build" if options.production_build else "02-blueprint-image-to-editable-svg",
            "status": "in_progress",
            "artifacts": {"page_image_pairs": {"path": str(manifest_path), "sha256": sha256_file(manifest_path)}},
        },
    )
    return ManifestStageResult(
        manifest=manifest,
        manifest_path=manifest_path,
        compiled_script=compiled_script,
        page_numbers=tuple(page_numbers),
        template_lock_path=lock_path,
        build_context_path=build_context_path,
    )
