from __future__ import annotations

import copy
import json
from pathlib import Path

from script_engine.audit_reports import final_audit_report
from script_engine.semantic_contract import (
    audit_final_script_semantic_contract,
    validate_authoring_mode_authorization,
    validate_relationship_shape,
    validate_source_structure_preservation,
)


ROOT = Path(__file__).resolve().parents[2]
EXAMPLES = ROOT / "examples"


def _examples() -> tuple[dict, dict, dict]:
    final_script = json.loads(
        (EXAMPLES / "final-script-v1.1.example.json").read_text(encoding="utf-8")
    )
    plan = json.loads(
        (EXAMPLES / "deck-plan.example.json").read_text(encoding="utf-8")
    )
    foundation = json.loads(
        (EXAMPLES / "foundation.example.json").read_text(encoding="utf-8")
    )
    return final_script, plan, foundation


def test_final_audit_report_surfaces_structured_role_diagnostic(tmp_path: Path) -> None:
    final_script, plan, foundation = _examples()
    foundation["facts"][1]["argument_duty"] = "response"

    final_path = tmp_path / "final-script.json"
    plan_path = tmp_path / "deck-plan.json"
    foundation_path = tmp_path / "foundation.json"
    final_path.write_text(json.dumps(final_script, ensure_ascii=False), encoding="utf-8")
    plan_path.write_text(json.dumps(plan, ensure_ascii=False), encoding="utf-8")
    foundation_path.write_text(json.dumps(foundation, ensure_ascii=False), encoding="utf-8")

    report, exit_code = final_audit_report(
        final_path,
        plan_path,
        foundation_path,
    )

    assert exit_code == 1
    assert any(
        "[EVIDENCE_ROLE_INCOMPATIBLE]" in issue for issue in report["issues"]
    )
    assert any(
        finding["code"] == "EVIDENCE_ROLE_INCOMPATIBLE"
        and finding["severity"] == "blocking"
        and finding["evidence_refs"] == ["F2"]
        for finding in report["semantic_diagnostics"]
    )


def test_structured_authoring_mode_authorization_rejects_unapproved_escalation() -> None:
    final_script, plan, _ = _examples()
    final_script = copy.deepcopy(final_script)
    final_script["deck"]["authoring_mode"] = "analytical"
    plan["authoring_mode"] = "faithful"

    issues = validate_authoring_mode_authorization(final_script, plan)

    assert issues == [
        "AUTHORING_MODE_NOT_AUTHORIZED: final script requests analytical mode "
        "without analytical mode in the approved Deck Plan"
    ]


def test_single_semantic_entry_preserves_structured_authorization_blocker() -> None:
    final_script, plan, foundation = _examples()
    final_script = copy.deepcopy(final_script)
    final_script["deck"]["authoring_mode"] = "analytical"
    plan["authoring_mode"] = "faithful"

    issues, warnings, diagnostics = audit_final_script_semantic_contract(
        final_script,
        plan,
        foundation,
    )

    assert any("AUTHORING_MODE_NOT_AUTHORIZED" in issue for issue in issues)
    assert not any("AUTHORING_MODE_NOT_AUTHORIZED" in warning for warning in warnings)
    assert isinstance(diagnostics, list)


def test_single_semantic_entry_combines_structured_and_compatibility_findings() -> None:
    final_script, plan, foundation = _examples()
    foundation["facts"][1]["argument_duty"] = "response"
    final_script = copy.deepcopy(final_script)
    final_script["deck"]["authoring_mode"] = "analytical"
    plan["authoring_mode"] = "faithful"

    issues, _, diagnostics = audit_final_script_semantic_contract(
        final_script,
        plan,
        foundation,
    )

    assert any("[EVIDENCE_ROLE_INCOMPATIBLE]" in issue for issue in issues)
    assert any("AUTHORING_MODE_NOT_AUTHORIZED" in issue for issue in issues)
    assert any(
        finding["code"] == "EVIDENCE_ROLE_INCOMPATIBLE"
        for finding in diagnostics
    )


def test_structured_relationship_shape_rejects_missing_endpoint() -> None:
    final_script = {
        "slides": [
            {
                "id": "P01",
                "page_type": "content",
                "relationships": [
                    {"from": "数据输入", "relation": "支撑"},
                ],
            }
        ]
    }

    assert validate_relationship_shape(final_script) == [
        "slides.0 (P01): AUTHOR_RELATIONSHIP_NOT_MATERIALIZED: "
        "relationships[0] is missing ['to']"
    ]


def test_structured_relationship_shape_accepts_complete_edge() -> None:
    final_script = {
        "slides": [
            {
                "id": "P01",
                "page_type": "content",
                "relationships": [
                    {"from": "数据输入", "to": "服务输出", "relation": "支撑"},
                ],
            }
        ]
    }

    assert validate_relationship_shape(final_script) == []


def test_structured_source_preservation_rejects_changed_single_source_chapter_title() -> None:
    final_script = {
        "slides": [
            {
                "id": "P01",
                "page_type": "chapter",
                "chapter_id": "C01",
                "title": "改写后的章节名",
            }
        ]
    }
    plan = {
        "source_structure_mode": "preserve",
        "chapters": [
            {
                "id": "C01",
                "source_chapter_ids": ["CH01"],
            }
        ],
    }
    foundation = {
        "source_structure": [
            {
                "id": "CH01",
                "title": "第一章 原始章节名",
            }
        ]
    }

    issues = validate_source_structure_preservation(final_script, plan, foundation)

    assert issues == [
        "slides.0 (P01): source_structure_mode='preserve' requires chapter title "
        "'原始章节名', got '改写后的章节名'"
    ]


def test_structured_source_preservation_accepts_normalized_source_chapter_title() -> None:
    final_script = {
        "slides": [
            {
                "id": "P01",
                "page_type": "chapter",
                "chapter_id": "C01",
                "title": "原始章节名",
            }
        ]
    }
    plan = {
        "source_structure_mode": "preserve",
        "chapters": [
            {
                "id": "C01",
                "source_chapter_ids": ["CH01"],
            }
        ],
    }
    foundation = {
        "source_structure": [
            {
                "id": "CH01",
                "title": "第一章 原始章节名",
            }
        ]
    }

    assert validate_source_structure_preservation(final_script, plan, foundation) == []


def test_source_preservation_is_inactive_without_preserve_mode() -> None:
    final_script = {
        "slides": [
            {
                "id": "P01",
                "page_type": "chapter",
                "chapter_id": "C01",
                "title": "允许改写",
            }
        ]
    }
    plan = {
        "source_structure_mode": "reorganize",
        "chapters": [
            {
                "id": "C01",
                "source_chapter_ids": ["CH01"],
            }
        ],
    }
    foundation = {
        "source_structure": [
            {
                "id": "CH01",
                "title": "第一章 原始章节名",
            }
        ]
    }

    assert validate_source_structure_preservation(final_script, plan, foundation) == []
