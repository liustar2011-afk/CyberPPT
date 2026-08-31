"""Focused Final Script onscreen composition, density, and contract audits."""
from __future__ import annotations

from .common import *
from .final_authoring import (
    _evidence_first_item_hierarchy_issues,
    _onscreen_module_lines,
)


def _audit_authored_onscreen_composition(
    page: dict[str, Any], slide: dict[str, Any]
) -> list[str]:
    """Check that module lead text follows the approved page composition policy."""
    composition = page.get("onscreen_composition")
    if not isinstance(composition, dict):
        return []

    issues = _audit_onscreen_composition_definition(page)
    mode = composition.get("mode")
    if mode not in _ONSCREEN_COMPOSITION_MODES:
        return issues

    slide_id = str(slide.get("id") or page.get("id") or "?")
    modules = [module for module in slide.get("onscreen") or [] if isinstance(module, dict)]
    lead_modules = [
        module for module in modules
        if isinstance(module.get("text"), str) and module["text"].strip()
    ]
    if mode == "evidence_first":
        for module in lead_modules:
            heading = str(module.get("heading") or "?").strip()
            issues.append(
                f"{slide_id}: onscreen_composition='evidence_first' forbids module lead text in "
                f"'{heading}'; move the judgment to core_message and retain source facts as evidence items"
            )
        for module in modules:
            issues.extend(_evidence_first_item_hierarchy_issues(slide_id, module))
    else:
        lead_budget = composition.get("lead_budget")
        if isinstance(lead_budget, int) and not isinstance(lead_budget, bool) and len(lead_modules) > lead_budget:
            issues.append(
                f"{slide_id}: onscreen_composition='selective_lead' permits at most {lead_budget} "
                f"module lead(s), got {len(lead_modules)}"
            )
    return issues


def _semantic_payload_units(module: dict[str, Any]) -> int:
    """Estimate distinct reader-facing information units in one module."""
    units = 0
    for line in _onscreen_module_lines(module):
        fragments = [
            fragment.strip()
            for fragment in re.split(r"[、，,；;]", line)
            if fragment.strip()
        ]
        units += max(1, len(fragments))
    return units


def _audit_self_reading_density(
    delivery_mode: str | dict[str, Any], page: dict[str, Any], slide: dict[str, Any]
) -> list[str]:
    """Require content pages in self-read decks to explain themselves on screen."""
    mode = str(delivery_mode.get("delivery_mode") if isinstance(delivery_mode, dict) else delivery_mode)
    page_type = str(slide.get("page_type") or page.get("page_role") or "")
    if mode != "self_read" or page_type != "content":
        return []
    load = str(slide.get("content_load") or page.get("content_load") or "standard")
    if load == "light":
        return []
    modules = [module for module in slide.get("onscreen") or [] if isinstance(module, dict)]
    slide_id = str(slide.get("id") or page.get("id") or "?")
    if not modules:
        return [f"ONSCREEN_SELF_READ_PAYLOAD_MISSING: {slide_id} has no reader-facing modules"]
    issues: list[str] = []
    empty_headings = [
        str(module.get("heading") or "?").strip()
        for module in modules
        if not _onscreen_module_lines(module)
    ]
    if empty_headings:
        issues.append(
            f"ONSCREEN_SELF_READ_MODULE_THIN: {slide_id} modules {empty_headings} have headings "
            "without explanatory payload"
        )
    units = sum(_semantic_payload_units(module) for module in modules)
    module_count = len(modules)
    minimum = 2 * module_count if load == "dense" else (3 * module_count + 1) // 2
    if units < minimum:
        issues.append(
            f"ONSCREEN_SELF_READ_DENSITY_LOW: {slide_id} {load} content provides {units} "
            f"semantic payload units across {module_count} modules; at least {minimum} are "
            "required for independent reading at the approved load. Add distinct source-backed "
            "facts, roles, conditions, boundaries or results; do not repeat the page judgment"
        )
    return issues


def _audit_authored_onscreen_contract(
    page: dict[str, Any], slide: dict[str, Any], items: dict[str, dict[str, Any]]
) -> list[str]:
    """Check that AUTHOR consumed the declared module-level semantic contract."""
    contract = page.get("onscreen_contract")
    if not isinstance(contract, dict):
        return []

    issues = _onscreen_contract_definition_issues(page, contract, items)
    expected_modules = [module for module in contract.get("modules") or [] if isinstance(module, dict)]
    actual_modules = [module for module in slide.get("onscreen") or [] if isinstance(module, dict)]
    expected_headings = [str(module.get("heading") or "").strip() for module in expected_modules]
    actual_headings = [str(module.get("heading") or "").strip() for module in actual_modules]
    slide_id = str(slide.get("id") or page.get("id") or "?")

    if actual_headings != expected_headings:
        issues.append(
            f"{slide_id}: onscreen module headings do not match the approved contract; "
            f"expected {expected_headings}, got {actual_headings}"
        )

    modules_by_heading = {
        str(module.get("heading") or "").strip(): module
        for module in actual_modules
        if str(module.get("heading") or "").strip()
    }
    contract_headings = set(expected_headings)
    policy = contract.get("detail_policy") or {}
    if not isinstance(policy, dict):
        policy = {}
    role_markers = policy.get("role_markers") or {}
    if not isinstance(role_markers, dict):
        role_markers = {}
    allowed_roles = {str(role) for role in policy.get("allowed_roles") or []}
    forbidden_roles = {str(role) for role in policy.get("forbidden_roles") or []}
    forbidden_patterns = [pattern for pattern in policy.get("forbidden_patterns") or [] if isinstance(pattern, str)]

    for expected in expected_modules:
        heading = str(expected.get("heading") or "").strip()
        module = modules_by_heading.get(heading)
        if module is None:
            continue
        lines = _onscreen_module_lines(module)
        body = " ".join(lines)
        for signal in expected.get("required_signals") or []:
            if isinstance(signal, str) and signal and signal not in body:
                issues.append(
                    f"ONSCREEN_REQUIRED_SIGNAL_MISSING: {slide_id} module '{heading}': "
                    f"required signal '{signal}' is missing"
                )
        for signal in expected.get("forbidden_signals") or []:
            if isinstance(signal, str) and signal and signal in body:
                issues.append(f"{slide_id} module '{heading}': forbidden cross-scope signal '{signal}' is present")

        if contract.get("scope_mode") == "exclusive":
            for other_heading in contract_headings - {heading}:
                if other_heading and other_heading in body:
                    issues.append(
                        f"{slide_id} module '{heading}': exclusive scope contains peer module heading '{other_heading}'"
                    )

        for line in lines:
            matched_roles: set[str] = set()
            for role, patterns in role_markers.items():
                if not isinstance(role, str) or not isinstance(patterns, list):
                    continue
                for pattern in patterns:
                    if not isinstance(pattern, str) or not pattern:
                        continue
                    try:
                        if re.search(pattern, line):
                            matched_roles.add(role)
                            break
                    except re.error:
                        continue
            disallowed = matched_roles.intersection(forbidden_roles)
            if allowed_roles:
                disallowed.update(matched_roles - allowed_roles)
            if disallowed:
                issues.append(
                    f"{slide_id} module '{heading}': detail line '{line}' uses disallowed role(s) "
                    f"{sorted(disallowed)}"
                )
            for pattern in forbidden_patterns:
                try:
                    matched = re.search(pattern, line)
                except re.error:
                    matched = None
                if matched:
                    issues.append(
                        f"{slide_id} module '{heading}': detail line '{line}' matches forbidden pattern '{pattern}'"
                    )
    return issues


__all__ = [
    "_audit_authored_onscreen_composition",
    "_semantic_payload_units",
    "_audit_self_reading_density",
    "_audit_authored_onscreen_contract",
]
