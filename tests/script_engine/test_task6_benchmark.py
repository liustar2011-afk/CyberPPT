from benchmarks.run import DEFAULT_FIXTURE, run_benchmark


def test_task6_benchmark_separates_shape_coverage_from_real_project_graduation() -> None:
    report = run_benchmark(DEFAULT_FIXTURE)

    assert len(report["shape_results"]) == 5
    assert all(item["passed"] for item in report["shape_results"])
    assert report["source_artifact_boundary"]["created_files"] == [
        "script/.cache/source-index.json"
    ]
    assert report["field_reduction"]["reduction"] >= 0.4
    assert report["real_projects_reaching_stage02_handoff"] < 3
    assert report["graduated"] is False
    assert report["default_plan_contract"] == 1
    assert report["technical_judgment"] == "SUPPORT WITH CONDITIONS"
