from __future__ import annotations

from pathlib import Path
import sys

SCRIPTS_DIR = Path(__file__).resolve().parent.parent / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from svg_to_pptx.drawingml_utils import parse_hex_color


def test_parse_hex_color_accepts_named_white_as_export_fallback() -> None:
    assert parse_hex_color("white") == "FFFFFF"
    assert parse_hex_color("White") == "FFFFFF"


def test_parse_hex_color_accepts_rgb_as_export_fallback() -> None:
    assert parse_hex_color("rgb(255, 255, 255)") == "FFFFFF"
    assert parse_hex_color("rgba(11, 59, 115, 0.8)") == "0B3B73"


def test_parse_hex_color_keeps_invalid_values_unhandled() -> None:
    assert parse_hex_color("currentColor") is None
    assert parse_hex_color("url(#grad)") is None
