"""Explicit Stage 02 runtime dependencies.

Production code consumes these callables through a typed dependency object so
compatibility shims do not need to mutate module globals. Fields are migrated
from the legacy patch seam incrementally; default dependencies always point to
the repository's concrete production backends.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable

from scripts.imagegen_pipeline.page_manifest import require_generated


RequireGenerated = Callable[[dict[str, Any]], Any]


@dataclass(frozen=True)
class Stage02Dependencies:
    """Runtime callables supplied explicitly to the Stage 02 orchestrator."""

    require_generated: RequireGenerated


def default_stage02_dependencies() -> Stage02Dependencies:
    return Stage02Dependencies(require_generated=require_generated)


__all__ = [
    "RequireGenerated",
    "Stage02Dependencies",
    "default_stage02_dependencies",
]
