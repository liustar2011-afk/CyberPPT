from __future__ import annotations

from script_engine.semantic_contract.source_boundary import (
    collect_source_boundary_diagnostics,
)


def _foundation(statement: str) -> dict:
    return {
        "facts": [{"id": "F1", "statement": statement}],
        "concepts": [],
        "entities": [],
        "relations": [],
        "arguments": [],
        "constraints": [],
        "numbers": [],
        "source_structure": [],
    }


def _script(text: str) -> dict:
    return {
        "contract": "cyberppt.final-script",
        "version": "1.0",
        "slides": [
            {
                "id": "P01",
                "page_type": "content",
                "title": "来源边界",
                "full_copy": text,
                "onscreen": [{"heading": "来源边界", "text": text}],
            }
        ],
    }


def test_foundation_number_is_allowed() -> None:
    diagnostics = collect_source_boundary_diagnostics(
        _script("现有12项要求保持不变。"),
        _foundation("现有12项要求保持不变。"),
    )

    assert diagnostics == []


def test_typed_number_value_list_is_allowed() -> None:
    foundation = _foundation("范围由结构化数值记录给出。")
    foundation["numbers"] = [
        {"id": "N1", "value": [12, 18], "unit": "项"}
    ]

    diagnostics = collect_source_boundary_diagnostics(
        _script("范围为12至18项。"),
        foundation,
    )

    assert diagnostics == []


def test_unknown_number_is_structured_blocker() -> None:
    diagnostics = collect_source_boundary_diagnostics(
        _script("新增99项处理要求。"),
        _foundation("来源事实未给出新增数量。"),
    )

    assert diagnostics
    assert {diagnostic.code for diagnostic in diagnostics} == {
        "FINAL_NUMBER_OUTSIDE_FOUNDATION"
    }
    assert all(diagnostic.severity == "blocking" for diagnostic in diagnostics)
    assert any("99" in diagnostic.message for diagnostic in diagnostics)
    assert any(diagnostic.target.endswith("full_copy") for diagnostic in diagnostics)


def test_v11_structured_onscreen_item_text_is_checked() -> None:
    final_script = {
        "contract": "cyberppt.final-script",
        "version": "1.1",
        "slides": [
            {
                "id": "P01",
                "page_type": "content",
                "onscreen": [
                    {
                        "id": "M01",
                        "heading": "执行要求",
                        "items": [{"id": "M01-I01", "text": "新增77项要求"}],
                    }
                ],
            }
        ],
    }

    diagnostics = collect_source_boundary_diagnostics(
        final_script,
        _foundation("来源事实只说明执行要求。"),
    )

    assert any(
        diagnostic.code == "FINAL_NUMBER_OUTSIDE_FOUNDATION"
        and diagnostic.target == "slides.0.onscreen[0].items[0].text"
        and "77" in diagnostic.message
        for diagnostic in diagnostics
    )


def test_relationship_numeric_payload_is_checked() -> None:
    final_script = {
        "contract": "cyberppt.final-script",
        "version": "1.0",
        "slides": [
            {
                "id": "P01",
                "page_type": "content",
                "relationships": [
                    {"from": "阶段1", "relation": "连接", "to": "阶段2"}
                ],
            }
        ],
    }

    diagnostics = collect_source_boundary_diagnostics(
        final_script,
        _foundation("来源事实不包含阶段编号。"),
    )

    messages = "\n".join(diagnostic.message for diagnostic in diagnostics)
    assert "1" in messages
    assert "2" in messages
