#!/usr/bin/env python3
"""Harvest approved reference-image crop candidates into a project asset manifest.

The tool is deliberately conservative: it only materializes crop candidates
that layout_reference.json already marks as non-structural asset/fallback
candidates, and it reuses crop_policy_lib to block text/card/connector/main
structure substitutions.
"""

from __future__ import annotations

import argparse
import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from PIL import Image

try:
    from crop_intake_summary import DEFAULT_NORMALIZED_IMAGE, DEFAULT_SOURCE_META
    from crop_policy_lib import crop_bbox_px, is_forbidden_structural_crop, validate_precrop_eligible
    from layout_reference_rebuild2_lib import is_rebuild2
except ImportError:  # pragma: no cover
    from scripts.crop_intake_summary import DEFAULT_NORMALIZED_IMAGE, DEFAULT_SOURCE_META  # type: ignore
    from scripts.crop_policy_lib import crop_bbox_px, is_forbidden_structural_crop, validate_precrop_eligible  # type: ignore
    from scripts.layout_reference_rebuild2_lib import is_rebuild2  # type: ignore


ASSET_INTENTS = {"asset"}
FALLBACK_INTENTS = {"fallback"}
DEFAULT_OUT_DIR = "images/harvested_assets"
MANIFEST_NAME = "image_asset_manifest.json"


@dataclass
class HarvestItem:
    id: str
    page_id: str
    path: str
    source_candidate_id: str
    bbox_px: list[int]
    editability_intent: str
    crop_role: str
    treatment: str
    warnings: list[str] = field(default_factory=list)

    def as_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "page_id": self.page_id,
            "kind": "reference_crop_asset",
            "path": self.path,
            "source": "layout_reference.crop_candidates",
            "source_candidate_id": self.source_candidate_id,
            "bbox_px": self.bbox_px,
            "editability_intent": self.editability_intent,
            "crop_role": self.crop_role,
            "treatment": self.treatment,
            "warnings": list(self.warnings),
        }


def _load_json(path: Path) -> dict[str, Any]:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _relative_to(project: Path, path: Path) -> str:
    try:
        return path.resolve().relative_to(project.resolve()).as_posix()
    except ValueError:
        return path.as_posix()


def _page_id_from_layout(layout_path: Path, layout: dict[str, Any]) -> str:
    raw = layout.get("page_id")
    page_block = layout.get("page")
    if not raw and isinstance(page_block, dict):
        raw = page_block.get("page_id")
    if isinstance(raw, str) and raw.strip():
        return raw.strip()
    if layout_path.parent.name.startswith("P"):
        return layout_path.parent.name
    return "P01"


def _layout_paths(project: Path) -> list[Path]:
    manifest = _load_json(project / "slide_image_rebuild_manifest.json")
    paths: list[Path] = []
    pages = manifest.get("pages")
    if isinstance(pages, list):
        for page in pages:
            if not isinstance(page, dict):
                continue
            page_dir_raw = page.get("page_dir") or page.get("page_project") or page.get("project_path")
            if isinstance(page_dir_raw, str) and page_dir_raw.strip():
                page_dir = Path(page_dir_raw)
                if not page_dir.is_absolute():
                    page_dir = project / page_dir
            else:
                page_id = str(page.get("page_id", "")).strip()
                page_dir = project / "pages" / page_id if page_id else project
            layout = page_dir / str(page.get("layout_reference", "layout_reference.json"))
            if layout.is_file():
                paths.append(layout)
    root = project / "layout_reference.json"
    if root.is_file():
        paths.append(root)
    deduped: dict[str, Path] = {}
    for path in paths:
        deduped[str(path.resolve())] = path
    return list(deduped.values())


def _resolve_source_image(project: Path, layout: dict[str, Any], explicit: Path | None) -> Path | None:
    if explicit is not None:
        candidates = [explicit] if explicit.is_absolute() else [project / explicit, explicit]
        for path in candidates:
            if path.is_file():
                return path.resolve()
        return None

    meta_path = project / DEFAULT_SOURCE_META
    if meta_path.is_file():
        meta = _load_json(meta_path)
        normalized = meta.get("normalized")
        if isinstance(normalized, str) and normalized.strip():
            path = Path(normalized)
            if not path.is_absolute():
                path = project / path
            if path.is_file():
                return path.resolve()

    source_ref = layout.get("source_reference")
    if isinstance(source_ref, dict):
        for key in ["normalized_path", "path"]:
            raw = source_ref.get(key)
            if isinstance(raw, str) and raw.strip():
                path = Path(raw)
                if not path.is_absolute():
                    path = project / path
                if path.is_file():
                    return path.resolve()

    for fallback in [
        project / DEFAULT_NORMALIZED_IMAGE,
        project / "images/reference_layout.png",
        project / "images/reference_pages/P01.png",
    ]:
        if fallback.is_file():
            return fallback.resolve()
    return None


def _candidate_allowed(
    candidate: dict[str, Any],
    layout: dict[str, Any],
    *,
    rebuild2: bool,
    include_fallback: bool,
) -> tuple[bool, list[str], list[str]]:
    errors: list[str] = []
    warnings: list[str] = []
    intent = str(candidate.get("editability_intent", "")).strip()
    allowed_intents = set(ASSET_INTENTS)
    if include_fallback:
        allowed_intents.update(FALLBACK_INTENTS)
    if intent not in allowed_intents:
        return False, errors, warnings
    if candidate.get("needs_review") is True:
        errors.append(f"{candidate.get('id', '<unnamed>')}: needs_review=true blocks automatic asset harvesting")
    if is_forbidden_structural_crop(candidate, rebuild2=rebuild2):
        errors.append(f"{candidate.get('id', '<unnamed>')}: structural crop is forbidden")

    probe = dict(candidate)
    probe["precrop"] = {"enabled": True}
    item_errors, item_warnings = validate_precrop_eligible(probe, layout, rebuild2=rebuild2)
    errors.extend(item_errors)
    warnings.extend(item_warnings)
    return not errors, errors, warnings


def _asset_treatment(candidate: dict[str, Any]) -> str:
    role = str(candidate.get("crop_role") or candidate.get("role") or candidate.get("recommended_treatment") or "").lower()
    if "icon" in role:
        return "small_icon_crop"
    if "photo" in role:
        return "photo_crop"
    if "logo" in role:
        return "logo_crop"
    return "decorative_crop"


def harvest_assets(
    project: Path,
    *,
    source_image: Path | None = None,
    out_dir: Path | None = None,
    include_fallback: bool = False,
    write_report: bool = True,
) -> dict[str, Any]:
    project = project.resolve()
    target_root = out_dir or project / DEFAULT_OUT_DIR
    if not target_root.is_absolute():
        target_root = project / target_root
    layouts = _layout_paths(project)
    errors: list[str] = []
    warnings: list[str] = []
    items: list[HarvestItem] = []
    skipped: list[dict[str, Any]] = []

    for layout_path in layouts:
        layout = _load_json(layout_path)
        if not layout:
            warnings.append(f"Skip invalid layout JSON: {layout_path}")
            continue
        page_id = _page_id_from_layout(layout_path, layout)
        src = _resolve_source_image(project, layout, source_image)
        if src is None:
            warnings.append(f"Page {page_id}: source image not found; skip asset harvesting")
            continue
        candidates = layout.get("crop_candidates", [])
        if not isinstance(candidates, list):
            continue
        use_rebuild2 = is_rebuild2(layout)
        with Image.open(src) as image:
            rgba = image.convert("RGBA")
            page_out = target_root / page_id
            for index, candidate in enumerate(candidates):
                if not isinstance(candidate, dict):
                    continue
                candidate_id = str(candidate.get("id") or f"crop_{index:02d}")
                allowed, item_errors, item_warnings = _candidate_allowed(
                    candidate,
                    layout,
                    rebuild2=use_rebuild2,
                    include_fallback=include_fallback,
                )
                if not allowed:
                    if item_errors:
                        skipped.append({"id": candidate_id, "page_id": page_id, "reasons": item_errors})
                    continue
                bbox = crop_bbox_px(candidate)
                if bbox is None:
                    errors.append(f"{candidate_id}: bbox_px must be valid before harvesting")
                    continue
                x, y, w, h = bbox
                left = max(0, min(x, rgba.width - 1))
                top = max(0, min(y, rgba.height - 1))
                right = max(left + 1, min(x + w, rgba.width))
                bottom = max(top + 1, min(y + h, rgba.height))
                page_out.mkdir(parents=True, exist_ok=True)
                filename = f"{candidate_id}.png"
                out_path = page_out / filename
                rgba.crop((left, top, right, bottom)).save(out_path)
                items.append(HarvestItem(
                    id=f"{page_id}_{candidate_id}",
                    page_id=page_id,
                    path=_relative_to(project, out_path),
                    source_candidate_id=candidate_id,
                    bbox_px=[left, top, right - left, bottom - top],
                    editability_intent=str(candidate.get("editability_intent", "")),
                    crop_role=str(candidate.get("crop_role") or candidate.get("role") or ""),
                    treatment=_asset_treatment(candidate),
                    warnings=item_warnings,
                ))

    manifest = {
        "workflow": "slide-image-rebuild",
        "version": "1.0",
        "generated_by": "harvest_reference_assets.py",
        "policy": {
            "source": "layout_reference.crop_candidates",
            "allowed_intents": sorted(ASSET_INTENTS | (FALLBACK_INTENTS if include_fallback else set())),
            "forbidden": "text/card/connector/main-structure crops",
            "output_dir": _relative_to(project, target_root),
        },
        "valid": not errors,
        "errors": errors,
        "warnings": warnings,
        "skipped": skipped,
        "assets": [item.as_dict() for item in items],
        "summary": {
            "layout_files": len(layouts),
            "assets_written": len(items),
            "skipped": len(skipped),
        },
    }
    if write_report:
        _write_json(project / MANIFEST_NAME, manifest)
    return manifest


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Harvest approved reference crop candidates into image_asset_manifest.json.")
    parser.add_argument("project", type=Path)
    parser.add_argument("--source-image", type=Path, help="Override reference/normalized source image")
    parser.add_argument("--out-dir", type=Path, help=f"Output directory, default {DEFAULT_OUT_DIR}")
    parser.add_argument("--include-fallback", action="store_true", help="Also harvest editability_intent=fallback candidates")
    parser.add_argument("--no-write-report", action="store_true", help="Do not write image_asset_manifest.json")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    payload = harvest_assets(
        args.project,
        source_image=args.source_image,
        out_dir=args.out_dir,
        include_fallback=args.include_fallback,
        write_report=not args.no_write_report,
    )
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0 if payload["valid"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
