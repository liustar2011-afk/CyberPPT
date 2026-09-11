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


def _script(text: str, *, source_refs: list[str] | None = None) -> dict:
    slide = {
        "id": "P01",
        "page_type": "content",
        "title": "来源边界",
        "full_copy": text,
        "onscreen": [{"heading": "来源边界", "text": text}],
    }
    if source_refs is not None:
        slide["source_refs"] = source_refs
    return {
        "contract": "cyberppt.final-script",
        "version": "1.0",
        "slides": [slide],
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


def test_number_elsewhere_in_foundation_but_outside_slide_evidence_is_blocked() -> None:
    foundation = _foundation("本页仅说明执行安排。")
    foundation["facts"].append({"id": "F2", "statement": "另一页包含12项要求。"})

    diagnostics = collect_source_boundary_diagnostics(
        _script("本页包含12项要求。", source_refs=["F1"]),
        foundation,
    )

    assert any(
        diagnostic.code == "FINAL_NUMBER_OUTSIDE_SLIDE_EVIDENCE"
        and diagnostic.evidence_refs == ("F1",)
        and "12" in diagnostic.message
        for diagnostic in diagnostics
    )
    assert not any(
        diagnostic.code == "FINAL_NUMBER_OUTSIDE_FOUNDATION"
        for diagnostic in diagnostics
    )


def test_number_reachable_through_cited_number_ref_is_allowed() -> None:
    foundation = _foundation("范围由结构化数值记录给出。")
    foundation["facts"][0]["number_refs"] = ["N1"]
    foundation["numbers"] = [{"id": "N1", "value": 12, "unit": "项"}]

    diagnostics = collect_source_boundary_diagnostics(
        _script("范围为12项。", source_refs=["F1"]),
        foundation,
    )

    assert not any(
        diagnostic.code in {
            "FINAL_NUMBER_OUTSIDE_FOUNDATION",
            "FINAL_NUMBER_OUTSIDE_SLIDE_EVIDENCE",
        }
        for diagnostic in diagnostics
    )


def test_formal_instrument_outside_foundation_is_blocked() -> None:
    diagnostics = collect_source_boundary_diagnostics(
        _script("按照《新增管理办法》执行。"),
        _foundation("来源事实未列出正式文书。"),
    )

    assert any(
        diagnostic.code == "FINAL_FORMAL_INSTRUMENT_OUTSIDE_FOUNDATION"
        and "《新增管理办法》" in diagnostic.message
        for diagnostic in diagnostics
    )


def test_formal_instrument_elsewhere_but_outside_slide_evidence_is_blocked() -> None:
    foundation = _foundation("本页仅说明执行安排。")
    foundation["facts"].append(
        {"id": "F2", "statement": "另一页引用《专项管理办法》。"}
    )

    diagnostics = collect_source_boundary_diagnostics(
        _script("按照《专项管理办法》执行。", source_refs=["F1"]),
        foundation,
    )

    assert any(
        diagnostic.code == "FINAL_FORMAL_INSTRUMENT_OUTSIDE_SLIDE_EVIDENCE"
        and diagnostic.evidence_refs == ("F1",)
        and "《专项管理办法》" in diagnostic.message
        for diagnostic in diagnostics
    )
    assert not any(
        diagnostic.code == "FINAL_FORMAL_INSTRUMENT_OUTSIDE_FOUNDATION"
        for diagnostic in diagnostics
    )


def test_formal_instrument_in_cited_record_is_allowed() -> None:
    foundation = _foundation("本页依据《专项管理办法》执行。")

    diagnostics = collect_source_boundary_diagnostics(
        _script("按照《专项管理办法》执行。", source_refs=["F1"]),
        foundation,
    )

    assert not any(
        diagnostic.code.startswith("FINAL_FORMAL_INSTRUMENT_OUTSIDE_")
        for diagnostic in diagnostics
    )


def test_no_slide_source_refs_does_not_create_page_scope_finding() -> None:
    foundation = _foundation("另一处来源包含12项要求和《专项管理办法》。")

    diagnostics = collect_source_boundary_diagnostics(
        _script("本页使用12项要求和《专项管理办法》。"),
        foundation,
    )

    assert not any(
        diagnostic.code.endswith("OUTSIDE_SLIDE_EVIDENCE")
        for diagnostic in diagnostics
    )


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
