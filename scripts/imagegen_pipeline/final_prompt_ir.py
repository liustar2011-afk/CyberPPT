"""Structured intermediate representation for the final ImageGen prompt.

The IR is the single normalized shape between the audited ``PageArtifactSpec``
and the final prompt text. It carries only what the image generator needs to
see; internal Stage 02 bookkeeping (relationship qualifiers, priority codes,
connector booleans, raw backend enum tokens) never reaches this type.
"""

from __future__ import annotations

from dataclasses import dataclass

# Technical safety ceiling on prompt size/complexity -- not a business rule
# about how many modules a page may have. Semantic groups now mirror Stage
# 02's authoritative root-module count (see content_integrity_contract.py);
# pages with more root modules than this should be rare, and
# MAX_PROMPT_CHARACTERS in final_prompt_contract.py remains the primary
# backstop against runaway prompt size.
MAX_SEMANTIC_GROUPS = 10

# Bump when FinalPromptIR's field shape or normalization rules change in a
# way that would make an old debug receipt misleading about how a prompt
# was built.
FINAL_PROMPT_IR_VERSION = "v2"

_DANGLING_JUDGMENT_SUFFIXES = ("可信",)


class PromptContractError(ValueError):
    """Raised when normalized content violates the final prompt contract."""


def _dangling_phrase(text: str) -> bool:
    stripped = text.strip().rstrip("。.!！?？")
    return any(stripped.endswith(suffix) for suffix in _DANGLING_JUDGMENT_SUFFIXES)


@dataclass(frozen=True)
class SemanticGroupIR:
    """One deterministic bucket of evidence, grouped by content root module
    (falling back to ``EvidenceSpec.kind`` when root structure is unavailable)."""

    id: str
    role: str
    summary: str
    emphasis: str = "secondary"

    def __post_init__(self) -> None:
        if self.emphasis not in {"primary", "secondary"}:
            raise PromptContractError(
                f"semantic group {self.id!r} emphasis must be primary or secondary, "
                f"got {self.emphasis!r}"
            )
        if not self.id.strip():
            raise PromptContractError("semantic group requires a non-empty id")
        if not self.summary.strip():
            raise PromptContractError(f"semantic group {self.id!r} requires a summary")


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


__all__ = [
    "FINAL_PROMPT_IR_VERSION",
    "MAX_SEMANTIC_GROUPS",
    "CompositionIR",
    "FinalPromptIR",
    "PromptContractError",
    "RuntimeLockIR",
    "SemanticGroupIR",
]
