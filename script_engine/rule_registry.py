"""Rule-registry policy checks for deterministic Stage 01 gates."""

from __future__ import annotations

from typing import Any

from .schema_contracts import CONTRACTS, load_json


RULE_REGISTRY_PATH = CONTRACTS / "rule-registry.json"
_REQUIRED_RULE_FIELDS = frozenset(
    {
        "id",
        "pattern",
        "kind",
        "severity",
        "scope",
        "confidence",
        "owner",
        "severity_rationale",
    }
)
_ALLOWED_CONFIDENCE = frozenset({"high", "medium", "low"})


def load_rule_registry() -> dict[str, Any]:
    return load_json(RULE_REGISTRY_PATH)


def validate_default_rule_registry(
    banned_phrasing: dict[str, Any] | None = None,
    registry: dict[str, Any] | None = None,
) -> list[str]:
    """Validate rule metadata and default-profile blocking policy."""

    registry_payload = registry if isinstance(registry, dict) else load_rule_registry()
    banned_payload = (
        banned_phrasing
        if isinstance(banned_phrasing, dict)
        else load_json(CONTRACTS / "banned-phrasing.json")
    )
    blocking_kinds = set(registry_payload.get("blocking_kinds") or [])
    warning_kinds = set(registry_payload.get("warning_kinds") or [])
    forbidden_default = set(registry_payload.get("forbidden_default_kinds") or [])
    allowed_kinds = blocking_kinds | warning_kinds | forbidden_default

    issues: list[str] = []
    seen_ids: set[str] = set()
    for index, rule in enumerate(banned_payload.get("rules") or []):
        if not isinstance(rule, dict):
            issues.append(f"rules[{index}]: rule must be an object")
            continue
        missing = sorted(_REQUIRED_RULE_FIELDS - set(rule))
        if missing:
            issues.append(f"rules[{index}]: missing metadata {missing}")
            continue
        rule_id = str(rule.get("id") or "").strip()
        if not rule_id:
            issues.append(f"rules[{index}]: id must be non-empty")
        elif rule_id in seen_ids:
            issues.append(f"rules[{index}]: duplicate id {rule_id!r}")
        seen_ids.add(rule_id)

        kind = str(rule.get("kind") or "")
        severity = str(rule.get("severity") or "")
        confidence = str(rule.get("confidence") or "")
        if kind not in allowed_kinds:
            issues.append(f"{rule_id}: unknown rule kind {kind!r}")
        if kind in forbidden_default:
            issues.append(f"{rule_id}: project-specific rules are forbidden in the default profile")
        if severity not in {"blocking", "warning"}:
            issues.append(f"{rule_id}: unsupported severity {severity!r}")
        elif severity == "blocking" and kind not in blocking_kinds:
            issues.append(
                f"{rule_id}: blocking severity requires a structural, safety, or explicit delivery-policy kind"
            )
        elif severity == "warning" and kind not in warning_kinds:
            issues.append(
                f"{rule_id}: warning severity requires a declared heuristic kind"
            )
        if confidence not in _ALLOWED_CONFIDENCE:
            issues.append(f"{rule_id}: unsupported confidence {confidence!r}")
        if not str(rule.get("severity_rationale") or "").strip():
            issues.append(f"{rule_id}: severity_rationale must be non-empty")

    for source in registry_payload.get("sources") or []:
        if not isinstance(source, dict):
            continue
        if (
            source.get("profile") == registry_payload.get("default_profile")
            and source.get("kind") in forbidden_default
        ):
            issues.append(
                f"registry source {source.get('id')!r}: project-specific source cannot be enabled by default"
            )
    return issues


__all__ = [
    "RULE_REGISTRY_PATH",
    "load_rule_registry",
    "validate_default_rule_registry",
]
