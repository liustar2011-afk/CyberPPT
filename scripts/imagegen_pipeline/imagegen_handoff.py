#!/usr/bin/env python3
"""Compatibility facade for the reviewable ImageGen handoff pipeline.
Behavior lives in ``handoff`` modules; these names are direct re-exports so legacy imports
and direct script execution keep working without wrappers or duplicate rules.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from cyberppt.commands.script_gate import stage_script
from cyberppt.script_quality_contract import (ScriptPage, parse_script_markdown, resolve_judgment_mode, strip_authoring_group_marker)
from cyberppt.semantic_intent import (SemanticIntentDecision, canonicalize_intent, resolve_semantic_intent, validate_semantic_structure)
from cyberppt.composition_resolver import resolve_composition, validate_composition
from cyberppt.page_artifact_spec import PageArtifactSpec, load_project_page_artifact_specs
from cyberppt.visual_carrier_resolver import select_visual_carrier, validate_visual_carrier
from scripts.imagegen_pipeline.creative_brief import (CreativeBrief, build_creative_brief, render_creative_brief)
from scripts.imagegen_pipeline.deliverable_prompt import (
    PageBlock,
    _compile_style09_contract,
    _style09_page_semantic_tags,
    assert_deliverable_prompt,
    render_prompt,
)
from scripts.imagegen_pipeline.prompt_diagnostics import (
    PagePromptDiagnostics,
    analyze_prompt,
    write_batch_diagnostics,
    write_compiler_comparison,
)
from scripts.imagegen_pipeline.style_library import (
    _strip_style09_registry_meta,
    load_style_lock,
    resolve_default_style,
)
from scripts.imagegen_pipeline.page_semantics import (PageSemanticContext, derive_page_semantics)
from scripts.imagegen_pipeline.prompt_compiler import (
    ARTIFACT_PROMPT_COMPILER,
    CompiledPagePrompt,
    DEFAULT_PROMPT_COMPILER,
    DEFAULT_TEXT_RENDER_MODE,
    PROMPT_COMPILERS,
    TEXT_RENDER_MODES,
    validate_prompt_compiler,
    validate_text_render_mode,
)
from scripts.imagegen_pipeline.script_parser import (
    load_page_missions,
    load_page_visual_contexts,
    load_page_visual_intent_overrides,
)
from scripts.imagegen_pipeline.build_transaction import atomic_write_text, build_lock
from scripts.imagegen_pipeline.artifact_prompt import render_artifact_prompt
from scripts.imagegen_pipeline.handoff.common import (
    _clean_onscreen_for_imagegen,
    _module_label,
)
from scripts.imagegen_pipeline.handoff.contracts import (
    BUSINESS_RELATION_MARKERS,
    CONTENT_FIRST_CORE_JUDGMENT_LABEL,
    CONTENT_FIRST_CORE_MEANING_LABEL,
    CONTENT_FIRST_ONSCREEN_STORY_CONTRACT,
    CONTENT_FIRST_PAGE_MISSION_LABEL,
    CONTENT_FIRST_SEMANTIC_ONLY_STORY_CONTRACT,
    CONTENT_FIRST_SEMANTIC_ONLY_WITH_LOCKED_STORY_CONTRACT,
    CONTENT_FIRST_SHARED_PREDICATE_CONTRACT,
    CONTENT_FIRST_VISIBLE_TEXT_WHITELIST_CONTRACT,
    DETACHED_TEXT_RAIL_AVOID,
    EVIDENCE_ID_RE,
    IMAGEGEN_CANVAS_CONTRACT,
    IMAGEGEN_CHROME_BAN_CONTRACT,
    NON_RENDERING_RELATION_LABELS,
    ONSCREEN_ASIDE_RE,
    PAGE_SEMANTIC_LABEL_MARKERS,
    PAGE_SEMANTIC_LEAD_PHRASE_MARKERS,
    PAGE_SEMANTIC_MARKERS,
    PAGE_SEMANTIC_PHRASE_MARKERS,
    PAGE_SEMANTIC_STRUCTURE_LABEL_MARKERS,
    SEMANTIC_VISUAL_BRIEF_HEADER,
    SEMANTIC_VISUAL_CHROME_CONTRACT,
    SEMANTIC_VISUAL_FACTS_HEADER,
    SEMANTIC_VISUAL_TEXT_CONTRACT,
    TEXT_IN_COMPOSITION_RULE,
    VISUAL_INTENT_PRIORITY,
    VISUAL_INTENT_SIGNALS,
    VISUAL_INTENT_TEMPLATES,
    VISUAL_PROOF_FALLBACKS,
    VISUAL_STRUCTURE_HARD_HINTS,
    _AUTHORING_STRUCTURE_TAIL_RE,
    _CROSSCUT_HARD_HINT_MARKERS,
    _CROSSCUT_HARD_HINT_PREFIXES,
    _LABEL_SEMANTIC_RE,
    _STRUCTURE_LABEL_LEAD_RE,
)
from scripts.imagegen_pipeline.handoff.semantics import (
    MODULE_CHAIN_MARKERS,
    _explicit_visual_intent_type,
    _has_business_relation_marker,
    _has_semantic_marker,
    _is_degenerate_semantic_sentence,
    _is_module_enumeration_chain,
    _normalize_semantic_sentence,
    _page_semantic_relations,
    _visual_structure_hard_hint,
    audit_page_semantic_intent,
    build_page_creative_brief,
    build_page_visual_intent,
    resolve_page_semantic_intent,
    resolve_page_visual_intent,
    select_page_visual_intent_type,
)
from scripts.imagegen_pipeline.handoff.text import (
    MAX_IMAGE_LOCKED_CHARS,
    MAX_IMAGE_LOCKED_LINE_CHARS,
    MAX_IMAGE_LOCKED_LINES,
    ONSCREEN_JUDGMENT_MODES,
    _flatten_markdown_tables,
    _selected_content_first_style,
    _semantic_phrase_digest,
    content_lock_text,
    diagnostic_onscreen_text,
    locked_onscreen_text,
    render_semantic_visual_brief,
    resolve_onscreen_judgment_mode,
    resolve_text_render_mode,
    select_image_locked_text,
)
from scripts.imagegen_pipeline.handoff.presentation import (
    CONTENT_FIRST_STYLE_RULE_FIELDS,
    DEFAULT_SCENE_ROLE_BY_MOTIF,
    DEFAULT_SCENE_ROLE_BY_RELATION,
    LAYOUT_MOTIFS,
    MOTIF_CANDIDATES,
    PresentationDecision,
    SCENE_ROLES,
    STYLE_COLOR_LABELS,
    VISUAL_MEDIA,
    compact_visual_structure_for_logic,
    render_content_first_style_contract,
    render_page_logic_contract,
    render_presentation_contract,
    render_visual_carrier_contract,
    render_visual_center_contract,
    resolve_presentation_decision,
    resolve_visual_carrier,
    resolve_visual_center,
    resolve_visual_medium,
    select_dense_supporting_facts,
)
from scripts.imagegen_pipeline.handoff.prompt import (
    build_page_prompt,
    compile_page_prompt,
    render_content_first_prompt,
)
from scripts.imagegen_pipeline.handoff.delivery import (
    _page_missions,
    _page_visual_contexts,
    _page_visual_intent_overrides,
    write_chapter_handoff,
)
from scripts.imagegen_pipeline.handoff.cli import main

__all__ = (
    "ARTIFACT_PROMPT_COMPILER", "Any", "BUSINESS_RELATION_MARKERS", "CONTENT_FIRST_CORE_JUDGMENT_LABEL", "CONTENT_FIRST_CORE_MEANING_LABEL", "CONTENT_FIRST_ONSCREEN_STORY_CONTRACT", "CONTENT_FIRST_PAGE_MISSION_LABEL", "CONTENT_FIRST_SEMANTIC_ONLY_STORY_CONTRACT", "CONTENT_FIRST_SEMANTIC_ONLY_WITH_LOCKED_STORY_CONTRACT", "CONTENT_FIRST_SHARED_PREDICATE_CONTRACT",
    "CONTENT_FIRST_STYLE_RULE_FIELDS", "CONTENT_FIRST_VISIBLE_TEXT_WHITELIST_CONTRACT", "CompiledPagePrompt", "CreativeBrief", "DEFAULT_PROMPT_COMPILER", "DEFAULT_SCENE_ROLE_BY_MOTIF", "DEFAULT_SCENE_ROLE_BY_RELATION", "DEFAULT_TEXT_RENDER_MODE", "DETACHED_TEXT_RAIL_AVOID", "EVIDENCE_ID_RE",
    "IMAGEGEN_CANVAS_CONTRACT", "IMAGEGEN_CHROME_BAN_CONTRACT", "LAYOUT_MOTIFS", "MAX_IMAGE_LOCKED_CHARS", "MAX_IMAGE_LOCKED_LINES", "MAX_IMAGE_LOCKED_LINE_CHARS", "MODULE_CHAIN_MARKERS", "MOTIF_CANDIDATES", "NON_RENDERING_RELATION_LABELS", "ONSCREEN_ASIDE_RE",
    "ONSCREEN_JUDGMENT_MODES", "PAGE_SEMANTIC_LABEL_MARKERS", "PAGE_SEMANTIC_LEAD_PHRASE_MARKERS", "PAGE_SEMANTIC_MARKERS", "PAGE_SEMANTIC_PHRASE_MARKERS", "PAGE_SEMANTIC_STRUCTURE_LABEL_MARKERS", "PROMPT_COMPILERS", "PageArtifactSpec", "PageBlock", "PagePromptDiagnostics",
    "PageSemanticContext", "Path", "PresentationDecision", "SCENE_ROLES", "SEMANTIC_VISUAL_BRIEF_HEADER", "SEMANTIC_VISUAL_CHROME_CONTRACT", "SEMANTIC_VISUAL_FACTS_HEADER", "SEMANTIC_VISUAL_TEXT_CONTRACT", "STYLE_COLOR_LABELS",
    "ScriptPage", "SemanticIntentDecision", "TEXT_IN_COMPOSITION_RULE", "TEXT_RENDER_MODES", "VISUAL_INTENT_PRIORITY", "VISUAL_INTENT_SIGNALS", "VISUAL_INTENT_TEMPLATES", "VISUAL_MEDIA", "VISUAL_PROOF_FALLBACKS", "VISUAL_STRUCTURE_HARD_HINTS",
    "analyze_prompt", "annotations", "argparse", "assert_deliverable_prompt", "atomic_write_text", "audit_page_semantic_intent", "build_creative_brief", "build_lock", "build_page_creative_brief", "build_page_prompt",
    "build_page_visual_intent", "canonicalize_intent", "compact_visual_structure_for_logic", "compile_page_prompt", "content_lock_text", "dataclass", "derive_page_semantics", "diagnostic_onscreen_text", "json", "load_page_missions",
    "load_page_visual_contexts", "load_page_visual_intent_overrides", "load_project_page_artifact_specs", "load_style_lock", "locked_onscreen_text", "main", "parse_script_markdown", "re", "render_artifact_prompt", "render_content_first_prompt",
    "render_content_first_style_contract", "render_creative_brief", "render_page_logic_contract", "render_presentation_contract", "render_prompt", "render_semantic_visual_brief", "render_visual_carrier_contract", "render_visual_center_contract", "resolve_composition", "resolve_default_style",
    "resolve_judgment_mode", "resolve_onscreen_judgment_mode", "resolve_page_semantic_intent", "resolve_page_visual_intent", "resolve_presentation_decision", "resolve_semantic_intent", "resolve_text_render_mode", "resolve_visual_carrier", "resolve_visual_center", "resolve_visual_medium",
    "select_dense_supporting_facts", "select_image_locked_text", "select_page_visual_intent_type", "select_visual_carrier", "stage_script", "strip_authoring_group_marker", "sys", "validate_composition", "validate_prompt_compiler", "validate_semantic_structure",
    "validate_text_render_mode", "validate_visual_carrier", "write_batch_diagnostics", "write_chapter_handoff", "write_compiler_comparison",
)

if __name__ == "__main__":
    raise SystemExit(main())
