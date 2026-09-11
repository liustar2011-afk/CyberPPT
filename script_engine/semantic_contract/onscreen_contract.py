"""Deterministic enforcement of explicit PLAN onscreen contracts.

Only fields explicitly authored in PLAN are enforced here.  The validator does
not classify business prose, infer roles from generic wording, or reproduce the
legacy source-colocation lexical heuristic.
"""

from __future__ import annotations

import re
from typing import Any

from .foundation_index import FoundationIndex
from .models import SemanticDiagnostic


_EXPRESSION_MODES = frozenset({"phrase_led", "sentence_led", "mixed"})


def _text(value: object) -> str:
    return str(value or "").strip()


def _page_id(page: dict[str, Any]) -> str:
    return _text(page.get("id") or page.get("page_id"))


def _module_lines(module: dict[str, Any]) -> list[str]:
    """Return visible module payload for both Final Script 1.0 and 1.1."""

    lines: list[str] = []
    text = module.get("text")
    if isinstance(text, str) and text.strip():
        lines.append(text.strip())
    for item in module.get("items") or []:
        if isinstance(item, str) and item.strip():
            lines.append(item.strip())
        elif isinstance(item, dict):
            value = item.get("text")
            if isinstance(value, str) and value.strip():
                lines.append(value.strip())
    return lines


def _diagnostic(
    code: str,
    message: str,
    *,
    slide_id: str,
    module_id: str = "",
    target: str = "onscreen_contract",
    evidence_refs: tuple[str, ...] = (),
) -> SemanticDiagnostic:
    return SemanticDiagnostic(
        code=code,
        message=message,
        slide_id=slide_id,
        module_id=module_id,
        target=target,
        severity="blocking",
        evidence_refs=evidence_refs,
        relation="conforms_to_plan",
    )


def _definition_diagnostics(
    page: dict[str, Any],
    contract: dict[str, Any],
    index: FoundationIndex,
    *,
    slide_id: str,
) -> list[SemanticDiagnostic]:
    diagnostics: list[SemanticDiagnostic] = []
    modules = [
        module for module in contract.get("modules") or [] if isinstance(module, dict)
    ]

    if _text(contract.get("relation")) == "parallel" and len(modules) < 2:
        diagnostics.append(
            _diagnostic(
                "ONSCREEN_CONTRACT_INVALID",
                "onscreen_contract.relation='parallel' requires at least two modules",
                slide_id=slide_id,
            )
        )

    expression_mode = contract.get("expression_mode")
    if expression_mode is not None and (
        not isinstance(expression_mode, str)
        or expression_mode not in _EXPRESSION_MODES
    ):
        diagnostics.append(
            _diagnostic(
                "ONSCREEN_CONTRACT_INVALID",
                "onscreen_contract.expression_mode must be one of: phrase_led, sentence_led, mixed",
                slide_id=slide_id,
                target="onscreen_contract.expression_mode",
            )
        )

    headings: list[str] = []
    for module_index, module in enumerate(modules):
        heading = _text(module.get("heading"))
        module_id = f"plan.modules[{module_index}]"
        if not heading:
            diagnostics.append(
                _diagnostic(
                    "ONSCREEN_CONTRACT_INVALID",
                    "module heading is required",
                    slide_id=slide_id,
                    module_id=module_id,
                    target="heading",
                )
            )
        elif heading in headings:
            diagnostics.append(
                _diagnostic(
                    "ONSCREEN_CONTRACT_INVALID",
                    f"duplicate module heading {heading!r}",
                    slide_id=slide_id,
                    module_id=module_id,
                    target="heading",
                )
            )
        headings.append(heading)

        refs = tuple(
            dict.fromkeys(
                ref.strip()
                for ref in module.get("evidence_refs") or []
                if isinstance(ref, str) and ref.strip()
            )
        )
        if not refs:
            diagnostics.append(
                _diagnostic(
                    "ONSCREEN_CONTRACT_INVALID",
                    "module requires at least one evidence_ref",
                    slide_id=slide_id,
                    module_id=module_id,
                    target="evidence_refs",
                )
            )
        unknown = tuple(ref for ref in refs if not index.contains(ref))
        if unknown:
            diagnostics.append(
                _diagnostic(
                    "ONSCREEN_CONTRACT_EVIDENCE_UNKNOWN",
                    f"module cites unknown evidence_refs {list(unknown)}",
                    slide_id=slide_id,
                    module_id=module_id,
                    target="evidence_refs",
                    evidence_refs=unknown,
                )
            )

        signals = [
            signal
            for signal in module.get("required_signals") or []
            if isinstance(signal, str) and signal
        ]
        if not signals:
            diagnostics.append(
                _diagnostic(
                    "ONSCREEN_CONTRACT_INVALID",
                    "module requires at least one required_signals entry",
                    slide_id=slide_id,
                    module_id=module_id,
                    target="required_signals",
                    evidence_refs=refs,
                )
            )

    policy = contract.get("detail_policy") or {}
    if not isinstance(policy, dict):
        diagnostics.append(
            _diagnostic(
                "ONSCREEN_CONTRACT_INVALID",
                "onscreen_contract.detail_policy must be an object",
                slide_id=slide_id,
                target="onscreen_contract.detail_policy",
            )
        )
        return diagnostics

    markers = policy.get("role_markers") or {}
    if not isinstance(markers, dict):
        diagnostics.append(
            _diagnostic(
                "ONSCREEN_CONTRACT_INVALID",
                "onscreen_contract.detail_policy.role_markers must be an object",
                slide_id=slide_id,
                target="onscreen_contract.detail_policy.role_markers",
            )
        )
        markers = {}

    for role in policy.get("forbidden_roles") or []:
        if role not in markers:
            diagnostics.append(
                _diagnostic(
                    "ONSCREEN_CONTRACT_INVALID",
                    f"forbidden role {role!r} has no role_markers",
                    slide_id=slide_id,
                    target="onscreen_contract.detail_policy.forbidden_roles",
                )
            )
    for role in policy.get("allowed_roles") or []:
        if role not in markers:
            diagnostics.append(
                _diagnostic(
                    "ONSCREEN_CONTRACT_INVALID",
                    f"allowed role {role!r} has no role_markers",
                    slide_id=slide_id,
                    target="onscreen_contract.detail_policy.allowed_roles",
                )
            )

    for role, patterns in markers.items():
        target = f"onscreen_contract.detail_policy.role_markers.{role}"
        if not isinstance(role, str) or not isinstance(patterns, list) or not patterns:
            diagnostics.append(
                _diagnostic(
                    "ONSCREEN_CONTRACT_INVALID",
                    "role marker requires a non-empty pattern list",
                    slide_id=slide_id,
                    target=target,
                )
            )
            continue
        for pattern in patterns:
            if not isinstance(pattern, str) or not pattern:
                diagnostics.append(
                    _diagnostic(
                        "ONSCREEN_CONTRACT_INVALID",
                        "role marker patterns must be non-empty strings",
                        slide_id=slide_id,
                        target=target,
                    )
                )
                continue
            try:
                re.compile(pattern)
            except re.error as error:
                diagnostics.append(
                    _diagnostic(
                        "ONSCREEN_CONTRACT_INVALID",
                        f"invalid regex {pattern!r}: {error}",
                        slide_id=slide_id,
                        target=target,
                    )
                )

    for pattern in policy.get("forbidden_patterns") or []:
        target = "onscreen_contract.detail_policy.forbidden_patterns"
        if not isinstance(pattern, str) or not pattern:
            diagnostics.append(
                _diagnostic(
                    "ONSCREEN_CONTRACT_INVALID",
                    "forbidden patterns must be non-empty strings",
                    slide_id=slide_id,
                    target=target,
                )
            )
            continue
        try:
            re.compile(pattern)
        except re.error as error:
            diagnostics.append(
                _diagnostic(
                    "ONSCREEN_CONTRACT_INVALID",
                    f"invalid regex {pattern!r}: {error}",
                    slide_id=slide_id,
                    target=target,
                )
            )

    return diagnostics


def _consumption_diagnostics(
    page: dict[str, Any],
    slide: dict[str, Any],
    contract: dict[str, Any],
    *,
    slide_id: str,
) -> list[SemanticDiagnostic]:
    diagnostics: list[SemanticDiagnostic] = []
    expected_modules = [
        module for module in contract.get("modules") or [] if isinstance(module, dict)
    ]
    actual_modules = [
        module for module in slide.get("onscreen") or [] if isinstance(module, dict)
    ]
    expected_headings = [_text(module.get("heading")) for module in expected_modules]
    actual_headings = [_text(module.get("heading")) for module in actual_modules]

    if actual_headings != expected_headings:
        diagnostics.append(
            _diagnostic(
                "ONSCREEN_CONTRACT_MODULES_MISMATCH",
                f"approved module headings are {expected_headings}, got {actual_headings}",
                slide_id=slide_id,
                target="onscreen",
            )
        )

    modules_by_heading = {
        _text(module.get("heading")): module
        for module in actual_modules
        if _text(module.get("heading"))
    }
    contract_headings = set(expected_headings)
    policy = contract.get("detail_policy")
    policy = policy if isinstance(policy, dict) else {}
    role_markers = policy.get("role_markers")
    role_markers = role_markers if isinstance(role_markers, dict) else {}
    allowed_roles = {str(role) for role in policy.get("allowed_roles") or []}
    forbidden_roles = {str(role) for role in policy.get("forbidden_roles") or []}
    forbidden_patterns = [
        pattern
        for pattern in policy.get("forbidden_patterns") or []
        if isinstance(pattern, str) and pattern
    ]

    for module_index, expected in enumerate(expected_modules):
        heading = _text(expected.get("heading"))
        module = modules_by_heading.get(heading)
        if module is None:
            continue
        module_id = _text(module.get("id")) or f"onscreen[{module_index}]"
        lines = _module_lines(module)
        body = " ".join(lines)
        refs = tuple(
            ref.strip()
            for ref in expected.get("evidence_refs") or []
            if isinstance(ref, str) and ref.strip()
        )

        for signal in expected.get("required_signals") or []:
            if isinstance(signal, str) and signal and signal not in body:
                diagnostics.append(
                    _diagnostic(
                        "ONSCREEN_REQUIRED_SIGNAL_MISSING",
                        f"required signal {signal!r} is missing",
                        slide_id=slide_id,
                        module_id=module_id,
                        target="visible_payload",
                        evidence_refs=refs,
                    )
                )
        for signal in expected.get("forbidden_signals") or []:
            if isinstance(signal, str) and signal and signal in body:
                diagnostics.append(
                    _diagnostic(
                        "ONSCREEN_FORBIDDEN_SIGNAL_PRESENT",
                        f"forbidden cross-scope signal {signal!r} is present",
                        slide_id=slide_id,
                        module_id=module_id,
                        target="visible_payload",
                        evidence_refs=refs,
                    )
                )

        if contract.get("scope_mode") == "exclusive":
            for other_heading in contract_headings - {heading}:
                if other_heading and other_heading in body:
                    diagnostics.append(
                        _diagnostic(
                            "ONSCREEN_EXCLUSIVE_SCOPE_VIOLATION",
                            f"exclusive scope contains peer module heading {other_heading!r}",
                            slide_id=slide_id,
                            module_id=module_id,
                            target="visible_payload",
                            evidence_refs=refs,
                        )
                    )

        for line_index, line in enumerate(lines):
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
                        # Definition diagnostics own invalid regexes.
                        continue
            disallowed = matched_roles.intersection(forbidden_roles)
            if allowed_roles:
                disallowed.update(matched_roles - allowed_roles)
            if disallowed:
                diagnostics.append(
                    _diagnostic(
                        "ONSCREEN_DETAIL_ROLE_DISALLOWED",
                        f"detail line {line!r} uses disallowed role(s) {sorted(disallowed)}",
                        slide_id=slide_id,
                        module_id=module_id,
                        target=f"visible_payload[{line_index}]",
                        evidence_refs=refs,
                    )
                )

            for pattern in forbidden_patterns:
                try:
                    matched = re.search(pattern, line)
                except re.error:
                    matched = None
                if matched:
                    diagnostics.append(
                        _diagnostic(
                            "ONSCREEN_DETAIL_PATTERN_FORBIDDEN",
                            f"detail line {line!r} matches forbidden pattern {pattern!r}",
                            slide_id=slide_id,
                            module_id=module_id,
                            target=f"visible_payload[{line_index}]",
                            evidence_refs=refs,
                        )
                    )

    return diagnostics


def collect_onscreen_contract_diagnostics(
    final_script: dict[str, Any],
    plan: dict[str, Any] | None,
    foundation: dict[str, Any] | None,
) -> list[SemanticDiagnostic]:
    """Validate explicit PLAN onscreen contracts against Final Script output."""

    if not isinstance(plan, dict):
        return []
    pages = {
        _page_id(page): page
        for page in plan.get("pages") or []
        if isinstance(page, dict) and _page_id(page)
    }
    index = FoundationIndex(foundation)
    diagnostics: list[SemanticDiagnostic] = []

    for slide in final_script.get("slides") or []:
        if not isinstance(slide, dict):
            continue
        slide_id = _text(slide.get("id"))
        page = pages.get(slide_id)
        if not isinstance(page, dict):
            continue
        contract = page.get("onscreen_contract")
        if not isinstance(contract, dict):
            continue
        diagnostics.extend(
            _definition_diagnostics(page, contract, index, slide_id=slide_id)
        )
        diagnostics.extend(
            _consumption_diagnostics(
                page,
                slide,
                contract,
                slide_id=slide_id,
            )
        )

    return diagnostics


__all__ = ["collect_onscreen_contract_diagnostics"]
