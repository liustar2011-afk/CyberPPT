"""Configurable quality gate for OCR forensic evidence."""

from __future__ import annotations

from difflib import SequenceMatcher
from typing import Any


def _ratio(observed: str, expected: str) -> float:
    return SequenceMatcher(None, "".join(observed.split()), "".join(expected.split())).ratio()


def evaluate_ocr_quality(forensics: dict[str, Any], *, policy: dict[str, Any]) -> dict[str, Any]:
    """Evaluate evidence without mutating raw OCR observations.

    Policy values are deliberately explicit so projects can tighten the gate
    without changing the rebuild implementation.
    """
    quality = forensics.get("quality") if isinstance(forensics.get("quality"), dict) else {}
    lines = [line for line in forensics.get("lines", []) if isinstance(line, dict)]
    expected = [str(item) for item in forensics.get("expected_lines", []) if str(item).strip()]
    observed = [str(line.get("final_text") or line.get("observed_text") or "") for line in lines]
    recall = quality.get("line_recall")
    if recall is None:
        recall = sum(max((_ratio(text, want) for text in observed), default=0.0) >= 0.62 for want in expected) / len(expected) if expected else 1.0
    low_ratio = quality.get("low_confidence_ratio")
    if low_ratio is None:
        threshold = float(policy.get("min_line_confidence", 0.8))
        low_ratio = sum(float(line.get("confidence", 1.0)) < threshold for line in lines) / len(lines) if lines else 0.0
    protected_failures = int(quality.get("protected_replacement_failures", 0) or 0)
    if not protected_failures:
        protected_failures = sum(
            1 for line in lines
            if isinstance(line.get("correction"), dict) and line["correction"].get("reason") == "protected_term" and line.get("review_required", True)
        )
    failures: list[str] = []
    review_count = sum(1 for line in lines if line.get("review_required"))
    if review_count and policy.get("fail_on_review_required", True):
        failures.append("review_required")
    artifacts = forensics.get("artifacts") if isinstance(forensics.get("artifacts"), dict) else {}
    required_artifacts = policy.get("required_artifacts", ["correction_audit", "evidence"])
    if policy.get("require_artifacts", False):
        for name in required_artifacts:
            if not artifacts.get(name):
                failures.append(f"missing_artifact:{name}")
    order = [line.get("reading_order") for line in lines if line.get("reading_order") is not None]
    if policy.get("fail_on_invalid_order", True) and order and (len(order) != len(set(order)) or order != sorted(order)):
        failures.append("invalid_reading_order")
    if policy.get("require_geometry_provenance", False):
        if any(not line.get("bbox") and not line.get("polygon") for line in lines): failures.append("missing_geometry")
        if not forensics.get("provenance") and not quality.get("provenance"): failures.append("missing_provenance")
    if float(recall) < float(policy.get("min_line_recall", 0.95)):
        failures.append("line_recall")
    if float(low_ratio) > float(policy.get("max_low_confidence_ratio", 0.10)):
        failures.append("low_confidence_ratio")
    if protected_failures > int(policy.get("max_protected_replacement_failures", 0)):
        failures.append("protected_replacement")
    metrics = {
        "line_recall": round(float(recall), 4),
        "low_confidence_ratio": round(float(low_ratio), 4),
        "protected_replacement_failures": protected_failures,
        "line_count": len(lines),
        "expected_line_count": len(expected),
        "review_required_count": review_count,
    }
    recovery = str(policy.get("recovery_command") or "python3 -m scripts.dual_image_overlay.rebuild_engine.editable_overlay_rebuild rebuild <manifest> --ocr-backend paddleocr-local --force-ocr --ocr-scale 2.0")
    return {"status": "passed" if not failures else "failed", "failures": failures, "metrics": metrics, "recovery_command": recovery}
