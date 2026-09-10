from __future__ import annotations

from pathlib import Path

from cyberppt.script_quality.parsing import parse_script_markdown
from script_engine.contracts import load_json, validate_final_script
from script_engine.render import render_stage02_markdown
from script_engine.semantic_contract import FoundationIndex, validate_final_script_provenance


ROOT = Path(__file__).resolve().parents[2]
EXAMPLES = ROOT / "examples"


def _payload() -> dict:
    return load_json(EXAMPLES / "final-script-v1.1.example.json")


def _plan() -> dict:
    return load_json(EXAMPLES / "deck-plan.example.json")


def _foundation() -> dict:
    return load_json(EXAMPLES / "foundation.example.json")


def test_legacy_final_script_10_remains_schema_compatible() -> None:
    payload = load_json(EXAMPLES / "final-script.example.json")
    assert validate_final_script(payload) == []
    assert validate_final_script_provenance(payload, _plan(), _foundation()) == []


def test_final_script_11_example_is_schema_and_provenance_valid() -> None:
    payload = _payload()
    assert validate_final_script(payload) == []
    assert validate_final_script_provenance(payload, _plan(), _foundation()) == []


def test_final_script_11_schema_requires_module_identity_and_provenance() -> None:
    payload = _payload()
    payload["slides"][0]["onscreen"][0].pop("id")
    payload["slides"][0]["onscreen"][1].pop("provenance")

    issues = validate_final_script(payload)

    assert any("'id' is a required property" in issue for issue in issues)
    assert any("'provenance' is a required property" in issue for issue in issues)


def test_final_script_11_schema_rejects_legacy_string_items() -> None:
    payload = _payload()
    payload["slides"][0]["onscreen"][1]["items"] = ["legacy item"]

    issues = validate_final_script(payload)

    assert any("is not of type 'object'" in issue for issue in issues)


def test_provenance_requires_exactly_one_binding_per_visible_target() -> None:
    payload = _payload()
    payload["slides"][0]["onscreen"][0]["provenance"]["bindings"] = [
        {"target": "heading", "source_refs": ["F1"], "relation": "expresses"}
    ]

    issues = validate_final_script_provenance(payload, _plan(), _foundation())

    assert any("[PROVENANCE_TARGET_BINDING_COUNT]" in issue and "/text:" in issue for issue in issues)


def test_provenance_rejects_refs_outside_page_and_foundation() -> None:
    payload = _payload()
    binding = payload["slides"][0]["onscreen"][0]["provenance"]["bindings"][0]
    binding["source_refs"] = ["F999"]

    issues = validate_final_script_provenance(payload, _plan(), _foundation())

    assert any("[PROVENANCE_REF_OUTSIDE_SLIDE]" in issue for issue in issues)
    assert any("[PROVENANCE_REF_OUTSIDE_PAGE]" in issue for issue in issues)
    assert any("[PROVENANCE_REF_UNKNOWN]" in issue for issue in issues)


def test_duplicate_module_identity_is_rejected() -> None:
    payload = _payload()
    payload["slides"][0]["onscreen"][1]["id"] = payload["slides"][0]["onscreen"][0]["id"]

    issues = validate_final_script_provenance(payload, _plan(), _foundation())

    assert any("[PROVENANCE_MODULE_ID_DUPLICATE]" in issue for issue in issues)


def test_foundation_index_reuses_existing_semantic_records() -> None:
    index = FoundationIndex(_foundation())

    assert index.contains("F1")
    assert index.contains("A1")
    assert index.status("F1") == "stated"
    assert index.claim_origin("A1") == "explicit"
    assert index.relations_between(["F3"])


def test_rendered_evidence_mapping_is_audit_only_and_not_visible_copy() -> None:
    payload = _payload()
    markdown = render_stage02_markdown(payload)

    assert "### 证据映射（模块级｜不上屏）" in markdown
    assert "- M01-01 | direct | claims=F1" in markdown
    assert "  - heading <= F1 (expresses)" in markdown

    parsed = parse_script_markdown(markdown)
    assert len(parsed.pages) == 1
    visible = parsed.pages[0].onscreen_text
    assert "数据资源首先需要完成可识别和可管理的治理" in visible
    assert "证据映射" not in visible
    assert "claims=" not in visible
    assert "M01-01" not in visible
    assert "F1 (expresses)" not in visible
