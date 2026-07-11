from scripts.dual_image_overlay.rebuild_engine.ocr_quality_gate import evaluate_ocr_quality


POLICY = {"min_line_recall": 0.95, "max_low_confidence_ratio": 0.10, "max_protected_replacement_failures": 0}


def test_quality_gate_passes_clean_evidence():
    report = evaluate_ocr_quality({"quality": {"line_recall": 1.0, "low_confidence_ratio": 0.0}}, policy=POLICY)
    assert report["status"] == "passed"
    assert report["failures"] == []


def test_quality_gate_rejects_missing_lines():
    report = evaluate_ocr_quality({"quality": {"line_recall": .72, "low_confidence_ratio": .04}}, policy=POLICY)
    assert report["status"] == "failed"
    assert "line_recall" in report["failures"]


def test_quality_gate_rejects_protected_replacement_failure():
    report = evaluate_ocr_quality(
        {"lines": [{"review_required": True, "correction": {"reason": "protected_term"}}]},
        policy=POLICY,
    )
    assert report["status"] == "failed"
    assert "protected_replacement" in report["failures"]


def test_quality_gate_recovery_command_has_executable_two_x_flag():
    report = evaluate_ocr_quality({"quality": {"line_recall": .5}}, policy=POLICY)
    assert "--ocr-scale 2.0" in report["recovery_command"]
