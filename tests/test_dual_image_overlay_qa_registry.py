from __future__ import annotations

from pathlib import Path

from scripts.dual_image_overlay.qa_registry import build_page_quality_report


def test_page_quality_report_blocks_failed_registered_rule(tmp_path: Path) -> None:
    evidence = tmp_path / "layout_qa.json"
    evidence.write_text('{"valid": false}\n', encoding="utf-8")

    report = build_page_quality_report(
        stage="overlay",
        page_number=6,
        project_path=tmp_path,
        artifacts={"layout_qa": str(evidence)},
        reports={"layout_qa": {"schema": "example", "valid": False, "error_count": 1}},
        rules=[
            {
                "id": "overlay.layout_qa_pass",
                "stage": "overlay",
                "severity": "error",
                "kind": "report_valid",
                "report": "layout_qa",
                "evidence_required": True,
            }
        ],
    )

    assert report["schema"] == "cyberppt.dual_image.page_quality_report.v1"
    assert report["valid"] is False
    assert report["blocking_error_count"] == 1
    assert report["blocking_errors"][0]["id"] == "overlay.layout_qa_pass"


def test_page_quality_report_treats_warning_as_non_blocking(tmp_path: Path) -> None:
    report = build_page_quality_report(
        stage="template",
        page_number=6,
        project_path=tmp_path,
        artifacts={"rendered_preview": None},
        reports={},
        rules=[
            {
                "id": "template.rendered_preview_available",
                "stage": "template",
                "severity": "warning",
                "kind": "artifact_exists",
                "artifact": "rendered_preview",
                "evidence_required": True,
            }
        ],
    )

    assert report["valid"] is True
    assert report["warning_count"] == 1
    assert report["warnings"][0]["id"] == "template.rendered_preview_available"
