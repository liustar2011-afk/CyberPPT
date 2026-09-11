"""Deterministic enforcement of explicit PLAN onscreen composition policy."""

from __future__ import annotations

from typing import Any

from .models import SemanticDiagnostic


_COMPOSITION_MODES = frozenset({"evidence_first", "selective_lead"})


def _text(value: object) -> str:
    return str(value or "").strip()


def _page_id(page: dict[str, Any]) -> str:
    return _text(page.get("id") or page.get("page_id"))


def _diagnostic(
    code: str,
    message: str,
    *,
    slide_id: str,
    module_id: str = "",
    target: str = "onscreen_composition",
) -> SemanticDiagnostic:
    return SemanticDiagnostic(
        code=code,
        message=message,
        slide_id=slide_id,
        module_id=module_id,
        target=target,
        severity="blocking",
        relation="conforms_to_plan",
    )


def collect_onscreen_composition_diagnostics(
    final_script: dict[str, Any],
    plan: dict[str, Any] | None,
) -> list[SemanticDiagnostic]:
    """Check explicit module-lead policy without textual hierarchy heuristics."""

    if not isinstance(plan, dict):
        return []
    pages = {
        _page_id(page): page
        for page in plan.get("pages") or []
        if isinstance(page, dict) and _page_id(page)
    }
    diagnostics: list[SemanticDiagnostic] = []

    for slide in final_script.get("slides") or []:
        if not isinstance(slide, dict):
            continue
        slide_id = _text(slide.get("id"))
        page = pages.get(slide_id)
        if not isinstance(page, dict):
            continue
        composition = page.get("onscreen_composition")
        if composition is None:
            continue
        if not isinstance(composition, dict):
            diagnostics.append(
                _diagnostic(
                    "ONSCREEN_COMPOSITION_INVALID",
                    "onscreen_composition must be an object",
                    slide_id=slide_id,
                )
            )
            continue

        mode = composition.get("mode")
        if mode not in _COMPOSITION_MODES:
            diagnostics.append(
                _diagnostic(
                    "ONSCREEN_COMPOSITION_INVALID",
                    "onscreen_composition.mode must be 'evidence_first' or 'selective_lead'",
                    slide_id=slide_id,
                    target="onscreen_composition.mode",
                )
            )
            continue

        lead_budget = composition.get("lead_budget")
        if mode == "evidence_first":
            if lead_budget not in (None, 0):
                diagnostics.append(
                    _diagnostic(
                        "ONSCREEN_COMPOSITION_INVALID",
                        "evidence_first requires lead_budget to be omitted or 0",
                        slide_id=slide_id,
                        target="onscreen_composition.lead_budget",
                    )
                )
        elif (
            not isinstance(lead_budget, int)
            or isinstance(lead_budget, bool)
            or lead_budget < 1
        ):
            diagnostics.append(
                _diagnostic(
                    "ONSCREEN_COMPOSITION_INVALID",
                    "selective_lead requires a positive integer lead_budget",
                    slide_id=slide_id,
                    target="onscreen_composition.lead_budget",
                )
            )
            continue

        modules = [
            module for module in slide.get("onscreen") or [] if isinstance(module, dict)
        ]
        lead_modules = [
            (module_index, module)
            for module_index, module in enumerate(modules)
            if isinstance(module.get("text"), str) and module["text"].strip()
        ]

        if mode == "evidence_first":
            for module_index, module in lead_modules:
                diagnostics.append(
                    _diagnostic(
                        "ONSCREEN_MODULE_LEAD_FORBIDDEN",
                        "evidence_first forbids module lead text",
                        slide_id=slide_id,
                        module_id=_text(module.get("id")) or f"onscreen[{module_index}]",
                        target="text",
                    )
                )
        elif len(lead_modules) > lead_budget:
            diagnostics.append(
                _diagnostic(
                    "ONSCREEN_LEAD_BUDGET_EXCEEDED",
                    f"selective_lead permits at most {lead_budget} module lead(s), got {len(lead_modules)}",
                    slide_id=slide_id,
                    target="onscreen",
                )
            )

    return diagnostics


__all__ = ["collect_onscreen_composition_diagnostics"]
