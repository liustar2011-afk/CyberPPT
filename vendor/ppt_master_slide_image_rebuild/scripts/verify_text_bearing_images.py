#!/usr/bin/env python3
"""
PPT Master - Text-Bearing Image Verifier

Verify that slide-image rebuilds do not preserve presentation text as raster
image regions without an approved treatment.

Usage:
    python3 scripts/verify_text_bearing_images.py <project_path>

Examples:
    python3 scripts/verify_text_bearing_images.py projects/demo
    python3 scripts/verify_text_bearing_images.py projects/demo --write-report

Dependencies:
    None (only uses standard library)
"""

from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

FULL_SLIDE_RATIO = 0.88
OVERLAP_WARNING_RATIO = 0.18
STRUCTURE_CROP_LARGE_RATIO = 0.12

TEXT_APPROVED_TREATMENTS = {
    "editable_text",
    "vector_rebuild",
    "raster_exception",
    "user_accepts_non_editable_text",
}

CROP_APPROVED_TREATMENTS = {
    "remove_text_then_embed_background",
    "crop_as_screenshot_exception",
    "vector_rebuild",
    "raster_exception",
    "user_accepts_non_editable_text",
}

STRUCTURE_VECTOR_MODES = {
    "vector-hifi",
    "hifi",
    "full-editable",
    "editable",
    "wps-hifi",
}

SNAPSHOT_MODES = {
    "text-editable-snapshot",
}

ALLOWED_CROP_ROLES = {
    "decorative_background",
    "background_decoration",
    "footer_line_art",
    "footer_grid",
    "complex_background",
    "texture",
    "ambient_texture",
    "dense_infrastructure",
    "complex_small_icon",
    "small_complex_icon",
    "logo",
    "photo",
    "product_photo",
    "screenshot_exception",
    "ui_screenshot",
}

FORBIDDEN_STRUCTURE_ROLE_KEYWORDS = {
    "card",
    "border",
    "arrow",
    "connector",
    "center",
    "node",
    "circle",
    "process",
    "flow",
    "body",
    "text",
    "title",
    "subtitle",
    "conclusion",
    "main",
    "diagram",
}


@dataclass
class Finding:
    level: str
    code: str
    message: str
    path: str = ""

    def as_dict(self) -> dict[str, str]:
        payload = {
            "level": self.level,
            "code": self.code,
            "message": self.message,
        }
        if self.path:
            payload["path"] = self.path
        return payload


def _load_json(path: Path) -> dict[str, Any]:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}


def _regions(payload: dict[str, Any]) -> list[dict[str, Any]]:
    if isinstance(payload.get("regions"), list):
        page_id = str(payload.get("page_id", ""))
        return [
            {**region, "page_id": str(region.get("page_id") or page_id)}
            for region in payload.get("regions", [])
            if isinstance(region, dict)
        ]
    regions: list[dict[str, Any]] = []
    for page in payload.get("pages", []) if isinstance(payload.get("pages"), list) else []:
        if not isinstance(page, dict):
            continue
        page_id = str(page.get("page_id", ""))
        for region in page.get("regions", []) if isinstance(page.get("regions"), list) else []:
            if isinstance(region, dict):
                regions.append({**region, "page_id": str(region.get("page_id") or page_id)})
    return regions


def _bbox(value: Any) -> tuple[float, float, float, float] | None:
    if not isinstance(value, list) or len(value) != 4:
        return None
    try:
        x, y, w, h = (float(item) for item in value)
    except (TypeError, ValueError):
        return None
    return x, y, w, h


def _area(box: tuple[float, float, float, float]) -> float:
    return max(box[2], 0.0) * max(box[3], 0.0)


def _overlap_ratio(
    image_box: tuple[float, float, float, float],
    text_box: tuple[float, float, float, float],
) -> float:
    ix, iy, iw, ih = image_box
    tx, ty, tw, th = text_box
    left = max(ix, tx)
    top = max(iy, ty)
    right = min(ix + iw, tx + tw)
    bottom = min(iy + ih, ty + th)
    if right <= left or bottom <= top:
        return 0.0
    text_area = _area(text_box)
    if text_area <= 0:
        return 0.0
    return ((right - left) * (bottom - top)) / text_area


def _has_reason(item: dict[str, Any]) -> bool:
    return bool(str(item.get("reason", "")).strip())


def _token_blob(item: dict[str, Any]) -> str:
    parts = [
        item.get("id", ""),
        item.get("svg_element_id", ""),
        item.get("href", ""),
        item.get("crop_role", ""),
        item.get("recommended_treatment", ""),
    ]
    return " ".join(str(part).lower() for part in parts if part)


def _is_forbidden_structure_crop(crop: dict[str, Any]) -> bool:
    role = str(crop.get("crop_role", "")).strip().lower()
    if role and role in ALLOWED_CROP_ROLES:
        return False
    blob = _token_blob(crop)
    return any(keyword in blob for keyword in FORBIDDEN_STRUCTURE_ROLE_KEYWORDS)


def _check_text_regions(
    project: Path,
    regions: list[dict[str, Any]],
    findings: list[Finding],
) -> None:
    for region in regions:
        region_id = str(region.get("id", "unnamed"))
        treatment = str(region.get("final_treatment", "") or region.get("treatment", ""))
        if not treatment:
            findings.append(Finding(
                "error",
                "text_region_missing_treatment",
                f"Text region `{region_id}` has no final_treatment; use editable_text or an explicit exception.",
                str(project / "text_region_map.json"),
            ))
            continue
        if treatment not in TEXT_APPROVED_TREATMENTS:
            findings.append(Finding(
                "error",
                "text_region_unapproved_treatment",
                f"Text region `{region_id}` uses unsupported treatment `{treatment}`.",
                str(project / "text_region_map.json"),
            ))
        if treatment in {"raster_exception", "user_accepts_non_editable_text"} and not _has_reason(region):
            findings.append(Finding(
                "error",
                "text_region_exception_missing_reason",
                f"Text region `{region_id}` keeps text non-editable but has no reason.",
                str(project / "text_region_map.json"),
            ))


def _check_crops(
    project: Path,
    crops: list[dict[str, Any]],
    regions: list[dict[str, Any]],
    findings: list[Finding],
    *,
    mode: str,
) -> None:
    regions_by_page: dict[str, list[dict[str, Any]]] = {}
    for region in regions:
        regions_by_page.setdefault(str(region.get("page_id", "")), []).append(region)

    for crop in crops:
        crop_id = str(crop.get("id", "unnamed"))
        path = str(project / "image_crops_manifest.json")
        area_ratio = float(crop.get("area_ratio", 0) or 0)
        source_kind = str(crop.get("source_kind", ""))
        crop_role = str(crop.get("crop_role", "")).strip().lower()
        contains_text = crop.get("contains_text")
        text_removed = bool(crop.get("text_removed"))
        treatment = str(crop.get("treatment", ""))
        flags = crop.get("risk_flags", [])
        if not isinstance(flags, list):
            flags = []

        if area_ratio >= FULL_SLIDE_RATIO:
            if mode in SNAPSHOT_MODES:
                if not _has_reason(crop):
                    findings.append(Finding(
                        "error",
                        "snapshot_mode_missing_user_acceptance",
                        f"Image crop `{crop_id}` covers {area_ratio:.0%} of the slide; snapshot mode requires a recorded user acceptance reason.",
                        path,
                    ))
            else:
                findings.append(Finding(
                    "error",
                    "near_full_slide_image",
                    f"Image crop `{crop_id}` covers {area_ratio:.0%} of the slide; full-slide reference images are forbidden.",
                    path,
                ))

        if mode in STRUCTURE_VECTOR_MODES:
            if crop_role and crop_role not in ALLOWED_CROP_ROLES and _is_forbidden_structure_crop(crop):
                findings.append(Finding(
                    "error",
                    "structure_crop_forbidden",
                    f"Image crop `{crop_id}` is marked as `{crop_role}`; main structure must be rebuilt as editable vectors, not cropped.",
                    path,
                ))
            elif crop_role and crop_role not in ALLOWED_CROP_ROLES:
                findings.append(Finding(
                    "warning",
                    "unknown_crop_role",
                    f"Image crop `{crop_id}` uses unknown crop_role `{crop_role}`; use a decorative/small-icon/screenshot role or rebuild it as vectors.",
                    path,
                ))
            elif not crop_role and _is_forbidden_structure_crop(crop):
                findings.append(Finding(
                    "error",
                    "structure_crop_forbidden",
                    f"Image crop `{crop_id}` appears to carry card/arrow/connector/text/main-structure content; rebuild that structure as editable vectors.",
                    path,
                ))
            elif not crop_role and area_ratio >= STRUCTURE_CROP_LARGE_RATIO and source_kind in {"reference_with_text", "reference_image", "crop"}:
                findings.append(Finding(
                    "warning",
                    "crop_role_missing_for_vector_hifi",
                    f"Image crop `{crop_id}` is a sizable reference-derived crop; set data-crop-role to a decorative/small-icon role or rebuild it as vectors.",
                    path,
                ))

        if source_kind in {"reference_with_text", "reference_image"} and not treatment:
            findings.append(Finding(
                "error",
                "reference_image_without_treatment",
                f"Image crop `{crop_id}` comes from a reference image and needs an explicit treatment.",
                path,
            ))

        if contains_text is True:
            if treatment not in CROP_APPROVED_TREATMENTS:
                findings.append(Finding(
                    "error",
                    "text_bearing_crop_unapproved",
                    f"Image crop `{crop_id}` contains text but has no approved treatment.",
                    path,
                ))
            if treatment == "remove_text_then_embed_background" and not text_removed:
                findings.append(Finding(
                    "error",
                    "text_bearing_crop_not_cleaned",
                    f"Image crop `{crop_id}` claims text removal treatment but text_removed is not true.",
                    path,
                ))
            if treatment in {"crop_as_screenshot_exception", "raster_exception", "user_accepts_non_editable_text"} and not _has_reason(crop):
                findings.append(Finding(
                    "error",
                    "text_bearing_crop_exception_missing_reason",
                    f"Image crop `{crop_id}` keeps raster text but has no reason.",
                    path,
                ))
        elif contains_text is None and ("source_reference_image" in flags or area_ratio >= 0.35):
            findings.append(Finding(
                "warning",
                "crop_text_status_unknown",
                f"Image crop `{crop_id}` is high risk; set contains_text true/false in image_crops_manifest.json.",
                path,
            ))

        image_box = _bbox(crop.get("bbox"))
        if image_box is None:
            continue
        for region in regions_by_page.get(str(crop.get("page_id", "")), []):
            text_box = _bbox(region.get("bbox"))
            if text_box is None:
                continue
            overlap = _overlap_ratio(image_box, text_box)
            if overlap < OVERLAP_WARNING_RATIO:
                continue
            region_id = str(region.get("id", "unnamed"))
            if contains_text is True and not text_removed:
                findings.append(Finding(
                    "error",
                    "text_region_overlaps_unclean_image",
                    f"Text region `{region_id}` overlaps text-bearing image crop `{crop_id}` by {overlap:.0%}.",
                    path,
                ))
            elif contains_text is None:
                findings.append(Finding(
                    "warning",
                    "text_region_overlaps_unknown_image",
                    f"Text region `{region_id}` overlaps image crop `{crop_id}` by {overlap:.0%}; confirm the crop is clean.",
                    path,
                ))


def verify_project(project: Path) -> dict[str, Any]:
    findings: list[Finding] = []
    text_map_path = project / "text_region_map.json"
    manifest_path = project / "image_crops_manifest.json"

    text_map = _load_json(text_map_path)
    manifest = _load_json(manifest_path)

    if not text_map:
        findings.append(Finding(
            "error",
            "missing_text_region_map",
            "text_region_map.json is required. Create it in Step 2.5, even when no text regions are detected.",
            str(text_map_path),
        ))
    if not manifest:
        findings.append(Finding(
            "error",
            "missing_image_crops_manifest",
            "image_crops_manifest.json is required. Run build_image_crops_manifest.py after SVG generation.",
            str(manifest_path),
        ))

    regions = _regions(text_map)
    crops = [
        crop for crop in manifest.get("crops", []) if isinstance(crop, dict)
    ] if isinstance(manifest, dict) else []
    mode = str(manifest.get("rebuild_mode", "vector-hifi")) if isinstance(manifest, dict) else "vector-hifi"

    if text_map:
        _check_text_regions(project, regions, findings)
    if manifest:
        _check_crops(project, crops, regions, findings, mode=mode)

    errors = [finding.as_dict() for finding in findings if finding.level == "error"]
    warnings = [finding.as_dict() for finding in findings if finding.level == "warning"]
    return {
        "valid": not errors,
        "errors": errors,
        "warnings": warnings,
        "text_regions": len(regions),
        "image_crops": len(crops),
        "rebuild_mode": mode,
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Verify text-bearing image handling for slide-image rebuilds.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("project_path", help="Project directory")
    parser.add_argument(
        "--write-report",
        action="store_true",
        help="Write qa_text_bearing_images.json beside the project manifest",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    project = Path(args.project_path).resolve()
    if not project.is_dir():
        print(json.dumps({
            "valid": False,
            "errors": [{
                "level": "error",
                "code": "missing_project",
                "message": f"Project directory not found: {project}",
                "path": str(project),
            }],
            "warnings": [],
        }, ensure_ascii=False, indent=2))
        return 1

    result = verify_project(project)
    if args.write_report:
        report_path = project / "qa_text_bearing_images.json"
        report_path.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["valid"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
