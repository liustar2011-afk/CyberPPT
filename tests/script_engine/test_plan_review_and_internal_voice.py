from __future__ import annotations

import copy
import json
from pathlib import Path

from script_engine.analysis_audit import audit_deck_plan
from script_engine.cli import main
from script_engine.plan_review import render_plan_review


ROOT = Path(__file__).resolve().parents[2]


def _example() -> tuple[dict, dict]:
    plan = json.loads((ROOT / "examples/deck-plan.example.json").read_text(encoding="utf-8"))
    foundation = json.loads((ROOT / "examples/foundation.example.json").read_text(encoding="utf-8"))
    return plan, foundation


def test_plan_review_renders_only_v2_lean_review_boundary_without_mutation() -> None:
    plan, foundation = _example()
    before = copy.deepcopy(plan)

    markdown = render_plan_review(plan, foundation)

    assert "# 脚本规划待确认" in markdown
    assert "- 规划合同：v2 lean" in markdown
    assert "| P01 | 机制解释 | 数据服务形成机制 |" in markdown
    assert "页面使命" in markdown and "来源范围" in markdown
    assert "完整文字稿" not in markdown and "上屏合同" not in markdown
    assert plan == before


def test_review_plan_cli_prints_markdown_and_creates_no_artifact(tmp_path, capsys) -> None:
    plan, foundation = _example()
    plan_path = tmp_path / "deck-plan.json"
    foundation_path = tmp_path / "foundation.json"
    plan_path.write_text(json.dumps(plan, ensure_ascii=False), encoding="utf-8")
    foundation_path.write_text(json.dumps(foundation, ensure_ascii=False), encoding="utf-8")
    before = {path.name for path in tmp_path.iterdir()}

    assert main(["review-plan", str(plan_path), str(foundation_path)]) == 0

    assert "# 脚本规划待确认" in capsys.readouterr().out
    assert {path.name for path in tmp_path.iterdir()} == before


def _grouping_fixture(groups: list[list[str]]) -> tuple[dict, dict]:
    source_ids = [item for group in groups for item in group]
    foundation = {
        "source_structure": [
            {"id": source_id, "level": "chapter", "order": index + 1}
            for index, source_id in enumerate(source_ids)
        ],
        "facts": [
            {"id": f"F{index + 1}", "statement": f"来源事实{index + 1}"}
            for index in range(len(groups))
        ],
        "concepts": [], "entities": [], "relations": [], "arguments": [],
        "constraints": [], "numbers": [],
    }
    chapters = []
    pages = [
        {"id": "P00", "title": "封面", "question": "汇报主题是什么", "logic": "建立汇报主题", "page_role": "cover", "source_refs": []},
        {"id": "P01", "title": "目录", "question": "汇报如何展开", "logic": "展示汇报结构", "page_role": "agenda", "source_refs": []},
    ]
    for index, group in enumerate(groups, start=1):
        chapter_id = f"C{index:02d}"
        chapters.append({
            "id": chapter_id, "title": f"章节{index}", "purpose": f"解释问题{index}",
            "source_chapter_ids": group,
            "structural_operation": "group_adjacent_source_chapters" if len(group) > 1 else "preserve",
        })
        if len(groups) > 1:
            pages.append({
                "id": f"T{index:02d}", "chapter_id": chapter_id, "title": f"章节{index}",
                "question": f"章节{index}讲什么", "logic": f"进入章节{index}",
                "page_role": "transition", "source_refs": [],
            })
        pages.append({
            "id": f"P{index + 1:02d}", "chapter_id": chapter_id, "title": f"内容{index}",
            "question": f"问题{index}", "logic": f"说明来源事实{index}", "page_role": "content",
            "source_refs": [f"F{index}"],
        })
    pages.append({"id": "P99", "title": "封底", "question": "如何结束", "logic": "结束汇报", "page_role": "ending", "source_refs": []})
    plan = {
        "communication_goal": "解释来源结构", "plan_contract_version": 2,
        "planning_profile": "lean", "audience_scope": "internal",
        "source_structure_mode": "presentation_grouping",
        "presentation_structure_mode": "formal_chaptered",
        "chapters": chapters, "pages": pages,
    }
    return plan, foundation


def test_presentation_grouping_preserves_source_order() -> None:
    plan, foundation = _grouping_fixture([["CH1", "CH2"], ["CH3"]])
    issues, _ = audit_deck_plan(plan, foundation)
    assert not issues


def test_presentation_grouping_rejects_source_reordering() -> None:
    plan, foundation = _grouping_fixture([["CH1"], ["CH2"]])
    plan["chapters"][0]["source_chapter_ids"] = ["CH2"]
    plan["chapters"][1]["source_chapter_ids"] = ["CH1"]
    issues, _ = audit_deck_plan(plan, foundation)
    assert any("PRESENTATION_SOURCE_CHAPTER_MAPPING_CONFLICT" in issue for issue in issues)


def test_single_chapter_forbids_transition_page() -> None:
    plan, foundation = _grouping_fixture([["CH1"]])
    plan["pages"].insert(2, {
        "id": "T01", "chapter_id": "C01", "title": "章节一", "question": "讲什么",
        "logic": "进入章节", "page_role": "transition", "source_refs": [],
    })
    issues, _ = audit_deck_plan(plan, foundation)
    assert "PRESENTATION_SINGLE_CHAPTER_TRANSITION_FORBIDDEN" in issues

