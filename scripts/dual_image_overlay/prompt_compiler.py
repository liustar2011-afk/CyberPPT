"""Prompt compiler contracts shared by ImageGen handoff callers."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from scripts.dual_image_overlay.creative_brief import CreativeBrief


PROMPT_COMPILERS = ("legacy", "creative-brief-v1", "content-first-v1")
DEFAULT_PROMPT_COMPILER = "content-first-v1"


def validate_prompt_compiler(name: str) -> str:
    value = str(name or DEFAULT_PROMPT_COMPILER).strip()
    if value not in PROMPT_COMPILERS:
        raise ValueError(
            f"unsupported prompt compiler: {value}; "
            f"choose one of {', '.join(PROMPT_COMPILERS)}"
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

    def build_metadata(self) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "compiler_version": self.compiler_version,
            "relation": self.relation,
            "injected_rule_ids": list(self.injected_rule_ids),
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
        return payload


__all__ = [
    "CompiledPagePrompt",
    "DEFAULT_PROMPT_COMPILER",
    "PROMPT_COMPILERS",
    "validate_prompt_compiler",
]
