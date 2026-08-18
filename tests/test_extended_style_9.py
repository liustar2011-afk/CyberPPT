from __future__ import annotations

import json
from pathlib import Path
from tempfile import TemporaryDirectory

from cyberppt.cli import build_parser
from scripts.imagegen_pipeline.page_manifest import main as pair_manifest_main
from scripts.imagegen_pipeline.deliverable_prompt import (
    PageBlock,
    _style09_page_semantic_tags,
    enforce_style09_terminal_lock,
    style_contract,
)
from scripts.imagegen_pipeline.imagegen_handoff import render_content_first_style_contract
from scripts.imagegen_pipeline.style_library import (
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
    # Style09's prompt_contract is the scene-led spec from
    # references/visual-system.md's "扩展风格9" section (restored 2026-08-18
    # after an earlier rewrite had silently dropped it down to a much
    # shorter flat/minimal contract with no terminal execution lock).
    # Assertions below check real behavioral properties of that contract by
    # their actual current wording, not brittle exact headings from the
    # long-gone draft this test was originally written against.
    assert "reconstruction-friendly, editorial visual blueprint" in style_nine["prompt_contract"]
    assert "Do not distribute content according to item count" in style_nine["prompt_contract"]
    assert "executive briefing" in style_nine["prompt_contract"]
    assert "#FFFFFF" in style_nine["prompt_contract"]
    assert "#12355B" in style_nine["prompt_contract"]
    assert "Industry scene anchor" not in style_nine["prompt_contract"]
    assert "逐项配图" not in style_nine["prompt_contract"]
    assert "线条：主关系用细、实、方向一致的深蓝线" in style_nine["component_rule"]
    assert "禁止宽箭头带" in style_nine["component_rule"]
    assert "低矮哑光正视微立体" in style_nine["component_rule"]
    assert "icon_rule" not in style_nine
    assert "政企领导汇报所需的信息密度" in style_nine["density_rule"]
    assert "领导汇报" in style_nine["scenario"]
    assert 10_000 < len(style_nine["prompt_contract"]) < 25_000
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
    assert "scene-led editorial business-infographic style" in payload["style"]["prompt_contract"]
    assert "Icon count is zero by default" in payload["style"]["prompt_contract"]
    assert "reconstruction-friendly, editorial visual blueprint" in payload["style"]["prompt_contract"]
    assert "最终执行锁" in payload["style"]["prompt_contract"]
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

    assert "scene-led editorial business-infographic style" in contract
    assert "reconstruction-friendly, editorial visual blueprint" in contract
    assert "### 6. Depth, material and icon discipline — hard" in contract
    assert "Icons are not a default visual language for Style 09" in contract
    assert "Icon count is zero by default" in contract
    assert "semantic_tags:" not in contract
    assert "style09:scope" not in contract
    assert "最终执行锁" in contract


def test_style_nine_is_a_full_universal_contract_not_a_page_clause_selector() -> None:
    with TemporaryDirectory() as directory:
        lock = write_project_style_lock(project=Path(directory), style_id=9)
        contract = render_content_first_style_contract(
            lock,
            semantic_tags=frozenset({"flow", "feedback"}),
        )

    assert "### 2. Semantic anchor and composition — hard" in contract
    assert "### 7. Semantic economy and final priority — hard" in contract
    assert "Identify the page’s core judgment and primary business relationship" in contract
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


def test_style_nine_terminal_lock_helper_is_not_the_formal_style_consumer() -> None:
    with TemporaryDirectory() as directory:
        lock = write_project_style_lock(project=Path(directory), style_id=9)
        prompt = enforce_style09_terminal_lock(style_contract(lock), lock)

    assert prompt.count("### Final ImageGen execution lock — hard") == 0
    assert prompt.count("【风格09最终执行锁｜最高优先级】") == 1


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
    assert "### 7. Semantic economy and final priority — hard" in contract
    assert "must not restate the same label, sequence or conclusion" in contract
    assert "extra summary band" in contract
    assert "建设响应" not in contract
    assert "input, processing, review, control or output" in contract


def test_style_nine_contract_preserves_industry_scene_and_rejects_large_document_carriers() -> None:
    with TemporaryDirectory() as directory:
        lock = write_project_style_lock(project=Path(directory), style_id=9)
        payload = json.loads(lock.read_text(encoding="utf-8"))

    contract = payload["style"]["prompt_contract"]
    assert "Build the page from recognizable business scenes, concrete objects, visible actions, evidence and outcomes" in contract
    assert "richness should come from meaningful business expression, not decorative objects" in contract
    assert "drop the scene entirely and use a flat, structured relationship field instead" in contract
    assert "supporting scene or evidence fragments" in contract
    assert "Icons are not a default visual language for Style 09. Start from zero icons." in contract
