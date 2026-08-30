"""Pytest migration helpers for Stage 02 ownership boundaries.

Production no longer copies monkey patches from the historical
``cyberppt.commands.final_script_pages`` facade into typed Stage 02 modules.
The large legacy regression module still names those old patch points.  During
its migration window, translate only those test patch targets to the modules
that now own the dependency.  This keeps production non-mutating while the
historical regression suite continues to exercise the same seams.
"""
from __future__ import annotations

from unittest.mock import patch as _stdlib_patch


_STAGE02_PATCH_TARGETS = {
    "cyberppt.commands.final_script_pages.run_codex_image": (
        "cyberppt.stage02_production.image_stage.run_codex_image"
    ),
    "cyberppt.commands.final_script_pages.ensure_output_size": (
        "cyberppt.stage02_production.image_stage.ensure_output_size"
    ),
    "cyberppt.commands.final_script_pages.require_generated": (
        "cyberppt.stage02_production.orchestrator.require_generated"
    ),
    "cyberppt.commands.final_script_pages._run_image_to_editable_svg_build": (
        "cyberppt.stage02_production.reconstruction_stage._run_image_to_editable_svg_build"
    ),
    "cyberppt.commands.final_script_pages.run_officecli_render_qa": (
        "cyberppt.stage02_production.delivery_stage.run_officecli_render_qa"
    ),
    "cyberppt.commands.final_script_pages._append_ledger": (
        "cyberppt.stage02_production.delivery_stage._append_ledger"
    ),
}


def _stage02_patch(target: str, *args: object, **kwargs: object):
    return _stdlib_patch(_STAGE02_PATCH_TARGETS.get(target, target), *args, **kwargs)


# Preserve the normal helper surface if the legacy module happens to use it.
_stage02_patch.object = _stdlib_patch.object  # type: ignore[attr-defined]
_stage02_patch.dict = _stdlib_patch.dict  # type: ignore[attr-defined]
_stage02_patch.multiple = _stdlib_patch.multiple  # type: ignore[attr-defined]
_stage02_patch.stopall = _stdlib_patch.stopall  # type: ignore[attr-defined]
_stage02_patch.TEST_PREFIX = _stdlib_patch.TEST_PREFIX  # type: ignore[attr-defined]


def pytest_collection_modifyitems(items: list[object]) -> None:
    """Redirect old Stage 02 patch names only in the legacy regression module."""

    for item in items:
        module = getattr(item, "module", None)
        if getattr(module, "__name__", "") == "test_final_script_pages":
            setattr(module, "patch", _stage02_patch)
