from __future__ import annotations

import json
from pathlib import Path
from tempfile import TemporaryDirectory

from cyberppt.cli import build_parser
from scripts.dual_image_overlay.cyberppt_pair_manifest import main as pair_manifest_main
from scripts.dual_image_overlay.deliverable_prompt import (
    PageBlock,
    _style09_page_semantic_tags,
    enforce_style09_terminal_lock,
)
from scripts.dual_image_overlay.imagegen_handoff import render_content_first_style_contract
from scripts.dual_image_overlay.style_library import (
    default_style_choices,
    load_style_lock,
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
    style_four = next(style for style in styles if style["id"] == 4)
    assert style_four["id"] == STYLE_FOUR_CONTRACT["id"]
    assert style_four["slug"] == STYLE_FOUR_CONTRACT["slug"]
    assert style_four["colors"] == STYLE_FOUR_CONTRACT["colors"]
    style_nine = resolve_default_style(style_id=9)
    assert style_nine["slug"] == "ivory_deep_blue_scene"
    assert style_nine["extension_only"] is True
    assert style_nine["name"] == "象牙白 + 深蓝领导汇报"
    assert resolve_default_style(style_name="ivory_deep_blue_scene")["id"] == 9
    assert style_nine["colors"] == STYLE_FOUR_CONTRACT["colors"]
    assert "先保证锁定上屏文字完整、舒展、清晰" in style_nine["content_visual_rule"]
    assert "再区分主体、支撑、输入、输出" in style_nine["content_visual_rule"]
    assert "使用跨页面展开的图形形态、色带、路径、箭头" not in style_nine["content_visual_rule"]
    assert "实景、近实景和物件型语义图只作少量局部点缀" not in style_nine["content_visual_rule"]
    assert "不得逐项配图、形成照片栏或取代整页图形主线" not in style_nine["content_visual_rule"]
    assert "locked on-screen text faithfully in the main composition" in style_nine["semantic_image_text_rule"]
    assert "may use a small amount of clear Chinese labels" in style_nine["semantic_image_text_rule"]
    assert "dense pseudo-Chinese" in style_nine["semantic_image_text_rule"]
    assert "生成式图形构图负责组织页面主线" not in style_nine["scope_rule"]
    assert "锁定文字嵌入稳定承载面" not in style_nine["scope_rule"]
    assert "文字是页面主体" not in style_nine["scope_rule"]
    assert "少量实景、近实景或物件型语义图仅作点缀" not in style_nine["scope_rule"]
    assert style_nine["people_rule"] == "默认不出现人物；禁止正脸、围桌会议、多人讨论及摆拍办公场景。"
    assert "one integrated composition" in style_nine["prompt_contract"]
    assert "50/50" in style_nine["prompt_contract"]
    assert "1/4" in style_nine["prompt_contract"]
    assert "speech-support" in style_nine["prompt_contract"]
    assert "#F7F6F0" in style_nine["prompt_contract"]
    assert "#12355B" in style_nine["prompt_contract"]
    assert "Industry scene anchor" not in style_nine["prompt_contract"]
    assert "逐项配图" not in style_nine["prompt_contract"]
    assert "线条：主关系用细、实、方向一致的深蓝线" in style_nine["component_rule"]
    assert "禁止宽箭头带" in style_nine["component_rule"]
    assert "低矮哑光正视微立体" in style_nine["component_rule"]
    assert "icon_rule" not in style_nine
    assert "政企领导汇报所需的信息密度" in style_nine["density_rule"]
    assert "领导汇报" in style_nine["scenario"]
    assert 600 < len(style_nine["prompt_contract"]) < 4000
    assert style_nine["imagegen_signature"] == []
    assert "节奏与媒介" not in style_nine["prompt_contract"]


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
    assert "### 核心视觉语法" in payload["style"]["prompt_contract"]
    assert "图标默认数量为零" in payload["style"]["prompt_contract"]
    assert "宽箭头带" in payload["style"]["prompt_contract"]
    assert "页面先读到一个业务锚点，再读到文字关系" in payload["style"]["prompt_contract"]
    assert payload["style"]["prompt_contract"].count("文字型视觉主线") == 1
    assert "不得新增非锁定标签" in payload["style"]["prompt_contract"]
    assert payload["style"]["prompt_contract"].count("**图文融合**") == 1
    assert "禁止图形区与文字区各自完整重复同一组内容" in payload["style"]["prompt_contract"]
    assert "把文字列表伪装成关系图" in payload["style"]["prompt_contract"]
    assert "2—5个文字组共享同一视觉场" in payload["style"]["prompt_contract"]
    assert "禁止重复表达同一语义" in payload["style"]["prompt_contract"]
    assert "不得把不同角色复制成同一种设备" in payload["style"]["prompt_contract"]
    assert "微软雅黑（Microsoft YaHei）" in payload["style"]["prompt_contract"]
    assert "不得小于 14pt 等效尺寸" in payload["style"]["prompt_contract"]
    assert "Final ImageGen execution lock" in payload["style"]["prompt_contract"]
    assert payload["reference_image"]["required_for_every_page"] is True
    assert payload["reference_image"]["path"].endswith("palette-09.png")


def test_style_nine_reference_stops_at_indented_following_h2() -> None:
    with TemporaryDirectory() as directory:
        root = Path(directory)
        reference = root / "visual-system.md"
        reference.write_text(
            "## 扩展风格9：测试\n\nStyle 09 only.\n\n"
            "  ## 扩展风格10：测试\n\nStyle 10 must not leak.\n",
            encoding="utf-8",
        )
        lock = root / "visual_style_lock.json"
        lock.write_text(
            json.dumps(
                {
                    "style_source": str(root / "styles.json"),
                    "source_reference": str(reference),
                    "style": {"id": 9, "prompt_contract": "stale"},
                },
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )

        payload = load_style_lock(lock)

    contract = payload["style"]["prompt_contract"]
    assert "Style 09 only." in contract
    assert "扩展风格10" not in contract
    assert "Style 10 must not leak." not in contract


def test_style_nine_component_contract_reaches_prompt_compiler() -> None:
    with TemporaryDirectory() as directory:
        lock = write_project_style_lock(project=Path(directory), style_id=9)
        contract = render_content_first_style_contract(lock)

    assert "基础组件表达规范（通用）" in contract
    assert "直线端点、折点和曲线切线要干净" in contract
    assert "宽箭头带" in contract
    assert "微立体承载面保持低矮、正视、哑光" in contract
    assert "同类线宽必须一致" in contract
    assert "边框使用细、低对比、单层描边" in contract
    assert "曲线转向平滑、切线连续" in contract
    assert "不得据此改变页面的业务结构、元素数量、空间关系、阅读路径或主次关系" in contract
    assert "保留已经确定的方向、数量和连接关系" in contract
    assert "箭头头使用贴近线端的小型简洁三角形" in contract
    assert "保留既有容器形状和数量" in contract
    assert "保留已经选择的载体类型、轮廓和数量" in contract
    assert "保留已经确定的前后关系与视觉重心" in contract
    assert "主业务锚点优先表现可观察的业务动作、状态变化或受控结果" in contract
    assert "生成优先级：核心判断 → 业务动作或状态 → 主业务锚点" in contract
    assert "沿页面主要阅读路径形成连续主线" in contract
    assert "不得据此固定生成时间轴、卡片墙、左右分栏或等宽多列" in contract
    assert contract.count("文字型视觉主线") == 1
    assert contract.count("**图文融合**") == 1
    assert "左右分区仅用于不同且互补的业务角色" in contract
    assert "删除视觉部分后若业务逻辑不变" in contract
    assert "#### 多行正文或多个维度" in contract
    assert "#### 分类或矩阵" in contract
    assert "#### 步骤、流程或输入输出" in contract
    assert "#### 权利边界" in contract
    assert "#### 闭环语义" in contract
    assert "semantic_tags:" not in contract
    assert "style09:scope" not in contract
    assert "连接只表达真实关系并保持细、小、从属" in contract
    assert contract.count("保留已经确定的方向、数量和连接关系") == 1
    assert contract.count("保留既有容器形状和数量") == 1


def test_style_nine_selects_composable_conditional_clauses() -> None:
    with TemporaryDirectory() as directory:
        lock = write_project_style_lock(project=Path(directory), style_id=9)
        contract = render_content_first_style_contract(
            lock,
            semantic_tags=frozenset({"flow", "feedback"}),
        )

    assert "#### 步骤、流程或输入输出" in contract
    assert "#### 闭环语义" in contract
    assert "#### 多行正文或多个维度" not in contract
    assert "#### 分类或矩阵" not in contract
    assert "#### 权利边界" not in contract
    assert "semantic_tags:" not in contract


def test_style_nine_infers_multiple_page_semantic_tags_without_incidental_boundary() -> None:
    page = PageBlock(
        10,
        "总体业务主线",
        "\n".join(
            (
                "产品形成链：需求论证与五类审核共同形成产品设计。",
                "订单履行链：可信交付形成计量、验收、账单与结算依据。",
                "运营反馈环：跟踪订购并回流至产品形成链。",
            )
        ),
    )
    tags = _style09_page_semantic_tags(page, page.text.splitlines())

    assert {"flow", "sequence", "feedback", "loop"}.issubset(tags)
    assert "boundary" not in tags


def test_style_nine_people_rule_comes_from_the_single_style_contract() -> None:
    with TemporaryDirectory() as directory:
        lock = write_project_style_lock(project=Path(directory), style_id=9)
        prompt = enforce_style09_terminal_lock(
            "页面场景要求联合团队围桌讨论。\n默认不出现人物；禁止正脸、围桌会议、多人讨论及摆拍办公场景。",
            lock,
        )

    rule = "默认不出现人物；禁止正脸、围桌会议、多人讨论及摆拍办公场景。"
    assert "### Final ImageGen execution lock" not in prompt
    assert prompt.count(rule) == 1


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
