"""High-confidence checks for source items grouped under one onscreen parent."""
from __future__ import annotations

import re
from collections.abc import Iterable
from dataclasses import dataclass


_NARROW_INSTITUTION_PARENT_RE = re.compile(r"(?:制度|规章|法规)$")
_ACTION_POLICY_RE = re.compile(r"(?:行动计划|专项行动|重点行动领域|应用场景)")
_APPLICATION_REQUIREMENT_RE = re.compile(
    r"(?:场景|应用|采集|流通|利用|融合|预测|多能互补|梯度定价)"
)
_INSTITUTION_SOURCE_RE = re.compile(
    r"(?:分类分级指南|管理办法|条例|规章|管理规则|制度安排|保护责任|安全责任)"
)


@dataclass(frozen=True)
class SourceGroupingMismatch:
    """Evidence that paragraph co-location was promoted into a false hierarchy."""

    heading: str
    action_refs: tuple[str, ...]
    institution_refs: tuple[str, ...]
    shared_source_refs: tuple[str, ...]


def source_colocation_grouping_mismatch(
    heading: object,
    evidence: Iterable[tuple[object, object, Iterable[object]]],
) -> SourceGroupingMismatch | None:
    """Flag a narrow institution parent mixing action/application policy evidence.

    This rule is intentionally narrow.  A policy umbrella such as ``政策要求``
    may legitimately contain regulatory and application requirements.  A parent
    ending in ``制度``/``规章``/``法规`` claims a tighter institutional taxonomy;
    source items from an action plan or application-scene requirement cannot be
    treated as its children merely because they occur in the same paragraph.
    """

    clean_heading = str(heading or "").strip()
    if not _NARROW_INSTITUTION_PARENT_RE.search(clean_heading):
        return None

    action_records: list[tuple[str, set[str]]] = []
    institution_records: list[tuple[str, set[str]]] = []
    for raw_ref, raw_statement, raw_source_refs in evidence:
        ref = str(raw_ref or "?").strip() or "?"
        statement = str(raw_statement or "").strip()
        source_values = (
            [raw_source_refs] if isinstance(raw_source_refs, str) else raw_source_refs
        )
        source_refs = {
            str(value).strip() for value in source_values if str(value).strip()
        }
        if not statement:
            continue
        is_action = bool(
            _ACTION_POLICY_RE.search(statement)
            and _APPLICATION_REQUIREMENT_RE.search(statement)
        )
        is_institution = bool(_INSTITUTION_SOURCE_RE.search(statement))
        if is_action and not is_institution:
            action_records.append((ref, source_refs))
        if is_institution:
            institution_records.append((ref, source_refs))

    shared_source_refs = {
        source_ref
        for _, action_sources in action_records
        for _, institution_sources in institution_records
        for source_ref in action_sources.intersection(institution_sources)
    }
    if not action_records or not institution_records or not shared_source_refs:
        return None
    return SourceGroupingMismatch(
        heading=clean_heading,
        action_refs=tuple(dict.fromkeys(ref for ref, _ in action_records)),
        institution_refs=tuple(dict.fromkeys(ref for ref, _ in institution_records)),
        shared_source_refs=tuple(sorted(shared_source_refs)),
    )
