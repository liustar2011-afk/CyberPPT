"""Pure helpers shared by ImageGen handoff rule domains."""

from __future__ import annotations

import re

from scripts.imagegen_pipeline.handoff.contracts import (
    NON_RENDERING_RELATION_LABELS,
    ONSCREEN_ASIDE_RE,
)


def _audience_facing_group_label(label: str) -> str:
    """Pure local equivalent of the script-contract authoring label cleanup."""

    value = str(label or "").strip()
    value = re.sub(
        r"^第\s*(?:[一二三四五六七八九十]+|\d+|[Xx])\s*行\s*[｜|:]\s*",
        "",
        value,
    )
    value = re.sub(r"(?:一|二|两|三|四|五|六|七|八|九|十|\d+)个层面$", "", value)
    value = re.sub(r"(控制链|权利对象)层面$", r"\1", value)
    if value == "四个维度分别选择":
        value = "交付维度选择"
    return value.strip(" ：:")


def _strip_authoring_group_marker(line: str) -> str:
    """Remove authoring-only row markers while preserving indentation."""

    raw = str(line or "")
    match = re.match(r"^(\s*)(.*)$", raw, flags=re.S)
    if not match:
        return raw
    indent, body = match.groups()
    cleaned = _audience_facing_group_label(body)
    return indent + cleaned if cleaned != body else raw


def _clean_onscreen_for_imagegen(text: str) -> str:
    """Keep theme bullets; strip boundary asides that dilute the page mission."""

    cleaned_lines: list[str] = []
    for raw in text.splitlines():
        # Row numbers/coordinates are authoring metadata, not audience copy.
        # Apply this before every compiler (including content-first) so stale
        # approved prompts cannot reintroduce markers such as ``第X行｜``.
        raw = _strip_authoring_group_marker(raw)
        relation_match = re.match(
            r"^\s*[-*•]?\s*(?P<label>[^：:\n]{2,14})[：:]",
            raw,
        )
        if relation_match and relation_match.group("label").strip() in NON_RENDERING_RELATION_LABELS:
            continue
        line = ONSCREEN_ASIDE_RE.sub("", raw)
        line = re.sub(r"[；;]\s*$", "", line.rstrip())
        line = re.sub(r"\s{2,}", " ", line)
        # Drop emptied bullets that only carried an aside.
        if re.fullmatch(r"\s*[-*•]?\s*", line or ""):
            continue
        cleaned_lines.append(line)
    return "\n".join(cleaned_lines).strip()


def _module_label(title: str) -> str:
    return re.sub(r"^\s*\d+\s*｜\s*", "", title).strip()
