from __future__ import annotations

from copy import deepcopy

from cyberppt.foundation_projection import project_source_truth_to_foundation
from script_engine.contracts import validate_foundation


def _source_truth() -> dict:
    return {
        "source_structure": [
            {
                "id": "H-1",
                "title": "第一章 建设背景",
                "order": 1,
                "level": "chapter",
                "source_refs": ["SU-H1"],
            }
        ],
        "semantic_concepts": [
            {
                "id": "C-1",
                "term": "行业平台",
                "definition": "组织行业资源与需求的平台。",
                "source_refs": ["ST0001"],
                "visibility": "external_ok",
            }
        ],
        "semantic_relations": [
            {
                "id": "R-1",
                "from": "C-1",
                "to": "C-1",
                "relation": "supports",
                "basis": "explicit",
                "confidence": "high",
                "support": ["ST0001"],
                "source_refs": ["SU-1"],
            }
        ],
        "open_questions": ["待确认合作范围。"],
        "sources": [
            {
                "id": "SRC-1",
                "file": "material.md",
                "original_source_file": "material.docx",
                "role": "primary",
            }
        ],
        "conclusions": [
            {
                "id": "C001",
                "statement": "行业节点、运营平台和协同载体共同支撑资源组织。",
                "source_refs": ["ST0001", "ST0002"],
            }
        ],
        "records": [
            {
                "id": "ST0001",
                "atomic_item_id": "AI-001",
                "type": "J",
                "priority": "P1",
                "claim_origin": "source_explicit",
                "statement": "行业资源较为分散。",
                "source_unit_refs": ["SU-1"],
                "semantic_units": [
                    {"text": "行业资源分散在不同主体。", "claim_role": "premise"},
                    {"text": "资源连接仍需加强。", "claim_role": "consequence"},
                ],
                "coverage_anchors": ["不同主体", "资源连接"],
                "conditions": ["在跨主体协同场景下"],
                "source_locator": {
                    "source_id": "SRC-1",
                    "section": "第一章",
                    "paragraph": 2,
                },
                "actors": ["电力企业", "数据服务机构"],
                "numeric_facts": [],
                "depends_on": [],
                "supports": ["ST0002"],
                "allowed_page_roles": ["background", "diagnosis"],
                "forbidden_page_roles": [],
            },
            {
                "id": "ST0002",
                "type": "F",
                "priority": "P1",
                "claim_origin": "source_explicit",
                "claim_role": "recommendation",
                "status": "规划",
                "semantic_status": "planned",
                "source_argument_role": "implementation",
                "argument_duty": "response",
                "normalized_fact_type": "process",
                "normalized_semantic_role": "process",
                "table_context": {
                    "group_label": "A 基础通用标准",
                    "basis": "inherited_previous_nonempty_first_column",
                },
                "statement": "行业需要形成资源连接和持续服务基础。",
                "source_unit_refs": ["SU-2"],
                "actors": ["电力企业"],
                "numeric_facts": [{"value": 3, "unit": "项", "context": "三项现状"}],
                "depends_on": [],
                "supports": [],
                "forbidden_page_roles": [],
            },
            {
                "id": "ST0003",
                "type": "B",
                "priority": "P2",
                "claim_origin": "inferred",
                "statement": "本页仅说明建设背景，不展开平台构成。",
                "source_unit_refs": ["SU-3"],
                "actors": [],
                "numeric_facts": [],
                "depends_on": [],
                "supports": [],
                "forbidden_page_roles": ["internal"],
            },
        ],
    }


def test_projected_foundation_is_schema_valid() -> None:
    foundation = project_source_truth_to_foundation(_source_truth())
    assert validate_foundation(foundation) == []


def test_facts_and_constraints_are_split_by_record_type() -> None:
    foundation = project_source_truth_to_foundation(_source_truth())
    fact_ids = {fact["id"] for fact in foundation["facts"]}
    constraint_ids = {item["id"] for item in foundation["constraints"]}
    assert fact_ids == {"ST0001", "ST0002"}
    assert constraint_ids == {"ST0003"}


def test_supports_edge_is_projected_as_a_relation() -> None:
    foundation = project_source_truth_to_foundation(_source_truth())
    relation = next(r for r in foundation["relations"] if r["relation"] == "supports")
    assert relation["from"] == "ST0001"
    assert relation["to"] == "ST0002"
    assert relation["basis"] == "explicit"


def test_conclusion_becomes_an_argument_with_support() -> None:
    foundation = project_source_truth_to_foundation(_source_truth())
    argument = foundation["arguments"][0]
    assert argument["id"] == "C001"
    assert set(argument["support"]) == {"ST0001", "ST0002"}


def test_numeric_fact_and_entity_are_projected() -> None:
    foundation = project_source_truth_to_foundation(_source_truth())
    assert foundation["numbers"][0]["unit"] == "项"
    assert foundation["entities"][0]["name"] == "电力企业"


def test_projection_preserves_nested_source_features_without_aliasing() -> None:
    source_truth = _source_truth()
    expected = {
        key: deepcopy(source_truth["records"][0][key])
        for key in (
            "atomic_item_id",
            "claim_origin",
            "semantic_units",
            "coverage_anchors",
            "conditions",
            "source_locator",
            "allowed_page_roles",
            "forbidden_page_roles",
        )
    }

    foundation = project_source_truth_to_foundation(source_truth)
    fact = next(item for item in foundation["facts"] if item["id"] == "ST0001")

    for key, value in expected.items():
        assert fact[key] == value
        if isinstance(value, (dict, list)):
            assert fact[key] is not source_truth["records"][0][key]


def test_projection_adds_strict_policy_and_explicit_fact_bindings() -> None:
    foundation = project_source_truth_to_foundation(_source_truth())
    fact1 = next(item for item in foundation["facts"] if item["id"] == "ST0001")
    fact2 = next(item for item in foundation["facts"] if item["id"] == "ST0002")
    entities = {item["name"]: item for item in foundation["entities"]}
    number = foundation["numbers"][0]

    assert foundation["source_consumption_policy"] == "required"
    assert foundation["source_consumption_contract_version"] == 2
    assert fact1["entity_refs"] == [
        entities["电力企业"]["id"],
        entities["数据服务机构"]["id"],
    ]
    assert fact2["entity_refs"] == [entities["电力企业"]["id"]]
    assert entities["电力企业"]["fact_refs"] == ["ST0001", "ST0002"]
    assert fact2["number_refs"] == [number["id"]]
    assert number["fact_ref"] == "ST0002"


def test_internal_only_visibility_is_preserved() -> None:
    foundation = project_source_truth_to_foundation(_source_truth())
    constraint = foundation["constraints"][0]
    assert constraint["visibility"] == "internal_only"


def test_source_structure_concepts_relations_and_questions_are_preserved() -> None:
    foundation = project_source_truth_to_foundation(_source_truth())
    assert foundation["source_structure"][0]["id"] == "H-1"
    assert foundation["concepts"][0]["id"] == "C-1"
    assert any(item["id"] == "R-1" for item in foundation["relations"])
    assert foundation["open_questions"] == ["待确认合作范围。"]


def test_fact_semantic_role_status_and_table_context_are_preserved() -> None:
    foundation = project_source_truth_to_foundation(_source_truth())
    fact = next(item for item in foundation["facts"] if item["id"] == "ST0002")
    assert fact["claim_role"] == "recommendation"
    assert fact["status"] == "规划"
    assert fact["semantic_status"] == "planned"
    assert fact["source_argument_role"] == "implementation"
    assert fact["argument_duty"] == "response"
    assert fact["normalized_fact_type"] == "process"
    assert fact["table_context"]["group_label"] == "A 基础通用标准"
