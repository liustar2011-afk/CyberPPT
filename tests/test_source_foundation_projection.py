from __future__ import annotations

import json
from pathlib import Path

import pytest

from cyberppt.source_foundation_projection import (
    _atomic_semantic_profile,
    _block_to_source_unit,
    _table_group_contexts,
    project_source_foundation_truth,
)
from cyberppt.source_truth_contract import audit_source_truth, load_source_truth


def _write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")


def _project(tmp_path: Path) -> tuple[Path, Path, Path]:
    project = tmp_path / "project"
    foundation = project / "workbench/source-foundation/foundation/source"
    semantic = project / "workbench/source-foundation/semantic/source"
    source_map = project / "workbench/stages/00-source-map"
    project.mkdir(parents=True)

    blocks = [
        {"block_id": "blk-0001", "type": "paragraph", "text": "行业资源较为分散。", "line_start": 1, "line_end": 1, "section_id": "sec-1", "heading_path": ["第一章 建设背景"]},
        {"block_id": "blk-0002", "type": "paragraph", "text": "行业需要形成资源连接和持续服务基础。", "line_start": 2, "line_end": 2, "section_id": "sec-1", "heading_path": ["第一章 建设背景"]},
        {"block_id": "blk-0003", "type": "paragraph", "text": "合作事项按单项合作协商确定。", "line_start": 3, "line_end": 3, "section_id": "sec-1", "heading_path": ["第一章 建设背景"]},
    ]
    _write_json(foundation / "structure.json", {"source": {"source_file": "material.docx"}, "blocks": blocks})
    _write_json(foundation / "fact-base.json", {"entries": []})
    _write_json(semantic / "semantic-report.json", {"status": "ok"})
    _write_json(
        semantic / "semantic-workpack.json",
        {"sections": [{"section_id": "sec-1", "title": "第一章 建设背景"}]},
    )
    facts = [
        {"normalized_fact_id": "NF-0001", "statement": blocks[0]["text"], "fact_type": "problem", "normalization": "verbatim", "evidence": [{"block_id": "blk-0001"}]},
        {"normalized_fact_id": "NF-0002", "statement": blocks[1]["text"], "fact_type": "goal", "normalization": "verbatim", "evidence": [{"block_id": "blk-0002"}]},
        {"normalized_fact_id": "NF-0003", "statement": blocks[2]["text"], "fact_type": "constraint", "normalization": "verbatim", "evidence": [{"block_id": "blk-0003"}]},
    ]
    _write_json(semantic / "normalized-facts.json", {"facts": facts, "conflicts": [], "ambiguities": []})
    _write_json(
        semantic / "concept-base.json",
        {"concepts": [{"concept_id": "C-1", "canonical_name": "行业平台", "definition": "组织行业资源。", "normalized_fact_ids": ["NF-0001"]}]},
    )
    _write_json(
        semantic / "relation-graph.json",
        {"relations": [{"relation_id": "R-1", "from_concept_id": "C-1", "to_concept_id": "C-1", "relation_type": "supports", "basis": "explicit", "confidence": "high", "normalized_fact_ids": ["NF-0001", "NF-0002"]}]},
    )
    _write_json(
        semantic / "argument-chain.json",
        {
            "document_semantics": {
                "document_role": "建设方案",
                "subject_of_report": "行业资源连接和服务基础",
                "primary_thesis": "资源分散要求形成连接和服务基础。",
                "author_purpose": "说明现有问题并提出建设目标。",
                "argument_method": ["RC-001"],
                "supporting_basis": ["NF-0001", "NF-0002"],
                "business_objects": ["行业资源", "连接和服务基础"],
                "decision_boundary": "合作事项仍按单项协商确定。",
                "scope": "建设背景、建设目标和合作边界。",
                "decision_intent": "确认建设必要性和合作边界。",
            },
            "document_thesis": {
                "statement": "资源分散要求形成连接和服务基础。",
                "normalized_fact_ids": ["NF-0001", "NF-0002"],
                "section_ids": ["sec-1"],
                "basis": "inferred",
                "inference_rationale": "问题事实与目标事实共同构成建设必要性判断。",
                "actor_refs": ["行业建设相关方"],
            },
            "source_chain": [{"node_id": "SC-001", "role": "background", "argument_weight": "supporting", "statement": "建设背景", "normalized_fact_ids": ["NF-0001", "NF-0002", "NF-0003"], "section_ids": ["sec-1"]}],
            "reconstructed_chain": [{"node_id": "RC-001", "role": "background", "argument_weight": "core", "statement": "资源分散要求形成连接和服务基础。", "normalized_fact_ids": ["NF-0001", "NF-0002"], "section_ids": ["sec-1"]}],
            "argument_relations": [{
                "relation_id": "AR-001",
                "from_node_id": "RC-001",
                "to_node_id": "document_thesis",
                "relation_type": "establishes",
                "basis": "inferred",
                "inference_rationale": "问题与目标共同建立全文判断。",
                "normalized_fact_ids": ["NF-0001", "NF-0002"],
                "explanation": "建设背景建立全文建设必要性判断。",
            }],
            "diagnostics": [],
        },
    )
    units = [
        {"schema": "cyberppt.source_unit.v1", "unit_id": f"SU-{index}", "source_id": "SRC-1", "source_path": "source/material.docx", "kind": "paragraph", "source_order": index, "heading_id": "H-1", "heading_path": ["第一章 建设背景"], "locator": {"paragraph": index}, "text": block["text"]}
        for index, block in enumerate(blocks, start=1)
    ]
    source_map.mkdir(parents=True)
    (source_map / "source-units.jsonl").write_text(
        "".join(json.dumps(item, ensure_ascii=False) + "\n" for item in units),
        encoding="utf-8",
        newline="\n",
    )
    _write_json(
        source_map / "source-heading-tree.json",
        {"headings": [{"heading_id": "H-1", "title": "第一章 建设背景", "level": 1, "parent_heading_id": None, "source_order": 1, "unit_id": "SU-H1"}]},
    )
    _write_json(
        source_map / "source-registry.json",
        {"sources": [{"source_id": "SRC-1", "path": "source/material.docx", "role": "primary"}]},
    )
    return project, foundation, semantic


def test_projects_validated_semantics_into_auditable_source_truth(tmp_path: Path) -> None:
    project, foundation, semantic = _project(tmp_path)
    model_path, truth_path = project_source_foundation_truth(
        project,
        foundation_dir=foundation,
        semantic_dir=semantic,
    )
    assert model_path.is_file()
    truth = load_source_truth(truth_path)
    assert audit_source_truth(truth) == []
    assert len(truth["records"]) == 3
    assert truth["source_structure"][0]["level"] == "chapter"
    assert truth["semantic_concepts"][0]["id"] == "C-1"
    assert truth["semantic_relations"][0]["id"] == "R-1"


def test_projection_preserves_authored_semantic_units_and_status_terms(tmp_path: Path) -> None:
    project, foundation, semantic = _project(tmp_path)
    normalized_path = semantic / "normalized-facts.json"
    normalized = json.loads(normalized_path.read_text(encoding="utf-8"))
    normalized["facts"][0]["semantic_units"] = [
        {
            "id": "NF-0001#event",
            "text": "行业资源较为分散",
            "semantic_role": "current_state",
            "event_status": "现状",
            "protected_terms": ["较为分散"],
        },
        {
            "id": "NF-0001#effect",
            "text": "资源协同成本较高",
            "semantic_role": "effect",
        },
    ]
    _write_json(normalized_path, normalized)

    _, truth_path = project_source_foundation_truth(
        project,
        foundation_dir=foundation,
        semantic_dir=semantic,
    )
    truth = load_source_truth(truth_path)

    assert truth["records"][0]["semantic_units"] == [
        {
            "id": "NF-0001#event",
            "text": "行业资源较为分散",
            "semantic_role": "current_state",
            "event_status": "现状",
            "protected_terms": ["较为分散"],
            "claim_role": "problem",
            "source_unit_refs": ["SU-1"],
        },
        {
            "id": "NF-0001#effect",
            "text": "资源协同成本较高",
            "semantic_role": "effect",
            "claim_role": "problem",
            "source_unit_refs": ["SU-1"],
        },
    ]


def test_projection_copies_authored_document_thesis_and_argument_graph(tmp_path: Path) -> None:
    project, foundation, semantic = _project(tmp_path)

    model_path, _ = project_source_foundation_truth(
        project,
        foundation_dir=foundation,
        semantic_dir=semantic,
    )
    model = json.loads(model_path.read_text(encoding="utf-8"))

    assert model["document_thesis"]["statement"] == "资源分散要求形成连接和服务基础。"
    assert model["document_semantics"]["argument_method"] == ["RC-001"]
    assert model["section_nodes"][0]["argument_weight"] == "core"
    assert model["argument_relations"] == [
        {
            "id": "AR-001",
            "from": "RC-001",
            "to": "document_thesis",
            "relation": "establishes",
            "weight_effect": "none",
            "basis": "inferred",
            "evidence_refs": ["SU-1", "SU-2"],
            "inference_rationale": "问题与目标共同建立全文判断。",
            "explanation": "建设背景建立全文建设必要性判断。",
            "projection_only": True,
        }
    ]


def test_projection_rejects_argument_chain_without_authored_document_thesis(tmp_path: Path) -> None:
    project, foundation, semantic = _project(tmp_path)
    argument_path = semantic / "argument-chain.json"
    argument = json.loads(argument_path.read_text(encoding="utf-8"))
    del argument["document_thesis"]
    _write_json(argument_path, argument)

    with pytest.raises(ValueError, match="must declare document_thesis"):
        project_source_foundation_truth(
            project,
            foundation_dir=foundation,
            semantic_dir=semantic,
        )


def test_projection_fails_closed_when_source_map_text_differs(tmp_path: Path) -> None:
    project, foundation, semantic = _project(tmp_path)
    units_path = project / "workbench/stages/00-source-map/source-units.jsonl"
    lines = units_path.read_text(encoding="utf-8").splitlines()
    first = json.loads(lines[0])
    first["text"] = "已变化的源材料。"
    lines[0] = json.dumps(first, ensure_ascii=False)
    units_path.write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")
    with pytest.raises(ValueError, match="does not match the current stable source map"):
        project_source_foundation_truth(
            project,
            foundation_dir=foundation,
            semantic_dir=semantic,
        )


def test_projection_accepts_converter_only_bold_markers(tmp_path: Path) -> None:
    project, foundation, semantic = _project(tmp_path)
    structure_path = foundation / "structure.json"
    structure = json.loads(structure_path.read_text(encoding="utf-8"))
    structure["blocks"][0]["text"] = "**行业资源较为分散。**"
    _write_json(structure_path, structure)

    normalized_path = semantic / "normalized-facts.json"
    normalized = json.loads(normalized_path.read_text(encoding="utf-8"))
    normalized["facts"][0]["statement"] = "**行业资源较为分散。**"
    _write_json(normalized_path, normalized)

    _, truth_path = project_source_foundation_truth(
        project,
        foundation_dir=foundation,
        semantic_dir=semantic,
    )
    assert truth_path.is_file()


def test_projection_skips_matching_explicit_table_header_source_unit(tmp_path: Path) -> None:
    project = tmp_path / "project"
    source_map = project / "workbench/stages/00-source-map"
    source_map.mkdir(parents=True)
    units = [
        {
            "unit_id": "SU-PRE",
            "kind": "paragraph",
            "source_order": 1,
            "locator": {"paragraph": 1},
            "text": "表格前说明",
        },
        {
            "unit_id": "SU-HEADER",
            "kind": "table_row",
            "source_order": 2,
            "locator": {"table": 1, "table_row": 1},
            "text": "一级类目 | 二级子体系 | 重点方向",
        },
        {
            "unit_id": "SU-A1",
            "kind": "table_row",
            "source_order": 2,
            "locator": {"table": 1, "table_row": 2},
            "text": "A 基础通用标准 | A1 术语 | 统一术语定义",
        },
        {
            "unit_id": "SU-A2",
            "kind": "table_row",
            "source_order": 2,
            "locator": {"table": 1, "table_row": 3},
            "text": " | A2 架构 | 明确架构映射",
        },
        {
            "unit_id": "SU-POST",
            "kind": "paragraph",
            "source_order": 3,
            "locator": {"paragraph": 2},
            "text": "表格后说明",
        },
    ]
    (source_map / "source-units.jsonl").write_text(
        "".join(json.dumps(item, ensure_ascii=False) + "\n" for item in units),
        encoding="utf-8",
        newline="\n",
    )
    structure = {
        "blocks": [
            {"block_id": "blk-pre", "type": "paragraph", "text": "表格前说明", "line_start": 1},
            {
                "block_id": "blk-table",
                "type": "table",
                "line_start": 2,
                "header_status": "explicit",
                "headers": ["**一级类目**", "**二级子体系**", "**重点方向**"],
                "rows": [
                    ["A 基础通用标准", "A1 术语", "统一术语定义"],
                    ["", "A2 架构", "明确架构映射"],
                ],
            },
            {"block_id": "blk-post", "type": "paragraph", "text": "表格后说明", "line_start": 6},
        ]
    }

    mapping = _block_to_source_unit(project, structure)

    assert mapping == {
        ("blk-pre", 1): "SU-PRE",
        ("blk-table", 4): "SU-A1",
        ("blk-table", 5): "SU-A2",
        ("blk-post", 6): "SU-POST",
    }


def test_projection_does_not_skip_nonmatching_first_table_row(tmp_path: Path) -> None:
    project = tmp_path / "project"
    source_map = project / "workbench/stages/00-source-map"
    source_map.mkdir(parents=True)
    unit = {
        "unit_id": "SU-DATA",
        "kind": "table_row",
        "source_order": 1,
        "locator": {"table": 1, "table_row": 1},
        "text": "A 基础通用标准 | A1 术语 | 统一术语定义",
    }
    (source_map / "source-units.jsonl").write_text(
        json.dumps(unit, ensure_ascii=False) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    structure = {
        "blocks": [
            {
                "block_id": "blk-table",
                "type": "table",
                "line_start": 1,
                "header_status": "explicit",
                "headers": ["一级类目", "二级子体系", "重点方向"],
                "rows": [["其他类目", "其他子体系", "其他方向"]],
            }
        ]
    }

    with pytest.raises(ValueError, match="does not match the current stable source map"):
        _block_to_source_unit(project, structure)


def test_unlisted_substantive_fact_inherits_its_section_source_node(tmp_path: Path) -> None:
    project, foundation, semantic = _project(tmp_path)
    argument_path = semantic / "argument-chain.json"
    argument = json.loads(argument_path.read_text(encoding="utf-8"))
    argument["source_chain"][0]["normalized_fact_ids"] = ["NF-0001", "NF-0002"]
    _write_json(argument_path, argument)

    model_path, _ = project_source_foundation_truth(
        project,
        foundation_dir=foundation,
        semantic_dir=semantic,
    )
    model = json.loads(model_path.read_text(encoding="utf-8"))
    assignments = {
        item["atomic_items"][0]["item_id"]: item["semantic_node_ids"]
        for item in model["source_coverage"]["assignments"]
    }
    assert assignments["NF-0003"] == ["SC-001"]


def test_unlisted_substantive_fact_without_section_node_fails_closed(tmp_path: Path) -> None:
    project, foundation, semantic = _project(tmp_path)
    argument_path = semantic / "argument-chain.json"
    argument = json.loads(argument_path.read_text(encoding="utf-8"))
    argument["source_chain"][0]["normalized_fact_ids"] = ["NF-0001", "NF-0002"]
    _write_json(argument_path, argument)

    normalized_path = semantic / "normalized-facts.json"
    normalized = json.loads(normalized_path.read_text(encoding="utf-8"))
    normalized["facts"][2]["section_id"] = "sec-missing"
    _write_json(normalized_path, normalized)

    structure_path = foundation / "structure.json"
    structure = json.loads(structure_path.read_text(encoding="utf-8"))
    structure["blocks"][2]["section_id"] = "sec-missing"
    _write_json(structure_path, structure)

    with pytest.raises(ValueError, match=r"has no source-chain node for section\(s\): sec-missing"):
        project_source_foundation_truth(
            project,
            foundation_dir=foundation,
            semantic_dir=semantic,
        )


def test_table_continuation_rows_inherit_first_column_group_as_context() -> None:
    facts = [
        {
            "normalized_fact_id": "NF-A1",
            "evidence": [{"block_id": "blk-table", "line_start": 10}],
            "table_cell": {
                "row_index": 1,
                "cell_index": 2,
                "header": "二级子体系",
                "row_label": "A 基础通用标准",
            },
        },
        {
            "normalized_fact_id": "NF-A2",
            "evidence": [{"block_id": "blk-table", "line_start": 11}],
            "table_cell": {
                "row_index": 2,
                "cell_index": 2,
                "header": "二级子体系",
                "row_label": "",
            },
        },
    ]

    contexts = _table_group_contexts(facts)

    assert contexts["NF-A1"]["group_label"] == "A 基础通用标准"
    assert contexts["NF-A1"]["basis"] == "explicit_first_column"
    assert contexts["NF-A2"]["group_label"] == "A 基础通用标准"
    assert contexts["NF-A2"]["basis"] == "inherited_previous_nonempty_first_column"


def test_source_argument_role_preserves_recommendation_and_plan_strength() -> None:
    principle = {
        "statement": "坚持顶层对接，确保概念、架构和术语协调一致。",
        "fact_type": "requirement",
    }
    implementation = {
        "statement": "此阶段应完成第一优先级标准立项。",
        "fact_type": "process",
    }

    assert _atomic_semantic_profile(principle, source_role="approach") == (
        "recommendation",
        "recommendation",
        "response",
    )
    assert _atomic_semantic_profile(implementation, source_role="implementation") == (
        "recommendation",
        "planned",
        "response",
    )


def test_requirement_action_and_goal_are_not_flattened_to_existing_fact() -> None:
    standard_direction = {
        "statement": "制定电力数据基础设施参考架构行业实施细则。",
        "fact_type": "requirement",
    }
    research_goal = {
        "statement": "本研究旨在构建覆盖完整的标准体系框架。",
        "fact_type": "goal",
    }

    assert _atomic_semantic_profile(standard_direction, source_role="") == (
        "recommendation",
        "planned",
        "response",
    )
    assert _atomic_semantic_profile(research_goal, source_role="goal") == (
        "fact",
        "planned",
        "response",
    )


def test_conclusion_keeps_completed_finding_separate_from_future_action() -> None:
    completed = {
        "statement": "本研究构建了七大类标准体系框架。",
        "fact_type": "goal",
    }
    future = {
        "statement": "后续工作中，中电联将持续完善标准体系框架。",
        "fact_type": "goal",
    }

    assert _atomic_semantic_profile(completed, source_role="conclusion") == (
        "fact",
        "existing",
        "response",
    )
    assert _atomic_semantic_profile(future, source_role="conclusion") == (
        "recommendation",
        "planned",
        "response",
    )
