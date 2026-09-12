from __future__ import annotations

from cyberppt.stage02_script_adapter import parse_stage02_script
from scripts.imagegen_pipeline.handoff.text import (
    locked_onscreen_text,
    select_conditional_fidelity_text,
    select_image_locked_text,
)


def _page(fidelity_block: str = ""):
    document = parse_stage02_script(
        f"""
## P01 保真选择

- 页面类型：内容页
- 页面标题：保真选择
- 页面使命：说明精确文字边界。
- 核心结论：到2028年覆盖80%的业务场景。

### 完整文字稿

到2028年覆盖80%的业务场景，形成“统一入口”，预计投入100万元。

{fidelity_block}
""".strip()
        + "\n",
        source_mode="script_file",
    )
    return document.pages[0]


def test_normal_prose_numbers_quotes_and_titles_are_not_exact_copy_locks() -> None:
    page = _page()

    # The compatibility helper may still describe legacy authored-copy rules,
    # but the production selector must no longer consume those inferred locks.
    assert locked_onscreen_text(page)
    assert select_image_locked_text(page) == ""
    assert select_conditional_fidelity_text(page) == ""


def test_required_fidelity_is_the_only_new_image_locked_text() -> None:
    page = _page(
        """
### 保真文字

- [required] 2028年
- [required] “统一入口”
- [if_rendered] 80%
""".strip()
    )

    assert select_image_locked_text(page) == "2028年\n“统一入口”"
    assert select_conditional_fidelity_text(page) == "80%"


def test_if_rendered_fidelity_does_not_become_required_bitmap_copy() -> None:
    page = _page(
        """
### 保真文字

- [if_rendered] 100万元
""".strip()
    )

    assert select_image_locked_text(page) == ""
    assert select_conditional_fidelity_text(page) == "100万元"


def test_legacy_image_locked_text_does_not_override_new_fidelity_authority() -> None:
    page = _page(
        """
### 保真文字

- [required] 2028年
""".strip()
    )
    # Simulate a legacy field surviving on a compatibility object.  New
    # production must still take exact-copy authority from fidelity_text only.
    object.__setattr__(page, "image_locked_text", "旧版自动锁字")

    assert select_image_locked_text(page) == "2028年"
