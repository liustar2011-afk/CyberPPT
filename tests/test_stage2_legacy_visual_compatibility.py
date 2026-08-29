from pathlib import Path

from cyberppt.page_artifact_spec import build_page_artifact_spec
from scripts.imagegen_pipeline.artifact_prompt import build_final_prompt_ir
from scripts.imagegen_pipeline.final_prompt_renderer import render_final_prompt
from tests.test_page_artifact_spec import PageArtifactSpecTests


def _legacy_inputs(tmp_path: Path, *, use_scene: bool):
    handoff_page, visual_page, style_lock = PageArtifactSpecTests()._inputs(tmp_path)
    visual_page.pop("region_graph", None)
    visual_page.pop("visual_medium_policy", None)
    visual_page["image_plan"].pop("scene_policy", None)
    visual_page["image_plan"]["use_scene"] = use_scene
    for item in visual_page.get("final_text") or []:
        item.pop("region_id", None)
    return handoff_page, visual_page, style_lock


def _build(tmp_path: Path, *, use_scene: bool):
    handoff_page, visual_page, style_lock = _legacy_inputs(tmp_path, use_scene=use_scene)
    return build_page_artifact_spec(
        handoff_page=handoff_page,
        visual_page=visual_page,
        style_lock=style_lock,
        script_input_sha256="a" * 64,
        visual_source_sha256="b" * 64,
    )


def test_legacy_visual_spec_without_region_or_medium_policy_still_compiles(tmp_path):
    spec = _build(tmp_path, use_scene=True)
    assert spec.region_graph is None
    assert spec.visual_medium_policy is None
    assert spec.visual_carrier.use_scene is True
    assert spec.visual_carrier.scene_policy == "allowed"

    ir = build_final_prompt_ir(spec)
    assert ir.region_graph is None
    assert ir.visual_medium_policy is None
    assert ir.micro_visual_freedom is None
    prompt = render_final_prompt(ir)
    assert "Macro region structure:" not in prompt
    assert "ImageGen region-internal freedom:" not in prompt
    for visible_text in ir.visible_text:
        assert prompt.count(f'- Exact visible text: "{visible_text}"') == 1


def test_legacy_use_scene_false_maps_to_forbidden_scene_policy(tmp_path):
    spec = _build(tmp_path, use_scene=False)
    assert spec.region_graph is None
    assert spec.visual_medium_policy is None
    assert spec.visual_carrier.use_scene is False
    assert spec.visual_carrier.scene_policy == "forbidden"
    render_final_prompt(build_final_prompt_ir(spec))
