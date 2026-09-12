from __future__ import annotations

from dataclasses import replace

from cyberppt.script_quality_contract import parse_script_markdown
from scripts.imagegen_pipeline.handoff.text import (
    select_conditional_fidelity_text,
    select_image_locked_text,
)


SCRIPT_12 = """## P01 外部内容源

- 页面类型：内容页
- 页面标题：外部内容源
- 页面使命：验证 Stage02 外部稿件保持可改写
- 核心结论：普通正文不自动升级为逐字锁定项。

### 完整文字稿

2028年形成稳定服务能力。
"""


def _external_page():
    page = parse_script_markdown(SCRIPT_12).pages[0]
    return replace(
        page,
        onscreen_text="- 2028年\n- 稳定服务能力",
        full_prose="- 2028年\n- 稳定服务能力",
        onscreen_source="external_content_stage02_source",
        fidelity_text=(),
    )


def test_external_stage02_content_does_not_infer_exact_copy_locks() -> None:
    page = _external_page()

    assert select_image_locked_text(page) == ""
    assert select_conditional_fidelity_text(page) == ""


def test_external_stage02_content_uses_only_explicit_fidelity_literals() -> None:
    page = replace(
        _external_page(),
        fidelity_text=(
            {"text": "2028年", "visibility": "required"},
            {"text": "《服务规范》", "visibility": "if_rendered"},
        ),
    )

    assert select_image_locked_text(page) == "2028年"
    assert select_conditional_fidelity_text(page) == "《服务规范》"
