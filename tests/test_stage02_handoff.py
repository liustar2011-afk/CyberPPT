from __future__ import annotations

import json
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from cyberppt.stage02_handoff import HANDOFF_JSON, audit_stage02_handoff, prepare_stage02_handoff


def _payload(project: Path, *, created_at: str, outline_sha256: str) -> dict[str, object]:
    script = project / "script.md"
    outline = project / "outline.json"
    truth = project / "source-truth.json"
    return {
        "schema": "cyberppt.stage02_handoff.v1",
        "project": str(project),
        "created_at": created_at,
        "stage01_confirmation_mode": "interactive_lightweight_confirmation",
        "source_bindings": {
            "script": {"path": str(script), "sha256": "a" * 64},
            "outline": {"path": str(outline), "sha256": outline_sha256},
            "source_truth": {"path": str(truth), "sha256": "b" * 64},
        },
        "page_order": ["p01"],
        "pages": [
            {
                "page_id": "p01",
                "page_number": 1,
                "render_role": "content",
                "title": "标题",
                "page_mission": "说明首期合作的决策门槛",
                "core_message": "先验证再扩展。",
                "onscreen_text": "验证\n扩展",
                "onscreen_items": ["验证", "扩展"],
                "onscreen_expression": {
                    "form": "key_points_3",
                    "source": "fallback",
                    "confidence": 0.2,
                    "evidence": ["fixture"],
                    "candidates": [["key_points_3", 0.2]],
                },
                "stage02_visual_input": {
                    "locked_text_items": [
                        {"text_id": "P01-T01", "text": "验证", "ordinal": 1},
                        {"text_id": "P01-T02", "text": "扩展", "ordinal": 2},
                    ],
                    "business_relationships": [],
                    "stage01_relationship_features": {
                        "authority": "stage01_semantic_handoff",
                        "actors": ["合作方"],
                        "actions": [
                            {"subject": "合作方", "relation": "验证", "object": "首期场景"}
                        ],
                        "directions": [],
                        "conditions": [],
                        "branches": [],
                        "feedback": [],
                        "source_visual_notes": "",
                    },
                    "author_visual_notes_authority": "advisory_only",
                    "body_image_canvas": {"width": 2048, "height": 1024, "ratio": "2:1"},
                },
            }
        ],
    }


def _write_inputs(project: Path) -> None:
    for filename in ("script.md", "outline.json", "source-truth.json"):
        (project / filename).write_text("current\n", encoding="utf-8")


def test_prepare_reuses_current_handoff_when_stage01_authority_is_identical() -> None:
    with TemporaryDirectory() as directory:
        project = Path(directory)
        _write_inputs(project)
        old = _payload(project, created_at="2026-08-13T00:00:00+00:00", outline_sha256="c" * 64)
        handoff_path = project / HANDOFF_JSON
        handoff_path.parent.mkdir(parents=True)
        handoff_path.write_text(json.dumps(old, ensure_ascii=False), encoding="utf-8")
        candidate = _payload(project, created_at="2026-08-13T01:00:00+00:00", outline_sha256="c" * 64)

        with patch("cyberppt.stage02_handoff.build_stage02_handoff", return_value=candidate):
            report = prepare_stage02_handoff(project, reuse_current_handoff=True)

        assert report["status"] == "passed"
        assert report["reused"] is True
        assert json.loads(handoff_path.read_text(encoding="utf-8"))["created_at"] == old["created_at"]


def test_prepare_rebuilds_when_a_bound_stage01_input_digest_changes() -> None:
    with TemporaryDirectory() as directory:
        project = Path(directory)
        _write_inputs(project)
        old = _payload(project, created_at="2026-08-13T00:00:00+00:00", outline_sha256="c" * 64)
        handoff_path = project / HANDOFF_JSON
        handoff_path.parent.mkdir(parents=True)
        handoff_path.write_text(json.dumps(old, ensure_ascii=False), encoding="utf-8")
        candidate = _payload(project, created_at="2026-08-13T01:00:00+00:00", outline_sha256="d" * 64)

        with patch("cyberppt.stage02_handoff.build_stage02_handoff", return_value=candidate):
            report = prepare_stage02_handoff(project, reuse_current_handoff=True)

        assert report["status"] == "passed"
        assert "reused" not in report
        assert json.loads(handoff_path.read_text(encoding="utf-8"))["created_at"] == candidate["created_at"]


def test_handoff_audit_requires_expression_decision() -> None:
    with TemporaryDirectory() as directory:
        project = Path(directory)
        _write_inputs(project)
        payload = _payload(project, created_at="2026-08-13T00:00:00+00:00", outline_sha256="c" * 64)
        del payload["pages"][0]["onscreen_expression"]
        report = audit_stage02_handoff(project, payload)
    codes = {item["code"] for item in report["warnings"]}
    assert "ONSCREEN_EXPRESSION_MISSING" in codes
