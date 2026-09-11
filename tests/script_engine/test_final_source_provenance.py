from __future__ import annotations

from copy import deepcopy

from script_engine.final_source_provenance import validate_final_source_provenance
from script_engine.schema_contracts import validate_final_script


_PACKET_SHA = "a" * 64


def _content_slide() -> dict:
    return {
        "id": "P01",
        "page_type": "content",
        "title": "事实页",
        "full_copy": "甲单位已完成第一阶段工作。",
        "onscreen": [{"heading": "第一阶段工作已完成"}],
        "source_refs": ["F1"],
        "source_provenance": {
            "packet_sha256": _PACKET_SHA,
            "source_refs": ["F1"],
            "unit_ids": ["SU-001"],
        },
    }


def _final_script(slide: dict | None = None) -> dict:
    return {
        "contract": "cyberppt.final-script",
        "version": "1.0",
        "deck": {
            "title": "工作进展",
            "communication_goal": "说明工作进展。",
            "authoring_mode": "faithful",
        },
        "slides": [slide or _content_slide()],
    }


def _preflight() -> dict:
    return {
        "schema": "cyberppt.author_preflight.v2",
        "builder_version": "stage1-author-preflight-v2",
        "pages": [
            {
                "page_id": "P01",
                "gate_status": "passed",
                "packet_sha256": _PACKET_SHA,
                "source_refs": ["F1"],
                "unit_ids": ["SU-001"],
            }
        ],
    }


def test_final_script_schema_requires_source_provenance_for_content_slide() -> None:
    payload = _final_script()
    del payload["slides"][0]["source_provenance"]

    issues = validate_final_script(payload)

    assert issues
    assert any("source_provenance" in issue for issue in issues)


def test_final_script_schema_accepts_complete_source_provenance() -> None:
    assert validate_final_script(_final_script()) == []


def test_final_script_schema_forbids_source_provenance_on_structural_slide() -> None:
    slide = {
        "id": "P01",
        "page_type": "cover",
        "title": "封面",
        "source_provenance": {
            "packet_sha256": _PACKET_SHA,
            "source_refs": ["F1"],
            "unit_ids": ["SU-001"],
        },
    }

    issues = validate_final_script(_final_script(slide))

    assert issues
    assert any("should not be valid" in issue for issue in issues)


def test_final_source_provenance_matches_preflight_exactly() -> None:
    assert validate_final_source_provenance(_final_script(), _preflight()) == []


def test_final_source_provenance_detects_packet_source_ref_and_unit_drift() -> None:
    payload = _final_script()
    provenance = payload["slides"][0]["source_provenance"]
    provenance["packet_sha256"] = "b" * 64
    provenance["source_refs"] = ["F2"]
    provenance["unit_ids"] = ["SU-999"]

    issues = validate_final_source_provenance(payload, _preflight())

    assert "FINAL_SOURCE_PROVENANCE_PACKET_MISMATCH: P01" in issues
    assert "FINAL_SOURCE_PROVENANCE_SLIDE_REFS_MISMATCH: P01" in issues
    assert "FINAL_SOURCE_PROVENANCE_PREFLIGHT_REFS_MISMATCH: P01" in issues
    assert "FINAL_SOURCE_PROVENANCE_UNIT_IDS_MISMATCH: P01" in issues


def test_final_source_provenance_blocks_missing_or_nonpassed_preflight_page() -> None:
    missing = _preflight()
    missing["pages"] = []
    assert validate_final_source_provenance(_final_script(), missing) == [
        "FINAL_SOURCE_PROVENANCE_PREFLIGHT_PAGE_MISSING: P01"
    ]

    blocked = _preflight()
    blocked["pages"][0]["gate_status"] = "blocked"
    assert validate_final_source_provenance(_final_script(), blocked) == [
        "FINAL_SOURCE_PROVENANCE_PREFLIGHT_PAGE_NOT_PASSED: P01"
    ]


def test_final_source_provenance_forbids_structural_page_lineage_semantically() -> None:
    structural = {
        "id": "P02",
        "page_type": "closing",
        "title": "结束页",
        "source_provenance": {
            "packet_sha256": _PACKET_SHA,
            "source_refs": ["F1"],
            "unit_ids": ["SU-001"],
        },
    }
    payload = _final_script(structural)

    assert validate_final_source_provenance(payload, _preflight()) == [
        "FINAL_SOURCE_PROVENANCE_FORBIDDEN: P02"
    ]


def test_final_source_provenance_requires_slide_source_refs_to_match_lineage() -> None:
    payload = _final_script()
    payload["slides"][0]["source_refs"] = ["F2"]

    issues = validate_final_source_provenance(payload, _preflight())

    assert issues == ["FINAL_SOURCE_PROVENANCE_SLIDE_REFS_MISMATCH: P01"]
