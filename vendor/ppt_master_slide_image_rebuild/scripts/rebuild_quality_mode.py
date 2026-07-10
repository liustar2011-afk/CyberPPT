#!/usr/bin/env python3
"""
PPT Master - Rebuild Quality Mode Resolver

Map user-facing rebuild_quality_mode aliases to canonical rebuild_mode and
pptx_export_mode values for slide-image-rebuild manifests.

Usage:
    python3 scripts/rebuild_quality_mode.py <slide_image_rebuild_manifest.json>

Examples:
    python3 scripts/rebuild_quality_mode.py projects/demo/slide_image_rebuild_manifest.json

Dependencies:
    None (only uses standard library)
"""

from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

QUALITY_MODE_ALIASES: dict[str, tuple[str, str]] = {
    "balanced": ("vector-hifi", "hifi"),
    "max_editable": ("full-editable", "editable"),
    "visual_locked": ("text-editable-snapshot", "hifi"),
}

ALLOWED_QUALITY_MODES = frozenset(QUALITY_MODE_ALIASES)

SLIDE_IMAGE_REBUILD_WORKFLOW = "slide-image-rebuild"


@dataclass(frozen=True)
class ResolvedRebuildModes:
    rebuild_mode: str | None
    pptx_export_mode: str | None
    rebuild_quality_mode: str | None
    resolved_from_quality_mode: bool
    errors: tuple[str, ...]
    error_codes: tuple[str, ...]
    warnings: tuple[str, ...]

    def as_dict(self) -> dict[str, Any]:
        return {
            "rebuild_mode": self.rebuild_mode,
            "pptx_export_mode": self.pptx_export_mode,
            "rebuild_quality_mode": self.rebuild_quality_mode,
            "resolved_from_quality_mode": self.resolved_from_quality_mode,
            "errors": list(self.errors),
            "error_codes": list(self.error_codes),
            "warnings": list(self.warnings),
        }


def _normalized_quality_mode(manifest: dict[str, Any]) -> str | None:
    raw = manifest.get("rebuild_quality_mode")
    if not isinstance(raw, str) or not raw.strip():
        return None
    return raw.strip()


def _normalized_mode(manifest: dict[str, Any], key: str) -> str | None:
    raw = manifest.get(key)
    if not isinstance(raw, str) or not raw.strip():
        return None
    return raw.strip()


def resolve_rebuild_modes(manifest: dict[str, Any]) -> ResolvedRebuildModes:
    errors: list[str] = []
    error_codes: list[str] = []
    warnings: list[str] = []

    def add_error(code: str, message: str) -> None:
        error_codes.append(code)
        errors.append(message)

    quality_mode = _normalized_quality_mode(manifest)
    explicit_rebuild = _normalized_mode(manifest, "rebuild_mode")
    explicit_export = _normalized_mode(manifest, "pptx_export_mode")

    mapped_rebuild: str | None = None
    mapped_export: str | None = None
    resolved_from_quality = False

    if quality_mode is not None:
        if quality_mode not in ALLOWED_QUALITY_MODES:
            add_error(
                "invalid_rebuild_quality_mode",
                f"rebuild_quality_mode must be one of: {', '.join(sorted(ALLOWED_QUALITY_MODES))}.",
            )
        else:
            mapped_rebuild, mapped_export = QUALITY_MODE_ALIASES[quality_mode]

    if quality_mode is not None and mapped_rebuild and mapped_export:
        if explicit_rebuild and explicit_rebuild != mapped_rebuild:
            add_error(
                "quality_mode_rebuild_mode_mismatch",
                "rebuild_quality_mode conflicts with rebuild_mode; remove one or align both.",
            )
        if explicit_export and explicit_export != mapped_export:
            add_error(
                "quality_mode_pptx_export_mode_mismatch",
                "rebuild_quality_mode conflicts with pptx_export_mode; remove one or align both.",
            )

    if quality_mode is not None and mapped_rebuild and mapped_export and not errors:
        rebuild_mode = explicit_rebuild or mapped_rebuild
        export_mode = explicit_export or mapped_export
        resolved_from_quality = explicit_rebuild is None or explicit_export is None
    else:
        rebuild_mode = explicit_rebuild
        export_mode = explicit_export

    workflow = manifest.get("workflow")
    is_slide_image_rebuild = workflow == SLIDE_IMAGE_REBUILD_WORKFLOW

    if quality_mode == "visual_locked" or rebuild_mode == "text-editable-snapshot":
        has_acceptance = bool(str(manifest.get("user_acceptance", "")).strip())
        if not has_acceptance:
            # Default v2 (structure_contract + vector-hifi) forbids a raster snapshot as
            # the final slide body. text-editable-snapshot is the one documented escape
            # hatch -- it requires an explicit, recorded user_acceptance. Without one,
            # both checks fire so the agent knows exactly what's missing.
            if is_slide_image_rebuild:
                add_error(
                    "visual_locked_incompatible_with_slide_image_rebuild_v2",
                    "visual_locked / text-editable-snapshot is incompatible with slide-image-rebuild "
                    "default v2 (structure_contract + vector-hifi) unless manifest.user_acceptance "
                    "records the user's explicit approval.",
                )
            add_error(
                "snapshot_missing_user_acceptance",
                "text-editable-snapshot requires manifest.user_acceptance explaining the user's approval.",
            )
        elif is_slide_image_rebuild:
            warnings.append(
                "visual_locked / text-editable-snapshot overrides slide-image-rebuild default v2 "
                f"on recorded user_acceptance: {manifest.get('user_acceptance', '')!r}."
            )

    return ResolvedRebuildModes(
        rebuild_mode=rebuild_mode,
        pptx_export_mode=export_mode,
        rebuild_quality_mode=quality_mode,
        resolved_from_quality_mode=resolved_from_quality,
        errors=tuple(errors),
        error_codes=tuple(error_codes),
        warnings=tuple(warnings),
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Resolve rebuild_quality_mode aliases in a slide-image rebuild manifest.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("manifest", type=Path, help="Path to slide_image_rebuild_manifest.json")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        manifest = json.loads(args.manifest.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        payload = {"valid": False, "errors": [str(exc)], "warnings": []}
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return 1
    resolved = resolve_rebuild_modes(manifest)
    payload = {
        "valid": not resolved.errors,
        **resolved.as_dict(),
    }
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0 if payload["valid"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
