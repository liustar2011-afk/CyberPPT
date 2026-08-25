from __future__ import annotations

from types import SimpleNamespace

from cyberppt.deck_structure_validator import audit_deck_structure_collapse
from cyberppt.onscreen_expression import resolve_onscreen_expression
from cyberppt.semantic_verifier import verify_semantic_proposals
from cyberppt.stage02_semantic_intake import normalize_semantic_proposals
from cyberppt.topology_resolver import resolve_semantic_topology


def _page(*modules: str) -> SimpleNamespace:
    return SimpleNamespace(
        onscreen_expression_form="",
        top_level_module_titles=modules,
        page_type="content",
        onscreen_judgment="",
    )


def test_intake_caps_script_inference_and_keeps_it_soft() -> None:
    proposals = normalize_semantic_proposals([
        {
            "subject": "行业节点",
            "relation": "directed_dependency",
            "objects": ["运营平台"],
            "direction": "subject_to_objects",
            "basis": "derived_from_script_visual_structure",
            "confidence": "high",
            "authority_ref": "final-script.visual-structure",
        }
    ])
    assert proposals[0]["authority"] == "script_inference"
    assert proposals[0]["confidence"] == 0.82
    assert proposals[0]["constraint_authority"] == "soft"


def test_intake_promotes_source_explicit_relation_to_hard_only_with_high_confidence() -> None:
    proposals = normalize_semantic_proposals([
        {
            "subject": "A",
            "relation": "sequence_before",
            "objects": ["B"],
            "direction": "subject_to_objects",
            "basis": "source_explicit",
            "confidence": 0.96,
            "source_refs": ["S001"],
        }
    ])
    assert proposals[0]["authority"] == "source_explicit"
    assert proposals[0]["constraint_authority"] == "hard"


def test_verifier_rejects_peer_claim_that_also_declares_direction() -> None:
    verification = verify_semantic_proposals([
        {
            "proposal_id": "R01",
            "subject": "A",
            "objects": ["B", "C"],
            "proposed_relation": "peer_classification",
            "direction": "subject_to_objects",
            "directional": True,
            "basis": "model_inference",
            "origin": "stage01",
            "authority": "script_inference",
            "constraint_authority": "soft",
            "confidence": 0.80,
        }
    ])
    verdict = verification["verdicts"][0]
    assert verdict["verdict"] == "rejected"
    assert verdict["verified_relation"] == "directed_relation"
    assert "PEER_CONFLICTS_WITH_EXPLICIT_DIRECTION" in verdict["conflict_codes"]
    assert verification["verified_relationships"][0]["relation"] == "directed_relation"


def test_verifier_discards_peer_taxonomy_when_children_form_directed_chain() -> None:
    verification = verify_semantic_proposals([
        {
            "proposal_id": "R01",
            "subject": "本页",
            "objects": ["A", "B", "C"],
            "proposed_relation": "peer_classification",
            "direction": "one_to_many",
            "directional": False,
            "authority": "script_inference",
            "constraint_authority": "soft",
            "confidence": 0.75,
        },
        {
            "proposal_id": "R02",
            "subject": "A",
            "objects": ["B"],
            "proposed_relation": "directed_dependency",
            "direction": "subject_to_objects",
            "directional": True,
            "authority": "script_inference",
            "constraint_authority": "soft",
            "confidence": 0.75,
        },
        {
            "proposal_id": "R03",
            "subject": "B",
            "objects": ["C"],
            "proposed_relation": "directed_dependency",
            "direction": "subject_to_objects",
            "directional": True,
            "authority": "script_inference",
            "constraint_authority": "soft",
            "confidence": 0.75,
        },
    ])
    peer = verification["verdicts"][0]
    assert peer["verdict"] == "rejected"
    assert "PEER_CONFLICTS_WITH_CHILD_DIRECTION_CHAIN" in peer["conflict_codes"]
    assert all(item["relation"] != "peer_classification" for item in verification["verified_relationships"])


def test_topology_resolver_distinguishes_convergence_from_dependency_chain() -> None:
    convergence = resolve_semantic_topology([
        {"subject": "需求增长", "relation": "evidence_supports", "objects": ["统一基础"], "direction": "subject_to_objects", "confidence": 0.82, "constraint_authority": "soft"},
        {"subject": "资源分散", "relation": "evidence_supports", "objects": ["统一基础"], "direction": "subject_to_objects", "confidence": 0.82, "constraint_authority": "soft"},
    ], module_count=3)
    assert convergence["primary_topology"] == "support_convergence"

    chain = resolve_semantic_topology([
        {"subject": "行业节点", "relation": "directed_dependency", "objects": ["运营平台"], "direction": "subject_to_objects", "confidence": 0.82, "constraint_authority": "soft"},
        {"subject": "运营平台", "relation": "evidence_supports", "objects": ["协同载体"], "direction": "subject_to_objects", "confidence": 0.82, "constraint_authority": "soft"},
    ], module_count=3)
    assert chain["primary_topology"] == "dependency_chain"
    assert chain["eligibility"]["peer_set"]["allowed"] is False


def test_expression_selector_consumes_verified_topology_before_surface_keywords() -> None:
    topology = {
        "primary_topology": "dependency_chain",
        "confidence": 0.88,
        "constraint_authority": "soft",
    }
    decision = resolve_onscreen_expression(
        _page("行业节点", "运营平台", "协同载体"),
        page_mission="形成行业节点、运营平台、协同载体三类能力",
        actions=("行业节点 支撑 运营平台", "运营平台 支撑 协同载体"),
        semantic_topology=topology,
    )
    assert decision.form == "directed_dependency_2_6"
    assert decision.source == "verified_topology"


def test_unknown_verified_topology_stays_neutral() -> None:
    decision = resolve_onscreen_expression(
        _page("A", "B", "C", "D"),
        page_mission="说明四项内容",
        semantic_topology={
            "primary_topology": "unknown",
            "confidence": 0.42,
            "constraint_authority": "soft",
        },
    )
    assert decision.form == "neutral_structure_1_7"


def test_deck_validator_blocks_directed_semantics_flattened_to_parallel() -> None:
    pages = [
        {
            "page_id": "P05",
            "page_role": "content",
            "semantic_contract": {
                "topology": {
                    "primary_topology": "dependency_chain",
                    "constraint_authority": "strong",
                    "confidence": 0.88,
                }
            },
            "semantic_graph": {"topology": "parallel_set"},
            "expression_contract": {"form": "parallel_classification_3_6"},
        }
    ]
    report = audit_deck_structure_collapse(pages)
    assert report["status"] == "failed"
    assert report["blocking_issues"][0]["code"] == "DIRECTED_SEMANTICS_FLATTENED_TO_PARALLEL"


def test_deck_validator_can_recover_semantic_topology_from_compiled_graph() -> None:
    pages = [
        {
            "page_id": "P05",
            "page_role": "content",
            "semantic_graph": {
                "topology": "parallel_set",
                "business_relationships": [
                    {
                        "subject": "行业节点",
                        "relation": "directed_dependency",
                        "objects": ["运营平台"],
                        "direction": "subject_to_objects",
                        "confidence": 0.82,
                        "constraint_authority": "soft",
                    },
                    {
                        "subject": "运营平台",
                        "relation": "evidence_supports",
                        "objects": ["协同载体"],
                        "direction": "subject_to_objects",
                        "confidence": 0.82,
                        "constraint_authority": "soft",
                    },
                ],
            },
            "expression_contract": {"form": "parallel_classification_3_6"},
        }
    ]
    report = audit_deck_structure_collapse(pages)
    assert report["status"] == "failed"
    assert report["blocking_issues"][0]["code"] == "DIRECTED_SEMANTICS_FLATTENED_TO_PARALLEL"


def test_deck_validator_warns_on_peer_like_concentration_without_forcing_diversity() -> None:
    pages = [
        {
            "page_id": f"P{index:02d}",
            "page_role": "content",
            "semantic_contract": {
                "topology": {
                    "primary_topology": "peer_set",
                    "constraint_authority": "soft",
                    "confidence": 0.75,
                }
            },
            "semantic_graph": {"topology": "parallel_set"},
            "expression_contract": {"form": "parallel_classification_3_6"},
        }
        for index in range(1, 6)
    ]
    report = audit_deck_structure_collapse(pages)
    codes = {item["code"] for item in report["warnings"]}
    assert report["status"] == "passed"
    assert "DECK_PEER_LIKE_TOPOLOGY_CONCENTRATION" in codes
