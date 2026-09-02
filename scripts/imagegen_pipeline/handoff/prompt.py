"""Compile approved page content into ImageGen handoff prompts."""

from __future__ import annotations

import re
from pathlib import Path

from cyberppt.composition_resolver import resolve_composition
from cyberppt.page_artifact_spec import PageArtifactSpec
from cyberppt.script_quality_contract import ScriptPage
from cyberppt.visual_carrier_resolver import select_visual_carrier
from scripts.imagegen_pipeline.artifact_prompt import build_final_prompt_ir, render_artifact_prompt
from scripts.imagegen_pipeline.final_prompt_ir import FINAL_PROMPT_IR_VERSION
from scripts.imagegen_pipeline.final_prompt_renderer import render_debug_receipt, render_final_prompt
from scripts.imagegen_pipeline.creative_brief import CreativeBrief, render_creative_brief
from scripts.imagegen_pipeline.deliverable_prompt import (
    PageBlock,
    _style09_page_semantic_tags,
    assert_deliverable_prompt,
    render_prompt,
)
from scripts.imagegen_pipeline.page_semantics import (
    PageSemanticContext,
    derive_page_semantics,
)
from scripts.imagegen_pipeline.prompt_compiler import (
    ARTIFACT_PROMPT_COMPILER,
    CompiledPagePrompt,
    DEFAULT_PROMPT_COMPILER,
    DEFAULT_TEXT_RENDER_MODE,
    validate_prompt_compiler,
    validate_text_render_mode,
)
from scripts.imagegen_pipeline.handoff.contracts import (
    CONTENT_FIRST_CORE_MEANING_LABEL,
    CONTENT_FIRST_ONSCREEN_STORY_CONTRACT,
    CONTENT_FIRST_PAGE_MISSION_LABEL,
    CONTENT_FIRST_SHARED_PREDICATE_CONTRACT,
    CONTENT_FIRST_VISIBLE_TEXT_WHITELIST_CONTRACT,
    EVIDENCE_ID_RE,
    IMAGEGEN_CANVAS_CONTRACT,
    IMAGEGEN_CHROME_BAN_CONTRACT,
    SEMANTIC_VISUAL_BRIEF_HEADER,
    SEMANTIC_VISUAL_CHROME_CONTRACT,
    SEMANTIC_VISUAL_FACTS_HEADER,
    SEMANTIC_VISUAL_TEXT_CONTRACT,
)
from scripts.imagegen_pipeline.handoff.presentation import (
    PresentationDecision,
    render_content_first_style_contract,
    render_page_logic_contract,
    render_presentation_contract,
    resolve_presentation_decision,
)
from scripts.imagegen_pipeline.handoff.semantics import (
    _page_semantic_relations,
    build_page_creative_brief,
    build_page_visual_intent,
    resolve_page_semantic_intent,
    resolve_page_visual_intent,
)
from scripts.imagegen_pipeline.handoff.text import (
    _selected_content_first_style,
    content_lock_text,
    render_semantic_visual_brief,
    resolve_onscreen_judgment_mode,
    resolve_text_render_mode,
)


__all__ = (
    "build_page_prompt",
    "compile_page_prompt",
    "render_content_first_prompt",
)


def render_content_first_prompt(
    page: ScriptPage,
    *,
    style_lock: Path,
    page_mission: str = "",
    visual_context: dict[str, str] | None = None,
    visual_intent_override: dict[str, str] | None = None,
    presentation_decision: PresentationDecision | None = None,
    semantic_context: PageSemanticContext | None = None,
    semantic_composition_contract: str = "",
    stage02_semantic_adapter: str = "",
    text_render_mode: str = DEFAULT_TEXT_RENDER_MODE,
) -> tuple[str, str]:
    """Render a content-first prompt with an explicit text/image boundary."""

    text_render_mode = validate_text_render_mode(text_render_mode)

    # The core meaning is mandatory semantic context; a visible conclusion is optional.
    judgment_mode = resolve_onscreen_judgment_mode(page, visual_context)
    semantic_visual = text_render_mode == "semantic_visual"
    onscreen_body = page.onscreen_text.strip()
    core_meaning_for_semantics = page.core_message.strip() or page.title.strip()
    # The script's 上屏文字 is a content reference. Assembly may rewrite it
    # freely for a readable visual expression; it is not a bitmap whitelist.
    complete_semantics = onscreen_body
    style09_semantic_tags = _style09_page_semantic_tags(
        PageBlock(page.sequence, page.title, complete_semantics),
        [line for line in complete_semantics.splitlines() if line.strip()],
    )
    # Style 09 is a shared visual surface, not a page-specific blueprint
    # language.  The final script's ``结构形态`` often contains literal
    # instructions such as "四行矩阵", "泳道" or "顶部五节点".  Passing that
    # authoring field to ImageGen makes those recipes dominate the generic
    # style contract and is the direct cause of the recent P19–P27 card-wall
    # output.  Keep the semantic intent resolver (which still reads the field)
    # but do not forward the layout recipe itself for Style 09.
    selected_style_for_logic = _selected_content_first_style(style_lock)
    style09_surface = int(selected_style_for_logic.get("id") or 0) == 9
    include_authoring_structure = not style09_surface
    if semantic_context is None:
        relation, intent_source, logic_contract = render_page_logic_contract(
            page,
            page_mission=page_mission,
            visual_context=visual_context,
            visual_intent_override=visual_intent_override,
            include_structure=include_authoring_structure,
        )
        semantic_relations = _page_semantic_relations(page)
    else:
        relation = semantic_context.relation
        intent_source = semantic_context.intent_source
        _, _, logic_contract = render_page_logic_contract(
            page,
            page_mission=page_mission,
            visual_context=semantic_context.visual_context,
            visual_intent_override=semantic_context.visual_intent_override,
            include_structure=include_authoring_structure,
        )
        semantic_relations = semantic_context.semantic_relations
    # Only the Stage 02 relationship-aware path has an audited page context to
    # accompany this compact label.  Keep ordinary direct callers and generic
    # pages free of a synthetic logic block, as they were before the Style 09
    # adapter was added.
    style09_relation_context = style09_surface and bool(
        visual_context
        or (
            semantic_context is not None
            and semantic_context.visual_context
        )
    )
    presentation = presentation_decision or resolve_presentation_decision(
        page,
        relation,
    )
    if semantic_composition_contract:
        # Review mode replaces legacy composition inference. Keeping both would
        # give ImageGen two conflicting structural instructions. The legacy
        # relation remains available in review metadata for human comparison.
        logic_contract = ""
    # Dense medium may still guide typography, but approved facts from full
    # prose must not be re-promoted into a must-onscreen contract. Gaps belong
    # in Stage 01 上屏文字, not in ImageGen recovery.
    # Core meaning is passed separately from optional visible conclusion.
    # Content-first keeps ordinary pages free of the long logic block. Inject
    # it only when the relation is confidently known and is not the low-score
    # judgment_evidence fallback — never force a wrong default into every
    # semantic_only page.
    include_logic_context = bool(
        # Style 09 receives the compact relation label even when the page's
        # authoring metadata does not provide a high-confidence legacy source,
        # but only when that source is a real signal (explicit/hint/contract
        # relation, or scored with actual semantic relations to point at).
        # The bare "scored + semantic_only" fallback is too weak a signal for
        # style09 — it fires on nearly every ordinary page — so it must not
        # leak the block there even though it still applies to other styles.
        style09_relation_context
        or (
            relation != "judgment_evidence"
            and (
                intent_source in {"explicit", "hint", "contract_relation"}
                or (
                    intent_source == "scored"
                    and (
                        bool(semantic_relations)
                        or (not style09_surface and judgment_mode == "semantic_only")
                    )
                )
            )
        )
    )
    presentation_contract = (
        render_presentation_contract(page, presentation)
        if presentation.source == "script"
        else ""
    )
    if semantic_visual:
        semantic_brief = render_semantic_visual_brief(page)
        page_specific_semantics = str(
            (visual_context or {}).get("visual_center") or ""
        ).strip()
        parts = [
            SEMANTIC_VISUAL_TEXT_CONTRACT,
            "",
            SEMANTIC_VISUAL_FACTS_HEADER,
            f"- 页面核心意思：{core_meaning_for_semantics}",
            (
                f"- 页面副标题语义：{page.subtitle.strip()}"
                if page.subtitle.strip()
                else ""
            ),
            (
                f"- 页面任务：{page_mission.strip()}"
                if page_mission.strip()
                else ""
            ),
                "【上屏文字参考】",
                onscreen_body,
            "",
            SEMANTIC_VISUAL_BRIEF_HEADER,
            semantic_brief,
            (
                "【页面专属语义图谱｜仅供理解】\n" + page_specific_semantics
                if page_specific_semantics
                else ""
            ),
            "",
            (
                "【页面语义关系｜仅供理解，不上屏】\n" + semantic_relations
                if semantic_relations
                else ""
            ),
            "",
            logic_contract if include_logic_context else "",
            "",
            presentation_contract,
            "",
            IMAGEGEN_CANVAS_CONTRACT,
            "",
            SEMANTIC_VISUAL_CHROME_CONTRACT,
            "",
            stage02_semantic_adapter.strip(),
            "",
            render_content_first_style_contract(
                style_lock,
                semantic_tags=style09_semantic_tags,
            ),
        ]
    else:
        nonvisible_semantic_context = (
            [
                "【非上屏语义边界】",
                "页面任务与核心意思已在上游用于推导语义关系，不在本提示中复述原句；不得自行生成额外结论、总结框或标题。",
                "",
            ]
            if style09_surface
            else [
                CONTENT_FIRST_PAGE_MISSION_LABEL,
                page_mission.strip() or page.core_message.strip(),
                "",
                CONTENT_FIRST_CORE_MEANING_LABEL,
                core_meaning_for_semantics,
                "",
            ]
        )
        parts = [
            "【完整上屏内容】",
            complete_semantics,
            "",
            CONTENT_FIRST_ONSCREEN_STORY_CONTRACT,
            "",
            CONTENT_FIRST_VISIBLE_TEXT_WHITELIST_CONTRACT,
            "",
            CONTENT_FIRST_SHARED_PREDICATE_CONTRACT,
            "",
            *nonvisible_semantic_context,
            (
                "【页面语义关系｜仅供理解，不上屏】\n" + semantic_relations
                if semantic_relations
                else ""
            ),
            "",
            logic_contract if include_logic_context else "",
            "",
            presentation_contract,
            "",
            IMAGEGEN_CANVAS_CONTRACT,
            "",
            IMAGEGEN_CHROME_BAN_CONTRACT,
            "",
            stage02_semantic_adapter.strip(),
            "",
            render_content_first_style_contract(
                style_lock,
                semantic_tags=style09_semantic_tags,
            ),
        ]
    if semantic_composition_contract:
        # Composition guidance is semantic metadata, never visible copy.
        insert_at = 2 if semantic_visual else 3
        parts[insert_at:insert_at] = [semantic_composition_contract, ""]
    return relation, "\n".join(parts).strip() + "\n"

def compile_page_prompt(
    page: ScriptPage,
    style_lock: Path,
    page_mission: str = "",
    visual_context: dict[str, str] | None = None,
    visual_intent_override: dict[str, str] | None = None,
    prompt_compiler: str = DEFAULT_PROMPT_COMPILER,
    prior_decisions: tuple[PresentationDecision, ...] = (),
    visual_structure_mode: str = "off",
    prior_semantic_carriers: tuple[str, ...] = (),
    text_render_mode: str | None = None,
    visual_design: "VisualDesignIR | None" = None,
    enrichment_block: str = "",
    artifact_spec: PageArtifactSpec | None = None,
) -> CompiledPagePrompt:
    prompt_compiler = validate_prompt_compiler(prompt_compiler)
    if visual_structure_mode not in {"off", "review"}:
        raise ValueError("visual_structure_mode must be 'off' or 'review'")
    if visual_structure_mode == "review" and prompt_compiler != "content-first-v1":
        raise ValueError("visual structure review mode requires content-first-v1")
    if prompt_compiler == ARTIFACT_PROMPT_COMPILER:
        if artifact_spec is None:
            raise ValueError("artifact-spec-v2 requires artifact_spec")
        if visual_design is not None or enrichment_block.strip():
            raise ValueError(
                "artifact-spec-v2 accepts only artifact_spec; visual_design and enrichment are separate prompt authorities"
            )
        final_prompt_ir = build_final_prompt_ir(artifact_spec)
        prompt = render_final_prompt(
            final_prompt_ir,
            style_id=artifact_spec.art_direction.style_id,
            style_lock=style_lock,
        )
        debug_receipt = render_debug_receipt(
            final_prompt_ir,
            page_id=artifact_spec.page_id,
            compiler=prompt_compiler,
            prompt_ir_version=FINAL_PROMPT_IR_VERSION,
            source_hashes=artifact_spec.source_hashes,
        )
        relation = artifact_spec.relationships[0] if artifact_spec.relationships else "artifact_spec"
        art_direction = artifact_spec.art_direction
        return CompiledPagePrompt(
            prompt=prompt,
            compiler_version=prompt_compiler,
            relation=relation,
            injected_rule_ids=(
                "artifact.deliverable",
                "artifact.communication_goal",
                "artifact.visual_thesis",
                "artifact.evidence_relationships",
                "artifact.visual_carrier",
                "artifact.composition",
                "artifact.art_direction",
                "artifact.typography",
                "artifact.hard_constraints",
            ),
            style_selection={
                "id": art_direction.style_id,
                "slug": art_direction.style_slug,
                "name": art_direction.style_name,
                "style_lock": str(style_lock),
            },
            image_locked_text="",
            text_render_mode="full_image",
            prompt_ir_version=FINAL_PROMPT_IR_VERSION,
            debug_receipt=debug_receipt,
            artifact_spec=artifact_spec,
        )
    semantic_context = derive_page_semantics(
        page,
        page_mission=page_mission,
        visual_context=visual_context,
        visual_intent_override=visual_intent_override,
        resolve_intent=resolve_page_visual_intent,
        extract_relations=_page_semantic_relations,
    )
    if prompt_compiler == "content-first-v1":
        stage02_semantic_adapter = ""
        if visual_design is not None:
            from scripts.imagegen_pipeline.style09_adapter import adapt_style09

            selected_style = _selected_content_first_style(style_lock)
            if int(selected_style.get("id") or 0) == 9:
                stage02_semantic_adapter = adapt_style09(visual_design).render_non_onscreen()
            else:
                from cyberppt.visual_prompt_consumer import _compile_visual_design

                stage02_semantic_adapter = _compile_visual_design(visual_design)
        if enrichment_block.strip():
            stage02_semantic_adapter = "\n\n".join(
                item for item in (stage02_semantic_adapter, enrichment_block.strip()) if item
            )
        selected_style = _selected_content_first_style(style_lock)
        resolved_text_render_mode = resolve_text_render_mode(
            style_lock,
            explicit=text_render_mode,
        )
        relation = semantic_context.relation
        presentation = resolve_presentation_decision(
            page,
            relation,
            prior_decisions,
        )
        semantic_structure: dict[str, object] | None = None
        semantic_composition_contract = ""
        if visual_structure_mode == "review":
            semantic_decision = resolve_page_semantic_intent(
                page,
                page_mission,
                context=visual_context,
                override=visual_intent_override,
            )
            composition = resolve_composition(semantic_decision)
            carrier = select_visual_carrier(
                semantic_decision,
                composition,
                prior_semantic_carriers,
            )
            semantic_structure = {
                "mode": visual_structure_mode,
                "intent": semantic_decision.to_dict(),
                "composition": composition.to_dict(),
                "visual_carrier": carrier.to_dict(),
            }
            semantic_composition_contract = "\n".join(
                (
                    "[Mandatory composition guidance] Apply this layout guidance before placing any on-screen text. Do not render its field names or instruction text.",
                    "[Prompt context] Page-specific visual intent (composition guidance only; do not render field names or instruction text)",
                    f"- Selected visual intent type: {semantic_decision.primary_intent}",
                    f"- Decision relationship: {semantic_decision.primary_intent}",
                    f"- Dominant visual carrier: {carrier.selected}",
                    f"- Recommended composition: {composition.spatial_organization}",
                    f"- Reading path: {' -> '.join(composition.reading_path)}",
                    f"- Relationship encoding: {', '.join(composition.relationship_encoding)}",
                    f"- Required structural elements: {', '.join(composition.required_elements)}",
                    f"- Avoid on this page: {', '.join(composition.avoid)}",
                    "- Keep one visual center. Attach supporting text to its business objects and relation nodes; do not create an independent text wall.",
                )
            )
        relation, prompt = render_content_first_prompt(
            page,
            style_lock=style_lock,
            page_mission=page_mission,
            visual_context=visual_context,
            visual_intent_override=visual_intent_override,
            presentation_decision=presentation,
            semantic_context=semantic_context,
            semantic_composition_contract=semantic_composition_contract,
            stage02_semantic_adapter=stage02_semantic_adapter,
            text_render_mode=resolved_text_render_mode,
        )
        if int(selected_style.get("id") or 0) == 9:
            from scripts.imagegen_pipeline.deliverable_prompt import enforce_style09_terminal_lock

            prompt = enforce_style09_terminal_lock(prompt, style_lock)
        assert_deliverable_prompt(prompt)
        if EVIDENCE_ID_RE.search(prompt):
            raise ValueError(f"{page.page_id} ImageGen prompt still contains evidence IDs")
        return CompiledPagePrompt(
            prompt=prompt,
            compiler_version=prompt_compiler,
            relation=relation,
            injected_rule_ids=(
                "content.page_task",
                "content.core_meaning",
                "content.full_semantics",
                "content.page_logic_contract",
                "content.locked_key_copy",
                "content.complete_page_semantics",
                "content.independent_reading",
                "fact.source_boundary",
                "style.selected_lock",
                "style.tone_only",
                *(
                    (
                        "semantic_structure.intent",
                        "semantic_structure.composition",
                        "semantic_structure.carrier",
                    )
                    if visual_structure_mode == "review"
                    else ()
                ),
            ),
            style_selection={
                "id": selected_style.get("id"),
                "slug": selected_style.get("slug"),
                "name": selected_style.get("name"),
                "colors": dict(selected_style.get("colors") or {}),
                "style_lock": str(style_lock),
            },
            presentation=presentation,
            image_locked_text="",
            editable_body_text=page.onscreen_text.strip(),
            semantic_structure=semantic_structure,
            text_render_mode=resolved_text_render_mode,
        )

    relation = semantic_context.relation
    creative_brief: CreativeBrief | None = None
    if prompt_compiler == "creative-brief-v1":
        creative_brief = build_page_creative_brief(
            page,
            page_mission,
            context=visual_context,
            override=visual_intent_override,
        )
        visual_intent = render_creative_brief(creative_brief)
        injected_rule_ids = (
            "creative.context",
            "creative.freedom_envelope",
            "text.locked_key_copy_exact",
            "text.auxiliary_allowed",
            *(
                f"creative.page_avoid.{index}"
                for index, _ in enumerate(
                    creative_brief.page_specific_avoids,
                    start=1,
                )
            ),
        )
    else:
        visual_intent = build_page_visual_intent(
            page,
            page_mission,
            context=visual_context,
            override=visual_intent_override,
        )
        injected_rule_ids = ("legacy.visual_intent", "legacy.visual_grammar")
    prompt_text = content_lock_text(page, page_mission=page_mission).rstrip()
    block = PageBlock(
        page_number=int(page.page_id[1:]),
        title=page.title or page.page_id,
        text=prompt_text,
    )
    prompt = render_prompt(
        block,
        style_lock_path=style_lock,
        composition_guidance=visual_intent,
        compiler_version=prompt_compiler,
    )
    assert_deliverable_prompt(prompt)
    if EVIDENCE_ID_RE.search(prompt):
        raise ValueError(f"{page.page_id} ImageGen prompt still contains evidence IDs")
    for banned in ("完整文字稿", "文字稿取舍说明", "证据映射", "讲解提示", "禁止项"):
        if banned in prompt:
            raise ValueError(f"{page.page_id} ImageGen prompt still contains backend field: {banned}")
    if "Boundary (do not show on slide)" in prompt:
        raise ValueError(f"{page.page_id} ImageGen prompt still contains Boundary block")
    # Field injection form only — style presets may still mention the concept as guidance.
    if "视觉结构：" in prompt or re.search(r"(?m)^-?\s*视觉结构\b", prompt):
        raise ValueError(f"{page.page_id} ImageGen prompt still contains backend field: 视觉结构")
    return CompiledPagePrompt(
        prompt=prompt,
        compiler_version=prompt_compiler,
        relation=relation,
        creative_brief=creative_brief,
        injected_rule_ids=tuple(injected_rule_ids),
    )


def build_page_prompt(
    page: ScriptPage,
    style_lock: Path,
    page_mission: str = "",
    visual_context: dict[str, str] | None = None,
    visual_intent_override: dict[str, str] | None = None,
    prompt_compiler: str = DEFAULT_PROMPT_COMPILER,
    visual_structure_mode: str = "off",
    text_render_mode: str | None = None,
) -> str:
    """Backward-compatible string API over the versioned prompt compiler."""

    return compile_page_prompt(
        page,
        style_lock,
        page_mission=page_mission,
        visual_context=visual_context,
        visual_intent_override=visual_intent_override,
        prompt_compiler=prompt_compiler,
        visual_structure_mode=visual_structure_mode,
        text_render_mode=text_render_mode,
    ).prompt
