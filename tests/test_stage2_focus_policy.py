from cyberppt.commands.visual_structure_stage import _build_executable_page
from cyberppt.onscreen_expression import expression_constraints


def _expression_fit(form: str):
    constraints = expression_constraints(form)
    return {
        "form": form,
        "constraint_status": "default_profile",
        "satisfied_constraints": list(constraints["required_features"]),
        "reading_relation": str(constraints["relation_pattern"]),
        "balance_strategy": str(constraints["balance_requirement"]),
        "changed_constraints": [],
        "deviation_reason": "",
    }


def _page(topology: str, grammar: list[str], form: str):
    source = {
        "page_id": "p01",
        "page_number": 1,
        "page_title": "Title",
        "prompt_mode": "semantic_brief",
        "page_mission": "Explain the relationship between two approved evidence units.",
        "core_judgment": "The evidence units form the approved page relationship.",
        "locked_text_items": [
            {"text_id": "P01-T01", "text": "Evidence A"},
            {"text_id": "P01-T02", "text": "Evidence B"},
        ],
        "business_relationships": [],
        "expression_constraints": expression_constraints(form),
    }
    decision = {
        "page_id": "p01",
        "evidence_units": [
            {"key": "a", "summary": "Evidence A", "text_ids": ["P01-T01"]},
            {"key": "b", "summary": "Evidence B", "text_ids": ["P01-T02"]},
        ],
        "candidates": [{
            "id": "c1",
            "visual_thesis": "The two evidence units visibly preserve their approved relationship.",
            "semantic_focus": {"kind": "entity", "evidence_key": "a"},
            "reading_sequence": ["a", "b"],
            "spatial_grammar": grammar,
            "topology": topology,
            "direction": "left_to_right",
            "visual_intent_type": "relationship_field",
            "expression_fit": _expression_fit(form),
        }],
        "selected_candidate": "c1",
    }
    return _build_executable_page(source, decision)


def test_parallel_set_compiles_peer_field_focus_policy():
    page = _page("parallel_set", ["peer"], "framework_4")
    assert page["visual_decision"]["focus_policy"] == "peer_field"
    assert page["visual_decision"]["visual_center_count"] == 2


def test_convergence_compiles_single_anchor_focus_policy():
    page = _page("causal_convergence", ["convergence"], "pyramid_argument")
    assert page["visual_decision"]["focus_policy"] == "single_anchor"


def test_candidate_can_explicitly_select_supported_focus_policy():
    page = _page("governance_boundary", ["boundary"], "flow_3_5")
    # topology default is paired_focus
    assert page["visual_decision"]["focus_policy"] == "paired_focus"


def test_parallel_set_keeps_all_peers_co_primary_without_result_binding():
    page = _page("parallel_set", ["peer"], "framework_4")
    assert {item["role"] for item in page["semantic_graph"]["nodes"]} == {"evidence"}
    assert {item["kind"] for item in page["evidence_units"]} == {"fact"}
    assert set(page["structural_decision"]["primary_refs"]) == {"E1", "E2"}
    assert page["structural_decision"]["secondary_refs"] == []
    assert all(item["binding"] == "embedded" for item in page["structural_decision"]["text_bindings"])


def test_peer_field_focus_audit_accepts_co_primary_peers():
    from cyberppt.visual_structure_contract import _audit_focus_competition

    page = _page("parallel_set", ["peer"], "framework_4")
    issues = []
    def issue(code, message, page_id=None):
        issues.append((code, message, page_id))
    result = _audit_focus_competition(page, issue, "p01")
    assert result["status"] == "passed"
    assert issues == []


def test_peer_field_focus_audit_rejects_invented_result_binding():
    from cyberppt.visual_structure_contract import _audit_focus_competition

    page = _page("parallel_set", ["peer"], "framework_4")
    page["structural_decision"]["text_bindings"][0]["binding"] = "result"
    issues = []
    def issue(code, message, page_id=None):
        issues.append((code, message, page_id))
    result = _audit_focus_competition(page, issue, "p01")
    assert result["status"] == "failed"
    assert issues[0][0] == "FOCUS_COMPETITION_DETECTED"
