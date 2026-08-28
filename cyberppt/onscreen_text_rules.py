"""Shared Stage 01 rules for deterministic on-screen text normalization."""

from __future__ import annotations

import re
import unicodedata


_VISIBLE_CHAR_RE = re.compile(r"[一-鿿A-Za-z0-9]")

_PROPOSITION_PREDICATE_RE = re.compile(
    r"(?:是|为|由|包括|包含|涵盖|覆盖|形成|完成|建立|实现|支撑|用于|"
    r"承担|负责|明确|开展|推进|达到|进入|保持|具备|面向|聚焦|构成|"
    r"衔接|检验|转化|提供|解决|适用|存在|不足|滞后|确定|规定|承载|"
    r"组织|分工|映射|参与|协调|连接|规范|统一|促进|满足|对应|形成)"
)


def strip_terminal_punctuation(value: str) -> str:
    """Remove terminal punctuation/symbols without changing internal copy."""
    result = value.rstrip()
    while result and unicodedata.category(result[-1])[0] in {"P", "S"}:
        result = result[:-1].rstrip()
    return result


def is_readable_onscreen_proposition(
    value: str,
    *,
    min_chars: int = 16,
    max_chars: int = 90,
) -> bool:
    """Recognize one compact business proposition independently of punctuation.

    The check is deliberately narrow and advisory. It distinguishes normal
    sentence-like copy from labelled detail fragments while leaving final
    reading quality to AUTHOR/Critic judgment.
    """
    text = str(value or "").strip()
    if not text or re.search(r"[：:]", text):
        return False
    chars = len(_VISIBLE_CHAR_RE.findall(text))
    return min_chars <= chars <= max_chars and bool(
        _PROPOSITION_PREDICATE_RE.search(text)
    )


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
