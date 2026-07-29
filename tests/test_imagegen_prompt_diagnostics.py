from __future__ import annotations

import json
from pathlib import Path
from tempfile import TemporaryDirectory

from scripts.dual_image_overlay.prompt_diagnostics import (
    PagePromptDiagnostics,
    analyze_generated_text_fidelity,
    analyze_prompt,
    compare_page_diagnostics,
    write_batch_diagnostics,
    write_compiler_comparison,
    write_generated_text_fidelity,
)


PROMPT = """【页面编码】P18｜测试页
[Mandatory composition guidance] Apply before text.
- Recommended composition: Use one layered field.

【内容锁定】
- 上屏文字
- **治理层｜质量与授权**
- 2025年完成率 95%。

【构图指令】
Do not invent section labels; only render 上屏文字 modules.
Do not invent section labels; only render 上屏文字 modules.
Factual numbers and labels must be verified and remain editable.
Auxiliary semantic imagery may use a small amount of clear Chinese labels.
Avoid a detached full-height text column or text rail.
Treat text as in-composition panels, not a detached left/right column.
"""

CONTENT_FIRST_PROMPT = """【页面任务｜仅供理解，不上屏】
解释为什么先做试点

【核心判断｜仅供理解】
先验证再推广

【页面逻辑｜不上屏】
主导关系：阶段递进。

【锁定上屏文字】
先验证再推广

【完整页面内容｜用于视觉叙事】
试点验证通过后再推广

【结论句要求｜不上屏】
第一段是正文结论句。

【内容与视觉要求｜不上屏】
不得捏造事实。

【输出与风格｜不上屏】
象牙白与深蓝。
"""


def test_analyze_prompt_reports_metrics_duplicates_and_known_conflicts() -> None:
    metrics = analyze_prompt(
        PROMPT,
        onscreen_text="**治理层｜质量与授权**\n2025年完成率 95%。",
    )

    assert metrics.total_chars > 0
    assert metrics.page_content_chars > 0
    assert metrics.global_rule_chars > 0
    assert 0 < metrics.page_specific_ratio < 1
    assert metrics.onscreen_chars > 0
    assert metrics.exact_number_count == 2
    assert metrics.duplicate_rules == (
        "Do not invent section labels; only render 上屏文字 modules.",
        "semantic:detached_text_zone",
    )
    assert metrics.conflicts == (
        "editable_text_in_bitmap",
        "extra_auxiliary_text_vs_locked_text",
    )


def test_analyze_prompt_is_read_only() -> None:
    original = PROMPT
    analyze_prompt(PROMPT, onscreen_text="正文")
    assert PROMPT == original


def test_analyze_prompt_measures_content_first_page_sections() -> None:
    metrics = analyze_prompt(
        CONTENT_FIRST_PROMPT,
        onscreen_text="先验证再推广",
    )

    assert metrics.page_content_chars > 0
    assert metrics.global_rule_chars > 0
    assert 0 < metrics.page_specific_ratio < 1


def test_generated_text_fidelity_requires_phrases_numbers_and_85_percent() -> None:
    locked = """供需研判转向多维综合判断
**关键变化**
- 2025年全社会用电量同比增长5.0%
**综合判断**
- 结构、区域、时段和市场共同作用
"""
    passed = analyze_generated_text_fidelity(locked, locked)
    failed = analyze_generated_text_fidelity(
        locked,
        "供需研判转向综合判断\n关键变化\n2025年全社会用电量增长",
    )

    assert passed.passed is True
    assert passed.character_retention_ratio == 1.0
    assert passed.text_coverage_ratio == 1.0
    assert failed.passed is False
    assert "generated_text_character_retention_low" in failed.issue_codes
    assert "generated_text_required_phrase_missing" in failed.issue_codes
    assert "generated_text_exact_number_missing" in failed.issue_codes


def test_generated_text_fidelity_writer_requests_one_no_reference_retry() -> None:
    with TemporaryDirectory() as directory:
        path = write_generated_text_fidelity(
            Path(directory) / "fidelity.json",
            page_id="p05",
            locked_text="结论\n**模块**\n2025年完成率95%",
            ocr_text="结论",
        )
        payload = json.loads(path.read_text(encoding="utf-8"))

    assert payload["schema"] == "cyberppt.imagegen_text_fidelity.v1"
    assert payload["result"]["passed"] is False
    assert (
        payload["next_action"]
        == "retry_once_with_same_prompt_and_stronger_text_preservation_no_reference_image"
    )


def test_write_batch_diagnostics_uses_warning_only_schema() -> None:
    metrics = analyze_prompt(PROMPT, onscreen_text="2025年完成率 95%。")
    page = PagePromptDiagnostics(page_id="p18", title="测试页", metrics=metrics)

    with TemporaryDirectory() as directory:
        path = write_batch_diagnostics(
            Path(directory) / "diagnostics.json",
            [page],
            batch_name="test-batch",
        )
        payload = json.loads(path.read_text(encoding="utf-8"))

    assert payload["schema"] == "cyberppt.imagegen_prompt_diagnostics.v2"
    assert payload["mode"] == "warning_only"
    assert payload["summary"]["page_count"] == 1
    assert payload["summary"]["pages_with_conflicts"] == 1
    assert payload["pages"][0]["page_id"] == "p18"
    assert payload["pages"][0]["conflict_count"] == 2


def test_compare_compilers_reports_metric_deltas() -> None:
    legacy = PagePromptDiagnostics(
        page_id="p18",
        title="测试页",
        metrics=analyze_prompt(PROMPT, onscreen_text="2025年完成率 95%。"),
        build_metadata={"compiler_version": "legacy"},
    )
    candidate_prompt = PROMPT.replace(" and remain editable", "").replace(
        "Auxiliary semantic imagery may use a small amount of clear Chinese labels.",
        "Auxiliary imagery must remain text-free.",
    )
    candidate = PagePromptDiagnostics(
        page_id="p18",
        title="测试页",
        metrics=analyze_prompt(
            candidate_prompt,
            onscreen_text="2025年完成率 95%。",
        ),
        build_metadata={"compiler_version": "creative-brief-v1"},
    )

    result = compare_page_diagnostics(legacy, candidate)
    assert result["delta"]["conflict_count"] < 0
    assert result["delta"]["locked_text_preserved"] is True
    assert result["delta"]["exact_facts_preserved"] is True

    with TemporaryDirectory() as directory:
        path = write_compiler_comparison(
            Path(directory) / "comparison.json",
            [(legacy, candidate)],
            batch_name="test-batch",
        )
        payload = json.loads(path.read_text(encoding="utf-8"))
    assert payload["summary"]["page_count"] == 1
    assert payload["pages"][0]["candidate"]["build_metadata"] == {
        "compiler_version": "creative-brief-v1"
    }
