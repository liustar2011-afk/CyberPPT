from __future__ import annotations

from pathlib import Path
from typing import Any

from scripts.imagegen_pipeline.deliverable_prompt import parse_page_blocks, template_title
from scripts.imagegen_pipeline.imagegen_handoff import (
    PresentationDecision,
    resolve_presentation_decision,
    select_image_locked_text,
    select_page_visual_intent_type,
)
from scripts.imagegen_pipeline.page_manifest import build_manifest, output_variants_for_mode
from cyberppt.script_quality_contract import assert_imagegen_onscreen_readiness, parse_script_path

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
) -> Path:
    blocks = parse_page_blocks(script)
    document = parse_script_path(script)
    if not allow_script_edit:
        assert_imagegen_onscreen_readiness(document, set(pages))
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
    same_identity, legacy_identity_mode = _recovery_identity_compatible(manifest, prior_manifest)
    if not (same_source and same_mode and same_identity):
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
        prior_authoring_svg = Path(str(prior_pair.get("authoring_svg") or ""))
        prior_graphic_text_policy = prior_pair.get("graphic_text_policy")
        if prior_authoring_svg.is_file():
            pair["authoring_svg"] = str(prior_authoring_svg)
        prior_clean_base = prior_pair.get("clean_base")
        if isinstance(prior_clean_base, dict) and prior_clean_base.get("status") == "complete":
            pair["clean_base"] = prior_clean_base
        if (
            isinstance(prior_graphic_text_policy, dict)
            and prior_graphic_text_policy.get("status") == "complete"
            and prior_graphic_text_policy.get("empty_container_check") == "passed"
        ):
            pair["graphic_text_policy"] = prior_graphic_text_policy
        prior_quick_checkpoint = prior_pair.get("quick_page_checkpoint")
        if isinstance(prior_quick_checkpoint, dict):
            pair["quick_page_checkpoint"] = prior_quick_checkpoint
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
            if (
                prior_path == Path(str(current_item.get("path") or ""))
                and prior_path.is_file()
                and same_prompt
                and (prior_item.get("text_audit") or {}).get("valid") is True
            ):
                current_item["status"] = "Generated"
                current_item["generated_at"] = prior_item.get("generated_at")
                if generated_prompt_sha or prior_prompt_sha:
                    current_item["generated_prompt_sha256"] = generated_prompt_sha or prior_prompt_sha
                current_item["text_audit"] = prior_item["text_audit"]


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
        prompt_compiler="artifact-spec-v2",
        allow_script_edit=False,
        allow_prompt_edit=options.allow_prompt_edit,
        prompt_overrides_dir=prompt_overrides_dir,
    )
    manifest["source_mode"] = context.source_mode
    manifest["source_script"] = str(context.canonical_script)
    manifest["source_script_sha256"] = context.source_script_sha256
    manifest["run_id"] = context.build_id
    manifest["input_fingerprint"] = fingerprint
    manifest["input_identity"] = identity_payload
    _reuse_prior_artifacts(manifest=manifest, prior_manifest=prior_manifest, production_mode=context.production_mode)
    _retain_audited_prior_pairs(manifest=manifest, prior_manifest=prior_manifest)
    write_json(manifest_path, manifest)
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
