from __future__ import annotations

from copy import deepcopy

from script_engine.author_preflight import build_author_preflight
from script_engine.page_source_packet import build_page_source_packet
from script_engine.source_freshness import build_input_fingerprints


def _fixture() -> tuple[dict, dict, dict, dict]:
    structural_page = {
        "id": "P00",
        "title": "封面",
        "logic": "结构页",
        "page_role": "cover",
        "source_refs": [],
    }
    content_page = {
        "id": "P01",
        "title": "事实页",
        "logic": "忠实呈现来源事实",
        "page_role": "content",
        "source_refs": ["F1"],
    }
    plan = {
        "authoring_mode": "faithful",
        "pages": [structural_page, content_page],
    }
    foundation = {
        "facts": [
            {
                "id": "F1",
                "statement": "甲单位已完成第一阶段工作。",
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
                "heading_id": "H-01",
                "text": "甲单位已完成第一阶段工作。",
                "locator": {"paragraph": 3},
            }
        ],
    }
    page_context = dict(content_page)
    page_context["authoring_mode"] = "faithful"
    packet = build_page_source_packet(page_context, foundation, source_index)
    packet["inputs"] = build_input_fingerprints(plan, foundation, source_index)
    packet["source_index"] = "/project/script/.cache/source-index.json"
    return plan, foundation, source_index, packet


def test_author_preflight_passes_fresh_content_and_marks_structural_page_not_applicable() -> None:
    plan, foundation, source_index, packet = _fixture()

    manifest = build_author_preflight(
        plan,
        foundation,
        source_index,
        {"P01": packet},
        packet_paths={"P01": "/project/script/.cache/page-source/P01.json"},
    )

    assert manifest["summary"] == {
        "passed": 1,
        "blocked": 0,
        "missing": 0,
        "stale": 0,
        "not_applicable": 1,
        "overall_status": "passed",
    }
    assert manifest["pages"][0]["gate_status"] == "not_applicable"
    assert manifest["pages"][1]["gate_status"] == "passed"
    assert manifest["pages"][1]["freshness"] == "fresh"
    assert manifest["pages"][1]["exact_source_status"] == "available"
    assert len(manifest["pages"][1]["packet_sha256"]) == 64


def test_author_preflight_blocks_missing_content_packet() -> None:
    plan, foundation, source_index, _packet = _fixture()

    manifest = build_author_preflight(plan, foundation, source_index, {})

    content = manifest["pages"][1]
    assert content["gate_status"] == "missing"
    assert content["freshness"] == "missing"
    assert content["issues"] == ["AUTHOR_PREFLIGHT_PACKET_MISSING"]
    assert manifest["summary"]["overall_status"] == "blocked"


def test_author_preflight_marks_packet_stale_after_plan_change() -> None:
    plan, foundation, source_index, packet = _fixture()
    changed_plan = deepcopy(plan)
    changed_plan["pages"][1]["title"] = "已修改标题"

    manifest = build_author_preflight(
        changed_plan,
        foundation,
        source_index,
        {"P01": packet},
    )

    content = manifest["pages"][1]
    assert content["gate_status"] == "stale"
    assert content["freshness"] == "stale"
    assert content["issues"] == ["AUTHOR_PREFLIGHT_PACKET_STALE"]
    assert manifest["summary"]["stale"] == 1
    assert manifest["summary"]["overall_status"] == "blocked"


def test_author_preflight_blocks_packet_that_failed_exact_source_gate() -> None:
    plan, foundation, source_index, _packet = _fixture()
    blocked_source_index = {"schema": "cyberppt.source_index.v2", "units": []}
    content_page = plan["pages"][1]
    page_context = dict(content_page)
    page_context["authoring_mode"] = "faithful"
    blocked_packet = build_page_source_packet(
        page_context,
        foundation,
        blocked_source_index,
    )
    blocked_packet["inputs"] = build_input_fingerprints(
        plan,
        foundation,
        blocked_source_index,
    )
    blocked_packet["source_index"] = "/project/script/.cache/source-index.json"

    manifest = build_author_preflight(
        plan,
        foundation,
        blocked_source_index,
        {"P01": blocked_packet},
    )

    content = manifest["pages"][1]
    assert content["gate_status"] == "blocked"
    assert content["freshness"] == "fresh"
    assert content["exact_source_status"] == "unavailable"
    assert "AUTHOR_PREFLIGHT_PACKET_BLOCKED" in content["issues"]
    assert "AUTHOR_PREFLIGHT_EXACT_SOURCE_UNAVAILABLE" in content["issues"]
    assert manifest["summary"]["blocked"] == 1
    assert manifest["summary"]["overall_status"] == "blocked"


def test_author_preflight_blocks_invalid_exact_source_unit_shape() -> None:
    plan, foundation, source_index, packet = _fixture()
    packet["evidence"][0]["exact_source_units"] = ["not-an-object"]
    packet["inputs"] = build_input_fingerprints(plan, foundation, source_index)

    manifest = build_author_preflight(
        plan,
        foundation,
        source_index,
        {"P01": packet},
    )

    content = manifest["pages"][1]
    assert content["gate_status"] == "blocked"
    assert content["exact_source_status"] == "unavailable"
    assert "AUTHOR_PREFLIGHT_EXACT_SOURCE_UNAVAILABLE" in content["issues"]
