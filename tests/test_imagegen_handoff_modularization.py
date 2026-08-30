from __future__ import annotations

import importlib
from pathlib import Path
from tempfile import TemporaryDirectory

from cyberppt.script_quality_contract import parse_script_markdown
from scripts.imagegen_pipeline.style_library import (
    resolve_default_style,
    write_project_style_lock,
)


FACADE = "scripts.imagegen_pipeline.imagegen_handoff"
PROMPT_MODULE = "scripts.imagegen_pipeline.handoff.prompt"
DELIVERY_MODULE = "scripts.imagegen_pipeline.handoff.delivery"
CLI_MODULE = "scripts.imagegen_pipeline.handoff.cli"


def _page():
    document = parse_script_markdown(
        """## 第1页：运行底座
- 页面类型：内容页
- 页面标题：运行底座
- 主判断：统一底座支撑稳定运行。
- 上屏文字：

  **01｜数据治理**
  - 质量与授权

  **02｜运行结果**
  - 可追溯
"""
    )
    return document.pages[0]


def test_compatibility_facade_reexports_modular_implementations_directly() -> None:
    facade = importlib.import_module(FACADE)
    prompt = importlib.import_module(PROMPT_MODULE)
    delivery = importlib.import_module(DELIVERY_MODULE)
    cli = importlib.import_module(CLI_MODULE)

    assert facade.build_page_prompt is prompt.build_page_prompt
    assert facade.compile_page_prompt is prompt.compile_page_prompt
    assert facade.render_content_first_prompt is prompt.render_content_first_prompt
    assert facade.write_chapter_handoff is delivery.write_chapter_handoff
    assert facade.main is cli.main


def test_facade_public_surface_is_unique_and_does_not_restore_retired_style10_symbols() -> None:
    facade = importlib.import_module(FACADE)
    exported = tuple(getattr(facade, "__all__", ()))

    assert exported
    assert len(exported) == len(set(exported))
    assert "STYLE10_SEMANTIC_RULE_FIELDS" not in exported
    for required in (
        "build_page_prompt",
        "compile_page_prompt",
        "render_content_first_style_contract",
        "write_chapter_handoff",
        "main",
    ):
        assert required in exported
        assert hasattr(facade, required)


def test_facade_and_modular_prompt_builder_are_behaviorally_identical_for_style09() -> None:
    facade = importlib.import_module(FACADE)
    prompt_module = importlib.import_module(PROMPT_MODULE)
    page = _page()

    with TemporaryDirectory() as directory:
        lock = write_project_style_lock(project=Path(directory), style_id=9)
        via_facade = facade.build_page_prompt(
            page,
            lock,
            page_mission="平台如何稳定支撑业务",
        )
        via_module = prompt_module.build_page_prompt(
            page,
            lock,
            page_mission="平台如何稳定支撑业务",
        )

    assert via_facade == via_module
    assert "2048×1024" in via_facade
    assert "【模板层禁绘｜不上屏】" in via_facade
    assert "pure white background #FFFFFF" in via_facade
    assert "01｜数据治理" in via_facade
    assert "02｜运行结果" in via_facade


def test_content_first_prompt_keeps_current_canvas_text_and_template_contracts() -> None:
    facade = importlib.import_module(FACADE)
    page = _page()

    with TemporaryDirectory() as directory:
        lock = write_project_style_lock(project=Path(directory), style_id=9)
        prompt = facade.build_page_prompt(page, lock)

    assert "输出必须严格为 2048×1024 像素（2:1）" in prompt
    assert "图中所有可读文字只能来自【锁定关键文字】或【完整上屏内容】" in prompt
    assert "不绘制页面标题、副标题、页码、页面序号" in prompt
    assert "### 2. Semantic anchor and composition — hard" in prompt
    assert "【最终视觉执行约束｜最高优先级】" in prompt


def test_compiled_prompt_metadata_uses_current_compiler_and_style09() -> None:
    facade = importlib.import_module(FACADE)
    page = _page()

    with TemporaryDirectory() as directory:
        lock = write_project_style_lock(project=Path(directory), style_id=9)
        compiled = facade.compile_page_prompt(page, lock)

    metadata = compiled.build_metadata()
    assert compiled.prompt
    assert metadata["compiler_version"]
    assert metadata["text_render_mode"]
    assert "pure white background #FFFFFF" in compiled.prompt


def test_legacy_style10_alias_does_not_create_second_facade_authority() -> None:
    style9 = resolve_default_style(style_id=9)
    style10 = resolve_default_style(style_id=10)

    assert style10["id"] == 9
    assert style10["prompt_contract_sha256"] == style9["prompt_contract_sha256"]
    assert style10["legacy_alias_from_style_id"] == 10
