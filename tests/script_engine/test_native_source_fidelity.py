from __future__ import annotations

from script_engine.native_source_fidelity import exact_source_text, native_source_fidelity_issues


def _packet(text: str) -> dict:
    return {
        "page_id": "P01",
        "evidence": [
            {
                "foundation_ref": "F1",
                "exact_source_units": [
                    {"unit_id": "SU-001", "text": text},
                ],
            }
        ],
    }


def _final(text: str, *, field: str = "full_copy") -> dict:
    slide = {
        "id": "P01",
        "page_type": "content",
        "title": "来源事实",
        "full_copy": "来源事实。",
        "onscreen": [{"heading": "来源事实"}],
        "source_refs": ["F1"],
    }
    slide[field] = text
    return {"slides": [slide]}


def test_exact_source_text_deduplicates_same_unit_across_evidence() -> None:
    packet = _packet("原始事实。")
    packet["evidence"].append(
        {
            "foundation_ref": "F2",
            "exact_source_units": [
                {"unit_id": "SU-001", "text": "原始事实。"},
                {"unit_id": "SU-002", "text": "第二条事实。"},
            ],
        }
    )

    assert exact_source_text(packet) == "原始事实。\n第二条事实。"


def test_native_source_fidelity_allows_numbers_present_in_exact_source() -> None:
    final = _final("截至2026年，覆盖4.5%的样本。")
    packet = _packet("截至2026年，覆盖4.5%的样本。")

    assert native_source_fidelity_issues(final, {"P01": packet}) == []


def test_native_source_fidelity_blocks_added_number_or_date() -> None:
    final = _final("截至2027年，覆盖5.2%的样本。")
    packet = _packet("截至2026年，覆盖4.5%的样本。")

    issues = native_source_fidelity_issues(final, {"P01": packet})

    assert any("NATIVE_NUMBER_OR_DATE_ADDED" in issue and "2027年" in issue for issue in issues)
    assert any("NATIVE_NUMBER_OR_DATE_ADDED" in issue and "5.2%" in issue for issue in issues)


def test_native_source_fidelity_blocks_dropped_numeric_qualifier() -> None:
    final = _final("平台汇聚30万条记录。")
    packet = _packet("平台汇聚约30万条记录。")

    issues = native_source_fidelity_issues(final, {"P01": packet})

    assert issues == [
        "NATIVE_NUMERIC_QUALIFIER_DROPPED: P01.full_copy: source qualifier '约' for '30万' is missing"
    ]


def test_native_source_fidelity_blocks_dropped_scope_qualifier() -> None:
    final = _final("服务面向高校开放。")
    packet = _packet("服务仅面向高校开放。")

    issues = native_source_fidelity_issues(final, {"P01": packet})

    assert issues == [
        "NATIVE_SCOPE_QUALIFIER_DROPPED: P01.full_copy: source marker '仅' for '面向高校开放' is missing"
    ]


def test_native_source_fidelity_preserves_explicit_scope_marker() -> None:
    final = _final("服务仅面向高校开放。")
    packet = _packet("服务仅面向高校开放。")

    assert native_source_fidelity_issues(final, {"P01": packet}) == []


def test_native_source_fidelity_blocks_removed_exclusion_scope() -> None:
    final = _final("数据集包含用户明细数据。")
    packet = _packet("数据集不含用户明细数据。")

    issues = native_source_fidelity_issues(final, {"P01": packet})

    assert any(
        "NATIVE_SCOPE_QUALIFIER_DROPPED" in issue
        and "'不含'" in issue
        and "用户明细数据" in issue
        for issue in issues
    )


def test_native_source_fidelity_blocks_tentative_to_achieved_status_promotion() -> None:
    final = _final("项目已完成3项工作。")
    packet = _packet("项目计划完成3项工作。")

    issues = native_source_fidelity_issues(final, {"P01": packet})

    assert any("NATIVE_STATUS_PROMOTED" in issue for issue in issues)


def test_native_source_fidelity_blocks_new_obligation_and_claim_strength() -> None:
    final = _final("项目必须全面开展数据治理。")
    packet = _packet("项目开展数据治理。")

    issues = native_source_fidelity_issues(final, {"P01": packet})

    assert "NATIVE_MODALITY_PROMOTED: P01.full_copy: ['必须']" in issues
    assert "NATIVE_CLAIM_STRENGTH_PROMOTED: P01.full_copy: ['全面']" in issues


def test_native_source_fidelity_requires_packet_and_exact_text() -> None:
    final = _final("来源事实。")

    assert native_source_fidelity_issues(final, {}) == [
        "NATIVE_SOURCE_PACKET_MISSING: P01"
    ]
    assert native_source_fidelity_issues(final, {"P01": {"evidence": []}}) == [
        "NATIVE_SOURCE_TEXT_MISSING: P01"
    ]


def test_native_source_fidelity_checks_onscreen_object_item_text() -> None:
    final = {
        "slides": [
            {
                "id": "P01",
                "page_type": "content",
                "title": "来源事实",
                "full_copy": "来源事实。",
                "onscreen": [
                    {
                        "heading": "来源事实",
                        "items": [{"id": "M01-I01", "text": "新增700家主体"}],
                    }
                ],
                "source_refs": ["F1"],
            }
        ]
    }
    packet = _packet("覆盖600家主体。")

    issues = native_source_fidelity_issues(final, {"P01": packet})

    assert any(
        "NATIVE_NUMBER_OR_DATE_ADDED: P01.onscreen[0].items[0].text" in issue
        and "700家" in issue
        for issue in issues
    )
