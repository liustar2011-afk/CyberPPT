from __future__ import annotations

from script_engine.contracts import check_fidelity_text_contract, lint_final_script
from script_engine.fidelity_text_contracts import (
    FIDELITY_TEXT_MAX_EFFECTIVE_CHARS,
    FIDELITY_TEXT_MAX_ITEMS,
    canonicalize_fidelity_text,
)


def _payload(*, fidelity_text: object = None, include_field: bool = True) -> dict:
    slide = {
        "id": "P01",
        "page_type": "content",
        "title": "测试页",
        "full_copy": "截至2028年，项目完成37.5%的阶段任务，并依据《国家数据基础设施建设指引》推进建设。",
        "onscreen": [{"heading": "阶段进展", "text": "项目持续推进"}],
    }
    if include_field:
        slide["fidelity_text"] = fidelity_text
    return {
        "contract": "cyberppt.final-script",
        "version": "1.1",
        "deck": {
            "title": "测试",
            "communication_goal": "验证保真文字合同",
            "authoring_mode": "faithful",
        },
        "slides": [slide],
    }


def test_fidelity_text_is_additive_during_migration() -> None:
    assert check_fidelity_text_contract(_payload(include_field=False)) == []


def test_fidelity_text_accepts_required_and_if_rendered_literals() -> None:
    payload = _payload(
        fidelity_text=[
            {"text": "2028年", "visibility": "required"},
            {"text": "37.5%", "visibility": "required"},
            {"text": "《国家数据基础设施建设指引》", "visibility": "if_rendered"},
        ]
    )
    assert check_fidelity_text_contract(payload) == []


def test_fidelity_text_requires_canonical_object_entries() -> None:
    payload = _payload(fidelity_text=["2028年"])
    issues = check_fidelity_text_contract(payload)
    assert any(issue.startswith("FIDELITY_TEXT_ITEM_INVALID:") for issue in issues)


def test_fidelity_text_rejects_invalid_visibility_duplicate_and_outside_copy() -> None:
    payload = _payload(
        fidelity_text=[
            {"text": "2028年", "visibility": "always"},
            {"text": "2028年", "visibility": "required"},
            {"text": "不存在的专名", "visibility": "required"},
        ]
    )
    issues = check_fidelity_text_contract(payload)
    assert any(issue.startswith("FIDELITY_TEXT_VISIBILITY_INVALID:") for issue in issues)
    assert any(issue.startswith("FIDELITY_TEXT_DUPLICATE:") for issue in issues)
    assert any(issue.startswith("FIDELITY_TEXT_OUTSIDE_FULL_COPY:") for issue in issues)


def test_fidelity_text_capacity_limits_are_explicit() -> None:
    items = [
        {"text": f"值{i}", "visibility": "required"}
        for i in range(FIDELITY_TEXT_MAX_ITEMS + 1)
    ]
    payload = _payload(fidelity_text=items)
    payload["slides"][0]["full_copy"] += "".join(item["text"] for item in items)
    issues = check_fidelity_text_contract(payload)
    assert any(issue.startswith("FIDELITY_TEXT_ITEM_LIMIT:") for issue in issues)

    long_text = "保" * (FIDELITY_TEXT_MAX_EFFECTIVE_CHARS + 1)
    payload = _payload(fidelity_text=[{"text": long_text, "visibility": "required"}])
    payload["slides"][0]["full_copy"] += long_text
    issues = check_fidelity_text_contract(payload)
    assert any(issue.startswith("FIDELITY_TEXT_CHAR_LIMIT:") for issue in issues)


def test_canonicalize_fidelity_text_deduplicates_without_inventing_visibility() -> None:
    value = [
        {"text": " 2028年 ", "visibility": "required"},
        {"text": "2028年", "visibility": "required"},
        {"text": "37.5%", "visibility": "if_rendered"},
        {"text": "无可见性"},
        "字符串旧格式",
    ]
    assert canonicalize_fidelity_text(value) == [
        {"text": "2028年", "visibility": "required"},
        {"text": "37.5%", "visibility": "if_rendered"},
    ]


def test_fidelity_text_contract_is_part_of_final_script_lint() -> None:
    payload = _payload(
        fidelity_text=[{"text": "不存在的专名", "visibility": "required"}]
    )
    issues = lint_final_script(payload)
    assert any(issue.startswith("FIDELITY_TEXT_OUTSIDE_FULL_COPY:") for issue in issues)
