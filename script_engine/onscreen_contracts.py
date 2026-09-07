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
_FAITHFUL_LINE_MIN_BIGRAMS = 4
_FAITHFUL_LINE_MIN_FULL_COPY_COVERAGE = 0.10


def _authoring_mode(final_script: dict[str, Any]) -> str:
    deck = final_script.get("deck") if isinstance(final_script.get("deck"), dict) else {}
    return "analytical" if deck.get("authoring_mode") == "analytical" else "faithful"


def _uses_structured_authoring(mode: str, slide: dict[str, Any]) -> bool:
    return (
        mode == "analytical"
        or isinstance(slide.get("argument"), dict)
        or bool(str(slide.get("core_message") or "").strip())
    )


def check_onscreen_heading_semantics(final_script: dict[str, Any]) -> list[str]:
    """Protect heading semantics without forcing minimal faithful labels into judgments."""

    issues: list[str] = []
    mode = _authoring_mode(final_script)
    for index, slide in enumerate(final_script.get("slides") or []):
        if not isinstance(slide, dict) or slide.get("page_type") != "content":
            continue
        structured_page = _uses_structured_authoring(mode, slide)
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
                or "贯穿" in heading
            ) and bool(module.get("text") or module.get("items"))
            if _CONTEXT_DEPENDENT_HEADING_RE.search(heading):
                issues.append(
                    f"ONSCREEN_HEADING_OBJECT_OMITTED: slides.{index} ({slide_id}).onscreen[{module_index}].heading: "
                    f"'{heading}' relies on hidden page context to supply the business matter; name the exact deployment, "
                    "project, research output or work item"
                )
                continue
            if structured_page and GENERIC_TRANSFORMATION_CLAIM_RE.search(compact):
                issues.append(
                    f"ONSCREEN_HEADING_ABSTRACT_TRANSFORMATION: slides.{index} ({slide_id}).onscreen[{module_index}].heading: "
                    f"'{heading}' is grammatically complete but leaves both the construction mechanism and operating "
                    "result abstract; an explicitly structured page must name what changes in the business"
                )
                continue
            if (
                structured_page
                and heading
                and len(compact) < 16
                and not source_defined_taxonomy
                and not category_with_criterion
                and not has_complete_semantic_predicate(heading)
            ):
                issues.append(
                    f"ONSCREEN_HEADING_INCOMPLETE: slides.{index} ({slide_id}).onscreen[{module_index}].heading: "
                    f"'{heading}' is only a category label; use a source-native minimal page for label-led structure, "
                    "or make the heading a complete point when core/argument authoring is explicitly declared"
                )
    return issues


def check_onscreen_detail_semantics(final_script: dict[str, Any]) -> list[str]:
    """Reject ambiguous details while allowing source-native faithful phrases."""

    issues: list[str] = []
    mode = _authoring_mode(final_script)
    for index, slide in enumerate(final_script.get("slides") or []):
        if not isinstance(slide, dict) or slide.get("page_type") != "content":
            continue
        structured_page = _uses_structured_authoring(mode, slide)
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
                    structured_page
                    and _DANGLING_MODIFIER_RE.search(body)
                    and not has_complete_semantic_predicate(body)
                    and not _PASS_RESULT_RE.search(body)
                ):
                    issues.append(
                        f"ONSCREEN_DANGLING_MODIFIER: slides.{index} ({slide_id}).onscreen[{module_index}].{field}: "
                        f"'{line}' states only a basis, condition, method or scope; explicitly structured pages "
                        "must complete the authored proposition"
                    )
                elif len(parts) == 2 and _GENERIC_DETAIL_TAIL_RE.fullmatch(normalize_item_text(body)):
                    issues.append(
                        f"ONSCREEN_DETAIL_GENERIC: slides.{index} ({slide_id}).onscreen[{module_index}].{field}: "
                        f"'{line}' uses a semantic label but leaves the business matter abstract"
                    )
    return issues


def check_onscreen_projection_structure(final_script: dict[str, Any]) -> list[str]:
    """Require explanatory payload for normal multi-module self-read pages."""

    issues: list[str] = []
    for index, slide in enumerate(final_script.get("slides") or []):
        if not isinstance(slide, dict) or slide.get("page_type") != "content":
            continue
        modules = [module for module in slide.get("onscreen") or [] if isinstance(module, dict)]
        if len(modules) < 2:
            continue
        has_payload_layer = any(
            (isinstance(module.get("text"), str) and module.get("text", "").strip())
            or any(isinstance(item, str) and item.strip() for item in module.get("items") or [])
            for module in modules
        )
        if not has_payload_layer:
            slide_id = slide.get("id") or f"#{index}"
            issues.append(
                f"ONSCREEN_EVIDENCE_LAYER_MISSING: slides.{index} ({slide_id}).onscreen: "
                "multiple modules are presented without any child text or items; retain the source-backed "
                "detail, condition, scope, definition or result needed for independent reading"
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


def _onscreen_entries(slide: dict[str, Any]) -> list[tuple[str, str]]:
    entries: list[tuple[str, str]] = []
    for module_index, module in enumerate(slide.get("onscreen") or []):
        if not isinstance(module, dict):
            continue
        for key in ("heading", "text"):
            value = module.get(key)
            if isinstance(value, str) and value.strip():
                entries.append((f"onscreen[{module_index}].{key}", value.strip()))
        entries.extend(
            (f"onscreen[{module_index}].items[{item_index}]", item.strip())
            for item_index, item in enumerate(module.get("items") or [])
            if isinstance(item, str) and item.strip()
        )
    return entries


def _check_faithful_full_copy_alignment(final_script: dict[str, Any]) -> list[str]:
    """Require faithful visible copy to inherit semantic anchors from ``full_copy``."""

    issues: list[str] = []
    for index, slide in enumerate(final_script.get("slides") or []):
        if not isinstance(slide, dict) or slide.get("page_type") != "content":
            continue
        full_copy_bigrams = _semantic_bigrams(slide.get("full_copy"))
        if len(full_copy_bigrams) < _FAITHFUL_LINE_MIN_BIGRAMS:
            continue
        slide_id = slide.get("id") or f"#{index}"
        for field, text in _onscreen_entries(slide):
            line_bigrams = _semantic_bigrams(text)
            if len(line_bigrams) < _FAITHFUL_LINE_MIN_BIGRAMS:
                continue
            coverage = len(line_bigrams & full_copy_bigrams) / len(line_bigrams)
            if coverage < _FAITHFUL_LINE_MIN_FULL_COPY_COVERAGE:
                issues.append(
                    f"ONSCREEN_FULL_COPY_MISALIGNED: slides.{index} ({slide_id}).{field}: "
                    f"visible copy shares only {coverage:.0%} of its semantic anchors with full_copy "
                    f"(minimum {_FAITHFUL_LINE_MIN_FULL_COPY_COVERAGE:.0%}); select, merge or lightly rephrase "
                    "from full_copy instead of introducing a new proposition"
                )
    return issues


def _check_declared_core_consistency(final_script: dict[str, Any]) -> list[str]:
    """When a page declares ``core_message``, keep it consistent without making it the faithful parent."""

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
        if coverage < _ONSCREEN_CORE_MIN_COVERAGE or body_coverage < _ONSCREEN_BODY_MIN_COVERAGE:
            slide_id = slide.get("id") or f"#{index}"
            issues.append(
                f"ONSCREEN_CORE_MISALIGNED: slides.{index} ({slide_id}).onscreen: "
                f"title + body cover {coverage:.0%} and body modules cover {body_coverage:.0%} "
                "of the declared core_message anchors (minimum 25% / 15%); either align the optional "
                "core_message with the source-faithful page or remove that optional field"
            )
    return issues


def check_onscreen_core_alignment(final_script: dict[str, Any]) -> list[str]:
    """Keep faithful parentage in ``full_copy`` and validate optional core consistency.

    Analytical pages still require core-message alignment. Faithful pages always
    project from ``full_copy``; when they voluntarily declare ``core_message``, it
    is checked as a consistency constraint rather than a semantic parent.
    """

    if _authoring_mode(final_script) != "analytical":
        return [
            *_check_faithful_full_copy_alignment(final_script),
            *_check_declared_core_consistency(final_script),
        ]
    return _check_declared_core_consistency(final_script)


__all__ = [
    "check_onscreen_code_context",
    "check_onscreen_core_alignment",
    "check_onscreen_detail_semantics",
    "check_onscreen_heading_semantics",
    "check_onscreen_hierarchy_punctuation",
    "check_onscreen_projection_structure",
]
