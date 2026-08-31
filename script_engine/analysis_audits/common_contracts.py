"""Higher-level PLAN/onscreen contract validators shared by analysis audits."""
from __future__ import annotations

import re
from typing import Any

from cyberppt.semantic_group_review import source_colocation_grouping_mismatch

from .common_primitives import (
    _EVIDENCE_FIT_VALUES,
    _EVIDENCE_FIT_VERDICTS,
    _EXPRESSION_MODES,
    _ONSCREEN_COMPOSITION_MODES,
    _item_text,
    _normalized_review_text,
    _page_claim_evidence_ids,
)


def _evidence_fit_review_issues(
    review: object,
    *,
    expected_refs: set[str],
    items: dict[str, dict[str, Any]],
    context: str,
    require_direct: bool,
    allow_indirect: bool,
    expected_question: object | None = None,
) -> list[str]:
    """Validate source-bound PLAN self-review without trusting its verdict alone."""
    if not expected_refs:
        return []
    if not isinstance(review, dict):
        return [f"{context}.evidence_fit_review is required in strict mode"]

    issues: list[str] = []
    question = str(review.get("question") or "").strip()
    if not question:
        issues.append(f"{context}.evidence_fit_review.question is required")
    elif expected_question is not None and _normalized_review_text(question) != _normalized_review_text(expected_question):
        issues.append(
            f"{context}.evidence_fit_review.question must match the page question so evidence is reviewed against the actual page mission"
        )

    verdict = str(review.get("verdict") or "").strip()
    if verdict not in _EVIDENCE_FIT_VERDICTS:
        issues.append(
            f"{context}.evidence_fit_review.verdict must be one of {sorted(_EVIDENCE_FIT_VERDICTS)}"
        )
    elif verdict != "keep":
        issues.append(
            f"{context}.evidence_fit_review.verdict='{verdict}' requires PLAN repair before AUTHOR"
        )

    review_items = [entry for entry in review.get("items") or [] if isinstance(entry, dict)]
    reviewed_refs = [str(entry.get("evidence_ref") or "").strip() for entry in review_items]
    nonempty_refs = [ref for ref in reviewed_refs if ref]
    duplicates = sorted({ref for ref in nonempty_refs if nonempty_refs.count(ref) > 1})
    if duplicates:
        issues.append(f"{context}.evidence_fit_review has duplicate evidence_refs {duplicates}")
    missing = sorted(expected_refs - set(nonempty_refs))
    extra = sorted(set(nonempty_refs) - expected_refs)
    if missing:
        issues.append(f"{context}.evidence_fit_review is missing evidence_refs {missing}")
    if extra:
        issues.append(f"{context}.evidence_fit_review reviews unassigned evidence_refs {extra}")

    for item_index, entry in enumerate(review_items):
        ref = str(entry.get("evidence_ref") or "").strip()
        fit = str(entry.get("fit") or "").strip()
        role = str(entry.get("role") or "").strip()
        reason = str(entry.get("reason") or "").strip()
        item_context = f"{context}.evidence_fit_review.items[{item_index}] ({ref or '?'})"
        if ref and ref not in items:
            issues.append(f"{item_context}: unknown evidence_ref")
        if fit not in _EVIDENCE_FIT_VALUES:
            issues.append(f"{item_context}: invalid fit '{fit}'")
        elif fit in {"no", "uncertain"}:
            issues.append(f"{item_context}: fit='{fit}' requires PLAN repair before AUTHOR")
        elif fit == "topic_only":
            issues.append(f"{item_context}: topic_only evidence cannot support the current page or module claim")
        elif require_direct and fit != "direct":
            issues.append(f"{item_context}: module evidence must answer its parent question directly")
        elif fit == "indirect" and not allow_indirect:
            issues.append(
                f"{item_context}: indirect evidence requires an inferred relation_basis with explicit support"
            )
        if not role:
            issues.append(f"{item_context}: role is required")
        if not reason:
            issues.append(f"{item_context}: reason is required")
    return issues


def _audit_evidence_fit_reviews(
    page: dict[str, Any],
    items: dict[str, dict[str, Any]],
    *,
    strict: bool,
) -> list[str]:
    if not strict:
        return []

    issues: list[str] = []
    analysis = page.get("analysis_basis") if isinstance(page.get("analysis_basis"), dict) else {}
    proof = page.get("proof") if isinstance(page.get("proof"), dict) else {}
    inferred = analysis.get("relation_basis") == "inferred" or proof.get("relation_basis") == "inferred"
    issues.extend(
        _evidence_fit_review_issues(
            page.get("evidence_fit_review"),
            expected_refs=_page_claim_evidence_ids(page),
            items=items,
            context="page",
            require_direct=False,
            allow_indirect=inferred,
            expected_question=page.get("question"),
        )
    )

    contract = page.get("onscreen_contract")
    if not isinstance(contract, dict):
        return issues
    for module_index, module in enumerate(contract.get("modules") or []):
        if not isinstance(module, dict):
            continue
        refs = {ref for ref in module.get("evidence_refs") or [] if isinstance(ref, str) and ref}
        issues.extend(
            _evidence_fit_review_issues(
                module.get("evidence_fit_review"),
                expected_refs=refs,
                items=items,
                context=f"onscreen_contract.modules[{module_index}] ({module.get('heading') or '?'})",
                require_direct=True,
                allow_indirect=False,
            )
        )
    return issues


def _onscreen_contract_definition_issues(
    page: dict[str, Any], contract: dict[str, Any], items: dict[str, dict[str, Any]]
) -> list[str]:
    """Validate the semantic shape of an optional page-level onscreen contract."""
    issues: list[str] = []
    relation = str(contract.get("relation") or "").strip()
    if relation == "parallel" and len(contract.get("modules") or []) < 2:
        issues.append("onscreen_contract.relation='parallel' requires at least two modules")

    expression_mode = contract.get("expression_mode")
    if (
        expression_mode is not None
        and (
            not isinstance(expression_mode, str)
            or expression_mode not in _EXPRESSION_MODES
        )
    ):
        issues.append(
            "onscreen_contract.expression_mode must be one of: phrase_led, sentence_led, mixed"
        )

    modules = [module for module in contract.get("modules") or [] if isinstance(module, dict)]
    headings: list[str] = []
    for module_index, module in enumerate(modules):
        heading = str(module.get("heading") or "").strip()
        if not heading:
            issues.append(f"onscreen_contract.modules[{module_index}].heading is required")
        elif heading in headings:
            issues.append(f"onscreen_contract.modules[{module_index}]: duplicate heading '{heading}'")
        headings.append(heading)

        refs = [ref for ref in module.get("evidence_refs") or [] if isinstance(ref, str)]
        if not refs:
            issues.append(f"onscreen_contract.modules[{module_index}] ({heading or '?'}) has no evidence_refs")
        unknown = [ref for ref in refs if ref not in items]
        if unknown:
            issues.append(
                f"onscreen_contract.modules[{module_index}] ({heading or '?'}): unknown evidence_refs {unknown}"
            )
        mismatch = source_colocation_grouping_mismatch(
            heading,
            (
                (ref, _item_text(items[ref]), items[ref].get("source_refs") or [])
                for ref in refs
                if ref in items
            ),
        )
        if mismatch:
            issues.append(
                "ONSCREEN_SOURCE_COLOCATION_AS_HIERARCHY: onscreen_contract.modules"
                f"[{module_index}] ({heading or '?'}): action/application evidence "
                f"{list(mismatch.action_refs)} and institutional evidence "
                f"{list(mismatch.institution_refs)} share a source location but do not "
                "form one narrow institutional taxonomy; rename the parent to a supported "
                "policy-requirement umbrella or move/split the action item; shared source "
                f"locations={list(mismatch.shared_source_refs)}"
            )
        signals = [signal for signal in module.get("required_signals") or [] if isinstance(signal, str) and signal]
        if not signals:
            issues.append(
                f"onscreen_contract.modules[{module_index}] ({heading or '?'}): requires at least one required_signals entry"
            )

    policy = contract.get("detail_policy") or {}
    if isinstance(policy, dict):
        markers = policy.get("role_markers") or {}
        if isinstance(markers, dict):
            for role in policy.get("forbidden_roles") or []:
                if role not in markers:
                    issues.append(
                        f"onscreen_contract.detail_policy: forbidden role '{role}' has no role_markers"
                    )
            for role in policy.get("allowed_roles") or []:
                if role not in markers:
                    issues.append(
                        f"onscreen_contract.detail_policy: allowed role '{role}' has no role_markers"
                    )
            for role, patterns in markers.items():
                if not isinstance(role, str) or not isinstance(patterns, list) or not patterns:
                    issues.append(
                        f"onscreen_contract.detail_policy.role_markers.{role}: requires a non-empty pattern list"
                    )
                    continue
                for pattern in patterns:
                    if not isinstance(pattern, str) or not pattern:
                        issues.append(
                            f"onscreen_contract.detail_policy.role_markers.{role}: patterns must be non-empty strings"
                        )
                        continue
                    try:
                        re.compile(pattern)
                    except re.error as error:
                        issues.append(
                            f"onscreen_contract.detail_policy.role_markers.{role}: invalid regex '{pattern}': {error}"
                        )
        for pattern in policy.get("forbidden_patterns") or []:
            if not isinstance(pattern, str) or not pattern:
                issues.append("onscreen_contract.detail_policy.forbidden_patterns: patterns must be non-empty strings")
                continue
            try:
                re.compile(pattern)
            except re.error as error:
                issues.append(
                    f"onscreen_contract.detail_policy.forbidden_patterns: invalid regex '{pattern}': {error}"
                )
    return issues


def _audit_onscreen_composition_definition(page: dict[str, Any]) -> list[str]:
    """Validate an optional page-level module-lead policy."""
    composition = page.get("onscreen_composition")
    if composition is None:
        return []
    if not isinstance(composition, dict):
        return ["onscreen_composition: must be an object"]

    issues: list[str] = []
    mode = composition.get("mode")
    if mode not in _ONSCREEN_COMPOSITION_MODES:
        issues.append(
            "onscreen_composition.mode: must be 'evidence_first' or 'selective_lead'"
        )
        return issues

    lead_budget = composition.get("lead_budget")
    if mode == "evidence_first":
        if lead_budget not in (None, 0):
            issues.append(
                "onscreen_composition='evidence_first' requires lead_budget to be omitted or 0"
            )
    elif not isinstance(lead_budget, int) or isinstance(lead_budget, bool) or lead_budget < 1:
        issues.append(
            "onscreen_composition='selective_lead' requires a positive integer lead_budget"
        )
    return issues


__all__ = [
    "_evidence_fit_review_issues",
    "_audit_evidence_fit_reviews",
    "_onscreen_contract_definition_issues",
    "_audit_onscreen_composition_definition",
]
