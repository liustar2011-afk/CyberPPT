from pathlib import Path
import xml.etree.ElementTree as ET

from scripts.image_to_pptx_runtime.native_text_style import (
    STYLE_ATTR,
    apply_default_native_text_style,
)


def _text_nodes(path: Path) -> list[ET.Element]:
    root = ET.parse(path).getroot()
    return [node for node in root.iter() if node.tag.rsplit("}", 1)[-1] == "text"]


def test_default_style_splits_labels_and_preserves_geometry(tmp_path: Path) -> None:
    svg = tmp_path / "page.svg"
    svg.write_text(
        '<svg xmlns="http://www.w3.org/2000/svg" width="400" height="200" '
        'viewBox="0 0 400 200"><text x="40" y="80" font-size="20">'
        "资源管理：统一整合数据、模型</text></svg>",
        encoding="utf-8",
    )

    report = apply_default_native_text_style(svg)
    root = ET.parse(svg).getroot()
    node = _text_nodes(svg)[0]
    assert report["profile"] == "editorial-source-text-v1"
    assert report["split_label_count"] == 1
    assert node.get("x") == "40"
    assert node.get("y") == "80"
    assert node.get("font-size") == "20"
    assert root.get(STYLE_ATTR) == "editorial-source-text-v1"
    tspans = list(node)
    assert ["".join(tspan.itertext()) for tspan in tspans] == ["资源管理：", "统一整合数据、模型"]
    assert tspans[0].get("fill") == "#12355B"
    assert tspans[0].get("font-weight") == "700"
    assert tspans[1].get("fill") == "#202020"
    assert tspans[1].get("font-weight") == "400"


def test_locked_native_text_style_is_left_unchanged(tmp_path: Path) -> None:
    svg = tmp_path / "locked.svg"
    original = (
        '<svg xmlns="http://www.w3.org/2000/svg" '
        f'{STYLE_ATTR}="locked"><text x="2" y="3">标题：正文</text></svg>'
    )
    svg.write_text(original, encoding="utf-8")

    report = apply_default_native_text_style(svg)
    assert report["preserved_locked"] is True
    assert svg.read_text(encoding="utf-8") == original
