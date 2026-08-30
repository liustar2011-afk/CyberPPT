from __future__ import annotations

from cyberppt.stage02_production.compat import LEGACY_PATCH_FIELDS, LegacyPatchSet


def test_legacy_patch_surface_is_finite_and_explicit() -> None:
    assert LEGACY_PATCH_FIELDS == (
        "run_codex_image",
        "ensure_output_size",
        "require_generated",
        "reconstruction_build",
        "officecli_render_qa",
        "append_ledger",
    )
    assert len(LegacyPatchSet.__dataclass_fields__) == 6
