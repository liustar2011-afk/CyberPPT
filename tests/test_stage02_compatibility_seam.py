from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

from cyberppt.stage02_production import compat


ROOT = Path(__file__).resolve().parents[1]


def test_legacy_patch_sync_is_non_mutating() -> None:
    target = SimpleNamespace(value="original")

    compat.sync_legacy_patch_points(
        image_stage=target,
        orchestrator=target,
        reconstruction_stage=target,
        delivery_stage=target,
        run_codex_image_patch="replacement",
        ensure_output_size_patch="replacement",
        require_generated_patch="replacement",
        reconstruction_patch="replacement",
        officecli_patch="replacement",
        append_ledger_patch="replacement",
    )

    assert target.value == "original"
    assert not hasattr(target, "run_codex_image")
    assert not hasattr(target, "require_generated")


def test_final_script_pages_does_not_sync_patch_points_before_production() -> None:
    source = (ROOT / "cyberppt" / "commands" / "final_script_pages.py").read_text(encoding="utf-8")
    run_body = source.split("def run_final_script_pages(", 1)[1]

    assert "_sync_legacy_patch_points()" not in run_body
    assert "_orchestrator.run_production(" in run_body
