"""Lightweight communication-goal input for Outline authoring.

The full hash-bound communication-strategy gate (candidate/audit/approval
files) has been removed; this module now only prepares the source-grounded
input the agent uses to propose communication-goal options in conversation.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


SOURCE_UNITS = Path("workbench/stages/00-source-map/source-units.jsonl")

LIGHTWEIGHT_GOAL_HEADING_TERMS = (
    "定位",
    "目标",
    "对象",
    "合作",
    "实施",
    "推进",
    "建议",
    "结论",
    "结束语",
)
LIGHTWEIGHT_GOAL_TEXT_TERMS = (
    "受众",
    "政府",
    "领导",
    "企业",
    "客户",
    "需求单位",
    "合作伙伴",
    "科研院所",
    "高等院校",
    "参与",
    "协同",
    "共同",
    "推动",
    "建立",
    "组织",
    "试点",
    "运营",
    "推广",
    "建议",
    "应当",
    "需要",
    "诚邀",
)


def _load_source_units_for_lightweight_strategy(
    project: Path,
) -> tuple[Path, list[dict[str, Any]]]:
    path = project / SOURCE_UNITS
    if not path.is_file():
        raise FileNotFoundError(
            "lightweight communication strategy requires source-units.jsonl; "
            f"run: python -m cyberppt prepare-source-map {project}"
        )
    units: list[dict[str, Any]] = []
    for line_number, raw in enumerate(
        path.read_text(encoding="utf-8-sig").splitlines(),
        start=1,
    ):
        if not raw.strip():
            continue
        try:
            item = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise ValueError(
                f"invalid source unit JSON at {path}:{line_number}: {exc.msg}"
            ) from exc
        if not isinstance(item, dict) or not str(item.get("unit_id") or "").strip():
            raise ValueError(
                f"invalid source unit at {path}:{line_number}: unit_id is required"
            )
        units.append(item)
    if not units:
        raise ValueError(f"source unit registry is empty: {path}")
    return path, units


def _lightweight_goal_score(unit: dict[str, Any]) -> int:
    if unit.get("kind") != "paragraph":
        return -1
    heading = " > ".join(str(item) for item in unit.get("heading_path") or [])
    content = str(unit.get("text") or "")
    score = sum(3 for term in LIGHTWEIGHT_GOAL_HEADING_TERMS if term in heading)
    score += sum(1 for term in LIGHTWEIGHT_GOAL_TEXT_TERMS if term in content)
    if any(term in content for term in ("诚邀", "首期", "下一步", "本阶段形成")):
        score += 4
    return score


def _lightweight_goal_evidence(
    units: list[dict[str, Any]],
    *,
    limit: int = 12,
) -> list[dict[str, Any]]:
    paragraphs = [item for item in units if item.get("kind") == "paragraph"]
    ranked = sorted(
        paragraphs,
        key=lambda item: (
            -_lightweight_goal_score(item),
            int(item.get("source_order") or 0),
        ),
    )
    positive = [item for item in ranked if _lightweight_goal_score(item) > 0]
    pool = positive or ranked
    selected: list[dict[str, Any]] = []
    selected_ids: set[str] = set()
    selected_headings: set[str] = set()

    # First retain the strongest cue under distinct source headings, then fill
    # the remaining slots by score. This keeps one verbose source section from
    # crowding out the document's other audience and action signals.
    for item in pool:
        heading_path = [str(value) for value in item.get("heading_path") or []]
        heading_key = heading_path[-1] if heading_path else "__root__"
        if heading_key in selected_headings:
            continue
        selected.append(item)
        selected_ids.add(str(item["unit_id"]))
        selected_headings.add(heading_key)
        if len(selected) >= limit:
            break
    for item in pool:
        if len(selected) >= limit:
            break
        unit_id = str(item["unit_id"])
        if unit_id in selected_ids:
            continue
        selected.append(item)
        selected_ids.add(unit_id)

    selected.sort(key=lambda item: int(item.get("source_order") or 0))
    return [
        {
            "unit_id": str(item["unit_id"]),
            "source_order": item.get("source_order"),
            "heading_path": [str(value) for value in item.get("heading_path") or []],
            "text": str(item.get("text") or "").strip(),
        }
        for item in selected
    ]


def _lightweight_communication_strategy_input(project: Path) -> dict[str, Any]:
    source_units_path, units = _load_source_units_for_lightweight_strategy(project)
    headings = [
        {
            "unit_id": str(item["unit_id"]),
            "level": item.get("outline_level"),
            "title": str(item.get("text") or "").strip(),
        }
        for item in units
        if item.get("kind") == "heading" and str(item.get("text") or "").strip()
    ]
    return {
        "schema": "cyberppt.lightweight_communication_strategy_input.v1",
        "mode": "lightweight",
        "status": "agent_recommendation_required",
        "source_units": str(source_units_path),
        "source_count": len(
            {str(item.get("source_id")) for item in units if item.get("source_id")}
        ),
        "unit_count": len(units),
        "source_outline": headings,
        "decision_evidence": _lightweight_goal_evidence(units),
        "instructions": [
            "先阅读并分析 source_outline 与 decision_evidence，再与用户讨论交流目标。",
            "必须提出 2-3 个由源材料支持、方向实质不同的交流目标选项，并明确标出推荐项。",
            "每个选项必须说明具体受众、使用场景、希望受众理解或相信什么、希望受众采取什么行动，并引用至少两个 source unit_id 作为依据。",
            "不得直接向用户抛出受众、场景、目标行动等空白问题；用户只需选择、修改或补充已经形成的建议。",
            "在当前对话中展示建议并等待用户输入；不要为该交互写确认文件、状态 JSON、审批、哈希、回执、attempt、manifest 或 ledger。",
            "在用户选择、修改或补充交流目标后，必须展示完成作者编辑后的章节与页面提纲、页面使命和主论证链，再进入逐页详细内容。",
            "逐页详细内容完成后，必须向用户展示可阅读的完整稿、上屏文字和讲解逻辑；自动门禁只核验作者产物，不能代替上述内容交付。",
        ],
    }


def prepare_communication_strategy(project: Path) -> dict[str, Any]:
    project = project.expanduser().resolve()
    return _lightweight_communication_strategy_input(project)
