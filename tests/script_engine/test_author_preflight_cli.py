from __future__ import annotations

import json
from pathlib import Path

from script_engine.cli import main


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def _project_inputs(tmp_path: Path) -> tuple[Path, Path, Path, Path]:
    script_dir = tmp_path / "script"
    plan_path = script_dir / "deck-plan.json"
    foundation_path = script_dir / "foundation.json"
    source_index_path = script_dir / ".cache" / "source-index.json"
    packet_path = script_dir / ".cache" / "page-source" / "P01.json"

    plan = {
        "authoring_mode": "faithful",
        "pages": [
            {
                "id": "P01",
                "title": "事实页",
                "logic": "忠实呈现原文",
                "page_role": "content",
                "source_refs": ["F1"],
            }
        ],
    }
    foundation = {
        "facts": [
            {
                "id": "F1",
                "statement": "甲单位完成第一阶段工作。",
                "source_refs": ["SU-001"],
            }
        ]
    }
    source_index = {
        "schema": "cyberppt.source_index.v2",
        "units": [
            {
                "unit_id": "SU-001",
                "source_id": "SRC-1",
                "kind": "paragraph",
                "heading_id": "H-1",
                "text": "甲单位完成第一阶段工作。",
                "locator": {"paragraph": 1},
            }
        ],
    }
    _write_json(plan_path, plan)
    _write_json(foundation_path, foundation)
    _write_json(source_index_path, source_index)
    return plan_path, foundation_path, source_index_path, packet_path


def test_author_preflight_cli_writes_default_manifest_when_all_packets_pass(
    tmp_path: Path, capsys
) -> None:
    plan_path, foundation_path, source_index_path, packet_path = _project_inputs(tmp_path)

    page_source_exit = main(
        [
            "page-source",
            str(plan_path),
            str(foundation_path),
            "P01",
            "--source-index",
            str(source_index_path),
            "--output",
            str(packet_path),
        ]
    )
    capsys.readouterr()
    assert page_source_exit == 0

    exit_code = main(["author-preflight", str(plan_path), str(foundation_path)])
    captured = capsys.readouterr()
    report = json.loads(captured.out)
    manifest_path = foundation_path.parent / ".cache" / "author-preflight.json"

    assert exit_code == 0
    assert captured.err == ""
    assert report["summary"]["overall_status"] == "passed"
    assert report["pages"][0]["gate_status"] == "passed"
    assert manifest_path.is_file()
    persisted = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert persisted["summary"]["overall_status"] == "passed"


def test_author_preflight_cli_returns_nonzero_and_persists_blocked_manifest_without_packet(
    tmp_path: Path, capsys
) -> None:
    plan_path, foundation_path, _source_index_path, _packet_path = _project_inputs(tmp_path)
    (foundation_path.parent / ".cache" / "page-source").mkdir(parents=True, exist_ok=True)

    exit_code = main(["author-preflight", str(plan_path), str(foundation_path)])
    captured = capsys.readouterr()
    report = json.loads(captured.err)
    manifest_path = foundation_path.parent / ".cache" / "author-preflight.json"

    assert exit_code == 1
    assert captured.out == ""
    assert report["summary"]["overall_status"] == "blocked"
    assert report["pages"][0]["gate_status"] == "missing"
    assert manifest_path.is_file()
