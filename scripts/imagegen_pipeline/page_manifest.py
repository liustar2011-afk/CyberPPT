#!/usr/bin/env python3
"""Build CyberPPT full-image manifests for editable-SVG reconstruction.

This creates the audited full-image input consumed by the Stage 02
image-to-editable-SVG reconstruction route.

It intentionally does not import any legacy image-pair batch generator or
external style preset system.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Sequence

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from scripts.imagegen_pipeline.deliverable_prompt import (
    parse_page_blocks,
    parse_pages,
    render_prompt,
    style_contract,
)
from scripts.imagegen_pipeline.providers.codex_oauth_image import ensure_output_size
from scripts.imagegen_pipeline.style_library import write_project_style_lock
from scripts.imagegen_pipeline.prompt_approval import (
    assert_prompt_fresh,
    build_prompt_approval,
    prompt_sha256,
)
from scripts.imagegen_pipeline.build_transaction import (
    atomic_copy,
    atomic_write_json,
    atomic_write_text,
    build_lock,
)
from cyberppt.commands.script_gate import assert_approved_final_script
from cyberppt.page_artifact_spec import PageArtifactSpec, load_project_page_artifact_specs
from scripts.imagegen_pipeline.artifact_prompt import build_final_prompt_ir
from scripts.imagegen_pipeline.final_prompt_contract import validate_final_prompt
from scripts.imagegen_pipeline.final_prompt_ir import FINAL_PROMPT_IR_VERSION
from scripts.imagegen_pipeline.final_prompt_renderer import render_debug_receipt
from scripts.imagegen_pipeline.prompt_compiler import (
    ARTIFACT_PROMPT_COMPILER,
    DEFAULT_PROMPT_COMPILER,
    validate_prompt_compiler,
)


# Stage 02 images are body-only assets.  Their native contract is 2:1; the
# 16:9 slide canvas and chrome are supplied later by the PPT template.
CANVAS = {"width": 2048, "height": 1024}
CONTENT_REGION = {"x": 0, "y": 0, "width": 2048, "height": 1024}
# API-valid 16-multiple canvas used for ImageGen request + full-image ingest resize.
GENERATION_SIZE = {"width": 2048, "height": 1024}
GENERATION_SIZE_TEXT = f"{GENERATION_SIZE['width']}x{GENERATION_SIZE['height']}"
FULL_IMAGE_MODE = "image-to-editable-svg"
PRODUCTION_MODES = (FULL_IMAGE_MODE,)
FULL_GENERATION_METHOD = "text_to_image_generate_full"
BLUEPRINT_PATTERNS = (
    "slide-{page:03d}-blueprint.png",
    "slide-{page:02d}-blueprint.png",
    "slide-{page}-blueprint.png",
    "page_{page:03d}_blueprint.png",
    "page-{page:03d}-blueprint.png",
)


def _slug(text: str, fallback: str = "page") -> str:
    normalized = re.sub(r"[^0-9A-Za-z\u4e00-\u9fff]+", "_", text).strip("_")
    return (normalized or fallback)[:36]


def _page_stem(page_number: int, title: str) -> str:
    return f"page_{page_number:03d}_{_slug(title)}"


def _sha256_text(value: str) -> str:
    return prompt_sha256(value)


def _is_style09_lock(style_lock: Path | None) -> bool:
    if style_lock is None:
        return False
    try:
        payload = json.loads(style_lock.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return False
    style = payload.get("style") if isinstance(payload, dict) else None
    return isinstance(style, dict) and int(style.get("id") or 0) == 9


def _compiled_script_path(output_dir: Path, source: Path, pages: list[int]) -> Path:
    first = pages[0]
    last = pages[-1]
    return output_dir / f"{source.stem}_cyberppt_deliverable_p{first}_p{last}.md"


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _load_reference_map(project_path: Path | None) -> dict[int, list[dict[str, Any]]]:
    """Load optional per-page ImageGen reference images.

    References are project-owned, hash-bound assets.  They guide composition
    and material only; the approved page prompt remains the content source of
    truth.  Keeping the map in the manifest makes every attachment auditable.
    """

    if project_path is None:
        return {}
    map_path = project_path / "workbench" / "locks" / "imagegen_reference_map.json"
    if not map_path.is_file():
        return {}
    payload = json.loads(map_path.read_text(encoding="utf-8"))
    raw_pages = payload.get("pages") if isinstance(payload, dict) else None
    if not isinstance(raw_pages, dict):
        raise ValueError(f"ImageGen reference map pages must be an object: {map_path}")
    result: dict[int, list[dict[str, Any]]] = {}
    for raw_page, raw_items in raw_pages.items():
        try:
            page_number = int(raw_page)
        except (TypeError, ValueError) as exc:
            raise ValueError(f"invalid ImageGen reference page {raw_page!r}: {map_path}") from exc
        if not isinstance(raw_items, list):
            raise ValueError(f"reference map page {page_number} must be a list: {map_path}")
        items: list[dict[str, Any]] = []
        for raw_item in raw_items:
            if not isinstance(raw_item, dict) or not raw_item.get("path"):
                raise ValueError(f"reference map page {page_number} has an invalid item: {map_path}")
            path = Path(str(raw_item["path"])).expanduser()
            if not path.is_absolute():
                path = (project_path / path).resolve()
            else:
                path = path.resolve()
            if not path.is_file():
                raise FileNotFoundError(f"ImageGen reference image not found: {path}")
            expected = str(raw_item.get("sha256") or "").lower()
            actual = _sha256_file(path)
            if expected and expected != actual:
                raise ValueError(
                    f"ImageGen reference hash mismatch: {path}; expected {expected}, got {actual}"
                )
            items.append(
                {
                    "path": str(path),
                    "role": str(raw_item.get("role") or "style_and_composition_reference"),
                    "sha256": actual,
                }
            )
        result[page_number] = items
    return result


def output_variants_for_mode(production_mode: str) -> list[str]:
    if production_mode != FULL_IMAGE_MODE:
        raise ValueError("unsupported production mode; expected image-to-editable-svg")
    return ["full"]


def _mark_status(item: dict[str, Any], *, force_pending: bool = False) -> None:
    path = Path(item["path"])
    if path.is_file() and path.stat().st_size > 0 and not force_pending:
        item["status"] = "Generated"
        item["generated_at"] = datetime.fromtimestamp(path.stat().st_mtime, timezone.utc).isoformat()
        item.pop("last_error", None)
    else:
        item["status"] = "Pending"
        item.pop("generated_at", None)
        if not path.is_file():
            item["last_error"] = f"Missing expected CyberPPT image file: {path}"


def _compact_blueprint_prompt(
    *,
    page_number: int,
    handoff_page: dict[str, Any],
    visual_prompt: str,
    style_lock: Path | None,
) -> str:
    parts = [
            f"【页面编码】P{page_number:02d}",
            "【正文画布合同】\n2048×1024（2:1）正文内容区。不得绘制标题、副标题、Logo、页码、页脚或模板外框。",
            "【严格上屏文字】\n" + str(handoff_page.get("onscreen_text") or "").strip(),
            visual_prompt.strip(),
            "【生成约束】\n只渲染“严格上屏文字”中的文字；字段名、指令、证据编号和调试信息均不得上屏。",
            "【正式风格锁｜不上屏】\n" + style_contract(style_lock).strip(),
        ]
    return "\n\n".join(parts)


def _relationship_aware_canonical_prompts(
    *,
    script: Path,
    project_path: Path,
    style_lock: Path,
    page_numbers: list[int],
    visual_source: str = "auto",
    prompt_compiler: str = DEFAULT_PROMPT_COMPILER,
    artifact_specs: dict[int, PageArtifactSpec] | None = None,
) -> dict[int, str]:
    """Compile strict prompts through the same page-intent path used for approval."""

    from cyberppt.script_quality_contract import parse_script_markdown
    from scripts.imagegen_pipeline.imagegen_handoff import (
        _page_missions,
        _page_visual_contexts,
        _page_visual_intent_overrides,
        compile_page_prompt,
    )

    document = parse_script_markdown(script.read_text(encoding="utf-8"))
    pages = {
        int(page.page_id[1:]): page
        for page in document.pages
        if page.page_type == "content"
    }
    if prompt_compiler == ARTIFACT_PROMPT_COMPILER:
        missing_script_pages = [number for number in page_numbers if number not in pages]
        if missing_script_pages:
            raise ValueError(
                "artifact compiler cannot resolve requested content pages in the approved script: "
                + ", ".join(f"P{number:02d}" for number in missing_script_pages)
            )
        specs = artifact_specs or {}
        missing = [number for number in page_numbers if number not in specs]
        if missing:
            raise ValueError(
                "artifact prompt projection is missing requested pages: "
                + ", ".join(f"P{number:02d}" for number in missing)
            )
        return {
            page_number: compile_page_prompt(
                pages[page_number],
                style_lock,
                prompt_compiler=ARTIFACT_PROMPT_COMPILER,
                artifact_spec=specs[page_number],
            ).prompt
            for page_number in page_numbers
            if page_number in pages
        }

    missions = _page_missions(project_path)
    # The current production compiler owns the page semantics and consumes the
    # selected style lock directly. Do not let a stale visual-structure package
    # become an implicit second authority.
    use_legacy_visual_context = prompt_compiler != DEFAULT_PROMPT_COMPILER
    contexts = _page_visual_contexts(project_path) if use_legacy_visual_context else {}
    overrides = _page_visual_intent_overrides(project_path) if use_legacy_visual_context else {}
    try:
        from cyberppt.stage02_input import input_page_map, load_stage02_input

        script_input = load_stage02_input(project_path)
    except (FileNotFoundError, ValueError):
        script_input = None
    input_pages = input_page_map(script_input) if script_input else {}
    # The final compiler owns content, Stage 02 semantics, and the selected
    # style together.  Nothing is appended after approval.
    canonical: dict[int, str] = {}
    source_blocks = parse_page_blocks(script)
    prior_decisions: list[Any] = []
    prior_semantic_carriers: list[str] = []
    for page_number in page_numbers:
        page = pages.get(page_number)
        if page is None:
            continue
        input_page = input_pages.get(page_number) or {}
        page_mission = str(input_page.get("page_mission") or missions.get(page.page_id, ""))
        visual_context = dict(contexts.get(page.page_id) or {})
        if not page.onscreen_text.strip():
            # Bare Markdown manuscripts may not use Stage 01 field labels.
            # Preserve their body as the source text for the normal compiler.
            from dataclasses import replace

            source_block = source_blocks.get(page_number)
            if source_block is not None:
                page = replace(
                    page,
                    onscreen_text=source_block.text.strip(),
                    raw_onscreen_text=source_block.text.strip(),
                )
        if prompt_compiler == DEFAULT_PROMPT_COMPILER:
            # Stage 01 visual notes are not part of the new production route.
            # Blank only this transient page view; the locked source script is
            # left untouched for audit and compatibility consumers.
            from dataclasses import replace

            page = replace(page, visual_structure="")
        compiled = compile_page_prompt(
            page,
            style_lock,
            page_mission=page_mission,
            visual_context=visual_context,
            visual_intent_override=overrides.get(page.page_id),
            prompt_compiler=prompt_compiler,
            prior_decisions=tuple(prior_decisions),
            prior_semantic_carriers=tuple(prior_semantic_carriers),
            visual_structure_mode="off",
            visual_design=None,
        )
        canonical[page_number] = compiled.prompt
        if compiled.presentation is not None:
            prior_decisions.append(compiled.presentation)
        if compiled.semantic_structure is not None:
            carrier = compiled.semantic_structure.get("visual_carrier") or {}
            if isinstance(carrier, dict) and carrier.get("selected"):
                prior_semantic_carriers.append(str(carrier["selected"]))
    return canonical


def build_manifest(
    *,
    script: Path,
    pages_raw: str,
    output_dir: Path,
    project_path: Path | None,
    style_lock: Path | None,
    force_pending: bool = False,
    require_approved_prompts: bool = False,
    production_mode: str = FULL_IMAGE_MODE,
    prompt_enrich: str = "off",
    require_send_approval: bool = False,
    enforce_prompt_freshness: bool = False,
    compact_blueprint: bool = False,
    visual_source: str = "auto",
    prompt_compiler: str = DEFAULT_PROMPT_COMPILER,
    allow_script_edit: bool = False,
    allow_prompt_edit: bool = False,
    prompt_overrides_dir: Path | None = None,
    persist: bool = True,
) -> tuple[dict[str, Any], Path, Path, list[int]]:
    prompt_compiler = validate_prompt_compiler(prompt_compiler)
    if prompt_compiler == ARTIFACT_PROMPT_COMPILER and project_path is None:
        raise ValueError("artifact-spec-v2 requires project_path")
    if visual_source not in {"auto", "governed-json", "legacy-markdown"}:
        raise ValueError("visual_source must be auto, governed-json, or legacy-markdown")
    if allow_prompt_edit and prompt_overrides_dir is None:
        raise ValueError("allow_prompt_edit requires prompt_overrides_dir")
    if (allow_script_edit or allow_prompt_edit) and prompt_enrich != "off":
        raise ValueError("direct script/prompt edit mode requires --prompt-enrich off")
    output_variants = output_variants_for_mode(production_mode)
    source_pages = parse_page_blocks(script)
    page_numbers = parse_pages(pages_raw, set(source_pages))
    from cyberppt.script_quality_contract import parse_script_markdown
    from cyberppt.visual_prompt_consumer import (
        load_visual_design,
        load_visual_prompt_module,
        visual_module_metadata,
    )
    from scripts.imagegen_pipeline.prompt_send_enrich import (
        enrich_result_as_dict,
        resolve_send_prompt,
    )

    script_pages = {
        int(page.page_id[1:]): page
        for page in parse_script_markdown(script.read_text(encoding="utf-8")).pages
    }
    role_aliases = {
        "cover": "cover",
        "contents": "agenda",
        "agenda": "agenda",
        "chapter": "section",
        "section": "section",
        "closing": "ending",
        "ending": "ending",
    }
    page_roles = {
        number: role_aliases.get(
            script_pages.get(number).page_type if number in script_pages else "",
            "content",
        )
        for number in page_numbers
    }
    stage02_input: dict[str, Any] | None = None
    stage02_input_path: Path | None = None
    input_pages: dict[int, dict[str, Any]] = {}
    if project_path is not None:
        from cyberppt.stage02_input import input_page_map, input_path, load_stage02_input

        stage02_input = load_stage02_input(project_path)
        if stage02_input is not None:
            stage02_input_path = input_path(project_path)
            input_pages = input_page_map(stage02_input)
            role_aliases_from_input = {
                "cover": "cover",
                "agenda": "agenda",
                "section": "section",
                "content": "content",
                "ending": "ending",
            }
            for number in page_numbers:
                input_page = input_pages.get(number)
                if input_page is None:
                    raise ValueError(f"Stage 02 script input is missing requested page {number}")
                page_roles[number] = role_aliases_from_input[str(input_page["render_role"])]
    content_page_numbers = [
        number for number in page_numbers if page_roles[number] == "content"
    ]
    # Style 09 is a universal surface-language contract, not the owner of a
    # page's layout. The final prompt must consume the approved Stage 02
    # visual module for every style; Style 09 is asserted only after that
    # page-specific module as the final rendering language.
    style09_source_contract = _is_style09_lock(style_lock)
    effective_compact_blueprint = bool(
        compact_blueprint and input_pages
    )
    if prompt_compiler == ARTIFACT_PROMPT_COMPILER and effective_compact_blueprint:
        raise ValueError("artifact-spec-v2 cannot be combined with compact_blueprint")
    if require_approved_prompts and effective_compact_blueprint:
        raise ValueError("compact_blueprint is a legacy preview and cannot enter approved production")
    reference_map = _load_reference_map(project_path)
    output_dir.mkdir(parents=True, exist_ok=True)
    compiled_script = _compiled_script_path(output_dir, script, page_numbers)
    approved_prompts: dict[int, tuple[str, Path]] = {}
    prompt_overrides: dict[int, tuple[str, Path]] = {}
    if allow_prompt_edit:
        assert prompt_overrides_dir is not None
        for page_number in content_page_numbers:
            candidates = (
                prompt_overrides_dir / f"p{page_number:02d}.txt",
                prompt_overrides_dir / f"p{page_number:02d}.md",
            )
            override_path = next((path for path in candidates if path.is_file()), None)
            if override_path is None:
                raise FileNotFoundError(
                    f"direct prompt edit mode is missing override for page {page_number}: "
                    f"{candidates[0]}"
                )
            override_text = override_path.read_text(encoding="utf-8-sig").strip()
            if not override_text:
                raise ValueError(f"direct prompt override is empty: {override_path}")
            prompt_overrides[page_number] = (override_text, override_path.resolve())
    relationship_aware_prompts: dict[int, str] = {}
    artifact_specs = (
        load_project_page_artifact_specs(project_path, style_lock=style_lock)
        if prompt_compiler == ARTIFACT_PROMPT_COMPILER
        and project_path is not None
        and style_lock is not None
        else {}
    )
    enrich_mode = (prompt_enrich or "off").strip().lower()
    if prompt_compiler == ARTIFACT_PROMPT_COMPILER and enrich_mode != "off":
        raise ValueError("artifact-spec-v2 cannot be changed by prompt enrichment after approval")
    if project_path is not None and style_lock is not None and not effective_compact_blueprint:
        relationship_aware_prompts = _relationship_aware_canonical_prompts(
            script=script,
            project_path=project_path,
            style_lock=style_lock,
            page_numbers=content_page_numbers,
            visual_source=visual_source,
            prompt_compiler=prompt_compiler,
            artifact_specs=artifact_specs,
        )
    if require_approved_prompts:
        if project_path is None:
            raise ValueError("per-slide prompt approval requires --project-path")
        if effective_compact_blueprint:
            relationship_aware_prompts = {}
            for page_number in content_page_numbers:
                module = load_visual_prompt_module(project_path, page_number)
                if module is None:
                    raise ValueError(
                        f"compact production prompt requires visual design module for page {page_number}"
                    )
                relationship_aware_prompts[page_number] = _compact_blueprint_prompt(
                    page_number=page_number,
                    handoff_page=input_pages[page_number],
                    visual_prompt=module.prompt_text,
                    style_lock=style_lock,
                )
        for page_number in content_page_numbers:
            approved_path = assert_approved_final_script(project_path, page_number, "imagegen")
            approved_text = approved_path.read_text(encoding="utf-8-sig")
            if prompt_compiler == ARTIFACT_PROMPT_COMPILER:
                spec = artifact_specs[page_number]
                validate_final_prompt(
                    approved_text,
                    build_final_prompt_ir(spec),
                    style_id=spec.art_direction.style_id,
                )
            approved_prompts[page_number] = (
                approved_text,
                approved_path,
            )
        # Keep explicit page delimiters in the compiled deliverable so the
        # prompt file remains auditable and can be traced back to its page.
        compiled = "\n\n".join(
            f"## p{page_number:02d}\n\n{approved_prompts[page_number][0].strip()}"
            for page_number in content_page_numbers
        ) + "\n"
    else:
        # Write the compiled audit artifact from the exact final per-page
        # prompts below.  A separate precompile path previously allowed Stage
        # 01 visual notes to bypass the approved Stage 02 layout module.
        compiled = ""

    # Compiled prompts no longer carry "## 第N页：" headers; use source page
    # metadata + per-page render_prompt for pair entries.
    pairs: list[dict[str, Any]] = []
    enrich_ledger: list[dict[str, Any]] = []
    for page_number in content_page_numbers:
        page = source_pages[page_number]
        reference_images = reference_map.get(page_number, [])
        prompt = relationship_aware_prompts.get(page_number) or render_prompt(
            page, style_lock_path=style_lock
        )
        prompt_source = "script_compiler"
        prompt_override_path: Path | None = None
        if page_number in prompt_overrides:
            prompt, prompt_override_path = prompt_overrides[page_number]
            prompt_source = "direct_prompt_override"
        elif allow_script_edit:
            prompt_source = "direct_script_edit"
        # The default production compiler consumes the final script and Style
        # 09 directly. Do not even load legacy visual-structure artifacts for
        # this route; their presence must not appear as a consumed handoff.
        visual_module = (
            load_visual_prompt_module(
                project_path,
                page_number,
                allow_legacy=visual_source in {"auto", "legacy-markdown"},
            )
            if project_path is not None
            and (prompt_compiler != DEFAULT_PROMPT_COMPILER or effective_compact_blueprint)
            else None
        )
        if effective_compact_blueprint:
            input_page = input_pages.get(page_number) or {}
            if not input_page:
                raise ValueError(
                    f"compact blueprint requires Stage 02 script input page {page_number}"
                )
            if visual_module is None:
                raise ValueError(
                    f"compact blueprint requires visual design module for page {page_number}"
                )
            prompt = _compact_blueprint_prompt(
                page_number=page_number,
                handoff_page=input_page,
                visual_prompt=visual_module.prompt_text,
                style_lock=style_lock,
            )
        approval_path: Path | None = None
        approval_meta: dict[str, Any] | None = None
        current_canonical_prompt = prompt
        approved_prompt = ""
        if page_number in approved_prompts:
            approved_prompt, approval_path = approved_prompts[page_number]
            canonical_prompt = relationship_aware_prompts.get(page_number, prompt).strip()
            current_canonical_prompt = canonical_prompt
            approval = build_prompt_approval(
                approved_path=approval_path,
                approved_prompt=approved_prompt,
                canonical_prompt=canonical_prompt,
                consumed_prompt=approved_prompt,
            )
            approval_meta = approval.metadata()
            # The approval is for complete compiler output.  A source/style
            # change is stale evidence, never permission to substitute a new
            # canonical prompt at send time.
            prompt = approved_prompt
        send_final: Path | None = None
        if project_path is not None and enrich_mode == "send":
            try:
                send_final = assert_approved_final_script(
                    project_path, page_number, "imagegen-send"
                )
            except (FileNotFoundError, PermissionError):
                if require_send_approval:
                    raise
                send_final = None
        enrich = resolve_send_prompt(
            approved_prompt=prompt,
            mode=enrich_mode,
            send_final_path=send_final,
            require_send=require_send_approval and enrich_mode == "send",
        )
        prompt = enrich.prompt
        # Enrichment is strictly a non-onscreen block.  It is placed before
        # the one STYLE09 terminal lock; it never owns page semantics or adds
        # a second style contract.
        if enrich.enrich_block:
            prompt = f"{prompt.rstrip()}\n\n{enrich.enrich_block.strip()}\n"
            if _is_style09_lock(style_lock):
                from scripts.imagegen_pipeline.deliverable_prompt import enforce_style09_terminal_lock

                prompt = enforce_style09_terminal_lock(prompt, style_lock)
        enrich_ledger.append({"page_number": page_number, **enrich_result_as_dict(enrich)})
        if approval_meta is not None:
            # Compare approval after every compiler-owned transformation,
            # including output-variant compilation and opt-in enrichment.
            # The old chain checked an earlier source prompt and then merely
            # overwrote a consumed hash, which certified bytes never sent.
            assert approval_path is not None
            approval = build_prompt_approval(
                approved_path=approval_path,
                approved_prompt=approved_prompt,
                canonical_prompt=current_canonical_prompt,
                consumed_prompt=prompt,
            )
            approval_meta = approval.metadata()
            if enforce_prompt_freshness:
                assert_prompt_fresh(approval, page_number=page_number)
        visual_handoff_metadata = visual_module_metadata(visual_module)
        stem = _page_stem(page_number, page.title)
        prompt_file = output_dir / "prompts" / f"p{page_number:02d}.txt"
        prompt = prompt.rstrip() + "\n"
        full_path = output_dir / f"{stem}_full.png"
        artifact_ir_fields: dict[str, Any] = {}
        if prompt_compiler == ARTIFACT_PROMPT_COMPILER and prompt_source != "direct_prompt_override":
            page_spec = artifact_specs[page_number]
            page_ir = build_final_prompt_ir(page_spec)
            artifact_ir_fields = {
                "prompt_ir_version": FINAL_PROMPT_IR_VERSION,
                # validate_final_prompt already ran inside render_final_prompt
                # when this prompt was compiled; reaching this line means it
                # passed, so there is nothing left to report but "ok".
                "final_prompt_contract": {"status": "ok", "issues": []},
                "debug_receipt": render_debug_receipt(
                    page_ir,
                    page_id=page_spec.page_id,
                    compiler=prompt_compiler,
                    prompt_ir_version=FINAL_PROMPT_IR_VERSION,
                    source_hashes=page_spec.source_hashes,
                ),
            }
        full = {
            "filename": full_path.name,
            "path": str(full_path),
            "prompt": prompt,
            "prompt_sha256": _sha256_text(prompt),
            "generation_method": FULL_GENERATION_METHOD,
            "operation": "generate",
            "output_role": "full_textual_visual_reference",
            "aspect_ratio": "content-region",
            "image_size": "2x-content-region",
            "canvas": f"{GENERATION_SIZE['width']}x{GENERATION_SIZE['height']}",
            "prompt_enrich": enrich_result_as_dict(enrich),
            "visual_structure_handoff": visual_handoff_metadata,
            "prompt_source": prompt_source,
            **({"prompt_override_path": str(prompt_override_path)} if prompt_override_path else {}),
            **({"prompt_override_sha256": _sha256_file(prompt_override_path)} if prompt_override_path else {}),
            **artifact_ir_fields,
            "prompt_provenance": {
                **(approval_meta or {}),
                **({
                    "consumed_prompt_sha256": _sha256_text(prompt),
                    "consumed_from": "script_compiler",
                } if approval_meta is None else {}),
            },
        }
        _mark_status(full, force_pending=force_pending)
        if not require_approved_prompts:
            compiled += f"## p{page_number:02d}\n\n{prompt.rstrip()}\n\n"
        variants: dict[str, dict[str, Any]] = {"full": full}
        image_text_reference = (
            "\n".join(artifact_specs[page_number].typography.visible_text)
            if prompt_compiler == ARTIFACT_PROMPT_COMPILER
            else script_pages[page_number].onscreen_text
        ).strip()
        pairs.append(
            {
                "page_number": page_number,
                "page_code": f"P{page_number:02d}",
                "title": page.title,
                "page_script": prompt,
                "image_text_truth": {
                    "script_text": image_text_reference,
                    "scope": "typo_and_gibberish_only",
                },
                "graphic_text_policy": {
                    "schema": "cyberppt.image_to_pptx.graphic_text_policy.v1",
                    "status": "required",
                    "empty_container_check": "required",
                    "items": [],
                    "note": "Classify embedded graphic text before clean-base preparation; complete this policy before Quick SVG export.",
                },
                "clean_base": {
                    "schema": "cyberppt.stage02.clean_base.v3",
                    "status": "required",
                    "algorithm_version": "masked-text-clearance-v3",
                    "note": "Prepare a text-free base by locally repairing only declared native_text regions; record one bounded repair per policy item, compute pixel-difference QA, and pass the clean-base visual checks before editable PPTX assembly.",
                },
                "prompt_file": str(prompt_file),
                **({"reference_images": reference_images} if reference_images else {}),
                "visual_structure_handoff": visual_handoff_metadata,
                **(
                    {
                        "stage02_script_input": str(stage02_input_path.resolve()),
                    }
                    if stage02_input_path is not None
                    else {}
                ),
                **({"prompt_approval": str(approval_path.resolve())} if approval_path else {}),
                **({"prompt_provenance": approval_meta} if approval_meta else {}),
                **variants,
            }
        )

    manifest = {
        "mode": "cyberppt.stage02.editable_pptx.v1",
        "production_mode": production_mode,
        "requested_pages": page_numbers,
        "content_page_numbers": content_page_numbers,
        "skipped_pages": [
            {
                "page_number": number,
                "page_role": page_roles[number],
                "render_mode": "template",
                "status": "skipped",
                "reason": "template_only_page",
            }
            for number in page_numbers
            if page_roles[number] != "content"
        ],
        "output_variants": output_variants,
        "text_audit_contract": {
            "required_before_enhancement": True,
            "scope": "typo_and_gibberish_only",
            "max_generation_attempts": 3,
            "failure_action": "regenerate_image",
        },
        "generation_contract": {
            "mode": FULL_IMAGE_MODE,
            "owner": "CyberPPT",
            "slide_canvas": CANVAS,
            "content_region": CONTENT_REGION,
            "generation_size": GENERATION_SIZE,
            "rule": "Generate one audited full content-area image for registered editable-SVG reconstruction; PPT title, subtitle and enterprise chrome are handled by template/export code.",
        },
        "project_path": str(project_path.resolve()) if project_path else "",
        "source_script": str(compiled_script.resolve()),
        "original_script": str(script.resolve()),
        "style_lock": str(style_lock.resolve()) if style_lock else None,
        "stage02_script_input": (
            {
                "path": str(stage02_input_path.resolve()),
                "schema": stage02_input.get("schema"),
            }
            if stage02_input_path is not None and stage02_input is not None
            else None
        ),
        "output_dir": str(output_dir.resolve()),
        "created_at": datetime.now(timezone.utc).isoformat(),
        "prompt_contract": {
            "approved_prompt_is_source": bool(require_approved_prompts),
            "direct_edit_mode": "prompt_override" if allow_prompt_edit else "script" if allow_script_edit else None,
            "freshness_enforced": bool(require_approved_prompts and enforce_prompt_freshness),
            "canonical_prompt_is_diagnostic_only": bool(require_approved_prompts),
            "compact_blueprint": effective_compact_blueprint,
            "compiler": prompt_compiler,
        },
        "prompt_enrich": {
            "mode": enrich_mode,
            "require_send_approval": require_send_approval,
            "pages": enrich_ledger,
        },
        "pairs": pairs,
    }
    manifest_path = output_dir / "page_image_pairs.json"
    if persist:
        write_manifest_artifacts(manifest, manifest_path, compiled_script)
    return manifest, manifest_path, compiled_script, page_numbers


def write_manifest_artifacts(manifest: dict[str, Any], manifest_path: Path, compiled_script: Path) -> None:
    """Publish only after compilation and production reuse validation succeed."""
    pairs = manifest.get("pairs", [])
    compiled = "\n\n".join(
        f"## p{int(pair['page_number']):02d}\n\n{str(pair['full']['prompt']).strip()}"
        for pair in pairs
    ) + "\n"
    with build_lock(manifest_path.parent, f"pair-manifest-{manifest_path.stem}"):
        for pair in pairs:
            atomic_write_text(Path(pair["prompt_file"]), str(pair["full"]["prompt"]).rstrip() + "\n")
        atomic_write_text(compiled_script, compiled)
        atomic_write_json(manifest_path, manifest)


def require_generated(manifest: dict[str, Any]) -> None:
    missing: list[str] = []
    contract_errors: list[str] = []
    production_mode = str(manifest.get("production_mode") or FULL_IMAGE_MODE)
    output_variants = output_variants_for_mode(production_mode)
    for pair in manifest.get("pairs", []):
        page_number = pair.get("page_number", "?")
        full_item = pair.get("full") or {}
        provenance = full_item.get("prompt_provenance") or {}
        prompt_contract = manifest.get("prompt_contract", {})
        if prompt_contract.get("approved_prompt_is_source"):
            if prompt_contract.get("freshness_enforced") and provenance.get("status") == "stale":
                contract_errors.append(f"page {page_number} approved prompt is stale")
        if full_item.get("generation_method") != FULL_GENERATION_METHOD:
            contract_errors.append(
                f"page {page_number} full.generation_method must be {FULL_GENERATION_METHOD}"
            )
        text_audit = full_item.get("text_audit") or {}
        if text_audit.get("valid") is not True:
            contract_errors.append(
                f"page {page_number} full image has no passed image-text audit"
            )
        for variant in output_variants:
            item = pair.get(variant) or {}
            path = Path(str(item.get("path", "")))
            if not path.is_file() or path.stat().st_size <= 0:
                missing.append(str(path))
    if contract_errors:
        raise ValueError(
            "CyberPPT image contract violation.\n"
            + "\n".join(contract_errors)
        )
    if missing:
        raise FileNotFoundError(
            "CyberPPT image files are not generated yet. Generate the pending manifest variants, "
            "then rerun with --require-images.\nMissing:\n"
            + "\n".join(missing)
        )


def _normalize_ingest_image(path: Path) -> None:
    """Resize a stored full image to the project generation canvas."""

    ensure_output_size(path, GENERATION_SIZE_TEXT)


def _copy_existing_images(existing_manifest: Path, output_dir: Path, *, force: bool = False) -> None:
    data = json.loads(existing_manifest.read_text(encoding="utf-8"))
    variants = output_variants_for_mode(str(data.get("production_mode") or FULL_IMAGE_MODE))
    for pair in data.get("pairs", []):
        page_number = int(pair["page_number"])
        title = str(pair.get("title") or f"page_{page_number}")
        stem = _page_stem(page_number, title)
        for variant in variants:
            item = pair.get(variant) or {}
            source = Path(str(item.get("path", ""))).expanduser()
            if not source.is_file():
                continue
            target = output_dir / f"{stem}_{variant}.png"
            if target.exists() and not force:
                continue
            output_dir.mkdir(parents=True, exist_ok=True)
            atomic_copy(source, target)
            _normalize_ingest_image(target)


def _find_blueprint_image(blueprint_dir: Path, page_number: int) -> Path | None:
    for pattern in BLUEPRINT_PATTERNS:
        candidate = blueprint_dir / pattern.format(page=page_number)
        if candidate.is_file():
            return candidate
    matches = sorted(blueprint_dir.glob(f"*{page_number:03d}*blueprint*.png"))
    if not matches:
        matches = sorted(blueprint_dir.glob(f"*{page_number}*blueprint*.png"))
    return matches[0] if matches else None


def _copy_full_images_from_blueprints(
    *,
    blueprint_dir: Path,
    output_dir: Path,
    script: Path,
    pages_raw: str,
    force: bool = False,
) -> None:
    source_pages = parse_page_blocks(script)
    page_numbers = parse_pages(pages_raw, set(source_pages))
    for page_number in page_numbers:
        blueprint = _find_blueprint_image(blueprint_dir, page_number)
        if blueprint is None:
            continue
        page = source_pages[page_number]
        target = output_dir / f"{_page_stem(page_number, page.title)}_full.png"
        if target.exists() and not force:
            continue
        output_dir.mkdir(parents=True, exist_ok=True)
        atomic_copy(blueprint, target)
        _normalize_ingest_image(target)


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Create CyberPPT image-to-editable-SVG manifests.")
    parser.add_argument("--script", required=True, type=Path)
    parser.add_argument("--pages", default="all")
    parser.add_argument("--output-dir", required=True, type=Path)
    parser.add_argument("--project-path", type=Path)
    parser.add_argument("--style-lock", type=Path)
    parser.add_argument("--style-id", type=int, choices=range(1, 11), metavar="1-10")
    parser.add_argument("--style-name")
    parser.add_argument("--production-mode", choices=PRODUCTION_MODES, default=FULL_IMAGE_MODE)
    parser.add_argument("--resume", action="store_true", help="Reuse existing images in output-dir if present.")
    parser.add_argument("--force", action="store_true", help="Mark images pending and overwrite copied cache images.")
    parser.add_argument("--require-generated", action="store_true", help="Fail if the audited full image is missing.")
    parser.add_argument("--copy-images-from", type=Path, help="Optional existing page_image_pairs.json to seed image files.")
    parser.add_argument(
        "--promote-blueprints-from",
        type=Path,
        help="Optional approved blueprint image directory; matching blueprint PNGs are copied as full images.",
    )
    parser.add_argument(
        "--prompt-enrich",
        choices=("off", "deterministic", "send"),
        default="off",
        help="Send-time prompt enrichment mode (default: off; approved prompt is consumed verbatim).",
    )
    parser.add_argument(
        "--require-send-approval",
        action="store_true",
        help="With --prompt-enrich send, require approved imagegen-send finals.",
    )
    args = parser.parse_args(argv)

    if args.copy_images_from:
        _copy_existing_images(args.copy_images_from.resolve(), args.output_dir.resolve(), force=args.force)
    if args.promote_blueprints_from:
        _copy_full_images_from_blueprints(
            blueprint_dir=args.promote_blueprints_from.resolve(),
            output_dir=args.output_dir.resolve(),
            script=args.script.resolve(),
            pages_raw=args.pages,
            force=args.force,
        )

    style_lock = args.style_lock.resolve() if args.style_lock else None
    if style_lock is not None and (args.style_id is not None or args.style_name):
        raise ValueError("--style-lock cannot be combined with --style-id or --style-name")
    if style_lock is None and args.project_path is not None:
        style_lock = write_project_style_lock(
            project=args.project_path.resolve(),
            style_id=args.style_id,
            style_name=args.style_name,
            source_script=args.script.resolve(),
        )

    manifest, manifest_path, compiled_script, page_numbers = build_manifest(
        script=args.script.resolve(),
        pages_raw=args.pages,
        output_dir=args.output_dir.resolve(),
        project_path=args.project_path.resolve() if args.project_path else None,
        style_lock=style_lock,
        force_pending=bool(args.force and not args.resume),
        production_mode=args.production_mode,
        prompt_enrich=args.prompt_enrich,
        require_send_approval=args.require_send_approval,
    )
    if args.require_generated:
        require_generated(manifest)
    print(json.dumps({
        "manifest": str(manifest_path),
        "compiled_script": str(compiled_script),
        "pages": page_numbers,
        "pairs": len(manifest["pairs"]),
    }, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
