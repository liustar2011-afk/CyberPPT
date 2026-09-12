from __future__ import annotations

from cyberppt.script_quality.parsing import parse_script_markdown
from script_engine.contracts import (
    check_author_field_contract,
    lint_final_script,
    validate_final_script,
)
from script_engine.fidelity_text_contracts import FIDELITY_TEXT_MAX_ITEMS
from script_engine.render import render_stage02_markdown


def _source_provenance() -> dict:
    return {
        "packet_sha256": "a" * 64,
        "source_refs": ["S001"],
        "unit_ids": ["SU-doc-001"],
    }


def _v12_payload() -> dict:
    return {
        "contract": "cyberppt.final-script",
        "version": "1.2",
        "deck": {
            "title": "保真文字迁移",
            "communication_goal": "验证 Stage 01 与 Stage 02 的文字职责边界",
            "authoring_mode": "faithful",
        },
        "slides": [
            {
                "id": "P01",
                "page_type": "content",
                "title": "职责边界",
                "full_copy": (
                    "截至2028年，项目完成37.5%的阶段任务，并依据"
                    "《国家数据基础设施建设指引》推进建设。普通业务措辞允许下游重组。"
                ),
                "fidelity_text": [
                    {"text": "2028年", "visibility": "required"},
                    {"text": "37.5%", "visibility": "required"},
                    {
                        "text": "《国家数据基础设施建设指引》",
                        "visibility": "if_rendered",
                    },
                ],
                "source_refs": ["S001"],
                "source_provenance": _source_provenance(),
            }
        ],
    }


def _v11_payload() -> dict:
    payload = _v12_payload()
    payload["version"] = "1.1"
    payload["slides"][0].pop("fidelity_text")
    payload["slides"][0]["onscreen"] = [
        {
            "id": "M01",
            "heading": "阶段任务",
            "items": [{"id": "M01-I01", "text": "2028年完成阶段任务"}],
            "provenance": {
                "derivation": "direct",
                "claim_refs": ["S001"],
                "bindings": [
                    {
                        "target": "M01",
                        "source_refs": ["S001"],
                        "relation": "expresses",
                    }
                ],
            },
        }
    ]
    return payload


def test_v12_accepts_full_copy_and_empty_fidelity_without_onscreen() -> None:
    payload = _v12_payload()
    payload["slides"][0]["fidelity_text"] = []
    assert validate_final_script(payload) == []
    assert not any(
        "AUTHOR_ONSCREEN_REQUIRED" in issue
        for issue in check_author_field_contract(payload)
    )


def test_v12_requires_fidelity_text_even_when_empty_is_allowed() -> None:
    payload = _v12_payload()
    del payload["slides"][0]["fidelity_text"]
    issues = validate_final_script(payload)
    assert any("fidelity_text" in issue for issue in issues)


def test_v12_rejects_parallel_authored_onscreen_authority() -> None:
    payload = _v12_payload()
    payload["slides"][0]["onscreen"] = [{"heading": "不应存在"}]
    issues = validate_final_script(payload)
    assert any("onscreen" in issue for issue in issues)


def test_v12_rejects_invalid_fidelity_visibility() -> None:
    payload = _v12_payload()
    payload["slides"][0]["fidelity_text"][0]["visibility"] = "always"
    issues = validate_final_script(payload)
    assert any("visibility" in issue for issue in issues)


def test_v12_capacity_overage_is_not_a_schema_blocker() -> None:
    payload = _v12_payload()
    items = [
        {"text": f"保真项{i}", "visibility": "required"}
        for i in range(FIDELITY_TEXT_MAX_ITEMS + 1)
    ]
    payload["slides"][0]["fidelity_text"] = items
    payload["slides"][0]["full_copy"] += "".join(item["text"] for item in items)
    assert validate_final_script(payload) == []


def test_v11_still_requires_authored_onscreen() -> None:
    payload = _v11_payload()
    del payload["slides"][0]["onscreen"]
    issues = validate_final_script(payload)
    assert any("onscreen" in issue for issue in issues)
    assert any(
        "AUTHOR_ONSCREEN_REQUIRED" in issue
        for issue in check_author_field_contract(payload)
    )


def test_v12_lint_does_not_run_legacy_onscreen_shape_contracts() -> None:
    payload = _v12_payload()
    issues = lint_final_script(payload)
    assert not any("AUTHOR_ONSCREEN_REQUIRED" in issue for issue in issues)
    assert not any("ONSCREEN_" in issue for issue in issues)


def test_v12_markdown_renders_fidelity_without_onscreen_section() -> None:
    markdown = render_stage02_markdown(_v12_payload())
    assert "### 完整文字稿" in markdown
    assert "### 保真文字" in markdown
    assert "- [required] 2028年" in markdown
    assert "- [required] 37.5%" in markdown
    assert "- [if_rendered] 《国家数据基础设施建设指引》" in markdown
    assert "### 上屏文字" not in markdown


def test_v12_empty_fidelity_still_emits_explicit_contract_marker() -> None:
    payload = _v12_payload()
    payload["slides"][0]["fidelity_text"] = []
    markdown = render_stage02_markdown(payload)
    assert "### 保真文字\n\n（无）" in markdown
    parsed = parse_script_markdown(markdown)
    page = parsed.pages[0]
    assert page.fidelity_text == ()
    assert page.onscreen_source == "full_copy_stage02_source"
    assert page.onscreen_text == page.full_prose
    assert page.module_titles == ()


def test_v12_markdown_round_trip_preserves_fidelity_items_and_stage02_source() -> None:
    payload = _v12_payload()
    markdown = render_stage02_markdown(payload)
    parsed = parse_script_markdown(markdown)
    page = parsed.pages[0]
    assert page.fidelity_text == tuple(payload["slides"][0]["fidelity_text"])
    assert page.onscreen_source == "full_copy_stage02_source"
    assert page.onscreen_text == payload["slides"][0]["full_copy"]
    assert page.raw_onscreen_text == payload["slides"][0]["full_copy"]
    assert page.module_titles == ()


def test_v11_render_behavior_is_unchanged() -> None:
    payload = _v11_payload()
    markdown = render_stage02_markdown(payload)
    assert "### 上屏文字" in markdown
    assert "### 保真文字" not in markdown
