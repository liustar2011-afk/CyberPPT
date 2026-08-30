from __future__ import annotations

from pathlib import Path

from cyberppt.stage02_production.models import Stage02BuildContext


def test_build_context_exposes_run_id_as_compatibility_alias(tmp_path: Path) -> None:
    context = Stage02BuildContext(
        project=tmp_path,
        canonical_script=tmp_path / "script.md",
        selected_pages=(1,),
        pages_raw="1",
        build_id="20260831T000000Z-abcdef0123",
        build_dir=tmp_path / "build",
        style_lock=tmp_path / "style.json",
        source_script_sha256="script",
        script_input_sha256="intake",
        visual_spec_sha256="visual",
        style_lock_sha256="lock",
        production_mode="image-to-editable-svg",
        assembly_mode="editable",
        source_mode="script_file",
        input_fingerprint="f" * 64,
        resolved_style_contract_sha256="s" * 64,
    )

    assert context.run_id == context.build_id
    assert context.input_fingerprint != context.run_id


def test_identity_document_forbids_run_id_as_input_identity() -> None:
    text = (
        Path(__file__).resolve().parents[1] / "docs" / "STAGE02_BUILD_IDENTITY.md"
    ).read_text(encoding="utf-8")

    assert "不得用 `run_id/build_id` 判断两次运行的输入是否相同" in text
    assert "run_id == build_id" in text
