"""Preview a page's onscreen anchors from outline.json before authoring."""

from __future__ import annotations

from pathlib import Path

from cyberppt.outline_contract import load_outline

# ONSCREEN_DETAIL_PHRASE_TOO_LONG treats an anchor over this length as a
# hard format violation; keep the threshold visible here so authors can
# read straight from the preview instead of hitting the error later.
_DETAIL_PHRASE_LENGTH_LIMIT = 30


def preview_page_anchors(
    project: Path,
    page_id: str,
    outline_path: Path | None = None,
) -> dict[str, object]:
    project = project.expanduser().resolve()
    if not project.exists():
        raise FileNotFoundError(f"project does not exist: {project}")
    if not page_id:
        raise ValueError("--page is required")
    outline_path = (
        outline_path.expanduser().resolve()
        if outline_path is not None
        else project / "workbench" / "stages" / "01-analysis" / "outline.json"
    )
    if not outline_path.exists():
        raise FileNotFoundError(f"outline does not exist: {outline_path}")
    outline = load_outline(outline_path, lightweight=True)
    pages = outline.get("pages")
    page = next(
        (item for item in pages if isinstance(item, dict) and item.get("page_id") == page_id),
        None,
    )
    if page is None:
        known = sorted(
            str(item.get("page_id"))
            for item in pages
            if isinstance(item, dict) and item.get("page_id")
        )
        raise ValueError(f"page not found in outline: {page_id} (known pages: {', '.join(known)})")

    content_units = []
    for unit in page.get("content_units") or []:
        if not isinstance(unit, dict):
            continue
        anchors = [str(item) for item in unit.get("onscreen_anchors") or []]
        content_units.append({
            "unit_id": unit.get("unit_id"),
            "role": unit.get("role"),
            "onscreen_required": unit.get("onscreen_required"),
            "source_refs": list(unit.get("source_refs") or []),
            "coverage_anchors": list(unit.get("coverage_anchors") or []),
            "onscreen_anchors": [
                {
                    "text": anchor,
                    "length": len(anchor),
                    "over_detail_phrase_limit": len(anchor) > _DETAIL_PHRASE_LENGTH_LIMIT,
                }
                for anchor in anchors
            ],
        })

    return {
        "schema": "cyberppt.page_anchor_preview.v1",
        "page_id": page.get("page_id"),
        "title": page.get("title"),
        "argument_role": page.get("argument_role"),
        "expression_model_selection": page.get("expression_model_selection"),
        "outline": str(outline_path),
        "content_units": content_units,
    }
