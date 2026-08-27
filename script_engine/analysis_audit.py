"""Deterministic audit helpers for source fidelity and analytical inference."""
from __future__ import annotations

import re
from difflib import SequenceMatcher
from typing import Any

from cyberppt.content_route import audit_content_route
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
from .internal_report_voice import (
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
_EVIDENCE_FIT_VALUES = {"direct", "indirect", "topic_only", "no", "uncertain"}
_EVIDENCE_FIT_VERDICTS = {"keep", "rename", "move", "split", "reject"}
_LEAD_LIKE_EVIDENCE_ITEM_RE = re.compile(
    r"(?:需要|应当|应|须|用于|构成|提供|支撑|形成|明确|保持|覆盖|衔接|检验|"
    r"推动|进入|完成|面向|达到|对应|转化|可(?:以|用于))|"
    r"为.{0,18}(?:提供|形成|支撑|明确|转化)"
)
_COMPLETE_PROPOSITION_MIN_CHARS = 16
_COMPLETE_PROPOSITION_MAX_CHARS = 90


def _normalized_review_text(value: object) -> str:
    return re.sub(r"[^一-鿿A-Za-z0-9]", "", str(value or "")).lower()


def _adjacent_plan_duplication_warnings(plan: dict[str, Any]) -> list[str]:
    """Flag only high-confidence near duplication; shared terminology is valid."""

    pages = [page for page in plan.get("pages") or [] if isinstance(page, dict)]
    warnings: list[str] = []
    for previous, current in zip(pages, pages[1:]):
        previous_message = _normalized_review_text(previous.get("message"))
        current_message = _normalized_review_text(current.get("message"))
        if min(len(previous_message), len(current_message)) < 12:
            continue
        similarity = SequenceMatcher(None, previous_message, current_message).ratio()
        if similarity >= 0.90:
            warnings.append(
                "adjacent pages {left} and {right} have near-duplicate core messages "
                "(similarity {similarity:.0%}); verify that each page has a distinct proof responsibility".format(
                    left=previous.get("id") or "?",
                    right=current.get("id") or "?",
                    similarity=similarity,
                )
            )
    for page in pages:
        title = _normalized_review_text(page.get("title"))
        message = _normalized_review_text(page.get("message"))
        if title and len(title) >= 8 and title == message:
            warnings.append(
                f"page {page.get('id') or '?'} repeats the same text as title and core message; "
                "verify the title-message hierarchy"
            )
    return warnings


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


def _scope_chapters(source_scope: list[Any]) -> set[int]:
    chapters: set[int] = set()
    for ref in source_scope:
        if isinstance(ref, str):
            match = SOURCE_CHAPTER_RE.match(ref)
            if match:
                chapters.add(int(match.group(1)))
    return chapters


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

    counter_case = str(review.get("counter_case") or "").strip()
    if len(_normalized_review_text(counter_case)) < 4 or _normalized_review_text(counter_case) in {
        "无", "没有", "暂无", "不适用", "无反例",
    }:
        issues.append(
            f"{context}.evidence_fit_review.counter_case must state a concrete alternative grouping, boundary, or strongest counter-case"
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


def _onscreen_module_lines(module: dict[str, Any]) -> list[str]:
    lines: list[str] = []
    text = module.get("text")
    if isinstance(text, str) and text.strip():
        lines.append(text.strip())
    for item in module.get("items") or []:
        if isinstance(item, str) and item.strip():
            lines.append(item.strip())
    return lines


def _is_lead_like_evidence_item(value: str) -> bool:
    """Identify a proposition-shaped item that can shadow a forbidden lead.

    Evidence-first pages may still contain complete factual statements. The
    relevant failure mode is narrower: a broad proposition appears only as the
    first item while lighter sibling facts follow at the same rendered level.
    """
    return (
        len(_VISIBLE_CHAR_RE.findall(value)) >= _COMPLETE_PROPOSITION_MIN_CHARS
        and bool(_LEAD_LIKE_EVIDENCE_ITEM_RE.search(value))
    )


def _evidence_first_item_hierarchy_issues(
    slide_id: str, module: dict[str, Any]
) -> list[str]:
    """Reject a hidden module lead placed in the first flat evidence item."""
    items = [
        item.strip()
        for item in module.get("items") or []
        if isinstance(item, str) and item.strip()
    ]
    if len(items) < 2 or not _is_lead_like_evidence_item(items[0]):
        return []
    if all(_is_lead_like_evidence_item(item) for item in items[1:]):
        return []
    heading = str(module.get("heading") or "?").strip()
    return [
        f"{slide_id}: onscreen_composition='evidence_first' module '{heading}' "
        "uses a lead-like first item above lighter peer evidence; rewrite every item "
        "as same-granularity source facts, or use selective_lead when the judgment "
        "must remain inside the module"
    ]


def _is_readable_proposition(line: str) -> bool:
    """Return whether a visible line carries a compact, sentence-like proposition."""
    value = str(line or "").strip()
    if not value or re.search(r"[：:]", value) or not _PROPOSITION_END_RE.search(value):
        return False
    chars = len(_VISIBLE_CHAR_RE.findall(value))
    return _COMPLETE_PROPOSITION_MIN_CHARS <= chars <= _COMPLETE_PROPOSITION_MAX_CHARS


def _onscreen_expression_warnings(
    page: dict[str, Any], slide: dict[str, Any],
) -> list[str]:
    """Advisory checks for a declared sentence-led or mixed visible expression mode."""
    contract = page.get("onscreen_contract")
    if not isinstance(contract, dict) or "expression_mode" not in contract:
        return []
    mode = str(contract.get("expression_mode") or "").strip()
    if mode not in {"sentence_led", "mixed"}:
        return []

    modules = [module for module in slide.get("onscreen") or [] if isinstance(module, dict)]
    if mode == "sentence_led":
        warnings = []
        for module in modules:
            heading = str(module.get("heading") or "?").strip()
            lines = _onscreen_module_lines(module)
            if not any(_is_readable_proposition(line) for line in lines):
                warnings.append(
                    f"module '{heading}': expression_mode='sentence_led' has no readable proposition; "
                    "add one source-grounded sentence with a subject, predicate and terminal punctuation"
                )
        return warnings

    lines = [line for module in modules for line in _onscreen_module_lines(module)]
    if lines and not any(_is_readable_proposition(line) for line in lines):
        return [
            "expression_mode='mixed' contains no readable proposition; "
            "combine compact evidence phrases with at least one source-grounded sentence"
        ]
    return []


def _authored_bare_label_detail_issues(
    page: dict[str, Any],
    slide: dict[str, Any],
    items: dict[str, dict[str, Any]],
) -> list[str]:
    """Keep source detail and role-bearing payload attached to visible labels."""

    contract = page.get("onscreen_contract")
    contract = contract if isinstance(contract, dict) else {}
    detail_policy = contract.get("detail_policy")
    detail_policy = detail_policy if isinstance(detail_policy, dict) else {}
    label_only_allowed = detail_policy.get("label_only_allowed") is True
    contract_modules = {
        str(module.get("heading") or "").strip(): module
        for module in contract.get("modules") or []
        if isinstance(module, dict) and str(module.get("heading") or "").strip()
    }
    page_evidence_ids = _page_evidence_ids(page)
    issues: list[str] = []
    for module_index, module in enumerate(slide.get("onscreen") or []):
        if not isinstance(module, dict):
            continue
        heading = str(module.get("heading") or "").strip()
        visible_items = [
            str(value).strip()
            for value in module.get("items") or []
            if isinstance(value, str) and value.strip()
        ]
        if not visible_items:
            continue
        module_contract = contract_modules.get(heading, {})
        evidence_ids = {
            str(value)
            for value in module_contract.get("evidence_refs") or []
            if str(value)
        } or page_evidence_ids
        source_statements = [
            _item_text(items[item_id])
            for item_id in evidence_ids
            if item_id in items
        ]
        collapsed = [
            value
            for value in visible_items
            if is_bare_business_label(value)
            and source_has_richer_item_detail(value, source_statements)
        ]
        role_only = functional_group_needs_item_explanations(
            heading,
            visible_items,
            content_load=page.get("content_load"),
            label_only_allowed=label_only_allowed,
        )
        if collapsed or role_only:
            labels = collapsed or [
                value for value in visible_items if is_bare_business_label(value)
            ]
            issues.append(
                "onscreen module {index} '{heading}' collapses source-backed or role-bearing "
                "details into bare labels {labels}; write '标签：来源支持的对象、作用、任务或边界' "
                "without terminal punctuation. Use detail_policy.label_only_allowed=true only "
                "when the approved source intentionally provides a label-only taxonomy".format(
                    index=module_index,
                    heading=heading or "?",
                    labels=labels,
                )
            )
    return issues


def _audit_content_coverage_definition(page: dict[str, Any]) -> list[str]:
    """Ensure an explicit internal-report route has evidence and meaning duties.

    This replaces character and module-count proxies. The audit only checks
    obligations the page author already declared in its route and visible-module
    contract; it never asks a sparse, source-native page to add filler.
    """

    route = page.get("content_route")
    if not isinstance(route, dict) or str(route.get("primary") or "") == "source_native":
        return []
    issues: list[str] = []
    if not _page_evidence_ids(page):
        issues.append(
            "explicit content_route has no declared source evidence; add source_refs, proof evidence_refs, "
            "analysis supports, or onscreen_contract module evidence_refs"
        )
    facets = {
        str(value).strip()
        for value in route.get("facets") or []
        if isinstance(value, str) and value.strip()
    }
    if facets.intersection({"risk", "coordination", "next_step"}) and not [
        value for value in route.get("meaning_signals") or []
        if isinstance(value, str) and value.strip()
    ]:
        issues.append(
            "content_route facets require one or more meaning_signals that must remain visible in final copy"
        )
    return issues


def _audit_authored_content_coverage(page: dict[str, Any], slide: dict[str, Any]) -> list[str]:
    route = page.get("content_route")
    if not isinstance(route, dict):
        return []
    visible = re.sub(r"\s+", "", _slide_text(slide))
    slide_id = str(slide.get("id") or page.get("id") or "?")
    issues: list[str] = []
    for signal in route.get("meaning_signals") or []:
        if isinstance(signal, str) and signal.strip() and re.sub(r"\s+", "", signal) not in visible:
            issues.append(
                f"{slide_id}: content_route meaning signal '{signal}' is absent from final copy"
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


def _audit_onscreen_contract_definition(
    page: dict[str, Any], items: dict[str, dict[str, Any]]
) -> list[str]:
    contract = page.get("onscreen_contract")
    if not isinstance(contract, dict):
        return []
    return _onscreen_contract_definition_issues(page, contract, items)


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


def _audit_source_consumption_definition(
    page: dict[str, Any], items: dict[str, dict[str, Any]]
) -> list[str]:
    """Validate the optional Deck Plan source-to-prose-to-screen contract."""
    contract = page.get("source_consumption")
    if contract is None:
        return []
    if not isinstance(contract, dict):
        return ["source_consumption: must be an object"]

    issues: list[str] = []
    if contract.get("mode") != "strict":
        issues.append("source_consumption.mode: must be 'strict'")

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
                f"source_consumption.intentional_omissions[{omission_index}]: reason must contain at least 8 characters"
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
            f"source_consumption: declared refs must belong to page.source_refs; outside refs {outside}"
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
                f"source_consumption: refs cannot be both {label.replace('/', ' and ')} {sorted(refs)}"
            )

    if onscreen_refs:
        onscreen_contract = page.get("onscreen_contract")
        if not isinstance(onscreen_contract, dict):
            issues.append("source_consumption.onscreen_refs requires an onscreen_contract")
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
                    "source_consumption.onscreen_refs must be mapped by "
                    f"onscreen_contract.modules[].evidence_refs; unmapped refs {unmapped}"
                )
    return issues


def _audit_authored_source_consumption(
    page: dict[str, Any], slide: dict[str, Any], items: dict[str, dict[str, Any]]
) -> list[str]:
    """Require assigned source facts in full_copy and selected facts onscreen."""
    contract = page.get("source_consumption")
    if not isinstance(contract, dict) or contract.get("mode") != "strict":
        return []

    issues = _audit_source_consumption_definition(page, items)
    detail_refs, omitted_refs, _ = _source_consumption_sets(contract)
    required_refs = [
        ref
        for ref in page.get("source_refs") or []
        if isinstance(ref, str) and ref and ref not in detail_refs and ref not in omitted_refs
    ]
    anchors_by_ref = {
        str(anchor.get("source_ref")): anchor
        for anchor in contract.get("full_prose_anchors") or []
        if isinstance(anchor, dict) and isinstance(anchor.get("source_ref"), str)
    }
    full_copy = str(slide.get("full_copy") or "")
    compact_full_copy = re.sub(r"\s+", "", full_copy)

    for ref in required_refs:
        item = items.get(ref)
        if not isinstance(item, dict):
            continue
        anchor_contract = anchors_by_ref.get(ref)
        if anchor_contract:
            anchors = [
                str(value).strip()
                for value in anchor_contract.get("anchors") or []
                if str(value).strip()
            ]
            hits = [
                anchor for anchor in anchors
                if re.sub(r"\s+", "", anchor) in compact_full_copy
            ]
            minimum_hits = anchor_contract.get("minimum_hits", len(anchors))
            if isinstance(minimum_hits, int) and len(hits) < minimum_hits:
                missing = [anchor for anchor in anchors if anchor not in hits]
                issues.append(
                    f"source_consumption full_copy gap for {ref}: anchor hits "
                    f"{len(hits)}/{minimum_hits}; missing anchors {missing}; "
                    f"source statement: {_item_text(item)}"
                )
            continue

        statements = [_item_text(item)]
        statements.extend(
            str(unit.get("text") or "")
            for unit in item.get("semantic_units") or []
            if isinstance(unit, dict) and str(unit.get("text") or "").strip()
        )
        overlap = max(
            (_source_statement_overlap(statement, full_copy) for statement in statements if statement.strip()),
            default=0.0,
        )
        if overlap < 0.08:
            issues.append(
                f"source_consumption full_copy gap for {ref}: source-specific content is absent "
                f"(overlap={overlap:.3f}); source statement: {_item_text(item)}"
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


def _audit_authored_onscreen_composition(
    page: dict[str, Any], slide: dict[str, Any]
) -> list[str]:
    """Check that module lead text follows the approved page composition policy."""
    composition = page.get("onscreen_composition")
    if not isinstance(composition, dict):
        return []

    issues = _audit_onscreen_composition_definition(page)
    mode = composition.get("mode")
    if mode not in _ONSCREEN_COMPOSITION_MODES:
        return issues

    slide_id = str(slide.get("id") or page.get("id") or "?")
    modules = [module for module in slide.get("onscreen") or [] if isinstance(module, dict)]
    lead_modules = [
        module for module in modules
        if isinstance(module.get("text"), str) and module["text"].strip()
    ]
    if mode == "evidence_first":
        for module in lead_modules:
            heading = str(module.get("heading") or "?").strip()
            issues.append(
                f"{slide_id}: onscreen_composition='evidence_first' forbids module lead text in "
                f"'{heading}'; move the judgment to core_message and retain source facts as evidence items"
            )
        for module in modules:
            issues.extend(_evidence_first_item_hierarchy_issues(slide_id, module))
    else:
        lead_budget = composition.get("lead_budget")
        if isinstance(lead_budget, int) and not isinstance(lead_budget, bool) and len(lead_modules) > lead_budget:
            issues.append(
                f"{slide_id}: onscreen_composition='selective_lead' permits at most {lead_budget} "
                f"module lead(s), got {len(lead_modules)}"
            )
    return issues


def _audit_authored_onscreen_contract(
    page: dict[str, Any], slide: dict[str, Any], items: dict[str, dict[str, Any]]
) -> list[str]:
    """Check that AUTHOR consumed the declared module-level semantic contract.

    This intentionally does not infer a module's meaning from keywords on pages that
    have no contract.  The plan author declares the page's axis, source scope and role
    vocabulary; the final audit then checks the visible module payload against it.
    """
    contract = page.get("onscreen_contract")
    if not isinstance(contract, dict):
        return []

    issues = _onscreen_contract_definition_issues(page, contract, items)
    expected_modules = [module for module in contract.get("modules") or [] if isinstance(module, dict)]
    actual_modules = [module for module in slide.get("onscreen") or [] if isinstance(module, dict)]
    expected_headings = [str(module.get("heading") or "").strip() for module in expected_modules]
    actual_headings = [str(module.get("heading") or "").strip() for module in actual_modules]
    slide_id = str(slide.get("id") or page.get("id") or "?")

    if actual_headings != expected_headings:
        issues.append(
            f"{slide_id}: onscreen module headings do not match the approved contract; "
            f"expected {expected_headings}, got {actual_headings}"
        )

    modules_by_heading = {
        str(module.get("heading") or "").strip(): module
        for module in actual_modules
        if str(module.get("heading") or "").strip()
    }
    contract_headings = set(expected_headings)
    policy = contract.get("detail_policy") or {}
    if not isinstance(policy, dict):
        policy = {}
    role_markers = policy.get("role_markers") or {}
    if not isinstance(role_markers, dict):
        role_markers = {}
    allowed_roles = {str(role) for role in policy.get("allowed_roles") or []}
    forbidden_roles = {str(role) for role in policy.get("forbidden_roles") or []}
    forbidden_patterns = [pattern for pattern in policy.get("forbidden_patterns") or [] if isinstance(pattern, str)]

    for expected in expected_modules:
        heading = str(expected.get("heading") or "").strip()
        module = modules_by_heading.get(heading)
        if module is None:
            continue
        lines = _onscreen_module_lines(module)
        body = " ".join(lines)
        for signal in expected.get("required_signals") or []:
            if isinstance(signal, str) and signal and signal not in body:
                issues.append(f"{slide_id} module '{heading}': required signal '{signal}' is missing")
        for signal in expected.get("forbidden_signals") or []:
            if isinstance(signal, str) and signal and signal in body:
                issues.append(f"{slide_id} module '{heading}': forbidden cross-scope signal '{signal}' is present")

        if contract.get("scope_mode") == "exclusive":
            for other_heading in contract_headings - {heading}:
                if other_heading and other_heading in body:
                    issues.append(
                        f"{slide_id} module '{heading}': exclusive scope contains peer module heading '{other_heading}'"
                    )

        for line in lines:
            matched_roles: set[str] = set()
            for role, patterns in role_markers.items():
                if not isinstance(role, str) or not isinstance(patterns, list):
                    continue
                for pattern in patterns:
                    if not isinstance(pattern, str) or not pattern:
                        continue
                    try:
                        if re.search(pattern, line):
                            matched_roles.add(role)
                            break
                    except re.error:
                        # The definition audit reports the malformed pattern.  Avoid
                        # duplicating that same error for every authored line.
                        continue
            disallowed = matched_roles.intersection(forbidden_roles)
            if allowed_roles:
                disallowed.update(matched_roles - allowed_roles)
            if disallowed:
                issues.append(
                    f"{slide_id} module '{heading}': detail line '{line}' uses disallowed role(s) "
                    f"{sorted(disallowed)}"
                )
            for pattern in forbidden_patterns:
                try:
                    matched = re.search(pattern, line)
                except re.error:
                    matched = None
                if matched:
                    issues.append(
                        f"{slide_id} module '{heading}': detail line '{line}' matches forbidden pattern '{pattern}'"
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


def _slide_text(slide: dict[str, Any]) -> str:
    parts: list[str] = []
    for key in ("title", "subtitle", "mission", "core_message", "full_copy", "visual_thesis", "speaker_notes"):
        value = slide.get(key)
        if isinstance(value, str):
            parts.append(value)
    argument = slide.get("argument") or {}
    if isinstance(argument, dict):
        if isinstance(argument.get("pattern"), str):
            parts.append(argument["pattern"])
        parts.extend(x for x in (argument.get("chain") or []) if isinstance(x, str))
    for module in slide.get("onscreen") or []:
        if not isinstance(module, dict):
            continue
        for key in ("heading", "text"):
            value = module.get(key)
            if isinstance(value, str):
                parts.append(value)
        parts.extend(x for x in (module.get("items") or []) if isinstance(x, str))
    for relation in slide.get("relationships") or []:
        if not isinstance(relation, dict):
            continue
        for key in ("from", "to", "relation"):
            value = relation.get(key)
            if isinstance(value, str):
                parts.append(value)
    return " ".join(parts)


def _source_text_for_refs(source_refs: list[Any], foundation: dict[str, Any]) -> str:
    refs = {x for x in source_refs if isinstance(x, str)}
    parts: list[str] = []
    for key in CITABLE_KEYS:
        for item in foundation.get(key) or []:
            if not isinstance(item, dict):
                continue
            if refs.intersection(x for x in (item.get("source_refs") or []) if isinstance(x, str)):
                parts.append(_item_text(item))
    return " ".join(parts)


def _normalize_source_chapter_title(title: str) -> str:
    return CHAPTER_PREFIX_RE.sub("", title).strip(" 　")


def audit_foundation_analysis(foundation: dict[str, Any]) -> tuple[list[str], list[str]]:
    issues: list[str] = []
    warnings: list[str] = []
    items = foundation_items_by_id(foundation)
    known_ids = set(items)

    for key in CITABLE_KEYS:
        for index, item in enumerate(foundation.get(key) or []):
            if not isinstance(item, dict):
                continue
            item_id = item.get("id") or f"#{index}"
            text = _item_text(item)
            declared = item.get("visibility")
            if any(marker in text for marker in INTERNAL_MARKERS) and declared == "external_ok":
                issues.append(f"{key}.{index} ({item_id}): source text is explicitly internal ('内部…') but visibility is external_ok")

    for index, relation in enumerate(foundation.get("relations") or []):
        if not isinstance(relation, dict):
            continue
        rel_id = relation.get("id") or f"#{index}"
        support_ids = [x for x in (relation.get("support") or []) if isinstance(x, str)]
        support = _support_items(support_ids, items)
        if relation.get("basis") == "inferred":
            if not support_ids:
                issues.append(f"relations.{index} ({rel_id}): inferred relation requires non-empty support fact IDs")
            unknown = [x for x in support_ids if x not in known_ids]
            if unknown:
                issues.append(f"relations.{index} ({rel_id}): inferred relation cites unknown support IDs {unknown}")
            if not relation.get("confidence"):
                warnings.append(f"relations.{index} ({rel_id}): inferred relation has no confidence level")
        if _has_optionality(support):
            relation_text = _item_text(relation)
            if DEEPENING_RE.search(relation_text) and not INDEPENDENCE_RE.search(relation_text):
                issues.append(f"relations.{index} ({rel_id}): support preserves independent choice + progressive deepening, but relation keeps only the progression")

    for index, argument in enumerate(foundation.get("arguments") or []):
        if not isinstance(argument, dict):
            continue
        arg_id = argument.get("id") or f"#{index}"
        support = _support_items(argument.get("support") or [], items)
        claim = str(argument.get("claim") or "")
        group_issue = _group_strength_issue(claim, support)
        if group_issue:
            issues.append(f"arguments.{index} ({arg_id}): {group_issue}")

    structure = [x for x in (foundation.get("source_structure") or []) if isinstance(x, dict)]
    ids = [x.get("id") for x in structure if x.get("id")]
    if len(ids) != len(set(ids)):
        issues.append("source_structure: duplicate structure IDs")
    orders = [x.get("order") for x in structure if isinstance(x.get("order"), int)]
    if len(orders) != len(set(orders)):
        warnings.append("source_structure: duplicate order values; verify source hierarchy ordering")
    return issues, warnings


def audit_deck_plan(plan: dict[str, Any], foundation: dict[str, Any]) -> tuple[list[str], list[str]]:
    issues: list[str] = audit_plan_internal_expert_voice(plan)
    warnings: list[str] = _adjacent_plan_duplication_warnings(plan)
    items = foundation_items_by_id(foundation)
    structure = [x for x in (foundation.get("source_structure") or []) if isinstance(x, dict)]
    source_chapters = [
        x.get("id")
        for x in sorted(
            (x for x in structure if x.get("level") == "chapter" and x.get("id")),
            key=lambda x: x.get("order", 0),
        )
    ]
    mode = plan.get("source_structure_mode")
    if source_chapters and not mode:
        warnings.append("source_structure_mode: missing; source-driven plans should declare 'preserve' unless user authorized restructuring")
    if mode == "preserve":
        planned: list[str] = []
        missing = False
        for index, chapter in enumerate(plan.get("chapters") or []):
            if not isinstance(chapter, dict):
                continue
            ids = [x for x in (chapter.get("source_chapter_ids") or []) if isinstance(x, str)]
            if not ids:
                missing = True
            planned.extend(ids)
            if chapter.get("structural_operation") == "user_authorized_cross_chapter":
                issues.append(f"chapters.{index}: cross-chapter operation conflicts with source_structure_mode='preserve'")
        if missing:
            warnings.append("chapters: one or more chapters lack source_chapter_ids, so chapter-order fidelity cannot be audited mechanically")
        elif planned != source_chapters:
            issues.append(f"chapters: source chapter order/content differs from source_structure; expected {source_chapters}, got {planned}")

    audience_scope = plan.get("audience_scope", "unspecified")
    strict_evidence_fit = plan.get("evidence_fit_review_mode") == "strict"
    if not strict_evidence_fit:
        issues.append(
            "evidence_fit_review_mode: strict is required before PLAN can enter AUTHOR"
        )
    for index, page in enumerate(plan.get("pages") or []):
        if not isinstance(page, dict):
            continue
        page_id = page.get("id") or f"#{index}"
        for route_issue in audit_content_route(page):
            issues.append(f"pages.{index} ({page_id}): {route_issue}")
        for coverage_issue in _audit_content_coverage_definition(page):
            issues.append(f"pages.{index} ({page_id}): {coverage_issue}")
        for readiness_issue in audit_stage02_readiness(page):
            issues.append(f"pages.{index} ({page_id}): {readiness_issue}")
        for composition_issue in _audit_onscreen_composition_definition(page):
            issues.append(f"pages.{index} ({page_id}): {composition_issue}")
        for contract_issue in _audit_onscreen_contract_definition(page, items):
            issues.append(f"pages.{index} ({page_id}): {contract_issue}")
        for consumption_issue in _audit_source_consumption_definition(page, items):
            issues.append(f"pages.{index} ({page_id}): {consumption_issue}")
        for review_issue in _audit_evidence_fit_reviews(page, items, strict=strict_evidence_fit):
            issues.append(f"pages.{index} ({page_id}): {review_issue}")
        scope = page.get("source_scope") or []
        chapters = _scope_chapters(scope)
        operation = page.get("structural_operation")
        if len(chapters) > 1 and operation != "user_authorized_cross_chapter":
            issues.append(f"pages.{index} ({page_id}): source_scope crosses chapters {sorted(chapters)} without user_authorized_cross_chapter")

        analysis_basis = page.get("analysis_basis") or {}
        if isinstance(analysis_basis, dict) and analysis_basis.get("relation_basis") == "inferred":
            supports = [x for x in (analysis_basis.get("supports") or []) if isinstance(x, str)]
            if not supports:
                issues.append(f"pages.{index} ({page_id}).analysis_basis: inferred relation requires support IDs")
            unknown = [x for x in supports if x not in items]
            if unknown:
                issues.append(f"pages.{index} ({page_id}).analysis_basis: unknown support IDs {unknown}")

        evidence_ids = _page_evidence_ids(page)
        evidence = _support_items(sorted(evidence_ids), items)
        internal = [item.get("id", "?") for item in evidence if effective_visibility(item) == "internal_only"]
        if audience_scope == "external" and internal:
            decision = page.get("visibility_decision")
            if decision not in ("internal_only_used_as_hidden_support", "user_approved_exposure"):
                issues.append(f"pages.{index} ({page_id}): external audience uses internal-only evidence {sorted(internal)} without an explicit visibility_decision")

        page_text = _page_text(page)
        if _has_optionality(evidence) and not _preserves_optionality(page_text):
            issues.append(f"pages.{index} ({page_id}): source evidence says modes may be independently selected and progressively deepened; plan must preserve both meanings")

        group_issue = _group_strength_issue(str(page.get("message") or ""), evidence)
        if group_issue:
            issues.append(f"pages.{index} ({page_id}): {group_issue}")

    return issues, warnings


def audit_final_script(final_script: dict[str, Any], plan: dict[str, Any], foundation: dict[str, Any]) -> tuple[list[str], list[str]]:
    issues: list[str] = audit_final_internal_expert_voice(final_script, plan)
    warnings: list[str] = []
    items = foundation_items_by_id(foundation)
    pages = {p.get("id"): p for p in (plan.get("pages") or []) if isinstance(p, dict) and isinstance(p.get("id"), str)}
    chapters = {c.get("id"): c for c in (plan.get("chapters") or []) if isinstance(c, dict) and isinstance(c.get("id"), str)}
    structure = {x.get("id"): x for x in (foundation.get("source_structure") or []) if isinstance(x, dict) and isinstance(x.get("id"), str)}
    audience_scope = plan.get("audience_scope", "unspecified")
    preserve_structure = plan.get("source_structure_mode") == "preserve"
    strict_evidence_fit = plan.get("evidence_fit_review_mode") == "strict"
    if not strict_evidence_fit:
        issues.append(
            "PLAN evidence-fit gate: evidence_fit_review_mode: strict is required before AUTHOR"
        )

    for index, slide in enumerate(final_script.get("slides") or []):
        if not isinstance(slide, dict):
            continue
        slide_id = slide.get("id") or f"#{index}"
        page = pages.get(slide_id)
        if page is None:
            warnings.append(f"slides.{index} ({slide_id}): no matching deck-plan page; semantic inheritance cannot be audited")
            continue
        final_text = _slide_text(slide)
        plan_text = _page_text(page)
        evidence_ids = _page_evidence_ids(page)
        evidence = _support_items(sorted(evidence_ids), items)

        for review_issue in _audit_evidence_fit_reviews(page, items, strict=strict_evidence_fit):
            issues.append(f"slides.{index} ({slide_id}): PLAN evidence-fit gate: {review_issue}")

        plan_model = str((page.get("analysis_basis") or {}).get("model") or "").lower()
        plan_logic = str(page.get("logic") or "")
        plan_is_classification = any(token in plan_model for token in ("classification", "taxonomy", "typology")) or "分类" in plan_logic
        plan_allows_progression = bool(PROGRESSION_RE.search(plan_text) or any(token in plan_model for token in ("progression", "maturity")))
        if plan_is_classification and not plan_allows_progression and PROGRESSION_RE.search(final_text):
            issues.append(f"slides.{index} ({slide_id}): AUTHOR upgraded a classification/taxonomy plan into a progression chain")

        if _has_optionality(evidence) and not _preserves_optionality(final_text):
            issues.append(f"slides.{index} ({slide_id}): final script lost source optionality; it must preserve independent choice and progressive deepening")

        group_issue = _group_strength_issue(str(slide.get("core_message") or ""), evidence)
        if group_issue:
            issues.append(f"slides.{index} ({slide_id}): {group_issue}")

        internal = [item for item in evidence if effective_visibility(item) == "internal_only"]
        if audience_scope == "external" and internal:
            exposed: list[str] = []
            for item in internal:
                item_text = _item_text(item)
                values = [str(item.get("value") or "")]
                for match in re.findall(r"\d+(?:\.\d+)?%?(?:至|-|—)\d+(?:\.\d+)?%?|\d+(?:\.\d+)?%", item_text):
                    values.append(match)
                normalized_final = final_text.replace("至", "-").replace("—", "-")
                if any(value and value.replace("至", "-").replace("—", "-") in normalized_final for value in values):
                    exposed.append(str(item.get("id") or "?"))
            if exposed:
                issues.append(f"slides.{index} ({slide_id}): external final script exposes internal-only evidence {sorted(set(exposed))}")

        if GAP_RE.search(final_text):
            source_text = _source_text_for_refs(page.get("source_refs") or [], foundation)
            if not GAP_RE.search(plan_text) and not GAP_RE.search(source_text):
                issues.append(f"slides.{index} ({slide_id}): final script introduces a current-vs-target gap judgment without a source or plan baseline")

        for composition_issue in _audit_authored_onscreen_composition(page, slide):
            issues.append(f"slides.{index} ({slide_id}): {composition_issue}")
        for contract_issue in _audit_authored_onscreen_contract(page, slide, items):
            issues.append(f"slides.{index} ({slide_id}): {contract_issue}")
        for consumption_issue in _audit_authored_source_consumption(page, slide, items):
            issues.append(f"slides.{index} ({slide_id}): {consumption_issue}")
        for coverage_issue in _audit_authored_content_coverage(page, slide):
            issues.append(f"slides.{index} ({slide_id}): {coverage_issue}")
        for readiness_issue in audit_authored_stage02_readiness(page, slide):
            issues.append(f"slides.{index} ({slide_id}): {readiness_issue}")
        for detail_issue in _authored_bare_label_detail_issues(page, slide, items):
            issues.append(
                f"slides.{index} ({slide_id}): ONSCREEN_SOURCE_DETAIL_COLLAPSED_TO_LABEL: "
                f"{detail_issue}"
            )
        warnings.extend(
            f"slides.{index} ({slide_id}): {warning}"
            for warning in _onscreen_expression_warnings(page, slide)
        )

        if preserve_structure and slide.get("page_type") == "chapter":
            chapter_id = slide.get("chapter_id")
            chapter = chapters.get(chapter_id) if isinstance(chapter_id, str) else None
            source_ids = chapter.get("source_chapter_ids") if isinstance(chapter, dict) else None
            if source_ids and len(source_ids) == 1:
                node = structure.get(source_ids[0])
                if isinstance(node, dict) and isinstance(node.get("title"), str):
                    expected = _normalize_source_chapter_title(node["title"])
                    actual = str(slide.get("title") or "").strip()
                    if actual and expected and actual != expected:
                        issues.append(f"slides.{index} ({slide_id}): source_structure_mode='preserve' requires chapter title '{expected}', got '{actual}'")

    return issues, warnings


def validate_source_index_coverage(final_script: dict[str, Any], source_index: dict[str, Any]) -> list[str]:
    refs = source_index.get("refs") or {}
    issues: list[str] = []
    for index, slide in enumerate(final_script.get("slides") or []):
        if not isinstance(slide, dict):
            continue
        slide_id = slide.get("id") or f"#{index}"
        for ref in slide.get("source_refs") or []:
            if isinstance(ref, str) and ref and ref not in refs:
                issues.append(f"slides.{index} ({slide_id}).source_refs: '{ref}' is not mapped in source-index.json")
    return issues
