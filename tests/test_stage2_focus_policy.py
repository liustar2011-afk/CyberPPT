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
    assert page["visual_decision"]["visual_center_count"] == 1


def test_convergence_compiles_single_anchor_focus_policy():
    page = _page("causal_convergence", ["convergence"], "pyramid_argument")
    assert page["visual_decision"]["focus_policy"] == "single_anchor"


def test_candidate_can_explicitly_select_supported_focus_policy():
    page = _page("governance_boundary", ["boundary"], "flow_3_5")
    # topology default is paired_focus
    assert page["visual_decision"]["focus_policy"] == "paired_focus"
