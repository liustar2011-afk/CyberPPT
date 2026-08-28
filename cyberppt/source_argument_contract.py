"""Stable vocabulary and validation constants for the source argument model.

This module owns the model contract vocabulary.  ``source_argument_model``
continues to import these names at module scope so its historical public
imports remain valid while parsing, rendering and validation stay together in
the façade module.
"""

from __future__ import annotations

import re


SCHEMA = "cyberppt.semantic_argument_model.v1"
MODEL_JSON = "semantic-argument-model.json"
MODEL_BLOCK_MARKER = "semantic-argument-model"
ROOT_NODE_IDS = frozenset({"document", "document_thesis"})

RELATIONS = frozenset(
    {
        "supports",
        "depends_on",
        "transforms_to",
        "realized_by",
        "implemented_by",
        "maps_to",
        "operationalizes",
        "precedes",
        "constrains",
        "contains",
        "composed_of",
        "contrasts_with",
        "requires_confirmation_of",
    }
)
RELATION_WEIGHT_EFFECTS = frozenset({"none"})
ARGUMENT_WEIGHTS = frozenset({"core", "supporting", "detail", "constraint"})
ARGUMENT_DUTIES = frozenset(
    {"premise", "driver", "consequence", "gap", "response", "support", "detail", "boundary", "metadata"}
)
ARGUMENT_ROLES = frozenset(
    {
        "thesis",
        "foundation",
        "definition",
        "positioning",
        "construction",
        "capability",
        "advantage",
        "architecture",
        "operation",
        "cooperation",
        "implementation",
        "recommendation",
        "boundary",
        "gap",
        "evidence",
    }
)
STATUS_VALUES = frozenset(
    {
        "existing",
        "in_progress",
        "planned",
        "proposal",
        "to_confirm",
        "recommendation",
        "mixed",
        "unknown",
    }
)
INTERPRETATION_CONTRACT_MODES = frozenset({"legacy", "strict"})
CLAIM_ORIGINS = frozenset({"source_explicit", "source_implied", "editorial_hypothesis"})
SOURCE_TRUTH_CLAIM_ROLES = frozenset(
    {"fact", "change", "problem", "judgment", "recommendation", "boundary", "unresolved"}
)
INFERENCE_ORIGINS = frozenset({"source_implied", "editorial_hypothesis"})
CONCEPT_RESOLUTIONS = frozenset({"same_meaning", "different_dimension", "homonym", "requires_review"})

_LEGACY_EVIDENCE_RE = re.compile(r"S\d+")
_SOURCE_UNIT_RE = re.compile(r"SU-[A-Z0-9-]+")


__all__ = [
    "SCHEMA", "MODEL_JSON", "MODEL_BLOCK_MARKER", "ROOT_NODE_IDS", "RELATIONS",
    "RELATION_WEIGHT_EFFECTS", "ARGUMENT_WEIGHTS", "ARGUMENT_DUTIES", "ARGUMENT_ROLES",
    "STATUS_VALUES", "INTERPRETATION_CONTRACT_MODES", "CLAIM_ORIGINS",
    "SOURCE_TRUTH_CLAIM_ROLES", "INFERENCE_ORIGINS", "CONCEPT_RESOLUTIONS",
    "_LEGACY_EVIDENCE_RE", "_SOURCE_UNIT_RE",
]
