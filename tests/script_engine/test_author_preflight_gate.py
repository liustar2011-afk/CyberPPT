from __future__ import annotations

import json
from pathlib import Path

from script_engine.audit_reports import final_audit_report
from script_engine.author_preflight import author_preflight_gate_report, author_preflight_report
from script_engine.delivery_commands import render_stage02_delivery
from script_engine.page_source_command import page_source_report


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def _build_project(tmp_path: Path) -> dict[str, Path]:
    script_dir = tmp_path / "script"
    cache_dir = script_dir / ".cache"
    packet_dir = cache_dir / "page-source"
    final_dir = script_dir / "dist"

    plan_path = script_dir / "deck-plan.json"
    foundation_path = script_dir / "foundation.json"
    source_index_path = cache_dir / "source-index.json"
    packet_path = packet_dir / "P01.json"
    preflight_path = cache_dir / "author-preflight.json"
    final_path = final_dir / "final-script.json"
    output_path = final_dir / "final-script.md"

    plan = {
        "communication_goal": "说明第一阶段工作完成情况。",
        "plan_contract_version": 2,
        "planning_profile": "lean",
        "authoring_mode": "faithful",
        "source_structure_mode": "preserve",
        "chapters": [
            {
                "id": "C01",
                "title": "工作进展",
                "purpose": "说明来源中的工作进展。",
                "source_chapter_ids": ["CH01"],
            }
        ],
        "pages": [
            {
                "id": "P01",
                "chapter_id": "C01",
                "title": "工作进展",
                "question": "当前进展是什么？",
                "logic": "忠实呈现第一阶段完成情况",
                "page_role": "content",
                "source_refs": ["F1"],
            }
        ],
    }
    foundation = {
        "sources": [],
        "entities": [],
        "facts": [
            {
                "id": "F1",
                "statement": "甲单位已完成第一阶段工作。",
                "source_refs": ["SU-001"],
            }
        ],
        "concepts": [],
        "relations": [],
        "arguments": [],
        "constraints": [],
        "numbers": [],
    }
    source_index = {
        "schema": "cyberppt.source_index.v2",
        "units": [
            {
                "unit_id": "SU-001",
                "source_id": "SRC-1",
                "kind": "paragraph",
                "heading_id": "H-01",
                "text": "甲单位已完成第一阶段工作。",
                "locator": {"paragraph": 1},
            }
        ],
    }
    final_script = {
        "contract": "cyberppt.final-script",
        "version": "1.0",
        "deck": {
            "title": "工作进展",
            "communication_goal": "说明第一阶段工作完成情况。",
            "authoring_mode": "faithful",
        },
        "slides": [
            {
                "id": "P01",
                "page_type": "content",
                "title": "工作进展",
                "full_copy": "甲单位已完成第一阶段工作。",
                "onscreen": [
                    {
                        "heading": "第一阶段工作已完成",
                        "text": "甲单位已完成第一阶段工作。",
                    }
                ],
                "source_refs": ["F1"],
            }
        ],
    }

    _write_json(plan_path, plan)
    _write_json(foundation_path, foundation)
    _write_json(source_index_path, source_index)
    _write_json(final_path, final_script)
    return {
        "plan": plan_path,
        "foundation": foundation_path,
        "source_index": source_index_path,
        "packet": packet_path,
        "preflight": preflight_path,
        "final": final_path,
        "output": output_path,
    }


def _prepare_gate(paths: dict[str, Path]) -> None:
    packet, packet_exit = page_source_report(
        paths["plan"],
        paths["foundation"],
        "P01",
        source_index_path=paths["source_index"],
        output_path=paths["packet"],
    )
    assert packet_exit == 0
    assert packet["status"] == "passed"

    manifest, preflight_exit = author_preflight_report(
        paths["plan"],
        paths["foundation"],
        source_index_path=paths["source_index"],
        packet_dir=paths["packet"].parent,
        output_path=paths["preflight"],
    )
    assert preflight_exit == 0
    assert manifest["summary"]["overall_status"] == "passed"


def test_gate_passes_when_manifest_and_packets_match_current_inputs(tmp_path: Path) -> None:
    paths = _build_project(tmp_path)
    _prepare_gate(paths)

    report, exit_code = author_preflight_gate_report(
        paths["plan"],
        paths["foundation"],
    )

    assert exit_code == 0
    assert report["status"] == "passed"
    assert report["issues"] == []


def test_gate_fails_after_packet_changes_without_regenerating_manifest(tmp_path: Path) -> None:
    paths = _build_project(tmp_path)
    _prepare_gate(paths)

    packet = json.loads(paths["packet"].read_text(encoding="utf-8"))
    packet["generated_at"] = "2099-01-01T00:00:00+00:00"
    _write_json(paths["packet"], packet)

    report, exit_code = author_preflight_gate_report(
        paths["plan"],
        paths["foundation"],
    )

    assert exit_code == 1
    assert report["status"] == "failed"
    assert any("packet_sha256" in issue for issue in report["issues"])


def test_final_audit_is_blocked_when_preflight_manifest_is_missing(tmp_path: Path) -> None:
    paths = _build_project(tmp_path)

    report, exit_code = final_audit_report(
        paths["final"],
        paths["plan"],
        paths["foundation"],
    )

    assert exit_code == 1
    assert report["author_preflight"]["status"] == "failed"
    assert any("AUTHOR_PREFLIGHT_MANIFEST_MISSING" in issue for issue in report["issues"])


def test_stage02_render_is_blocked_before_final_validation_when_preflight_is_missing(
    tmp_path: Path,
) -> None:
    paths = _build_project(tmp_path)

    rendered, error_report, exit_code = render_stage02_delivery(
        paths["final"],
        paths["output"],
        plan_path=paths["plan"],
        foundation_path=paths["foundation"],
        final_lint_findings=lambda _payload, _markdown: ([], []),
    )

    assert exit_code == 1
    assert rendered is None
    assert error_report is not None
    assert error_report["kind"] == "stage1-author-preflight"
    assert any("AUTHOR_PREFLIGHT_MANIFEST_MISSING" in issue for issue in error_report["issues"])
    assert not paths["output"].exists()


def test_stage02_render_passes_after_fresh_preflight(tmp_path: Path) -> None:
    paths = _build_project(tmp_path)
    _prepare_gate(paths)

    rendered, error_report, exit_code = render_stage02_delivery(
        paths["final"],
        paths["output"],
        plan_path=paths["plan"],
        foundation_path=paths["foundation"],
        final_lint_findings=lambda _payload, _markdown: ([], []),
    )

    assert exit_code == 0
    assert error_report is None
    assert rendered == str(paths["output"].resolve())
    assert paths["output"].is_file()
