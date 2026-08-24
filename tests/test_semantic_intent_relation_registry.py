from __future__ import annotations

from cyberppt.composition_resolver import COMPOSITION_GRAMMARS
from cyberppt.semantic_intent import CANONICAL_INTENTS
from cyberppt.visual_carrier_resolver import _CARRIERS


def test_every_canonical_intent_has_composition_and_carrier_registry_entries() -> None:
    intents = set(CANONICAL_INTENTS)
    assert intents == set(COMPOSITION_GRAMMARS)
    assert intents == set(_CARRIERS)


def test_new_peer_and_mapping_intents_are_fully_registered() -> None:
    assert "coordinate_peer_set" in CANONICAL_INTENTS
    assert "correspondence_mapping" in CANONICAL_INTENTS
    assert COMPOSITION_GRAMMARS["coordinate_peer_set"]["axis"] == "shared_field"
    assert COMPOSITION_GRAMMARS["correspondence_mapping"]["axis"] == "paired_mapping"
    assert len(_CARRIERS["coordinate_peer_set"]) >= 3
    assert len(_CARRIERS["correspondence_mapping"]) >= 3
