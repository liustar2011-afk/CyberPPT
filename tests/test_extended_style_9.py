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

    assert [style["id"] for style in styles] == list(range(1, 10))
    assert next(style for style in styles if style["id"] == 4) == STYLE_FOUR_CONTRACT
    style_nine = resolve_default_style(style_id=9)
    assert style_nine["slug"] == "ivory_deep_blue_scene"
    assert style_nine["extension_only"] is True
    assert style_nine["name"] == "象牙白 + 深蓝领导汇报"
    assert resolve_default_style(style_name="ivory_deep_blue_scene")["id"] == 9
    assert style_nine["colors"] == STYLE_FOUR_CONTRACT["colors"]
    assert "icon_rule" in style_nine
    assert "people_rule" in style_nine
    assert "Do not use identifiable people to imply a specific event, organization, role assignment, endorsement, or historical fact" in style_nine["people_rule"]
    assert "small-scale anonymous professional figures" in style_nine["people_rule"]
    assert "never use portraits, leaders, name badges, uniforms" in style_nine["people_rule"]
    assert "documentary-style activities" in style_nine["people_rule"]
    assert "professional activity is part of the business meaning" not in style_nine["people_rule"]
    assert "factuality_rule" in style_nine
    assert "organization names, logos, seals, signage" in style_nine["factuality_rule"]
    assert "editable text layer only" in style_nine["factuality_rule"]
    assert "non-evidentiary" in style_nine["factuality_rule"]
    assert "Generic, non-location-specific facilities" in style_nine["factuality_rule"]
    assert "content_visual_rule" in style_nine
    assert "文字逻辑与业务流程是页面主体" in style_nine["content_visual_rule"]
    assert "图像是把已锁定内容空间化、形象化和关系化的表达工具" in style_nine["content_visual_rule"]
    assert "不得生成独立图片区、照片条、照片拼贴" in style_nine["content_visual_rule"]
    assert "不预设或改变页面的内容关系、模块数量、模块顺序或版式骨架" in style_nine["content_visual_rule"]
    assert "leadership briefing" in style_nine["prompt_contract"]
    assert "speech-support" in style_nine["prompt_contract"]
    assert "not a process infographic" in style_nine["prompt_contract"]
    assert "Not a consulting deliverable" in style_nine["prompt_contract"]
    assert "Consulting research" not in style_nine["prompt_contract"]
    assert "Microsoft YaHei" in style_nine["prompt_contract"] or "Source Han Sans" in style_nine["prompt_contract"]
    assert "Prefer editorial simplicity and business clarity" in style_nine["prompt_contract"]
    assert "not a marketing poster or design showcase" in style_nine["prompt_contract"]
    assert "Visual hierarchy and content fit:" in style_nine["prompt_contract"]
    assert "Visual hierarchy should follow the importance of the message" in style_nine["prompt_contract"]
    assert "Do not force every page to have a single hero image" in style_nine["prompt_contract"]
    assert "conclusion, relationship, comparison, business scenario, or supporting evidence" in style_nine["prompt_contract"]
    assert "Do not apply one visual template to all pages" in style_nine["prompt_contract"]
    assert "Image-text fusion:" in style_nine["prompt_contract"]
    assert "must not prescribe or replace page-specific content relationships" in style_nine["prompt_contract"]
    assert "Do not create photo strips, photo galleries, detached photo columns" in style_nine["prompt_contract"]
    assert "Industry scene and imagery:" in style_nine["prompt_contract"]
    assert "translates concrete business meaning into visible real-world context" in style_nine["prompt_contract"]
    assert "Use semantically relevant real-world imagery selectively" in style_nine["prompt_contract"]
    assert "Use only the number of images needed for the page's dynamic content" in style_nine["prompt_contract"]
    assert "power grid operation" in style_nine["prompt_contract"]
    assert "may carry nearby analytical context" in style_nine["prompt_contract"]
    assert "Avoid control-room hero shots" in style_nine["prompt_contract"]
    assert "smart city exhibition style" in style_nine["prompt_contract"]
    assert "control/dispatch rooms" not in style_nine["prompt_contract"]
    assert "Prefer: architecture" not in style_nine["prompt_contract"]
    assert "capability evolution map" not in style_nine["prompt_contract"]
    assert "software-architecture look" in style_nine["prompt_contract"]
    assert "center module + satellite nodes" in style_nine["prompt_contract"]
    assert "Content fidelity and visual logic:" in style_nine["prompt_contract"]
    assert "Do not introduce new visual relationships" in style_nine["prompt_contract"]
    assert "clarify the content, not redefine the content" in style_nine["prompt_contract"]
    assert "explicitly supported by the page content or page-specific visual intent" in style_nine["prompt_contract"]
    assert "Preserve the original meaning and hierarchy" in style_nine["prompt_contract"]
    assert "lifecycle circles with isolated nodes" in style_nine["prompt_contract"]
    assert "numbered step cards" in style_nine["prompt_contract"]
    assert "equal-weight modules" in style_nine["prompt_contract"]
    assert "mechanical process flow templates" in style_nine["prompt_contract"]
    assert "实景彩色插画" in style_nine["prompt_contract"]
    assert "场景辅助" not in style_nine["prompt_contract"]
    assert "photo-inspired editorial industry illustration" in style_nine["prompt_contract"]
    assert "Documentary / editorial photography" in style_nine["prompt_contract"]
    assert "card-per-module" in style_nine["prompt_contract"]
    assert "process infographic" in style_nine["prompt_contract"]
    assert "must not override 【内容锁定】 or [Prompt context] Page-specific visual intent" in style_nine["scope_rule"]
    assert "Do not force every page to have a single hero image" in style_nine["prompt_contract"]
    assert "Do not introduce new visual relationships" in style_nine["prompt_contract"]
    assert "Enhance the message" in style_nine["prompt_contract"]
    assert "#F7F6F0" in style_nine["prompt_contract"]
    assert "#12355B" in style_nine["prompt_contract"]
    assert "dashboard UI" in style_nine["prompt_contract"]
    assert "card wall" in style_nine["prompt_contract"]
    assert "Moderate-to-high information density" in style_nine["density_rule"]
    assert "semantically necessary images" in style_nine["density_rule"]
    assert "领导汇报" in style_nine["scenario"]
    assert "演讲辅助" in style_nine["scenario"]
    assert "语义实景图文融合" in style_nine["scenario"]
    assert "视觉结构" in style_nine["scope_rule"]
    assert "视觉结构" not in style_nine["icon_rule"]
    assert "supporting evidence, not mandatory decoration" not in style_nine["icon_rule"]
    assert "one icon per bullet" in style_nine["icon_rule"]
    assert "One dominant visual narrative" not in style_nine["prompt_contract"]
    assert "One visual center" not in style_nine["prompt_contract"]
    assert "visual anchor" not in style_nine["prompt_contract"]
    assert "key high-end craft" not in style_nine["prompt_contract"]
    assert "Business capability formation is the narrative center" not in style_nine["prompt_contract"]
    assert "real-world industry scenes as the visual foundation" not in style_nine["prompt_contract"]
    combined_contract = "\n".join(
        (
            style_nine["scope_rule"],
            style_nine["prompt_contract"],
            style_nine["icon_rule"],
        )
    )
    assert len(style_nine["prompt_contract"]) < 4200
    assert len(style_nine["scope_rule"]) < 300
    assert len(style_nine["icon_rule"]) < 220
    assert "Images are supporting evidence, not mandatory decoration." not in combined_contract
    assert "Use images only when they improve understanding" not in combined_contract
    assert "宁少勿滥" not in style_nine["density_rule"]
    assert combined_contract.count("Do not introduce new visual relationships") == 1
    assert combined_contract.count("Do not force") == 1
    assert "请以【视觉结构】为构图思考起点" not in style_nine["prompt_contract"]
    assert "主动思考与发挥" not in style_nine["scope_rule"]
    assert "图不是装饰" not in style_nine["prompt_contract"]
    assert "图多字少" not in style_nine["density_rule"]
    assert "文字字面保真" not in style_nine["prompt_contract"]
    assert "secondary point-art" not in style_nine["prompt_contract"]
    assert "never the page hero" not in style_nine["prompt_contract"]
    # Negative overload / design-essay walls removed
    assert "勿为塞入每一句牺牲设计" not in style_nine["prompt_contract"]
    assert "禁止两条极端" not in style_nine["prompt_contract"]
    assert "非对称编辑式报告布局" not in style_nine["prompt_contract"]


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
