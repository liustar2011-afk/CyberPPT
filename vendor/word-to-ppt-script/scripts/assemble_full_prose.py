#!/usr/bin/env python3
"""Assemble a page's 完整文字稿 (full manuscript) from source-truth records.

Replaces naive `"".join(r["statement"] for r in records)` concatenation.
That approach produces two concrete, observed defects:

1. Orphaned enumeration markers. Formal Chinese source documents often write
   clauses as "一是……二是……三是……". A page's content units frequently pull
   only a *subset* of that original list (e.g. items 2-4, because item 1
   belongs to an earlier page's argument). Naive concatenation reproduces the
   original document-global numbering verbatim, so the page's 完整文字稿 can
   open mid-list ("二是……三是……四是……") with "一是" never appearing on that
   page, or skip a number outright (一/二/四/五…). Both read as an
   unexplained fragment even though each clause is individually well-formed.
2. No framing. A bare, un-introduced list of clauses reads as a pile of
   facts rather than an argument, even when the clauses themselves are fine.

This module fixes both mechanically, without inventing new claims:

- detect and strip each statement's *original* enumeration marker
  (一是/二是/…/十是);
- when 2 or more statements in the page originally carried a marker,
  re-issue fresh, page-local, contiguous markers starting at 一是, so the
  list is self-contained;
- prepend one framing sentence chosen from a small template table keyed by
  the page's dominant `semantic_argument_role`, only when re-issuing markers
  (i.e. only when there is actually a list to frame);
- stable-sort records first by `semantic_argument_weight`
  (core > supporting > detail > constraint) and then by a fixed
  `semantic_argument_role` priority (thesis/positioning, then
  foundation/evidence/definition, then architecture/capability/operation/
  cooperation, then recommendation, then boundary) before assembly. On most
  pages every record shares the same weight and role, so this is a no-op
  (stable sort preserves original order); on pages that do mix roles, it
  orders the prose as background/evidence before judgment before mechanism
  before recommendation before caveats, instead of following whatever order
  the source_refs list happened to be in.

Deliberately does NOT auto-generate a closing synthesis sentence. Writing a
new sentence that paraphrases "what these facts add up to" risks asserting a
conclusion beyond what source-truth actually states, which conflicts with
this skill's no-fabrication rule. If a page's argument genuinely needs an
explicit close, write it by hand and keep it traceable to a specific record.

Also breaks the assembled body into paragraphs (blank-line separated) instead
of one unbroken block, which was unreadable once a page carried more than a
handful of statements. Paragraph breaks land at two kinds of boundary:

- a `semantic_argument_weight`/`semantic_argument_role` tier change (the sort
  already groups records by tier, so this reuses that structure rather than
  inventing new topic boundaries);
- inside a long same-tier run, every `_PARAGRAPH_CHUNK_SIZE` statements, so a
  single tier with many records still reads as several short paragraphs
  rather than one wall of text.

This is a mechanical, content-preserving heuristic, not real topic-aware
paragraphing — it never reorders or rewrites a statement, only decides where
a blank line goes. A hand-authored page that genuinely needs a different
paragraph shape should still be edited by hand.

Usage:

    from assemble_full_prose import assemble_full_prose
    full_prose = assemble_full_prose([records[r] for r in unit_refs])

Each record must provide at least `statement`; `semantic_argument_role` and
`semantic_argument_weight` are used when present and safely ignored (treated
as neutral/mid-priority) when absent, so this also works against source-truth
records that predate those fields.
"""
from __future__ import annotations

import re

_MARKER_RE = re.compile(r"^([一二三四五六七八九十]+)是")
_CN_NUM = ["一", "二", "三", "四", "五", "六", "七", "八", "九", "十"]

_WEIGHT_ORDER = {"core": 0, "supporting": 1, "detail": 2, "constraint": 3}
_ROLE_ORDER = {
    "thesis": 0, "positioning": 0,
    "foundation": 1, "evidence": 1, "definition": 1,
    "architecture": 2, "capability": 2, "operation": 2, "cooperation": 2,
    "recommendation": 3,
    "boundary": 4,
}
_DEFAULT_WEIGHT = 1  # treated as "supporting" when the field is absent
_DEFAULT_ROLE = 2    # treated as mechanism-tier when the field is absent

_FRAME_BY_ROLE = {
    "foundation": "现实基础和制约条件体现在以下几个方面：",
    "positioning": "总体定位具体落实为以下几个方面：",
    "thesis": "核心判断体现在以下几个方面：",
    "cooperation": "具体机制安排包括以下几个方面：",
    "architecture": "总体架构体现在以下几个方面：",
    "capability": "能力建设体现在以下几个方面：",
    "operation": "运行安排包括以下几个方面：",
    "boundary": "边界要求体现在以下几个方面：",
    "evidence": "具体依据包括以下几个方面：",
    "definition": "具体构成包括以下几个方面：",
    "recommendation": "具体建议包括以下几个方面：",
}
_FRAME_DEFAULT = "具体内容包括以下几个方面："

# Inside one same-tier run, start a new paragraph after this many statements
# so a long run of same-weight/same-role records doesn't render as one
# unbroken block.
_PARAGRAPH_CHUNK_SIZE = 3


def _strip_marker(statement: str) -> str:
    return _MARKER_RE.sub("", statement, count=1)


def _tier_key(record: dict) -> tuple:
    weight = _WEIGHT_ORDER.get(record.get("semantic_argument_weight", ""), _DEFAULT_WEIGHT)
    role = _ROLE_ORDER.get(record.get("semantic_argument_role", ""), _DEFAULT_ROLE)
    return (weight, role)


def _sort_key(record: dict, index: int) -> tuple:
    return _tier_key(record) + (index,)  # index is the stable-order tiebreaker


def _paragraph_join(parts: list[str], tiers: list[tuple]) -> str:
    """Join statement fragments into blank-line-separated paragraphs.

    Breaks whenever the (weight, role) tier changes, and additionally every
    `_PARAGRAPH_CHUNK_SIZE` fragments within a same-tier run.
    """

    if not parts:
        return ""
    paragraphs: list[str] = [parts[0]]
    run_length = 1
    for prev_tier, tier, part in zip(tiers, tiers[1:], parts[1:]):
        tier_changed = tier != prev_tier
        if tier_changed or run_length >= _PARAGRAPH_CHUNK_SIZE:
            paragraphs.append(part)
            run_length = 1
        else:
            paragraphs[-1] += part
            run_length += 1
    return "\n\n".join(paragraphs)


def assemble_full_prose(records: list[dict]) -> str:
    """records: source-truth record dicts, in a page's original ref order.

    Each dict should have `statement`, and may have `semantic_argument_role`
    and `semantic_argument_weight`. Returns the assembled 完整文字稿 string.
    """
    if not records:
        return ""

    ordered = [r for _, r in sorted(
        enumerate(records), key=lambda pair: _sort_key(pair[1], pair[0])
    )]

    marked = [bool(_MARKER_RE.match(r.get("statement", ""))) for r in ordered]
    statements = [
        _strip_marker(r["statement"]) if m else r.get("statement", "")
        for r, m in zip(ordered, marked)
    ]

    # Only re-issue local enumeration markers when at least half the
    # statements originally had one and there are 2+ statements — a lone
    # marked statement, or a majority-unmarked mix, usually means these are
    # not really meant to read as one parallel list.
    reissue = len(statements) >= 2 and sum(marked) * 2 >= len(marked)
    if reissue:
        parts = [
            f"{_CN_NUM[i]}是{s}" if i < len(_CN_NUM) else s
            for i, s in enumerate(statements)
        ]
    else:
        parts = statements

    tiers = [_tier_key(r) for r in ordered]
    body = _paragraph_join(parts, tiers)

    if reissue:
        dominant_role = ordered[0].get("semantic_argument_role", "")
        frame = _FRAME_BY_ROLE.get(dominant_role, _FRAME_DEFAULT)
        return frame + body
    return body
