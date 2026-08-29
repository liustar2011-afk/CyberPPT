from __future__ import annotations

import xml.etree.ElementTree as ET
import zipfile
from pathlib import Path

import pytest
from PIL import Image

from scripts.image_to_pptx_runtime.template_assembly import (
    assemble_brand_page_svg,
    assemble_template_pptx,
    assemble_template_svg,
    load_template_contract,
)
from scripts.image_to_pptx_runtime.svg_to_pptx.drawingml.elements import _project_image_href


@pytest.mark.parametrize("xlink_href", ["template.png", "other.png"])
def test_project_image_rejects_dual_href_attributes(xlink_href: str) -> None:
    image = ET.fromstring(
        '<image xmlns="http://www.w3.org/2000/svg" '
        'xmlns:xlink="http://www.w3.org/1999/xlink" '
        f'href="template.png" xlink:href="{xlink_href}"/>'
    )

    with pytest.raises(ValueError) as exc_info:
        _project_image_href(image)

    assert str(exc_info.value) == "requires exactly one href or xlink:href"


def test_structural_page_roles_render_native_copy_without_ending_page_overflow(tmp_path: Path) -> None:
    for role, lines in (
        ("cover", ["封面标题", "封面副标题", "2026年8月"]),
        ("contents", ["目录", "第一章", "第二章", "第三章", "第四章", "第五章", "第六章"]),
        ("chapter", ["第一章", "章节导语"]),
        ("closing", ["建议提请研究确定", "明确首期产品边界和分阶段投入依据"]),
    ):
        output = tmp_path / f"{role}.svg"
        assemble_brand_page_svg(output=output, role=role, onscreen_lines=lines)
        text = output.read_text(encoding="utf-8")
        for line in lines:
            assert line in text
        assert 'font-size="58"' not in text
        expected_background = {
            "cover": "cover_bg.jpg",
            "contents": "agenda_bg.png",
            "chapter": "section_bg.png",
            "closing": "cover_bg.jpg",
        }[role]
        assert expected_background in text
    cover = (tmp_path / "cover.svg").read_text(encoding="utf-8")
    assert 'data-brand-template="01_cover"' in cover
    assert 'cx="1180"' not in cover
    contents = (tmp_path / "contents.svg").read_text(encoding="utf-8")
    assert 'id="agenda-items"' in contents
    assert contents.count('class="agenda-item-card"') == 6
    assert ">01</text>" in contents
    assert ">06</text>" in contents
    assert 'id="sectionLeftWash"' in (tmp_path / "chapter.svg").read_text(encoding="utf-8")


def test_cec_navigation_pages_split_authored_numbers_from_chapter_titles(tmp_path: Path) -> None:
    contents = tmp_path / "contents.svg"
    chapter = tmp_path / "chapter.svg"
    assemble_brand_page_svg(
        output=contents,
        role="contents",
        onscreen_lines=["汇报目录", "01 建设依据与现实差距", "02 体系构建与框架设计"],
    )
    assemble_brand_page_svg(
        output=chapter,
        role="chapter",
        onscreen_lines=["02：体系构建与框架设计"],
    )

    contents_text = contents.read_text(encoding="utf-8")
    chapter_text = chapter.read_text(encoding="utf-8")
    assert ">01</text>" in contents_text
    assert ">建设依据与现实差距</text>" in contents_text
    assert ">01 建设依据与现实差距</text>" not in contents_text
    assert ">02</text>" in chapter_text
    assert ">体系构建与框架设计</text>" in chapter_text
    assert "章节导览" not in chapter_text


def test_template_contract_uses_exact_two_to_one_body_slot() -> None:
    contract = load_template_contract()
    body = contract["rules"]["content_regions"]["body_pages"]
    assert (body["x"], body["y"], body["width"], body["height"]) == (33, 89, 1214, 607)
    assert body["width"] / body["height"] == 2
    master = contract["rules"]["master_elements"]
    assert master["footer_company_text"]["y"] == 712
    assert master["footer_page_num"]["y"] == 712


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
    assert 'width="1280" height="720" fill="#FFFFFF"' in text
    assert 'width="1214" height="607"' in text
    assert 'x="33" y="89"' in text
    assert "总体定位" in text
    assert "中国电力企业联合会" in text
    assert "5</text>" in text
    assert text.count('y="712"') >= 2
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


def test_template_pptx_embeds_notes_by_svg_stem(tmp_path: Path) -> None:
    source = tmp_path / "source.svg"
    source.write_text(
        '<svg xmlns="http://www.w3.org/2000/svg" width="400" height="200" viewBox="0 0 400 200">'
        '<text x="20" y="50">正文文字</text>'
        "</svg>",
        encoding="utf-8",
    )
    wrapper = tmp_path / "editable" / "svg_output" / "p05.svg"
    assemble_template_svg(
        source=source,
        output=wrapper,
        title="总体定位",
        page_number=5,
        mode="editable",
    )
    output = tmp_path / "exports" / "editable.svg.pptx"
    assemble_template_pptx(
        [wrapper],
        output,
        notes={"p05": "这一页说明总体定位。"},
    )

    with zipfile.ZipFile(output) as package:
        note_parts = [
            name
            for name in package.namelist()
            if name.startswith("ppt/notesSlides/notesSlide") and name.endswith(".xml")
        ]
        assert len(note_parts) == 1
        assert "这一页说明总体定位。" in package.read(note_parts[0]).decode("utf-8")
