import json
from pathlib import Path

from scripts.dual_image_overlay.rebuild_engine.controlled_correction import correct_lines


ROOT = Path(__file__).parents[1]
POLICY = ROOT / "config/ocr/correction_policy.json"
PROTECTED = ROOT / "config/ocr/protected_terms.json"


def test_correction_is_reversible_and_protected_term_is_unchanged(tmp_path):
    lines = [{"observed_text": "经菅管理", "char_candidates": [{"from": "菅", "to": "营", "confidence": .997, "scales": ["small", "large"]}]}]
    corrected = correct_lines(lines, policy_path=POLICY, protected_terms_path=PROTECTED)
    assert corrected[0]["final_text"] == "经营管理"
    assert corrected[0]["correction"]["reversible"] is True


def test_protected_span_blocks_candidate(tmp_path):
    protected = tmp_path / "protected.json"
    protected.write_text(json.dumps({"terms": ["菅理"]}), encoding="utf-8")
    lines = [{"observed_text": "经菅理", "char_candidates": [{"from": "菅", "to": "营", "confidence": .999}]}]
    result = correct_lines(lines, policy_path=POLICY, protected_terms_path=protected)[0]
    assert result["final_text"] == "经菅理"
    assert result["review_required"] is True


def test_missing_scale_agreement_preserves_original():
    lines = [{"observed_text": "经菅管理", "char_candidates": [{"from": "菅", "to": "营", "confidence": .999}]}]
    result = correct_lines(lines, policy_path=POLICY, protected_terms_path=PROTECTED)[0]
    assert result["final_text"] == result["observed_text"]
    assert result["review_required"] is True


def test_mixed_candidates_apply_safe_change_but_require_review():
    lines = [{"observed_text": "经菅理", "char_candidates": [
        {"from": "菅", "to": "营", "confidence": .999, "scales": ["small", "large"]},
        {"from": "理", "to": "里", "confidence": .7, "scales": ["small", "large"]},
    ]}]
    result = correct_lines(lines, policy_path=POLICY, protected_terms_path=PROTECTED)[0]
    assert result["final_text"] == "经营理"
    assert result["correction"]["applied"] is True
    assert result["review_required"] is True


def test_low_confidence_preserves_original_and_requests_review():
    lines = [{"observed_text": "经菅管理", "char_candidates": [{"from": "菅", "to": "营", "confidence": .8}]}]
    result = correct_lines(lines, policy_path=POLICY, protected_terms_path=PROTECTED)[0]
    assert result["final_text"] == result["observed_text"]
    assert result["review_required"] is True
