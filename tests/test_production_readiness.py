from scripts.dual_image_overlay.production_readiness import build_production_readiness


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
