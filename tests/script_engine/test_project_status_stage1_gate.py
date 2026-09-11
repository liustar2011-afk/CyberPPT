from __future__ import annotations

import json
from pathlib import Path

from script_engine.author_preflight import author_preflight_report
from script_engine.page_source_command import page_source_report
from script_engine.project_status import build_project_status


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def _project(tmp_path: Path) -> tuple[Path, Path, Path, Path, Path]:
    project = tmp_path / "demo"
    source_dir = project / "source"
    script_dir = project / "script"
    cache_dir = script_dir / ".cache"
    packet_dir = cache_dir / "page-source"
    source_dir.mkdir(parents=True)
    packet_dir.mkdir(parents=True)
    (source_dir / "brief.md").write_text("平台覆盖600家主体。", encoding="utf-8")
    (project / "manifest.yml").write_text("profile: strict\n", encoding="utf-8")

    foundation_path = script_dir / "foundation.json"
    plan_path = script_dir / "deck-plan.json"
    source_index_path = cache_dir / "source-index.json"
    packet_path = packet_dir / "P01.json"
    manifest_path = cache_dir / "author-preflight.json"

    foundation = {
        "sources": [],
        "facts": [
            {
                "id": "F1",
                "statement": "平台覆盖600家主体。",
                "source_refs": ["SU-001"],
            }
        ],
        "concepts": [],
        "relations": [],
        "arguments": [],
    }
    plan = {
        "communication_goal": "说明平台覆盖情况。",
        "plan_contract_version": 2,
        "planning_profile": "lean",
        "authoring_mode": "faithful",
        "source_structure_mode": "preserve",
        "chapters": [
            {
                "id": "C01",
                "title": "覆盖情况",
                "purpose": "说明来源事实。",
                "source_chapter_ids": [],
            }
        ],
        "pages": [
            {
                "id": "P01",
                "chapter_id": "C01",
                "title": "覆盖情况",
                "question": "平台覆盖情况如何？",
                "logic": "直接呈现来源事实。",
                "page_role": "content",
                "source_refs": ["F1"],
            }
        ],
    }
    source_index = {
        "schema": "cyberppt.source_index.v2",
        "units": [
            {
                "unit_id": "SU-001",
                "source_id": "SRC-1",
                "kind": "paragraph",
                "heading_id": "H-01",
                "text": "平台覆盖600家主体。",
            }
        ],
    }
    _write_json(foundation_path, foundation)
    _write_json(plan_path, plan)
    _write_json(source_index_path, source_index)

    packet, packet_exit = page_source_report(
        plan_path,
        foundation_path,
        "P01",
        source_index_path=source_index_path,
        output_path=packet_path,
    )
    assert packet_exit == 0
    manifest, preflight_exit = author_preflight_report(
        plan_path,
        foundation_path,
        source_index_path=source_index_path,
        packet_dir=packet_dir,
        output_path=manifest_path,
    )
    assert preflight_exit == 0
    assert manifest["summary"]["overall_status"] == "passed"
    return project, plan_path, foundation_path, packet_path, manifest_path


def _status(project: Path) -> dict:
    return build_project_status(
        project,
        final_lint_findings=lambda _payload, _markdown: ([], []),
    )


def test_status_exposes_fresh_author_preflight_per_page(tmp_path: Path) -> None:
    project, _plan_path, _foundation_path, _packet_path, _manifest_path = _project(tmp_path)

    status = _status(project)
    stage1 = status["stage1"]
    preflight = stage1["author_preflight"]

    assert stage1["source_index"]["status"] == "passed"
    assert stage1["foundation"]["status"] == "passed"
    assert stage1["deck_plan"]["status"] == "passed"
    assert preflight["status"] == "passed"
    assert preflight["current_summary"]["overall_status"] == "passed"
    assert preflight["pages"][0]["page_id"] == "P01"
    assert preflight["pages"][0]["gate_status"] == "passed"
    assert preflight["pages"][0]["freshness"] == "fresh"
    assert preflight["pages"][0]["exact_source_status"] == "available"
    assert stage1["final_script"]["status"] == "missing"
    assert stage1["final_audit"]["status"] == "not_run"
    assert status["stage"] == "Stage1 Author Preflight 已通过，待写作最终脚本"


def test_status_marks_packet_stale_after_plan_changes(tmp_path: Path) -> None:
    project, plan_path, _foundation_path, _packet_path, _manifest_path = _project(tmp_path)
    plan = json.loads(plan_path.read_text(encoding="utf-8"))
    plan["pages"][0]["logic"] = "修改后的页面使命。"
    _write_json(plan_path, plan)

    status = _status(project)
    preflight = status["stage1"]["author_preflight"]

    assert preflight["status"] == "blocked"
    assert preflight["pages"][0]["gate_status"] == "stale"
    assert preflight["pages"][0]["freshness"] == "stale"
    assert any("INPUTS_STALE" in issue for issue in preflight["issues"])
    assert status["stage"] == "Stage1 Author Preflight 未通过：待补齐或刷新逐页精确来源证据"


def test_status_reports_missing_manifest_without_trusting_packets(tmp_path: Path) -> None:
    project, _plan_path, _foundation_path, _packet_path, manifest_path = _project(tmp_path)
    manifest_path.unlink()

    status = _status(project)
    preflight = status["stage1"]["author_preflight"]

    assert preflight["status"] == "missing"
    assert preflight["current_summary"]["overall_status"] == "passed"
    assert preflight["pages"][0]["gate_status"] == "passed"
    assert any("MANIFEST_MISSING" in issue for issue in preflight["issues"])
    assert status["stage"] == "Stage1 Author Preflight 未通过：待补齐或刷新逐页精确来源证据"
