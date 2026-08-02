from __future__ import annotations

import json
from pathlib import Path

from cyberppt.composition_resolver import (
    COMPOSITION_GRAMMARS,
    resolve_composition,
    validate_composition,
)
from cyberppt.semantic_intent import CANONICAL_INTENTS, resolve_semantic_intent
from cyberppt.visual_carrier_resolver import (
    select_visual_carrier,
    validate_visual_carrier,
)
from cyberppt.commands.semantic_intent_audit import build_override_proposal


FIXTURE = Path(__file__).parent / "fixtures" / "semantic_intent_golden.json"


def test_every_canonical_intent_has_composition_grammar() -> None:
    assert set(COMPOSITION_GRAMMARS) == set(CANONICAL_INTENTS)


def test_every_intent_produces_three_scored_carrier_candidates() -> None:
    for intent in CANONICAL_INTENTS:
        decision = resolve_semantic_intent(explicit_intent=intent)
        composition = resolve_composition(decision)
        carrier = select_visual_carrier(decision, composition)
        assert len(carrier.candidates) >= 3
        assert carrier.selected == carrier.candidates[0].carrier
        assert carrier.candidates[0].score >= 90
        assert validate_composition(composition) == ()
        assert validate_visual_carrier(carrier) == ()


def test_recent_carrier_receives_deck_rhythm_penalty() -> None:
    decision = resolve_semantic_intent(explicit_intent="closed_loop_operation")
    composition = resolve_composition(decision)
    first = select_visual_carrier(decision, composition)
    second = select_visual_carrier(decision, composition, (first.selected,))
    repeated = next(item for item in second.candidates if item.carrier == first.selected)
    assert repeated.score == 95
    assert repeated.score_breakdown["deck_rhythm"] == 0


def test_golden_semantic_intents_produce_required_reading_paths() -> None:
    cases = json.loads(FIXTURE.read_text(encoding="utf-8"))
    for case in cases:
        decision = resolve_semantic_intent(
            content_relations=case["relations"], corpus=case["corpus"]
        )
        composition = resolve_composition(decision)
        assert decision.primary_intent == case["expected_intent"], case["id"]
        assert case["required_path_item"] in composition.reading_path, case["id"]


def test_override_proposal_never_approves_or_activates_changes() -> None:
    audit = {
        "script": "script-final.md",
        "pages": [
            {
                "page_id": "p18",
                "page_title": "智能应用技术引擎",
                "legacy_intent": "capability_relationship",
                "legacy_canonical_intent": "convergence_to_capability",
                "legacy_matches": True,
                "semantic_refinement": True,
                "primary_intent": "capability_to_outcomes",
                "secondary_intents": [],
                "confidence": 0.8,
                "evidence": ["signal:分别支撑"],
                "visual_carrier": {"selected": "capability_to_scene_fanout"},
            }
        ],
    }
    proposal = build_override_proposal(audit)
    assert proposal["approval_effect"] == "none"
    assert proposal["proposals"][0]["status"] == "pending_user_approval"
    assert "semantic_intent_type" not in proposal
