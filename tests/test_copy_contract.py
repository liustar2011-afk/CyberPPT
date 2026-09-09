from __future__ import annotations

from dataclasses import dataclass

import pytest

from cyberppt.copy_contract import (
    COPY_CONTRACT_VERSION,
    CopyContractSpec,
    ExtraTextPolicySpec,
    LockedCopySpec,
    RewriteableCopySpec,
    build_copy_contract,
)


@dataclass(frozen=True)
class _Binding:
    text_id: str
    text: str
    role: str
    hierarchy_level: int


def test_authored_copy_is_locked_by_default_and_preserves_region_ownership() -> None:
    contract = build_copy_contract(
        (
            _Binding("P01-T01", "电力领域数据基础设施", "primary_judgment", 1),
            _Binding("P01-T02", "数据资源组织", "peer_group_heading", 2),
        ),
        region_by_text_id={"P01-T01": "region-hero", "P01-T02": "region-resource"},
    )

    assert contract.version == COPY_CONTRACT_VERSION
    assert contract.rewriteable_copy == ()
    assert contract.extra_text == ExtraTextPolicySpec(allowed=False, max_count=0)
    assert [item.text for item in contract.locked_copy] == [
        "电力领域数据基础设施",
        "数据资源组织",
    ]
    assert [item.count for item in contract.locked_copy] == [1, 1]
    assert [item.region_id for item in contract.locked_copy] == ["region-hero", "region-resource"]
    assert all(item.allowed_transformations == ("line_break",) for item in contract.locked_copy)


def test_copy_becomes_rewriteable_only_with_explicit_authorization() -> None:
    bindings = (
        _Binding("P01-T01", "一级判断保持原文", "primary_judgment", 1),
        _Binding("P01-T02", "这是一段明确允许视觉阶段压缩的支持性说明", "supporting_copy", 3),
    )

    contract = build_copy_contract(
        bindings,
        explicit_rewriteable_text_ids=("P01-T02",),
        rewrite_max_length_by_text_id={"P01-T02": 18},
        rewrite_goal_by_text_id={"P01-T02": "压缩为结论先行的支持性说明"},
    )

    assert [item.text_id for item in contract.locked_copy] == ["P01-T01"]
    assert [item.text_id for item in contract.rewriteable_copy] == ["P01-T02"]
    rewriteable = contract.rewriteable_copy[0]
    assert rewriteable.max_length == 18
    assert rewriteable.rewrite_goal == "压缩为结论先行的支持性说明"
    assert "claim_strength" in rewriteable.preserve


def test_unknown_explicit_rewriteable_id_is_rejected() -> None:
    with pytest.raises(ValueError, match="not present"):
        build_copy_contract(
            (_Binding("P01-T01", "原文", "primary_judgment", 1),),
            explicit_rewriteable_text_ids=("P01-T99",),
        )


def test_duplicate_binding_ids_are_rejected() -> None:
    with pytest.raises(ValueError, match="duplicate visible text binding"):
        build_copy_contract(
            (
                _Binding("P01-T01", "甲", "supporting_copy", 3),
                _Binding("P01-T01", "乙", "supporting_copy", 3),
            )
        )


def test_contract_rejects_locked_rewriteable_overlap() -> None:
    with pytest.raises(ValueError, match="both locked and rewriteable"):
        CopyContractSpec(
            locked_copy=(LockedCopySpec(text_id="T1", text="锁定文本"),),
            rewriteable_copy=(RewriteableCopySpec(text_id="T1", source_text="可改写文本"),),
        )


def test_locked_copy_rejects_rewrite_transformation() -> None:
    with pytest.raises(ValueError, match="unsupported transformations"):
        LockedCopySpec(
            text_id="T1",
            text="锁定文本",
            allowed_transformations=("line_break", "rewrite"),
        )


def test_extra_text_policy_is_closed_by_default() -> None:
    contract = build_copy_contract((_Binding("T1", "唯一上屏文字", "primary_judgment", 1),))
    assert contract.extra_text.allowed is False
    assert contract.extra_text.max_count == 0


def test_extra_text_policy_can_only_open_explicitly() -> None:
    contract = build_copy_contract(
        (_Binding("T1", "唯一上屏文字", "primary_judgment", 1),),
        extra_text_allowed=True,
        extra_text_max_count=2,
    )
    assert contract.extra_text == ExtraTextPolicySpec(allowed=True, max_count=2)
