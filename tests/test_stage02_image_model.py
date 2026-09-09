import json
from pathlib import Path

import pytest

from cyberppt.cli import build_parser
from cyberppt.commands.final_script_pages import run_final_script_pages
from cyberppt.stage02_production.models import Stage02RunOptions
from cyberppt.stage02_production.preflight import resolve_image_model
from scripts.imagegen_pipeline.providers.codex_oauth_image import DEFAULT_MODEL


def test_cli_preserves_unspecified_model_and_explicit_override():
    args = ["final-script-pages", "project", "--script", "script.md", "--pages", "4"]
    assert build_parser().parse_args(args).image_model is None
    assert build_parser().parse_args(args + ["--image-model", "gpt-image-2"]).image_model == "gpt-image-2"


def test_cli_accepts_max_quality_for_sunburst():
    from scripts.imagegen_pipeline.providers.codex_oauth_image import _build_responses_body

    args = build_parser().parse_args([
        "final-script-pages", "project", "--script", "script.md", "--pages", "4",
        "--image-model", "gpt-image-2.5-sunburst", "--image-quality", "max",
    ])
    body = _build_responses_body(prompt="test", image_paths=[], model=args.image_model,
                                 size="1536x1024", quality=args.image_quality)
    assert body["tools"][0]["quality"] == "max"
    assert body["tools"][0]["model"] == "gpt-image-2.5-sunburst"


def test_default_quality_is_max_and_explicit_high_is_preserved(tmp_path):
    from scripts.imagegen_pipeline.providers.codex_oauth_image import DEFAULT_QUALITY

    args = ["final-script-pages", "project", "--script", "script.md", "--pages", "4"]
    assert build_parser().parse_args(args).image_quality == "max"
    assert build_parser().parse_args(args + ["--image-quality", "high"]).image_quality == "high"
    assert Stage02RunOptions(project=tmp_path, script=tmp_path / "script.md", pages_raw="4").image_quality == "max"
    assert DEFAULT_QUALITY == "max"


@pytest.mark.parametrize("record", ["page_image_pairs.json", "build_context.json"])
def test_resume_resolves_recorded_model_before_default(tmp_path, record):
    options = Stage02RunOptions(project=tmp_path, script=tmp_path / "script.md", pages_raw="4")
    assert resolve_image_model(options, tmp_path).image_model == "gpt-image-2.5-sunburst"
    (tmp_path / record).write_text(json.dumps({"input_identity": {"image_model": "gpt-image-2"}}))
    assert resolve_image_model(options, tmp_path).image_model == "gpt-image-2"


def test_unrecorded_legacy_model_requires_explicit_selection(tmp_path):
    (tmp_path / "page_image_pairs.json").write_text("{}")
    options = Stage02RunOptions(project=tmp_path, script=tmp_path / "script.md", pages_raw="4")
    with pytest.raises(ValueError, match="explicit --image-model"):
        resolve_image_model(options, tmp_path)
    explicit = Stage02RunOptions(project=tmp_path, script=options.script, pages_raw="4", image_model="gpt-image-2")
    assert resolve_image_model(explicit, tmp_path).image_model == "gpt-image-2"


@pytest.mark.parametrize("model", [None, "gpt-image-2"])
def test_official_facade_dry_run_persists_and_resumes_effective_model(tmp_path: Path, model):
    script = tmp_path / "script.md"
    script.write_text("""## P04 运营责任
- 页面类型：内容页
- 页面标题：运营责任

### 完整文字稿
明确运营责任和使用范围。

### 上屏文字
- 明确运营责任和使用范围。
""", encoding="utf-8")
    build = tmp_path / "build"
    kwargs = dict(project=tmp_path / "project", script=script, pages_raw="4",
                  external_script=True, output_dir=build, build_id="model-test",
                  generate_images=True, dry_run_images=True)
    run_final_script_pages(**kwargs, image_model=model)
    expected = model or DEFAULT_MODEL
    # Repeating the original command without a model must retain the batch identity.
    result = run_final_script_pages(**kwargs)
    manifest = json.loads((build / "page_image_pairs.json").read_text())
    assert manifest["input_identity"]["image_model"] == expected
    request = json.loads((build / "prompts/attempts/page-004-full-attempt-01-request.json").read_text())
    assert request["model"] == request["requested_model"] == expected
    assert request["quality"] == "max"
    assert manifest["input_identity"]["image_quality"] == "max"
    assert "--image-quality max" in result["resume_command"]
    assert request["actual_model"] is None
    assert request["model_verification"] == "unknown_backend_model_not_captured"
    assert f"--image-model {expected}" in result["resume_command"]
