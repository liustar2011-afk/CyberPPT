from cyberppt.source_detail_visibility import (
    functional_group_needs_item_explanations,
    is_bare_business_label,
    source_has_richer_item_detail,
)


def test_compact_business_names_are_bare_labels() -> None:
    assert is_bare_business_label("统一目录")
    assert is_bare_business_label("安全保障")
    assert is_bare_business_label("绿色低碳")
    assert not is_bare_business_label("绿色低碳：检验标准适用性")


def test_source_detail_detection_distinguishes_explanation_from_enumeration() -> None:
    assert source_has_richer_item_detail(
        "绿色低碳",
        ["绿色低碳场景用于检验标准在电碳业务中的适用性和可操作性"],
    )
    assert not source_has_richer_item_detail(
        "绿色低碳",
        ["重点场景包括行业治理、市场运行、绿色低碳、科技创新等方向"],
    )


def test_functional_group_requires_payload_with_explicit_thin_source_escape() -> None:
    items = ["行业治理", "市场运行", "绿色低碳", "科技创新"]
    assert functional_group_needs_item_explanations("重点验证场景", items)
    assert not functional_group_needs_item_explanations(
        "重点验证场景", items, label_only_allowed=True
    )
    assert not functional_group_needs_item_explanations(
        "重点验证场景", items, content_load="light"
    )
