"""Final Script deterministic lint orchestration.

This module owns banned-phrasing scanning and the composition order of semantic
sub-checks. Focused AUTHOR/full-copy/onscreen checks are still supplied by the
legacy rule module during the incremental split and will be replaced one domain
at a time.
"""
from __future__ import annotations

import re
from collections.abc import Iterator
from typing import Any

from . import contract_rules as _legacy
from .schema_contracts import CONTRACTS, load_json


BANNED_PHRASING_PATH = CONTRACTS / "banned-phrasing.json"


def load_banned_phrasing() -> list[dict[str, Any]]:
    return load_json(BANNED_PHRASING_PATH).get("rules", [])


def iter_final_script_text_fields(
    final_script: dict[str, Any],
) -> Iterator[tuple[str, str, str]]:
    """Yield ``(field_path, field_key, text)`` for every prose field."""

    deck = final_script.get("deck") or {}
    for key in ("title", "communication_goal", "audience", "narrative"):
        value = deck.get(key)
        if isinstance(value, str) and value:
            yield f"deck.{key}", f"deck.{key}", value

    for index, slide in enumerate(final_script.get("slides") or []):
        if not isinstance(slide, dict):
            continue
        prefix = f"slides.{index} ({slide.get('id') or f'#{index}'})"
        for key in (
            "title",
            "subtitle",
            "mission",
            "core_message",
            "full_copy",
            "visual_thesis",
            "speaker_notes",
        ):
            value = slide.get(key)
            if isinstance(value, str) and value:
                yield f"{prefix}.{key}", key, value

        argument = slide.get("argument") or {}
        pattern = argument.get("pattern")
        if isinstance(pattern, str) and pattern:
            yield f"{prefix}.argument.pattern", "argument.pattern", pattern
        for step_index, step in enumerate(argument.get("chain") or []):
            if isinstance(step, str) and step:
                yield f"{prefix}.argument.chain[{step_index}]", "argument.chain", step

        for module_index, module in enumerate(slide.get("onscreen") or []):
            if not isinstance(module, dict):
                continue
            for key in ("heading", "text"):
                value = module.get(key)
                if isinstance(value, str) and value:
                    yield (
                        f"{prefix}.onscreen[{module_index}].{key}",
                        f"onscreen.{key}",
                        value,
                    )
            for item_index, item in enumerate(module.get("items") or []):
                if isinstance(item, str) and item:
                    yield (
                        f"{prefix}.onscreen[{module_index}].items[{item_index}]",
                        "onscreen.items",
                        item,
                    )

        for relation_index, relation in enumerate(slide.get("relationships") or []):
            if not isinstance(relation, dict):
                continue
            value = relation.get("relation")
            if isinstance(value, str) and value:
                yield (
                    f"{prefix}.relationships[{relation_index}].relation",
                    "relationships.relation",
                    value,
                )


def lint_final_script(final_script: dict[str, Any]) -> list[str]:
    """Run banned-phrasing scans and deterministic semantic sub-checks."""

    rules = [
        (
            rule["id"],
            re.compile(rule["pattern"]),
            rule.get("description", ""),
            set(rule.get("exclude_fields") or []),
            set(rule["include_fields"]) if rule.get("include_fields") else None,
        )
        for rule in load_banned_phrasing()
    ]
    issues: list[str] = []
    for field_path, field_key, text in iter_final_script_text_fields(final_script):
        for rule_id, regex, description, exclude_fields, include_fields in rules:
            if field_key in exclude_fields:
                continue
            if include_fields is not None and field_key not in include_fields:
                continue
            match = regex.search(text)
            if match:
                issues.append(
                    f"{field_path}: [{rule_id}] {description} — matched '{match.group(0)}'"
                )

    issues.extend(_legacy.check_author_field_contract(final_script))
    issues.extend(_legacy.check_full_copy_structure(final_script))
    issues.extend(_legacy.check_full_copy_topic_semantics(final_script))
    issues.extend(_legacy.check_full_copy_parallel_subconclusions(final_script))
    issues.extend(_legacy.check_onscreen_heading_semantics(final_script))
    issues.extend(_legacy.check_onscreen_detail_semantics(final_script))
    issues.extend(_legacy.check_onscreen_projection_structure(final_script))
    issues.extend(_legacy.check_onscreen_hierarchy_punctuation(final_script))
    issues.extend(_legacy.check_onscreen_code_context(final_script))
    issues.extend(_legacy.check_onscreen_core_alignment(final_script))
    return issues


__all__ = [
    "BANNED_PHRASING_PATH",
    "iter_final_script_text_fields",
    "lint_final_script",
    "load_banned_phrasing",
]
