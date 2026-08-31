"""Deterministic onscreen semantic projection checks."""
from __future__ import annotations

import re
from typing import Any

from .semantic_text_primitives import (
    GENERIC_TRANSFORMATION_CLAIM_RE,
    has_complete_semantic_predicate,
    normalize_item_text,
)


_FORMAL_TAXONOMY_HEADING_RE = re.compile(r"^(?:[A-Z]\s+|\d{1,2}[.、．\s]+)\S+")
_CONTEXT_DEPENDENT_HEADING_RE = re.compile(
    r"^(?:国家|行业|项目|研究|体系)(?:已|将|需|应|可|形成|明确|推进|承担|负责|提供|支撑)"
    r"|^后续(?:推进|开展|落实)"
)
_DANGLING_MODIFIER_RE = re.compile(r"^(?:以|基于|围绕|结合|按照|通过|面向|依托|针对)")
_PASS_RESULT_RE = re.compile(r"^通过.{2,}(?:评价|认证|验收|审核|审查)$")
_GENERIC_DETAIL_TAIL_RE = re.compile(
    r"^(?:国家政策|行业特点|协同实施|形成支撑|相关要求|有关工作|持续推进)$"
)
_CODE_ONLY_MAPPING_RE = re.compile(
    r"^[A-G](?:\d+|类)(?:\s*(?:\+|＋|、|/|／)\s*[A-G](?:\d+|类))*$",
    re.IGNORECASE,
)
_LABEL_SPLIT_RE = re.compile(r"[：:]", flags=re.UNICODE)

_ONSCREEN_CORE_MIN_BIGRAMS = 4
_ONSCREEN_CORE_MIN_COVERAGE = 0.25
_ONSCREEN_BODY_MIN_COVERAGE = 0.15


def check_onscreen_heading_semantics(final_script: dict[str, Any]) -> list[str]:
    """Reject short category labels that force readers to infer a module's business meaning."""

    issues: list[str] = []
    for index, slide in enumerate(final_script.get("slides") or []):
        if not isinstance(slide, dict) or slide.get("page_type") != "content":
            continue
        slide_id = slide.get("id") or f"#{index}"
        for module_index, module in enumerate(slide.get("onscreen") or []):
            if not isinstance(module, dict):
                continue
            heading = str(module.get("heading") or "").strip()
            compact = normalize_item_text(heading)
            parts = [part for part in re.split(r"[｜|]", heading) if normalize_item_text(part)]
            category_with_criterion = len(parts) >= 2 and all(
                len(normalize_item_text(part)) >= 4 for part in parts
            )
            source_defined_taxonomy = bool(
                _FORMAL_TAXONOMY_HEADING_RE.match(heading)
                or heading.endswith("层")
                or ("贯穿" in heading and "贯穿" in str(slide.get("core_message") or ""))
            ) and bool(module.get("text") or module.get("items"))
            if _CONTEXT_DEPENDENT_HEADING_RE.search(heading):
                issues.append(
                    f"ONSCREEN_HEADING_OBJECT_OMITTED: slides.{index} ({slide_id}).onscreen[{module_index}].heading: "
                    f"'{heading}' relies on page context to supply the business matter; name the exact deployment, "
                    "project, research output or work item in the heading itself"
                )
                continue
            if GENERIC_TRANSFORMATION_CLAIM_RE.search(compact):
                issues.append(
                    f"ONSCREEN_HEADING_ABSTRACT_TRANSFORMATION: slides.{index} ({slide_id}).onscreen[{module_index}].heading: "
                    f"'{heading}' is grammatically complete but leaves both the construction mechanism and operating "
                    "result abstract; name what will work differently in the business"
                )
                continue
            if (
                heading
                and len(compact) < 16
                and not source_defined_taxonomy
                and not category_with_criterion
                and not has_complete_semantic_predicate(heading)
            ):
                issues.append(
                    f"ONSCREEN_HEADING_INCOMPLETE: slides.{index} ({slide_id}).onscreen[{module_index}].heading: "
                    f"'{heading}' is only a category label; state the object and its action, status, role or judgment"
                )
    return issues


def check_onscreen_detail_semantics(final_script: dict[str, Any]) -> list[str]:
    """Reject detail lines that stop at a basis, condition, method or scope."""

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
                body = parts[1].strip() if len(parts) == 2 else line
                if (
                    _DANGLING_MODIFIER_RE.search(body)
                    and not has_complete_semantic_predicate(body)
                    and not _PASS_RESULT_RE.search(body)
                ):
                    issues.append(
                        f"ONSCREEN_DANGLING_MODIFIER: slides.{index} ({slide_id}).onscreen[{module_index}].{field}: "
                        f"'{line}' states only a basis, condition, method or scope; add the business action or result"
                    )
                elif len(parts) == 2 and _GENERIC_DETAIL_TAIL_RE.fullmatch(normalize_item_text(body)):
                    issues.append(
                        f"ONSCREEN_DETAIL_GENERIC: slides.{index} ({slide_id}).onscreen[{module_index}].{field}: "
                        f"'{line}' uses a semantic label but leaves the business matter abstract"
                    )
    return issues


def check_onscreen_projection_structure(final_script: dict[str, Any]) -> list[str]:
    """Require a mechanical evidence floor for normal multi-module self-read pages."""

    issues: list[str] = []
    for index, slide in enumerate(final_script.get("slides") or []):
        if not isinstance(slide, dict) or slide.get("page_type") != "content":
            continue
        modules = [module for module in slide.get("onscreen") or [] if isinstance(module, dict)]
        if len(modules) < 2:
            continue
        has_evidence_layer = any(
            (isinstance(module.get("text"), str) and module.get("text", "").strip())
            or any(isinstance(item, str) and item.strip() for item in module.get("items") or [])
            for module in modules
        )
        if not has_evidence_layer:
            slide_id = slide.get("id") or f"#{index}"
            issues.append(
                f"ONSCREEN_EVIDENCE_LAYER_MISSING: slides.{index} ({slide_id}).onscreen: "
                "multiple module judgments are presented without any child text or items; "
                "retain the decisive evidence, condition, scope or result that establishes "
                "the projected argument layer"
            )
    return issues


def check_onscreen_hierarchy_punctuation(final_script: dict[str, Any]) -> list[str]:
    """Reject one visible detail line that encodes multiple hierarchy levels with colons."""

    issues: list[str] = []
    nested_colon_re = re.compile(r"^[^：:\n]{1,24}[：:][^：:\n]+[：:]")
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
                if nested_colon_re.search(line):
                    issues.append(
                        f"ONSCREEN_MULTILEVEL_COLON_CHAIN: slides.{index} ({slide_id}).onscreen"
                        f"[{module_index}].{field}: '{line}' encodes multiple hierarchy levels in one line; "
                        "keep one label-content relation per line and express parent-child structure with nesting"
                    )
    return issues


def check_onscreen_code_context(final_script: dict[str, Any]) -> list[str]:
    """Reject taxonomy-code mappings that require the previous page to decode."""

    issues: list[str] = []
    for index, slide in enumerate(final_script.get("slides") or []):
        if not isinstance(slide, dict) or slide.get("page_type") != "content":
            continue
        slide_id = slide.get("id") or f"#{index}"
        for module_index, module in enumerate(slide.get("onscreen") or []):
            if not isinstance(module, dict):
                continue
            for item_index, item in enumerate(module.get("items") or []):
                if not isinstance(item, str) or not item.strip():
                    continue
                parts = _LABEL_SPLIT_RE.split(item.strip(), maxsplit=1)
                body = parts[1].strip() if len(parts) == 2 else item.strip()
                if _CODE_ONLY_MAPPING_RE.fullmatch(body):
                    issues.append(
                        f"ONSCREEN_CODE_WITHOUT_NAME: slides.{index} ({slide_id}).onscreen[{module_index}].items[{item_index}]: "
                        f"'{item}' exposes only taxonomy codes; add each code's business name or role so the page is self-readable"
                    )
    return issues


def _semantic_bigrams(text: object) -> set[str]:
    compact = normalize_item_text(str(text or "")).lower()
    return {compact[index:index + 2] for index in range(len(compact) - 1)}


def _onscreen_text(slide: dict[str, Any]) -> str:
    values: list[str] = []
    for module in slide.get("onscreen") or []:
        if not isinstance(module, dict):
            continue
        values.extend(str(module.get(key) or "") for key in ("heading", "text"))
        values.extend(str(item) for item in module.get("items") or [] if isinstance(item, str))
    return " ".join(values)


def check_onscreen_core_alignment(final_script: dict[str, Any]) -> list[str]:
    """Treat ``core_message`` as page meaning and ``onscreen`` as its visible projection."""

    issues: list[str] = []
    for index, slide in enumerate(final_script.get("slides") or []):
        if not isinstance(slide, dict) or slide.get("page_type") != "content":
            continue
        core_bigrams = _semantic_bigrams(slide.get("core_message"))
        if len(core_bigrams) < _ONSCREEN_CORE_MIN_BIGRAMS:
            continue
        body_bigrams = _semantic_bigrams(_onscreen_text(slide))
        projection_bigrams = body_bigrams | _semantic_bigrams(
            f"{slide.get('title') or ''} {slide.get('subtitle') or ''}"
        )
        body_coverage = len(core_bigrams & body_bigrams) / len(core_bigrams)
        coverage = len(core_bigrams & projection_bigrams) / len(core_bigrams)
        if (
            coverage < _ONSCREEN_CORE_MIN_COVERAGE
            or body_coverage < _ONSCREEN_BODY_MIN_COVERAGE
        ):
            slide_id = slide.get("id") or f"#{index}"
            issues.append(
                f"ONSCREEN_CORE_MISALIGNED: slides.{index} ({slide_id}).onscreen: "
                f"title + body cover {coverage:.0%} and body modules cover {body_coverage:.0%} "
                "of the core conclusion's semantic anchors (minimum 25% / 15%); organize the "
                "whole onscreen expression around core_message"
            )
    return issues


__all__ = [
    "check_onscreen_code_context",
    "check_onscreen_core_alignment",
    "check_onscreen_detail_semantics",
    "check_onscreen_heading_semantics",
    "check_onscreen_hierarchy_punctuation",
    "check_onscreen_projection_structure",
]
