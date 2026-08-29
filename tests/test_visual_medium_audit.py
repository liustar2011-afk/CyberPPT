from cyberppt.visual_medium_audit import audit_visual_medium_policy


def _page():
    return {
        "region_graph": {"regions": []},
        "final_text": [{"id": "T1", "region_id": "RG01"}],
        "image_plan": {"scene_policy": "auto"},
        "visual_medium_policy": {
            "preferred": "mixed",
            "allowed": [
                "business_scene",
                "object_illustration",
                "relationship_diagram",
                "data_visualization",
                "mixed",
            ],
            "scene_policy": "auto",
            "rationale": "Choose medium from page mission, drawable objects and Style lock.",
        },
        "semantic_graph": {"topology": "parallel_set"},
    }


def _codes(page):
    return [item["code"] for item in audit_visual_medium_policy(page)]


def test_medium_audit_accepts_valid_current_page():
    assert audit_visual_medium_policy(_page()) == []


def test_medium_audit_requires_policy_for_current_region_graph_page():
    page = _page()
    del page["visual_medium_policy"]
    assert _codes(page) == ["VISUAL_MEDIUM_POLICY_MISSING"]


def test_medium_audit_rejects_invalid_policy():
    page = _page()
    page["visual_medium_policy"]["preferred"] = "card_wall"
    assert _codes(page) == ["VISUAL_MEDIUM_POLICY_INVALID"]


def test_medium_audit_rejects_scene_policy_mismatch():
    page = _page()
    page["visual_medium_policy"]["scene_policy"] = "forbidden"
    page["visual_medium_policy"]["allowed"] = ["relationship_diagram"]
    page["visual_medium_policy"]["preferred"] = "relationship_diagram"
    assert _codes(page) == ["VISUAL_MEDIUM_SCENE_POLICY_MISMATCH"]


def test_medium_audit_does_not_compare_policy_to_topology():
    page = _page()
    page["semantic_graph"]["topology"] = "causal_convergence"
    assert audit_visual_medium_policy(page) == []


def test_legacy_page_without_region_graph_or_policy_is_compatible():
    page = _page()
    del page["region_graph"]
    del page["visual_medium_policy"]
    page["final_text"][0]["region_id"] = "R_RELATION"
    assert audit_visual_medium_policy(page) == []
