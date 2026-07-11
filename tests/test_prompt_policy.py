from __future__ import annotations

from pathlib import Path

from scripts.dual_image_overlay.deliverable_prompt import parse_page_blocks, visible_deliverable_lines
from scripts.dual_image_overlay.prompt_policy import (
    DEFAULT_PROMPT_POLICY,
    classify_forbidden_text,
    validate_visible_text,
)


def test_processing_policy_classifies_process_review_placeholder_and_metadata_text() -> None:
    assert "process_instruction" in classify_forbidden_text("本页说明：请将内容放入左侧")
    assert "review_note" in classify_forbidden_text("待核对")
    assert "placeholder" in classify_forbidden_text("示意图，占位")
    assert "metadata" in classify_forbidden_text("target_language=zh-CN")
    assert classify_forbidden_text("全国用电量同比增长5.0%") == ()


def test_processing_policy_exposes_non_visible_control_contract() -> None:
    assert DEFAULT_PROMPT_POLICY.visible_text_source == "content_lock"
    assert DEFAULT_PROMPT_POLICY.required_sections == (
        "【页面类型】",
        "【内容锁定】",
        "【构图指令】",
        "【结构密度】",
    )


def test_visible_content_drops_process_instruction_but_keeps_business_content(tmp_path: Path) -> None:
    script = tmp_path / "script.md"
    script.write_text(
        "## 第1页：测试\n"
        "本页说明：仅用于构图\n"
        "真实业务内容\n"
        "全国用电量同比增长5.0%\n",
        encoding="utf-8",
    )

    page = parse_page_blocks(script)[1]

    assert visible_deliverable_lines(page) == ["真实业务内容", "全国用电量同比增长5.0%"]


def test_validate_visible_text_returns_classified_violations() -> None:
    violations = validate_visible_text(["资源保障", "生成要求：请补充一个流程图", "待补充"])

    assert [item["class"] for item in violations] == ["process_instruction", "placeholder"]
    assert violations[0]["text"] == "生成要求：请补充一个流程图"
