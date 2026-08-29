"""Audit the Stage 02 Visual Medium Policy independently from topology."""

from __future__ import annotations

from typing import Mapping

from cyberppt.visual_medium_policy import validate_visual_medium_policy


def audit_visual_medium_policy(page_spec: Mapping[str, object]) -> list[dict[str, str]]:
    issues: list[dict[str, str]] = []
    raw = page_spec.get("visual_medium_policy")
    final_text = [item for item in page_spec.get("final_text") or [] if isinstance(item, Mapping)]
    current_region_graph = isinstance(page_spec.get("region_graph"), Mapping) or any(
        str(item.get("region_id") or "").startswith("RG") for item in final_text
    )
    if not isinstance(raw, Mapping):
        if current_region_graph:
            issues.append({
                "code": "VISUAL_MEDIUM_POLICY_MISSING",
                "message": "Current Stage2 Region Graph page requires visual_medium_policy.",
            })
        return issues
    try:
        policy = validate_visual_medium_policy(raw)
    except ValueError as exc:
        issues.append({"code": "VISUAL_MEDIUM_POLICY_INVALID", "message": str(exc)})
        return issues

    image_plan = page_spec.get("image_plan")
    image_plan = image_plan if isinstance(image_plan, Mapping) else {}
    scene_policy = str(image_plan.get("scene_policy") or "").strip()
    if scene_policy and policy.scene_policy != scene_policy:
        issues.append({
            "code": "VISUAL_MEDIUM_SCENE_POLICY_MISMATCH",
            "message": "visual_medium_policy.scene_policy must match image_plan.scene_policy.",
        })
    return issues


__all__ = ["audit_visual_medium_policy"]
