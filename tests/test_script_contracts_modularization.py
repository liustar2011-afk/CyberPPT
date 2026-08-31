from __future__ import annotations

import ast
from pathlib import Path

import script_engine.contract_rules as implementation
import script_engine.contracts as facade
import script_engine.delivery_contracts as delivery_contracts
import script_engine.lint_contracts as lint_contracts
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
    assert facade.check_speaker_notes_length is delivery_contracts.check_speaker_notes_length
    assert facade.check_declared_count is delivery_contracts.check_declared_count
    assert facade.check_onscreen_terminal_punctuation is delivery_contracts.check_onscreen_terminal_punctuation
    assert facade.check_onscreen_detail_length is delivery_contracts.check_onscreen_detail_length
    assert facade.outline_final_script is delivery_contracts.outline_final_script
    assert facade.check_onscreen_structure is structural_contracts.check_onscreen_structure
    assert facade.check_full_copy_duplication is structural_contracts.check_full_copy_duplication
    assert facade.load_banned_phrasing is lint_contracts.load_banned_phrasing
    assert facade.iter_final_script_text_fields is lint_contracts.iter_final_script_text_fields
    assert facade.lint_final_script is lint_contracts.lint_final_script


def test_contracts_facade_keeps_remaining_rules_compatible() -> None:
    assert facade.check_author_field_contract is implementation.check_author_field_contract
    assert facade.check_full_copy_structure is implementation.check_full_copy_structure
    assert facade.check_onscreen_heading_semantics is implementation.check_onscreen_heading_semantics


def test_contracts_facade_contains_no_rule_implementation() -> None:
    path = ROOT / "script_engine" / "contracts.py"
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    functions = [node.name for node in tree.body if isinstance(node, ast.FunctionDef)]
    classes = [node.name for node in tree.body if isinstance(node, ast.ClassDef)]
    assert functions == []
    assert classes == []
    assert path.stat().st_size < 3_000
