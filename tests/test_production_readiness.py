from scripts.dual_image_overlay.production_readiness import (
    build_production_readiness,
    summarize_page_understanding_readiness,
)


def test_production_readiness_requires_all_required_tools():
    readiness = build_production_readiness(
        stage="02-production-build",
        artifacts={
            "source_capture": "/tmp/source_capture.json",
            "semantic_binding": None,
            "semantic_plan": "/tmp/semantic_plan.json",
            "container_workspace": "/tmp/container_workspace.json",
            "workspace_assignment": "/tmp/workspace_assignment.json",
            "office_textbox_fit": "/tmp/office_textbox_fit.json",
            "editable_pptx": "/tmp/out.pptx",
            "render_compare": "/tmp/render_compare.json",
            "qa_registry": "/tmp/page_quality_report.json",
        },
        reports={},
    )

    assert readiness["status"] == "production_rework_required"
    assert readiness["tool_consumption"]["semantic_binding"]["ran"] is False
    assert readiness["checks"]["all_required_tools_consumed"] is False


def test_production_readiness_passes_when_all_required_tools_have_artifacts():
    artifacts = {
        "source_capture": "/tmp/source_capture.json",
        "semantic_binding": "/tmp/semantic_binding.json",
        "semantic_plan": "/tmp/semantic_plan.json",
        "scene_graph": "/tmp/scene_graph.json",
        "visual_registry": "/tmp/visual_registry",
        "container_workspace": "/tmp/container_workspace.json",
        "workspace_assignment": "/tmp/workspace_assignment.json",
        "office_textbox_fit": "/tmp/office_textbox_fit.json",
        "editable_pptx": "/tmp/out.pptx",
        "render_compare": "/tmp/render_compare.json",
        "qa_registry": "/tmp/page_quality_report.json",
    }

    readiness = build_production_readiness(stage="02-production-build", artifacts=artifacts, reports={})

    assert readiness["status"] == "production_ready"
    assert readiness["checks"]["all_required_tools_consumed"] is True


def test_production_readiness_blocks_failed_quality_reports():
    artifacts = {
        "source_capture": "/tmp/source_capture.json",
        "semantic_binding": "/tmp/semantic_binding.json",
        "semantic_plan": "/tmp/semantic_plan.json",
        "scene_graph": "/tmp/scene_graph.json",
        "visual_registry": "/tmp/visual_registry",
        "container_workspace": "/tmp/container_workspace.json",
        "workspace_assignment": "/tmp/workspace_assignment.json",
        "office_textbox_fit": "/tmp/office_textbox_fit.json",
        "editable_pptx": "/tmp/out.pptx",
        "render_compare": "/tmp/render_compare.json",
        "qa_registry": "/tmp/page_quality_report.json",
    }

    readiness = build_production_readiness(
        stage="02-production-build",
        artifacts=artifacts,
        reports={
            "office_textbox_fit": {"schema": "cyberppt.dual_image.office_textbox_fit.v1", "valid": False},
            "render_compare": {"schema": "cyberppt.render_compare.v1", "passed": False},
            "qa_registry": {"schema": "cyberppt.dual_image.page_quality_report.v1", "valid": False},
        },
    )

    assert readiness["status"] == "production_rework_required"
    assert readiness["checks"]["all_consumed_reports_pass"] is False
    assert {"tool": "qa_registry", "code": "tool_report_failed"} in readiness["blocking_errors"]


def test_production_readiness_requires_page_understanding_consumption() -> None:
    summary = summarize_page_understanding_readiness(
        {
            "inputs": {
                "page_understanding_available": True,
                "page_understanding_count": 2,
                "page_understanding_paths": [
                    "/tmp/page_012_page_understanding.json",
                    "/tmp/page_013_page_understanding.json",
                ],
            },
            "pages": [{"page_number": 12}, {"page_number": 13}],
        }
    )

    assert summary["page_understanding_available"] is True
    assert summary["page_understanding_consumed"] is False
    assert summary["page_understanding_consumed_count"] == 0
    assert summary["script_truth_verified"] is False
    assert summary["fit_review_queue_clear"] is False


def test_production_readiness_blocks_advertised_unconsumed_page_understanding() -> None:
    artifacts = {
        "source_capture": "/tmp/source_capture.json",
        "semantic_binding": "/tmp/semantic_binding.json",
        "semantic_plan": "/tmp/semantic_plan.json",
        "scene_graph": "/tmp/scene_graph.json",
        "visual_registry": "/tmp/visual_registry",
        "container_workspace": "/tmp/container_workspace.json",
        "workspace_assignment": "/tmp/workspace_assignment.json",
        "office_textbox_fit": "/tmp/office_textbox_fit.json",
        "editable_pptx": "/tmp/out.pptx",
        "render_compare": "/tmp/render_compare.json",
        "qa_registry": "/tmp/page_quality_report.json",
    }

    readiness = build_production_readiness(
        stage="02-production-build",
        artifacts=artifacts,
        reports={
            "source_capture": {
                "inputs": {
                    "page_understanding_available": True,
                    "page_understanding_count": 1,
                    "page_understanding_paths": ["/tmp/page_013_page_understanding.json"],
                },
                "pages": [{"page_number": 13}],
            }
        },
    )

    assert readiness["valid"] is False
    assert readiness["status"] == "production_rework_required"
    assert {"tool": "source_capture", "code": "page_understanding_not_consumed"} in readiness["blocking_errors"]
    assert {"tool": "source_capture", "code": "script_truth_not_verified"} in readiness["blocking_errors"]
    assert {
        "tool": "source_capture",
        "code": "page_understanding_fit_review_queue_not_clear",
    } in readiness["blocking_errors"]


def test_production_readiness_malformed_page_understanding_count_fails_closed() -> None:
    summary = summarize_page_understanding_readiness(
        {
            "inputs": {
                "page_understanding_available": True,
                "page_understanding_count": "not-a-number",
                "page_understanding_paths": ["/tmp/page_013_page_understanding.json"],
            },
            "pages": [{"page_number": 13}],
        }
    )

    assert summary["page_understanding_available"] is True
    assert summary["page_understanding_count"] == 0
    assert summary["page_understanding_consumed"] is False
    assert summary["script_truth_verified"] is False
    assert summary["fit_review_queue_clear"] is False
    assert summary["reason"] == "invalid_page_understanding_count"


def test_production_readiness_malformed_text_block_count_fails_closed() -> None:
    summary = summarize_page_understanding_readiness(
        {
            "inputs": {
                "page_understanding_available": True,
                "page_understanding_count": 1,
                "page_understanding_paths": ["/tmp/page_013_page_understanding.json"],
            },
            "pages": [
                {
                    "page_number": 13,
                    "page_understanding": {
                        "path": "/tmp/page_013_page_understanding.json",
                        "text_block_count": "bad",
                        "script_truth_verified": True,
                        "fit_review_queue_clear": True,
                    },
                }
            ],
        }
    )

    assert summary["page_understanding_available"] is True
    assert summary["page_understanding_consumed"] is True
    assert summary["script_truth_verified"] is False
    assert summary["fit_review_queue_clear"] is True
    assert {"code": "invalid_page_understanding_text_block_count"} in summary["issues"]


def test_production_readiness_float_text_block_count_fails_closed() -> None:
    summary = summarize_page_understanding_readiness(
        {
            "inputs": {
                "page_understanding_available": True,
                "page_understanding_count": 1,
                "page_understanding_paths": ["/tmp/page_013_page_understanding.json"],
            },
            "pages": [
                {
                    "page_number": 13,
                    "page_understanding": {
                        "path": "/tmp/page_013_page_understanding.json",
                        "text_block_count": 1.9,
                        "script_truth_verified": True,
                        "fit_review_queue_clear": True,
                    },
                }
            ],
        }
    )

    assert summary["page_understanding_available"] is True
    assert summary["page_understanding_consumed"] is True
    assert summary["script_truth_verified"] is False
    assert summary["fit_review_queue_clear"] is True
    assert {"code": "invalid_page_understanding_text_block_count"} in summary["issues"]


def test_production_readiness_exposes_page_understanding_checks() -> None:
    artifacts = {
        "source_capture": "/tmp/source_capture.json",
        "semantic_binding": "/tmp/semantic_binding.json",
        "semantic_plan": "/tmp/semantic_plan.json",
        "scene_graph": "/tmp/scene_graph.json",
        "visual_registry": "/tmp/visual_registry",
        "container_workspace": "/tmp/container_workspace.json",
        "workspace_assignment": "/tmp/workspace_assignment.json",
        "office_textbox_fit": "/tmp/office_textbox_fit.json",
        "editable_pptx": "/tmp/out.pptx",
        "render_compare": "/tmp/render_compare.json",
        "qa_registry": "/tmp/page_quality_report.json",
    }

    readiness = build_production_readiness(
        stage="02-production-build",
        artifacts=artifacts,
        reports={
            "source_capture": {
                "inputs": {
                    "page_understanding_available": True,
                    "page_understanding_count": 1,
                    "page_understanding_paths": ["/tmp/page_013_page_understanding.json"],
                },
                "pages": [
                    {
                        "page_number": 13,
                        "page_understanding": {
                            "path": "/tmp/page_013_page_understanding.json",
                            "text_block_count": 1,
                            "script_truth_verified": True,
                            "fit_review_queue_clear": True,
                        },
                    }
                ],
            }
        },
    )

    assert readiness["checks"]["page_understanding_available"] is True
    assert readiness["checks"]["page_understanding_consumed"] is True
    assert readiness["checks"]["script_truth_verified"] is True
    assert readiness["checks"]["fit_review_queue_clear"] is True
    assert readiness["page_understanding_readiness"]["page_understanding_consumed_count"] == 1
