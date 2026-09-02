"""Structured intermediate representation for the final ImageGen prompt.

The IR is the single normalized shape between the audited ``PageArtifactSpec``
and the final prompt text. It carries model-facing semantic content plus a
small amount of debug-only binding metadata that the renderer never exposes.
"""

from __future__ import annotations

from dataclasses import dataclass

MAX_SEMANTIC_GROUPS = 10
# The rendered contract now binds exact text to semantic groups and renders each
# visible string once, so persisted debug receipts must record the new version.
# v4 additionally preserves per-line visible-text hierarchy so the prompt can
# render a shared group heading, peer groups, and their details distinctly.
FINAL_PROMPT_IR_VERSION = "v4"
_DANGLING_JUDGMENT_SUFFIXES = ("可信",)


class PromptContractError(ValueError):
    """Raised when normalized content violates the final prompt contract."""


def _dangling_phrase(text: str) -> bool:
    stripped = text.strip().rstrip("。.!！?？")
    return any(stripped.endswith(suffix) for suffix in _DANGLING_JUDGMENT_SUFFIXES)


@dataclass(frozen=True)
class SemanticGroupIR:
    """One deterministic bucket of evidence grouped by audited content root."""

    id: str
    role: str
    summary: str
    emphasis: str = "secondary"

    def __post_init__(self) -> None:
        if self.emphasis not in {"primary", "secondary"}:
            raise PromptContractError(
                f"semantic group {self.id!r} emphasis must be primary or secondary, got {self.emphasis!r}"
            )
        if not self.id.strip():
            raise PromptContractError("semantic group requires a non-empty id")
        if not self.summary.strip():
            raise PromptContractError(f"semantic group {self.id!r} requires a summary")


@dataclass(frozen=True)
class TextBindingIR:
    """Text ownership for one semantic group.

    ``group_id`` and ``text_ids`` are debug-only keys. The renderer uses group
    order/role and ``exact_text`` but never emits backend identifiers.
    """

    group_id: str
    role: str
    hierarchy_level: int
    exact_text: tuple[str, ...]
    text_ids: tuple[str, ...] = ()
    hierarchy_levels: tuple[int, ...] = ()

    def __post_init__(self) -> None:
        if not self.group_id.strip():
            raise PromptContractError("text binding requires group_id")
        if not self.exact_text:
            raise PromptContractError(f"text binding {self.group_id!r} requires exact text")
        if self.hierarchy_level <= 0:
            raise PromptContractError("text binding hierarchy_level must be positive")
        if self.text_ids and len(self.text_ids) != len(self.exact_text):
            raise PromptContractError("text binding text_ids must align one-to-one with exact_text")
        if self.hierarchy_levels:
            if len(self.hierarchy_levels) != len(self.exact_text):
                raise PromptContractError("text binding hierarchy_levels must align one-to-one with exact_text")
            if any(level <= 0 for level in self.hierarchy_levels):
                raise PromptContractError("text binding hierarchy_levels must be positive")


@dataclass(frozen=True)
class CompositionIR:
    spatial_organization: str
    primary_focus: str
    visual_responsibility: tuple[str, ...]
    focus_policy: str = "single_anchor"

    def __post_init__(self) -> None:
        if not self.spatial_organization.strip():
            raise PromptContractError("composition requires spatial organization")
        if not self.primary_focus.strip():
            raise PromptContractError("composition requires a primary focus")
        if self.focus_policy not in {"single_anchor", "paired_focus", "peer_field", "distributed_focus", "sequence_focus"}:
            raise PromptContractError(f"unsupported prompt focus policy: {self.focus_policy!r}")


@dataclass(frozen=True)
class RegionIR:
    id: str
    semantic_refs: tuple[str, ...]
    role: str
    anchor: str
    weight: float
    span: str
    priority: str
    text_ids: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not self.id.strip() or not self.semantic_refs:
            raise PromptContractError("region IR requires id and semantic refs")
        if not 0 < self.weight <= 1:
            raise PromptContractError("region IR weight must be >0 and <=1")


@dataclass(frozen=True)
class RegionRelationIR:
    source: str
    target: str
    type: str


@dataclass(frozen=True)
class RegionGraphIR:
    primary_axis: str
    regions: tuple[RegionIR, ...]
    relations: tuple[RegionRelationIR, ...]

    def __post_init__(self) -> None:
        if not self.primary_axis.strip() or not self.regions:
            raise PromptContractError("region graph IR requires axis and regions")
        ids = {item.id for item in self.regions}
        if len(ids) != len(self.regions):
            raise PromptContractError("region graph IR region ids must be unique")
        if any(item.source not in ids or item.target not in ids for item in self.relations):
            raise PromptContractError("region graph IR relation references unknown region")


@dataclass(frozen=True)
class VisualMediumPolicyIR:
    preferred: str
    allowed: tuple[str, ...]
    scene_policy: str
    rationale: str

    def __post_init__(self) -> None:
        if not self.preferred.strip() or not self.allowed or not self.scene_policy.strip():
            raise PromptContractError("visual medium policy IR is incomplete")
        if self.preferred not in self.allowed:
            raise PromptContractError("preferred visual medium must be allowed")


@dataclass(frozen=True)
class MicroVisualFreedomIR:
    allowed: tuple[str, ...]
    forbidden: tuple[str, ...]

    def __post_init__(self) -> None:
        if not self.allowed or not self.forbidden:
            raise PromptContractError("micro visual freedom requires allowed and forbidden boundaries")
        if any(not item.strip() for item in (*self.allowed, *self.forbidden)):
            raise PromptContractError("micro visual freedom entries must be non-empty")
        if len(self.allowed) != len(set(self.allowed)) or len(self.forbidden) != len(set(self.forbidden)):
            raise PromptContractError("micro visual freedom entries must be unique")


@dataclass(frozen=True)
class RuntimeLockIR:
    style_contract: str
    terminal_lock: str = ""



@dataclass(frozen=True)
class FinalPromptIR:
    deliverable: str
    page_judgment: str
    dominant_relationship: str
    reading_path: tuple[str, ...]
    semantic_groups: tuple[SemanticGroupIR, ...]
    composition: CompositionIR
    visible_text: tuple[str, ...]
    hard_constraints: tuple[str, ...]
    runtime_lock: RuntimeLockIR
    page_mission: str = ""
    semantic_context: str = ""
    prompt_mode: str = "semantic_brief"
    text_bindings: tuple[TextBindingIR, ...] = ()
    region_graph: RegionGraphIR | None = None
    visual_medium_policy: VisualMediumPolicyIR | None = None
    micro_visual_freedom: MicroVisualFreedomIR | None = None

    def __post_init__(self) -> None:
        if self.prompt_mode not in {"semantic_brief", "directed_composition"}:
            raise PromptContractError(f"unsupported final prompt mode: {self.prompt_mode!r}")
        if not self.deliverable.strip():
            raise PromptContractError("final prompt IR requires a deliverable")
        if not self.page_judgment.strip():
            raise PromptContractError("final prompt IR requires a page judgment")
        if _dangling_phrase(self.page_judgment):
            raise PromptContractError(
                f"page judgment ends with a dangling phrase: {self.page_judgment!r}"
            )
        if not self.dominant_relationship.strip():
            raise PromptContractError("final prompt IR requires a dominant relationship")
        if not self.reading_path:
            raise PromptContractError("final prompt IR requires a non-empty reading path")
        if not self.semantic_groups:
            raise PromptContractError("final prompt IR requires at least one semantic group")
        if len(self.semantic_groups) > MAX_SEMANTIC_GROUPS:
            raise PromptContractError(
                "final prompt IR allows at most "
                f"{MAX_SEMANTIC_GROUPS} semantic groups, got {len(self.semantic_groups)}: "
                + ", ".join(group.id for group in self.semantic_groups)
            )
        ids = [group.id for group in self.semantic_groups]
        if len(ids) != len(set(ids)):
            raise PromptContractError("semantic group ids must be unique")
        if not self.visible_text:
            raise PromptContractError("final prompt IR requires visible text")
        if len(self.visible_text) != len(set(self.visible_text)):
            raise PromptContractError("visible text entries must be unique")
        if self.text_bindings:
            bound = tuple(text for binding in self.text_bindings for text in binding.exact_text)
            if bound != self.visible_text:
                raise PromptContractError(
                    "text bindings must cover exact visible text once and in authoritative order"
                )
            group_ids = {group.id for group in self.semantic_groups}
            unknown = [binding.group_id for binding in self.text_bindings if binding.group_id not in group_ids]
            if unknown:
                raise PromptContractError(
                    f"text bindings reference unknown semantic groups: {', '.join(unknown)}"
                )
            binding_groups = [binding.group_id for binding in self.text_bindings]
            if len(binding_groups) != len(set(binding_groups)):
                raise PromptContractError("text bindings may define each semantic group at most once")
            text_ids = tuple(text_id for binding in self.text_bindings for text_id in binding.text_ids)
            if text_ids and len(text_ids) != len(set(text_ids)):
                raise PromptContractError("text binding text_ids must be globally unique")


__all__ = [
    "FINAL_PROMPT_IR_VERSION",
    "MAX_SEMANTIC_GROUPS",
    "CompositionIR",
    "FinalPromptIR",
    "MicroVisualFreedomIR",
    "PromptContractError",
    "RegionGraphIR",
    "RegionIR",
    "RegionRelationIR",
    "RuntimeLockIR",
    "SemanticGroupIR",
    "TextBindingIR",
    "VisualMediumPolicyIR",
]
