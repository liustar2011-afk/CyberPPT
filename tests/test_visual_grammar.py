from __future__ import annotations
from pathlib import Path
from tempfile import TemporaryDirectory

from scripts.dual_image_overlay.deliverable_prompt import PageBlock, render_prompt
from scripts.dual_image_overlay.style_library import write_project_style_lock
from scripts.dual_image_overlay.visual_grammar import default_visual_grammar

_SHORT_LINES = (
    "- No body text on busy/high-contrast imagery.",
    "- No connectors through/under text; no fake flow lines; one connector style.",
    "- Unequal visual weight by hierarchy — not an equal card wall.",
)

_OLD_CHINESE_FRAGMENTS = (
    "允许使用文字框、标签、卡片、侧栏、色块和分区",
    "每个容器必须承担明确的业务语义",
    "不得为了版式整齐复制无语义容器",
    "箭头、路径和连接线采用细线或色带",
    "不得穿过、遮挡或托载正文文字",
    "正文必须位于干净、稳定、对比充足的区域",
    "不同层级不得被处理成完全等权",
)


def test_open_visual_grammar_allows_expression_with_business_boundaries() -> None:
    contract = default_visual_grammar()
    rendered = contract.render()

    for line in _SHORT_LINES:
        assert line in rendered
    assert rendered == "\n".join(_SHORT_LINES)
    for fragment in _OLD_CHINESE_FRAGMENTS:
        assert fragment not in rendered
    assert "光流" not in rendered
    assert "空间轨迹" not in rendered
    assert "轻微立体效果" not in rendered


def test_deliverable_prompt_renders_visual_grammar_once_for_style_nine() -> None:
    with TemporaryDirectory() as directory:
        lock = write_project_style_lock(project=Path(directory), style_id=9)
        prompt = render_prompt(
            PageBlock(page_number=9, title="测试", text="组件A：业务内容"),
            style_lock_path=lock,
        )

    assert prompt.count("【视觉组织原则】") == 1
    for line in _SHORT_LINES:
        assert line in prompt
    for fragment in _OLD_CHINESE_FRAGMENTS:
        assert fragment not in prompt
    assert "【设计目标与叙事】" not in prompt
    assert "leadership briefing" in prompt.lower()
    assert "speech-support" in prompt
    assert "not a process infographic" in prompt
    assert "Not a consulting deliverable" in prompt
    assert "Prefer editorial simplicity and business clarity" in prompt
    assert "Visual hierarchy should follow the importance of the message" in prompt
    assert "Do not force every page to have a single hero image" in prompt
    assert "Do not apply one visual template to all pages" in prompt
    assert "People are supporting contextual elements only" in prompt
    assert "Avoid front-facing portraits" in prompt
    assert "Prefer side views, back views, three-quarter views" in prompt
    assert "highest-contrast or largest visual element" in prompt
    assert "naturally engaged in professional work" in prompt
    assert "Visual priority: page message and business logic" in prompt
    assert "Screens, charts, and data interfaces are supporting evidence only" in prompt
    assert "Avoid control-room hero shots" in prompt
    assert "smart city exhibition style" in prompt
    assert "Consulting research" not in prompt
    assert "Industry scene and imagery:" in prompt
    assert "Images are supporting evidence, not mandatory decoration" in prompt
    assert "Use images only when they improve understanding" in prompt
    assert "Prefer: architecture" not in prompt
    assert "capability evolution map" not in prompt
    assert "software-architecture look" in prompt
    assert "Content fidelity and visual logic:" in prompt
    assert "Do not introduce new visual relationships" in prompt
    assert "clarify the content, not redefine the content" in prompt
    assert "lifecycle circles with isolated nodes" in prompt
    assert "Documentary / editorial photography" in prompt
    assert "numbered step cards" in prompt
    assert "请先理解" not in prompt
    assert "页面使命" not in prompt
    assert "母版" not in prompt
    assert "可编辑文字层" not in prompt
    assert "光流" not in prompt
    assert "空间轨迹" not in prompt
    assert "实景彩色插画" in prompt
    assert "场景辅助" not in prompt
    assert "photo-inspired editorial industry illustration" in prompt
    assert "secondary point-art" not in prompt
    assert "Enhance the message" in prompt
    assert "宁少勿滥" in prompt
    assert "One dominant visual narrative" not in prompt
    assert "One visual center" not in prompt
    assert "visual anchor" not in prompt
    assert "Business capability formation is the narrative center" not in prompt
    assert "不使用外部风格 preset" not in prompt
    assert "确认样张" not in prompt
    assert "密度：不改变【内容锁定】" not in prompt
    assert "Style constrains color" not in prompt
    assert "Do not rely on 「视觉结构」" not in prompt
    assert "视觉结构" not in prompt
    assert "请以【视觉结构】为构图思考起点" not in prompt
    assert "视觉结构：" not in prompt
    assert "图不是装饰" not in prompt
    assert "图多字少" not in prompt
    assert "## 第9页：" not in prompt
    assert "忠实于【内容锁定】" in prompt
    assert "核心判断" not in prompt
    assert "禁止项" not in prompt
    assert "Boundary (do not show on slide)" not in prompt
    assert "Boundary text must not appear on the slide" not in prompt
    assert (
        "Do not invent section labels like meta headers; only render 上屏文字 modules."
        in prompt
    )
