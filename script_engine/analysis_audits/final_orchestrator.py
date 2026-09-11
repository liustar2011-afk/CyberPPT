"""Focused orchestration for the deterministic Final Script semantic audit."""
from __future__ import annotations

from ..onscreen_contracts import onscreen_alignment_advisories
from ..quality_policy import ADVISORY, classify_issue
from .common import *
from .composed_trace import (
    hard_finding_messages,
    identifier_review_messages,
    trace_composed,
)
from .final_authoring import (
    _audit_authored_content_coverage,
    _authored_bare_label_detail_issues,
    _author_execution_issues,
    _onscreen_expression_warnings,
    _slide_text,
)
from .final_deck import (
    _source_text_for_refs,
    _whole_deck_authoring_warnings,
)
from .final_lean import (
    _audit_lean_authored_source_consumption,
    _audit_lean_onscreen_full_copy_alignment,
    _audit_lean_onscreen_protected_retention,
    _audit_lean_relationship_visibility,
)
from .final_fidelity import (
    faithful_relation_promotion_issues,
    faithful_semantic_addition_issues,
)
from .final_onscreen import (
    _audit_authored_onscreen_composition,
    _audit_authored_onscreen_contract,
    _audit_self_reading_density,
)
from .onscreen_contract_heuristics import (
    onscreen_composition_hierarchy_review_findings,
    onscreen_contract_colocation_review_findings,
)


_MIGRATED_STRUCTURED_FINDING_CODES = frozenset(
    {
        "AUTHOR_SOURCE_CONSUMPTION_MISSING",
        "AUTHOR_SOURCE_REF_UNKNOWN",
        "AUTHOR_SOURCE_REF_OUTSIDE_PLAN_SCOPE",
        "AUTHOR_RELATIONSHIP_NOT_MATERIALIZED",
        "AUTHOR_NUMBER_OR_DATE_LOST",
        "AUTHOR_CONDITION_LOST",
        "AUTHOR_RESPONSIBILITY_LOST",
        "AUTHOR_ONSCREEN_NUMBER_OR_DATE_LOST",
        "AUTHOR_ONSCREEN_CONDITION_LOST",
        "AUTHOR_ONSCREEN_RESPONSIBILITY_LOST",
        "FAITHFUL_NUMBER_ADDED",
        "FAITHFUL_FORMAL_INSTRUMENT_ADDED",
    }
)


def _compatibility_findings(
    findings: list[str],
    *,
    compatibility_mode: bool,
) -> list[str]:
    """Suppress findings whose formal owner has moved to semantic_contract.

    Raw legacy callers use the default ``compatibility_mode=False`` and retain
    historical behavior. The single semantic entry calls this orchestrator in
    compatibility mode, where migrated structured findings are already emitted by
    their authoritative validators and must not be recomputed as a second owner.
    """

    if not compatibility_mode:
        return findings
    return [
        finding
        for finding in findings
        if not any(
            finding.startswith(f"{code}:")
            for code in _MIGRATED_STRUCTURED_FINDING_CODES
        )
    ]


def _append_governed_finding(
    issues: list[str],
    warnings: list[str],
    scope: str,
    finding: str,
) -> None:
    """Route one deterministic finding through the central Phase 3 registry.

    Unknown findings remain blocking by policy. Only codes explicitly registered
    as advisory can move to ``warnings``. Classify the raw finding before adding
    the slide scope so leading finding codes remain machine-readable.
    """

    target = warnings if classify_issue(finding)["severity"] == ADVISORY else issues
    target.append(f"{scope}: {finding}")


def _append_onscreen_alignment_finding(
    issues: list[str],
    warnings: list[str],
    scope: str,
    finding: str,
    *,
    compatibility_mode: bool,
) -> None:
    """Route legacy full-copy/onscreen alignment at the formal compatibility edge.

    A number that is visible onscreen but absent from ``full_copy`` is a layer
    consistency signal, not proof that the number is outside Foundation. In the
    formal path the Foundation source-boundary checks own that question, so this
    legacy condition becomes review-only. Raw legacy behavior remains unchanged.
    """

    code = "AUTHOR_ONSCREEN_PROTECTED_FACT_DRIFTED:"
    if compatibility_mode and finding.startswith(code):
        detail = finding[len(code):].strip()
        warnings.append(
            f"{scope}: LEGACY_ONSCREEN_PROTECTED_FACT_REVIEW_REQUIRED: {detail}; "
            "confirm the value against the cited Foundation evidence"
        )
        return
    _append_governed_finding(issues, warnings, scope, finding)


def audit_final_script(
    final_script: dict[str, Any],
    plan: dict[str, Any],
    foundation: dict[str, Any],
    *,
    compatibility_mode: bool = False,
) -> tuple[list[str], list[str]]:
    issues: list[str] = audit_final_internal_expert_voice(final_script, plan)
    warnings: list[str] = []
    composed_trace = trace_composed(final_script, foundation)
    if compatibility_mode:
        # Exact numeric source-boundary blocking is now owned by
        # semantic_contract.source_boundary. Keep only the heuristic identifier
        # discovery signal at this legacy compatibility edge.
        warnings.extend(identifier_review_messages(composed_trace))
    else:
        issues.extend(hard_finding_messages(composed_trace))
    items = foundation_items_by_id(foundation)
    pages = {p.get("id"): p for p in (plan.get("pages") or []) if isinstance(p, dict) and isinstance(p.get("id"), str)}
    audience_scope = plan.get("audience_scope", "unspecified")
    delivery_mode = str((final_script.get("deck") or {}).get("delivery_mode") or plan.get("delivery_mode") or "self_read")
    plan_authoring_mode = str(plan.get("authoring_mode") or "faithful")
    final_authoring_mode = str(
        (final_script.get("deck") or {}).get("authoring_mode") or plan_authoring_mode
    )

    warnings.extend(onscreen_alignment_advisories({
        **final_script, "deck": {**(final_script.get("deck") or {}), "authoring_mode": final_authoring_mode},
    }))

    for index, slide in enumerate(final_script.get("slides") or []):
        if not isinstance(slide, dict):
            continue
        slide_id = slide.get("id") or f"#{index}"
        scope = f"slides.{index} ({slide_id})"
        page = pages.get(slide_id)
        if page is None:
            warnings.append(f"{scope}: no matching deck-plan page; semantic inheritance cannot be audited")
            continue
        final_text = _slide_text(slide)
        plan_text = _page_text(page)
        page_source_refs = {
            ref for ref in page.get("source_refs") or [] if isinstance(ref, str) and ref
        }
        evidence_ids = _page_evidence_ids(page) | page_source_refs
        evidence = _support_items(sorted(evidence_ids), items)
        if final_authoring_mode == "faithful":
            for finding in faithful_relation_promotion_issues(slide, evidence):
                _append_governed_finding(issues, warnings, scope, finding)
            semantic_addition_findings = _compatibility_findings(
                faithful_semantic_addition_issues(slide, evidence, items),
                compatibility_mode=compatibility_mode,
            )
            for finding in semantic_addition_findings:
                _append_governed_finding(issues, warnings, scope, finding)

        plan_model = str((page.get("analysis_basis") or {}).get("model") or "").lower()
        plan_logic = str(page.get("logic") or "")
        plan_is_classification = any(token in plan_model for token in ("classification", "taxonomy", "typology")) or "分类" in plan_logic
        plan_allows_progression = bool(PROGRESSION_RE.search(plan_text) or any(token in plan_model for token in ("progression", "maturity")))
        if plan_is_classification and not plan_allows_progression and PROGRESSION_RE.search(final_text):
            _append_governed_finding(
                issues,
                warnings,
                scope,
                "FINAL_PROGRESSION_HEURISTIC: AUTHOR may have upgraded a classification/taxonomy plan "
                "into a progression chain; lexical progression markers require Critic review",
            )

        if _has_optionality(evidence) and not _preserves_optionality(final_text):
            _append_governed_finding(
                issues,
                warnings,
                scope,
                "FINAL_OPTIONALITY_HEURISTIC: final script may have lost source optionality; "
                "lexical independence/deepening markers require Critic review",
            )

        group_issue = _group_strength_issue(str(slide.get("core_message") or ""), evidence)
        if group_issue:
            _append_governed_finding(
                issues,
                warnings,
                scope,
                f"FINAL_GROUP_STRENGTH_HEURISTIC: {group_issue}",
            )

        internal = [item for item in evidence if effective_visibility(item) == "internal_only"]
        if audience_scope == "external" and internal:
            exposed_items: list[dict[str, Any]] = []
            for item in internal:
                item_text = _item_text(item)
                values = [str(item.get("value") or "")]
                for match in re.findall(r"\d+(?:\.\d+)?%?(?:至|-|—)\d+(?:\.\d+)?%?|\d+(?:\.\d+)?%", item_text):
                    values.append(match)
                normalized_final = final_text.replace("至", "-").replace("—", "-")
                if any(value and value.replace("至", "-").replace("—", "-") in normalized_final for value in values):
                    exposed_items.append(item)
            if exposed_items:
                if compatibility_mode:
                    marker_inferred = sorted(
                        {
                            str(item.get("id") or "?")
                            for item in exposed_items
                            if str(item.get("visibility") or "").strip() != "internal_only"
                        }
                    )
                    if marker_inferred:
                        warnings.append(
                            f"{scope}: legacy visibility review: text markers classify evidence "
                            f"{marker_inferred} as internal-only and matching values appear in "
                            "the external Final Script; confirm against explicit visibility policy"
                        )
                else:
                    exposed = sorted(
                        {str(item.get("id") or "?") for item in exposed_items}
                    )
                    issues.append(
                        f"{scope}: external final script exposes internal-only evidence {exposed}"
                    )

        if GAP_RE.search(final_text):
            source_text = _source_text_for_refs(page.get("source_refs") or [], foundation)
            if not GAP_RE.search(plan_text) and not GAP_RE.search(source_text):
                _append_governed_finding(
                    issues,
                    warnings,
                    scope,
                    "FINAL_GAP_HEURISTIC: final script may introduce a current-vs-target gap judgment "
                    "without the same lexical baseline in source or plan; Critic review is required",
                )

        if compatibility_mode:
            warnings.extend(
                f"{scope}: {finding}"
                for finding in onscreen_composition_hierarchy_review_findings(page, slide)
            )
        else:
            for finding in _audit_authored_onscreen_composition(
                page,
                slide,
                authoring_mode=final_authoring_mode,
            ):
                _append_governed_finding(issues, warnings, scope, finding)
        for finding in _audit_self_reading_density(delivery_mode, page, slide):
            _append_governed_finding(issues, warnings, scope, finding)
        if compatibility_mode:
            warnings.extend(
                f"{scope}: {finding}"
                for finding in onscreen_contract_colocation_review_findings(page, items)
            )
        else:
            for finding in _audit_authored_onscreen_contract(page, slide, items):
                _append_governed_finding(issues, warnings, scope, finding)
        source_consumption_findings = _compatibility_findings(
            _audit_lean_authored_source_consumption(page, slide, items, foundation),
            compatibility_mode=compatibility_mode,
        )
        for finding in source_consumption_findings:
            _append_governed_finding(issues, warnings, scope, finding)
        for finding in _audit_lean_onscreen_full_copy_alignment(slide):
            _append_onscreen_alignment_finding(
                issues,
                warnings,
                scope,
                finding,
                compatibility_mode=compatibility_mode,
            )
        retained_evidence = _support_items(slide.get("source_refs") or [], items)
        protected_retention_findings = _compatibility_findings(
            _audit_lean_onscreen_protected_retention(slide, retained_evidence, items),
            compatibility_mode=compatibility_mode,
        )
        for finding in protected_retention_findings:
            _append_governed_finding(issues, warnings, scope, finding)
        relationship_findings = _compatibility_findings(
            _audit_lean_relationship_visibility(slide),
            compatibility_mode=compatibility_mode,
        )
        for finding in relationship_findings:
            _append_governed_finding(issues, warnings, scope, finding)
        if not compatibility_mode:
            # Exact PLAN-declared meaning-signal retention is now owned by
            # semantic_contract.content_route on the formal path. Keep the raw
            # legacy implementation intact only for direct compatibility callers.
            for finding in _audit_authored_content_coverage(page, slide):
                _append_governed_finding(issues, warnings, scope, finding)
        for detail_issue in _authored_bare_label_detail_issues(page, slide, items):
            _append_governed_finding(
                issues,
                warnings,
                scope,
                f"ONSCREEN_SOURCE_DETAIL_COLLAPSED_TO_LABEL: {detail_issue}",
            )
        for finding in _author_execution_issues(
            delivery_mode,
            page,
            slide,
            items,
            authoring_mode=final_authoring_mode,
        ):
            _append_governed_finding(issues, warnings, scope, finding)
        warnings.extend(
            f"{scope}: {warning}"
            for warning in _onscreen_expression_warnings(page, slide)
        )

    warnings.extend(_whole_deck_authoring_warnings(final_script))
    return issues, warnings


__all__ = ["audit_final_script"]