from pathlib import Path

from PIL import Image

from scripts.image_to_editable_svg.reconstruct import author_page_svg, inspect_page
from scripts.image_to_editable_svg.roster import normalize_full_page
from scripts.image_to_editable_svg.svg_quality import check_page_svg


def _result(tmp_path):
    source = tmp_path / "source.png"
    Image.new("RGB", (100, 50), "white").save(source)
    frame = normalize_full_page(page_number=4, source=source, output_dir=tmp_path / "frames")
    return frame, inspect_page(frame, script_text=["核心结论"], ocr_layout={"items": [{"text": "核心结论", "bbox": [1, 2, 30, 10]}]})


def test_svg_uses_native_text_and_excludes_full_source_image(tmp_path):
    frame, result = _result(tmp_path)
    svg = author_page_svg(result, tmp_path / "svg")
    content = svg.read_text(encoding="utf-8")
    assert "核心结论" in content
    assert str(frame.normalized_path) not in content
    assert 'fill="#12355B"' in content
    assert 'font-weight="700"' in content
    assert check_page_svg(svg, result)["valid"] is True


def test_quality_gate_rejects_unregistered_or_manual_layer(tmp_path):
    _, result = _result(tmp_path)
    result["layers"][0]["status"] = "manual_required"
    svg = tmp_path / "p04.svg"
    svg.write_text('<svg xmlns="http://www.w3.org/2000/svg"><text>核心结论</text></svg>', encoding="utf-8")
    report = check_page_svg(svg, result)
    assert report["valid"] is False
