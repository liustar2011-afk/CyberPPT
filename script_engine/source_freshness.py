"""Deterministic fingerprints and freshness checks for Stage 01 source packets."""
from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
from typing import Any, Mapping


PAGE_SOURCE_PACKET_SCHEMA = "cyberppt.page_source_packet.v2"
PAGE_SOURCE_BUILDER_VERSION = "stage1-page-source-v2"
_REQUIRED_INPUT_KEYS = (
    "deck_plan_sha256",
    "foundation_sha256",
    "source_index_sha256",
)


def canonical_json_sha256(payload: Any) -> str:
    """Return a stable SHA-256 fingerprint for a JSON-compatible value."""

    canonical = json.dumps(
        payload,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def build_input_fingerprints(
    deck_plan: Mapping[str, Any],
    foundation: Mapping[str, Any],
    source_index: Mapping[str, Any],
) -> dict[str, str]:
    """Build the complete input fingerprint set required by persisted packets."""

    return {
        "deck_plan_sha256": canonical_json_sha256(deck_plan),
        "foundation_sha256": canonical_json_sha256(foundation),
        "source_index_sha256": canonical_json_sha256(source_index),
    }


def utc_now_iso() -> str:
    """Return an explicit UTC timestamp suitable for packet metadata."""

    return datetime.now(timezone.utc).isoformat()


def packet_freshness(
    packet: Mapping[str, Any],
    deck_plan: Mapping[str, Any],
    foundation: Mapping[str, Any],
    source_index: Mapping[str, Any],
) -> str:
    """Return ``fresh``, ``stale`` or ``invalid`` for a persisted source packet."""

    if packet.get("schema") != PAGE_SOURCE_PACKET_SCHEMA:
        return "invalid"

    inputs = packet.get("inputs")
    if not isinstance(inputs, Mapping):
        return "invalid"
    if any(not str(inputs.get(key) or "").strip() for key in _REQUIRED_INPUT_KEYS):
        return "invalid"

    current = build_input_fingerprints(deck_plan, foundation, source_index)
    if any(inputs.get(key) != current[key] for key in _REQUIRED_INPUT_KEYS):
        return "stale"
    return "fresh"


__all__ = [
    "PAGE_SOURCE_BUILDER_VERSION",
    "PAGE_SOURCE_PACKET_SCHEMA",
    "build_input_fingerprints",
    "canonical_json_sha256",
    "packet_freshness",
    "utc_now_iso",
]
