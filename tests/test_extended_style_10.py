from __future__ import annotations

import json
from pathlib import Path
from tempfile import TemporaryDirectory

from cyberppt.cli import build_parser
from scripts.imagegen_pipeline.page_manifest import main as pair_manifest_main
from scripts.imagegen_pipeline.deliverable_prompt import (
    PageBlock,
    render_prompt,
    style_contract,
    uses_compact_style_contract,
)
from scripts.imagegen_pipeline.imagegen_handoff import compile_page_prompt
from scripts.imagegen_pipeline.style_library import (
    default_style_choices,
    load_style_library,
    resolve_default_style,
    write_project_style_lock,
)


ROOT = Path(__file__).resolve().parents[1]


def test_style_ten_is_style_nine_rule_replacement_explicit_extension() -> None:
    library = load_style_library()
    styles = library["styles"]
    assert [style["id"] for style in styles] == list(range(1, 11))
    assert library["default_style_id"] == 10

    assert resolve_default_style()["id"] == 10
    style_ten = resolve_default_style(style_id=10)
    assert style_ten["slug"] == "light_tech_business_dense"
    assert style_ten["extension_only"] is True
    assert resolve_default_style(style_name=style_ten["slug"])["id"] == 10
    assert resolve_default_style(style_name="ivory_deep_blue_semantic_scene")["id"] == 10
    # Style 10 is now a byte-identical copy of Style 09's rules (including
    # palette) under its own numbered slot -- see
    # references/visual-system.md's "扩展风格10" section.
    assert style_ten["colors"]["background"] == "#FFFFFF"
    assert style_ten["colors"]["accent"] == "#12355B"
    assert "高级编辑式气质" in style_ten["scope_rule"]
    assert "executive briefing" in style_ten["prompt_contract"]
    assert "Keep connection lines absent by default" in style_ten["prompt_contract"]
    assert "连线：默认不使用连接线" in style_ten["prompt_contract"]
    assert "Positive construction grammar" not in style_ten["prompt_contract"]
    assert "style_prompt_v2" not in style_ten


def test_style_ten_contract_reaches_imagegen_prompt() -> None:
    with TemporaryDirectory() as directory:
        lock = write_project_style_lock(project=Path(directory), style_id=10)
        contract = style_contract(lock)
        payload = json.loads(lock.read_text(encoding="utf-8"))

    assert payload["style"]["id"] == 10
    assert "executive briefing" in contract
    assert "Keep all locked Chinese text complete, unchanged and readable" in contract
    assert "Do not use identifiable people" not in contract


def test_style_ten_keeps_page_composition_guidance_and_full_contract() -> None:
    with TemporaryDirectory() as directory:
        lock = write_project_style_lock(project=Path(directory), style_id=10)
        prompt = render_prompt(
            PageBlock(page_number=1, title="测试", text="锁定正文"),
            style_lock_path=lock,
            composition_guidance="主关系：多路能力汇聚为一个服务中枢。",
        )
        compact = uses_compact_style_contract(lock)

    assert compact is False
    assert "主关系：多路能力汇聚为一个服务中枢。" in prompt
    assert "Keep all locked Chinese text complete, unchanged and readable" in prompt
    assert "one continuous" in prompt
    assert prompt.count("【最终视觉执行约束｜最高优先级】") == 1
    terminal_lock = prompt.split("【最终视觉执行约束｜最高优先级】", 1)[1]
    assert terminal_lock.count("Keep connection lines absent by default") == 1
    assert "purposeful connectors" not in prompt


def test_style_ten_is_not_added_to_default_eight() -> None:
    choices = default_style_choices()
    assert choices.count("\n") == 7
    assert "9." not in choices
    assert "10." not in choices


def test_final_script_pages_cli_accepts_style_ten() -> None:
    args = build_parser().parse_args(
        [
            "final-script-pages",
            "project",
            "--script",
            "script.md",
            "--pages",
            "1",
            "--style-id",
            "10",
        ]
    )
    assert args.style_id == 10


def test_pair_manifest_accepts_style_ten() -> None:
    with TemporaryDirectory() as directory:
        root = Path(directory)
        script = root / "script.md"
        script.write_text("## 第1页：双层风格\n组件A：业务内容\n", encoding="utf-8")
        code = pair_manifest_main(
            [
                "--script",
                str(script),
                "--pages",
                "1",
                "--output-dir",
                str(root / "output"),
                "--project-path",
                str(root / "project"),
                "--style-id",
                "10",
            ]
        )
    assert code == 0


def test_style_ten_sample_and_reference_exist() -> None:
    assert (ROOT / "assets" / "palette-samples" / "palette-10.png").exists()
    reference = (ROOT / "references" / "visual-system.md").read_text(encoding="utf-8")
    assert "扩展风格10：纯白 + 深蓝领导汇报（与风格9相同，仅编号不同）" in reference
    style10_start = reference.index("## 扩展风格10：")
    style10_section = reference[style10_start:]
    assert "### 1. Style identity and semantic principle — hard" in style10_section
    assert "### 3. Content fidelity and presentation expression — hard" in style10_section
    assert "### 4. Reusable composition grammars" in style10_section


def test_style_ten_defaults_to_full_image_and_supports_explicit_semantic_visual() -> None:
    from cyberppt.script_quality_contract import parse_script_markdown

    script = ROOT / "projects" / "power-industry-data-services-operation-20260802" / "workbench" / "scripts" / "final" / "script-final.md"
    if not script.is_file():
        return
    page = next(page for page in parse_script_markdown(script.read_text(encoding="utf-8")).pages if page.page_id == "p10")
    with TemporaryDirectory() as directory:
        lock = write_project_style_lock(project=Path(directory), style_id=10)
        semantic = compile_page_prompt(page, lock)
        full = compile_page_prompt(page, lock, text_render_mode="full_image")
        semantic_visual = compile_page_prompt(page, lock, text_render_mode="semantic_visual")

    assert semantic.build_metadata()["text_render_mode"] == "full_image"
    assert "【完整上屏内容】" in semantic.prompt
    assert semantic_visual.build_metadata()["text_render_mode"] == "semantic_visual"
    assert "【完整上屏内容】" not in semantic_visual.prompt
    assert "数据资源" in semantic_visual.prompt
    assert full.build_metadata()["text_render_mode"] == "full_image"
    assert "【完整上屏内容】" in full.prompt
    assert page.module_titles[0] in full.prompt
    assert "平台负责连接" in full.prompt
