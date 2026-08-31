"""Stable facade for Script Engine delivery contracts.

Focused domains are exported from dedicated modules; remaining legacy rule
implementation stays behind :mod:`script_engine.contract_rules` while it is
split incrementally.
"""
from __future__ import annotations

from . import author_contracts as _author
from . import contract_rules as _impl
from . import delivery_contracts as _delivery
from . import lint_contracts as _lint
from . import schema_contracts as _schema
from . import source_trace_contracts as _source_trace
from . import structural_contracts as _structural

for _name, _value in vars(_impl).items():
    if not _name.startswith("__"):
        globals()[_name] = _value

_FOCUSED_EXPORTS = {
    "ROOT": _schema.ROOT,
    "CONTRACTS": _schema.CONTRACTS,
    "load_json": _schema.load_json,
    "load_schema": _schema.load_schema,
    "validate_payload": _schema.validate_payload,
    "validate_final_script": _schema.validate_final_script,
    "validate_deck_plan": _schema.validate_deck_plan,
    "validate_foundation": _schema.validate_foundation,
    "FOUNDATION_CITABLE_KEYS": _source_trace.FOUNDATION_CITABLE_KEYS,
    "collect_foundation_source_codes": _source_trace.collect_foundation_source_codes,
    "validate_source_refs_coverage": _source_trace.validate_source_refs_coverage,
    "BANNED_PHRASING_PATH": _lint.BANNED_PHRASING_PATH,
    "load_banned_phrasing": _lint.load_banned_phrasing,
    "iter_final_script_text_fields": _lint.iter_final_script_text_fields,
    "lint_final_script": _lint.lint_final_script,
    "check_author_field_contract": _author.check_author_field_contract,
    "SPEAKER_NOTES_MIN_CHARS": _delivery.SPEAKER_NOTES_MIN_CHARS,
    "ONSCREEN_DETAIL_PHRASE_MAX_CHARS": _delivery.ONSCREEN_DETAIL_PHRASE_MAX_CHARS,
    "ONSCREEN_COMPLETE_PROPOSITION_MAX_CHARS": _delivery.ONSCREEN_COMPLETE_PROPOSITION_MAX_CHARS,
    "check_speaker_notes_length": _delivery.check_speaker_notes_length,
    "check_declared_count": _delivery.check_declared_count,
    "check_onscreen_terminal_punctuation": _delivery.check_onscreen_terminal_punctuation,
    "check_onscreen_detail_length": _delivery.check_onscreen_detail_length,
    "outline_final_script": _delivery.outline_final_script,
    "check_onscreen_structure": _structural.check_onscreen_structure,
    "check_full_copy_duplication": _structural.check_full_copy_duplication,
}
globals().update(_FOCUSED_EXPORTS)

__all__ = sorted(
    {name for name in vars(_impl) if not name.startswith("__")}
    | set(_FOCUSED_EXPORTS)
)
