"""Density and source-volume Outline audit rules."""

from __future__ import annotations

from cyberppt.outline_audit_shared import AuditIssue, _page_id


def _weight_issues(outline: dict[str, object], pages: list[dict[str, object]]) -> list[AuditIssue]:
    targets = outline.get("source_section_weights")
    if not isinstance(targets, dict) or not targets:
        return []
    actual: dict[str, float] = {}
    for page in pages:
        if page.get("page_type") != "content":
            continue
        chapter = str(page.get("chapter_id") or "")
        actual[chapter] = actual.get(chapter, 0.0) + float(page.get("source_weight") or 0.0)
    distorted = [chapter for chapter, target in targets.items() if float(target) - actual.get(str(chapter), 0.0) > 0.20]
    if not distorted:
        return []
    return [
        AuditIssue(
            "SOURCE_WEIGHT_DISTORTED",
            "Core source sections are underrepresented in the planned content pages.",
            tuple(str(item) for item in distorted),
            "rebalance_to_source_weight",
        )
    ]


def _page_source_volume(page: dict[str, object], records: dict[str, dict[str, object]]) -> int:
    """Approximate how much source material a page actually has to draw on.

    Sums the character length of every referenced Source Truth statement
    (main + detail refs). This is a proxy for how much a page *can* say, not
    a proxy for how good the page currently is — a page can under-use
    available material, but it cannot invent material it doesn't have.
    """

    ref_ids: set[str] = set()
    for field in ("source_refs", "detail_refs", "boundary_refs"):
        value = page.get(field)
        if isinstance(value, list):
            ref_ids.update(str(item) for item in value)
    return sum(len(str(records[ref_id].get("statement") or "")) for ref_id in ref_ids if ref_id in records)


def _content_page_density_issues(
    pages: list[dict[str, object]], source_truth: dict[str, object] | None
) -> list[AuditIssue]:
    """Flag runs of consecutive content pages whose source material is thin.

    A single terse page next to normal-density pages is often a deliberate
    beat (a stark decision or transition page) and is left alone. A *run* of
    2+ consecutive same-chapter pages that are all well below the deck's
    typical page volume usually means the source material for that stretch
    was thinner than the page-per-subsection default assumed, and the pages
    should be merged rather than force-padded — merging is the source-
    faithful fix; inventing content to fill a thin page is not.
    """

    if not isinstance(source_truth, dict):
        return []
    raw_records = source_truth.get("records")
    if not isinstance(raw_records, list):
        return []
    records = {
        str(record.get("id")): record
        for record in raw_records
        if isinstance(record, dict) and record.get("id")
    }
    content_pages = sorted(
        (page for page in pages if page.get("page_type") == "content"),
        key=lambda page: page.get("sequence", 0),
    )
    if len(content_pages) < 4:
        # Too few content pages for a stable median; not worth the noise.
        return []
    volumes = [
        (page, _page_source_volume(page, records)) for page in content_pages
    ]
    nonzero = sorted(volume for _, volume in volumes if volume > 0)
    if len(nonzero) < 4:
        return []
    median = nonzero[len(nonzero) // 2]
    threshold = median * 0.45
    if threshold <= 0:
        return []

    issues: list[AuditIssue] = []
    run: list[tuple[dict[str, object], int]] = []

    def _flush() -> None:
        if len(run) < 2:
            run.clear()
            return
        page_ids = tuple(_page_id(page) for page, _ in run)
        volumes_str = "、".join(f"{_page_id(page)}={volume}字" for page, volume in run)
        issues.append(
            AuditIssue(
                "CONTENT_PAGE_DENSITY_LOW",
                (
                    f"{len(run)} consecutive content pages in the same chapter each carry far less "
                    f"source material than the deck's typical page (median {median} chars, threshold "
                    f"{int(threshold)} chars): {volumes_str}. Merge them into fewer, denser pages "
                    "instead of writing a thin standalone page for each source subsection."
                ),
                page_ids,
                "merge_thin_adjacent_pages",
            )
        )
        run.clear()

    prev_chapter = None
    for page, volume in volumes:
        chapter = page.get("chapter_id")
        if chapter != prev_chapter:
            _flush()
        if volume > 0 and volume < threshold:
            run.append((page, volume))
        else:
            _flush()
        prev_chapter = chapter
    _flush()
    return issues
