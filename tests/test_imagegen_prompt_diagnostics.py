from __future__ import annotations

import json
from pathlib import Path
from tempfile import TemporaryDirectory

from scripts.dual_image_overlay.prompt_diagnostics import (
    PagePromptDiagnostics,
    analyze_prompt,
    write_batch_diagnostics,
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

    assert payload["schema"] == "cyberppt.imagegen_prompt_diagnostics.v1"
    assert payload["mode"] == "warning_only"
    assert payload["summary"]["page_count"] == 1
    assert payload["summary"]["pages_with_conflicts"] == 1
    assert payload["pages"][0]["page_id"] == "p18"
    assert payload["pages"][0]["conflict_count"] == 2
