from __future__ import annotations

from cyberppt.stage02_script_adapter import (
    parse_stage02_script,
    project_stage02_runtime_page,
)
from scripts.imagegen_pipeline.handoff.prompt import compile_page_prompt
from scripts.imagegen_pipeline.handoff.text import (
    render_fidelity_prompt_contract,
    select_image_locked_text,
)
from scripts.imagegen_pipeline.style_library import write_project_style_lock


def _internal_page():
    document = parse_stage02_script(
        """
## P01 保真提示词

- 页面类型：内容页
- 页面标题：保真提示词
- 页面使命：说明普通内容与逐字保真文字的边界。
- 核心结论：到2028年覆盖80%的业务场景。

### 完整文字稿

到2028年覆盖80%的业务场景，形成“统一入口”，预计投入100万元。

### 保真文字

- [required] 2028年
- [required] “统一入口”
- [if_rendered] 100万元
""".strip()
        + "\n",
        source_mode="script_file",
    )
    return document.pages[0]


def test_fidelity_prompt_contract_keeps_required_and_conditional_semantics_distinct() -> None:
    contract = render_fidelity_prompt_contract(_internal_page())

    assert "Required｜必须出现且逐字准确" in contract
    assert "必须在最终图片中可见地出现至少一次" in contract
    assert "- 2028年" in contract
    assert "- “统一入口”" in contract
    assert "If rendered｜可以省略，若出现则逐字准确" in contract
    assert "可以完全不出现" in contract
    assert "不得为了满足本区块而强制添加" in contract
    assert "- 100万元" in contract
    assert "80%" not in contract


def test_content_first_prompt_wires_fidelity_without_locking_normal_copy(tmp_path) -> None:
    page = _internal_page()
    style_lock = write_project_style_lock(project=tmp_path, style_id=4)

    compiled = compile_page_prompt(
        page,
        style_lock,
        prompt_compiler="content-first-v1",
    )

    assert "【页面内容素材｜允许提炼、改写、重组】" in compiled.prompt
    assert "【保真文字｜逐字合同】" in compiled.prompt
    assert "Required｜必须出现且逐字准确" in compiled.prompt
    assert "If rendered｜可以省略，若出现则逐字准确" in compiled.prompt
    assert "关键事实锚点（仅供校验）" not in compiled.prompt
    assert compiled.image_locked_text == "2028年\n“统一入口”"
    assert "100万元" not in compiled.image_locked_text
    assert "80%" not in compiled.image_locked_text
    assert compiled.editable_body_text == page.onscreen_text.strip()


def test_semantic_visual_prompt_retains_required_and_conditional_fidelity(tmp_path) -> None:
    page = _internal_page()
    style_lock = write_project_style_lock(project=tmp_path, style_id=4)

    compiled = compile_page_prompt(
        page,
        style_lock,
        prompt_compiler="content-first-v1",
        text_render_mode="semantic_visual",
    )

    assert "【保真文字｜逐字合同】" in compiled.prompt
    assert "- 2028年" in compiled.prompt
    assert "- 100万元" in compiled.prompt
    assert "可以完全不出现" in compiled.prompt
    assert compiled.image_locked_text == "2028年\n“统一入口”"


def test_external_content_source_never_falls_back_to_legacy_auto_lock() -> None:
    document = parse_stage02_script(
        """
## P01 外部稿

截至2028年，覆盖80%的业务场景并形成统一入口。
""".strip()
        + "\n",
        source_mode="external_script",
    )
    page = project_stage02_runtime_page(
        document.pages[0],
        source_mode="external_script",
    )

    assert page.onscreen_source == "external_content_stage02_source"
    assert select_image_locked_text(page) == ""
    assert render_fidelity_prompt_contract(page) == ""
