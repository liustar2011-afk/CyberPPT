"""Faithful-mode checks for author-created semantic relations."""
from __future__ import annotations

import re
from typing import Any

from .common import _item_text


_RELATION_PROMOTION_PATTERNS = (
    ("因此", re.compile(r"因此")),
    ("因而", re.compile(r"因而")),
    ("从而", re.compile(r"从而")),
    ("意味着", re.compile(r"意味着")),
    ("决定了", re.compile(r"决定了")),
    ("导致", re.compile(r"导致")),
    ("只有…才/才能", re.compile(r"只有[^。；\n]{0,50}(?:才|才能)")),
    ("必须…才能/方可", re.compile(r"必须[^。；\n]{0,50}(?:才能|方可)")),
    (
        "需要在…条件/节点下形成/实现/完成/推进/建设",
        re.compile(
            r"需要在[^。；\n]{0,40}(?:条件|节点|要求|背景)?下"
            r"[^。；\n]{0,40}(?:形成|实现|完成|推进|建设)"
        ),
    ),
    ("必然", re.compile(r"必然(?:形成|实现|导致|带来|推动|提升)")),
)


def faithful_relation_promotion_issues(
    slide: dict[str, Any], evidence: list[dict[str, Any]]
) -> list[str]:
    """Reject unsupported causal or necessity language in faithful mode."""

    source_text = "\n".join(_item_text(item) for item in evidence)
    fields: list[tuple[str, str]] = []
    for name in ("title", "core_message", "full_copy", "visual_thesis", "speaker_notes"):
        value = slide.get(name)
        if isinstance(value, str) and value.strip():
            fields.append((name, value))
    for index, module in enumerate(slide.get("onscreen") or []):
        if not isinstance(module, dict):
            continue
        for name in ("heading", "text"):
            value = module.get(name)
            if isinstance(value, str) and value.strip():
                fields.append((f"onscreen[{index}].{name}", value))
        for item_index, value in enumerate(module.get("items") or []):
            if isinstance(value, str) and value.strip():
                fields.append((f"onscreen[{index}].items[{item_index}]", value))
    for index, relation in enumerate(slide.get("relationships") or []):
        if not isinstance(relation, dict):
            continue
        value = relation.get("relation")
        if isinstance(value, str) and value.strip():
            fields.append((f"relationships[{index}].relation", value))

    issues: list[str] = []
    for field, text in fields:
        introduced = sorted(
            label
            for label, pattern in _RELATION_PROMOTION_PATTERNS
            if pattern.search(text) and not pattern.search(source_text)
        )
        if introduced:
            issues.append(
                "FAITHFUL_RELATION_PROMOTED: "
                f"{field} introduces unsupported causal/necessity marker(s) {introduced}; "
                "remove the composed relation or explicitly authorize analytical mode"
            )
    return issues


__all__ = ["faithful_relation_promotion_issues"]
