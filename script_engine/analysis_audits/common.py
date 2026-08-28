"""Shared deterministic helpers for staged analysis audits."""
from __future__ import annotations
import re
from difflib import SequenceMatcher
from typing import Any
from cyberppt.content_route import audit_content_route, is_structural_page
from cyberppt.script_quality.common import _source_statement_overlap
from cyberppt.source_detail_visibility import (
    functional_group_needs_item_explanations,
    is_bare_business_label,
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

CITABLE_KEYS = ("facts", "concepts", "entities", "relations", "arguments", "constraints", "numbers")

SOURCE_CHAPTER_RE = re.compile(r"^S(\d+)(?:\.|$)")

INTERNAL_MARKERS = (
    "内部测算", "内部参考", "内部审批", "内部口径", "仅供内部", "内部使用",
    "内部经营测算", "内部价格", "内部比例",
)

OPTIONALITY_RE = re.compile(r"(可|可以).{0,12}独立(采用|选择|使用).{0,18}(也|并且|同时).{0,18}(逐步|随着).{0,12}(深化|加深|升级)")

INDEPENDENCE_RE = re.compile(r"(独立采用|独立选择|可独立|分别选择|按需选择|任选|自行选择)")

DEEPENING_RE = re.compile(r"(逐步深化|逐步加深|逐级深化|逐步升级|随着.{0,10}(成熟|合作).{0,10}(深化|加深)|由浅入深)")

UNIVERSAL_RE = re.compile(r"(均|全部|所有|每个|各.{0,8}均|都已|均已)")

CRITICAL_GROUP_TERMS = ("长期积累", "已完成", "已具备", "已形成", "已实现", "已建立", "已纳入")

PROGRESSION_RE = re.compile(
    r"(依次递进|逐级递进|单向递进|沿.{0,12}(链条|路径).{0,8}递进|"
    r"起点.{0,30}(进一步|再|随后)|在.{0,20}基础上.{0,20}(进一步|再)|"
    r"进一步加工|从.{0,20}逐步.{0,20}到|由浅入深|投入最低|投入最深|升级到更深)"
)

GAP_RE = re.compile(r"(当前|目前|现有).{0,30}(距离|距).{0,15}目标.{0,20}(很大|较大|明显|较多).{0,8}缺口|距离目标还有.{0,12}缺口")

CHAPTER_PREFIX_RE = re.compile(r"^第[一二三四五六七八九十百\d]+章[\s　]*")

_VISIBLE_CHAR_RE = re.compile(r"[一-鿿A-Za-z0-9]")

_PROPOSITION_END_RE = re.compile(r"[。！？!?]\s*$")

_EXPRESSION_MODES = {"phrase_led", "sentence_led", "mixed"}

_ONSCREEN_COMPOSITION_MODES = {"evidence_first", "selective_lead"}

_GENERIC_OMISSION_REASON_PHRASES = {"后续再说", "不重要", "暂不展开", "以后再说", "后续处理"}

_UNIT_DISPOSITIONS = {"full_copy", "onscreen", "reserved_for_later", "trace_only", "intentional_omission"}

_UNIT_REASON_REQUIRED_DISPOSITIONS = {"reserved_for_later", "intentional_omission"}

_EVIDENCE_FIT_VALUES = {"direct", "indirect", "topic_only", "no", "uncertain"}

_EVIDENCE_FIT_VERDICTS = {"keep", "rename", "move", "split", "reject"}

_LEAD_LIKE_EVIDENCE_ITEM_RE = re.compile(
    r"(?:需要|应当|应|须|用于|构成|提供|支撑|形成|明确|保持|覆盖|衔接|检验|"
    r"推动|进入|完成|面向|达到|对应|转化|可(?:以|用于))|"
    r"为.{0,18}(?:提供|形成|支撑|明确|转化)"
)

_COMPLETE_PROPOSITION_MIN_CHARS = 16

_COMPLETE_PROPOSITION_MAX_CHARS = 90

_SECONDARY_RELATION_TYPES = {"influence", "dependency", "feedback", "reference"}

def _normalized_review_text(value: object) -> str:
    return re.sub(r"[^一-鿿A-Za-z0-9]", "", str(value or "")).lower()

def foundation_items_by_id(foundation: dict[str, Any]) -> dict[str, dict[str, Any]]:
    items: dict[str, dict[str, Any]] = {}
    for key in CITABLE_KEYS:
        for item in foundation.get(key) or []:
            if isinstance(item, dict) and isinstance(item.get("id"), str):
                items[item["id"]] = item
    return items

def _item_text(item: dict[str, Any]) -> str:
    parts: list[str] = []
    for key in ("statement", "claim", "definition", "context", "strength", "term", "relation", "value", "unit"):
        value = item.get(key)
        if isinstance(value, str):
            parts.append(value)
    return " ".join(parts)

def effective_visibility(item: dict[str, Any]) -> str:
    text = _item_text(item)
    if any(marker in text for marker in INTERNAL_MARKERS):
        return "internal_only"
    value = item.get("visibility")
    return value if isinstance(value, str) and value else "external_ok"

def _support_items(ids: list[Any], items: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    return [items[x] for x in ids if isinstance(x, str) and x in items]

def _has_optionality(items: list[dict[str, Any]]) -> bool:
    return any(OPTIONALITY_RE.search(_item_text(item)) for item in items)

def _preserves_optionality(text: str) -> bool:
    return bool(INDEPENDENCE_RE.search(text) and DEEPENING_RE.search(text))

def _group_strength_issue(claim: str, support: list[dict[str, Any]]) -> str | None:
    if not support or not UNIVERSAL_RE.search(claim):
        return None
    for term in CRITICAL_GROUP_TERMS:
        if term not in claim:
            continue
        missing = [item.get("id", "?") for item in support if term not in _item_text(item)]
        if missing:
            return f"universal group claim uses '{term}' but support items {missing} do not all carry that source strength"
    return None

def _page_evidence_ids(page: dict[str, Any]) -> set[str]:
    evidence_ids: set[str] = set()
    proof = page.get("proof") or {}
    if isinstance(proof, dict):
        evidence_ids.update(x for x in (proof.get("evidence_refs") or []) if isinstance(x, str))
        evidence_ids.update(x for x in (proof.get("boundary_refs") or []) if isinstance(x, str))
    analysis_basis = page.get("analysis_basis") or {}
    if isinstance(analysis_basis, dict):
        evidence_ids.update(x for x in (analysis_basis.get("supports") or []) if isinstance(x, str))
    onscreen_contract = page.get("onscreen_contract") or {}
    if isinstance(onscreen_contract, dict):
        for module in onscreen_contract.get("modules") or []:
            if isinstance(module, dict):
                evidence_ids.update(
                    x for x in (module.get("evidence_refs") or []) if isinstance(x, str)
                )
    return evidence_ids

def _page_claim_evidence_ids(page: dict[str, Any]) -> set[str]:
    """Return evidence that supports the page judgment outside visible modules."""

    evidence_ids: set[str] = set()
    proof = page.get("proof") or {}
    if isinstance(proof, dict):
        evidence_ids.update(x for x in (proof.get("evidence_refs") or []) if isinstance(x, str))
        evidence_ids.update(x for x in (proof.get("boundary_refs") or []) if isinstance(x, str))
    analysis_basis = page.get("analysis_basis") or {}
    if isinstance(analysis_basis, dict):
        evidence_ids.update(x for x in (analysis_basis.get("supports") or []) if isinstance(x, str))
    return evidence_ids

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
    """Validate the semantic shape of an optional page-level onscreen contract.

    The JSON schema checks types and enums.  This pass checks the relationships that
    require the page's source evidence: module headings must be unique, module evidence
    IDs must exist, and a declared role rule must actually have patterns to enforce.
    """
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

def _source_consumption_sets(
    contract: dict[str, Any],
) -> tuple[set[str], set[str], set[str]]:
    detail_refs = {
        ref for ref in contract.get("detail_refs") or [] if isinstance(ref, str) and ref
    }
    omitted_refs = {
        ref
        for omission in contract.get("intentional_omissions") or []
        if isinstance(omission, dict)
        for ref in omission.get("source_refs") or []
        if isinstance(ref, str) and ref
    }
    onscreen_refs = {
        ref for ref in contract.get("onscreen_refs") or [] if isinstance(ref, str) and ref
    }
    return detail_refs, omitted_refs, onscreen_refs

def requires_source_consumption(
    page: dict[str, Any], foundation: dict[str, Any]
) -> bool:
    """Return whether the compiler-owned strict contract applies to a page."""

    return (
        foundation.get("source_consumption_policy") == "required"
        and bool([ref for ref in page.get("source_refs") or [] if isinstance(ref, str) and ref])
        and not is_structural_page(page)
    )

def _source_surface_values(item: dict[str, Any]) -> list[str]:
    values = [str(item.get("statement") or "").strip()]
    values.extend(
        str(unit.get("text") or "").strip()
        for unit in item.get("semantic_units") or []
        if isinstance(unit, dict)
    )
    values.extend(
        str(value).strip()
        for value in item.get("coverage_anchors") or []
        if isinstance(value, str)
    )
    return [value for value in values if value]

def _anchor_is_source_grounded(anchor: str, item: dict[str, Any]) -> bool:
    normalized_anchor = _normalized_review_text(anchor)
    return bool(normalized_anchor) and any(
        normalized_anchor in _normalized_review_text(surface)
        for surface in _source_surface_values(item)
    )

def _audit_source_consumption_definition(
    page: dict[str, Any], items: dict[str, dict[str, Any]], foundation: dict[str, Any]
) -> list[str]:
    """Validate the Foundation-governed source-to-prose-to-screen contract."""
    required = requires_source_consumption(page, foundation)
    contract = page.get("source_consumption")
    if contract is None:
        return (
            ["SOURCE_CONSUMPTION_CONTRACT_MISSING: strict sourced content page requires source_consumption"]
            if required
            else []
        )
    if not isinstance(contract, dict):
        return ["SOURCE_CONSUMPTION_CONTRACT_MISSING: source_consumption must be an object"]

    issues: list[str] = []
    if contract.get("mode") != "strict":
        issues.append("SOURCE_CONSUMPTION_MODE_INVALID: source_consumption.mode must be 'strict'")

    page_refs = {
        ref for ref in page.get("source_refs") or [] if isinstance(ref, str) and ref
    }
    detail_refs, omitted_refs, onscreen_refs = _source_consumption_sets(contract)
    declared_refs = detail_refs | omitted_refs | onscreen_refs
    anchor_refs: list[str] = []

    for omission_index, omission in enumerate(contract.get("intentional_omissions") or []):
        if not isinstance(omission, dict):
            issues.append(
                f"source_consumption.intentional_omissions[{omission_index}]: must be an object"
            )
            continue
        refs = [ref for ref in omission.get("source_refs") or [] if isinstance(ref, str) and ref]
        reason = str(omission.get("reason") or "").strip()
        if not refs:
            issues.append(
                f"source_consumption.intentional_omissions[{omission_index}]: source_refs is required"
            )
        if len(reason) < 8:
            issues.append(
                "SOURCE_CONSUMPTION_OMISSION_REASON_MISSING: "
                f"source_consumption.intentional_omissions[{omission_index}]: reason must contain at least 8 characters"
            )
        normalized_reason = _normalized_review_text(reason)
        if normalized_reason in _GENERIC_OMISSION_REASON_PHRASES:
            issues.append(
                "SOURCE_CONSUMPTION_OMISSION_REASON_MISSING: "
                f"source_consumption.intentional_omissions[{omission_index}]: reason must state a specific editorial boundary"
            )

    for anchor_index, anchor in enumerate(contract.get("full_prose_anchors") or []):
        if not isinstance(anchor, dict):
            issues.append(
                f"source_consumption.full_prose_anchors[{anchor_index}]: must be an object"
            )
            continue
        ref = anchor.get("source_ref")
        if not isinstance(ref, str) or not ref:
            issues.append(
                f"source_consumption.full_prose_anchors[{anchor_index}].source_ref is required"
            )
            continue
        anchor_refs.append(ref)
        declared_refs.add(ref)
        anchors = [
            value for value in anchor.get("anchors") or []
            if isinstance(value, str) and value.strip()
        ]
        minimum_hits = anchor.get("minimum_hits", len(anchors))
        if not anchors:
            issues.append(
                f"source_consumption.full_prose_anchors[{anchor_index}] ({ref}): anchors must be non-empty"
            )
        item = items.get(ref)
        if isinstance(item, dict):
            for value in anchors:
                if not _anchor_is_source_grounded(value, item):
                    issues.append(
                        "SOURCE_CONSUMPTION_ANCHOR_NOT_SOURCE_GROUNDED: "
                        f"source_consumption.full_prose_anchors[{anchor_index}] ({ref}): "
                        f"anchor '{value}' is absent from the Foundation source surface"
                    )
        if (
            not isinstance(minimum_hits, int)
            or isinstance(minimum_hits, bool)
            or minimum_hits < 1
            or minimum_hits > len(anchors)
        ):
            issues.append(
                f"source_consumption.full_prose_anchors[{anchor_index}] ({ref}): minimum_hits must be between 1 and the number of anchors"
            )

    duplicate_anchor_refs = sorted({ref for ref in anchor_refs if anchor_refs.count(ref) > 1})
    if duplicate_anchor_refs:
        issues.append(
            f"source_consumption.full_prose_anchors: duplicate source_ref entries {duplicate_anchor_refs}"
        )

    outside = sorted(declared_refs - page_refs)
    if outside:
        issues.append(
            "SOURCE_CONSUMPTION_REF_OUTSIDE_PAGE: source_consumption declared refs "
            f"must belong to page.source_refs; outside refs {outside}"
        )
    unknown = sorted(ref for ref in page_refs if ref not in items)
    if unknown:
        issues.append(f"source_consumption: page.source_refs contain unknown foundation refs {unknown}")

    conflicts = {
        "detail/omitted": detail_refs & omitted_refs,
        "detail/onscreen": detail_refs & onscreen_refs,
        "omitted/onscreen": omitted_refs & onscreen_refs,
        "anchor/detail": set(anchor_refs) & detail_refs,
        "anchor/omitted": set(anchor_refs) & omitted_refs,
    }
    for label, refs in conflicts.items():
        if refs:
            issues.append(
                "SOURCE_CONSUMPTION_REF_CONFLICT: source_consumption refs cannot be both "
                f"{label.replace('/', ' and ')} {sorted(refs)}"
            )

    if required and contract.get("mode") == "strict":
        required_refs = page_refs - detail_refs - omitted_refs
        missing_anchor_refs = sorted(required_refs - set(anchor_refs))
        if missing_anchor_refs:
            issues.append(
                "SOURCE_CONSUMPTION_ANCHOR_MISSING: every full-copy source requires "
                f"full_prose_anchors; missing refs {missing_anchor_refs}"
            )
        if not onscreen_refs:
            issues.append(
                "SOURCE_CONSUMPTION_ONSCREEN_SELECTION_MISSING: strict sourced content page "
                "requires at least one representative onscreen_ref"
            )

    if onscreen_refs:
        onscreen_contract = page.get("onscreen_contract")
        if not isinstance(onscreen_contract, dict):
            issues.append(
                "SOURCE_CONSUMPTION_ONSCREEN_MAPPING_MISSING: "
                "source_consumption.onscreen_refs requires an onscreen_contract"
            )
        else:
            mapped_refs = {
                ref
                for module in onscreen_contract.get("modules") or []
                if isinstance(module, dict)
                for ref in module.get("evidence_refs") or []
                if isinstance(ref, str) and ref
            }
            unmapped = sorted(onscreen_refs - mapped_refs)
            if unmapped:
                issues.append(
                    "SOURCE_CONSUMPTION_ONSCREEN_MAPPING_MISSING: "
                    "source_consumption.onscreen_refs must be mapped by "
                    f"onscreen_contract.modules[].evidence_refs; unmapped refs {unmapped}"
                )
    return issues

def _record_unit_ids(ref: str, item: dict[str, Any]) -> set[str]:
    """Stable per-unit identifiers, synthesized positionally when Source Truth didn't
    assign one. Foundation projection is a deliberately pure mechanical copy (see
    ``cyberppt/foundation_projection.py``) and must not write new fields onto Source
    Truth data, so this identifier is derived at audit time rather than persisted."""
    return {
        str(unit.get("id") or "").strip() or f"{ref}#{index}"
        for index, unit in enumerate(item.get("semantic_units") or [])
        if isinstance(unit, dict)
    }

def _audit_unit_consumption_definition(
    page: dict[str, Any], items: dict[str, dict[str, Any]], foundation: dict[str, Any]
) -> list[str]:
    """Validate per-semantic-unit consumption disposition.

    Contract version 2 makes the disposition array mandatory for strict
    sourced pages. Historical foundations without that version retain the
    optional behavior, so migration happens only when project-foundation is
    explicitly rerun.
    """
    if not requires_source_consumption(page, foundation):
        return []
    contract = page.get("source_consumption")
    if not isinstance(contract, dict):
        return []
    dispositions = contract.get("unit_dispositions")
    if dispositions is None:
        return (
            [
                "SOURCE_CONSUMPTION_UNIT_CONTRACT_MISSING: "
                "source_consumption.unit_dispositions is required by "
                "source_consumption_contract_version=2"
            ]
            if foundation.get("source_consumption_contract_version") == 2
            else []
        )
    if not isinstance(dispositions, list):
        return ["source_consumption.unit_dispositions: must be an array"]

    detail_refs, omitted_refs, _onscreen_refs = _source_consumption_sets(contract)
    page_refs = {ref for ref in page.get("source_refs") or [] if isinstance(ref, str) and ref}
    required_refs = page_refs - detail_refs - omitted_refs

    issues: list[str] = []
    declared: set[tuple[str, str]] = set()
    for index, entry in enumerate(dispositions):
        if not isinstance(entry, dict):
            issues.append(f"source_consumption.unit_dispositions[{index}]: must be an object")
            continue
        ref = str(entry.get("source_ref") or "").strip()
        unit_id = str(entry.get("unit_id") or "").strip()
        disposition = entry.get("disposition")
        if not ref or not unit_id:
            issues.append(
                f"source_consumption.unit_dispositions[{index}]: source_ref and unit_id are required"
            )
            continue
        item = items.get(ref)
        if not isinstance(item, dict) or unit_id not in _record_unit_ids(ref, item):
            issues.append(
                "SOURCE_CONSUMPTION_UNIT_UNKNOWN: "
                f"source_consumption.unit_dispositions[{index}] ({ref}#{unit_id}): "
                "unit_id not found in the Foundation record's semantic_units"
            )
            continue
        if disposition not in _UNIT_DISPOSITIONS:
            issues.append(
                f"source_consumption.unit_dispositions[{index}] ({ref}#{unit_id}): "
                f"disposition must be one of {sorted(_UNIT_DISPOSITIONS)}"
            )
            continue
        if disposition in _UNIT_REASON_REQUIRED_DISPOSITIONS:
            reason = str(entry.get("reason") or "").strip()
            if len(reason) < 8 or _normalized_review_text(reason) in _GENERIC_OMISSION_REASON_PHRASES:
                issues.append(
                    "SOURCE_CONSUMPTION_UNIT_REASON_MISSING: "
                    f"source_consumption.unit_dispositions[{index}] ({ref}#{unit_id}): "
                    "reserved_for_later/intentional_omission requires a specific reason of at least 8 characters"
                )
        declared.add((ref, unit_id))

    for ref in sorted(required_refs):
        item = items.get(ref)
        if not isinstance(item, dict):
            continue
        for unit_id in sorted(_record_unit_ids(ref, item)):
            if (ref, unit_id) not in declared:
                issues.append(
                    "SOURCE_CONSUMPTION_UNIT_MISSING: "
                    "source_consumption.unit_dispositions must cover every semantic unit of a "
                    f"full-copy source; missing {ref}#{unit_id}"
                )
    return issues

def _audit_onscreen_composition_definition(page: dict[str, Any]) -> list[str]:
    """Validate an optional page-level module-lead policy.

    This is deliberately independent from ``onscreen_contract.expression_mode``.
    The latter describes the language form of visible copy; this policy decides
    whether individual modules may carry a lead at all.
    """
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

def _page_text(page: dict[str, Any]) -> str:
    parts: list[str] = []
    for key in ("title", "question", "message", "logic", "next", "receives"):
        value = page.get(key)
        if isinstance(value, str):
            parts.append(value)
    for key in ("content", "must_include", "reserved_for_later"):
        for value in page.get(key) or []:
            if isinstance(value, str):
                parts.append(value)
    analysis_basis = page.get("analysis_basis") or {}
    if isinstance(analysis_basis, dict):
        for key in ("model", "relation_basis", "confidence"):
            value = analysis_basis.get(key)
            if isinstance(value, str):
                parts.append(value)
    return " ".join(parts)

__all__ = ['annotations', 're', 'SequenceMatcher', 'Any', 'audit_content_route', '_source_statement_overlap', 'functional_group_needs_item_explanations', 'is_bare_business_label', 'source_has_richer_item_detail', 'source_colocation_grouping_mismatch', 'audit_authored_stage02_readiness', 'audit_stage02_readiness', 'audit_final_internal_expert_voice', 'audit_plan_internal_expert_voice', 'CITABLE_KEYS', 'SOURCE_CHAPTER_RE', 'INTERNAL_MARKERS', 'OPTIONALITY_RE', 'INDEPENDENCE_RE', 'DEEPENING_RE', 'UNIVERSAL_RE', 'CRITICAL_GROUP_TERMS', 'PROGRESSION_RE', 'GAP_RE', 'CHAPTER_PREFIX_RE', '_VISIBLE_CHAR_RE', '_PROPOSITION_END_RE', '_EXPRESSION_MODES', '_ONSCREEN_COMPOSITION_MODES', '_EVIDENCE_FIT_VALUES', '_EVIDENCE_FIT_VERDICTS', '_LEAD_LIKE_EVIDENCE_ITEM_RE', '_COMPLETE_PROPOSITION_MIN_CHARS', '_COMPLETE_PROPOSITION_MAX_CHARS', '_SECONDARY_RELATION_TYPES', '_normalized_review_text', 'foundation_items_by_id', '_item_text', 'effective_visibility', '_support_items', '_has_optionality', '_preserves_optionality', '_group_strength_issue', '_page_evidence_ids', '_page_claim_evidence_ids', '_evidence_fit_review_issues', '_audit_evidence_fit_reviews', '_onscreen_contract_definition_issues', '_source_consumption_sets', 'requires_source_consumption', '_source_surface_values', '_anchor_is_source_grounded', '_audit_source_consumption_definition', '_record_unit_ids', '_audit_unit_consumption_definition', '_audit_onscreen_composition_definition', '_page_text']
