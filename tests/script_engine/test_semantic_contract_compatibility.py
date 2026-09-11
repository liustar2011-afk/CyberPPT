from __future__ import annotations

from copy import deepcopy

from script_engine.semantic_contract import (
    FoundationIndex,
    audit_final_script_semantic_contract,
    collect_provenance_compatibility_diagnostics,
)


def _foundation(*, premise_role: str = "premise", response_role: str = "response") -> dict:
    return {
        "facts": [
            {
                "id": "F1",
                "statement": "现有团队已具备相关业务基础。",
                "argument_duty": premise_role,
                "semantic_status": "existing",
            },
            {
                "id": "F2",
                "statement": "方案拟由该团队承担新增责任。",
                "argument_duty": response_role,
                "semantic_status": "proposed",
            },
        ],
        "concepts": [],
        "relations": [],
        "arguments": [],
    }


def _page(
    *,
    claim_ref: str,
    evidence_ref: str,
    relation: str = "supports",
    item_text: str = "拟由该团队承担新增责任",
) -> dict:
    return {
        "contract": "cyberppt.final-script",
        "version": "1.1",
        "slides": [
            {
                "id": "P04",
                "page_type": "content",
                "source_refs": ["F1", "F2"],
                "onscreen": [
                    {
                        "id": "M04-01",
                        "heading": "页面主张",
                        "items": [
                            {
                                "id": "M04-01-I01",
                                "text": item_text,
                            }
                        ],
                        "provenance": {
                            "derivation": "direct",
                            "claim_refs": [claim_ref],
                            "bindings": [
                                {
                                    "target": "heading",
                                    "source_refs": [claim_ref],
                                    "relation": "expresses",
                                },
                                {
                                    "target": "M04-01-I01",
                                    "source_refs": [evidence_ref],
                                    "relation": relation,
                                },
                            ],
                        },
                    }
                ],
            }
        ],
    }


def _plan() -> dict:
    return {"pages": [{"id": "P04", "source_refs": ["F1", "F2"]}]}


def test_p04_response_cannot_support_existing_premise() -> None:
    final_script = _page(claim_ref="F1", evidence_ref="F2")

    diagnostics = collect_provenance_compatibility_diagnostics(
        final_script, _foundation()
    )

    blockers = [item for item in diagnostics if item.severity == "blocking"]
    assert len(blockers) == 1
    finding = blockers[0]
    assert finding.code == "EVIDENCE_ROLE_INCOMPATIBLE"
    assert finding.slide_id == "P04"
    assert finding.module_id == "M04-01"
    assert finding.target == "M04-01-I01"
    assert finding.claim_refs == ("F1",)
    assert finding.evidence_refs == ("F2",)
    assert finding.relation == "supports"


def test_role_compatibility_is_invariant_to_visible_synonym_rewrite() -> None:
    first = _page(
        claim_ref="F1",
        evidence_ref="F2",
        item_text="拟由该团队承担新增责任",
    )
    second = deepcopy(first)
    second["slides"][0]["onscreen"][0]["items"][0]["text"] = (
        "建议后续责任主体调整为该团队"
    )

    first_diagnostics = [
        finding.to_dict()
        for finding in collect_provenance_compatibility_diagnostics(
            first, _foundation()
        )
    ]
    second_diagnostics = [
        finding.to_dict()
        for finding in collect_provenance_compatibility_diagnostics(
            second, _foundation()
        )
    ]

    assert first_diagnostics == second_diagnostics


def test_existing_capability_may_support_proposed_responsibility() -> None:
    final_script = _page(claim_ref="F2", evidence_ref="F1")

    diagnostics = collect_provenance_compatibility_diagnostics(
        final_script, _foundation()
    )

    assert not [item for item in diagnostics if item.severity == "blocking"]


def test_unknown_typed_role_routes_to_review_instead_of_keyword_guess() -> None:
    final_script = _page(claim_ref="F1", evidence_ref="F2")
    foundation = _foundation(response_role="")
    foundation["facts"][1].pop("argument_duty")

    diagnostics = collect_provenance_compatibility_diagnostics(
        final_script, foundation
    )

    assert len(diagnostics) == 1
    assert diagnostics[0].code == "EVIDENCE_ROLE_UNKNOWN"
    assert diagnostics[0].severity == "review_required"


def test_unified_semantic_auditor_partitions_blockers_and_review_findings() -> None:
    final_script = _page(claim_ref="F1", evidence_ref="F2")
    blockers, warnings, structured = audit_final_script_semantic_contract(
        final_script,
        _plan(),
        _foundation(),
    )

    assert any("[EVIDENCE_ROLE_INCOMPATIBLE]" in issue for issue in blockers)
    # Phase 4's single entry also carries compatibility advisories. Structured
    # diagnostic severity is asserted independently below rather than requiring
    # the aggregate warning list to be empty.
    assert not any("EVIDENCE_ROLE_UNKNOWN" in warning for warning in warnings)
    assert any(
        finding["code"] == "EVIDENCE_ROLE_INCOMPATIBLE"
        and finding["severity"] == "blocking"
        for finding in structured
    )


def test_foundation_index_prefers_typed_status_and_role_fields() -> None:
    foundation = _foundation()
    foundation["facts"][0]["strength"] = "stated"
    index = FoundationIndex(foundation)

    assert index.status("F1") == "existing"
    assert index.argument_duty("F1") == "premise"
