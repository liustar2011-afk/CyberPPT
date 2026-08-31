"""Deterministic AUTHOR supporting-field contracts for content slides."""
from __future__ import annotations

import difflib
import re
from typing import Any

from .delivery_cleanliness import argument_pattern_topology
from .semantic_text_primitives import GENERIC_TRANSFORMATION_CLAIM_RE, normalize_item_text


_MISSION_GENERIC_RE = re.compile(
    r"^(?:说明|明确|解释|呈现|组织|界定|梳理).{0,12}(?:相关|有关|主要)(?:内容|情况|工作|事项|关系)[。.]?$"
)
_VISUAL_RELATION_GRAMMAR_RE = re.compile(
    r"共同|并列|汇聚|进入|形成|推动|驱动|衔接|决定|贯通|分层|分步|分为|归入|管理|依次|映射|对应|支撑|保障|承接|转化|闭环|递进|循环|流向|接受"
)
_PARALLEL_VISUAL_GRAMMAR_RE = re.compile(
    r"共同|并列|分组|分类|分层|贯穿|纵向|横向|三类|四类|五类|六类|七类|八类"
)
_CONVERGENCE_VISUAL_GRAMMAR_RE = re.compile(r"共同|汇聚|形成|构成|支撑|保障|接受|落到|指向")
_HIDDEN_RELATION_STEP_RE = re.compile(r"[，,；;].{0,24}(?:再|随后|进而|继而|并通过)")


def _field_is_blank(value: object) -> bool:
    return not isinstance(value, str) or not value.strip()


def _onscreen_lines(slide: dict[str, Any]) -> list[str]:
    lines: list[str] = []
    for module in slide.get("onscreen") or []:
        if not isinstance(module, dict):
            continue
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


def check_author_field_contract(final_script: dict[str, Any]) -> list[str]:
    """Enforce the mechanical floor of the mandatory AUTHOR supporting-field pass."""

    issues: list[str] = []
    for index, slide in enumerate(final_script.get("slides") or []):
        if not isinstance(slide, dict) or slide.get("page_type") != "content":
            continue
        slide_id = slide.get("id") or f"#{index}"
        prefix = f"slides.{index} ({slide_id})"

        for field in ("mission", "core_message", "full_copy", "visual_thesis", "speaker_notes"):
            if _field_is_blank(slide.get(field)):
                issues.append(
                    f"AUTHOR_FIELD_REQUIRED: {prefix}.{field}: content pages require a non-empty {field}"
                )

        mission = str(slide.get("mission") or "").strip()
        if mission and _MISSION_GENERIC_RE.fullmatch(mission):
            issues.append(
                f"AUTHOR_MISSION_GENERIC: {prefix}.mission: '{mission}' names a generic review topic; "
                "state the single audience question or page duty"
            )

        argument = slide.get("argument")
        if not isinstance(argument, dict):
            issues.append(
                f"AUTHOR_ARGUMENT_REQUIRED: {prefix}.argument: content pages require an argument object"
            )
            topology = None
            chain: list[object] = []
        else:
            pattern = str(argument.get("pattern") or "").strip()
            topology = argument_pattern_topology(pattern)
            if topology is None:
                issues.append(
                    f"AUTHOR_ARGUMENT_PATTERN_UNREGISTERED: {prefix}.argument.pattern: "
                    f"'{pattern}' has no registered topology"
                )
            chain = argument.get("chain") if isinstance(argument.get("chain"), list) else []
            usable_chain = [item.strip() for item in chain if isinstance(item, str) and item.strip()]
            if len(usable_chain) < 2 or len(usable_chain) != len(chain):
                issues.append(
                    f"AUTHOR_ARGUMENT_CHAIN_INVALID: {prefix}.argument.chain: provide at least two non-empty semantic nodes"
                )

        visual_thesis = str(slide.get("visual_thesis") or "").strip()
        if visual_thesis and not _VISUAL_RELATION_GRAMMAR_RE.search(visual_thesis):
            issues.append(
                f"AUTHOR_VISUAL_THESIS_NONRELATIONAL: {prefix}.visual_thesis: '{visual_thesis}' "
                "does not state a visible direction, grouping, mapping, convergence or closed loop"
            )
        if topology == "parallel" and visual_thesis and not _PARALLEL_VISUAL_GRAMMAR_RE.search(visual_thesis):
            issues.append(
                f"AUTHOR_VISUAL_TOPOLOGY_CONFLICT: {prefix}.visual_thesis: registered parallel pattern "
                "requires visible parallel, grouping or shared-dimension grammar"
            )
        if topology == "convergence" and visual_thesis and not _CONVERGENCE_VISUAL_GRAMMAR_RE.search(visual_thesis):
            issues.append(
                f"AUTHOR_VISUAL_TOPOLOGY_CONFLICT: {prefix}.visual_thesis: registered convergence pattern "
                "requires inputs to share a visible landing"
            )

        core = normalize_item_text(str(slide.get("core_message") or ""))
        visual = normalize_item_text(visual_thesis)
        if core and visual and len(core) >= 16 and difflib.SequenceMatcher(None, core, visual).ratio() >= 0.9:
            issues.append(
                f"AUTHOR_VISUAL_THESIS_RESTATEMENT: {prefix}.visual_thesis restates core_message "
                "instead of declaring the visual relationship"
            )

        for relation_index, relation in enumerate(slide.get("relationships") or []):
            if not isinstance(relation, dict):
                issues.append(
                    f"AUTHOR_RELATION_INVALID: {prefix}.relationships[{relation_index}] must be an object"
                )
                continue
            source = str(relation.get("from") or "").strip()
            target = str(relation.get("to") or "").strip()
            action = str(relation.get("relation") or "").strip()
            if not source or not target or not action:
                issues.append(
                    f"AUTHOR_RELATION_INCOMPLETE: {prefix}.relationships[{relation_index}] requires from, to and relation"
                )
                continue
            if _HIDDEN_RELATION_STEP_RE.search(action):
                issues.append(
                    f"AUTHOR_RELATION_HIDDEN_INTERMEDIATE: {prefix}.relationships[{relation_index}].relation: "
                    f"'{action}' hides more than one process step inside one edge"
                )
            combined = normalize_item_text(f"{source}{action}{target}")
            if GENERIC_TRANSFORMATION_CLAIM_RE.search(combined):
                issues.append(
                    f"AUTHOR_RELATION_ABSTRACT_TRANSFORMATION: {prefix}.relationships[{relation_index}]: "
                    "name the concrete operating mechanism and observable result at both ends"
                )

        notes = normalize_item_text(str(slide.get("speaker_notes") or ""))
        comparison_lines = [
            normalize_item_text(str(slide.get("core_message") or "")),
            *(normalize_item_text(line) for line in _onscreen_lines(slide)),
        ]
        if notes and any(
            line and len(line) >= 12 and difflib.SequenceMatcher(None, notes, line).ratio() >= 0.88
            for line in comparison_lines
        ):
            issues.append(
                f"AUTHOR_SPEAKER_NOTES_RESTATEMENT: {prefix}.speaker_notes directly restates a visible judgment; "
                "add basis, subordinate evidence, a non-material boundary, audience focus or natural transition"
            )
    return issues


__all__ = ["check_author_field_contract"]
