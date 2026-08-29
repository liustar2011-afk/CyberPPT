from __future__ import annotations

import json
from pathlib import Path

from script_engine.contracts import validate_deck_plan, validate_foundation

ROOT = Path(__file__).resolve().parents[2]

def _read(relative: str) -> str:
    return (ROOT / relative).read_text(encoding="utf-8")

def test_v04_examples_validate() -> None:
    foundation = json.loads(_read("examples/foundation.example.json"))
    plan = json.loads(_read("examples/deck-plan.example.json"))
    assert validate_foundation(foundation) == []
    assert validate_deck_plan(plan) == []
    assert foundation["source_structure"]
    assert foundation["relations"][0]["basis"] == "inferred"
    assert foundation["relations"][0]["support"]
    assert plan["source_structure_mode"] == "preserve"
    assert plan["pages"][0]["source_scope"]
    assert plan["pages"][0]["analysis_basis"]["supports"]

def test_understand_skill_contains_latent_logic_pass() -> None:
    text = _read(".agents/skills/cyberppt-script-understand/SKILL.md")
    for token in ("Source structure", "Atomic facts", "Latent Logic Mining", "basis: inferred", "support", "confidence"):
        assert token in text

def test_core_references_exist_without_new_authorities() -> None:
    for relative in (
        "docs/SOURCE_FIDELITY_AND_ANALYSIS.md",
        "references/analysis-models.md",
        "references/storyline-planning.md",
        "references/evidence-architecture.md",
        "references/argument-patterns.md",
        "references/script-quality-rubric.md",
        "references/screen-copy-authoring.md",
    ):
        assert (ROOT / relative).is_file()
    agents = _read("AGENTS.md")
    assert "Only these are authoritative content artifacts" in agents
    assert "foundation.json" in agents
    assert "deck-plan.json" in agents
    assert "dist/final-script.md" in agents
    assert ".cache" in agents
