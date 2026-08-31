"""Compatibility facade for composed trace and Critic-priority helpers."""
from __future__ import annotations

from .composed_trace_core import (
    CJK,
    _SOURCE_TEXT_KEYS,
    _FINAL_SCALAR_FIELDS,
    _specific_identifiers,
    _source_strings,
    cjk_ngrams,
    latin_tokens,
    numbers,
    foundation_source_surface,
    final_script_lines,
    trace_composed,
    hard_finding_messages,
)
from .composed_trace_priorities import _external_check_page_ids, critic_priorities


__all__ = [
    "cjk_ngrams",
    "latin_tokens",
    "numbers",
    "foundation_source_surface",
    "final_script_lines",
    "trace_composed",
    "critic_priorities",
    "hard_finding_messages",
]
