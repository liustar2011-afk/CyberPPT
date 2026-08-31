from __future__ import annotations

import ast
from pathlib import Path

import script_engine.author_contracts as author_contracts
import script_engine.contracts as facade
import script_engine.delivery_contracts as delivery_contracts
import script_engine.full_copy_contracts as full_copy_contracts
import script_engine.lint_contracts as lint_contracts
import script_engine.onscreen_contracts as onscreen_contracts
import script_engine.schema_contracts as schema_contracts
import script_engine.source_trace_contracts as source_trace_contracts
import script_engine.structural_contracts as structural_contracts


ROOT = Path(__file__).resolve().parents[1]


def test_contracts_facade_routes_focused_domains() -> None:
    assert facade.load_json is schema_contracts.load_json
    assert facade.validate_final_script is schema_contracts.validate_final_script
    assert facade.validate_deck_plan is schema_contracts.validate_deck_plan
    assert facade.validate_foundation is schema_contracts.validate_foundation
    assert facade.collect_foundation_source_codes is source_trace_contracts.collect_foundation_source_codes
    assert facade.validate_source_refs_coverage is source_trace_contracts.validate_source_refs_coverage
    assert facade.load_banned_phrasing is lint_contracts.load_banned_phrasing
    assert facade.iter_final_script_text_fields is lint_contracts.iter_final_script_text_fields
    assert facade.lint_final_script is lint_contracts.lint_final_script
    assert facade.check_author_field_contract is author_contracts.check_author_field_contract
    assert facade.check_full_copy_structure is full_copy_contracts.check_full_copy_structure
    assert facade.check_full_copy_topic_semantics is full_copy_contracts.check_full_copy_topic_semantics
    assert facade.check_full_copy_parallel_subconclusions is full_copy_contracts.check_full_copy_parallel_subconclusions
    assert facade.check_onscreen_heading_semantics is onscreen_contracts.check_onscreen_heading_semantics
    assert facade.check_onscreen_detail_semantics is onscreen_contracts.check_onscreen_detail_semantics
    assert facade.check_onscreen_projection_structure is onscreen_contracts.check_onscreen_projection_structure
    assert facade.check_onscreen_hierarchy_punctuation is onscreen_contracts.check_onscreen_hierarchy_punctuation
    assert facade.check_onscreen_code_context is onscreen_contracts.check_onscreen_code_context
    assert facade.check_onscreen_core_alignment is onscreen_contracts.check_onscreen_core_alignment
    assert facade.check_speaker_notes_length is delivery_contracts.check_speaker_notes_length
    assert facade.check_declared_count is delivery_contracts.check_declared_count
    assert facade.check_onscreen_terminal_punctuation is delivery_contracts.check_onscreen_terminal_punctuation
    assert facade.check_onscreen_detail_length is delivery_contracts.check_onscreen_detail_length
    assert facade.outline_final_script is delivery_contracts.outline_final_script
    assert facade.check_onscreen_structure is structural_contracts.check_onscreen_structure
    assert facade.check_full_copy_duplication is structural_contracts.check_full_copy_duplication


def test_contracts_facade_has_no_legacy_runtime_fallback() -> None:
    path = ROOT / "script_engine" / "contracts.py"
    source = path.read_text(encoding="utf-8")
    tree = ast.parse(source, filename=str(path))
    functions = [node.name for node in tree.body if isinstance(node, ast.FunctionDef)]
    classes = [node.name for node in tree.body if isinstance(node, ast.ClassDef)]
    imported_modules = {
        alias.name
        for node in tree.body
        if isinstance(node, ast.ImportFrom)
        for alias in node.names
    }
    assert functions == []
    assert classes == []
    assert "contract_rules" not in imported_modules
    assert "vars(" not in source
    assert path.stat().st_size < 4_000
