import pytest

from cyberppt.acceptance_contract import AcceptanceSpec, build_acceptance_spec


def test_default_acceptance_contract_is_strict():
    spec = build_acceptance_spec()
    assert spec.exact_copy_coverage == 1.0
    assert spec.extra_text_count == 0
    assert spec.region_ownership == "all_declared_copy_stays_in_assigned_macro_region"
    assert spec.relationship_accuracy == "source_supported_relationships_only"
    assert spec.hierarchy_preservation == "preserve_declared_hierarchy"
    assert spec.minimum_readability == "readable_at_normal_slide_view"
    assert spec.forbidden_structure_absence is True
    assert spec.style_lock_conformance is True


def test_explicit_extra_text_budget_can_be_projected():
    spec = build_acceptance_spec(allowed_extra_text_count=2)
    assert spec.extra_text_count == 2


def test_exact_copy_target_cannot_be_reduced():
    with pytest.raises(ValueError, match="must be 1.0"):
        AcceptanceSpec(exact_copy_coverage=0.99)


def test_forbidden_structure_and_style_lock_require_true():
    with pytest.raises(ValueError, match="forbidden structure absence"):
        AcceptanceSpec(forbidden_structure_absence=False)
    with pytest.raises(ValueError, match="style lock conformance"):
        AcceptanceSpec(style_lock_conformance=False)
