"""Compatibility facade for shared deterministic analysis audit helpers."""
from __future__ import annotations

import re
from difflib import SequenceMatcher
from typing import Any

from cyberppt.content_route import audit_content_route, is_structural_page
from cyberppt.script_quality.common import _source_statement_overlap
from cyberppt.source_detail_visibility import (
    functional_group_needs_item_explanations,
    is_bare_business_label,
    label_enumeration_collapses_richer_detail,
    source_has_richer_item_detail,
)
from cyberppt.semantic_group_review import source_colocation_grouping_mismatch
from cyberppt.stage02_readiness import (
    audit_authored_stage02_readiness,
    audit_stage02_readiness,
)
from ..internal_report_voice import (
    audit_final_internal_expert_voice,
    audit_plan_internal_expert_voice,
)
from .common_primitives import *
from .common_contracts import *


__all__ = ['annotations', 're', 'SequenceMatcher', 'Any', 'audit_content_route', '_source_statement_overlap', 'functional_group_needs_item_explanations', 'is_bare_business_label', 'label_enumeration_collapses_richer_detail', 'source_has_richer_item_detail', 'source_colocation_grouping_mismatch', 'audit_authored_stage02_readiness', 'audit_stage02_readiness', 'audit_final_internal_expert_voice', 'audit_plan_internal_expert_voice', 'CITABLE_KEYS', 'SOURCE_CHAPTER_RE', 'INTERNAL_MARKERS', 'OPTIONALITY_RE', 'INDEPENDENCE_RE', 'DEEPENING_RE', 'UNIVERSAL_RE', 'CRITICAL_GROUP_TERMS', 'PROGRESSION_RE', 'GAP_RE', 'CHAPTER_PREFIX_RE', '_VISIBLE_CHAR_RE', '_PROPOSITION_END_RE', '_EXPRESSION_MODES', '_ONSCREEN_COMPOSITION_MODES', '_EVIDENCE_FIT_VALUES', '_EVIDENCE_FIT_VERDICTS', '_LEAD_LIKE_EVIDENCE_ITEM_RE', '_COMPLETE_PROPOSITION_MIN_CHARS', '_COMPLETE_PROPOSITION_MAX_CHARS', '_SECONDARY_RELATION_TYPES', '_normalized_review_text', 'foundation_items_by_id', '_item_text', 'effective_visibility', '_support_items', '_has_optionality', '_preserves_optionality', '_group_strength_issue', '_page_evidence_ids', '_page_claim_evidence_ids', '_evidence_fit_review_issues', '_audit_evidence_fit_reviews', '_onscreen_contract_definition_issues', 'requires_source_consumption', '_source_surface_values', '_audit_onscreen_composition_definition', '_page_text']
