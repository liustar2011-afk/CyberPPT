"""Approval-chain primitives for ImageGen prompts.

The manifest layer can use these helpers without importing the full prompt
compiler.  A prompt is fresh only when the canonical text and the consumed
text still match the text that was approved.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from pathlib import Path
from typing import Any


def prompt_sha256(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


APPROVED_OVERRIDE_MARKER = "【本轮视觉返工要求｜不上屏】"


@dataclass(frozen=True)
class PromptApproval:
    approved_path: Path
    approved_prompt: str
    canonical_prompt: str
    consumed_prompt: str

    @property
    def approved_hash(self) -> str:
        return prompt_sha256(self.approved_prompt)

    @property
    def canonical_hash(self) -> str:
        return prompt_sha256(self.canonical_prompt)

    @property
    def consumed_hash(self) -> str:
        return prompt_sha256(self.consumed_prompt)

    @property
    def stale(self) -> bool:
        # Approval is meaningful only for the exact compiler output that is
        # consumed by ImageGen.  Do not silently accept a visual override or
        # post-approval enrichment: both require a new final approval.
        return not (
            self.approved_prompt == self.canonical_prompt == self.consumed_prompt
        )

    def metadata(self) -> dict[str, Any]:
        return {
            "approved_path": str(self.approved_path.resolve()),
            "approved_prompt_sha256": self.approved_hash,
            "canonical_prompt_sha256": self.canonical_hash,
            "canonical_matches_approval": not self.stale,
            "consumed_prompt_sha256": self.consumed_hash,
            "consumed_from": "approved_prompt",
            "approved_visual_override": APPROVED_OVERRIDE_MARKER in self.approved_prompt,
            "status": "stale" if self.stale else "fresh",
        }


def build_prompt_approval(
    *,
    approved_path: Path,
    approved_prompt: str,
    canonical_prompt: str,
    consumed_prompt: str,
) -> PromptApproval:
    return PromptApproval(
        approved_path=approved_path,
        approved_prompt=approved_prompt,
        canonical_prompt=canonical_prompt,
        consumed_prompt=consumed_prompt,
    )


def assert_prompt_fresh(approval: PromptApproval, *, page_number: int) -> None:
    if approval.stale:
        raise ValueError(
            f"approved ImageGen prompt is stale for page {page_number}; "
            "re-stage and reapprove the page prompt before generation"
        )


__all__ = [
    "PromptApproval",
    "assert_prompt_fresh",
    "build_prompt_approval",
    "prompt_sha256",
]
