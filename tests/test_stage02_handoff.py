from __future__ import annotations

import json
import hashlib
from pathlib import Path
from typing import Callable
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from cyberppt.stage02_handoff import (
    HANDOFF_JSON,
    audit_stage02_handoff,
    build_stage02_handoff,
    prepare_stage02_handoff,
)
from cyberppt.semantic_digest import outline_semantic_digest, script_semantic_digest, source_truth_semantic_digest
from cyberppt.onscreen_expression import expression_constraints


def _binding(path: Path, semantic_digest: Callable[[Path], str]) -> dict[str, str]:
    return {
        "path": str(path),
        "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        "semantic_sha256": semantic_digest(path),
    }


def _payload(project: Path, *, created_at: str) -> dict[str, object]:
    script = project / "script.md"
    stage01 = project / "workbench" / "stages" / "01-analysis"
    outline = stage01 / "outline.json"
    truth = stage01 / "source-truth.json"
    return {
        "schema": "cyberppt.stage02_handoff.v1",
        "project": str(project),
        "created_at": created_at,
        "source_bindings": {
            "script": _binding(script, script_semantic_digest),
            "outline": _binding(outline, outline_semantic_digest),
            "source_truth": _binding(truth, source_truth_semantic_digest),
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
                "expression_constraints": expression_constraints("key_points_3"),
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
                    "expression_constraints": expression_constraints("key_points_3"),
                    "body_image_canvas": {"width": 2048, "height": 1024, "ratio": "2:1"},
                },
            }
        ],
    }


def _write_inputs(project: Path) -> None:
    (project / "script.md").write_text(
        "## 第1页：标题\n"
        "- 页面类型：内容页\n"
        "- 页面标题：标题\n"
        "- 核心结论：先验证再扩展。\n"
        "- 完整文字稿：先验证再扩展。\n"
        "- 上屏文字：\n"
        "  - 验证\n"
        "  - 扩展\n",
        encoding="utf-8",
    )
    stage01 = project / "workbench" / "stages" / "01-analysis"
    stage01.mkdir(parents=True)
    (stage01 / "outline.json").write_text('{"schema":"outline.v1","pages":[]}', encoding="utf-8")
    (stage01 / "source-truth.json").write_text('{"schema":"truth.v1","records":[]}', encoding="utf-8")


def test_prepare_reuses_current_handoff_when_stage01_authority_is_identical() -> None:
    with TemporaryDirectory() as directory:
        project = Path(directory)
        _write_inputs(project)
        old = _payload(project, created_at="2026-08-13T00:00:00+00:00")
        handoff_path = project / HANDOFF_JSON
        handoff_path.parent.mkdir(parents=True)
        handoff_path.write_text(json.dumps(old, ensure_ascii=False), encoding="utf-8")
        candidate = _payload(project, created_at="2026-08-13T01:00:00+00:00")

        with patch("cyberppt.stage02_handoff.build_stage02_handoff", return_value=candidate):
            report = prepare_stage02_handoff(project, reuse_current_handoff=True)

        assert report["status"] == "passed"
        assert report["reused"] is True
        assert json.loads(handoff_path.read_text(encoding="utf-8"))["created_at"] == old["created_at"]


def test_build_handoff_uses_only_the_script_contract() -> None:
    with TemporaryDirectory() as directory:
        project = Path(directory)
        _write_inputs(project)
        payload = build_stage02_handoff(project, script=project / "script.md")

    assert payload["source_bindings"]["script"]["path"] == str((project / "script.md").resolve())
    assert set(payload["source_bindings"]) == {"script"}
    assert payload["pages"][0]["page_mission"] == "先验证再扩展。"


def test_build_handoff_does_not_call_stage01_audit() -> None:
    with TemporaryDirectory() as directory:
        project = Path(directory)
        _write_inputs(project)
        with patch(
            "cyberppt.commands.script_audit.run_script_audit",
            side_effect=AssertionError("Stage 02 must not call the editorial audit"),
        ):
            payload = build_stage02_handoff(project, script=project / "script.md")

    assert payload["source_bindings"]["script"]["path"] == str((project / "script.md").resolve())


def test_build_handoff_accepts_an_external_script_without_stage01_files() -> None:
    with TemporaryDirectory() as directory:
        project = Path(directory)
        script = project.parent / "external-script.md"
        script.write_text(
            "## 第1页：外部脚本\n"
            "- 页面类型：内容页\n"
            "- 页面标题：外部脚本\n"
            "- 核心结论：外部脚本可独立进入 Stage 02。\n"
            "- 完整文字稿：外部脚本可独立进入 Stage 02。\n"
            "- 上屏文字：\n"
            "  - 外部脚本\n"
            "  - 独立进入 Stage 02\n",
            encoding="utf-8",
        )
        report = prepare_stage02_handoff(project, script=script)
        payload = json.loads((project / HANDOFF_JSON).read_text(encoding="utf-8"))

    assert report["status"] == "passed"
    binding = payload["source_bindings"]["script"]
    assert set(payload["source_bindings"]) == {"script"}
    assert Path(binding["path"]).samefile(script)
    assert binding["sha256"] == hashlib.sha256(script.read_bytes()).hexdigest()


def test_prepare_reuses_handoff_when_stage01_inputs_change() -> None:
    with TemporaryDirectory() as directory:
        project = Path(directory)
        _write_inputs(project)
        old = _payload(project, created_at="2026-08-13T00:00:00+00:00")
        handoff_path = project / HANDOFF_JSON
        handoff_path.parent.mkdir(parents=True)
        handoff_path.write_text(json.dumps(old, ensure_ascii=False), encoding="utf-8")
        outline = project / "workbench" / "stages" / "01-analysis" / "outline.json"
        outline.write_text('{"schema":"outline.v1","pages":[{"page_id":"p01"}]}', encoding="utf-8")
        report = audit_stage02_handoff(project, old)

        assert report["status"] == "passed"


def test_handoff_audit_requires_expression_decision() -> None:
    with TemporaryDirectory() as directory:
        project = Path(directory)
        _write_inputs(project)
        payload = _payload(project, created_at="2026-08-13T00:00:00+00:00")
        del payload["pages"][0]["onscreen_expression"]
        report = audit_stage02_handoff(project, payload)
    codes = {item["code"] for item in report["warnings"]}
    assert "ONSCREEN_EXPRESSION_MISSING" in codes


def test_handoff_audit_reports_stale_script_digest() -> None:
    with TemporaryDirectory() as directory:
        project = Path(directory)
        _write_inputs(project)
        payload = _payload(project, created_at="2026-08-13T00:00:00+00:00")
        payload["source_bindings"]["script"]["semantic_sha256"] = "0" * 64
        report = audit_stage02_handoff(project, payload)

        assert report["status"] == "failed"
        assert "HANDOFF_BINDING_STALE" in {
            item["code"] for item in report["blocking_issues"]
        }


def test_handoff_audit_rejects_expression_constraints_drift() -> None:
    with TemporaryDirectory() as directory:
        project = Path(directory)
        _write_inputs(project)
        payload = _payload(project, created_at="2026-08-13T00:00:00+00:00")
        payload["pages"][0]["stage02_visual_input"]["expression_constraints"] = expression_constraints("framework_4")
        report = audit_stage02_handoff(project, payload)

    codes = {item["code"] for item in report["blocking_issues"]}
    assert "ONSCREEN_EXPRESSION_CONSTRAINTS_INVALID" in codes


def test_handoff_audit_ignores_stage01_policy_and_relationship_drift() -> None:
    policy = {
        "writing_style_mode": "government_official",
        "source_structure_mode": "locked",
    }
    relationship = {
        "subject": "项目",
        "relation": "has_goal",
        "objects": ["统一服务入口"],
        "direction": "subject_to_objects",
        "condition": "",
        "modality": "",
        "basis": "explicit",
        "confidence": "high",
        "source_refs": ["ST0002"],
        "authority_ref": "rel-0001",
    }
    with TemporaryDirectory() as directory:
        project = Path(directory)
        _write_inputs(project)
        outline = project / "workbench/stages/01-analysis/outline.json"
        outline.write_text(
            json.dumps(
                {
                    "schema": "outline.v1",
                    "planning_policy": policy,
                    "pages": [
                        {
                            "page_id": "p01",
                            "page_type": "content",
                            "content_relations": [relationship],
                        }
                    ],
                },
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )
        payload = _payload(project, created_at="2026-08-13T00:00:00+00:00")
        payload["planning_policy"] = {
            "writing_style_mode": "consulting",
            "source_structure_mode": "flexible",
        }
        payload["pages"][0]["stage02_visual_input"]["business_relationships"] = []
        report = audit_stage02_handoff(project, payload)

    assert report["status"] == "passed"


class Stage02PolicyAndRelationshipTests(unittest.TestCase):
    def test_build_uses_only_the_script_contract(self) -> None:
        test_build_handoff_uses_only_the_script_contract()

    def test_audit_ignores_stage01_policy_and_relationship_drift(self) -> None:
        test_handoff_audit_ignores_stage01_policy_and_relationship_drift()
