"""Machine-readable acceptance contract for Stage 02 ImageGen artifacts."""
from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any


ACCEPTANCE_CONTRACT_VERSION = "acceptance-contract-v1"


@dataclass(frozen=True)
class AcceptanceSpec:
    exact_copy_coverage: float = 1.0
    extra_text_count: int = 0
    region_ownership: str = "all_declared_copy_stays_in_assigned_macro_region"
    relationship_accuracy: str = "source_supported_relationships_only"
    hierarchy_preservation: str = "preserve_declared_hierarchy"
    minimum_readability: str = "readable_at_normal_slide_view"
    forbidden_structure_absence: bool = True
    style_lock_conformance: bool = True
    version: str = ACCEPTANCE_CONTRACT_VERSION

    def __post_init__(self) -> None:
        if self.version != ACCEPTANCE_CONTRACT_VERSION:
            raise ValueError(f"unsupported acceptance contract version: {self.version!r}")
        if self.exact_copy_coverage != 1.0:
            raise ValueError("acceptance exact_copy_coverage must be 1.0")
        if self.extra_text_count < 0:
            raise ValueError("acceptance extra_text_count cannot be negative")
        for field_name in (
            "region_ownership",
            "relationship_accuracy",
            "hierarchy_preservation",
            "minimum_readability",
        ):
            if not str(getattr(self, field_name) or "").strip():
                raise ValueError(f"acceptance {field_name} is required")
        if not self.forbidden_structure_absence:
            raise ValueError("acceptance requires forbidden structure absence")
        if not self.style_lock_conformance:
            raise ValueError("acceptance requires style lock conformance")

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def build_acceptance_spec(*, allowed_extra_text_count: int = 0) -> AcceptanceSpec:
    """Build the strict production acceptance target.

    ``extra_text_count`` represents the maximum visible extra-copy count allowed
    by the page contract.  The normal Stage2 path remains zero.
    """

    return AcceptanceSpec(extra_text_count=max(0, int(allowed_extra_text_count)))


__all__ = [
    "ACCEPTANCE_CONTRACT_VERSION",
    "AcceptanceSpec",
    "build_acceptance_spec",
]
