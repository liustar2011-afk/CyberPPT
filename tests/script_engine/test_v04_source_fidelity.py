from __future__ import annotations

import json
from pathlib import Path

from script_engine.analysis_audit import audit_deck_plan, audit_foundation_analysis, validate_source_index_coverage
from script_engine.contracts import validate_deck_plan, validate_foundation
from script_engine.source_index import build_source_index, build_source_index_file

ROOT = Path(__file__).resolve().parents[2]

def _foundation() -> dict:
    return {
        "sources": [{"id": "SRC1", "title": "x", "type": "docx"}],
        "source_structure": [
            {"id": "CH01", "title": "第一章", "order": 1, "level": "chapter", "source_refs": ["S1.0"]},
            {"id": "CH02", "title": "第二章", "order": 2, "level": "chapter", "source_refs": ["S2.0"]},
        ],
        "facts": [
            {"id": "F1", "statement": "A", "source_refs": ["S1.1"], "visibility": "external_ok"},
            {"id": "F2", "statement": "B", "source_refs": ["S1.1"], "visibility": "external_ok"},
            {"id": "F3", "statement": "内部测算", "source_refs": ["附件七"], "visibility": "internal_only"},
        ],
        "concepts": [],
        "relations": [{"id": "R1", "from": "A", "to": "B", "relation": "A提高B需求", "basis": "inferred", "confidence": "high", "support": ["F1", "F2"], "source_refs": ["S1.1"]}],
        "arguments": [],
    }

def _plan() -> dict:
    return {
        "communication_goal": "test",
        "audience_scope": "external",
        "source_structure_mode": "preserve",
        "evidence_fit_review_mode": "strict",
        "chapters": [
            {"id": "C1", "purpose": "x", "source_chapter_ids": ["CH01"]},
            {"id": "C2", "purpose": "y", "source_chapter_ids": ["CH02"]},
        ],
        "pages": [{
            "id": "P1", "chapter_id": "C1", "question": "q", "message": "m", "logic": "l", "content": ["x"],
            "source_scope": ["S1.1"], "structural_operation": "preserve",
            "analysis_basis": {"model": "problem-diagnosis", "relation_basis": "inferred", "confidence": "high", "supports": ["F1", "F2"]},
            "proof": {"method": "reasoning", "evidence_refs": ["F1", "F2"], "relation_basis": "inferred"},
            "evidence_fit_review": {
                "question": "q",
                "items": [
                    {"evidence_ref": "F1", "fit": "indirect", "role": "reason", "reason": "F1 supports the inferred relation"},
                    {"evidence_ref": "F2", "fit": "indirect", "role": "result", "reason": "F2 supports the inferred relation"},
                ],
                "counter_case": "Without both facts the inferred relation would need to be removed",
                "verdict": "keep",
            },
        }],
    }

def test_supported_inferred_relation_passes() -> None:
    foundation = _foundation()
    assert validate_foundation(foundation) == []
    issues, warnings = audit_foundation_analysis(foundation)
    assert issues == []

def test_inferred_relation_requires_support() -> None:
    foundation = _foundation()
    foundation["relations"][0]["support"] = []
    issues, _ = audit_foundation_analysis(foundation)
    assert any("requires non-empty support" in issue for issue in issues)

def test_source_preserve_detects_chapter_reorder() -> None:
    foundation = _foundation()
    plan = _plan()
    plan["chapters"] = list(reversed(plan["chapters"]))
    issues, _ = audit_deck_plan(plan, foundation)
    assert any("source chapter order/content differs" in issue for issue in issues)

def test_cross_chapter_page_requires_authorization() -> None:
    foundation = _foundation()
    plan = _plan()
    plan["pages"][0]["source_scope"] = ["S1.1", "S2.1"]
    issues, _ = audit_deck_plan(plan, foundation)
    assert any("crosses chapters" in issue for issue in issues)

def test_external_internal_evidence_requires_visibility_decision() -> None:
    foundation = _foundation()
    plan = _plan()
    plan["pages"][0]["proof"]["evidence_refs"].append("F3")
    issues, _ = audit_deck_plan(plan, foundation)
    assert any("internal-only evidence" in issue for issue in issues)
    plan["pages"][0]["visibility_decision"] = "internal_only_used_as_hidden_support"
    issues, _ = audit_deck_plan(plan, foundation)
    assert not any("internal-only evidence" in issue for issue in issues)

def test_plan_schema_accepts_v04_fields() -> None:
    assert validate_deck_plan(_plan()) == []

def test_source_index_maps_word_hierarchy() -> None:
    text = "\n".join([
        "[/body/p[1]] 第一章　建设背景",
        "[/body/p[2]] 一、建设背景",
        "[/body/p[3]] 正文",
        "[/body/p[4]] 第三章　重点服务与合作机会",
        "[/body/p[5]] 三、重点合作方向",
        "[/body/p[6]] （四）燃料价格预测与供应链服务",
        "[/body/p[7]] 重点服务正文",
        "[/body/p[8]] 结束语",
        "[/body/p[9]] 附件七　商务报价与收益分配参考模型",
    ])
    index = build_source_index(text, source_file="source.docx")
    assert "S1.1" in index["refs"]
    assert "S3.3.4" in index["refs"]
    assert "结束语" in index["refs"]
    assert "附件七" in index["refs"]
    assert index["refs"]["S3.3.4"]["paragraph_keys"] == ["6", "7"]

def test_source_index_file_uses_lf_line_endings(tmp_path) -> None:
    source_extract = tmp_path / "source_extract.txt"
    source_extract.write_bytes(b"[/body/p[1]] \xe7\xac\xac\xe4\xb8\x80\xe7\xab\xa0\r\n[/body/p[2]] \xe6\xad\xa3\xe6\x96\x87\r\n")
    output = tmp_path / ".cache" / "source-index.json"

    build_source_index_file(source_extract, output)

    data = output.read_bytes()
    assert b"\r\n" not in data
    assert data.endswith(b"\n")

def test_source_index_skips_word_toc_duplicates() -> None:
    text = "\n".join([
        "[/body/p[10]] 第一章　建设背景\t1",
        "[/body/p[11]] 一、建设背景\t1",
        "[/body/p[51]] 第一章　建设背景",
        "[/body/p[52]] 一、建设背景",
        "[/body/p[53]] 正文",
    ])
    index = build_source_index(text)
    chapter_nodes = [node for node in index["source_structure"] if node["level"] == "chapter"]
    assert [node["id"] for node in chapter_nodes] == ["CH01"]
    assert "11" not in index["refs"]["S1.1"]["paragraph_keys"]
    assert index["refs"]["S1.1"]["paragraph_keys"] == ["52", "53"]

def test_real_project_source_index_uses_body_structure_not_toc() -> None:
    source_extract = ROOT / "tests" / "script_engine" / "fixtures" / "projects" / "power-industry-data-infrastructure" / "sources" / "source_extract.txt"
    if not source_extract.exists():
        return
    index = build_source_index(source_extract.read_text(encoding="utf-8-sig"), source_file="source.docx")
    chapters = [node for node in index["source_structure"] if node["level"] == "chapter"]
    assert [node["id"] for node in chapters] == ["CH01", "CH02", "CH03", "CH04", "CH05"]
    assert "S3.3.4" in index["refs"]
    assert "141" in index["refs"]["S3.3.4"]["paragraph_keys"]
    assert "11" not in index["refs"]["S1.1"]["paragraph_keys"]
    assert "52" in index["refs"]["S1.1"]["paragraph_keys"]

def test_source_index_coverage_catches_unmapped_ref() -> None:
    final = {"slides": [{"id": "P01", "source_refs": ["S1.1", "S9.9"]}]}
    index = {"refs": {"S1.1": {}}}
    issues = validate_source_index_coverage(final, index)
    assert len(issues) == 1 and "S9.9" in issues[0]

def test_old_fixture_without_evidence_fit_gate_is_rejected() -> None:
    project = ROOT / "tests" / "script_engine" / "fixtures" / "projects" / "power-industry-data-infrastructure"
    if not project.exists():
        return
    foundation = json.loads((project / "foundation.json").read_text(encoding="utf-8"))
    plan = json.loads((project / "deck-plan.json").read_text(encoding="utf-8"))
    assert validate_foundation(foundation) == []
    assert any("evidence_fit_review_mode" in issue for issue in validate_deck_plan(plan))
