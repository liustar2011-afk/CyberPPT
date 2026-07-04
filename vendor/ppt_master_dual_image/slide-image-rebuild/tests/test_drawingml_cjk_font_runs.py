from __future__ import annotations

from pathlib import Path
import sys

SCRIPTS_DIR = Path(__file__).resolve().parent.parent / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from svg_to_pptx.drawingml_context import ConvertContext
from svg_to_pptx.drawingml_elements import _build_run_xml
from svg_to_pptx.drawingml_utils import parse_font_family


def test_cjk_text_run_declares_latin_ea_and_cs_typefaces() -> None:
    run = {
        "text": "中文测试",
        "fill": "111827",
        "fill_raw": "#111827",
        "font_size": 20,
        "font_weight": "400",
        "font_style": "",
        "text_decoration": "",
        "opacity": 1,
        "font_family": "Source Han Sans CN, PingFang SC, Microsoft YaHei, Arial",
    }
    fonts = parse_font_family(run["font_family"])

    xml = _build_run_xml(run, fonts, ConvertContext(), "")

    assert '<a:latin typeface="' in xml
    assert '<a:ea typeface="Microsoft YaHei"/>' in xml
    assert '<a:cs typeface="' in xml
    assert 'lang="zh-CN"' in xml
