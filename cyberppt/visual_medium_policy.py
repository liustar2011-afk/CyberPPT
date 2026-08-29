"""Independent visual-medium policy for Stage 02 generation planning."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping


VISUAL_MEDIA = frozenset({
    "business_scene",
    "object_illustration",
    "relationship_diagram",
    "data_visualization",
    "mixed",
})
SCENE_POLICIES = frozenset({"required", "allowed", "forbidden", "auto"})


@dataclass(frozen=True)
class VisualMediumPolicy:
    preferred: str
    allowed: tuple[str, ...]
    scene_policy: str
    rationale: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "preferred": self.preferred,
            "allowed": list(self.allowed),
            "scene_policy": self.scene_policy,
            "rationale": self.rationale,
        }


def validate_visual_medium_policy(value: Mapping[str, object]) -> VisualMediumPolicy:
    if not isinstance(value, Mapping):
        raise ValueError("visual_medium_policy must be an object")
    preferred = str(value.get("preferred") or "").strip()
    if preferred not in VISUAL_MEDIA:
        raise ValueError(f"unsupported preferred visual medium: {preferred!r}")
    raw_allowed = value.get("allowed")
    if not isinstance(raw_allowed, list) or not raw_allowed:
        raise ValueError("visual_medium_policy.allowed must be a non-empty array")
    allowed = tuple(str(item or "").strip() for item in raw_allowed)
    if any(item not in VISUAL_MEDIA for item in allowed):
        raise ValueError(f"visual_medium_policy.allowed contains unsupported medium: {allowed!r}")
    if len(allowed) != len(set(allowed)):
        raise ValueError("visual_medium_policy.allowed must be unique")
    if preferred not in allowed:
        raise ValueError("preferred visual medium must be included in allowed")
    scene_policy = str(value.get("scene_policy") or "").strip()
    if scene_policy not in SCENE_POLICIES:
        raise ValueError(f"unsupported visual medium scene_policy: {scene_policy!r}")
    rationale = str(value.get("rationale") or "").strip()
    if not rationale:
        raise ValueError("visual_medium_policy.rationale is required")
    if scene_policy == "forbidden" and "business_scene" in allowed:
        raise ValueError("scene_policy=forbidden cannot allow business_scene")
    if scene_policy == "required" and "business_scene" not in allowed and "mixed" not in allowed:
        raise ValueError("scene_policy=required must allow business_scene or mixed")
    return VisualMediumPolicy(
        preferred=preferred,
        allowed=allowed,
        scene_policy=scene_policy,
        rationale=rationale,
    )


def default_visual_medium_policy(scene_policy: str) -> VisualMediumPolicy:
    """Return a topology-neutral fallback policy from the independent scene policy."""

    if scene_policy not in SCENE_POLICIES:
        raise ValueError(f"unsupported scene policy for visual medium fallback: {scene_policy!r}")
    if scene_policy == "required":
        payload = {
            "preferred": "business_scene",
            "allowed": ["business_scene", "mixed"],
            "scene_policy": scene_policy,
            "rationale": "场景已由页面执行设计明确要求；具体场景内容仍由业务语义和Style lock约束。",
        }
    elif scene_policy == "forbidden":
        payload = {
            "preferred": "relationship_diagram",
            "allowed": ["object_illustration", "relationship_diagram", "data_visualization", "mixed"],
            "scene_policy": scene_policy,
            "rationale": "页面禁止完整业务场景，但仍允许对象插图、关系表达、数据表达或非场景混合视觉。",
        }
    else:
        payload = {
            "preferred": "mixed",
            "allowed": [
                "business_scene",
                "object_illustration",
                "relationship_diagram",
                "data_visualization",
                "mixed",
            ],
            "scene_policy": scene_policy,
            "rationale": "媒介由页面使命、可画业务对象、动作、信息密度和Style lock共同决定，不从relationship topology推导。",
        }
    return validate_visual_medium_policy(payload)


def resolve_visual_medium_policy(
    value: object,
    *,
    scene_policy: str,
) -> VisualMediumPolicy:
    if isinstance(value, Mapping):
        policy = validate_visual_medium_policy(value)
        if policy.scene_policy != scene_policy:
            raise ValueError("visual_medium_policy.scene_policy must match image scene_policy")
        return policy
    return default_visual_medium_policy(scene_policy)


__all__ = [
    "SCENE_POLICIES",
    "VISUAL_MEDIA",
    "VisualMediumPolicy",
    "default_visual_medium_policy",
    "resolve_visual_medium_policy",
    "validate_visual_medium_policy",
]
