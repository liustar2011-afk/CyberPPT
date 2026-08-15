from pathlib import Path

from PIL import Image

from scripts.image_to_editable_svg.reconstruct import author_page_svg, inspect_page
from scripts.image_to_editable_svg.roster import normalize_full_page
from scripts.presentation_qa.text_content import _normalize


def test_prepared_authoring_svg_preserves_native_reconstruction(tmp_path: Path) -> None:
    source = tmp_path / "source.png"
    Image.new("RGB", (100, 50), "white").save(source)
    frame = normalize_full_page(page_number=1, source=source, output_dir=tmp_path / "frames")
    authored = tmp_path / "authored.svg"
    authored.write_text('<svg xmlns="http://www.w3.org/2000/svg"><path d="M0 0h1"/><text>核心结论</text></svg>', encoding="utf-8")
    result = inspect_page(frame, script_text=["核心结论"], ocr_layout={"items": []}, authoring_svg_path=authored)
    assert result["layers"][0]["locator_source"] == "authoring_svg"
    output = author_page_svg(result, tmp_path / "out")
    assert output.read_text(encoding="utf-8") == authored.read_text(encoding="utf-8")


def test_text_content_normalizes_ideographic_space() -> None:
    assert _normalize("01　真实使用") == _normalize("01 真实使用")
