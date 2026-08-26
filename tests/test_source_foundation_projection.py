from __future__ import annotations

import json
from pathlib import Path

import pytest

from cyberppt.source_foundation_projection import project_source_foundation_truth
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
            "source_chain": [{"node_id": "SC-001", "role": "background", "statement": "建设背景", "normalized_fact_ids": ["NF-0001", "NF-0002", "NF-0003"], "section_ids": ["sec-1"]}],
            "reconstructed_chain": [{"node_id": "RC-001", "role": "background", "statement": "资源分散要求形成连接和服务基础。", "normalized_fact_ids": ["NF-0001", "NF-0002"], "section_ids": ["sec-1"]}],
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
