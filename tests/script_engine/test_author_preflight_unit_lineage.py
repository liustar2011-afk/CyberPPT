from __future__ import annotations

import json
from pathlib import Path

from script_engine.author_preflight import author_preflight_gate_report, author_preflight_report
from script_engine.page_source_command import page_source_report


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def test_gate_detects_tampered_resolved_unit_lineage(tmp_path: Path) -> None:
    script_dir = tmp_path / "script"
    cache_dir = script_dir / ".cache"
    packet_dir = cache_dir / "page-source"
    plan_path = script_dir / "deck-plan.json"
    foundation_path = script_dir / "foundation.json"
    source_index_path = cache_dir / "source-index.json"
    packet_path = packet_dir / "P01.json"
    manifest_path = cache_dir / "author-preflight.json"

    plan = {
        "authoring_mode": "faithful",
        "pages": [
            {
                "id": "P01",
                "page_role": "content",
                "title": "事实页",
                "source_refs": ["F1"],
            }
        ],
    }
    foundation = {
        "facts": [
            {
                "id": "F1",
                "statement": "来源事实。",
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
                "text": "来源事实原文。",
            }
        ],
    }
    _write_json(plan_path, plan)
    _write_json(foundation_path, foundation)
    _write_json(source_index_path, source_index)

    packet, packet_exit = page_source_report(
        plan_path,
        foundation_path,
        "P01",
        source_index_path=source_index_path,
        output_path=packet_path,
    )
    assert packet_exit == 0
    assert packet["status"] == "passed"

    manifest, preflight_exit = author_preflight_report(
        plan_path,
        foundation_path,
        source_index_path=source_index_path,
        packet_dir=packet_dir,
        output_path=manifest_path,
    )
    assert preflight_exit == 0
    assert manifest["pages"][0]["unit_ids"] == ["SU-001"]

    tampered = json.loads(manifest_path.read_text(encoding="utf-8"))
    tampered["pages"][0]["unit_ids"] = ["SU-999"]
    _write_json(manifest_path, tampered)

    report, exit_code = author_preflight_gate_report(plan_path, foundation_path)

    assert exit_code == 1
    assert report["status"] == "failed"
    assert "AUTHOR_PREFLIGHT_MANIFEST_PAGE_STALE: P01.unit_ids" in report["issues"]
