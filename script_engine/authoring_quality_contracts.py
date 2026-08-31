"""Focused deterministic checks for Stage1 authoring quality floors.

Keep this module limited to mechanically decidable failures that are not already
covered by the broader AUTHOR / Full Copy / Onscreen contracts. It must not
encode generative author judgment or create a second content authority.
"""
from __future__ import annotations

import re
from typing import Any


_LABEL_SPLIT_RE = re.compile(r"[：:]", flags=re.UNICODE)
_BARE_QUANTIFIED_DETAIL_RE = re.compile(
    r"^(?:[~≈≃<>≤≥]|约|近|超|少于|多于|不低于|不高于|至少|至多)?\s*"
    r"\d+(?:\.\d+)?\s*"
    r"(?:%|％|家|个|项|类|次|人|户|套|亿元|万元|元|MW|GW|kW|kWh|GWh|TWh|TB|GB|天|小时|h)?"
    r"\s*(?:左右|以上|以下)?$",
    flags=re.IGNORECASE,
)
_DATE_ONLY_RE = re.compile(
    r"^(?:19|20)\d{2}(?:年(?:\d{1,2}月(?:\d{1,2}日)?)?|[./-]\d{1,2}(?:[./-]\d{1,2})?)?$"
)


def check_onscreen_numeric_context(final_script: dict[str, Any]) -> list[str]:
    """Reject visible numeric fragments that omit the measured business object.

    The check is intentionally conservative:
    - a semantic label such as ``覆盖率：80%`` supplies the object and passes;
    - date-only milestones pass because a year/date can be a legitimate roadmap marker;
    - normal prose containing a number passes;
    - only unlabeled, near-pure quantities such as ``80%`` / ``30家`` / ``3项`` fail.
    """

    issues: list[str] = []
    for index, slide in enumerate(final_script.get("slides") or []):
        if not isinstance(slide, dict) or slide.get("page_type") != "content":
            continue
        slide_id = slide.get("id") or f"#{index}"
        for module_index, module in enumerate(slide.get("onscreen") or []):
            if not isinstance(module, dict):
                continue
            lines: list[tuple[str, str]] = []
            text = module.get("text")
            if isinstance(text, str) and text.strip():
                lines.append(("text", text.strip()))
            lines.extend(
                (f"items[{item_index}]", item.strip())
                for item_index, item in enumerate(module.get("items") or [])
                if isinstance(item, str) and item.strip()
            )
            for field, line in lines:
                parts = _LABEL_SPLIT_RE.split(line, maxsplit=1)
                if len(parts) == 2 and parts[0].strip() and parts[1].strip():
                    continue
                compact = re.sub(r"\s+", "", line)
                if _DATE_ONLY_RE.fullmatch(compact):
                    continue
                if _BARE_QUANTIFIED_DETAIL_RE.fullmatch(compact):
                    issues.append(
                        f"ONSCREEN_NUMBER_WITHOUT_OBJECT: slides.{index} ({slide_id}).onscreen"
                        f"[{module_index}].{field}: '{line}' shows a quantity without the measured "
                        "business object; name what the number measures and why it matters"
                    )
    return issues


__all__ = ["check_onscreen_numeric_context"]
