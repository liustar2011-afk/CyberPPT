from __future__ import annotations

from pathlib import Path

import fitz
from docx import Document
from pptx import Presentation
from pptx.util import Inches

from ppt_compiler.extractors import extract_source, initialise_project


def test_docx_pdf_pptx_and_txt_extractors(tmp_path: Path) -> None:
    docx_path = tmp_path / "sample.docx"
    document = Document()
    document.add_heading("建设目标", level=1)
    document.add_paragraph("形成可追溯的PPT脚本。")
    table = document.add_table(rows=1, cols=2)
    table.cell(0, 0).text = "字段"
    table.cell(0, 1).text = "内容"
    document.save(docx_path)

    pdf_path = tmp_path / "sample.pdf"
    pdf = fitz.open()
    page = pdf.new_page()
    page.insert_text((72, 72), "Project Goal", fontsize=18)
    page.insert_text((72, 110), "Build a traceable PPT script.", fontsize=11)
    pdf.save(pdf_path)
    pdf.close()

    pptx_path = tmp_path / "sample.pptx"
    prs = Presentation()
    slide = prs.slides.add_slide(prs.slide_layouts[5])
    slide.shapes.title.text = "总体架构"
    box = slide.shapes.add_textbox(Inches(1), Inches(2), Inches(5), Inches(1))
    box.text_frame.text = "源材料—信息资产—页面规划—视觉脚本"
    prs.save(pptx_path)

    txt_path = tmp_path / "sample.txt"
    txt_path.write_text("一、背景\n\n需要稳定解析材料。", encoding="utf-8")

    for path in [docx_path, pdf_path, pptx_path, txt_path]:
        result = extract_source(path)
        assert result.metadata["block_count"] >= 1
        assert result.metadata["character_count"] >= 1
        assert all(block["source_id"].startswith("S") for block in result.blocks)


def test_force_initialisation_removes_stale_managed_files(tmp_path: Path, skill_root: Path) -> None:
    project = tmp_path / "project"
    profile = skill_root / "assets/profiles/generic_executive.yaml"
    first = tmp_path / "first.txt"
    second = tmp_path / "second.txt"
    first.write_text("第一份材料", encoding="utf-8")
    second.write_text("第二份材料", encoding="utf-8")

    initialise_project([first], project, profile)
    stale = project / "stages/old-stage.json"
    stale.parent.mkdir(parents=True, exist_ok=True)
    stale.write_text("{}", encoding="utf-8")
    (project / ".ppt-script-skill-state.json").write_text('{"locks":{"assets":{}}}', encoding="utf-8")

    initialise_project([second], project, profile, force=True)

    assert not stale.exists()
    assert not (project / ".ppt-script-skill-state.json").exists()
    originals = list((project / "source/original").iterdir())
    assert len(originals) == 1
    assert originals[0].name.endswith("second.txt")
