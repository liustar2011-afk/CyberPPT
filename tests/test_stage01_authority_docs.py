from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_stage01_authority_map_declares_single_logical_semantic_ir() -> None:
    text = (ROOT / "docs" / "STAGE01_AUTHORITY_MAP.md").read_text(encoding="utf-8")

    assert "一个逻辑 `SemanticIR`" in text
    assert "`script/foundation.json`" in text
    assert "`script/deck-plan.json`" in text
    assert "`script/dist/final-script.md`" in text
    assert "Stage 02 只接收 `FinalScriptIR`" in text


def test_strict_skill_does_not_promote_projection_to_independent_authority() -> None:
    text = (
        ROOT / ".agents" / "skills" / "cyberppt-source-foundation" / "SKILL.md"
    ).read_text(encoding="utf-8")

    assert "STAGE01_AUTHORITY_MAP.md" in text
    assert "canonical whole-document `semantic-argument-model.json`" not in text
    assert "derived compatibility artifacts" in text


def test_business_semantic_skill_has_explicit_field_ownership() -> None:
    text = (
        ROOT / ".agents" / "skills" / "business-semantic-understanding" / "SKILL.md"
    ).read_text(encoding="utf-8")

    assert "## SemanticIR field ownership" in text
    assert "`normalized-facts.json` owns" in text
    assert "`concept-base.json` owns" in text
    assert "`relation-graph.json` owns" in text
    assert "`argument-chain.json` owns" in text
