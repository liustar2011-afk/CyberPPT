#!/usr/bin/env python3
"""
PPT Master - Layout Candidate Precrop

Materialize PNG crops for layout_reference.json crop_candidates with precrop.enabled.

Usage:
    python3 scripts/precrop_layout_candidates.py <project_or_page_dir>
    python3 scripts/precrop_layout_candidates.py <project_path> --write-back --rebuild2

Examples:
    python3 scripts/precrop_layout_candidates.py projects/demo --source-image images/reference_layout.normalized.png
    python3 scripts/precrop_layout_candidates.py projects/demo --write-back --out-dir images/precrops

Dependencies:
    Pillow
"""

from __future__ import annotations

import argparse
import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from PIL import Image

try:
    from crop_intake_summary import DEFAULT_NORMALIZED_IMAGE, DEFAULT_SOURCE_META, summarize_crop_candidates
    from crop_policy_lib import (
        crop_bbox_px,
        precrop_enabled_candidates,
        validate_precrop_eligible,
    )
    from layout_reference_rebuild2_lib import is_rebuild2
except ImportError:  # pragma: no cover
    from scripts.crop_intake_summary import DEFAULT_NORMALIZED_IMAGE, DEFAULT_SOURCE_META, summarize_crop_candidates  # type: ignore
    from scripts.crop_policy_lib import (  # type: ignore
        crop_bbox_px,
        precrop_enabled_candidates,
        validate_precrop_eligible,
    )
    from scripts.layout_reference_rebuild2_lib import is_rebuild2  # type: ignore


@dataclass
class PrecropItemResult:
    id: str
    index: int
    output_path: str
    written: bool
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


@dataclass
class PrecropResult:
    valid: bool
    project: str
    layout_path: str
    source_image: str
    out_dir: str
    write_back: bool
    rebuild2: bool
    errors: list[str]
    warnings: list[str]
    items: list[PrecropItemResult]

    def as_dict(self, *, layout: dict[str, Any] | None = None) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "valid": self.valid,
            "project": self.project,
            "layout_path": self.layout_path,
            "source_image": self.source_image,
            "out_dir": self.out_dir,
            "write_back": self.write_back,
            "rebuild2": self.rebuild2,
            "errors": self.errors,
            "warnings": self.warnings,
            "items": [
                {
                    "id": item.id,
                    "index": item.index,
                    "output_path": item.output_path,
                    "written": item.written,
                    "errors": item.errors,
                    "warnings": item.warnings,
                }
                for item in self.items
            ],
        }
        if layout is not None:
            summary = summarize_crop_candidates(layout)
            payload["crop_candidates_summary"] = summary.as_dict()
            payload["precrop_files_written"] = sum(1 for item in self.items if item.written)
        return payload


def _load_json(path: Path) -> dict[str, Any]:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}


def _manifest_precrop_enabled(project: Path) -> tuple[bool, str]:
    manifest = _load_json(project / "slide_image_rebuild_manifest.json")
    intake = manifest.get("intake", {})
    if not isinstance(intake, dict):
        return False, ""
    block = intake.get("precrop_candidates", {})
    if not isinstance(block, dict):
        return False, ""
    out_dir = str(block.get("output_dir", "images/precrops")).strip() or "images/precrops"
    return block.get("enabled") is True, out_dir


def resolve_layout_path(project: Path, explicit: Path | None) -> Path:
    if explicit is not None and explicit.is_file():
        return explicit
    for candidate in [project / "layout_reference.json", project / "pages" / "P01" / "layout_reference.json"]:
        if candidate.is_file():
            return candidate
    raise SystemExit(f"layout_reference.json not found under {project}")


def resolve_source_image(
    project: Path,
    layout: dict[str, Any],
    *,
    explicit: Path | None = None,
) -> Path:
    if explicit is not None:
        candidates = [explicit] if explicit.is_absolute() else [project / explicit, Path.cwd() / explicit, explicit]
        for path in candidates:
            if path.is_file():
                return path
        raise SystemExit(f"Source image not found: {explicit}")

    meta_path = project / DEFAULT_SOURCE_META
    if meta_path.is_file():
        meta = _load_json(meta_path)
        normalized = meta.get("normalized")
        if isinstance(normalized, str) and normalized.strip():
            norm_path = Path(normalized)
            if not norm_path.is_absolute():
                norm_path = project / norm_path
            if norm_path.is_file():
                return norm_path

    for candidate in layout.get("crop_candidates", []) if isinstance(layout.get("crop_candidates"), list) else []:
        if not isinstance(candidate, dict):
            continue
        precrop = candidate.get("precrop")
        if isinstance(precrop, dict):
            source = precrop.get("source_image")
            if isinstance(source, str) and source.strip():
                source_path = project / source.strip()
                if source_path.is_file():
                    return source_path

    for fallback in [
        project / DEFAULT_NORMALIZED_IMAGE,
        project / "images/reference_layout.png",
        project / "images/reference_pages/P01.png",
    ]:
        if fallback.is_file():
            return fallback

    raise SystemExit(
        f"No source image found under {project}; pass --source-image or run preprocess_reference_image.py"
    )


def _relative_to_project(project: Path, path: Path) -> str:
    try:
        return path.resolve().relative_to(project.resolve()).as_posix()
    except ValueError:
        return path.as_posix()


def _validate_all(
    layout: dict[str, Any],
    *,
    rebuild2: bool,
) -> tuple[list[str], list[str]]:
    errors: list[str] = []
    warnings: list[str] = []
    for index, candidate in precrop_enabled_candidates(layout):
        item_errors, item_warnings = validate_precrop_eligible(
            candidate,
            layout,
            rebuild2=rebuild2,
            index=index,
        )
        errors.extend(item_errors)
        warnings.extend(item_warnings)
    return errors, warnings


def precrop_layout_candidates(
    project: Path,
    *,
    layout_path: Path | None = None,
    source_image: Path | None = None,
    out_dir: Path | None = None,
    write_back: bool = False,
    rebuild2: bool = False,
) -> PrecropResult:
    project = project.resolve()
    layout_file = resolve_layout_path(project, layout_path)
    layout = _load_json(layout_file)
    if not layout:
        raise SystemExit(f"Invalid or empty layout JSON: {layout_file}")

    use_rebuild2 = rebuild2 or is_rebuild2(layout)
    manifest_enabled, manifest_out_dir = _manifest_precrop_enabled(project)
    if write_back and not manifest_enabled:
        return PrecropResult(
            valid=False,
            project=str(project),
            layout_path=str(layout_file),
            source_image="",
            out_dir=str(out_dir or project / manifest_out_dir),
            write_back=write_back,
            rebuild2=use_rebuild2,
            errors=["manifest.intake.precrop_candidates.enabled must be true before --write-back"],
            warnings=[],
            items=[],
        )

    target_out = out_dir or project / manifest_out_dir or project / "images/precrops"
    if not target_out.is_absolute():
        target_out = project / target_out

    errors, warnings = _validate_all(layout, rebuild2=use_rebuild2)
    enabled = precrop_enabled_candidates(layout)
    if not enabled:
        warnings.append("No crop_candidates with precrop.enabled=true")

    items: list[PrecropItemResult] = []
    source_path_str = ""

    if enabled and not errors:
        source_path = resolve_source_image(project, layout, explicit=source_image)
        source_path_str = str(source_path)
        with Image.open(source_path) as image:
            rgb = image.convert("RGB")
            img_w, img_h = rgb.size
            target_out.mkdir(parents=True, exist_ok=True)
            for index, candidate in enabled:
                candidate_id = str(candidate.get("id", f"crop_{index}"))
                bbox = crop_bbox_px(candidate)
                item_errors: list[str] = []
                item_warnings: list[str] = []
                output_file = target_out / f"{candidate_id}.png"
                rel_output = _relative_to_project(project, output_file)
                written = False
                if bbox is None:
                    item_errors.append("invalid bbox_px")
                else:
                    x, y, w, h = bbox
                    left = max(0, min(x, img_w - 1))
                    top = max(0, min(y, img_h - 1))
                    right = max(left + 1, min(x + w, img_w))
                    bottom = max(top + 1, min(y + h, img_h))
                    crop = rgb.crop((left, top, right, bottom))
                    crop.save(output_file)
                    written = True
                    if write_back:
                        precrop = candidate.setdefault("precrop", {})
                        if isinstance(precrop, dict):
                            precrop["enabled"] = True
                            precrop["file"] = rel_output
                            precrop.setdefault("source_image", _relative_to_project(project, source_path))
                items.append(PrecropItemResult(
                    id=candidate_id,
                    index=index,
                    output_path=str(output_file),
                    written=written,
                    errors=item_errors,
                    warnings=item_warnings,
                ))
                errors.extend(item_errors)
                warnings.extend(item_warnings)

    if write_back and not errors:
        layout_file.write_text(json.dumps(layout, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    return PrecropResult(
        valid=not errors,
        project=str(project),
        layout_path=str(layout_file),
        source_image=source_path_str,
        out_dir=str(target_out),
        write_back=write_back,
        rebuild2=use_rebuild2,
        errors=errors,
        warnings=warnings,
        items=items,
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Precrop layout_reference crop_candidates to PNG files.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("project_path", type=Path, help="Project or page directory")
    parser.add_argument("--layout", type=Path, help="Path to layout_reference.json")
    parser.add_argument("--source-image", type=Path, help="Reference image to crop from")
    parser.add_argument("--out-dir", type=Path, help="Output directory for PNG precrops")
    parser.add_argument(
        "--write-back",
        action="store_true",
        help="Update layout_reference.json precrop.file paths (requires manifest intake.precrop_candidates.enabled)",
    )
    parser.add_argument(
        "--rebuild2",
        action="store_true",
        help="Apply rebuild-2 crop policy and structure_contract cross-checks",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    project = args.project_path.resolve()
    if not project.is_dir():
        payload = {"valid": False, "errors": [f"Project directory not found: {project}"], "warnings": []}
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return 1

    result = precrop_layout_candidates(
        project,
        layout_path=args.layout,
        source_image=args.source_image,
        out_dir=args.out_dir,
        write_back=args.write_back,
        rebuild2=args.rebuild2,
    )
    layout = _load_json(Path(result.layout_path))
    payload = result.as_dict(layout=layout if layout else None)
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0 if result.valid else 1


if __name__ == "__main__":
    raise SystemExit(main())
