from __future__ import annotations

import json
from pathlib import Path
from tempfile import TemporaryDirectory

from cyberppt.cli import build_parser
from scripts.dual_image_overlay.cyberppt_pair_manifest import main as pair_manifest_main
from scripts.dual_image_overlay.style_library import (
    default_style_choices,
    load_style_library,
    resolve_default_style,
    write_project_style_lock,
)


STYLE_FOUR_CONTRACT = {
    "id": 4,
    "slug": "ivory_deep_blue",
    "name": "象牙白 + 深蓝强调",
    "colors": {
        "background": "#F7F6F0",
        "title": "#101820",
        "body": "#303030",
        "secondary": "#6F7275",
        "divider": "#C9CDD1",
        "accent": "#12355B",
    },
    "scenario": "科技、SaaS、B2B、企业数字化、AI Agent 报告",
    "sample": "assets/palette-samples/palette-04.png",
    "scope_rule": (
        "本风格只约束色彩、材质、线条、图标克制度和视觉语气；其中提到的紧凑矩阵、右侧栏、"
        "编号 chips、流程轴、SO WHAT 条等仅为可选视觉语言，不得覆盖原脚本的页面定位、版式草图、"
        "组件数量、箭头关系和框内文字。"
    ),
    "prompt_contract": (
        "视觉风格使用象牙白 + 深蓝强调：背景 #F7F6F0，标题 #101820，正文 #303030，"
        "次级文字 #6F7275，线条 #C9CDD1，强调色 #12355B。适合科技、SaaS、B2B、企业数字化、"
        "AI Agent 报告；采用正式内部汇报结构、深蓝页内强调、紧凑矩阵、细线分隔、右侧栏、"
        "编号 chips 和底部 SO WHAT 条。"
    ),
    "density_rule": (
        "保持高密度企业数字化汇报页；在不改变原脚本结构的前提下，可使用紧凑矩阵、右侧栏、"
        "编号 chips、流程轴和底部 SO WHAT 条。"
    ),
}


def test_style_nine_is_explicit_extension_and_style_four_is_unchanged() -> None:
    styles = load_style_library()["styles"]

    assert [style["id"] for style in styles[:9]] == list(range(1, 10))
    assert len(styles) >= 9
    assert next(style for style in styles if style["id"] == 4) == STYLE_FOUR_CONTRACT
    style_nine = resolve_default_style(style_id=9)
    assert style_nine["slug"] == "ivory_deep_blue_scene"
    assert style_nine["extension_only"] is True
    assert style_nine["name"] == "象牙白 + 深蓝领导汇报"
    assert resolve_default_style(style_name="ivory_deep_blue_scene")["id"] == 9
    assert style_nine["colors"] == STYLE_FOUR_CONTRACT["colors"]
    assert "先保证锁定上屏文字完整、舒展、清晰" in style_nine["content_visual_rule"]
    assert "再区分主体、支撑、输入、输出" in style_nine["content_visual_rule"]
    assert "使用跨页面展开的图形形态、色带、路径、箭头" in style_nine["content_visual_rule"]
    assert "实景、近实景和物件型语义图只作少量局部点缀" in style_nine["content_visual_rule"]
    assert "不得逐项配图、形成照片栏或取代整页图形主线" in style_nine["content_visual_rule"]
    assert "locked on-screen text faithfully in the main composition" in style_nine["semantic_image_text_rule"]
    assert "may use a small amount of clear Chinese labels" in style_nine["semantic_image_text_rule"]
    assert "dense pseudo-Chinese" in style_nine["semantic_image_text_rule"]
    assert "生成式图形构图负责组织页面主线" in style_nine["scope_rule"]
    assert "锁定文字嵌入稳定承载面" in style_nine["scope_rule"]
    assert "文字是页面主体" not in style_nine["scope_rule"]
    assert "少量实景、近实景或物件型语义图仅作点缀" in style_nine["scope_rule"]
    assert "Do not show frontal faces" in style_nine["people_rule"]
    assert "three-quarter frontal faces" in style_nine["people_rule"]
    assert "People must never become the visual center" in style_nine["people_rule"]
    assert "象牙白 + 深蓝领导汇报" in style_nine["prompt_contract"]
    assert "逐项配图" not in style_nine["prompt_contract"]
    assert "#F7F6F0" in style_nine["prompt_contract"]
    assert "#12355B" in style_nine["prompt_contract"]
    assert "图标不是默认视觉载体" in style_nine["icon_rule"]
    assert "不得将抽象名词逐项转换成图标" in style_nine["icon_rule"]
    assert "不得使用“一项内容对应一个图标”的重复模式" in style_nine["icon_rule"]
    assert "生成构图时优先使用具有设计感的图形形态" in style_nine["icon_rule"]
    assert "政企内部汇报所需的信息密度" in style_nine["density_rule"]
    assert "避免依赖重复图标" in style_nine["density_rule"]
    assert "领导汇报" in style_nine["scenario"]
    assert "生成式图形构图主导，实景语义图点缀" in style_nine["scenario"]
    assert len(style_nine["prompt_contract"]) < 600
    assert len(style_nine["imagegen_signature"]) == 3
    assert "禁止霓虹蓝" in style_nine["imagegen_signature"][0]
    assert "由本页内容关系决定的清晰阅读主线" in style_nine["imagegen_signature"][1]
    assert "不得预设中央主体、等宽分栏、卡片阵列或其他固定版式" in style_nine["imagegen_signature"][1]
    assert "不得为了追求跨页差异而强制改变构图" in style_nine["imagegen_signature"][2]
    assert "不得使用夸张三维装置" in style_nine["imagegen_signature"][2]


def test_default_style_choices_still_show_only_original_eight() -> None:
    choices = default_style_choices()

    assert choices.count("\n") == 7
    assert "8. 冷白灰 + 深紫" in choices
    assert "9." not in choices


def test_style_nine_lock_records_extension_selection() -> None:
    with TemporaryDirectory() as directory:
        lock = write_project_style_lock(project=Path(directory), style_id=9)
        payload = json.loads(lock.read_text(encoding="utf-8"))

    assert payload["style"]["id"] == 9
    assert payload["style"]["name"] == "象牙白 + 深蓝领导汇报"
    assert payload["policy"]["selected_from_default_8"] is False
    assert payload["policy"]["selected_from_extension"] is True


def test_final_script_pages_cli_accepts_explicit_style_nine() -> None:
    args = build_parser().parse_args(
        [
            "final-script-pages",
            "project",
            "--script",
            "script.md",
            "--pages",
            "1",
            "--style-id",
            "9",
        ]
    )

    assert args.style_id == 9


def test_pair_manifest_accepts_explicit_style_nine() -> None:
    with TemporaryDirectory() as directory:
        root = Path(directory)
        script = root / "script.md"
        output = root / "output"
        script.write_text("## 第1页：扩展风格\n组件A：业务内容\n", encoding="utf-8")

        code = pair_manifest_main(
            [
                "--script",
                str(script),
                "--pages",
                "1",
                "--output-dir",
                str(output),
                "--project-path",
                str(root / "project"),
                "--style-id",
                "9",
            ]
        )

    assert code == 0
