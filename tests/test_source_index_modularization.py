from __future__ import annotations

import ast
from pathlib import Path

import script_engine.source_index as source_index
import script_engine.source_index_legacy as source_index_legacy
import script_engine.source_index_validation as source_index_validation
import script_engine.source_reading as source_reading


ROOT = Path(__file__).resolve().parents[1]


def test_source_index_routes_reading_strategy_through_focused_module() -> None:
    assert source_index.estimate_reading_load is source_reading.estimate_reading_load
    assert source_index.recommend_reading_mode is source_reading.recommend_reading_mode
    assert source_index.default_reading_strategy is source_reading.default_reading_strategy

    sources = [{"source_id": "SRC-1", "path": "sample.md", "sha256": "abc"}]
    headings = [{"heading_id": "H-1", "title": "标题", "level": 1}]
    units = [
        {
            "unit_id": "SU-1",
            "source_id": "SRC-1",
            "kind": "heading",
            "text": "标题",
            "heading_id": "H-1",
            "locator": {},
        },
        {
            "unit_id": "SU-2",
            "source_id": "SRC-1",
            "kind": "paragraph",
            "text": "项目应当明确责任边界和实施计划。",
            "heading_id": "H-1",
            "locator": {},
        },
    ]
    payload = source_index.build_source_index_v2(
        sources=sources,
        headings=headings,
        units=units,
    )
    expected_load = source_reading.estimate_reading_load(units, sources)
    expected_recommendation = source_reading.recommend_reading_mode(expected_load)
    assert payload["reading_load"] == expected_load
    assert payload["reading_recommendation"] == expected_recommendation
    assert payload["reading_strategy"] == source_reading.default_reading_strategy(
        expected_recommendation,
        headings,
        units,
    )


def test_source_index_routes_legacy_parser_through_focused_module() -> None:
    assert source_index.chinese_number is source_index_legacy.chinese_number
    assert source_index.build_source_index is source_index_legacy.build_source_index
    assert source_index.build_source_index_file is source_index_legacy.build_source_index_file
    assert source_index.PARAGRAPH_RE is source_index_legacy.PARAGRAPH_RE
    assert source_index.CHAPTER_RE is source_index_legacy.CHAPTER_RE
    assert source_index.SECTION_RE is source_index_legacy.SECTION_RE
    assert source_index.SUBSECTION_RE is source_index_legacy.SUBSECTION_RE
    assert source_index.APPENDIX_RE is source_index_legacy.APPENDIX_RE
    assert source_index.TOC_ENTRY_RE is source_index_legacy.TOC_ENTRY_RE
    assert source_index.DIGITS is source_index_legacy.DIGITS

    extract = "\n".join(
        [
            "[/body/p[1]] 第一章 总体要求",
            "[/body/p[2]] 一、 建设目标",
            "[/body/p[3]] 项目应当明确责任边界。",
        ]
    )
    assert source_index.build_source_index(extract, "sample.docx") == (
        source_index_legacy.build_source_index(extract, "sample.docx")
    )


def test_source_index_routes_v2_validation_through_focused_module() -> None:
    assert source_index.validate_reading_strategy is source_index_validation.validate_reading_strategy
    assert source_index.validate_foundation_source_bindings is source_index_validation.validate_foundation_source_bindings
    assert source_index.validate_foundation_detail_atomicity is source_index_validation.validate_foundation_detail_atomicity
    assert source_index.validate_script_foundation_against_index is source_index_validation.validate_script_foundation_against_index
    assert source_index._source_unit_refs is source_index_validation._source_unit_refs
    assert source_index._detail_obligation_count is source_index_validation._detail_obligation_count
    assert source_index._detail_overlap is source_index_validation._detail_overlap
    assert source_index._DETAIL_SENTENCE_SPLIT_RE is source_index_validation._DETAIL_SENTENCE_SPLIT_RE
    assert source_index._DETAIL_MEANINGFUL_RE is source_index_validation._DETAIL_MEANINGFUL_RE


def test_source_index_no_longer_owns_extracted_implementations() -> None:
    path = ROOT / "script_engine" / "source_index.py"
    source = path.read_text(encoding="utf-8")
    tree = ast.parse(source, filename=str(path))
    function_names = {
        node.name
        for node in tree.body
        if isinstance(node, ast.FunctionDef)
    }
    imported_names = {
        alias.name
        for node in tree.body
        if isinstance(node, ast.Import)
        for alias in node.names
    }
    imported_modules = {
        node.module
        for node in tree.body
        if isinstance(node, ast.ImportFrom) and node.module
    }

    assert "estimate_reading_load" not in function_names
    assert "recommend_reading_mode" not in function_names
    assert "default_reading_strategy" not in function_names
    assert "_critical_deep_read_unit_ids" not in function_names
    assert "chinese_number" not in function_names
    assert "_ensure" not in function_names
    assert "_is_toc_entry" not in function_names
    assert "build_source_index" not in function_names
    assert "build_source_index_file" not in function_names
    assert "_source_unit_refs" not in function_names
    assert "validate_reading_strategy" not in function_names
    assert "validate_foundation_source_bindings" not in function_names
    assert "_detail_obligation_count" not in function_names
    assert "_detail_overlap" not in function_names
    assert "validate_foundation_detail_atomicity" not in function_names
    assert "validate_script_foundation_against_index" not in function_names
    assert "math" not in imported_names
    assert "re" not in imported_names
    assert "source_index_validation" in imported_modules
    assert path.stat().st_size < 10_000
