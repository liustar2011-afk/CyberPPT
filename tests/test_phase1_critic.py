from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from cyberppt.phase1 import critic, workflow
from cyberppt.phase1.artifacts import phase1_paths
from tests.test_phase1_workflow import VALID_SOURCE_ANALYSIS_JSON, prepare_fixture_project


CRITIC_FINDINGS_JSON = json.dumps(
    {
        "findings": [
            {
                "category": "duplicate_page",
                "page": 4,
                "evidence_ids": ["E01"],
                "issue": "与上一页重复",
                "remediation": "增加承接关系",
                "severity": "medium",
            }
        ]
    },
    ensure_ascii=False,
)


def candidate_ready_project(tmp_path: Path) -> tuple[Path, Path]:
    project, source = prepare_fixture_project(tmp_path)
    workflow.prepare_phase1_prompt(project, "source_analysis", source)
    with patch.object(workflow, "run_codex_text", return_value=VALID_SOURCE_ANALYSIS_JSON):
        result = workflow.generate_phase1_candidate(project, "source_analysis", model="test-model")
    return project, Path(result["candidate"])


def test_parse_critic_output_rejects_unknown_category() -> None:
    payload = {"findings": [{"category": "invented", "page": 1, "evidence_ids": [], "issue": "x", "remediation": "y"}]}

    with pytest.raises(ValueError, match="unknown critic category"):
        critic.parse_critic_output(json.dumps(payload, ensure_ascii=False))


def test_critic_findings_do_not_rewrite_candidate(tmp_path: Path, monkeypatch) -> None:
    project, candidate = candidate_ready_project(tmp_path)
    original = candidate.read_text(encoding="utf-8")
    monkeypatch.setattr(critic, "run_codex_text", lambda **kwargs: CRITIC_FINDINGS_JSON)

    report = critic.critique_phase1_candidate(project, "source_analysis", model="critic-model")

    paths = phase1_paths(project, "source_analysis")
    assert candidate.read_text(encoding="utf-8") == original
    assert report["status"] == "critic_ready"
    assert report["findings"][0]["category"] == "duplicate_page"
    assert paths.critic_prompt.exists()
    assert paths.critic_raw.exists()
    assert paths.critic_report.exists()


def test_critic_model_failure_preserves_candidate_and_run_state(tmp_path: Path, monkeypatch) -> None:
    project, candidate = candidate_ready_project(tmp_path)
    original = candidate.read_text(encoding="utf-8")
    monkeypatch.setattr(critic, "run_codex_text", Mock(side_effect=RuntimeError("network unavailable")))

    with pytest.raises(RuntimeError, match="network unavailable"):
        critic.critique_phase1_candidate(project, "source_analysis")

    paths = phase1_paths(project, "source_analysis")
    run = json.loads(paths.run_manifest.read_text(encoding="utf-8"))
    assert candidate.read_text(encoding="utf-8") == original
    assert run["critic_status"] == "critic_model_failed"
    assert paths.critic_prompt.exists()
