"""High-confidence voice checks for formal internal-report authoring.

Business vocabulary is deliberately outside this module's concern. Customer,
market, transaction, value, growth and commercialisation language can all be
valid in a central-enterprise internal report. The checks below only identify
an external adviser speaking to the organisation or explicitly describing an
outside consulting viewpoint.
"""
from __future__ import annotations

import re
from typing import Any, Iterable


INTERNAL_REPORT_SCOPES = {"", "internal", "mixed", "unspecified"}

_CONSULTANT_VOICE_RULES: tuple[tuple[str, re.Pattern[str]], ...] = (
    (
        "addresses the organisation as an external adviser",
        re.compile(r"(?:我们)?建议贵(?:司|单位|公司|集团)"),
    ),
    (
        "promises assistance to the organisation from an external position",
        re.compile(r"(?:帮助|助力)贵(?:司|单位|公司|集团)"),
    ),
    (
        "declares an external consulting viewpoint",
        re.compile(r"(?:从|站在)(?:外部)?(?:咨询|顾问)(?:视角|角度|立场)(?:看|来看)?"),
    ),
    (
        "declares an external consultant identity",
        re.compile(r"作为(?:外部)?(?:咨询|顾问)(?:机构|团队|专家)?"),
    ),
    (
        "uses audience-addressed promotional narration",
        re.compile(r"(?:带您|带领您)(?:了解|看清|洞察|解锁|发现)"),
    ),
)


def is_internal_report_scope(plan: dict[str, Any]) -> bool:
    return str(plan.get("audience_scope") or "").strip().lower() in INTERNAL_REPORT_SCOPES


def consultant_voice_hits(text: str) -> list[tuple[str, str]]:
    hits: list[tuple[str, str]] = []
    for description, pattern in _CONSULTANT_VOICE_RULES:
        match = pattern.search(text)
        if match:
            hits.append((description, match.group(0)))
    return hits


def _nested_strings(value: object, prefix: str) -> Iterable[tuple[str, str]]:
    if isinstance(value, str) and value.strip():
        yield prefix, value.strip()
    elif isinstance(value, list):
        for index, item in enumerate(value):
            yield from _nested_strings(item, f"{prefix}.{index}")
    elif isinstance(value, dict):
        for key, item in value.items():
            yield from _nested_strings(item, f"{prefix}.{key}")


def page_text_fields(page: dict[str, Any]) -> Iterable[tuple[str, str]]:
    for field in ("title", "question", "message", "logic", "next"):
        value = page.get(field)
        if isinstance(value, str) and value.strip():
            yield field, value.strip()
    for index, value in enumerate(page.get("content") or []):
        if isinstance(value, str) and value.strip():
            yield f"content.{index}", value.strip()
    for field in ("must_include", "reserved_for_later", "proof"):
        yield from _nested_strings(page.get(field), field)


def slide_text_fields(slide: dict[str, Any]) -> Iterable[tuple[str, str]]:
    for field in (
        "title",
        "subtitle",
        "mission",
        "core_message",
        "full_copy",
        "visual_thesis",
        "speaker_notes",
    ):
        value = slide.get(field)
        if isinstance(value, str) and value.strip():
            yield field, value.strip()
    for module_index, module in enumerate(slide.get("onscreen") or []):
        if not isinstance(module, dict):
            continue
        for field in ("heading", "text"):
            value = module.get(field)
            if isinstance(value, str) and value.strip():
                yield f"onscreen.{module_index}.{field}", value.strip()
        for item_index, value in enumerate(module.get("items") or []):
            if isinstance(value, str) and value.strip():
                yield f"onscreen.{module_index}.items.{item_index}", value.strip()
    for field in ("argument", "relationships"):
        yield from _nested_strings(slide.get(field), field)


def audit_plan_internal_expert_voice(plan: dict[str, Any]) -> list[str]:
    """Return blocking, high-confidence external-adviser voice leaks."""

    if not is_internal_report_scope(plan):
        return []
    issues: list[str] = []
    for field in (
        "communication_goal",
        "audience_start",
        "audience_end",
        "thesis",
        "narrative_arc",
    ):
        value = plan.get(field)
        if not isinstance(value, str) or not value.strip():
            continue
        for description, matched in consultant_voice_hits(value):
            issues.append(
                f"plan.{field}: internal-expert voice required; {description} — matched '{matched}'"
            )
    for index, page in enumerate(plan.get("pages") or []):
        if not isinstance(page, dict):
            continue
        page_id = page.get("id") or f"#{index}"
        for field, text in page_text_fields(page):
            for description, matched in consultant_voice_hits(text):
                issues.append(
                    f"pages.{index} ({page_id}).{field}: internal-expert voice required; "
                    f"{description} — matched '{matched}'"
                )
    return issues


def audit_final_internal_expert_voice(
    final_script: dict[str, Any], plan: dict[str, Any]
) -> list[str]:
    """Return high-confidence voice leaks in audience-facing final copy."""

    if not is_internal_report_scope(plan):
        return []
    issues: list[str] = []
    for index, slide in enumerate(final_script.get("slides") or []):
        if not isinstance(slide, dict):
            continue
        slide_id = slide.get("id") or f"#{index}"
        for field, text in slide_text_fields(slide):
            for description, matched in consultant_voice_hits(text):
                issues.append(
                    f"slides.{index} ({slide_id}).{field}: internal-expert voice required; "
                    f"{description} — matched '{matched}'"
                )
    return issues
