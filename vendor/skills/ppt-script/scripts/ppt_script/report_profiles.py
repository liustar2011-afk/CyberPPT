from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml


REQUIRED_REPORTING_FIELDS = (
    "report_subtype",
    "decision_intent",
    "audience_level",
    "project_phase",
)


@dataclass(frozen=True, slots=True)
class ReportingProfileRegistry:
    report_subtypes: dict[str, dict[str, Any]]
    decision_intents: dict[str, dict[str, Any]]
    audience_levels: dict[str, dict[str, Any]]
    project_phases: dict[str, dict[str, Any]]


@dataclass(frozen=True, slots=True)
class ReportingContext:
    report_subtype: str
    report_subtype_label: str
    decision_intent: str
    decision_intent_label: str
    audience_level: str
    audience_level_label: str
    project_phase: str
    project_phase_label: str
    expected_chapter_roles: tuple[str, ...]
    required_intent_roles: tuple[str, ...]
    emphasis: tuple[str, ...]
    state_guidance: tuple[str, ...]
    forbidden_state_upgrades: tuple[str, ...]


def _mapping(data: Any, key: str) -> dict[str, dict[str, Any]]:
    value = (data or {}).get(key)
    if not isinstance(value, dict) or not value:
        raise ValueError(f"{key} must be a non-empty mapping")
    return value


def load_reporting_profiles(path: str | Path) -> ReportingProfileRegistry:
    source = Path(path)
    if not source.is_file():
        raise ValueError(f"reporting profiles file not found: {source}")
    data = yaml.safe_load(source.read_text(encoding="utf-8")) or {}
    return ReportingProfileRegistry(
        report_subtypes=_mapping(data, "report_subtypes"),
        decision_intents=_mapping(data, "decision_intents"),
        audience_levels=_mapping(data, "audience_levels"),
        project_phases=_mapping(data, "project_phases"),
    )


def _resolve(mapping: dict[str, dict[str, Any]], value: str, field: str) -> dict[str, Any]:
    if value not in mapping:
        supported = ", ".join(sorted(mapping))
        raise ValueError(f"unknown {field}: {value}; supported values: {supported}")
    return mapping[value]


def _dedupe(items: list[str]) -> tuple[str, ...]:
    return tuple(dict.fromkeys(item for item in items if item))


def resolve_reporting_context(
    registry: ReportingProfileRegistry,
    *,
    report_subtype: str,
    decision_intent: str,
    audience_level: str,
    project_phase: str,
) -> ReportingContext:
    subtype = _resolve(registry.report_subtypes, report_subtype, "report_subtype")
    intent = _resolve(registry.decision_intents, decision_intent, "decision_intent")
    audience = _resolve(registry.audience_levels, audience_level, "audience_level")
    phase = _resolve(registry.project_phases, project_phase, "project_phase")
    emphasis = _dedupe(
        list(subtype.get("emphasis", []))
        + list(intent.get("emphasis", []))
        + list(audience.get("emphasis", []))
    )
    return ReportingContext(
        report_subtype=report_subtype,
        report_subtype_label=str(subtype.get("label", report_subtype)),
        decision_intent=decision_intent,
        decision_intent_label=str(intent.get("label", decision_intent)),
        audience_level=audience_level,
        audience_level_label=str(audience.get("label", audience_level)),
        project_phase=project_phase,
        project_phase_label=str(phase.get("label", project_phase)),
        expected_chapter_roles=_dedupe(list(subtype.get("chapter_roles", []))),
        required_intent_roles=_dedupe(list(intent.get("required_roles", []))),
        emphasis=emphasis,
        state_guidance=_dedupe(list(phase.get("state_guidance", []))),
        forbidden_state_upgrades=_dedupe(list(phase.get("forbidden_state_upgrades", []))),
    )


def resolve_project_reporting_context(meta: dict[str, Any], repo_root: str | Path) -> ReportingContext:
    missing = [field for field in REQUIRED_REPORTING_FIELDS if not meta.get(field)]
    if missing:
        raise ValueError(f"missing required project fields: {', '.join(missing)}")
    registry = load_reporting_profiles(Path(repo_root) / "config/reporting-modes.yaml")
    return resolve_reporting_context(
        registry,
        report_subtype=str(meta["report_subtype"]),
        decision_intent=str(meta["decision_intent"]),
        audience_level=str(meta["audience_level"]),
        project_phase=str(meta["project_phase"]),
    )
