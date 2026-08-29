from __future__ import annotations

from pathlib import Path

import pytest

from cyberppt.foundation_authoring import prepare_script_foundation
from cyberppt.source_assets import validate_source_assets
from cyberppt.source_document_map import prepare_source_context
from script_engine.analysis_audit import audit_foundation_analysis
from script_engine.cli import main as script_engine_main
from script_engine.contracts import validate_foundation
from script_engine.source_index import validate_foundation_detail_atomicity, validate_reading_strategy
from script_engine.source_index import validate_foundation_source_bindings


def _foundation(strategy: dict, *, source_ref: str = "SU-1", statement: str = "覆盖率达到95%") -> dict:
    return {
        "sources": [{"id": "SRC-1", "path": "source/brief.md", "sha256": "abc"}],
        "source_structure": [
            {
                "id": "H-1",
                "title": "总体方案",
                "order": 1,
                "level": "chapter",
                "source_refs": ["SU-1"],
            }
        ],
        "reading_strategy": strategy,
        "document_thesis": {"statement": "总体方案形成完整闭环", "source_refs": ["SU-1"]},
        "document_semantics": {"argument_method": ["A-1"]},
        "argument_nodes": [
            {
                "id": "A-1",
                "statement": "总体方案",
                "argument_weight": "core",
                "source_refs": ["SU-1"],
            }
        ],
        "facts": [{"id": "F-1", "statement": statement, "source_refs": [source_ref]}],
        "concepts": [],
        "relations": [],
        "arguments": [],
        "constraints": [],
        "numbers": [],
    }


def test_prepare_script_foundation_emits_direct_authoring_task_and_no_semantic_sidecars(
    tmp_path: Path,
) -> None:
    project = tmp_path / "project"
    source = project / "source"
    source.mkdir(parents=True)
    (source / "brief.md").write_text("# 总体方案\n完整来源内容。\n", encoding="utf-8")

    payload = prepare_script_foundation(project)

    assert payload["profile"] == "script"
    assert payload["output"] == str(project / "script/foundation.json")
    assert "完整来源内容" in payload["authoring_task"]
    assert "source-index.json" not in payload["authoring_task"].split("Output the Foundation JSON only")[0]
    assert not (project / "workbench/stages/01-analysis/source-truth.json").exists()
    assert not (project / "script/foundation.json").exists()


def test_prepare_script_foundation_rejects_strict_profile_alias(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="project-foundation"):
        prepare_script_foundation(tmp_path, profile="strict")


def test_direct_strategy_must_deep_read_every_unit() -> None:
    foundation = _foundation(
        {
            "mode": "direct",
            "section_dispositions": [
                {"heading_id": "H-1", "disposition": "deep_read", "reason": "完整读取"}
            ],
            "deep_read_unit_ids": ["SU-1"],
            "excluded_unit_ids": [],
        }
    )

    assert validate_reading_strategy(
        foundation,
        [{"heading_id": "H-1"}],
        ["SU-1"],
    ) == []
    issues = validate_reading_strategy(
        foundation,
        [{"heading_id": "H-1"}],
        ["SU-1", "SU-2"],
    )
    assert "direct reading_strategy must deep-read every source unit" in issues


def test_long_strategy_requires_complete_structure_and_exclusion_reasons() -> None:
    foundation = _foundation(
        {
            "mode": "long",
            "section_dispositions": [
                {"heading_id": "H-1", "disposition": "excluded", "reason": ""}
            ],
            "deep_read_unit_ids": ["SU-1"],
            "excluded_unit_ids": [],
        },
        statement="事实说明",
    )

    issues = validate_reading_strategy(
        foundation,
        [{"heading_id": "H-1"}, {"heading_id": "H-2"}],
        ["SU-1"],
    )

    assert any("omits source headings" in issue for issue in issues)
    assert any("excluded without reason" in issue for issue in issues)


def test_long_strategy_blocks_precise_number_from_mapped_only_unit() -> None:
    foundation = _foundation(
        {
            "mode": "long",
            "section_dispositions": [
                {"heading_id": "H-1", "disposition": "mapped", "reason": "保留论点骨架"}
            ],
            "deep_read_unit_ids": [],
            "excluded_unit_ids": [],
        }
    )

    issues = validate_reading_strategy(
        foundation,
        [{"heading_id": "H-1"}],
        ["SU-1"],
    )

    assert any("precise numeric content requires deep-read" in issue for issue in issues)


def test_foundation_audit_applies_reading_strategy_boundary() -> None:
    foundation = _foundation(
        {
            "mode": "long",
            "section_dispositions": [],
            "deep_read_unit_ids": [],
            "excluded_unit_ids": [],
        },
        statement="事实说明",
    )

    issues, _ = audit_foundation_analysis(foundation)

    assert any("omits source headings" in issue for issue in issues)


def test_source_files_to_authored_foundation_passes_schema_and_sibling_index_audit(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    project = tmp_path / "project"
    source = project / "source"
    source.mkdir(parents=True)
    (source / "brief.md").write_text("# 总体方案\n关键事实。\n", encoding="utf-8")
    index = prepare_source_context(project)
    heading = index["source_structure"][0]
    heading_unit = next(item for item in index["units"] if item["kind"] == "heading")
    fact_unit = next(item for item in index["units"] if item["kind"] == "paragraph")
    source_record = index["sources"][0]
    foundation = {
        "sources": [
            {
                "id": source_record["source_id"],
                "path": source_record["path"],
                "sha256": source_record["sha256"],
            }
        ],
        "source_structure": [
            {
                "id": heading["heading_id"],
                "title": heading["title"],
                "order": 1,
                "level": "chapter",
                "source_refs": [heading_unit["unit_id"]],
            }
        ],
        "reading_strategy": index["reading_strategy"],
        "document_thesis": {
            "statement": "总体方案由关键事实支撑。",
            "source_refs": [heading_unit["unit_id"], fact_unit["unit_id"]],
        },
        "document_semantics": {"argument_method": ["A-1"]},
        "argument_nodes": [
            {
                "id": "A-1",
                "statement": "先明确方案，再给出事实。",
                "argument_weight": "core",
                "source_refs": [heading_unit["unit_id"], fact_unit["unit_id"]],
            }
        ],
        "facts": [
            {"id": "F-1", "statement": "关键事实。", "source_refs": [fact_unit["unit_id"]]}
        ],
        "concepts": [],
        "relations": [],
        "arguments": [],
    }
    output = project / "script/foundation.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    import json

    output.write_text(json.dumps(foundation, ensure_ascii=False), encoding="utf-8")

    assert validate_foundation(foundation) == []
    assert script_engine_main(["audit-foundation", str(output)]) == 0
    assert '"status": "passed"' in capsys.readouterr().out

    drifted = {**foundation, "sources": [{**foundation["sources"][0], "sha256": "drifted"}]}
    assert any(
        "sha256 differs" in issue
        for issue in validate_foundation_source_bindings(drifted, index)
    )


def _strict_v2_index(texts: list[str]) -> dict:
    return {
        "schema": "cyberppt.source_index.v2",
        "units": [
            {"unit_id": f"SU-{index}", "kind": "paragraph", "text": text}
            for index, text in enumerate(texts, start=1)
        ],
    }


def test_strict_v2_foundation_requires_atomic_units_for_compound_source_detail() -> None:
    foundation = _foundation({}, statement="形成标准建设安排")
    foundation.update(
        {"source_consumption_policy": "required", "source_consumption_contract_version": 2}
    )
    index = _strict_v2_index([
        "参考架构明确与国家数据基础设施总体架构的映射关系。"
        "标识目录规定电力数据标识管理和目录描述要求。"
    ])

    issues = validate_foundation_detail_atomicity(foundation, index)

    assert any("FOUNDATION_SOURCE_DETAIL_ATOMICITY_GAP" in issue for issue in issues)


def test_strict_v2_foundation_accepts_traceable_atomic_units() -> None:
    foundation = _foundation({}, statement="形成标准建设安排")
    foundation.update(
        {"source_consumption_policy": "required", "source_consumption_contract_version": 2}
    )
    foundation["facts"][0]["semantic_units"] = [
        {
            "id": "F-1#0",
            "text": "参考架构明确与国家数据基础设施总体架构的映射关系",
            "source_unit_refs": ["SU-1"],
        },
        {
            "id": "F-1#1",
            "text": "标识目录规定电力数据标识管理和目录描述要求",
            "source_unit_refs": ["SU-1"],
        },
    ]
    index = _strict_v2_index([
        "参考架构明确与国家数据基础设施总体架构的映射关系。"
        "标识目录规定电力数据标识管理和目录描述要求。"
    ])

    assert validate_foundation_detail_atomicity(foundation, index) == []


def test_strict_v2_foundation_rejects_generic_semantic_units_with_valid_refs() -> None:
    foundation = _foundation({}, statement="形成标准建设安排")
    foundation.update(
        {"source_consumption_policy": "required", "source_consumption_contract_version": 2}
    )
    foundation["facts"][0]["semantic_units"] = [
        {"id": "F-1#0", "text": "形成标准建设安排", "source_unit_refs": ["SU-1"]},
        {"id": "F-1#1", "text": "完善相关制度要求", "source_unit_refs": ["SU-1"]},
    ]
    index = _strict_v2_index([
        "参考架构明确与国家数据基础设施总体架构的映射关系。"
        "标识目录规定电力数据标识管理和目录描述要求。"
    ])

    issues = validate_foundation_detail_atomicity(foundation, index)

    assert any("FOUNDATION_SEMANTIC_UNIT_DETAIL_LOSS" in issue for issue in issues)


def test_strict_v2_foundation_rejects_generic_units_for_multiple_atomic_sources() -> None:
    foundation = _foundation({}, statement="形成标准建设安排")
    foundation.update(
        {"source_consumption_policy": "required", "source_consumption_contract_version": 2}
    )
    foundation["facts"][0]["source_refs"] = ["SU-1", "SU-2"]
    foundation["facts"][0]["semantic_units"] = [
        {"id": "F-1#0", "text": "形成架构安排", "source_unit_refs": ["SU-1"]},
        {"id": "F-1#1", "text": "完善目录要求", "source_unit_refs": ["SU-2"]},
    ]
    index = _strict_v2_index([
        "参考架构明确与国家数据基础设施总体架构的映射关系。",
        "标识目录规定电力数据标识管理和目录描述要求。",
    ])

    issues = validate_foundation_detail_atomicity(foundation, index)

    assert sum("FOUNDATION_SEMANTIC_UNIT_DETAIL_LOSS" in issue for issue in issues) == 2


def test_strict_v2_foundation_detects_enumerated_compound_paragraph() -> None:
    foundation = _foundation({}, statement="形成两项建设安排")
    foundation.update(
        {"source_consumption_policy": "required", "source_consumption_contract_version": 2}
    )
    index = _strict_v2_index([
        "一是建立跨部门数据共享责任清单，二是明确数据申请审核与授权边界"
    ])

    issues = validate_foundation_detail_atomicity(foundation, index)

    assert any("FOUNDATION_SOURCE_DETAIL_ATOMICITY_GAP" in issue for issue in issues)


def test_strict_v2_foundation_keeps_short_atomic_fact_lightweight() -> None:
    foundation = _foundation({}, statement="标准体系分为四类")
    foundation.update(
        {"source_consumption_policy": "required", "source_consumption_contract_version": 2}
    )
    index = _strict_v2_index(["标准体系分为四类。"])

    assert validate_foundation_detail_atomicity(foundation, index) == []


def test_source_asset_validation_warns_for_wrong_reading_and_blocks_money_slide() -> None:
    asset = {
        "id": "ASSET-0123456789ABCDEF",
        "kind": "table",
        "source_unit_refs": ["SU-1"],
        "locator": {"table": 1},
        "argument_node_ids": ["A-1"],
        "presentation_role": "supporting",
    }
    findings = validate_source_assets([asset], ["SU-1"])
    assert [(item["code"], item["severity"]) for item in findings] == [
        ("SOURCE_ASSET_WRONG_READING_MISSING", "warning")
    ]

    asset["presentation_role"] = "money_slide"
    findings = validate_source_assets([asset], ["SU-1"])
    assert findings[0]["severity"] == "blocking"


def test_foundation_asset_argument_binding_requires_intersecting_source_evidence() -> None:
    foundation = _foundation(
        {
            "mode": "direct",
            "section_dispositions": [
                {"heading_id": "H-1", "disposition": "deep_read", "reason": "完整读取"}
            ],
            "deep_read_unit_ids": ["SU-1"],
            "excluded_unit_ids": [],
        },
        statement="事实说明",
    )
    foundation["source_assets"] = [
        {
            "id": "ASSET-0123456789ABCDEF",
            "kind": "table",
            "source_unit_refs": ["SU-1"],
            "locator": {"table": 1},
            "argument_node_ids": ["A-1"],
            "wrong_reading": "单行变化等于总体趋势",
        }
    ]
    issues, warnings = audit_foundation_analysis(foundation)
    assert not any("SOURCE_ASSET" in item for item in issues + warnings)

    foundation["argument_nodes"][0]["source_refs"] = ["SU-2"]
    issues, _ = audit_foundation_analysis(foundation)
    assert any("SOURCE_ASSET_ARGUMENT_EVIDENCE_DISCONNECTED" in item for item in issues)


def test_foundation_source_asset_must_preserve_indexed_candidate_identity() -> None:
    foundation = _foundation(
        {
            "mode": "direct",
            "section_dispositions": [
                {"heading_id": "H-1", "disposition": "deep_read", "reason": "完整读取"}
            ],
            "deep_read_unit_ids": ["SU-1"],
            "excluded_unit_ids": [],
        },
        statement="事实说明",
    )
    asset = {
        "id": "ASSET-0123456789ABCDEF",
        "kind": "table",
        "source_unit_refs": ["SU-1"],
        "locator": {"table": 1},
        "argument_node_ids": ["A-1"],
        "wrong_reading": "单行变化等于总体趋势",
    }
    foundation["source_assets"] = [asset]
    source_index = {
        "schema": "cyberppt.source_index.v2",
        "sources": [{"source_id": "SRC-1", "path": "source/brief.md", "sha256": "abc"}],
        "units": [{"unit_id": "SU-1"}],
        "asset_candidates": [
            {
                "id": asset["id"],
                "kind": asset["kind"],
                "source_unit_refs": asset["source_unit_refs"],
                "locator": asset["locator"],
            }
        ],
    }

    assert validate_foundation_source_bindings(foundation, source_index) == []
    foundation["source_assets"][0]["locator"] = {"table": 2}
    assert any(
        "locator differs" in issue
        for issue in validate_foundation_source_bindings(foundation, source_index)
    )
