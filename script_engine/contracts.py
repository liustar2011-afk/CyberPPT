"""Stable facade for Script Engine delivery contracts.

Focused domains are exported from dedicated modules; remaining legacy rule
implementation stays behind :mod:`script_engine.contract_rules` while it is
split incrementally.
"""
from __future__ import annotations

from . import contract_rules as _impl
from . import schema_contracts as _schema
from . import source_trace_contracts as _source_trace

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
}
globals().update(_FOCUSED_EXPORTS)

__all__ = sorted(
    {name for name in vars(_impl) if not name.startswith("__")}
    | set(_FOCUSED_EXPORTS)
)
