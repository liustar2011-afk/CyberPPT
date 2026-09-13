from dataclasses import replace
from pathlib import Path
from unittest.mock import Mock
import json
import shlex

import pytest

from cyberppt.stage02_production import orchestrator, delivery_stage
from cyberppt.stage02_production.dependencies import Stage02Dependencies
from cyberppt.stage02_production.models import (
    Stage02RunOptions, Stage02BuildContext, ManifestStageResult, ImageStageResult,
    ReconstructionStageResult,
)


def setup_run(tmp_path, monkeypatch, *, mode="editable", dry=False, active=True):
    context = Stage02BuildContext(
        project=tmp_path, canonical_script=tmp_path / "script.md", selected_pages=(1,),
        pages_raw="1", build_id="pause-test", build_dir=tmp_path / "build",
        style_lock=tmp_path / "style.json", source_script_sha256="source",
        script_input_sha256="input", visual_spec_sha256="visual", style_lock_sha256="style",
        production_mode="image-to-editable-svg", assembly_mode=mode, source_mode="external_script",
    )
    context.build_dir.mkdir()
    files = [tmp_path / "compiled.md", tmp_path / "template.json", tmp_path / "context.json"]
    for path in [*files, context.canonical_script, context.style_lock]:
        path.write_text("{}")
    payload = {"pairs": [{"page_number": 1, "full": {"path": str(tmp_path / "p01.png")}}]}
    manifest = ManifestStageResult(payload, context.build_dir / "page_image_pairs.json", files[0], (1,), files[1], files[2])
    options = Stage02RunOptions(project=tmp_path, script=context.canonical_script, pages_raw="1",
        image_model="test-model", production_build=active, generate_images=active,
        stop_after_images=True, assembly_mode=mode, dry_run_images=dry)
    images = ImageStageResult(payload)
    monkeypatch.setattr(orchestrator, "prepare_preflight", lambda _: context)
    monkeypatch.setattr(orchestrator, "resolve_image_model", lambda o, _: o)
    monkeypatch.setattr(orchestrator, "prepare_manifest", lambda *_: manifest)
    monkeypatch.setattr(orchestrator, "apply_page_local_reuse", lambda **_: None)
    monkeypatch.setattr(orchestrator, "run_image_stage", lambda *_: images)
    normalize = Mock()
    monkeypatch.setattr(orchestrator, "normalize_audited_manifest_images", normalize)
    for name in ("run_reconstruction_stage", "run_full_image_rhythm_stage", "bind_reconstruction_visual_sources"):
        monkeypatch.setattr(orchestrator, name, Mock(side_effect=AssertionError(name + " ran after pause")))
    monkeypatch.setattr(delivery_stage, "_run_office_qa", Mock(side_effect=AssertionError("Office QA ran")))
    monkeypatch.setattr(delivery_stage, "_run_final_visible_text_qa", Mock(side_effect=AssertionError("final QA ran")))
    deps = Stage02Dependencies(require_generated=Mock(), append_ledger=Mock())
    return options, context, manifest, deps, normalize


@pytest.mark.parametrize("mode", ["image", "editable", "both"])
def test_pause_persists_and_continuation_keeps_identity(tmp_path, monkeypatch, mode):
    options, context, manifest, deps, normalize = setup_run(tmp_path, monkeypatch, mode=mode)
    result = orchestrator.run_production(options, dependencies=deps)
    deps.require_generated.assert_called_once()
    normalize.assert_called_once()
    summary = json.loads(result.delivery.summary_path.read_text())
    assert summary["status"] == "paused_after_images"
    assert summary["artifacts"]["exported_pptx"] is None
    assert summary["artifacts"]["audited_images"] == [str(tmp_path / "p01.png")]
    assert json.loads(manifest.manifest_path.read_text())["stage02_state"]["state"] == "paused_after_images"
    assert json.loads(manifest.build_context_path.read_text())["status"] == "paused_after_images"
    command = shlex.split(summary["resume_command"])
    assert "--stop-after-images" not in command
    assert "--stop-after-images" in shlex.split(summary["retry_command"])
    for flag, value in [("--build-id", context.build_id), ("--output-dir", str(context.build_dir)), ("--assembly-mode", mode)]:
        assert command[command.index(flag)+1] == value
    assert "--generate-images" in command and "--production-build" in command and "--external-script" in command
    # Removing the stop flag is a continuation control, not an input change.
    monkeypatch.setattr(orchestrator, "run_full_image_rhythm_stage", lambda *a, **k: {"status": "passed"})
    monkeypatch.setattr(orchestrator, "bind_reconstruction_visual_sources", lambda *_: None)
    reconstruction = Mock(return_value=ReconstructionStageResult(status="production_ready"))
    monkeypatch.setattr(orchestrator, "run_reconstruction_stage", reconstruction)
    monkeypatch.setattr(orchestrator, "run_delivery_stage", lambda *a: result.delivery)
    orchestrator.run_production(replace(options, stop_after_images=False), dependencies=deps)
    reconstruction.assert_called_once()


def test_failed_image_gate_cannot_report_pause(tmp_path, monkeypatch):
    options, _, manifest, deps, _ = setup_run(tmp_path, monkeypatch)
    deps.require_generated.side_effect = ValueError("image text audit failed")
    with pytest.raises(ValueError, match="image text audit failed"):
        orchestrator.run_production(options, dependencies=deps)
    assert not manifest.manifest_path.exists()
    assert not list(tmp_path.rglob("*_final_script_pages_run.json"))


@pytest.mark.parametrize("dry,active", [(True, True), (False, False)])
def test_compile_only_or_dry_run_does_not_claim_audited_pause(tmp_path, monkeypatch, dry, active):
    options, _, _, deps, _ = setup_run(tmp_path, monkeypatch, dry=dry, active=active)
    reconstruction = Mock(return_value=ReconstructionStageResult())
    monkeypatch.setattr(orchestrator, "run_reconstruction_stage", reconstruction)
    monkeypatch.setattr(orchestrator, "run_delivery_stage", lambda *a: None)
    result = orchestrator.run_production(options, dependencies=deps)
    assert result.reconstruction.status != "paused_after_images"
    deps.require_generated.assert_not_called()


def test_skip_audit_rejected_before_mutation(tmp_path, monkeypatch):
    options, _, _, deps, _ = setup_run(tmp_path, monkeypatch)
    preflight = Mock(side_effect=AssertionError("preflight ran"))
    monkeypatch.setattr(orchestrator, "prepare_preflight", preflight)
    with pytest.raises(ValueError, match="requires image text audit"):
        orchestrator.run_production(replace(options, skip_image_text_audit=True), dependencies=deps)
    preflight.assert_not_called()
