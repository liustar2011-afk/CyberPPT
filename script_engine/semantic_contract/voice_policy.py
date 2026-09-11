"""Deterministic delivery-voice policy for internal-report Final Scripts."""

from __future__ import annotations

from typing import Any

from script_engine.internal_report_voice import (
    consultant_voice_hits,
    is_internal_report_scope,
    slide_text_fields,
)

from .models import SemanticDiagnostic


def collect_voice_policy_diagnostics(
    final_script: dict[str, Any],
    plan: dict[str, Any] | None,
) -> list[SemanticDiagnostic]:
    """Reject explicit external-adviser voice under the internal-report policy."""

    plan_payload = plan if isinstance(plan, dict) else {}
    if not is_internal_report_scope(plan_payload):
        return []

    diagnostics: list[SemanticDiagnostic] = []
    for slide_index, slide in enumerate(final_script.get("slides") or []):
        if not isinstance(slide, dict):
            continue
        slide_id = str(slide.get("id") or f"#{slide_index}")
        for field, text in slide_text_fields(slide):
            for description, matched in consultant_voice_hits(text):
                diagnostics.append(
                    SemanticDiagnostic(
                        code="INTERNAL_EXPERT_VOICE_LEAK",
                        message=(
                            "internal-expert voice required; "
                            f"{description} — matched {matched!r}"
                        ),
                        slide_id=slide_id,
                        target=field,
                        severity="blocking",
                        relation="delivery_policy",
                    )
                )
    return diagnostics


__all__ = ["collect_voice_policy_diagnostics"]
