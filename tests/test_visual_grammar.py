from __future__ import annotations
from pathlib import Path
from tempfile import TemporaryDirectory

from scripts.dual_image_overlay.deliverable_prompt import PageBlock, render_prompt
from scripts.dual_image_overlay.style_library import write_project_style_lock
from scripts.dual_image_overlay.visual_grammar import default_visual_grammar

_SHORT_LINES = (
    (
        "- Treat readable text modules as elements inside the dominant composition, "
        "using calm in-composition panels or annotations rather than a separate text "
        "column or rail. No body text on busy/high-contrast imagery."
    ),
    (
        "- Do not split the canvas into a text-only half and an image-only half, and do "
        "not create a separate photo rail or image collage beside the text. Build one "
        "integrated composition: place semantic visuals within the same overall reading "
        "field as the nearby text modules, with varied scale, staggered placement, and "
        "shared whitespace. Each visual must directly clarify the adjacent statement."
    ),
    (
        "- Use process, hierarchy, paths, convergence, branching, and causal relationships "
        "when they make the locked text easier to understand and give its reading order "
        "clear visual motion. Let the graphic forms embody the relationships instead of "
        "reducing them to plain boxes and generic connector lines. Do not replace the text "
        "relationships with a decorative scene or generic office photo."
    ),
    "- No connectors through/under text; no fake flow lines; one connector style.",
    "- Unequal visual weight by hierarchy — not an equal card wall.",
    "- Bind each real-world image to one specific nearby business meaning.",
    "- Multiple images are allowed when they carry distinct and necessary semantic roles.",
    "- Do not use one generic industry scene to represent several unrelated meanings.",
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
    assert "【页面编码】P09｜测试" in prompt
    assert "不得在生成图中渲染页面编码或页面标题" in prompt
    for line in _SHORT_LINES:
        assert prompt.count(line) == 1
    for fragment in _OLD_CHINESE_FRAGMENTS:
        assert fragment not in prompt
    assert "【设计目标与叙事】" not in prompt
    assert "忠实于【内容锁定】" in prompt
    assert (
        "Do not invent section labels like meta headers; only render 上屏文字 modules."
        in prompt
    )
