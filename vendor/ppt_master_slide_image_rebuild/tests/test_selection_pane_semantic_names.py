from __future__ import annotations

import sys
from pathlib import Path

SCRIPTS_DIR = Path(__file__).resolve().parent.parent / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from svg_to_pptx.drawingml_converter import convert_svg_to_slide_shapes
from svg_to_pptx.semantic_names import semantic_shape_name


PNG_1X1 = (
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAF"
    "gwJ/lC4V8wAAAABJRU5ErkJggg=="
)


def test_svg_to_pptx_uses_semantic_selection_pane_names(tmp_path: Path) -> None:
    svg_path = tmp_path / "P01.svg"
    svg_path.write_text(
        f"""<svg xmlns="http://www.w3.org/2000/svg" width="1600" height="900">
  <text data-text-region-id="main_title" x="100" y="120"
        font-family="Microsoft YaHei" font-size="36" fill="#111827">标题</text>
  <g data-icon-id="security_shield">
    <circle cx="120" cy="220" r="24" fill="#0B5CAD"/>
  </g>
  <g data-zone-id="zone_goal_short" data-primitive="target_goal_card">
    <rect x="200" y="180" width="220" height="110" fill="#FFFFFF" stroke="#0B5CAD"/>
  </g>
  <line data-chain-connector="short_goal->mid_goal" x1="430" y1="235" x2="560" y2="235"
        stroke="#0B5CAD" stroke-width="4"/>
  <image data-crop-id="footer_pattern" x="100" y="700" width="20" height="20"
         href="data:image/png;base64,{PNG_1X1}"/>
</svg>""",
        encoding="utf-8",
    )

    slide_xml, media_files, rel_entries, _anim_targets = convert_svg_to_slide_shapes(svg_path)

    assert 'name="P01_text_main_title"' in slide_xml
    assert 'name="P01_icon_security_shield"' in slide_xml
    assert 'name="P01_zone_zone_goal_short_target_goal_card"' in slide_xml
    assert 'name="P01_connector_short_goal_mid_goal"' in slide_xml
    assert 'name="P01_crop_footer_pattern"' in slide_xml
    assert media_files
    assert rel_entries


def test_unannotated_shapes_keep_historical_fallback_names(tmp_path: Path) -> None:
    svg_path = tmp_path / "P02.svg"
    svg_path.write_text(
        """<svg xmlns="http://www.w3.org/2000/svg" width="1600" height="900">
  <rect x="20" y="20" width="100" height="60" fill="#FFFFFF"/>
  <text x="20" y="120" font-family="Arial" font-size="24" fill="#111827">Plain</text>
</svg>""",
        encoding="utf-8",
    )

    slide_xml, _media_files, _rel_entries, _anim_targets = convert_svg_to_slide_shapes(svg_path)

    assert 'name="Rectangle ' in slide_xml
    assert 'name="TextBox ' in slide_xml


def test_duplicate_semantic_names_are_suffixed_within_slide(tmp_path: Path) -> None:
    svg_path = tmp_path / "P03.svg"
    svg_path.write_text(
        """<svg xmlns="http://www.w3.org/2000/svg" width="1600" height="900">
  <text data-text-region-id="body_line" x="20" y="120"
        font-family="Arial" font-size="24" fill="#111827">Line 1</text>
  <text data-text-region-id="body_line" x="20" y="160"
        font-family="Arial" font-size="24" fill="#111827">Line 2</text>
</svg>""",
        encoding="utf-8",
    )

    slide_xml, _media_files, _rel_entries, _anim_targets = convert_svg_to_slide_shapes(svg_path)

    assert 'name="P03_text_body_line"' in slide_xml
    assert 'name="P03_text_body_line_2"' in slide_xml


def test_non_ascii_semantic_value_gets_stable_hash_name() -> None:
    from xml.etree import ElementTree as ET

    elem = ET.fromstring('<text data-text-region-id="总体目标"/>')

    name = semantic_shape_name(elem, "text", 7, page_id="P05")

    assert name.startswith("P05_text_")
    assert len(name) <= 80
    assert name != "P05_text_"
