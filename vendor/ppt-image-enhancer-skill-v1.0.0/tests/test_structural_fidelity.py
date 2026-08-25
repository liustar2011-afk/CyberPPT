from __future__ import annotations

import sys
from pathlib import Path

import cv2
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from ppt_image_enhancer.pipeline import _structural_fidelity


def _diagram() -> np.ndarray:
    image = np.full((240, 480, 3), 245, dtype=np.uint8)
    cv2.rectangle(image, (30, 40), (210, 105), (20, 70, 140), 3)
    cv2.rectangle(image, (270, 135), (450, 200), (20, 70, 140), 3)
    cv2.putText(image, "DATA", (65, 84), cv2.FONT_HERSHEY_SIMPLEX, 1.1, (5, 20, 60), 2)
    cv2.arrowedLine(image, (210, 72), (270, 165), (20, 70, 140), 3)
    return image


def test_structural_fidelity_accepts_conservative_resize() -> None:
    reference = _diagram()
    result = cv2.GaussianBlur(reference, (0, 0), 0.25)
    assert _structural_fidelity(reference, result, {})["valid"]


def test_structural_fidelity_rejects_repositioned_and_invented_edges() -> None:
    reference = _diagram()
    corrupted = np.roll(reference, 90, axis=1)
    cv2.putText(corrupted, "HALLUCINATED", (30, 150), cv2.FONT_HERSHEY_SIMPLEX, 1.0, (0, 0, 0), 3)
    metrics = _structural_fidelity(reference, corrupted, {})
    assert not metrics["valid"]
    assert metrics["correlation"] < 0.92
