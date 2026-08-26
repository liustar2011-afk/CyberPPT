"""Deterministic checks for authored evidence visibility mappings."""

from __future__ import annotations

import re

from cyberppt.page_consumption_contract import argument_chain_visibility_gaps
from cyberppt.page_logic_contract import validate_authored_page_logic

from .models import ScriptPage, ScriptQualityIssue, _issue
from .parsing import _source_refs


_ONSCREEN_VISIBILITIES = {"primary_onscreen", "supporting_onscreen"}
_OFFSCREEN_VISIBILITIES = {"prose_only", "notes_only", "trace_only"}
_MAPPING_ARROW_RE = re.compile(r"(?:→|->)")
_PARALLEL_CONNECTOR_RE = re.compile(r"(?:以及|、|及|和|与)")
_CIRCLED_ORDINAL_PREFIX_RE = re.compile(r"^[①-⑳]")


def _mapping_label(value: str) -> str:
    label = str(value or "").strip()
    if "=" in label:
        label = label.rsplit("=", 1)[-1].strip()
    label = re.sub(r"^[【\[（(]+|[】\]）)]+$", "", label).strip()
    return re.sub(r"\s+", "", label).strip("：:")


def _mapping_label_key(value: str) -> tuple[str, ...]:
    """Return an order-preserving key for explicit Chinese parallel labels.

    Exact labels remain exact.  Connector variants are equivalent only when
    they split the complete label into the same ordered terms.  Requiring at
    least two characters per term keeps single-character lexical uses of
    和／与／及 out of this deliberately narrow normalization.
    """

    label = _mapping_label(value)
    if not label:
        return ()
    terms = tuple(_PARALLEL_CONNECTOR_RE.split(label))
    if len(terms) < 2 or any(len(term) < 2 for term in terms):
        return (label,)
    return terms


def _mapping_label_display_core(value: str) -> tuple[str, bool]:
    """Return the business label and whether explicit display decoration exists."""

    label = _mapping_label(value)
    prefix_match = _CIRCLED_ORDINAL_PREFIX_RE.match(label)
    if prefix_match:
        label = label[prefix_match.end():]
    business_label, separator, qualifier = label.partition("｜")
    has_qualifier = bool(separator and qualifier)
    core = business_label if has_qualifier else label
    return core, bool(prefix_match or has_qualifier)


def _mapping_labels_equal(left: str, right: str) -> bool:
    left_label = _mapping_label(left)
    right_label = _mapping_label(right)
    if left_label == right_label:
        return bool(left_label)
    if not left_label or not right_label:
        return False
    if _mapping_label_key(left_label) == _mapping_label_key(right_label):
        return True
    left_core, left_decorated = _mapping_label_display_core(left_label)
    right_core, right_decorated = _mapping_label_display_core(right_label)
    return left_decorated != right_decorated and bool(left_core and right_core) and (
        _mapping_label_key(left_core) == _mapping_label_key(right_core)
    )


def _evidence_mapping_entries(text: str) -> tuple[tuple[str, tuple[str, ...]], ...]:
    entries: list[tuple[str, tuple[str, ...]]] = []
    for segment in re.split(r"[；;\n]+", str(text or "")):
        parts = _MAPPING_ARROW_RE.split(segment, maxsplit=1)
        if len(parts) != 2:
            continue
        label = _mapping_label(parts[0])
        refs = _source_refs(parts[1])
        if label and refs:
            entries.append((label, refs))
    return tuple(entries)


def _source_visibility(contract: dict[str, object]) -> dict[str, set[str]]:
    result: dict[str, set[str]] = {}
    for field in ("content_units", "evidence_roles"):
        records = contract.get(field)
        if not isinstance(records, list):
            continue
        for record in records:
            if not isinstance(record, dict):
                continue
            visibility = str(record.get("visibility") or "").strip()
            if visibility not in _ONSCREEN_VISIBILITIES | _OFFSCREEN_VISIBILITIES:
                continue
            for ref in record.get("source_refs") or []:
                if str(ref):
                    result.setdefault(str(ref), set()).add(visibility)
    return result


def _onscreen_visibility_contract_issues(
    page: ScriptPage,
    contract: dict[str, object],
) -> list[ScriptQualityIssue]:
    """Reject explicit promotion of offscreen evidence into visible modules.

    The check requires three exact declarations: a required consumption
    contract, an evidence-map arrow, and a target label that matches a parsed
    visible module.  It never infers visibility from token overlap.
    """

    if str(contract.get("page_consumption_contract_mode") or "legacy") != "required":
        return []
    visible_labels = {
        _mapping_label(title)
        for title in page.module_titles
        if _mapping_label(title)
    }
    if not visible_labels:
        return []
    visibility_by_ref = _source_visibility(contract)
    issues: list[ScriptQualityIssue] = []
    for label, refs in _evidence_mapping_entries(page.evidence_map):
        if not any(
            _mapping_labels_equal(label, visible_label)
            for visible_label in visible_labels
        ):
            continue
        promoted = tuple(
            ref
            for ref in refs
            if visibility_by_ref.get(ref)
            and visibility_by_ref[ref].issubset(_OFFSCREEN_VISIBILITIES)
        )
        if not promoted:
            continue
        issues.append(_issue(
            "ONSCREEN_VISIBILITY_CONTRACT_BREACH",
            page,
            "The evidence map promotes facts declared for offscreen use into a visible module.",
            "Move those facts back to their declared prose/notes/trace layer, or revise the authoritative page plan and rerun the formal handoff.",
            source_ids=promoted,
            evidence=(f"module={label}",),
        ))
    return issues


def _argument_chain_visibility_issues(
    page: ScriptPage,
    contract: dict[str, object],
) -> list[ScriptQualityIssue]:
    """Reject required fact-chain steps with no visible main-chain carrier."""

    if str(contract.get("page_consumption_contract_mode") or "legacy") != "required":
        return []
    records = [
        item
        for item in contract.get("content_units") or []
        if isinstance(item, dict)
    ]
    return [
        _issue(
            "ARGUMENT_CHAIN_FACT_VISIBILITY_MISSING",
            page,
            (
                f"Argument-chain step {gap.step_index} cites facts with no "
                "primary_onscreen/supporting_onscreen main-chain carrier."
            ),
            (
                "Revise the authoritative page plan so this argument-chain step "
                "has at least one primary_onscreen or supporting_onscreen fact "
                "with topology_role=main_chain, then rerun the formal handoff."
            ),
            source_ids=gap.source_refs,
            evidence=(f"step_index={gap.step_index}",),
        )
        for gap in argument_chain_visibility_gaps(
            records,
            contract.get("argument_chain"),
        )
    ]


def _page_logic_contract_issues(
    page: ScriptPage,
    contract: dict[str, object],
) -> list[ScriptQualityIssue]:
    """Verify logic-to-prose-to-screen continuity for required page contracts."""

    return [
        _issue(
            str(item.get("code") or "PAGE_LOGIC_CONTRACT_INVALID"),
            page,
            str(item.get("message") or "Page logic contract is invalid."),
            str(item.get("action") or "Repair the authoritative page logic contract."),
            source_ids=tuple(str(value) for value in item.get("source_refs") or []),
            evidence=tuple(str(value) for value in item.get("evidence") or []),
        )
        for item in validate_authored_page_logic(
            contract,
            prose=page.full_prose,
            onscreen=page.onscreen_text,
            module_titles=page.module_titles,
        )
    ]
__all__ = [
    "_argument_chain_visibility_issues",
    "_evidence_mapping_entries",
    "_mapping_label_key",
    "_mapping_labels_equal",
    "_onscreen_visibility_contract_issues",
    "_page_logic_contract_issues",
]
