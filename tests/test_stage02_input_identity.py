from __future__ import annotations

from dataclasses import replace
from pathlib import Path

from cyberppt.stage02_production.identity import input_fingerprint
from cyberppt.stage02_production.models import Stage02BuildContext, Stage02RunOptions


def _context(tmp_path: Path, *, build_id: str) -> Stage02BuildContext:
    script = tmp_path / "script.md"
    lock = tmp_path / "style.json"
    script.write_text("script", encoding="utf-8")
    lock.write_text("{}", encoding="utf-8")
    return Stage02BuildContext(
        project=tmp_path,
        canonical_script=script,
        selected_pages=(1, 2),
        pages_raw="1-2",
        build_id=build_id,
        build_dir=tmp_path / build_id,
        style_lock=lock,
        source_script_sha256="script-sha",
        script_input_sha256="input-sha",
        visual_spec_sha256="visual-sha",
        style_lock_sha256="style-sha",
        production_mode="image-to-editable-svg",
        assembly_mode="editable",
        source_mode="script_file",
    )


def test_input_fingerprint_is_independent_of_run_id(tmp_path: Path) -> None:
    options_a = Stage02RunOptions(project=tmp_path, script=tmp_path / "script.md", pages_raw="1-2")
    options_b = Stage02RunOptions(project=tmp_path, script=tmp_path / "script.md", pages_raw="1-2")
    assert input_fingerprint(_context(tmp_path, build_id="run-a"), options_a) == input_fingerprint(
        _context(tmp_path, build_id="run-b"), options_b
    )


def test_input_fingerprint_changes_with_output_affecting_options(tmp_path: Path) -> None:
    context = _context(tmp_path, build_id="run-a")
    high = Stage02RunOptions(project=tmp_path, script=tmp_path / "script.md", pages_raw="1-2", image_quality="high")
    low = Stage02RunOptions(project=tmp_path, script=tmp_path / "script.md", pages_raw="1-2", image_quality="low")
    assert input_fingerprint(context, high) != input_fingerprint(context, low)


def test_input_fingerprint_changes_with_external_script_contract(tmp_path: Path) -> None:
    local = _context(tmp_path, build_id="run-a")
    external = replace(local, source_mode="external_script")
    options = Stage02RunOptions(project=tmp_path, script=tmp_path / "script.md", pages_raw="1-2")

    assert input_fingerprint(local, options) != input_fingerprint(external, options)
