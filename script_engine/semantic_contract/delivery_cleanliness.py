"""Deterministic delivery-cleanliness checks for Final Script output."""

from __future__ import annotations

import re
from typing import Any

from .foundation_index import FoundationIndex
from .models import SemanticDiagnostic


_STRUCTURAL_METADATA_PATTERNS = (
    re.compile(r"^目\s*录$"),
    re.compile(r"^工作摘要$"),
    re.compile(r"^[（(]?(?:重构稿\s*)?V\d+(?:\.\d+)*[^。；]*[）)]?$", re.I),
    re.compile(r"^\d{4}年\d{1,2}月(?:\d{1,2}日)?$"),
    re.compile(r"^[一二三四五六七八九十]+、[^。；]{2,40}$"),
    re.compile(r"^附件[一二三四五六七八九十\d]+(?:[：:].*)?$"),
)


def _text(value: object) -> str:
    return str(value or "").strip()


def _page_id(page: dict[str, Any]) -> str:
    return _text(page.get("id") or page.get("page_id"))


def _record_text(payload: dict[str, Any]) -> str:
    """Mirror the legacy Foundation surface without inferring new semantics."""

    parts: list[str] = []
    for key in (
        "statement",
        "claim",
        "definition",
        "context",
        "strength",
        "term",
        "relation",
        "value",
        "unit",
    ):
        value = payload.get(key)
        if isinstance(value, str):
            parts.append(value)
    parts.extend(
        _text(unit.get("text"))
        for unit in payload.get("semantic_units") or []
        if isinstance(unit, dict) and _text(unit.get("text"))
    )
    return " ".join(parts)


def _looks_like_structural_metadata(value: str) -> bool:
    normalized = re.sub(r"\s+", " ", _text(value)).strip(" ；;。")
    return bool(normalized) and any(
        pattern.fullmatch(normalized) for pattern in _STRUCTURAL_METADATA_PATTERNS
    )


def _module_lines(module: dict[str, Any]) -> list[tuple[str, str]]:
    lines: list[tuple[str, str]] = []
    text = module.get("text")
    if isinstance(text, str) and text.strip():
        lines.append(("text", text.strip()))
    for item_index, item in enumerate(module.get("items") or []):
        if isinstance(item, str) and item.strip():
            lines.append((f"items[{item_index}]", item.strip()))
        elif isinstance(item, dict):
            value = item.get("text")
            if isinstance(value, str) and value.strip():
                lines.append((f"items[{item_index}]", value.strip()))
    return lines


def collect_delivery_cleanliness_diagnostics(
    final_script: dict[str, Any],
    plan: dict[str, Any] | None,
    foundation: dict[str, Any] | None,
) -> list[SemanticDiagnostic]:
    """Reject objective document/format leakage from source material into output."""

    plan_payload = plan if isinstance(plan, dict) else {}
    pages = {
        _page_id(page): page
        for page in plan_payload.get("pages") or []
        if isinstance(page, dict) and _page_id(page)
    }
    index = FoundationIndex(foundation)
    delivery_mode = _text(
        (final_script.get("deck") or {}).get("delivery_mode")
        if isinstance(final_script.get("deck"), dict)
        else ""
    ) or _text(plan_payload.get("delivery_mode")) or "self_read"

    diagnostics: list[SemanticDiagnostic] = []
    for slide in final_script.get("slides") or []:
        if not isinstance(slide, dict) or slide.get("page_type") != "content":
            continue
        slide_id = _text(slide.get("id"))
        page = pages.get(slide_id)
        if not isinstance(page, dict):
            continue

        full_copy = _text(slide.get("full_copy"))
        metadata_refs: list[str] = []
        for ref in page.get("source_refs") or []:
            if not isinstance(ref, str) or not ref.strip():
                continue
            record = index.record(ref)
            if record is None:
                continue
            source_text = _record_text(record.payload).strip()
            if (
                source_text
                and _looks_like_structural_metadata(source_text)
                and source_text in full_copy
            ):
                metadata_refs.append(ref)
        if metadata_refs:
            diagnostics.append(
                SemanticDiagnostic(
                    code="AUTHOR_STRUCTURAL_METADATA_LEAK",
                    message=(
                        "full_copy contains document front matter, TOC entries, or section "
                        f"labels as page prose: {metadata_refs}"
                    ),
                    slide_id=slide_id,
                    target="full_copy",
                    severity="blocking",
                    evidence_refs=tuple(metadata_refs),
                    relation="delivery_cleanliness",
                )
            )

        contract = page.get("onscreen_contract")
        expression_mode = (
            _text(contract.get("expression_mode")) if isinstance(contract, dict) else ""
        )
        if delivery_mode != "self_read" or expression_mode != "phrase_led":
            continue
        for module_index, module in enumerate(slide.get("onscreen") or []):
            if not isinstance(module, dict):
                continue
            module_id = _text(module.get("id"))
            heading = _text(module.get("heading")) or "?"
            for target, line in _module_lines(module):
                if "|" not in line:
                    continue
                diagnostics.append(
                    SemanticDiagnostic(
                        code="AUTHOR_ONSCREEN_TABLE_FRAGMENT",
                        message=(
                            f"module {heading!r} contains a raw table row: {line!r}"
                        ),
                        slide_id=slide_id,
                        module_id=module_id,
                        target=f"onscreen[{module_index}].{target}",
                        severity="blocking",
                        relation="delivery_cleanliness",
                    )
                )

    return diagnostics


__all__ = ["collect_delivery_cleanliness_diagnostics"]
