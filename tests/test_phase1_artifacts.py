from __future__ import annotations

import json
from pathlib import Path

from cyberppt.commands.init_project import init_project
from cyberppt.phase1.artifacts import Phase1Run, phase1_paths, write_phase1_run


def test_phase1_paths_are_gate_scoped(tmp_path: Path) -> None:
    paths = phase1_paths(tmp_path / "project", "source_analysis")

    assert paths.root.name == "source_analysis"
    assert paths.source_bundle_json.name == "source_bundle.json"
    assert paths.source_bundle_markdown.name == "source_bundle.md"
    assert paths.chunks_dir.name == "chunks"
    assert paths.prompt.name == "source_analysis_prompt.md"
    assert paths.raw_output.name == "source_analysis_raw.json"
    assert paths.candidate.name == "source_analysis.md"
    assert paths.grounding_report.name == "source_analysis_grounding.json"
    assert paths.run_manifest.name == "run.json"


def test_init_project_creates_phase1_model_run_directory(tmp_path: Path) -> None:
    project = tmp_path / "project"

    init_project(project)

    assert (project / "workbench/stages/01-analysis/model-runs").is_dir()


def test_write_phase1_run_persists_schema_and_resume_metadata(tmp_path: Path) -> None:
    paths = phase1_paths(tmp_path / "project", "source_analysis")
    run = Phase1Run(
        gate="source_analysis",
        status="prompt_ready",
        prompt_path=str(paths.prompt),
        prompt_sha256="prompt-hash",
        dependency_hashes={"source": "source-hash"},
    )

    target = write_phase1_run(run)
    payload = json.loads(target.read_text(encoding="utf-8"))

    assert target == paths.run_manifest
    assert payload["schema"] == "cyberppt.phase1_run.v1"
    assert payload["gate"] == "source_analysis"
    assert payload["status"] == "prompt_ready"
    assert payload["resume_command"].startswith("python3 -m cyberppt phase1 generate")
