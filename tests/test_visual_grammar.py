from __future__ import annotations
from pathlib import Path
from tempfile import TemporaryDirectory

from scripts.imagegen_pipeline.deliverable_prompt import PageBlock, render_prompt
from scripts.imagegen_pipeline.style_library import write_project_style_lock
from scripts.imagegen_pipeline.visual_grammar import default_visual_grammar

_SHORT_LINES = (
    (
        "- Treat readable text modules as elements inside the dominant composition, "
        "using calm in-composition panels or annotations rather than a separate text "
        "column or rail. No body text on busy/high-contrast imagery. Do not fabricate "
        "dates, versions, IDs, tracking codes, status values, sample records, UI data, "
        "or any other realistic-looking examples."
    ),
    (
        "- Do not split the canvas into a text-only half and an image-only half, and do "
        "not create a separate photo rail or image collage beside the text. Build one "
        "integrated composition in which image-native forms, paths, bands, depth, and "
        "spatial relationships organize the text into one reading field. Use small "
        "semantic images only as subordinate accents where they clarify meaning."
    ),
    (
        "- First distinguish subject, support, input, output, convergence, branching, loop, "
        "hierarchy, contrast, and causality. Choose the visual grammar that best explains "
        "those relationships: an architecture diagram, process flow, layered system, "
        "relationship field, or another designed composition may all be appropriate. "
        "Avoid only mechanically repeated cards, nodes, or connectors that do not clarify "
        "the page logic; let hierarchy and content determine visual weight and reading order."
    ),
    "- No connectors through/under text; no fake flow lines; one connector style.",
    "- Unequal visual weight by hierarchy — not an equal card wall.",
    (
        "- Bind each real-world image to one specific nearby business meaning. Do not use "
        "generic offices, skylines, campuses, server rooms, or technology scenes merely to "
        "fill whitespace."
    ),
    "- Multiple images are allowed when they carry distinct and necessary semantic roles.",
    (
        "- Do not use one generic industry scene to represent several unrelated meanings. "
        "Icons may be low-contrast micro-annotations only, never primary nodes, repeated "
        "module markers, card headings, or the visual mainline."
    ),
    (
        "- Do not invent summary, goal, value, outcome, or conclusion sections or labels. "
        "Any outcome inferred from the relationships may be expressed only as an unlabeled "
        "graphical state unless that text is present in the locked on-screen content."
    ),
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


def test_deliverable_prompt_uses_only_the_single_style_contract_for_style_nine() -> None:
    with TemporaryDirectory() as directory:
        lock = write_project_style_lock(project=Path(directory), style_id=9)
        prompt = render_prompt(
            PageBlock(page_number=9, title="测试", text="组件A：业务内容"),
            style_lock_path=lock,
        )

    assert "【视觉组织原则】" not in prompt
    assert "【页面编码】P09｜测试" in prompt
    assert "不得在生成图中渲染页面编码或页面标题" in prompt
    for line in _SHORT_LINES:
        assert line not in prompt
    for fragment in _OLD_CHINESE_FRAGMENTS:
        assert fragment not in prompt
    assert "【设计目标与叙事】" not in prompt
    assert "基于源文案进行专业改写" in prompt
    assert (
        "Do not render prompt field labels or meta headers. Rewrite the source copy into conclusion-first visible Chinese while preserving its factual boundary."
        in prompt
    )
