"""Typed primitives for the Stage 01 semantic provenance contract."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


PROVENANCE_DERIVATIONS = frozenset({"direct", "synthesis", "relation"})
PROVENANCE_RELATIONS = frozenset(
    {"expresses", "supports", "qualifies", "implements", "contrasts", "sequences"}
)


@dataclass(frozen=True)
class FoundationRecord:
    """One addressable semantic record from Foundation."""

    ref: str
    kind: str
    payload: dict[str, Any]


@dataclass(frozen=True)
class SemanticDiagnostic:
    """Deterministic semantic-contract diagnostic."""

    code: str
    message: str
    slide_id: str = ""
    module_id: str = ""
    target: str = ""

    def render(self) -> str:
        scope = "/".join(
            part for part in (self.slide_id, self.module_id, self.target) if part
        )
        prefix = f"[{self.code}]"
        return f"{prefix} {scope}: {self.message}" if scope else f"{prefix} {self.message}"
