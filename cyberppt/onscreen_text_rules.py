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
    """Strip terminal punctuation from label-phrase detail lines in each group.

    The first non-empty line in a blank-line-delimited group is its label or
    heading; subsequent lines are detail items. Only ``label：phrase`` style
    detail lines have their terminal punctuation removed. A line without a
    label separator is an independent boundary sentence, not a detail phrase
    -- its terminal period is the very signal the parser and the onscreen
    hierarchy convention use to tell a boundary sentence apart from a bare
    module title, so it must stay untouched.
    """
    raw_lines = str(text).splitlines()
    while raw_lines and not raw_lines[0].strip():
        raw_lines.pop(0)
    while raw_lines and not raw_lines[-1].strip():
        raw_lines.pop()
    groups = [
        group for group in "\n".join(raw_lines).split("\n\n") if group.strip()
    ]
    rendered_groups: list[str] = []
    for group in groups:
        lines = [line.rstrip() for line in group.splitlines() if line.strip()]
        if not lines:
            continue
        rendered = [lines[0]]
        rendered.extend(
            strip_terminal_punctuation(line) if ("：" in line or ":" in line) else line
            for line in lines[1:]
        )
        rendered_groups.append("\n".join(rendered))
    return "\n\n".join(rendered_groups)
