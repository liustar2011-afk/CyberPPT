from __future__ import annotations

from script_engine.page_source_packet import build_page_source_packet


def test_page_source_packet_returns_exact_full_unit_not_long_mode_preview() -> None:
    exact = (
        "这是一个没有数字、日期、责任、必须等关键标记的长段落。"
        "它主要解释概念之间的边界、业务含义和上下文，因此可能不会被默认长文阅读策略选为深读单元。"
        "Page Source Packet 在 AUTHOR 写具体页面时仍必须返回这段完整原文，而不是 source context 中可能出现的 180 字预览。"
        "为了验证不会截断，这里继续补充足够长的解释文字，并保留最后的唯一结束标记 EXACT-END。"
    )
    page = {"id": "P01", "title": "概念说明", "source_refs": ["F1"]}
    foundation = {
        "facts": [
            {
                "id": "F1",
                "statement": "来源段落解释了概念边界和业务含义。",
                "source_refs": ["SU-001"],
            }
        ]
    }
    source_index = {
        "schema": "cyberppt.source_index.v2",
        "units": [
            {
                "unit_id": "SU-001",
                "source_id": "SRC-1",
                "kind": "paragraph",
                "heading_id": "H-01",
                "text": exact,
                "locator": {"paragraph": 12},
            }
        ],
    }

    packet = build_page_source_packet(page, foundation, source_index)

    assert packet["status"] == "passed"
    assert packet["authority"] == "derived_runtime_context"
    assert packet["page_source_refs"] == ["F1"]
    assert packet["evidence"][0]["foundation_ref"] == "F1"
    assert packet["evidence"][0]["exact_source_units"][0]["text"] == exact
    assert packet["evidence"][0]["exact_source_units"][0]["text"].endswith("EXACT-END。")
    assert packet["issues"] == []
    assert packet["warnings"] == []


def test_page_source_packet_expands_protected_numbers_actors_conditions_and_status() -> None:
    page = {"id": "P02", "title": "推进状态", "source_refs": ["F1"]}
    foundation = {
        "facts": [
            {
                "id": "F1",
                "statement": "甲单位计划在验收通过后开展三项工作。",
                "source_refs": ["SU-010"],
                "entity_refs": ["E1"],
                "number_refs": ["N1"],
                "conditions": ["验收通过后"],
                "status": "规划",
                "strength": "stated",
                "visibility": "internal_only",
            }
        ],
        "entities": [
            {"id": "E1", "name": "甲单位", "source_refs": ["SU-010"]}
        ],
        "numbers": [
            {
                "id": "N1",
                "value": 3,
                "unit": "项",
                "context": "开展三项工作",
                "source_refs": ["SU-010"],
            }
        ],
    }
    source_index = {
        "schema": "cyberppt.source_index.v2",
        "units": [
            {
                "unit_id": "SU-010",
                "source_id": "SRC-1",
                "kind": "paragraph",
                "heading_id": "H-02",
                "text": "甲单位计划在验收通过后开展三项工作。",
            }
        ],
    }

    packet = build_page_source_packet(page, foundation, source_index)
    protected = packet["evidence"][0]["protected"]

    assert protected["actors"] == [{"id": "E1", "name": "甲单位"}]
    assert protected["numbers"] == [
        {"id": "N1", "value": 3, "unit": "项", "context": "开展三项工作"}
    ]
    assert protected["conditions"] == ["验收通过后"]
    assert protected["status"] == "规划"
    assert protected["strength"] == "stated"
    assert protected["visibility"] == "internal_only"


def test_page_source_packet_blocks_unknown_page_source_ref() -> None:
    packet = build_page_source_packet(
        {"id": "P03", "title": "未知来源", "source_refs": ["UNKNOWN"]},
        {"facts": []},
        {"schema": "cyberppt.source_index.v2", "units": []},
    )

    assert packet["status"] == "blocked"
    assert packet["evidence"] == []
    assert packet["issues"] == [
        "PAGE_SOURCE_REF_UNKNOWN: page source ref 'UNKNOWN' is not in Foundation or source index"
    ]
    assert packet["warnings"] == []


def test_page_source_packet_blocks_when_exact_source_is_unresolved() -> None:
    packet = build_page_source_packet(
        {"id": "P04", "title": "缺少原文", "source_refs": ["F1"]},
        {
            "facts": [
                {"id": "F1", "statement": "只有 Foundation 摘要。", "source_refs": ["SU-MISSING"]}
            ]
        },
        {"schema": "cyberppt.source_index.v2", "units": []},
    )

    assert packet["status"] == "blocked"
    assert packet["evidence"][0]["statement"] == "只有 Foundation 摘要。"
    assert packet["evidence"][0]["exact_source_units"] == []
    assert packet["issues"] == [
        "PAGE_SOURCE_EXACT_TEXT_UNRESOLVED: F1 has source refs ['SU-MISSING'] but none resolve in source-index.v2"
    ]
    assert packet["warnings"] == []


def test_page_source_packet_blocks_when_source_unit_binding_is_missing() -> None:
    packet = build_page_source_packet(
        {"id": "P05", "title": "缺少绑定", "source_refs": ["F1"]},
        {"facts": [{"id": "F1", "statement": "Foundation 事实没有绑定原始单元。"}]},
        {"schema": "cyberppt.source_index.v2", "units": []},
    )

    assert packet["status"] == "blocked"
    assert packet["issues"] == [
        "PAGE_SOURCE_UNIT_BINDING_MISSING: F1 has no source-unit refs"
    ]
    assert packet["warnings"] == []


def test_page_source_packet_blocks_partial_exact_source_resolution() -> None:
    packet = build_page_source_packet(
        {"id": "P06", "title": "部分原文", "source_refs": ["F1"]},
        {
            "facts": [
                {
                    "id": "F1",
                    "statement": "事实依赖两个原始单元。",
                    "source_refs": ["SU-001", "SU-MISSING"],
                }
            ]
        },
        {
            "schema": "cyberppt.source_index.v2",
            "units": [
                {
                    "unit_id": "SU-001",
                    "source_id": "SRC-1",
                    "kind": "paragraph",
                    "text": "只解析到了第一个原始单元。",
                }
            ],
        },
    )

    assert packet["status"] == "blocked"
    assert packet["evidence"][0]["exact_source_units"][0]["unit_id"] == "SU-001"
    assert packet["issues"] == [
        "PAGE_SOURCE_EXACT_TEXT_PARTIAL: F1 has unresolved source refs ['SU-MISSING']"
    ]
    assert packet["warnings"] == []
