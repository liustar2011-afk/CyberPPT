#!/usr/bin/env python3
"""
Slide-image-rebuild manifest resolution helpers (text granularity, export hints).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

ALLOWED_TEXT_GRANULARITY = frozenset({"paragraph_editable", "visual_line_lock"})
ALLOWED_TEXT_DENSITY = frozenset({"standard", "dense_formal_cn"})
ALLOWED_FIT_STRATEGIES = frozenset({
    "shrink_then_wrap_then_truncate",
    "wrap_then_shrink",
    "wrap_only",
})

DEFAULT_DENSE_FORMAL_CN_POLICY: dict[str, Any] = {
    "font_family": "Microsoft YaHei",
    "min_font_size_pt": 7.5,
    "max_font_size_pt": 12.0,
    "line_height_ratio": 1.12,
    "prefer_visual_line_lock": True,
    "fit_strategy": "shrink_then_wrap_then_truncate",
}


@dataclass(frozen=True)
class TextGranularityResolution:
    text_granularity: str
    text_density: str
    force_hifi_export: bool
    errors: tuple[str, ...]
    error_codes: tuple[str, ...]
    warnings: tuple[str, ...]

    def as_dict(self) -> dict[str, Any]:
        return {
            "text_granularity": self.text_granularity,
            "text_density": self.text_density,
            "force_hifi_export": self.force_hifi_export,
            "errors": list(self.errors),
            "error_codes": list(self.error_codes),
            "warnings": list(self.warnings),
        }


def _normalized(manifest: dict[str, Any], key: str, default: str) -> str:
    raw = manifest.get(key)
    if not isinstance(raw, str) or not raw.strip():
        return default
    return raw.strip()


def resolve_text_granularity(manifest: dict[str, Any]) -> TextGranularityResolution:
    errors: list[str] = []
    error_codes: list[str] = []
    warnings: list[str] = []

    granularity = _normalized(manifest, "text_granularity", "paragraph_editable")
    density = _normalized(manifest, "text_density", "standard")

    if granularity not in ALLOWED_TEXT_GRANULARITY:
        error_codes.append("invalid_text_granularity")
        errors.append(
            "text_granularity must be one of: "
            + ", ".join(sorted(ALLOWED_TEXT_GRANULARITY))
            + ".",
        )
    if density not in ALLOWED_TEXT_DENSITY:
        error_codes.append("invalid_text_density")
        errors.append(
            "text_density must be one of: "
            + ", ".join(sorted(ALLOWED_TEXT_DENSITY))
            + ".",
        )

    force_hifi = (
        granularity == "visual_line_lock"
        or density == "dense_formal_cn"
    )
    export_mode = _normalized(manifest, "pptx_export_mode", "")
    if force_hifi and export_mode == "editable":
        error_codes.append("visual_line_lock_conflicts_with_editable_export")
        errors.append(
            "visual_line_lock / dense_formal_cn requires pptx_export_mode hifi or wps-hifi, not editable.",
        )
    elif force_hifi and not export_mode:
        warnings.append(
            "text_granularity visual_line_lock or dense_formal_cn defaults export to hifi for fidelity.",
        )

    return TextGranularityResolution(
        text_granularity=granularity,
        text_density=density,
        force_hifi_export=force_hifi,
        errors=tuple(errors),
        error_codes=tuple(error_codes),
        warnings=tuple(warnings),
    )


@dataclass(frozen=True)
class TextLayoutPolicyResolution:
    policy: dict[str, Any]
    errors: tuple[str, ...]
    error_codes: tuple[str, ...]
    warnings: tuple[str, ...]

    def as_dict(self) -> dict[str, Any]:
        return {
            "policy": self.policy,
            "errors": list(self.errors),
            "error_codes": list(self.error_codes),
            "warnings": list(self.warnings),
        }


def default_text_layout_policy(*, text_density: str = "standard") -> dict[str, Any]:
    if text_density == "dense_formal_cn":
        return dict(DEFAULT_DENSE_FORMAL_CN_POLICY)
    return {
        "font_family": "Microsoft YaHei",
        "min_font_size_pt": 9.0,
        "max_font_size_pt": 14.0,
        "line_height_ratio": 1.2,
        "prefer_visual_line_lock": False,
        "fit_strategy": "shrink_then_wrap_then_truncate",
    }


def _coerce_positive_float(value: Any, field: str, errors: list[str], error_codes: list[str]) -> float | None:
    if not isinstance(value, (int, float)):
        errors.append(f"text_layout_policy.{field} must be a number.")
        error_codes.append(f"invalid_text_layout_policy_{field}")
        return None
    number = float(value)
    if number <= 0:
        errors.append(f"text_layout_policy.{field} must be positive.")
        error_codes.append(f"invalid_text_layout_policy_{field}")
        return None
    return number


def resolve_text_layout_policy(manifest: dict[str, Any]) -> TextLayoutPolicyResolution:
    errors: list[str] = []
    error_codes: list[str] = []
    warnings: list[str] = []

    density = _normalized(manifest, "text_density", "standard")
    raw = manifest.get("text_layout_policy")
    if raw is None:
        return TextLayoutPolicyResolution(
            policy=default_text_layout_policy(text_density=density),
            errors=tuple(),
            error_codes=tuple(),
            warnings=tuple(
                ["text_layout_policy omitted; using defaults for text_density."]
                if density != "standard"
                else []
            ),
        )
    if not isinstance(raw, dict):
        return TextLayoutPolicyResolution(
            policy=default_text_layout_policy(text_density=density),
            errors=("text_layout_policy must be an object.",),
            error_codes=("invalid_text_layout_policy",),
            warnings=tuple(),
        )

    policy = default_text_layout_policy(text_density=density)
    policy.update(raw)

    font_family = policy.get("font_family")
    if not isinstance(font_family, str) or not font_family.strip():
        errors.append("text_layout_policy.font_family must be a non-empty string.")
        error_codes.append("invalid_text_layout_policy_font_family")

    min_size = _coerce_positive_float(
        policy.get("min_font_size_pt"), "min_font_size_pt", errors, error_codes,
    )
    max_size = _coerce_positive_float(
        policy.get("max_font_size_pt"), "max_font_size_pt", errors, error_codes,
    )
    line_height = _coerce_positive_float(
        policy.get("line_height_ratio"), "line_height_ratio", errors, error_codes,
    )
    if min_size is not None and max_size is not None and min_size > max_size:
        errors.append("text_layout_policy.min_font_size_pt must be <= max_font_size_pt.")
        error_codes.append("invalid_text_layout_policy_font_range")

    fit_strategy = str(policy.get("fit_strategy", "")).strip()
    if fit_strategy and fit_strategy not in ALLOWED_FIT_STRATEGIES:
        errors.append(
            "text_layout_policy.fit_strategy must be one of: "
            + ", ".join(sorted(ALLOWED_FIT_STRATEGIES))
            + ".",
        )
        error_codes.append("invalid_text_layout_policy_fit_strategy")

    prefer_lock = policy.get("prefer_visual_line_lock")
    if prefer_lock is not None and not isinstance(prefer_lock, bool):
        errors.append("text_layout_policy.prefer_visual_line_lock must be a boolean when present.")
        error_codes.append("invalid_text_layout_policy_prefer_visual_line_lock")

    if density == "dense_formal_cn" and line_height is not None and line_height < 1.05:
        warnings.append("dense_formal_cn usually needs line_height_ratio >= 1.05 for readable CJK stacks.")

    return TextLayoutPolicyResolution(
        policy=policy,
        errors=tuple(errors),
        error_codes=tuple(error_codes),
        warnings=tuple(warnings),
    )
