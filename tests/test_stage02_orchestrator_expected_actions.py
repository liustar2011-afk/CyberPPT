from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

from cyberppt.stage02_production.models import (
    ImageStageResult,
    ManifestStageResult,
    Stage02BuildContext,
    Stage02RunOptions,
)
from cyberppt.stage02_production.orchestrator import run_production


def test_missing_authored_svg_returns_needs_action_instead_of_failure(tmp_path: Path) -> None:
    image = tmp_path / "p1.png"
    image.write_bytes(b"image")
    script = tmp_path / "script.md"
    script.write_text("script", encoding="utf-8")
    lock = tmp_path / "style.json"
    lock.write_text("{}", encoding="utf-8")
    build_dir = tmp_path / "build"
    build_dir.mkdir()
    manifest_path = build_dir / "page_image_pairs.json"
    context_path = build_dir / "build_context.json"
    context_path.write_text("{}", encoding="utf-8")
    manifest_payload = {
        "pairs": [
            {
                "page_number": 1,
                "full": {
                    "path": str(image),
                    "status": "Generated",
                    "text_audit": {"valid": True},
                },
            }
        ]
    }
    context = Stage02BuildContext(
        project=tmp_path,
        canonical_script=script,
        selected_pages=(1,),
        pages_raw="1",
        build_id="run-1",
        build_dir=build_dir,
        style_lock=lock,
        source_script_sha256="script",
        script_input_sha256="input",
        visual_spec_sha256="visual",
        style_lock_sha256="style",
        production_mode="image-to-editable-svg",
        assembly_mode="editable",
        source_mode="script_file",
    )
    manifest_result = ManifestStageResult(
        manifest=manifest_payload,
        manifest_path=manifest_path,
        compiled_script=script,
        page_numbers=(1,),
        template_lock_path=lock,
        build_context_path=context_path,
    )
    images = ImageStageResult(manifest=manifest_payload)
    options = Stage02RunOptions(
        project=tmp_path,
        script=script,
        pages_raw="1",
        production_build=False,
    )

    with (
        patch("cyberppt.stage02_production.orchestrator.prepare_preflight", return_value=context),
        patch("cyberppt.stage02_production.orchestrator.prepare_manifest", return_value=manifest_result),
        patch("cyberppt.stage02_production.orchestrator.run_image_stage", return_value=images),
        patch(
            "cyberppt.stage02_production.orchestrator.run_reconstruction_stage",
            side_effect=ValueError("requires a hand-authored SVG"),
        ),
    ):
        result = run_production(options)

    assert result.reconstruction.status == "needs_action"
    assert result.delivery.summary["status"] == "needs_action"
    assert result.delivery.summary["actions"][0]["state"] == "needs_svg_authoring"
    assert result.delivery.summary_path.is_file()
