from scripts.dual_image_overlay.standalone_runtime import check_standalone_runtime


def test_production_runtime_is_local_only():
    report = check_standalone_runtime()
    assert report["valid"] is True, report
    assert report["runtime"]["source"] == "cyberppt_vendor"
    assert report["runtime"]["host_root"] is None
    assert "CyberPPT" in report["resources"]["svg_quality_checker"]

