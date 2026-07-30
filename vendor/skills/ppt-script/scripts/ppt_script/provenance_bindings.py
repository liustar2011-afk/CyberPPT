"""Single registry for editorial provenance digest bindings.

editorial.py validates against this map; provenance-sync refreshes the same
inputs/targets. Do not duplicate binding lists elsewhere.
"""

from __future__ import annotations

from typing import Literal

ProvenanceSyncPhase = Literal["storyline", "outline", "red-team-review", "red-team", "all"]

_BASE_CONTRACTS = (
    "contracts/semantic-core.json",
    "contracts/content-role-map.json",
    "contracts/solution-model.json",
)

# relative editorial/contract JSON -> {"inputs": (...), "targets": (...)}
EDITORIAL_DIGEST_BINDINGS: dict[str, dict[str, tuple[str, ...]]] = {
    "contracts/semantic-core.json": {
        "inputs": ("analysis/01-source-truth-map.md",),
    },
    "contracts/content-role-map.json": {
        "inputs": ("analysis/01-source-truth-map.md",),
    },
    "contracts/solution-model.json": {
        "inputs": ("analysis/01-source-truth-map.md",),
    },
    "analysis/editorial/01-independent-judgment.json": {
        "inputs": ("analysis/01-source-truth-map.md", *_BASE_CONTRACTS),
    },
    "analysis/editorial/storyline-candidates.json": {
        "inputs": (*_BASE_CONTRACTS, "analysis/editorial/01-independent-judgment.json"),
    },
    "analysis/editorial/02-storyline-verdict.json": {
        "inputs": (
            "analysis/editorial/01-independent-judgment.json",
            "analysis/editorial/storyline-candidates.json",
        ),
        "targets": (
            "decision/01-decision.md",
            "contracts/deck-decision.json",
        ),
    },
    "analysis/editorial/03-outline-review.json": {
        "inputs": ("analysis/editorial/02-storyline-verdict.json",),
        "targets": (
            "outline/02-outline.md",
            "contracts/chapter-contracts.json",
            "contracts/page-contracts.json",
        ),
    },
    "analysis/editorial/04-red-team-review.json": {
        "inputs": ("analysis/editorial/02-storyline-verdict.json",),
        "targets": ("outline/02-outline.md",),
    },
    "analysis/editorial/05-red-team-response.json": {
        "inputs": (
            "analysis/editorial/04-red-team-review.json",
            "analysis/editorial/02-storyline-verdict.json",
        ),
        "targets": ("outline/02-outline.md",),
    },
}

# Files refreshed by provenance-sync (human-editable downstream targets).
PROVENANCE_SYNC_SPECS: dict[str, tuple[str, ...]] = {
    "storyline": ("analysis/editorial/02-storyline-verdict.json",),
    "outline": ("analysis/editorial/03-outline-review.json",),
    "red-team-review": ("analysis/editorial/04-red-team-review.json",),
    "red-team": (
        "analysis/editorial/04-red-team-review.json",
        "analysis/editorial/05-red-team-response.json",
    ),
}

# Authority artifacts whose SHA must match 00-active-context.json after context-pack.
CONTEXT_FRESHNESS_TARGETS: tuple[str, ...] = (
    "decision/01-decision.md",
    "decision/02-expression-logic.md",
    "outline/02-outline.md",
    "contracts/deck-decision.json",
    "contracts/chapter-contracts.json",
    "contracts/page-contracts.json",
)


def binding_groups(relative: str) -> dict[str, tuple[str, ...]]:
    groups = EDITORIAL_DIGEST_BINDINGS.get(relative)
    if not groups:
        return {}
    return {
        key: value
        for key, value in groups.items()
        if key in ("inputs", "targets") and value
    }


def sync_files_for_phase(phase: ProvenanceSyncPhase) -> tuple[str, ...]:
    if phase == "all":
        order: list[str] = []
        seen: set[str] = set()
        for name in ("storyline", "outline", "red-team-review", "red-team"):
            for relative in PROVENANCE_SYNC_SPECS[name]:
                if relative not in seen:
                    order.append(relative)
                    seen.add(relative)
        return tuple(order)
    if phase not in PROVENANCE_SYNC_SPECS:
        raise ValueError(
            f"未知 provenance 阶段：{phase}；可选 storyline|outline|red-team-review|red-team|all"
        )
    return PROVENANCE_SYNC_SPECS[phase]
