from __future__ import annotations

from dataclasses import replace
from hashlib import sha256
from pathlib import Path
from tempfile import TemporaryDirectory

from cyberppt.script_quality_contract import parse_script_markdown
from scripts.imagegen_pipeline.imagegen_handoff import compile_page_prompt
from scripts.imagegen_pipeline.style_library import write_project_style_lock


SCRIPT_12 = """## P01 保真文字送图合同

- 页面类型：内容页
- 页面标题：保真文字送图合同
- 页面使命：说明普通正文与少量保真字符串的送图边界
- 核心结论：普通内容允许改写，保真字符串按可见性规则精确控制。

### 完整文字稿

预计到2028年形成稳定服务能力。普通业务说明允许模型根据版面进行提炼、改写、合并和重组，并保留原有事实边界。《国家数据基础设施建设指引》可在版面需要时作为正式名称出现。

### 保真文字

- [required] 2028年
- [if_rendered] 《国家数据基础设施建设指引》
"""


def _page():
    return parse_script_markdown(SCRIPT_12).pages[0]


def _compile(page=None, *, text_render_mode: str = "full_image"):
    page = page or _page()
    directory = TemporaryDirectory()
    lock = write_project_style_lock(project=Path(directory.name), style_id=9)
    compiled = compile_page_prompt(page, lock, text_render_mode=text_render_mode)
    return directory, compiled


def test_final_script_12_projects_full_copy_as_runtime_content() -> None:
    page = _page()

    assert page.onscreen_source == "full_copy_stage02_source"
    assert page.onscreen_text == page.full_prose
    assert page.fidelity_text == (
        {"text": "2028年", "visibility": "required"},
        {"text": "《国家数据基础设施建设指引》", "visibility": "if_rendered"},
    )


def test_final_script_12_uses_one_content_authority_in_prompt() -> None:
    directory, compiled = _compile()
    try:
        prompt = compiled.prompt
        unique_copy = "预计到2028年形成稳定服务能力。普通业务说明允许模型根据版面进行提炼、改写、合并和重组"

        assert "【页面内容素材｜允许提炼、改写、重组】" in prompt
        assert "【完整文字稿（不上屏）】" not in prompt
        assert prompt.count(unique_copy) == 1
    finally:
        directory.cleanup()


def test_content_first_prompt_separates_required_and_if_rendered_fidelity() -> None:
    directory, compiled = _compile()
    try:
        prompt = compiled.prompt
        required_header = "【required｜必须出现且逐字准确】"
        conditional_header = "【if_rendered｜可不显示；若显示必须逐字准确】"

        assert "【保真文字合同｜控制指令，不上屏】" in prompt
        assert required_header in prompt
        assert conditional_header in prompt

        required_section = prompt.split(required_header, 1)[1].split(conditional_header, 1)[0]
        conditional_section = prompt.split(conditional_header, 1)[1]
        assert "2028年" in required_section
        assert "《国家数据基础设施建设指引》" not in required_section
        assert "《国家数据基础设施建设指引》" in conditional_section
        assert "不得因为字符串列入 if_rendered 而强制其出现" in conditional_section

        metadata = compiled.build_metadata()
        assert metadata["image_locked_text"] == "2028年"
        assert "text.fidelity_required_exact" in metadata["injected_rule_ids"]
        assert "text.fidelity_if_rendered_exact" in metadata["injected_rule_ids"]
        assert "普通业务说明允许模型根据版面进行提炼" not in metadata["image_locked_text"]
    finally:
        directory.cleanup()


def test_if_rendered_only_never_becomes_required() -> None:
    page = replace(
        _page(),
        fidelity_text=(
            {"text": "《国家数据基础设施建设指引》", "visibility": "if_rendered"},
        ),
    )
    directory, compiled = _compile(page)
    try:
        prompt = compiled.prompt
        assert "【required｜必须出现且逐字准确】" not in prompt
        assert "【if_rendered｜可不显示；若显示必须逐字准确】" in prompt
        assert "《国家数据基础设施建设指引》" in prompt
        assert "image_locked_text" not in compiled.build_metadata()
        assert "text.fidelity_required_exact" not in compiled.injected_rule_ids
        assert "text.fidelity_if_rendered_exact" in compiled.injected_rule_ids
    finally:
        directory.cleanup()


def test_fidelity_visibility_changes_prompt_hash() -> None:
    required_page = replace(
        _page(),
        fidelity_text=({"text": "2028年", "visibility": "required"},),
    )
    conditional_page = replace(
        _page(),
        fidelity_text=({"text": "2028年", "visibility": "if_rendered"},),
    )
    required_directory, required = _compile(required_page)
    conditional_directory, conditional = _compile(conditional_page)
    try:
        assert required.prompt != conditional.prompt
        assert sha256(required.prompt.encode("utf-8")).hexdigest() != sha256(
            conditional.prompt.encode("utf-8")
        ).hexdigest()
    finally:
        required_directory.cleanup()
        conditional_directory.cleanup()


def test_semantic_visual_keeps_same_fidelity_semantics() -> None:
    directory, compiled = _compile(text_render_mode="semantic_visual")
    try:
        prompt = compiled.prompt
        assert "【保真文字合同｜控制指令，不上屏】" in prompt
        assert "【required｜必须出现且逐字准确】" in prompt
        assert "【if_rendered｜可不显示；若显示必须逐字准确】" in prompt
        assert "关键事实锚点（仅供校验）：2028年" not in prompt
        assert "【完整文字稿（不上屏）】" not in prompt
    finally:
        directory.cleanup()
