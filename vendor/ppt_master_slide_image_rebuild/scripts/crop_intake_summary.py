#!/usr/bin/env python3
"""
PPT Master - Crop & Intake Summary

Summarize slide-image-rebuild manifest intake settings and layout_reference
crop_candidates for QA reports and regression JSON.

Usage:
    python3 scripts/crop_intake_summary.py <project_path>
    python3 scripts/crop_intake_summary.py <project_path> --page pages/P01

Examples:
    python3 scripts/crop_intake_summary.py projects/demo
    python3 scripts/crop_intake_summary.py fixtures/image_rebuild/crop_candidates_precrop_warn

Dependencies:
    None (only uses standard library; imports rebuild_quality_mode from same directory)
"""

from __future__ import annotations

import argparse
import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

try:
    from rebuild_quality_mode import resolve_rebuild_modes
except ImportError:  # pragma: no cover
    from scripts.rebuild_quality_mode import resolve_rebuild_modes  # type: ignore

try:
    from validate_layout_reference import FORBIDDEN_CROP_TOKENS, _crop_candidate_blob
except ImportError:  # pragma: no cover
    from scripts.validate_layout_reference import FORBIDDEN_CROP_TOKENS, _crop_candidate_blob  # type: ignore

try:
    from layout_reference_rebuild2_lib import is_rebuild2
except ImportError:  # pragma: no cover
    from scripts.layout_reference_rebuild2_lib import is_rebuild2  # type: ignore

DEFAULT_NORMALIZED_IMAGE = "images/reference_layout.normalized.png"
DEFAULT_SOURCE_META = "images/source_meta.json"


@dataclass(frozen=True)
class CropCandidateSummary:
    total: int
    by_editability_intent: dict[str, int]
    needs_review_count: int
    precrop_enabled_count: int
    precrop_missing_file_count: int
    precrop_file_present_count: int
    forbidden_structural_count: int
    ids_needing_review: list[str]

    def as_dict(self) -> dict[str, Any]:
        return {
            "total": self.total,
            "by_editability_intent": dict(self.by_editability_intent),
            "needs_review_count": self.needs_review_count,
            "precrop_enabled_count": self.precrop_enabled_count,
            "precrop_missing_file_count": self.precrop_missing_file_count,
            "precrop_file_present_count": self.precrop_file_present_count,
            "forbidden_structural_count": self.forbidden_structural_count,
            "ids_needing_review": list(self.ids_needing_review),
        }


@dataclass
class IntakeSummary:
    rebuild_quality_mode: str | None
    rebuild_mode: str | None
    pptx_export_mode: str | None
    resolved_from_quality_mode: bool
    preprocess_enabled: bool
    source_meta_present: bool
    normalized_image_present: bool
    source_meta_path: str
    normalized_image_path: str
    precrop_candidates_enabled: bool
    warnings: list[str] = field(default_factory=list)

    def as_dict(self) -> dict[str, Any]:
        return {
            "rebuild_quality_mode": self.rebuild_quality_mode,
            "rebuild_mode": self.rebuild_mode,
            "pptx_export_mode": self.pptx_export_mode,
            "resolved_from_quality_mode": self.resolved_from_quality_mode,
            "preprocess_enabled": self.preprocess_enabled,
            "source_meta_present": self.source_meta_present,
            "normalized_image_present": self.normalized_image_present,
            "source_meta_path": self.source_meta_path,
            "normalized_image_path": self.normalized_image_path,
            "precrop_candidates_enabled": self.precrop_candidates_enabled,
            "warnings": list(self.warnings),
        }


def _load_json(path: Path) -> dict[str, Any]:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}


def _preprocess_paths(project: Path, manifest: dict[str, Any]) -> tuple[Path, Path, bool]:
    intake = manifest.get("intake", {})
    preprocess = intake.get("preprocess", {}) if isinstance(intake, dict) else {}
    if not isinstance(preprocess, dict):
        preprocess = {}
    enabled = preprocess.get("enabled") is True
    meta_rel = str(preprocess.get("meta_json", DEFAULT_SOURCE_META)).strip() or DEFAULT_SOURCE_META
    norm_rel = str(preprocess.get("output_image", DEFAULT_NORMALIZED_IMAGE)).strip() or DEFAULT_NORMALIZED_IMAGE
    meta_path = project / meta_rel
    norm_path = project / norm_rel
    return meta_path, norm_path, enabled


def _precrop_enabled(manifest: dict[str, Any]) -> bool:
    intake = manifest.get("intake", {})
    if not isinstance(intake, dict):
        return False
    block = intake.get("precrop_candidates", {})
    if not isinstance(block, dict):
        return False
    return block.get("enabled") is True


def _manifest_precrop_paths(manifest: dict[str, Any]) -> tuple[bool, str]:
    intake = manifest.get("intake", {})
    if not isinstance(intake, dict):
        return False, "images/precrops"
    block = intake.get("precrop_candidates", {})
    if not isinstance(block, dict):
        return False, "images/precrops"
    out_dir = str(block.get("output_dir", "images/precrops")).strip() or "images/precrops"
    return block.get("enabled") is True, out_dir


def resolve_layout_path(project: Path, *, page_dir: Path | None = None) -> Path | None:
    if page_dir is not None:
        candidate = page_dir / "layout_reference.json"
        if candidate.is_file():
            return candidate
    root = project / "layout_reference.json"
    if root.is_file():
        return root
    return None


def summarize_crop_candidates(layout: dict[str, Any], *, project: Path | None = None) -> CropCandidateSummary:
    raw = layout.get("crop_candidates", [])
    candidates = [item for item in raw if isinstance(item, dict)] if isinstance(raw, list) else []
    by_intent: dict[str, int] = {}
    needs_review_count = 0
    precrop_enabled_count = 0
    precrop_missing_file_count = 0
    precrop_file_present_count = 0
    forbidden_structural_count = 0
    ids_needing_review: list[str] = []

    for candidate in candidates:
        intent = str(candidate.get("editability_intent", "unspecified"))
        by_intent[intent] = by_intent.get(intent, 0) + 1
        if candidate.get("needs_review") is True:
            needs_review_count += 1
            candidate_id = str(candidate.get("id", "")).strip()
            if candidate_id:
                ids_needing_review.append(candidate_id)
        precrop = candidate.get("precrop")
        if isinstance(precrop, dict) and precrop.get("enabled") is True:
            precrop_enabled_count += 1
            file_ref = str(precrop.get("file", "")).strip()
            if not file_ref:
                precrop_missing_file_count += 1
            elif project is not None:
                file_path = project / file_ref
                if file_path.is_file():
                    precrop_file_present_count += 1
                else:
                    precrop_missing_file_count += 1
        blob = _crop_candidate_blob(candidate)
        if any(token in blob for token in FORBIDDEN_CROP_TOKENS):
            forbidden_structural_count += 1

    return CropCandidateSummary(
        total=len(candidates),
        by_editability_intent=by_intent,
        needs_review_count=needs_review_count,
        precrop_enabled_count=precrop_enabled_count,
        precrop_missing_file_count=precrop_missing_file_count,
        precrop_file_present_count=precrop_file_present_count,
        forbidden_structural_count=forbidden_structural_count,
        ids_needing_review=ids_needing_review,
    )


def summarize_intake(project: Path, manifest: dict[str, Any] | None = None) -> IntakeSummary:
    manifest = manifest if manifest is not None else _load_json(project / "slide_image_rebuild_manifest.json")
    resolved = resolve_rebuild_modes(manifest) if manifest else resolve_rebuild_modes({})
    meta_path, norm_path, preprocess_enabled = _preprocess_paths(project, manifest)
    warnings: list[str] = list(resolved.warnings)
    if preprocess_enabled and not meta_path.is_file():
        warnings.append("preprocess_meta_missing")
    if preprocess_enabled and not norm_path.is_file():
        warnings.append("preprocess_normalized_image_missing")
    if _precrop_enabled(manifest):
        enabled, out_dir_rel = _manifest_precrop_paths(manifest)
        if enabled:
            out_dir = project / out_dir_rel
            has_png = out_dir.is_dir() and any(out_dir.glob("*.png"))
            if not has_png:
                warnings.append("precrop_pngs_pending")
    return IntakeSummary(
        rebuild_quality_mode=resolved.rebuild_quality_mode,
        rebuild_mode=resolved.rebuild_mode,
        pptx_export_mode=resolved.pptx_export_mode,
        resolved_from_quality_mode=resolved.resolved_from_quality_mode,
        preprocess_enabled=preprocess_enabled,
        source_meta_present=meta_path.is_file(),
        normalized_image_present=norm_path.is_file(),
        source_meta_path=str(meta_path),
        normalized_image_path=str(norm_path),
        precrop_candidates_enabled=_precrop_enabled(manifest),
        warnings=warnings,
    )


def summarize_page(project: Path, *, page_dir: Path | None = None) -> dict[str, Any]:
    layout_path = resolve_layout_path(project, page_dir=page_dir)
    layout: dict[str, Any] = _load_json(layout_path) if layout_path else {}
    manifest = _load_json(project / "slide_image_rebuild_manifest.json")
    intake = summarize_intake(project, manifest) if manifest else None
    crop = summarize_crop_candidates(layout, project=project) if layout else CropCandidateSummary(
        total=0,
        by_editability_intent={},
        needs_review_count=0,
        precrop_enabled_count=0,
        precrop_missing_file_count=0,
        precrop_file_present_count=0,
        forbidden_structural_count=0,
        ids_needing_review=[],
    )
    decorative_noise = layout.get("decorative_noise", [])
    noise_count = len(decorative_noise) if isinstance(decorative_noise, list) else 0
    crop_warnings: list[str] = []
    if crop.needs_review_count > 0:
        crop_warnings.append("crop_candidates_need_review")
    if crop.precrop_missing_file_count > 0:
        crop_warnings.append("crop_precrop_file_missing")
    if crop.total == 0 and layout and is_rebuild2(layout) and noise_count > 0:
        crop_warnings.append("crop_candidates_empty_with_noise")
    return {
        "project": str(project),
        "layout_path": str(layout_path) if layout_path else "",
        "intake_summary": intake.as_dict() if intake else None,
        "crop_candidates_summary": crop.as_dict(),
        "crop_warnings": crop_warnings,
        "decorative_noise_count": noise_count,
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Summarize manifest intake and crop_candidates for QA.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("project_path", type=Path, help="Project or fixture directory")
    parser.add_argument("--page", type=Path, help="Optional page subdirectory (e.g. pages/P01)")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    project = args.project_path.resolve()
    page_dir = args.page.resolve() if args.page else None
    if page_dir is not None and not page_dir.is_absolute():
        page_dir = (project / page_dir).resolve()
    payload = summarize_page(project, page_dir=page_dir)
    payload["valid"] = True
    payload["returncode"] = 0
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
