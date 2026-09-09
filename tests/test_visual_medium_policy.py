from pathlib import Path
import json

import jsonschema
import pytest

from cyberppt.visual_medium_policy import (
    default_visual_medium_policy,
    resolve_visual_medium_policy,
    validate_visual_medium_policy,
)


ROOT = Path(__file__).resolve().parents[1]
SCHEMA = ROOT / "vendor" / "skills" / "ppt-visual-structure-designer" / "assets" / "visual-medium-policy.schema.json"


def test_auto_policy_is_topology_neutral_and_does_not_default_to_mixed():
    policy = default_visual_medium_policy("auto")
    assert policy.preferred != "mixed"
    assert set(policy.allowed) == {
        "business_scene",
        "object_illustration",
        "relationship_diagram",
        "data_visualization",
        "mixed",
    }
    assert policy.confidence >= 0.5


def test_forbidden_scene_policy_keeps_non_scene_visual_media_and_forbids_scene():
    policy = default_visual_medium_policy("forbidden")
    assert "business_scene" not in policy.allowed
    assert "business_scene" in policy.forbidden
    assert "object_illustration" in policy.allowed
    assert "relationship_diagram" in policy.allowed
    assert "data_visualization" in policy.allowed


def test_required_scene_policy_prefers_business_scene():
    policy = default_visual_medium_policy("required")
    assert policy.preferred == "business_scene"
    assert "business_scene" in policy.allowed
    assert policy.confidence > 0.8


def test_explicit_policy_must_match_scene_policy():
    with pytest.raises(ValueError, match="must match image scene_policy"):
        resolve_visual_medium_policy(
            {
                "preferred": "relationship_diagram",
                "allowed": ["relationship_diagram"],
                "scene_policy": "forbidden",
                "rationale": "Use a relation-bearing visual field.",
            },
            scene_policy="auto",
        )


def test_forbidden_policy_rejects_business_scene():
    with pytest.raises(ValueError, match="cannot allow business_scene"):
        validate_visual_medium_policy(
            {
                "preferred": "business_scene",
                "allowed": ["business_scene"],
                "scene_policy": "forbidden",
                "rationale": "Invalid scene request.",
            }
        )


def test_schema_accepts_valid_medium_policy_v2():
    schema = json.loads(SCHEMA.read_text(encoding="utf-8"))
    jsonschema.Draft202012Validator(schema).validate(
        default_visual_medium_policy("allowed").to_dict()
    )


def test_legacy_explicit_policy_is_normalized_to_v2_fields():
    policy = validate_visual_medium_policy(
        {
            "preferred": "relationship_diagram",
            "allowed": ["relationship_diagram", "object_illustration"],
            "scene_policy": "forbidden",
            "rationale": "Explicit legacy policy.",
        }
    )
    assert policy.preferred == "relationship_diagram"
    assert policy.secondary == "object_illustration"
    assert "business_scene" in policy.forbidden
    assert policy.scores
