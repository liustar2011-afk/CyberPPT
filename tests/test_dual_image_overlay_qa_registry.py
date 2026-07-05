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


def test_dual_image_rule_requires_full_and_background_files(tmp_path: Path) -> None:
    full = tmp_path / "page_full.png"
    background = tmp_path / "page_background.png"
    full.write_bytes(b"full")
    background.write_bytes(b"background")

    report = build_page_quality_report(
        stage="template",
        page_number=6,
        project_path=tmp_path,
        artifacts={"pair_manifest": str(tmp_path / "page_image_pairs.json")},
        reports={
            "pair_manifest": {
                "pairs": [
                    {
                        "page_number": 6,
                        "full": {"path": str(full)},
                        "background": {"path": str(background)},
                    }
                ]
            }
        },
        rules=[
            {
                "id": "template.dual_image_required",
                "stage": "template",
                "severity": "error",
                "kind": "dual_image_pair_required",
                "report": "pair_manifest",
                "evidence_required": False,
            }
        ],
    )

    assert report["valid"] is True
    assert report["checks"][0]["observed"]["pair_count"] == 1


def test_min_font_size_rule_blocks_template_text_below_floor(tmp_path: Path) -> None:
    report = build_page_quality_report(
        stage="template",
        page_number=6,
        project_path=tmp_path,
        artifacts={"source_capture": str(tmp_path / "source_capture.json")},
        reports={
            "source_capture": {
                "pages": [
                    {
                        "page_number": 6,
                        "text_objects": [
                            {
                                "text": "审计追踪",
                                "style": {"font_size_pt": 8.5, "typography_role": "body"},
                            }
                        ],
                    }
                ]
            }
        },
        rules=[
            {
                "id": "template.min_font_after_template",
                "stage": "template",
                "severity": "error",
                "kind": "min_font_size",
                "report": "source_capture",
                "minimum_pt": 9,
                "evidence_required": False,
            }
        ],
    )

    assert report["valid"] is False
    assert report["blocking_errors"][0]["id"] == "template.min_font_after_template"
    assert report["blocking_errors"][0]["observed"]["below_minimum"][0]["font_size"] == 8.5


def test_min_font_size_rule_converts_svg_px_to_exported_pt(tmp_path: Path) -> None:
    report = build_page_quality_report(
        stage="template",
        page_number=6,
        project_path=tmp_path,
        artifacts={"source_capture": str(tmp_path / "source_capture.json")},
        reports={
            "source_capture": {
                "pages": [
                    {
                        "page_number": 6,
                        "text_objects": [
                            {
                                "text": "项目履约：业绩、合同、质量安全",
                                "style": {"font_size_px": 9.72, "typography_role": "body"},
                            }
                        ],
                    }
                ]
            }
        },
        rules=[
            {
                "id": "template.min_font_after_template",
                "stage": "template",
                "severity": "error",
                "kind": "min_font_size",
                "report": "source_capture",
                "minimum_pt": 9,
                "evidence_required": False,
            }
        ],
    )

    assert report["valid"] is False
    assert report["blocking_errors"][0]["observed"]["below_minimum"][0]["font_size"] == 7.29


def test_semantic_peer_style_rule_blocks_mixed_weight_peers(tmp_path: Path) -> None:
    report = build_page_quality_report(
        stage="template",
        page_number=6,
        project_path=tmp_path,
        artifacts={"source_capture": str(tmp_path / "source_capture.json")},
        reports={
            "source_capture": {
                "pages": [
                    {
                        "page_number": 6,
                        "text_objects": [
                            {"text": "基础评估服务", "style": {"typography_role": "service_title", "font_weight": "700"}},
                            {"text": "专项评估服务", "style": {"typography_role": "service_title", "font_weight": "400"}},
                        ],
                    }
                ]
            }
        },
        rules=[
            {
                "id": "template.semantic_weight_consistency",
                "stage": "template",
                "severity": "error",
                "kind": "semantic_peer_style",
                "report": "source_capture",
                "style_field": "font_weight",
                "evidence_required": False,
            }
        ],
    )

    assert report["valid"] is False
    assert "service_title" in report["blocking_errors"][0]["observed"]["inconsistent"]


def test_container_workspace_rule_requires_slots(tmp_path: Path) -> None:
    evidence = tmp_path / "container_workspace_index.json"
    evidence.write_text('{"valid": false}\n', encoding="utf-8")

    report = build_page_quality_report(
        stage="template",
        page_number=6,
        project_path=tmp_path,
        artifacts={"container_workspace": str(evidence)},
        reports={
            "container_workspace": {
                "schema": "cyberppt.dual_image.container_workspace.v1",
                "valid": False,
                "container_count": 1,
                "slot_count": 0,
                "error_count": 1,
            }
        },
        rules=[
            {
                "id": "template.container_workspace_pass",
                "stage": "template",
                "severity": "error",
                "kind": "container_workspace_required",
                "report": "container_workspace",
                "evidence_required": True,
            }
        ],
    )

    assert report["valid"] is False
    assert report["blocking_errors"][0]["id"] == "template.container_workspace_pass"
    assert report["blocking_errors"][0]["observed"]["slot_count"] == 0


def test_workspace_assignment_rule_requires_assigned_slot(tmp_path: Path) -> None:
    evidence = tmp_path / "workspace_assignment_index.json"
    evidence.write_text('{"valid": false}\n', encoding="utf-8")

    report = build_page_quality_report(
        stage="template",
        page_number=6,
        project_path=tmp_path,
        artifacts={"workspace_assignment": str(evidence)},
        reports={
            "workspace_assignment": {
                "schema": "cyberppt.dual_image.workspace_assignment.v1",
                "valid": False,
                "assignment_count": 1,
                "error_count": 1,
                "assignments": [
                    {
                        "text_index": 0,
                        "text": "证书审核",
                        "assigned_slot": None,
                        "inside_slot": False,
                    }
                ],
            }
        },
        rules=[
            {
                "id": "template.workspace_assignment_pass",
                "stage": "template",
                "severity": "error",
                "kind": "workspace_assignment_required",
                "report": "workspace_assignment",
                "evidence_required": True,
            }
        ],
    )

    assert report["valid"] is False
    assert report["blocking_errors"][0]["id"] == "template.workspace_assignment_pass"
    assert report["blocking_errors"][0]["observed"]["assignment_count"] == 1


def test_occupied_zone_avoidance_rule_blocks_intersecting_slots(tmp_path: Path) -> None:
    evidence = tmp_path / "container_workspace_index.json"
    evidence.write_text('{"valid": true}\n', encoding="utf-8")

    report = build_page_quality_report(
        stage="template",
        page_number=6,
        project_path=tmp_path,
        artifacts={"container_workspace": str(evidence)},
        reports={
            "container_workspace": {
                "schema": "cyberppt.dual_image.container_workspace.v1",
                "valid": True,
                "containers": [
                    {
                        "id": "card",
                        "occupied_zones": [
                            {
                                "id": "icon",
                                "source": "scene_graph",
                                "bbox": {"x": 10, "y": 10, "w": 20, "h": 20},
                            }
                        ],
                        "work_slots": [
                            {
                                "id": "card_body_slot",
                                "bbox": {"x": 15, "y": 15, "w": 50, "h": 20},
                            }
                        ],
                    }
                ],
            }
        },
        rules=[
            {
                "id": "template.occupied_zone_avoidance_pass",
                "stage": "template",
                "severity": "error",
                "kind": "occupied_zone_avoidance",
                "report": "container_workspace",
                "evidence_required": True,
            }
        ],
    )

    assert report["valid"] is False
    assert report["blocking_errors"][0]["id"] == "template.occupied_zone_avoidance_pass"
    assert report["blocking_errors"][0]["observed"]["failure_count"] == 1
