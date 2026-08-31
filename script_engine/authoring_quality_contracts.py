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
_ROADMAP_PATTERNS = frozenset({"roadmap", "pyramid-roadmap", "governance-roadmap"})
_ROADMAP_TRIGGER_RE = re.compile(
    r"(?:19|20)\d{2}(?:年|[./-]\d{1,2})?"
    r"|(?:第?[一二三四1-4]季度|Q[1-4]|上半年|下半年)"
    r"|(?:进入条件|触发条件|启动条件|前提)"
    r"|(?:完成|达到|具备|通过).{1,24}后",
    flags=re.IGNORECASE,
)
_ROADMAP_TRIGGER_ONLY_PREFIX_RE = re.compile(
    r"^(?:进入条件|触发条件|启动条件|前提|时间|时间节点|节点)\s*[：:]"
)
_ROADMAP_NEW_STATE_RE = re.compile(
    r"新状态\s*[：:]"
    r"|(?:形成|达到|实现|具备|建成|上线|固化|完成).{1,30}"
    r"|进入.{0,10}(?:试运行|运行|应用|常态)"
    r"|可(?:复用|比较|追溯|校核|验收|运行|使用|调用|复制)"
)


def _module_lines(module: dict[str, Any]) -> list[str]:
    lines: list[str] = []
    for key in ("heading", "text"):
        value = module.get(key)
        if isinstance(value, str) and value.strip():
            lines.append(value.strip())
    lines.extend(
        item.strip()
        for item in module.get("items") or []
        if isinstance(item, str) and item.strip()
    )
    return lines


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


def check_roadmap_completeness(final_script: dict[str, Any]) -> list[str]:
    """Require explicit roadmap pages to expose trigger/time and newly reached state.

    Only patterns whose declared name is literally roadmap-oriented are checked. Generic
    progression pages remain under AUTHOR judgment so this deterministic floor does not
    force every directed page into a staged delivery plan.
    """

    issues: list[str] = []
    for index, slide in enumerate(final_script.get("slides") or []):
        if not isinstance(slide, dict) or slide.get("page_type") != "content":
            continue
        argument = slide.get("argument")
        if not isinstance(argument, dict):
            continue
        pattern = str(argument.get("pattern") or "").strip().lower()
        if pattern not in _ROADMAP_PATTERNS:
            continue

        slide_id = slide.get("id") or f"#{index}"
        modules = [module for module in slide.get("onscreen") or [] if isinstance(module, dict)]
        if len(modules) < 2:
            issues.append(
                f"ROADMAP_STAGE_LAYER_MISSING: slides.{index} ({slide_id}).onscreen: roadmap pages "
                "must expose at least two visible stages with their conditions and reached states"
            )

        for module_index, module in enumerate(modules):
            lines = _module_lines(module)
            combined = " ".join(lines)
            if not _ROADMAP_TRIGGER_RE.search(combined):
                issues.append(
                    f"ROADMAP_TRIGGER_MISSING: slides.{index} ({slide_id}).onscreen[{module_index}]: "
                    "the stage has no visible time signal or entry/trigger condition"
                )

            state_lines = [
                line for line in lines if not _ROADMAP_TRIGGER_ONLY_PREFIX_RE.search(line)
            ]
            if not _ROADMAP_NEW_STATE_RE.search(" ".join(state_lines)):
                issues.append(
                    f"ROADMAP_NEW_STATE_MISSING: slides.{index} ({slide_id}).onscreen[{module_index}]: "
                    "the stage names activity but does not state the newly reached, verifiable state"
                )
    return issues


__all__ = ["check_onscreen_numeric_context", "check_roadmap_completeness"]
