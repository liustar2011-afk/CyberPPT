"""Build page-authoring constraints from an approved Outline contract."""

from __future__ import annotations

from pathlib import Path
import re

from cyberppt.outline_contract import load_outline

# ONSCREEN_DETAIL_PHRASE_TOO_LONG treats an anchor over this length as a
# hard format violation; keep the threshold visible here so authors can
# read straight from the preview instead of hitting the error later.
_DETAIL_PHRASE_LENGTH_LIMIT = 30
_SEMANTIC_COMPRESSION_MIN_LENGTH = 20
_ORDERED_VISUAL_INTENTS = {"phase", "closed_loop", "decision_admission"}
_NEGATIVE_FOREGROUND_ROLES = {
    "boundary", "security", "quality", "compliance", "risk", "assurance", "foundation",
}
_SECTION_METADATA_RE = re.compile(r"^(?:\*{1,2}\s*)?[一二三四五六七八九十百\d]+、")
_SUBSECTION_METADATA_RE = re.compile(r"^(?:\*{1,2}\s*)?（[一二三四五六七八九十\d]+）")
_CITATION_ONLY_RE = re.compile(r"^(?:\[\d+\])+(?:[-—]\[\d+\])?[。；;]?$")


def _is_structural_metadata(unit: dict[str, object]) -> bool:
    """Keep source headings and table headers out of audience-facing copy."""

    statement = str(unit.get("statement") or "").strip()
    if _SECTION_METADATA_RE.match(statement) or _SUBSECTION_METADATA_RE.match(statement):
        return True
    return (
        (statement.startswith("|") and statement.count("**") >= 4)
        or bool(_CITATION_ONLY_RE.match(statement))
    )


def _onscreen_policy(unit: dict[str, object]) -> str:
    """Classify a unit before writing, without changing its source contract."""

    if unit.get("onscreen_required") is not True:
        return "prose_only"
    if _is_structural_metadata(unit):
        return "metadata"
    anchors = [str(item).strip() for item in unit.get("onscreen_anchors") or [] if str(item).strip()]
    statement = str(unit.get("statement") or "").strip()
    if statement.startswith("|") and anchors and max(map(len, anchors)) <= 16:
        return "structural"
    if any(len(anchor) > _SEMANTIC_COMPRESSION_MIN_LENGTH for anchor in anchors):
        return "semantic"
    return "literal"


def _policy_requirement(policy: str) -> str:
    return {
        "literal": "上屏保留业务对象、关键动作、状态或数字；允许自然短语改写。",
        "semantic": "完整文字稿保留完整语义；上屏使用短语化表达，并在锚点覆盖说明点名来源记录和承载模块。",
        "structural": "作为结构标签或分组关系处理，不要求逐字复现来源表头。",
        "metadata": "来源章节标题或表头仅用于追溯，不进入内容页上屏。",
        "prose_only": "完整文字稿和演讲者备注保留，默认不占用上屏模块。",
    }[policy]


def _load_page(project: Path, page_id: str, outline_path: Path | None) -> tuple[Path, dict[str, object]]:
    project = project.expanduser().resolve()
    if not project.exists():
        raise FileNotFoundError(f"project does not exist: {project}")
    if not page_id:
        raise ValueError("--page is required")
    resolved_outline = (
        outline_path.expanduser().resolve()
        if outline_path is not None
        else project / "workbench" / "stages" / "01-analysis" / "outline.json"
    )
    if not resolved_outline.exists():
        raise FileNotFoundError(f"outline does not exist: {resolved_outline}")
    outline = load_outline(resolved_outline, lightweight=True)
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
    return resolved_outline, page


def build_page_preflight_from_contract(
    page: dict[str, object],
    outline_path: Path,
) -> dict[str, object]:
    """Build authoring constraints from one already-loaded page contract."""

    visual_intent = str(page.get("visual_intent_type") or page.get("semantic_intent_type") or "")
    content_units = []
    for raw_unit in page.get("content_units") or []:
        if not isinstance(raw_unit, dict):
            continue
        anchors = [str(item) for item in raw_unit.get("onscreen_anchors") or []]
        policy = _onscreen_policy(raw_unit)
        content_units.append({
            "unit_id": raw_unit.get("unit_id"),
            "role": raw_unit.get("role"),
            "priority": raw_unit.get("priority"),
            "onscreen_required": raw_unit.get("onscreen_required"),
            "onscreen_policy": policy,
            "authoring_requirement": _policy_requirement(policy),
            "source_refs": list(raw_unit.get("source_refs") or []),
            "coverage_anchors": list(raw_unit.get("coverage_anchors") or []),
            "onscreen_anchors": [
                {
                    "text": anchor,
                    "length": len(anchor),
                    "over_detail_phrase_limit": len(anchor) > _DETAIL_PHRASE_LENGTH_LIMIT,
                }
                for anchor in anchors
            ],
        })
    p0_units = [unit for unit in content_units if unit.get("priority") == "P0"]
    expression = page.get("expression_model_selection")
    model_id = expression.get("model_id") if isinstance(expression, dict) else None
    return {
        "schema": "cyberppt.page_preflight.v1",
        "page_id": page.get("page_id"),
        "title": page.get("title"),
        "argument_role": page.get("argument_role"),
        "outline": str(outline_path),
        "expression_model_selection": expression,
        "constraints": {
            "expression_model_id": model_id,
            "detail_phrase_limit": _DETAIL_PHRASE_LENGTH_LIMIT,
            "requires_order_signal": visual_intent in _ORDERED_VISUAL_INTENTS,
            "requires_feedback_signal": visual_intent == "closed_loop",
            "negative_foreground_allowed": str(page.get("argument_role") or "") in _NEGATIVE_FOREGROUND_ROLES,
        },
        "p0_unit_count": len(p0_units),
        "p0_unit_ids": [unit.get("unit_id") for unit in p0_units],
        "content_units": content_units,
    }


def build_page_preflight(
    project: Path,
    page_id: str,
    outline_path: Path | None = None,
) -> dict[str, object]:
    """Return the page-specific constraints an author needs before drafting."""

    resolved_outline, page = _load_page(project, page_id, outline_path)
    return build_page_preflight_from_contract(page, resolved_outline)


def preview_page_anchors(
    project: Path,
    page_id: str,
    outline_path: Path | None = None,
) -> dict[str, object]:
    report = build_page_preflight(project, page_id, outline_path)
    report["schema"] = "cyberppt.page_anchor_preview.v1"
    return report
