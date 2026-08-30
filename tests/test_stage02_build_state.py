from __future__ import annotations

from pathlib import Path

from cyberppt.stage02_production.state import (
    FAILED,
    NEEDS_SVG_AUTHORING,
    NEEDS_VISUAL_REVIEW,
    PAGE_READY,
    classify_manifest,
)


def _audited_pair(tmp_path: Path, page: int = 1) -> dict:
    image = tmp_path / f"p{page}.png"
    image.write_bytes(b"image")
    return {
        "page_number": page,
        "full": {
            "path": str(image),
            "status": "Generated",
            "text_audit": {"valid": True},
        },
    }


def test_missing_authored_svg_is_action_not_failure(tmp_path: Path) -> None:
    pair = _audited_pair(tmp_path)
    report = classify_manifest({"pairs": [pair]})
    assert report["state"] == "needs_action"
    assert report["pages"][0]["state"] == NEEDS_SVG_AUTHORING
    assert report["failures"] == []


def test_pending_visual_review_is_action(tmp_path: Path) -> None:
    pair = _audited_pair(tmp_path)
    authored = tmp_path / "p1.svg"
    authored.write_text("<svg/>", encoding="utf-8")
    pair["authoring_svg"] = str(authored)
    pair["quick_page_checkpoint"] = {
        "status": "rendered_pending_visual_review",
        "preview_png": str(tmp_path / "preview.png"),
    }
    report = classify_manifest({"pairs": [pair]})
    assert report["pages"][0]["state"] == NEEDS_VISUAL_REVIEW
    assert report["failures"] == []


def test_passed_checkpoint_is_ready_for_assembly(tmp_path: Path) -> None:
    pair = _audited_pair(tmp_path)
    authored = tmp_path / "p1.svg"
    authored.write_text("<svg/>", encoding="utf-8")
    pair["authoring_svg"] = str(authored)
    pair["quick_page_checkpoint"] = {"status": "passed"}
    report = classify_manifest({"pairs": [pair]})
    assert report["state"] == "ready_for_assembly"
    assert report["pages"][0]["state"] == PAGE_READY


def test_checkpoint_failure_remains_real_failure(tmp_path: Path) -> None:
    pair = _audited_pair(tmp_path)
    authored = tmp_path / "p1.svg"
    authored.write_text("<svg/>", encoding="utf-8")
    pair["authoring_svg"] = str(authored)
    pair["quick_page_checkpoint"] = {"status": "failed", "error": "invalid geometry"}
    report = classify_manifest({"pairs": [pair]})
    assert report["state"] == FAILED
    assert report["failures"][0]["error"] == "invalid geometry"
