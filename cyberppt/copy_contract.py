from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, Mapping, Sequence


COPY_CONTRACT_VERSION = "copy-contract-v1"
_ALLOWED_LOCKED_TRANSFORMATIONS = frozenset({"line_break", "grouping", "position_change"})


def _value(item: Any, key: str, default: Any = None) -> Any:
    if isinstance(item, Mapping):
        return item.get(key, default)
    return getattr(item, key, default)


def _clean(value: Any) -> str:
    return str(value or "").strip()


def _hierarchy(value: Any) -> int:
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        parsed = 3
    return max(1, parsed)


@dataclass(frozen=True)
class LockedCopySpec:
    """Exact visible copy that Stage2 must never rewrite."""

    text_id: str
    text: str
    count: int = 1
    semantic_role: str = "supporting_copy"
    hierarchy: int = 3
    region_id: str = ""
    placement_intent: str = ""
    allowed_transformations: tuple[str, ...] = ("line_break",)

    def __post_init__(self) -> None:
        if not self.text_id.strip():
            raise ValueError("locked copy requires text_id")
        if not self.text.strip():
            raise ValueError(f"locked copy {self.text_id!r} requires non-empty text")
        if self.count != 1:
            raise ValueError(f"locked copy {self.text_id!r} must render exactly once")
        unknown = set(self.allowed_transformations) - _ALLOWED_LOCKED_TRANSFORMATIONS
        if unknown:
            raise ValueError(
                f"locked copy {self.text_id!r} has unsupported transformations: {sorted(unknown)}"
            )


@dataclass(frozen=True)
class RewriteableCopySpec:
    """Copy that Stage01 explicitly authorizes Stage2 to compress or rewrite."""

    text_id: str
    source_text: str
    semantic_role: str = "supporting_explanation"
    hierarchy: int = 3
    region_id: str = ""
    max_length: int = 0
    rewrite_goal: str = "concise presentation copy"
    preserve: tuple[str, ...] = (
        "actors",
        "numbers",
        "dates",
        "units",
        "responsibility",
        "status",
        "claim_strength",
    )

    def __post_init__(self) -> None:
        if not self.text_id.strip():
            raise ValueError("rewriteable copy requires text_id")
        if not self.source_text.strip():
            raise ValueError(f"rewriteable copy {self.text_id!r} requires source_text")
        if self.max_length < 0:
            raise ValueError(f"rewriteable copy {self.text_id!r} max_length cannot be negative")


@dataclass(frozen=True)
class ExtraTextPolicySpec:
    allowed: bool = False
    max_count: int = 0

    def __post_init__(self) -> None:
        if self.max_count < 0:
            raise ValueError("extra text max_count cannot be negative")
        if not self.allowed and self.max_count != 0:
            raise ValueError("extra text max_count must be 0 when extra text is forbidden")


@dataclass(frozen=True)
class CopyContractSpec:
    """Single authority for what visible copy may be rendered and transformed."""

    locked_copy: tuple[LockedCopySpec, ...]
    rewriteable_copy: tuple[RewriteableCopySpec, ...] = ()
    extra_text: ExtraTextPolicySpec = ExtraTextPolicySpec()
    version: str = COPY_CONTRACT_VERSION

    def __post_init__(self) -> None:
        validate_copy_contract(self)

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


def validate_copy_contract(contract: CopyContractSpec) -> None:
    if contract.version != COPY_CONTRACT_VERSION:
        raise ValueError(f"unsupported copy contract version: {contract.version!r}")

    locked_ids = [item.text_id for item in contract.locked_copy]
    rewriteable_ids = [item.text_id for item in contract.rewriteable_copy]

    if len(locked_ids) != len(set(locked_ids)):
        raise ValueError("copy contract contains duplicate locked_copy text_id values")
    if len(rewriteable_ids) != len(set(rewriteable_ids)):
        raise ValueError("copy contract contains duplicate rewriteable_copy text_id values")

    overlap = set(locked_ids) & set(rewriteable_ids)
    if overlap:
        raise ValueError(f"copy contract text_id cannot be both locked and rewriteable: {sorted(overlap)}")


def build_copy_contract(
    visible_text_bindings: Sequence[Any],
    *,
    region_by_text_id: Mapping[str, str] | None = None,
    explicit_rewriteable_text_ids: Sequence[str] = (),
    rewrite_max_length_by_text_id: Mapping[str, int] | None = None,
    rewrite_goal_by_text_id: Mapping[str, str] | None = None,
    extra_text_allowed: bool = False,
    extra_text_max_count: int = 0,
) -> CopyContractSpec:
    """Build the copy authority from authored visible-text bindings.

    All authored visible text is locked by default. A text item may become
    rewriteable only when its id is explicitly supplied by the caller. This
    prevents Stage2 fallback logic from silently downgrading exact copy.
    """

    region_by_text_id = region_by_text_id or {}
    rewrite_max_length_by_text_id = rewrite_max_length_by_text_id or {}
    rewrite_goal_by_text_id = rewrite_goal_by_text_id or {}
    rewriteable_ids = {_clean(item) for item in explicit_rewriteable_text_ids if _clean(item)}

    locked: list[LockedCopySpec] = []
    rewriteable: list[RewriteableCopySpec] = []
    seen_ids: set[str] = set()

    for binding in visible_text_bindings:
        text_id = _clean(_value(binding, "text_id"))
        text = _clean(_value(binding, "text", _value(binding, "exact_text")))
        if not text_id:
            raise ValueError("visible text binding requires text_id")
        if not text:
            raise ValueError(f"visible text binding {text_id!r} requires text")
        if text_id in seen_ids:
            raise ValueError(f"duplicate visible text binding text_id: {text_id!r}")
        seen_ids.add(text_id)

        role = _clean(_value(binding, "role", _value(binding, "semantic_role"))) or "supporting_copy"
        hierarchy = _hierarchy(_value(binding, "hierarchy_level", _value(binding, "hierarchy", 3)))
        region_id = _clean(region_by_text_id.get(text_id, _value(binding, "region_id", "")))

        if text_id in rewriteable_ids:
            rewriteable.append(
                RewriteableCopySpec(
                    text_id=text_id,
                    source_text=text,
                    semantic_role=role,
                    hierarchy=hierarchy,
                    region_id=region_id,
                    max_length=max(0, int(rewrite_max_length_by_text_id.get(text_id, 0) or 0)),
                    rewrite_goal=_clean(rewrite_goal_by_text_id.get(text_id))
                    or "concise presentation copy",
                )
            )
            continue

        locked.append(
            LockedCopySpec(
                text_id=text_id,
                text=text,
                semantic_role=role,
                hierarchy=hierarchy,
                region_id=region_id,
            )
        )

    unknown_rewriteable = rewriteable_ids - seen_ids
    if unknown_rewriteable:
        raise ValueError(
            "explicit rewriteable ids are not present in visible text bindings: "
            + ", ".join(sorted(unknown_rewriteable))
        )

    return CopyContractSpec(
        locked_copy=tuple(locked),
        rewriteable_copy=tuple(rewriteable),
        extra_text=ExtraTextPolicySpec(
            allowed=bool(extra_text_allowed),
            max_count=extra_text_max_count if extra_text_allowed else 0,
        ),
    )
