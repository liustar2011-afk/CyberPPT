from xml.etree import ElementTree as ET

from scripts.dual_image_overlay.rebuild_engine.svg_to_pptx.drawingml_context import ConvertContext
from scripts.dual_image_overlay.rebuild_engine.svg_to_pptx.drawingml_elements import convert_text


def test_text_export_enforces_global_minimum_font_size() -> None:
    elem = ET.fromstring(
        '<text xmlns="http://www.w3.org/2000/svg" x="10" y="20" font-size="6.5">节点说明</text>'
    )
    ctx = ConvertContext(scale_y=0.8)

    result = convert_text(elem, ctx)

    assert result is not None
    assert 'sz="650"' in result.xml
