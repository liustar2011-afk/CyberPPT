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
from scripts.imagegen_pipeline.providers.codex_oauth_image import ensure_output_size, run_codex_image


RequireGenerated = Callable[[dict[str, Any]], Any]
RunCodexImage = Callable[..., Any]
EnsureOutputSize = Callable[[Any, str], Any]
StageCallable = Callable[..., Any]


@dataclass(frozen=True)
class Stage02Dependencies:
    """Runtime callables supplied explicitly to the Stage 02 pipeline.

    The three optional stage callables use ``None`` to mean "use the module's
    production default". This avoids circular imports while allowing the
    historical facade to pass patched implementations without mutating module
    globals.
    """

    require_generated: RequireGenerated
    run_codex_image: RunCodexImage = run_codex_image
    ensure_output_size: EnsureOutputSize = ensure_output_size
    reconstruction_build: StageCallable | None = None
    officecli_render_qa: StageCallable | None = None
    append_ledger: StageCallable | None = None


def default_stage02_dependencies() -> Stage02Dependencies:
    return Stage02Dependencies(
        require_generated=require_generated,
        run_codex_image=run_codex_image,
        ensure_output_size=ensure_output_size,
    )


__all__ = [
    "EnsureOutputSize",
    "RequireGenerated",
    "RunCodexImage",
    "Stage02Dependencies",
    "StageCallable",
    "default_stage02_dependencies",
]
