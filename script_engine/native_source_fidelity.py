"""Deterministic Final Script fidelity checks against exact native source units."""
from __future__ import annotations

import re
from typing import Any, Mapping


_NUMBER_RE = re.compile(
    r"\d+(?:\.\d+)?(?:%|％|年|月|日|亿元|万元|亿|万|项|类|级|个|家|人|台|套|次|倍|MW|GW|kW|kWh|TWh)?"
)
_QUALIFIERS = (
    "不少于",
    "不低于",
    "不超过",
    "不高于",
    "截至",
    "至少",
    "至多",
    "超过",
    "约",
    "近",
)
_ACHIEVED_RE = re.compile(r"已(?:完成|形成|实现|建立|具备|明确|建成|上线|投入|发布|通过|纳入)")
_TENTATIVE_RE = re.compile(r"计划|拟|预计|可能|有望|可望")
_OBLIGATION_RE = re.compile(r"必须|应当|不得|严禁")
_STRENGTH_RE = re.compile(r"必然|全面|显著")


def _text(value: object) -> str:
    return str(value or "").strip()


def _slide_text_fields(slide: Mapping[str, Any]) -> list[tuple[str, str]]:
    fields: list[tuple[str, str]] = []
    for name in (
        "title",
        "subtitle",
        "core_message",
        "full_copy",
        "visual_thesis",
        "speaker_notes",
    ):
        value = slide.get(name)
        if isinstance(value, str) and value.strip():
            fields.append((name, value.strip()))

    argument = slide.get("argument")
    if isinstance(argument, Mapping):
        for index, value in enumerate(argument.get("chain") or []):
            if isinstance(value, str) and value.strip():
                fields.append((f"argument.chain[{index}]", value.strip()))

    for module_index, module in enumerate(slide.get("onscreen") or []):
        if not isinstance(module, Mapping):
            continue
        for name in ("heading", "text"):
            value = module.get(name)
            if isinstance(value, str) and value.strip():
                fields.append((f"onscreen[{module_index}].{name}", value.strip()))
        for item_index, item in enumerate(module.get("items") or []):
            if isinstance(item, str) and item.strip():
                fields.append((f"onscreen[{module_index}].items[{item_index}]", item.strip()))
            elif isinstance(item, Mapping):
                value = item.get("text")
                if isinstance(value, str) and value.strip():
                    fields.append((f"onscreen[{module_index}].items[{item_index}].text", value.strip()))

    return fields


def exact_source_text(packet: Mapping[str, Any]) -> str:
    """Return exact native text once per resolved unit, preserving packet order."""

    seen: set[str] = set()
    parts: list[str] = []
    for evidence in packet.get("evidence") or []:
        if not isinstance(evidence, Mapping):
            continue
        for unit in evidence.get("exact_source_units") or []:
            if not isinstance(unit, Mapping):
                continue
            unit_id = _text(unit.get("unit_id"))
            text = _text(unit.get("text"))
            if not unit_id or not text or unit_id in seen:
                continue
            seen.add(unit_id)
            parts.append(text)
    return "\n".join(parts)


def _qualified_numbers(text: str) -> dict[str, set[str]]:
    """Map numeric tokens to source qualifiers occurring immediately before them."""

    result: dict[str, set[str]] = {}
    for match in _NUMBER_RE.finditer(text):
        token = match.group(0)
        prefix = text[max(0, match.start() - 16):match.start()]
        qualifiers = {qualifier for qualifier in _QUALIFIERS if qualifier in prefix}
        if qualifiers:
            result.setdefault(token, set()).update(qualifiers)
    return result


def _number_has_qualifier(text: str, token: str, qualifier: str) -> bool:
    for match in re.finditer(re.escape(token), text):
        prefix = text[max(0, match.start() - 16):match.start()]
        if qualifier in prefix:
            return True
    return False


def native_source_fidelity_issues(
    final_script: Mapping[str, Any],
    packets_by_page: Mapping[str, Mapping[str, Any]],
) -> list[str]:
    """Audit high-risk factual drift against exact per-page native source text."""

    issues: list[str] = []

    for slide in final_script.get("slides") or []:
        if not isinstance(slide, Mapping) or _text(slide.get("page_type")) != "content":
            continue
        page_id = _text(slide.get("id")) or "<unknown>"
        packet = packets_by_page.get(page_id)
        if not isinstance(packet, Mapping):
            issues.append(f"NATIVE_SOURCE_PACKET_MISSING: {page_id}")
            continue

        source_text = exact_source_text(packet)
        if not source_text:
            issues.append(f"NATIVE_SOURCE_TEXT_MISSING: {page_id}")
            continue

        source_numbers = set(_NUMBER_RE.findall(source_text))
        source_qualified_numbers = _qualified_numbers(source_text)
        source_has_achieved = bool(_ACHIEVED_RE.search(source_text))
        source_has_tentative = bool(_TENTATIVE_RE.search(source_text))
        source_has_obligation = bool(_OBLIGATION_RE.search(source_text))
        source_strength = set(_STRENGTH_RE.findall(source_text))

        for field, text in _slide_text_fields(slide):
            added_numbers = sorted(set(_NUMBER_RE.findall(text)) - source_numbers)
            if added_numbers:
                issues.append(
                    f"NATIVE_NUMBER_OR_DATE_ADDED: {page_id}.{field}: {added_numbers}"
                )

            for token in sorted(set(_NUMBER_RE.findall(text)) & set(source_qualified_numbers)):
                for qualifier in sorted(source_qualified_numbers[token]):
                    if not _number_has_qualifier(text, token, qualifier):
                        issues.append(
                            "NATIVE_NUMERIC_QUALIFIER_DROPPED: "
                            f"{page_id}.{field}: source qualifier '{qualifier}' for '{token}' is missing"
                        )

            achieved = sorted(set(_ACHIEVED_RE.findall(text)))
            if achieved and not source_has_achieved:
                reason = "source is tentative" if source_has_tentative else "source has no achieved-state marker"
                issues.append(
                    f"NATIVE_STATUS_PROMOTED: {page_id}.{field}: {achieved}; {reason}"
                )

            obligations = sorted(set(_OBLIGATION_RE.findall(text)))
            if obligations and not source_has_obligation:
                issues.append(
                    f"NATIVE_MODALITY_PROMOTED: {page_id}.{field}: {obligations}"
                )

            added_strength = sorted(set(_STRENGTH_RE.findall(text)) - source_strength)
            if added_strength:
                issues.append(
                    f"NATIVE_CLAIM_STRENGTH_PROMOTED: {page_id}.{field}: {added_strength}"
                )

    return list(dict.fromkeys(issues))


__all__ = ["exact_source_text", "native_source_fidelity_issues"]
