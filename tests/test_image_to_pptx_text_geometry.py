from __future__ import annotations

from pathlib import Path

from scripts.image_to_pptx_runtime.runtime_provenance import (
    CONVERSION_CONTRACT_VERSION,
    UPSTREAM_COMMIT,
)
from scripts.image_to_pptx_runtime.stage02_adapter import _quick_page_binding
from scripts.image_to_pptx_runtime.svg_quality.checker import SVGQualityChecker
from scripts.image_to_pptx_runtime.svg_to_pptx.drawingml.converter import (
    convert_svg_to_slide_shapes,
)


def _five_column_svg() -> str:
    columns = []
    for index, x in enumerate((70, 370, 670, 970, 1270), start=1):
        columns.append(
            f'<g id="column-{index}" data-pptx-bounds="{x} 180 260 600">'
            f'<text id="number-{index}" x="{x}" y="220" font-size="32" '
            f'font-family="Microsoft YaHei" font-weight="700">0{index}</text>'
            f'<text id="body-{index}" x="{x}" y="280" font-size="22" '
            f'font-family="Microsoft YaHei">'
            f'第{index}栏中文标题<tspan x="{x}" dy="34">第二行说明</tspan>'
            '</text></g>'
        )
    return (
        '<svg xmlns="http://www.w3.org/2000/svg" '
        'viewBox="0 0 1600 900" width="1600" height="900">'
        + ''.join(columns)
        + '</svg>'
    )


def test_five_column_chinese_text_geometry_trace(tmp_path: Path) -> None:
    svg_path = tmp_path / "five-columns.svg"
    svg_path.write_text(_five_column_svg(), encoding="utf-8")
    trace: list[dict] = []

    convert_svg_to_slide_shapes(
        svg_path,
        trace_out=trace,
        text_flow="preserve",
    )

    text_events = [
        event for event in trace[0]["events"]
        if event.get("output_geometry") == "text"
    ]
    assert len(text_events) == 10
    number_events = [event for event in text_events if event.get("id", "").startswith("number-")]
    assert [event["source_attributes"]["x"] for event in number_events] == [
        "70", "370", "670", "970", "1270"
    ]
    assert {tuple(event["output_font_sizes_pt"]) for event in number_events} == {(24.0,)}
    assert all(len(event["bounds_emu"]) == 4 for event in text_events)

    result = SVGQualityChecker().check_file(svg_path)
    assert not result["errors"]


def test_quick_checkpoint_binds_converter_version(tmp_path: Path) -> None:
    authored = tmp_path / "page.svg"
    authored.write_text(_five_column_svg(), encoding="utf-8")
    full = tmp_path / "full.png"
    clean = tmp_path / "clean.png"
    full.write_bytes(b"full")
    clean.write_bytes(b"clean")
    pair = {
        "full": {"path": str(full)},
        "clean_base": {"path": str(clean), "build_root": str(tmp_path)},
    }

    binding = _quick_page_binding(
        pair,
        authored,
        template_contract={"rules": {}},
        style_lock=None,
    )

    assert binding["quick_runtime_upstream_commit"] == UPSTREAM_COMMIT
    assert binding["quick_conversion_contract_version"] == CONVERSION_CONTRACT_VERSION
