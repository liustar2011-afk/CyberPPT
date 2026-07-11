from __future__ import annotations

import json
from pathlib import Path

from cyberppt.phase1.artifacts import phase1_paths
from cyberppt.phase1.source_bundle import build_source_bundle, write_source_bundle


def test_source_bundle_preserves_locator_and_numbers(tmp_path: Path) -> None:
    source = tmp_path / "source_extract.md"
    source.write_text("## P26\n2025年用电量103682亿千瓦时，同比增长5.0%。\n", encoding="utf-8")

    bundle = build_source_bundle(source, max_chunk_chars=20)

    unit = bundle.units[0]
    assert unit.unit_id == "U0001"
    assert unit.locator == "P26"
    assert "103682" in unit.numbers
    assert "5.0" in unit.numbers
    assert bundle.chunks[0].unit_ids == ("U0001",)


def test_source_bundle_keeps_table_rows_in_source_order(tmp_path: Path) -> None:
    source = tmp_path / "source_extract.md"
    source.write_text(
        "## 数据表\n\n| ID | 数值 |\n|---|---|\n| E01 | 10 |\n| E02 | 20 |\n\n下一段。\n",
        encoding="utf-8",
    )

    bundle = build_source_bundle(source)

    assert [unit.unit_id for unit in bundle.units] == ["U0001", "U0002"]
    assert bundle.units[0].kind == "table"
    assert bundle.units[0].locator == "数据表"
    assert bundle.units[0].numbers == ("10", "20")
    assert bundle.units[1].text == "下一段。"


def test_line_oriented_docx_extract_splits_paragraphs_but_keeps_tables(tmp_path: Path) -> None:
    source = tmp_path / "source_extract.md"
    source.write_text(
        "# DOCX 文本抽取稿\n\n"
        "## Paragraphs\n\n"
        "[1] (Normal) 第一段事实。\n"
        "[2] (Normal) 第二段事实。\n"
        "[3] (Heading 1) 第一章\n"
        "[4] (Normal) 标题下段落。\n\n"
        "## Tables\n\n"
        "### Table 1 (2 rows)\n\n"
        "指标 | 数值\n"
        "--- | ---\n"
        "E01 | 10\n"
        "E02 | 20\n",
        encoding="utf-8",
    )

    bundle = build_source_bundle(source)

    paragraph_units = [unit for unit in bundle.units if unit.locator.startswith("paragraph ")]
    assert [unit.locator for unit in paragraph_units] == [
        "paragraph 1",
        "paragraph 2",
        "paragraph 3",
        "paragraph 4",
    ]
    assert "[2]" not in paragraph_units[0].text
    table_units = [unit for unit in bundle.units if unit.kind == "table"]
    assert len(table_units) == 1
    assert "E01 | 10" in table_units[0].text
    assert "E02 | 20" in table_units[0].text


def test_source_bundle_is_stable_and_writes_machine_and_human_artifacts(tmp_path: Path) -> None:
    source = tmp_path / "source_extract.md"
    source.write_text("背景\n\n结论一。\n\n结论二。\n", encoding="utf-8")
    project = tmp_path / "project"
    paths = phase1_paths(project, "source_analysis")

    first = build_source_bundle(source)
    second = build_source_bundle(source)
    write_source_bundle(first, paths)

    assert first == second
    payload = json.loads(paths.source_bundle_json.read_text(encoding="utf-8"))
    assert payload["schema"] == "cyberppt.phase1_source_bundle.v1"
    assert "U0001" in paths.source_bundle_markdown.read_text(encoding="utf-8")
    assert (paths.chunks_dir / "chunk_001.json").exists()


def test_json_input_uses_markdown_sibling_when_present(tmp_path: Path) -> None:
    source_json = tmp_path / "source_extract.json"
    source_json.write_text(json.dumps({"ignored": True}), encoding="utf-8")
    source_md = tmp_path / "source_extract.md"
    source_md.write_text("## P3\nMarkdown truth。\n", encoding="utf-8")

    bundle = build_source_bundle(source_json)

    assert bundle.source_path.endswith("source_extract.md")
    assert "Markdown truth" in bundle.units[0].text
