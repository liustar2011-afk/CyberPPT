"""Shared Stage 01 rules for deterministic on-screen text normalization."""

from __future__ import annotations

import unicodedata


def strip_terminal_punctuation(value: str) -> str:
    """Remove terminal punctuation/symbols without changing internal copy."""
    result = value.rstrip()
    while result and unicodedata.category(result[-1])[0] in {"P", "S"}:
        result = result[:-1].rstrip()
    return result


def normalize_detail_lines(text: str) -> str:
    """Strip terminal punctuation from detail lines in each visible group.

    The first non-empty line in a blank-line-delimited group is its label or
    heading; subsequent lines are detail items. Their internal punctuation is
    preserved, while terminal punctuation is removed for presentation.
    """
    groups = [group for group in str(text).strip().split("\n\n") if group.strip()]
    rendered_groups: list[str] = []
    for group in groups:
        lines = [line.rstrip() for line in group.splitlines() if line.strip()]
        if not lines:
            continue
        rendered = [lines[0]]
        rendered.extend(strip_terminal_punctuation(line) for line in lines[1:])
        rendered_groups.append("\n".join(rendered))
    return "\n\n".join(rendered_groups)
