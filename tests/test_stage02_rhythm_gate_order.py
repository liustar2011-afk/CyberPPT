from pathlib import Path

import pytest

from cyberppt.stage02_production import orchestrator
from cyberppt.stage02_production.dependencies import Stage02Dependencies
from cyberppt.stage02_production.models import (
    ImageStageResult,
    ManifestStageResult,
    Stage02BuildContext,
    Stage02RunOptions,
)


def _context(tmp_path: Path) -> Stage02BuildContext:
    return Stage02BuildContext(
        project=tmp_path,
        canonical_script=tmp_path / "script.md",
        selected_pages=(1,),
        pages_raw="1",
        build_id="BUILD",
        build_dir=tmp_path / "build",
        style_lock=tmp_path / "style.json",
        source_script_sha256="a" * 64,
        script_input_sha256="b" * 64,
        visual_spec_sha256="c" * 64,
        style_lock_sha256="d" * 64,
        production_mode="image-to-editable-svg",
        assembly_mode="editable",
        source_mode="external",
    )


def _manifest(tmp_path: Path) -> ManifestStageResult:
    return ManifestStageResult(
        manifest={"pairs": []},
        manifest_path=tmp_path / "manifest.json",
        compiled_script=tmp_path / "compiled.md",
        page_numbers=(1,),
        template_lock_path=tmp_path / "template.json",
        build_context_path=tmp_path / "context.json",
    )


def _options(tmp_path: Path) -> Stage02RunOptions:
    return Stage02RunOptions(
        project=tmp_path,
        script=tmp_path / "script.md",
        pages_raw="1",
        require_images=True,
        production_build=True,
        assembly_mode="editable",
    )


def _install_common(monkeypatch, tmp_path: Path, events: list[str], rhythm_status: str) -> Stage02Dependencies:
    context = _context(tmp_path)
    manifest = _manifest(tmp_path)
    images = ImageStageResult(manifest={"pairs": []})
    monkeypatch.setattr(orchestrator, "prepare_preflight", lambda options: context)
    monkeypatch.setattr(orchestrator, "prepare_manifest", lambda context, options: manifest)
    monkeypatch.setattr(orchestrator, "run_image_stage", lambda context, manifest, options: images)
    monkeypatch.setattr(orchestrator, "normalize_audited_manifest_images", lambda payload: events.append("normalize"))

    def rhythm(payload, *, build_dir):
        events.append("rhythm")
        assert build_dir == context.build_dir
        payload["full_image_deck_rhythm_qa"] = {"status": rhythm_status}
        return {"status": rhythm_status, "receipt_path": str(build_dir / "qa" / "receipt.json")}

    monkeypatch.setattr(orchestrator, "run_full_image_rhythm_stage", rhythm)
    monkeypatch.setattr(orchestrator, "write_json", lambda path, payload: events.append("write"))
    monkeypatch.setattr(orchestrator, "bind_reconstruction_visual_sources", lambda payload: events.append("bind"))
    monkeypatch.setattr(orchestrator, "run_reconstruction_stage", lambda *args: events.append("reconstruct") or object())
    monkeypatch.setattr(orchestrator, "run_delivery_stage", lambda *args: events.append("delivery") or object())
    return Stage02Dependencies(require_generated=lambda payload: events.append("require"))


def test_rhythm_gate_runs_after_generated_check_and_before_authority_binding(monkeypatch, tmp_path):
    events: list[str] = []
    dependencies = _install_common(monkeypatch, tmp_path, events, "passed_with_warnings")
    orchestrator.run_production(_options(tmp_path), dependencies=dependencies)
    assert events.index("require") < events.index("rhythm") < events.index("bind")
    assert events.index("rhythm") < events.index("write") < events.index("bind")
    assert events[-2:] == ["reconstruct", "delivery"]


def test_blocked_rhythm_is_persisted_and_prevents_reconstruction_authority(monkeypatch, tmp_path):
    events: list[str] = []
    dependencies = _install_common(monkeypatch, tmp_path, events, "blocked")
    with pytest.raises(RuntimeError, match="FULL_IMAGE_DECK_RHYTHM_BLOCKED"):
        orchestrator.run_production(_options(tmp_path), dependencies=dependencies)
    assert events.index("rhythm") < events.index("write")
    assert "bind" not in events
    assert "reconstruct" not in events
    assert "delivery" not in events
