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
    assert plan["pages"][0]["source_refs"]
    assert plan["plan_contract_version"] == 2
    assert plan["planning_profile"] == "lean"

def test_understand_skill_preserves_only_explicit_relations() -> None:
    text = " ".join(
        _read(".agents/skills/cyberppt-script-understand/SKILL.md").split()
    )
    for token in (
        "Source structure",
        "Atomic facts",
        "Explicit relations",
        "basis: explicit",
        "Do not search for latent logic",
        "relations` may be empty",
    ):
        assert token in text


def test_understand_skill_bundles_its_analysis_references() -> None:
    skill_root = ROOT / ".agents/skills/cyberppt-script-understand"
    for relative in (
        "references/analysis-models.md",
        "references/evidence-architecture.md",
    ):
        assert (skill_root / relative).is_file()


def test_core_references_exist_without_new_authorities() -> None:
    for relative in (
        "docs/SOURCE_FIDELITY_AND_ANALYSIS.md",
        "references/storyline-planning.md",
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


def test_authoring_contract_requires_page_logic_normalization_before_full_copy() -> None:
    contract = _read(
        ".agents/skills/cyberppt-script-workflow/references/authoring-contract.md"
    )
    for token in (
        "Page-logic normalization and paragraph ownership",
        "页面问题归一化",
        "论证角色分配",
        "相邻页问题归属",
        "段落角色单一性",
        "Run the role-switch Critic",
        "Rewrite from the earliest failed link",
    ):
        assert token in contract

    assert "creates no new project artifact, authoring field, receipt or user gate" in contract


def test_authoring_contract_requires_full_copy_structure_pass_before_onscreen_selection() -> None:
    contract = _read(
        ".agents/skills/cyberppt-script-workflow/references/authoring-contract.md"
    )
    for token in (
        "Mandatory full-copy structure pass",
        "段首核心结论 → 分项结论句 → 事实明细",
        "Keep peers on one dimension",
        "Reject label-led pseudo-structure",
        "Flatten and audit before projection",
        "Critic repeats this classification independently",
    ):
        assert token in contract

    required_sequence = contract.split("### 1.2 Required page sequence", 1)[1].split(
        "## 2. Semantic foundation", 1
    )[0]
    assert "execute the full-copy structure pass in\n   2.10 before selecting onscreen information" in required_sequence
    assert "paragraph hierarchy tests in 2.10" in required_sequence


def test_authoring_contract_requires_onscreen_structure_projection_after_full_copy() -> None:
    contract = _read(
        ".agents/skills/cyberppt-script-workflow/references/authoring-contract.md"
    )
    for token in (
        "Mandatory onscreen structure-projection pass",
        "Lock the invariant logic skeleton",
        "Select before shortening",
        "Project semantic levels explicitly",
        "Preserve relationship grammar",
        "Reject abstract transformation claims",
        "Check projection completeness by role",
        "Flatten and reverse-test the page",
        "Critic performs this reverse test independently",
    ):
        assert token in contract

    required_sequence = contract.split("### 1.2 Required page sequence", 1)[1].split(
        "## 2. Semantic foundation", 1
    )[0]
    assert "mandatory onscreen structure-projection\n   pass in 3.3" in required_sequence
    assert "onscreen projection tests in 3.3" in required_sequence


def test_authoring_contract_requires_supporting_field_methods_and_cross_field_reverse_test() -> None:
    contract = _read(
        ".agents/skills/cyberppt-script-workflow/references/authoring-contract.md"
    )
    for token in (
        "Mandatory supporting-field construction pass",
        "Mission ownership method",
        "Core-answer method",
        "Argument-topology method",
        "Visual-structure method",
        "Speaker-note increment method",
        "Cross-field reverse test",
        "Critic repeats all six methods independently",
    ):
        assert token in contract

    required_sequence = contract.split("### 1.2 Required page sequence", 1)[1].split(
        "## 2. Semantic foundation", 1
    )[0]
    assert "mission and\n   core-message methods in 3.9" in required_sequence
    assert "argument-topology method in\n   3.9" in required_sequence
    assert "visual-structure method and\n   atomic relationship-edge test in 3.9" in required_sequence
    assert "speaker-note increment\n   method in 3.9" in required_sequence
    assert "cross-field reverse\n   test in 3.9" in required_sequence
