"""Single official generate -> validate -> render orchestration."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .generate import generate_outline
from .render import render_outline_directory
from .validate import validate_outline_outputs


def run_outline_pipeline(
    semantic_dir: Path | str,
    outline_dir: Path | str,
    *,
    authoring_spec_path: Path | str | None = None,
    authoring_spec: dict[str, Any] | None = None,
    force: bool = False,
) -> dict[str, Any]:
    """Run the only layer-four production sequence.

    Rendering is intentionally downstream of validation. A candidate may
    render for human authoring review, while its gate status remains blocked.
    """

    outline = Path(outline_dir).expanduser().resolve()
    if authoring_spec is not None and authoring_spec_path is not None:
        raise ValueError("authoring_spec and authoring_spec_path are mutually exclusive")
    if authoring_spec_path is not None:
        spec_path = Path(authoring_spec_path).expanduser().resolve()
        authoring_spec = json.loads(spec_path.read_text(encoding="utf-8"))
    generation = generate_outline(
        semantic_dir,
        outline,
        authoring_spec=authoring_spec,
        force=force,
    )
    validation = validate_outline_outputs(
        semantic_dir,
        outline,
        write_report=True,
    )
    rendered: str | None = None
    if validation.get("status") == "ok":
        rendered = str(render_outline_directory(outline, force=True))
    return {
        "status": "ok" if validation.get("status") == "ok" else "error",
        "generation": generation,
        "validation": validation,
        "rendered": rendered,
        "gates": validation.get("gates") or {},
    }


__all__ = ["run_outline_pipeline"]
