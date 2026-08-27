"""Structured intermediate representation for the final ImageGen prompt.

The IR is the single normalized shape between the audited ``PageArtifactSpec``
and the final prompt text. It carries only what the image generator needs to
see; internal Stage 02 bookkeeping never reaches the rendered prompt.
"""

from __future__ import annotations

from dataclasses import dataclass

MAX_SEMANTIC_GROUPS = 10
FINAL_PROMPT_IR_VERSION = "v3"
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
    """Model-facing text ownership for one semantic group.

    ``group_id`` remains an internal IR key and is not rendered directly.  The
    renderer uses the semantic group's stable display order/role while the
    debug receipt preserves this key for traceability.
    """

    group_id: str
    role: str
    hierarchy_level: int
    exact_text: tuple[str, ...]

    def __post_init__(self) -> None:
        if not self.group_id.strip():
            raise PromptContractError("text binding requires group_id")
        if not self.exact_text:
            raise PromptContractError(f"text binding {self.group_id!r} requires exact text")
        if self.hierarchy_level <= 0:
            raise PromptContractError("text binding hierarchy_level must be positive")


@dataclass(frozen=True)
class CompositionIR:
    """Composition skeleton and per-region visual responsibility."""

    spatial_organization: str
    primary_focus: str
    visual_responsibility: tuple[str, ...]

    def __post_init__(self) -> None:
        if not self.spatial_organization.strip():
            raise PromptContractError("composition requires spatial organization")
        if not self.primary_focus.strip():
            raise PromptContractError("composition requires a primary focus")


@dataclass(frozen=True)
class RuntimeLockIR:
    """Style runtime contract plus an optional terminal enforcement lock."""

    style_contract: str
    terminal_lock: str = ""

    def __post_init__(self) -> None:
        if not self.style_contract.strip():
            raise PromptContractError("runtime lock requires a style contract")


@dataclass(frozen=True)
class FinalPromptIR:
    """The complete normalized authority for one final ImageGen prompt."""

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

    def __post_init__(self) -> None:
        if self.prompt_mode not in {"semantic_brief", "directed_composition"}:
            raise PromptContractError(
                f"unsupported final prompt mode: {self.prompt_mode!r}"
            )
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


__all__ = [
    "FINAL_PROMPT_IR_VERSION",
    "MAX_SEMANTIC_GROUPS",
    "CompositionIR",
    "FinalPromptIR",
    "PromptContractError",
    "RuntimeLockIR",
    "SemanticGroupIR",
    "TextBindingIR",
]
