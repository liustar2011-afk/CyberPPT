from dataclasses import replace
from pathlib import Path
import shlex

import pytest

from cyberppt.stage02_production.delivery_stage import _resume_command
from cyberppt.stage02_production.models import Stage02BuildContext, Stage02RunOptions
from cyberppt.stage02_production.state import _production_invocation, require_production_invocation


@pytest.fixture
def context(tmp_path):
    project = tmp_path / "中文项目 with spaces"
    return Stage02BuildContext(project=project, canonical_script=project / "final script.md",
        selected_pages=(1, 2), pages_raw="1-2", build_id="stable-build",
        build_dir=project / "production", style_lock=project / "style lock.json",
        source_script_sha256="script", script_input_sha256="script", visual_spec_sha256="",
        style_lock_sha256="style", production_mode="image-to-editable-svg",
        assembly_mode="editable", source_mode="script_file")


def invocation_args(context):
    return dict(project=context.project, manifest_path=context.build_dir / "page_image_pairs.json",
        output_dir=context.build_dir / "editable_svg", requested_pages=[1, 2], assembly_mode="editable")


def test_invocation_is_cleared_on_exception(context):
    with pytest.raises(RuntimeError, match="failed stage"):
        with _production_invocation(context):
            require_production_invocation(**invocation_args(context))
            raise RuntimeError("failed stage")
    with pytest.raises(ValueError, match="STAGE02_OFFICIAL_ENTRY_REQUIRED"):
        require_production_invocation(**invocation_args(context))


@pytest.mark.parametrize("field,value", [
    ("project", Path("another-project")), ("manifest_path", Path("another-manifest.json")),
    ("output_dir", Path("temporary-export")), ("requested_pages", [1]),
    ("requested_pages", [2, 1]), ("assembly_mode", "image"),
])
def test_invocation_rejects_changed_target(context, field, value):
    args = invocation_args(context)
    args[field] = value
    with _production_invocation(context), pytest.raises(ValueError, match="STAGE02_INVOCATION_MISMATCH"):
        require_production_invocation(**args)


@pytest.mark.parametrize("mode", ["editable", "image", "both"])
def test_resume_round_trips_spaces_and_production_parameters(context, mode):
    context = replace(context, assembly_mode=mode)
    options = Stage02RunOptions(project=context.project, script=context.canonical_script,
        pages_raw="1-2", production_build=True, assembly_mode=mode, force_images=True,
        allow_prompt_edit=True, prompt_overrides_dir=context.project / "原有 prompts",
        reuse_audited_images_from=context.project / "原图 batch" / "page_image_pairs.json",
        image_quality="medium", image_timeout=321, no_style_reference=True)
    args = shlex.split(_resume_command(context, options))
    assert args[:4] == [".venv/bin/python3", "-m", "cyberppt", "final-script-pages"]
    assert args[4] == str(context.project)
    expected = {"--script": str(context.canonical_script), "--pages": "1-2",
        "--build-id": context.build_id, "--output-dir": str(context.build_dir),
        "--assembly-mode": mode, "--production-mode": "image-to-editable-svg",
        "--prompt-overrides-dir": str(options.prompt_overrides_dir),
        "--reuse-audited-images-from": str(options.reuse_audited_images_from),
        "--image-timeout": "321", "--image-quality": "medium"}
    for flag, value in expected.items():
        assert args[args.index(flag) + 1] == value
    assert "--production-build" in args and "--generate-images" in args
    assert "--force-images" not in args and "--skip-image-text-audit" not in args
