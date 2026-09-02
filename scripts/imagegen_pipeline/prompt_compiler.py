"""Prompt compiler contracts shared by ImageGen handoff callers."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from scripts.imagegen_pipeline.creative_brief import CreativeBrief

if TYPE_CHECKING:
    from cyberppt.page_artifact_spec import PageArtifactSpec

ARTIFACT_PROMPT_COMPILER = "artifact-spec-v2"
PROMPT_COMPILERS = (
    "legacy",
    "creative-brief-v1",
    "content-first-v1",
    ARTIFACT_PROMPT_COMPILER,
)
DEFAULT_PROMPT_COMPILER = "content-first-v1"
TEXT_RENDER_MODES = ("full_image", "semantic_visual")
DEFAULT_TEXT_RENDER_MODE = "full_image"


def validate_prompt_compiler(name: str) -> str:
    value = str(name or DEFAULT_PROMPT_COMPILER).strip()
    if value not in PROMPT_COMPILERS:
        raise ValueError(
            f"unsupported prompt compiler: {value}; "
            f"choose one of {', '.join(PROMPT_COMPILERS)}"
        )
    return value


def validate_text_render_mode(name: str) -> str:
    """Validate the separation between visual generation and text rendering.

    ``full_image`` lets ImageGen render Stage 02-authored visible copy in the
    generated artifact while preserving the supplied semantic boundary.
    ``semantic_visual`` produces a text-light semantic asset for an explicitly
    selected downstream editable-information workflow.
    """

    value = str(name or DEFAULT_TEXT_RENDER_MODE).strip()
    if value not in TEXT_RENDER_MODES:
        raise ValueError(
            f"unsupported text render mode: {value}; "
            f"choose one of {', '.join(TEXT_RENDER_MODES)}"
        )
    return value


@dataclass(frozen=True)
class CompiledPagePrompt:
    """The immutable result handed to diagnostics, approval, and manifests."""

    prompt: str
    compiler_version: str
    relation: str
    creative_brief: CreativeBrief | None = None
    injected_rule_ids: tuple[str, ...] = ()
    style_selection: dict[str, Any] | None = None
    presentation: Any | None = None
    image_locked_text: str = ""
    editable_body_text: str = ""
    semantic_structure: dict[str, Any] | None = None
    text_render_mode: str = DEFAULT_TEXT_RENDER_MODE
    artifact_spec: "PageArtifactSpec | None" = None
    prompt_ir_version: str = ""
    debug_receipt: dict[str, Any] | None = None

    def build_metadata(self) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "compiler_version": self.compiler_version,
            "relation": self.relation,
            "injected_rule_ids": list(self.injected_rule_ids),
            "text_render_mode": self.text_render_mode,
        }
        if self.creative_brief is not None:
            payload["creative_brief"] = self.creative_brief.to_dict()
        if self.style_selection is not None:
            payload["style_selection"] = dict(self.style_selection)
        if self.presentation is not None:
            to_dict = getattr(self.presentation, "to_dict", None)
            payload["presentation"] = to_dict() if callable(to_dict) else self.presentation
        if self.image_locked_text:
            payload["image_locked_text"] = self.image_locked_text
        if self.editable_body_text:
            payload["editable_body_text"] = self.editable_body_text
        if self.semantic_structure is not None:
            payload["semantic_structure"] = dict(self.semantic_structure)
        if self.artifact_spec is not None:
            payload["artifact_spec"] = self.artifact_spec.to_dict()
        if self.prompt_ir_version:
            payload["prompt_ir_version"] = self.prompt_ir_version
        return payload


__all__ = [
    "CompiledPagePrompt",
    "ARTIFACT_PROMPT_COMPILER",
    "DEFAULT_PROMPT_COMPILER",
    "DEFAULT_TEXT_RENDER_MODE",
    "PROMPT_COMPILERS",
    "TEXT_RENDER_MODES",
    "validate_prompt_compiler",
    "validate_text_render_mode",
]
