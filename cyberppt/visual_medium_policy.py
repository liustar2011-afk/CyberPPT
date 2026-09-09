"""Semantic Visual Medium Resolver v2 for Stage 02 generation planning.

The resolver scores visual media from page semantics, not from render topology.
Scene policy is an eligibility boundary; it is not a complete medium decision.
"""
from __future__ import annotations

from dataclasses import dataclass
import re
from typing import Any, Mapping, Sequence


VISUAL_MEDIA = frozenset({
    "business_scene",
    "object_illustration",
    "relationship_diagram",
    "data_visualization",
    "mixed",
})
SCENE_POLICIES = frozenset({"required", "allowed", "forbidden", "auto"})
VISUAL_MEDIUM_POLICY_VERSION = "visual-medium-policy-v2"
_MEDIA_TIE_ORDER = (
    "relationship_diagram",
    "object_illustration",
    "business_scene",
    "data_visualization",
    "mixed",
)

_PROCESS_RE = re.compile(r"运行|运营|作业|现场|调度|施工|检修|采购|操作|流程|协作动作|operation|workflow|process|dispatch|field", re.I)
_OBJECT_RE = re.compile(r"设备|装置|产品|平台|连接器|终端|组件|模型|系统对象|object|device|connector|equipment|product", re.I)
_RELATION_RE = re.compile(r"关系|协同|流通|机制|架构|治理|主体|角色|边界|接口|依赖|支撑|汇聚|网络|relationship|governance|architecture|dependency|interface|network", re.I)
_DATA_RE = re.compile(r"指标|趋势|占比|对比|统计|监测|预测|变化|曲线|分布|排名|metric|trend|share|forecast|comparison|distribution|statistics|chart", re.I)


@dataclass(frozen=True)
class VisualMediumPolicy:
    preferred: str
    allowed: tuple[str, ...]
    scene_policy: str
    rationale: str
    secondary: str = ""
    forbidden: tuple[str, ...] = ()
    confidence: float = 0.5
    scores: tuple[tuple[str, float], ...] = ()
    version: str = VISUAL_MEDIUM_POLICY_VERSION

    def to_dict(self) -> dict[str, Any]:
        return {
            "version": self.version,
            "preferred": self.preferred,
            "secondary": self.secondary,
            "allowed": list(self.allowed),
            "forbidden": list(self.forbidden),
            "scene_policy": self.scene_policy,
            "confidence": self.confidence,
            "scores": {medium: score for medium, score in self.scores},
            "rationale": self.rationale,
        }


def _normalize_media(value: object, *, field: str, allow_empty: bool = False) -> tuple[str, ...]:
    if value is None and allow_empty:
        return ()
    if not isinstance(value, (list, tuple)) or (not value and not allow_empty):
        qualifier = "" if allow_empty else " non-empty"
        raise ValueError(f"visual_medium_policy.{field} must be a{qualifier} array")
    media = tuple(str(item or "").strip() for item in value)
    if any(item not in VISUAL_MEDIA for item in media):
        raise ValueError(f"visual_medium_policy.{field} contains unsupported medium: {media!r}")
    if len(media) != len(set(media)):
        raise ValueError(f"visual_medium_policy.{field} must be unique")
    return media


def _score_pairs(value: object, allowed: tuple[str, ...], preferred: str) -> tuple[tuple[str, float], ...]:
    if isinstance(value, Mapping):
        pairs: list[tuple[str, float]] = []
        for medium in allowed:
            raw = value.get(medium)
            try:
                score = float(raw) if raw is not None else (1.0 if medium == preferred else 0.5)
            except (TypeError, ValueError) as exc:
                raise ValueError(f"visual_medium_policy.scores[{medium!r}] must be numeric") from exc
            if not 0.0 <= score <= 1.0:
                raise ValueError("visual_medium_policy scores must be between 0 and 1")
            pairs.append((medium, round(score, 3)))
        return tuple(sorted(pairs, key=lambda item: (-item[1], _MEDIA_TIE_ORDER.index(item[0]))))
    return tuple(
        (medium, 1.0 if medium == preferred else round(max(0.2, 0.6 - index * 0.05), 3))
        for index, medium in enumerate(allowed)
    )


def validate_visual_medium_policy(value: Mapping[str, object]) -> VisualMediumPolicy:
    if not isinstance(value, Mapping):
        raise ValueError("visual_medium_policy must be an object")
    preferred = str(value.get("preferred") or "").strip()
    if preferred not in VISUAL_MEDIA:
        raise ValueError(f"unsupported preferred visual medium: {preferred!r}")
    allowed = _normalize_media(value.get("allowed"), field="allowed")
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

    raw_forbidden = value.get("forbidden")
    forbidden = (
        _normalize_media(raw_forbidden, field="forbidden", allow_empty=True)
        if raw_forbidden is not None
        else tuple(medium for medium in _MEDIA_TIE_ORDER if medium not in allowed)
    )
    overlap = set(allowed) & set(forbidden)
    if overlap:
        raise ValueError(f"visual medium cannot be both allowed and forbidden: {sorted(overlap)}")
    secondary = str(value.get("secondary") or "").strip()
    if secondary:
        if secondary not in allowed or secondary == preferred:
            raise ValueError("visual_medium_policy.secondary must be a distinct allowed medium")
    else:
        secondary = next((medium for medium in allowed if medium != preferred), "")
    try:
        confidence = float(value.get("confidence", 0.75))
    except (TypeError, ValueError) as exc:
        raise ValueError("visual_medium_policy.confidence must be numeric") from exc
    if not 0.0 <= confidence <= 1.0:
        raise ValueError("visual_medium_policy.confidence must be between 0 and 1")
    scores = _score_pairs(value.get("scores"), allowed, preferred)
    return VisualMediumPolicy(
        preferred=preferred,
        secondary=secondary,
        allowed=allowed,
        forbidden=forbidden,
        scene_policy=scene_policy,
        confidence=round(confidence, 3),
        scores=scores,
        rationale=rationale,
        version=str(value.get("version") or VISUAL_MEDIUM_POLICY_VERSION),
    )


def _eligible_media(scene_policy: str) -> tuple[str, ...]:
    if scene_policy == "required":
        return ("business_scene", "mixed")
    if scene_policy == "forbidden":
        return ("object_illustration", "relationship_diagram", "data_visualization", "mixed")
    return _MEDIA_TIE_ORDER


def _relationship_text(value: object) -> str:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes)):
        return ""
    parts: list[str] = []
    for item in value:
        if not isinstance(item, Mapping):
            continue
        parts.extend((
            str(item.get("subject") or ""),
            str(item.get("relation") or ""),
            " ".join(str(obj) for obj in item.get("objects") or []),
            str(item.get("condition") or ""),
        ))
    return " ".join(part for part in parts if part)


def _add(scores: dict[str, float], reasons: dict[str, list[str]], medium: str, amount: float, reason: str) -> None:
    if medium not in scores:
        return
    scores[medium] += amount
    reasons[medium].append(reason)


def _semantic_policy(
    *,
    scene_policy: str,
    page_mission: str,
    business_relationships: object,
    text_count: int,
    text_characters: int,
    business_object: str,
    actor_type: str,
    data_available: bool,
) -> VisualMediumPolicy:
    if scene_policy not in SCENE_POLICIES:
        raise ValueError(f"unsupported scene policy for visual medium resolver: {scene_policy!r}")
    allowed = _eligible_media(scene_policy)
    scores = {medium: (0.18 if medium == "mixed" else 0.35) for medium in allowed}
    reasons = {medium: [] for medium in allowed}
    mission = str(page_mission or "")
    relationships = _relationship_text(business_relationships)
    object_text = str(business_object or "")
    actor = str(actor_type or "")
    evidence_signals = 0
    signal_families: set[str] = set()

    if scene_policy == "required":
        _add(scores, reasons, "business_scene", 0.48, "scene policy explicitly requires a business scene")
        _add(scores, reasons, "mixed", 0.10, "mixed remains eligible only as a scene-led hybrid")
        evidence_signals += 1
        signal_families.add("scene")
    elif scene_policy == "forbidden":
        evidence_signals += 1

    if _PROCESS_RE.search(mission + " " + relationships):
        _add(scores, reasons, "business_scene", 0.25, "page semantics describe an operational action or real business process")
        _add(scores, reasons, "relationship_diagram", 0.07, "the process also contains relationship structure")
        evidence_signals += 1
        signal_families.add("process")
    if _OBJECT_RE.search(mission + " " + object_text):
        _add(scores, reasons, "object_illustration", 0.28, "a concrete drawable business object is explicitly named")
        evidence_signals += 1
        signal_families.add("object")
    elif object_text and object_text not in {"业务关系", "business relationship", "业务关系场"}:
        _add(scores, reasons, "object_illustration", 0.12, "the page provides a named business object")
        evidence_signals += 1
        signal_families.add("object")
    if _RELATION_RE.search(mission + " " + relationships) or relationships:
        _add(scores, reasons, "relationship_diagram", 0.26, "the page mission or verified relations require explicit relationship encoding")
        evidence_signals += 1
        signal_families.add("relationship")
    if _DATA_RE.search(mission + " " + relationships) or data_available:
        _add(scores, reasons, "data_visualization", 0.30 if data_available else 0.24, "the page contains a metric, comparison, trend, forecast or other data-reading task")
        evidence_signals += 1
        signal_families.add("data")
    if re.search(r"企业|机构|部门|人员|客户|供应商|organization|person|customer|supplier", actor, re.I):
        _add(scores, reasons, "business_scene", 0.11, "the declared actor can participate in a concrete business scene")
        evidence_signals += 1
        signal_families.add("actor")

    # Density is a weak medium signal only. Capacity gating remains a separate
    # content-engineering responsibility and may never zero the visual budget.
    if text_count >= 10 or text_characters >= 220:
        _add(scores, reasons, "relationship_diagram", 0.06, "higher text density benefits from explicit semantic grouping")
        _add(scores, reasons, "data_visualization", 0.03, "higher information density benefits from compact evidence encoding")
        evidence_signals += 1

    specialized = sorted(
        ((medium, score) for medium, score in scores.items() if medium != "mixed"),
        key=lambda item: (-item[1], _MEDIA_TIE_ORDER.index(item[0])),
    )
    if "mixed" in scores and len(specialized) >= 2:
        first, second = specialized[:2]
        if (
            "data" in signal_families
            and len(signal_families - {"density", "scene"}) >= 2
            and first[1] >= 0.58
            and second[1] >= 0.56
            and abs(first[1] - second[1]) <= 0.08
        ):
            scores["mixed"] = min(0.94, (first[1] + second[1]) / 2 + 0.04)
            reasons["mixed"].append(
                f"two specialized media are simultaneously strong and close: {first[0]} + {second[0]}"
            )

    ranked = sorted(
        ((medium, min(0.99, max(0.0, score))) for medium, score in scores.items()),
        key=lambda item: (-item[1], _MEDIA_TIE_ORDER.index(item[0])),
    )
    preferred, top_score = ranked[0]
    secondary = ranked[1][0] if len(ranked) > 1 else ""
    second_score = ranked[1][1] if len(ranked) > 1 else 0.0
    gap = max(0.0, top_score - second_score)
    confidence = min(0.99, 0.54 + gap * 1.15 + min(0.12, evidence_signals * 0.02))
    preferred_reasons = reasons[preferred] or ["no strong specialized signal; deterministic neutral fallback"]
    rationale = (
        f"Visual Medium Resolver v2: preferred={preferred} score={top_score:.2f}; "
        + (f"secondary={secondary} score={second_score:.2f}; " if secondary else "")
        + "basis=" + "; ".join(preferred_reasons)
        + ". Medium selection uses page semantics and scene eligibility, not relationship topology."
    )
    forbidden = tuple(medium for medium in _MEDIA_TIE_ORDER if medium not in allowed)
    return VisualMediumPolicy(
        preferred=preferred,
        secondary=secondary,
        allowed=tuple(allowed),
        forbidden=forbidden,
        scene_policy=scene_policy,
        confidence=round(confidence, 3),
        scores=tuple((medium, round(score, 3)) for medium, score in ranked),
        rationale=rationale,
    )


def default_visual_medium_policy(scene_policy: str) -> VisualMediumPolicy:
    """Compatibility projection with no semantic hints.

    ``mixed`` is deliberately not the neutral default in v2. New production
    callers should provide semantic inputs through :func:`resolve_visual_medium_policy`.
    """

    return _semantic_policy(
        scene_policy=scene_policy,
        page_mission="",
        business_relationships=(),
        text_count=0,
        text_characters=0,
        business_object="",
        actor_type="",
        data_available=False,
    )


def resolve_visual_medium_policy(
    value: object,
    *,
    scene_policy: str,
    page_mission: str = "",
    business_relationships: object = (),
    text_count: int = 0,
    text_characters: int = 0,
    business_object: str = "",
    actor_type: str = "",
    data_available: bool = False,
) -> VisualMediumPolicy:
    """Resolve v2 medium policy while preserving explicit legacy policies.

    An explicit policy remains authoritative and is normalized to v2 fields.
    Missing policy is scored from semantic inputs.  ``mixed`` is selected only
    when two specialized media are independently strong and close in score.
    """

    if isinstance(value, Mapping):
        policy = validate_visual_medium_policy(value)
        if policy.scene_policy != scene_policy:
            raise ValueError("visual_medium_policy.scene_policy must match image scene_policy")
        return policy
    return _semantic_policy(
        scene_policy=scene_policy,
        page_mission=page_mission,
        business_relationships=business_relationships,
        text_count=max(0, int(text_count)),
        text_characters=max(0, int(text_characters)),
        business_object=business_object,
        actor_type=actor_type,
        data_available=bool(data_available),
    )


__all__ = [
    "SCENE_POLICIES",
    "VISUAL_MEDIA",
    "VISUAL_MEDIUM_POLICY_VERSION",
    "VisualMediumPolicy",
    "default_visual_medium_policy",
    "resolve_visual_medium_policy",
    "validate_visual_medium_policy",
]
