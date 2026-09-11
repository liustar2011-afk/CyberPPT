from __future__ import annotations

import json
from pathlib import Path

from script_engine.page_source_command import page_source_report
from script_engine.source_freshness import (
    PAGE_SOURCE_BUILDER_VERSION,
    PAGE_SOURCE_PACKET_SCHEMA,
    build_input_fingerprints,
    canonical_json_sha256,
    packet_freshness,
)


def _write_json(path: Path, payload: dict) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def test_canonical_json_sha256_ignores_object_key_order() -> None:
    left = {"b": 2, "a": {"y": 2, "x": 1}}
    right = {"a": {"x": 1, "y": 2}, "b": 2}

    assert canonical_json_sha256(left) == canonical_json_sha256(right)


def test_page_source_report_persists_complete_input_fingerprints(tmp_path: Path) -> None:
    page = {
        "id": "P01",
        "title": "测试页",
        "logic": "证明 packet 与三个上游输入绑定。",
        "source_refs": ["F1"],
    }
    plan = {"authoring_mode": "faithful", "pages": [page]}
    foundation = {
        "facts": [
            {
                "id": "F1",
                "statement": "测试事实。",
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
                "text": "测试事实原文。",
                "locator": {"paragraph": 1},
            }
        ],
    }

    plan_path = tmp_path / "deck-plan.json"
    foundation_path = tmp_path / "foundation.json"
    source_index_path = tmp_path / "source-index.json"
    output_path = tmp_path / "P01.page-source.json"
    _write_json(plan_path, plan)
    _write_json(foundation_path, foundation)
    _write_json(source_index_path, source_index)

    packet, exit_code = page_source_report(
        plan_path,
        foundation_path,
        "P01",
        source_index_path=source_index_path,
        output_path=output_path,
    )

    expected_inputs = build_input_fingerprints(plan, foundation, source_index)
    persisted = json.loads(output_path.read_text(encoding="utf-8"))

    assert exit_code == 0
    assert packet["status"] == "passed"
    assert persisted["schema"] == PAGE_SOURCE_PACKET_SCHEMA
    assert persisted["builder_version"] == PAGE_SOURCE_BUILDER_VERSION
    assert persisted["inputs"] == expected_inputs
    assert persisted["generated_at"]
    assert packet_freshness(persisted, plan, foundation, source_index) == "fresh"


def test_packet_freshness_detects_changed_upstream_input() -> None:
    plan = {"authoring_mode": "faithful", "pages": [{"id": "P01"}]}
    foundation = {"facts": []}
    source_index = {"schema": "cyberppt.source_index.v2", "units": []}
    packet = {
        "schema": PAGE_SOURCE_PACKET_SCHEMA,
        "inputs": build_input_fingerprints(plan, foundation, source_index),
    }

    changed_plan = {"authoring_mode": "faithful", "pages": [{"id": "P01", "title": "已修改"}]}

    assert packet_freshness(packet, plan, foundation, source_index) == "fresh"
    assert packet_freshness(packet, changed_plan, foundation, source_index) == "stale"


def test_packet_freshness_rejects_missing_or_old_fingerprint_contract() -> None:
    plan = {"pages": []}
    foundation = {"facts": []}
    source_index = {"schema": "cyberppt.source_index.v2", "units": []}

    assert packet_freshness({}, plan, foundation, source_index) == "invalid"
    assert (
        packet_freshness(
            {"schema": "cyberppt.page_source_packet.v1", "inputs": {}},
            plan,
            foundation,
            source_index,
        )
        == "invalid"
    )
