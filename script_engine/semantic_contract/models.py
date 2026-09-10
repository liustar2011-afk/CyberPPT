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
    """One deterministic or review-required semantic-contract finding."""

    code: str
    message: str
    slide_id: str = ""
    module_id: str = ""
    target: str = ""
    severity: str = "blocking"
    claim_refs: tuple[str, ...] = ()
    evidence_refs: tuple[str, ...] = ()
    relation: str = ""

    def render(self) -> str:
        scope = "/".join(
            part for part in (self.slide_id, self.module_id, self.target) if part
        )
        prefix = f"[{self.code}]"
        detail = f"{prefix} {scope}: {self.message}" if scope else f"{prefix} {self.message}"
        metadata: list[str] = []
        if self.relation:
            metadata.append(f"relation={self.relation}")
        if self.claim_refs:
            metadata.append(f"claims={','.join(self.claim_refs)}")
        if self.evidence_refs:
            metadata.append(f"evidence={','.join(self.evidence_refs)}")
        if metadata:
            detail += f" ({'; '.join(metadata)})"
        return detail

    def to_dict(self) -> dict[str, Any]:
        return {
            "code": self.code,
            "severity": self.severity,
            "page_id": self.slide_id,
            "module_id": self.module_id,
            "target": self.target,
            "claim_refs": list(self.claim_refs),
            "evidence_refs": list(self.evidence_refs),
            "relation": self.relation,
            "reason": self.message,
        }
