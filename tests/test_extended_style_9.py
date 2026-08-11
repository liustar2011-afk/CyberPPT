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
    assert style_nine["name"] == "纯白 + 深蓝领导汇报"
    assert resolve_default_style(style_name="ivory_deep_blue_scene")["id"] == 9
    assert style_nine["colors"] == {
        **STYLE_FOUR_CONTRACT["colors"],
        "background": "#FFFFFF",
    }
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
    assert payload["style"]["name"] == "纯白 + 深蓝领导汇报"
    assert payload["policy"]["selected_from_default_8"] is False
    assert payload["policy"]["selected_from_extension"] is True
    assert "### 核心视觉语法" in payload["style"]["prompt_contract"]
    assert "图标默认数量为零" in payload["style"]["prompt_contract"]
    assert "宽箭头带" in payload["style"]["prompt_contract"]
    assert "行业场景与文字共同构成主视觉" in payload["style"]["prompt_contract"]
    assert payload["style"]["prompt_contract"].count("文字型视觉主线") == 1
    assert "不得新增非锁定标签" in payload["style"]["prompt_contract"]
    assert payload["style"]["prompt_contract"].count("**图文融合**") == 1
    assert "禁止图形区与文字区各自完整重复同一组内容" in payload["style"]["prompt_contract"]
    assert "把文字列表伪装成关系图" in payload["style"]["prompt_contract"]
    assert "2—5个文字组分布在同一连续关系场中" in payload["style"]["prompt_contract"]
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
    assert "必要的微立体关系面保持低矮、正视、哑光" in contract
    assert "同类线宽必须一致" in contract
    assert "边框使用细、低对比、单层描边" in contract
    assert "曲线转向平滑、切线连续" in contract
    assert "不得据此改变页面的业务结构、元素数量、空间关系、阅读路径或主次关系" in contract
    assert "保留已经确定的方向、数量和连接关系" in contract
    assert "箭头头使用贴近线端的小型简洁三角形" in contract
    assert "本规则不得诱导新增、放大或复制容器" in contract
    assert "不得据此新增大底板、资料容器、独立文字面" in contract
    assert "保留已经确定的前后关系与视觉重心" in contract
    assert "主业务锚点优先由真实设施、设备、作业环境、人员动作、物流或信息流" in contract
    assert "生成优先级：核心判断 → 行业环境与业务对象 → 业务动作、状态或结果" in contract
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
    assert "少量方向线" in contract
    assert contract.count("保留已经确定的方向、数量和连接关系") == 1
    assert contract.count("本规则不得诱导新增、放大或复制容器") == 1


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


def test_style_nine_contract_suppresses_duplicate_response_structures() -> None:
    with TemporaryDirectory() as directory:
        lock = write_project_style_lock(project=Path(directory), style_id=9)
        payload = json.loads(lock.read_text(encoding="utf-8"))

    contract = payload["style"]["prompt_contract"]
    assert "重复表达压制（硬约束）" in contract
    assert "第二套同类关系结构" in contract
    assert "重复总结区" in contract
    assert "建设响应" not in contract
    assert "同一页每个核心概念只允许一个主文字载体和一个主要图形承载面" in contract


def test_style_nine_contract_preserves_industry_scene_and_rejects_large_document_carriers() -> None:
    with TemporaryDirectory() as directory:
        lock = write_project_style_lock(project=Path(directory), style_id=9)
        payload = json.loads(lock.read_text(encoding="utf-8"))

    contract = payload["style"]["prompt_contract"]
    assert "行业环境不是装饰或末端点缀" in contract
    assert "不得先切出独立文字区再把场景填入剩余区域" in contract
    assert "仅可作为小型证据细节，全部合计不得压过主要行业场景" in contract
    assert "一个占主导的行业场景或主关系" in contract
    assert "不得让所有区域等权" in contract
    assert "通过大胆裁切、大小差、前后景、清晰度和跨区流向形成三级权重" in contract
    assert "可使用少量轻量局部承载面，但不得形成等权卡片墙" in contract
    assert "若提供风格参考图，只继承色彩、材质、留白、字体层级和编辑节奏" in contract
    assert "不复制其具体物件或固定分区" in contract
    assert "平台、中枢、引擎、中心等本身就是页面明确表达的业务对象时，可以成为中心载体" in contract
    assert "不得放在底部通栏重复全文结论" in contract
    assert "合同或成果对象" not in contract
    assert "扩大主视觉面和文字区" not in contract
    assert "锚点在内容允许时占约35%—50%的视觉权重" not in contract
    assert "高端咨询报告构图" in contract
    assert "一个主视觉或主关系约占画面视觉注意力的40%—55%" in contract
    assert "每个主要语义区域都可以有行业配图" in contract
    assert "每一处图片、对象或场景都必须明确承担至少一个锁定文字组" in contract
    assert "允许一句主要判断、一个业务动作或一个重要明细拥有一张独立配图" in contract
    assert "不得为了减少图片数量而强行合并或压缩有明确语义价值的配图" in contract
    assert "判断标准不是“一句话一张图”的数量" in contract
    assert "配图粒度必须跟随语义粒度" in contract
    assert "一张大场景只有在其中可识别的对象、动作或流向能够同时解释多个文字组及其关系时才可合并承载" in contract
    assert "否则应为主要文字组配置各自贴合的语义场景、对象切片或关系画面" in contract
    assert "不得用只证明行业身份的全景照片替代" in contract
    assert "无法指出所对应锁定文字组的图片不得出现" in contract
    assert "不得把泛行业照片铺在页边、页角或底层充当气氛装饰" in contract
    assert "应删除无语义装饰，把面积让给真正解释主关系的场景、对象和文字" in contract
    assert "至少一处行业场景采用大胆裁切或延伸至画面边缘" in contract
    assert "否则禁止对称圆环、中央圆盘" in contract
    assert "不得让所有区域等权" in contract
