from __future__ import annotations

import xml.etree.ElementTree as ET
from pathlib import Path

from PIL import Image

from scripts.image_to_pptx_runtime.template_assembly import (
    assemble_template_svg,
    load_template_contract,
)


def test_template_contract_uses_exact_two_to_one_body_slot() -> None:
    contract = load_template_contract()
    body = contract["rules"]["content_regions"]["body_pages"]
    assert (body["x"], body["y"], body["width"], body["height"]) == (33, 89, 1214, 607)
    assert body["width"] / body["height"] == 2


def test_image_mode_places_body_image_in_template_slot(tmp_path: Path) -> None:
    image = tmp_path / "body.png"
    Image.new("RGB", (2432, 1216), "white").save(image)
    output = tmp_path / "image" / "svg_output" / "p01.svg"

    assemble_template_svg(
        source=image,
        output=output,
        title="总体定位",
        page_number=5,
        mode="image",
        body_image=image,
    )

    text = output.read_text(encoding="utf-8")
    assert 'width="1214" height="607"' in text
    assert 'x="33" y="89"' in text
    assert "总体定位" in text
    assert "中国电力企业联合会" in text
    assert "5</text>" in text
    assert (tmp_path / "image" / "images" / "logo.png").is_file()


def test_editable_mode_scales_two_to_one_authoring_svg_into_body_slot(tmp_path: Path) -> None:
    source = tmp_path / "source.svg"
    source.write_text(
        '<svg xmlns="http://www.w3.org/2000/svg" width="400" height="200" viewBox="0 0 400 200">'
        '<rect id="body-card" x="10" y="20" width="100" height="40" fill="#123B66"/>'
        '<text id="body-text" x="20" y="50" font-size="18">正文文字</text>'
        "</svg>",
        encoding="utf-8",
    )
    output = tmp_path / "editable" / "svg_output" / "p01.svg"

    assemble_template_svg(
        source=source,
        output=output,
        title="总体定位",
        page_number=5,
        mode="editable",
    )

    root = ET.parse(output).getroot()
    assert root.get("viewBox") == "0 0 1280 720"
    body = root.find("{http://www.w3.org/2000/svg}g")
    assert body is not None
    assert body.get("id") == "quick-body"
    assert body.get("transform") == "translate(33 89)"
    assert body.find("{http://www.w3.org/2000/svg}rect").get("x") == "30.35"
    assert body.find("{http://www.w3.org/2000/svg}text").get("x") == "60.7"
    assert body.find("{http://www.w3.org/2000/svg}text").get("font-size") == "54.63"
    assert "正文文字" in output.read_text(encoding="utf-8")


def test_editable_mode_rejects_non_two_to_one_svg(tmp_path: Path) -> None:
    source = tmp_path / "source.svg"
    source.write_text(
        '<svg xmlns="http://www.w3.org/2000/svg" width="400" height="225" viewBox="0 0 400 225"/>',
        encoding="utf-8",
    )
    try:
        assemble_template_svg(
            source=source,
            output=tmp_path / "out.svg",
            title="标题",
            page_number=1,
            mode="editable",
        )
    except ValueError as exc:
        assert "2:1" in str(exc)
    else:
        raise AssertionError("non-2:1 authoring SVG must be rejected")
