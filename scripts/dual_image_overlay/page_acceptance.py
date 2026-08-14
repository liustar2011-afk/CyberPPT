"""Deterministic representative-page selection and page-by-page acceptance."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Mapping, Sequence

from .qa_render_page import check_pptx_geometry, render_to_png


ACCEPTANCE_SCHEMA = "cyberppt.dual_image.page_acceptance.v1"


def _score(page: Mapping[str, Any]) -> tuple[float, int]:
    score = 0.0
    score += float(page.get("visual_node_count") or 0) * 2
    score += float(page.get("text_node_count") or 0)
    score += float(page.get("relation_count") or 0) * 3
    score += 5 if page.get("has_images") else 0
    score += 5 if page.get("has_table") else 0
    score += 5 if page.get("has_curve") else 0
    score += 3 if page.get("page_role") in {"content", "analysis", "process"} else 0
    return score, int(page.get("page_number") or 0)


def select_representative_pages(pages: Sequence[Mapping[str, Any]], *, max_pages: int = 3) -> list[int]:
    """Select complex, deterministic representatives without replacing full-deck QA."""
    if max_pages < 1:
        return []
    normalized = [page for page in pages if page.get("page_number") is not None]
    if not normalized:
        return []
    ranked = sorted(normalized, key=_score, reverse=True)
    selected: list[int] = []
    for page in ranked:
        number = int(page["page_number"])
        if number not in selected:
            selected.append(number)
        if len(selected) >= max_pages:
            break
    return sorted(selected)


def _artifact_status(path: str | Path | None) -> dict[str, Any]:
    if not path:
        return {"path": None, "exists": False}
    resolved = Path(path).expanduser().resolve()
    return {"path": str(resolved), "exists": resolved.is_file()}


def build_page_acceptance_manifest(
    pages: Sequence[Mapping[str, Any]],
    artifacts: Mapping[int | str, Mapping[str, Any]],
    *,
    representative_limit: int = 3,
    require_user_confirmation: bool = False,
) -> dict[str, Any]:
    representatives = select_representative_pages(pages, max_pages=representative_limit)
    records: list[dict[str, Any]] = []
    for page in sorted(pages, key=lambda item: int(item.get("page_number") or 0)):
        number = int(page["page_number"])
        raw = artifacts.get(number, artifacts.get(str(number), {}))
        evidence = {key: _artifact_status(raw.get(key)) for key in ("full", "background", "scene_graph", "page_svg_ir", "svg", "pptx", "rendered", "side_by_side", "qa_fusion", "geometry_qa")}
        required = ["full", "background", "scene_graph", "page_svg_ir", "qa_fusion"]
        if raw.get("pptx"):
            required.extend(["pptx", "geometry_qa"])
        if raw.get("rendered"):
            required.append("rendered")
        if raw.get("side_by_side"):
            required.append("side_by_side")
        missing = [key for key in required if not evidence[key]["exists"]]
        qa_valid = raw.get("qa_valid", True) is True
        user_confirmed = raw.get("user_confirmed", False) is True
        accepted = not missing and qa_valid and (user_confirmed or not require_user_confirmation)
        records.append({"page_number": number, "representative": number in representatives, "required_artifacts": required, "evidence": evidence, "missing_artifacts": missing, "qa_valid": qa_valid, "user_confirmed": user_confirmed, "accepted": accepted})
    return {"schema": ACCEPTANCE_SCHEMA, "representative_pages": representatives, "page_count": len(records), "accepted_page_count": sum(1 for record in records if record["accepted"]), "valid": bool(records) and all(record["accepted"] for record in records), "pages": records, "policy": {"full_deck_page_by_page": True, "representative_limit": representative_limit, "require_user_confirmation": require_user_confirmation}}


def accept_pptx_page(pptx_path: str | Path, out_dir: str | Path, *, render: bool = True) -> dict[str, Any]:
    """Render one PPTX and return geometry plus image evidence paths."""
    pptx = Path(pptx_path).expanduser().resolve()
    output = Path(out_dir).expanduser().resolve()
    output.mkdir(parents=True, exist_ok=True)
    geometry = check_pptx_geometry(pptx)
    geometry_path = output / f"{pptx.stem}_geometry_qa.json"
    geometry_path.write_text(json.dumps(geometry, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    rendered = render_to_png(pptx, output) if render else []
    return {"pptx": str(pptx), "geometry_qa": str(geometry_path), "geometry_valid": geometry["valid"], "render_status": "rendered" if rendered else ("not_requested" if not render else "unavailable"), "rendered": [str(path) for path in rendered], "accepted": bool(geometry["valid"] and (rendered or not render))}

