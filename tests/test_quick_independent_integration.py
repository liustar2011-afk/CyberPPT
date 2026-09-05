from __future__ import annotations

import hashlib
import json
import os
import xml.etree.ElementTree as ET
from pathlib import Path
from unittest.mock import Mock

import pytest
from PIL import Image, ImageDraw

from scripts.image_to_pptx_runtime.authored_layers import (
    REVIEW_CHECKS, register_quick_page, validate_authored_layers,
)
from scripts.image_to_pptx_runtime.clean_base_policy import is_reusable_clean_base
from scripts.image_to_pptx_runtime import stage02_adapter


def _hash(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _write(path, data):
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def _author(root, page=1):
    folder = root / "authoring" / f"p{page}"
    folder.mkdir(parents=True, exist_ok=True)
    source, base = folder / "source.png", folder / "base.png"
    color = "#EDF4FB" if page == 1 else "#FFF3E5"
    clean = Image.new("RGB", (400, 200), color)
    clean.save(base)
    original = clean.copy()
    ImageDraw.Draw(original).rectangle((40, 45, 170, 80), fill="#12355B")
    original.save(source)
    svg = folder / "page.svg"
    svg.write_text('''<svg xmlns="http://www.w3.org/2000/svg" width="400" height="200"
      viewBox="0 0 400 200" data-cyberppt-native-text-style="locked">
      <image href="base.png" x="0" y="0" width="400" height="200"/>
      <text x="40" y="80" font-family="Arial" font-size="24" fill="#12355B">登记编目</text>
    </svg>''', encoding="utf-8")
    return {
        "page_number": page, "authoring_svg": str(svg),
        "full": {"path": str(source), "canvas": "400x200", "status": "Generated",
                 "text_audit": {"valid": True}, "sha256": _hash(source),
                 "debug_receipt": {"visible_text": ["登记编目"]},
                 "reconstruction_visual_source": {
                     "authority": "audited_full_image", "path": str(source),
                     "sha256": _hash(source), "immutable_visual_composition": True,
                 }},
        "graphic_text_policy": {
            "schema": "cyberppt.image_to_pptx.graphic_text_policy.v1",
            "status": "complete", "empty_container_check": "passed",
            "fidelity_mode": "exact_source_image",
            "source_image_sha256": _hash(source),
            "source_text_inventory": [
                {"id": "label", "text": "登记编目", "bbox": [40, 45, 170, 80]},
            ],
            "items": [
                {"id": "label", "text": "登记编目", "treatment": "native_text",
                 "source_visible": True, "bbox": [40, 45, 170, 80]},
            ],
        },
    }


@pytest.fixture
def local_page(tmp_path):
    pair = _author(tmp_path)
    script = tmp_path / "script.md"
    script.write_text("## 第1页：测试\n登记编目\n", encoding="utf-8")
    path = tmp_path / "page_image_pairs.json"
    manifest = {"run_id": "local", "source_script": str(script), "source_script_sha256": _hash(script),
                "requested_pages": [1], "pairs": [pair]}
    _write(path, manifest)
    _write(tmp_path / "build_context.json", {
        "schema": "cyberppt.build_context.v1", "stage": "02-production-build",
        "build_id": "local", "assembly_mode": "editable", "source_script_sha256": _hash(script),
    })
    return path, pair


def _register(path, pair):
    svg = Path(pair["authoring_svg"])
    return register_quick_page(path, page_number=pair["page_number"], authored_svg=svg,
        clean_base=svg.parent / "base.png", source_sha256=pair["full"]["sha256"],
        reviewer="test-fixture", checks={key: "passed" for key in REVIEW_CHECKS})


def test_register_local_page_and_reuse(local_page):
    path, pair = local_page
    assert _register(path, pair)["status"] == "registered"
    current = json.loads(path.read_text())["pairs"][0]
    assert is_reusable_clean_base(current["clean_base"], full_image=pair["full"]["path"],
                                  graphic_text_policy=pair["graphic_text_policy"])


@pytest.mark.parametrize("changed", ["source", "base", "svg", "policy", "review", "canvas"])
def test_changed_input_invalidates_registered_layers(local_page, changed):
    path, pair = local_page
    _register(path, pair)
    pair = json.loads(path.read_text())["pairs"][0]
    contract = pair["clean_base"]
    if changed in {"source", "base"}:
        image = pair["full"]["path"] if changed == "source" else contract["path"]
        Image.new("RGB", (400, 200), "black").save(image)
    elif changed == "svg":
        svg = Path(pair["authoring_svg"])
        svg.write_text(svg.read_text().replace('y="80"', 'y="90"'))
    elif changed == "policy":
        pair["graphic_text_policy"]["items"][0]["bbox"] = [0, 0, 10, 10]
    elif changed == "review":
        contract["visual_review"]["checks"]["graphic_identity"] = "failed"
    else:
        contract["canvas"] = [200, 100]
    assert not validate_authored_layers(contract, full_image=pair["full"]["path"],
        authored_svg=pair["authoring_svg"], graphic_text_policy=pair["graphic_text_policy"], page_number=1)["valid"]


@pytest.mark.parametrize("href", ["https://example.com/base.png", "../../../base.png", "data:image/png;base64,eA=="])
def test_reject_nonlocal_layers_without_manifest_mutation(local_page, href):
    path, pair = local_page
    before = path.read_bytes()
    svg = Path(pair["authoring_svg"])
    svg.write_text(svg.read_text().replace("base.png", href))
    with pytest.raises(ValueError):
        _register(path, pair)
    assert path.read_bytes() == before


def test_reject_wrong_source(local_page):
    path, pair = local_page
    pair["full"]["sha256"] = "wrong"
    with pytest.raises(ValueError, match="source hash"):
        _register(path, pair)


def test_foreground_change_invalidates_review_and_checkpoint_binding(local_page):
    path, pair = local_page
    svg = Path(pair["authoring_svg"])
    photo = svg.parent / "photo.png"
    Image.new("RGB", (20, 20), "blue").save(photo)
    svg.write_text(svg.read_text().replace("</svg>",
        '<image href="photo.png" x="200" y="20" width="20" height="20"/></svg>'))
    _register(path, pair)
    current = json.loads(path.read_text())["pairs"][0]
    before = stage02_adapter._quick_page_binding(current, svg, template_contract={}, style_lock=None)
    Image.new("RGB", (20, 20), "red").save(photo)
    after = stage02_adapter._quick_page_binding(current, svg, template_contract={}, style_lock=None)
    assert before != after
    assert not is_reusable_clean_base(current["clean_base"], full_image=current["full"]["path"],
                                      graphic_text_policy=current["graphic_text_policy"])


def test_external_svg_is_rejected(local_page, tmp_path):
    path, pair = local_page
    with pytest.raises(ValueError, match="inside the active"):
        register_quick_page(path, page_number=1, authored_svg=tmp_path.parent / "outside.svg",
            clean_base=Path(pair["authoring_svg"]).parent / "base.png",
            source_sha256=pair["full"]["sha256"], reviewer="fixture-review",
            checks={key: "passed" for key in REVIEW_CHECKS})


def test_audited_image_import_rejects_changed_bytes(local_page):
    from cyberppt.stage02_production.manifest_stage import _import_audited_full_images
    path, pair = local_page
    manifest = json.loads(path.read_text())
    manifest["production_mode"] = "image-to-editable-svg"
    manifest["pairs"][0]["full"]["prompt_sha256"] = "prompt"
    _write(path, manifest)
    Image.new("RGB", (400, 200), "red").save(pair["full"]["path"])
    with pytest.raises(ValueError, match="audited hash"):
        _import_audited_full_images(manifest=manifest, source_manifest_path=path, selected_pages=(1,))


def test_page_scoped_assets_do_not_collide(tmp_path):
    first, second = _author(tmp_path, 1), _author(tmp_path, 2)
    targets = []
    for pair in [first, second]:
        target = tmp_path / "quick" / "svg_output" / f"p{pair['page_number']}.svg"
        target.parent.mkdir(parents=True, exist_ok=True)
        stage02_adapter._copy_relative_svg_assets(Path(pair["authoring_svg"]), target)
        href = next(node.get("href") for node in ET.parse(target).getroot() if node.tag.endswith("image"))
        targets.append((target.parent / href).resolve())
    assert targets[0] != targets[1]
    assert _hash(targets[0]) != _hash(targets[1])


def test_style_lock_does_not_bypass_cross_column_tspan_check(local_page):
    from scripts.image_to_pptx_runtime.native_text_geometry import analyze_native_text_geometry
    _, pair = local_page
    svg = Path(pair["authoring_svg"])
    svg.write_text(svg.read_text().replace("登记编目</text>",
        '<tspan x="40" y="80">登记</tspan><tspan x="350" y="110">编目</tspan></text>'))
    report = analyze_native_text_geometry(pair["graphic_text_policy"], authored_svg=svg, page_number=1)
    assert not report["valid"]
    assert any("jump" in warning for warning in report["warnings"])


def test_two_page_official_entry_register_preview_resume_and_export(tmp_path, monkeypatch):
    """Real manifest/orchestrator/native export; image provider is a local fixture.

    Set CYBERPPT_TEST_REAL_RENDER=1 to exercise OfficeCLI and final OCR as well.
    """
    from cyberppt.cli import main
    from cyberppt.commands.init_project import init_project
    from cyberppt.stage02_production import orchestrator
    from cyberppt.stage02_production.models import Stage02BuildContext, ImageStageResult
    from scripts.imagegen_pipeline.style_library import write_project_style_lock
    from scripts.image_to_pptx_runtime import clean_base_generator
    from scripts.image_to_pptx_runtime.quick_page_review import QUICK_VISUAL_REVIEW_CHECKS, record_quick_page_review
    from scripts.presentation_qa.text_content import pptx_texts

    original_open = Path.open
    def independent_open(path, *args, **kwargs):
        if "ppt-master" in Path(path).parts:
            raise AssertionError("external upstream repository is unavailable in this test")
        return original_open(path, *args, **kwargs)
    monkeypatch.setattr(Path, "open", independent_open)

    project = tmp_path / "standalone"
    init_project(project)
    script = project / "script.md"
    script.write_text("## 第1页：登记服务\n登记编目\n\n## 第2页：标准服务\n登记编目\n", encoding="utf-8")
    lock = write_project_style_lock(project=project, style_id=9, source_script=script)
    build = project / "workbench" / "stage02" / "production"
    context = Stage02BuildContext(project=project, canonical_script=script, selected_pages=(1, 2),
        pages_raw="1-2", build_id="independent-test", build_dir=build, style_lock=lock,
        source_script_sha256=_hash(script), script_input_sha256=_hash(script),
        visual_spec_sha256="", style_lock_sha256=_hash(lock), production_mode="image-to-editable-svg",
        assembly_mode="editable", source_mode="script_file")
    # Bypass only Stage 01 intake, which is outside the integration under test.
    monkeypatch.setattr(orchestrator, "prepare_preflight", lambda _: context)
    author_pairs = {}
    def fixture_images(ctx, manifest_result, options, deps):
        manifest = manifest_result.manifest
        for pair in manifest["pairs"]:
            page = pair["page_number"]
            if page not in author_pairs:
                author_pairs[page] = _author(build, page)
            authored = author_pairs[page]
            target = Path(pair["full"]["path"])
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(Path(authored["full"]["path"]).read_bytes())
            pair["full"].update(status="Generated", canvas="400x200", sha256=_hash(target),
                text_audit={"valid": True}, generated_prompt_sha256=pair["full"]["prompt_sha256"])
            if not pair.get("authoring_svg"):
                pair["authoring_svg"] = authored["authoring_svg"]
                pair["graphic_text_policy"] = authored["graphic_text_policy"]
        return ImageStageResult(manifest=manifest)
    monkeypatch.setattr(orchestrator, "run_image_stage", fixture_images)
    monkeypatch.setattr(orchestrator, "normalize_audited_manifest_images", lambda *a, **k: None)
    monkeypatch.setattr(orchestrator, "run_full_image_rhythm_stage", lambda *a, **k: {"status": "passed"})
    import cyberppt.commands.final_script_pages as command
    monkeypatch.setattr(command, "require_generated", lambda *a: None)
    forbidden = Mock(side_effect=AssertionError("legacy cleaner must never run"))
    monkeypatch.setattr(clean_base_generator, "prepare_clean_bases", forbidden)
    if not os.environ.get("CYBERPPT_TEST_REAL_RENDER"):
        def render(_pptx, folder, **kwargs):
            folder = Path(folder)
            folder.mkdir(parents=True, exist_ok=True)
            png = folder / "preview.png"
            Image.new("RGB", (1600, 900), "white").save(png)
            return [png]
        monkeypatch.setattr(stage02_adapter, "render_to_png", render)
        monkeypatch.setattr(command, "run_officecli_render_qa", lambda *a: {"passed": True, "report_path": "test-double"})
    args = ["final-script-pages", str(project), "--script", str(script), "--pages", "1-2",
            "--production-build", "--assembly-mode", "editable", "--build-id", "independent-test", "--output-dir", str(build)]
    assert main(args) == 0
    manifest_path = build / "page_image_pairs.json"
    manifest = json.loads(manifest_path.read_text())
    assert manifest["stage02_state"]["state"] == "needs_action"
    for pair in manifest["pairs"]:
        _register(manifest_path, pair)
    assert main(args) == 0
    manifest = json.loads(manifest_path.read_text())
    assert all(p["quick_page_checkpoint"]["status"] == "rendered_pending_visual_review" for p in manifest["pairs"])
    # Synthetic test review exercises the receipt; production reviews require looking at the PNG.
    for pair in manifest["pairs"]:
        record_quick_page_review(manifest_path, page_number=pair["page_number"], status="passed",
            reviewer="fixture-review", checks={name: "passed" for name in QUICK_VISUAL_REVIEW_CHECKS})
    assert main(args) == 0
    manifest = json.loads(manifest_path.read_text())
    assert all(p["quick_page_checkpoint"]["resume"] == "reused" for p in manifest["pairs"])
    outputs = list((build / "editable_svg" / "exports").glob("*.pptx"))
    assert outputs
    assert any(pptx_texts(p).count("登记编目") == 2 for p in outputs)
    forbidden.assert_not_called()
    from cyberppt.stage02_production.preflight import TEMPLATE_LOCK_DIR
    template_lock = json.loads((project / TEMPLATE_LOCK_DIR / "pages_001_002_template_text_lock.json").read_text())
    run_summary = json.loads(next(build.glob("pages_*_final_script_pages_run.json")).read_text())
    assert all(record["resume_command"] == run_summary["resume_command"] for record in template_lock["records"])

    # Even a complete, current disk context cannot replay the adapter outside
    # the production invocation that just returned.
    with pytest.raises(ValueError, match="STAGE02_OFFICIAL_ENTRY_REQUIRED"):
        stage02_adapter.run_stage02_reconstruction(project=project, manifest_path=manifest_path,
            output_dir=build / "editable_svg", requested_pages=[1, 2])

    # A later-page import rejection must preserve the active batch's files.
    from cyberppt.stage02_production.manifest_stage import prepare_manifest
    from cyberppt.stage02_production.models import Stage02RunOptions
    source = json.loads(manifest_path.read_text())
    source["pairs"][1]["full"]["prompt_sha256"] = "changed-prompt"
    bad_source = tmp_path / "bad-source.json"
    _write(bad_source, source)
    protected = [manifest_path, build / "build_context.json",
                 *build.glob("prompts/p*.txt"), *build.glob("final-script*.md"),
                 *(Path(pair["full"]["path"]) for pair in manifest["pairs"])]
    before = {path: path.read_bytes() for path in protected}
    with pytest.raises(ValueError, match="page 2 full-image prompt differs"):
        prepare_manifest(context, Stage02RunOptions(project=project, script=script,
            pages_raw="1-2", production_build=True, reuse_audited_images_from=bad_source))
    assert all(path.read_bytes() == content for path, content in before.items())
