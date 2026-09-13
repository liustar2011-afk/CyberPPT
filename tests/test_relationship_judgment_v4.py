"""Authored semantic cases + executable production-consumption regressions.

Cases are explicit human-readable judgments, not outputs of a classifier.
"""
import hashlib
import json
from dataclasses import replace
from pathlib import Path

import pytest

from cyberppt.stage02_input import prepare_stage02_input, load_stage02_input, input_page_map
from cyberppt.visual_stage.relationship_judgment import (
    SCHEMA, SKILL, digest, load_decisions, require_relationship_judgment,
    validate_decision,
)
from scripts.imagegen_pipeline.style_library import write_project_style_lock
from scripts.imagegen_pipeline.handoff.prompt import compile_page_prompt
from scripts.imagegen_pipeline.page_manifest import build_manifest
from cyberppt.script_quality_contract import parse_script_markdown

# Each expectation follows the entire short source. These named counter-readings
# exercise semantics which keyword/topology mapping would lose.
CASES = [
    tuple(case[key] for key in ("id", "source", "status", "statements", "constraints", "uncertainties", "analysis"))
    for case in json.loads((Path(__file__).parent / "fixtures/relationship_judgment_cases.json").read_text())
]


def decision_for(page, case):
    _, source, status, statements, constraints, uncertainties, analysis = case
    return dict(page_id=page["page_id"], input_sha256=digest(page), status=status,
                analysis=analysis, source_check="核对本案例完整原文；未使用外部事实。",
                relations=[dict(statement=s, evidence=[dict(field="content_text", quote=source)]) for s in statements],
                constraints=list(constraints), uncertainties=list(uncertainties))


def write_decisions(project, decisions):
    path = project / "visual/visual-design-decisions.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(dict(schema=SCHEMA, executor="main_agent",
        skill_sha256=hashlib.sha256(SKILL.read_bytes()).hexdigest(), pages=decisions), ensure_ascii=False))
    return path


@pytest.mark.parametrize("case", CASES, ids=[c[0] for c in CASES])
def test_semantics_reach_real_prompt_without_heuristic(case, tmp_path, monkeypatch):
    source = tmp_path / "source.md"
    source.write_text("## P01 测试\n\n" + case[1])
    prepare_stage02_input(tmp_path, script=source, source_mode="external_script")
    page = input_page_map(load_stage02_input(tmp_path, required=True))[1]
    decision = decision_for(page, case)
    write_decisions(tmp_path, [decision])
    validate_decision(decision, page)
    lock = write_project_style_lock(project=tmp_path, style_id=9, source_script=source)
    import scripts.imagegen_pipeline.handoff.prompt as compiler
    def forbidden(*args, **kwargs):
        raise AssertionError("legacy heuristic executed")
    monkeypatch.setattr(compiler, "derive_page_semantics", forbidden)
    monkeypatch.setattr(compiler, "resolve_presentation_decision", forbidden)
    monkeypatch.setattr(compiler, "resolve_composition", forbidden)
    manifest, path, compiled, _ = build_manifest(script=source, pages_raw="1", output_dir=tmp_path / "output",
        project_path=tmp_path, style_lock=lock, persist=True)
    prompt = manifest["pairs"][0]["full"]["prompt"]
    for statement in [r["statement"] for r in decision["relations"]] + decision["constraints"] + decision["uncertainties"]:
        assert statement in prompt
    assert "【核心判断" not in prompt
    assert decision["analysis"] not in prompt
    assert decision["input_sha256"] not in prompt
    assert "具体构图、媒介、空间安排" in prompt
    assert compiled.read_text().endswith(prompt.strip() + "\n")
    assert path.is_file()


def test_missing_stale_evidence_and_empty_decision(tmp_path):
    page = dict(page_id="p01", content_text=CASES[0][1])
    with pytest.raises(ValueError, match="RELATIONSHIP_JUDGMENT_REQUIRED"):
        require_relationship_judgment(tmp_path, {1: page})
    assert (tmp_path / "visual/skill-invocation.md").is_file()
    decision = decision_for(page, CASES[0])
    write_decisions(tmp_path, [decision])
    assert load_decisions(tmp_path, {1: page})[1] == decision
    with pytest.raises(ValueError, match="stale"):
        load_decisions(tmp_path, {1: dict(page, content_text="changed")})
    decision["relations"][0]["evidence"][0]["quote"] = "invented evidence"
    with pytest.raises(ValueError, match="absent"):
        validate_decision(decision, page)
    with pytest.raises(ValueError, match="object"):
        validate_decision(None, page)


def test_fidelity_and_relationship_change_prompt_hash(tmp_path):
    page = parse_script_markdown("## P01 测试\n\n" + CASES[0][1]).pages[0]
    page = replace(page, onscreen_text=CASES[0][1], fidelity_text=(
        {"text": "甲组", "visibility": "required"}, {"text": "乙组", "visibility": "if_rendered"}))
    source = tmp_path / "source.md"
    source.write_text("## P01 测试\n\n" + CASES[0][1])
    lock = write_project_style_lock(project=tmp_path, style_id=9, source_script=source)
    decision = decision_for(dict(page_id="p01", content_text=CASES[0][1]), CASES[0])
    first = compile_page_prompt(page, lock, relationship_decision=decision).prompt
    decision["constraints"].append("两组保持同等职责地位。")
    second = compile_page_prompt(page, lock, relationship_decision=decision).prompt
    assert first != second
    assert "甲组" in first and "乙组" in first and "保真文字合同" in first
    assert "允许提炼、改写、重组" in first


def test_official_cli_checkpoint_resume_and_fidelity(tmp_path):
    import subprocess
    import sys
    source = tmp_path / "internal.md"
    source.write_text("""## P01 建设安排
- 页面类型：内容页

### 完整文字稿
甲组与乙组分别开展建设。到2028年完成试点；推广须经评估通过。

### 保真文字
- [required] 2028年
- [if_rendered] 甲组
""")
    project = tmp_path / "project"
    output = tmp_path / "build"
    lock = write_project_style_lock(project=project, style_id=9, source_script=source)
    command = [sys.executable, "-m", "cyberppt", "final-script-pages", str(project),
               "--script", str(source), "--pages", "1", "--production-build",
               "--generate-images", "--dry-run-images", "--assembly-mode", "image",
               "--build-id", "relationship-integration", "--output-dir", str(output), "--style-lock", str(lock)]
    first = subprocess.run(command, capture_output=True, text=True)
    assert first.returncode != 0 and "RELATIONSHIP_JUDGMENT_REQUIRED" in first.stderr
    assert not (output / "page_image_pairs.json").exists()
    page = input_page_map(load_stage02_input(project, required=True))[1]
    decision = dict(page_id="p01", input_sha256=digest(page), status="supported",
        analysis="两主体分别建设；完成试点是有时间目标的状态，推广受评估条件限制。",
        source_check="核对完整文字稿中的主体、时间与触发条件。",
        relations=[dict(statement="甲组与乙组分别建设；试点到2028年完成，推广须评估通过。",
                        evidence=[dict(field="full_prose", quote=page["full_prose"])])],
        constraints=["不把分别建设改成主从关系，不把推广写成已经完成。"], uncertainties=[])
    write_decisions(project, [decision])
    # User review uses the existing compile-only route, before any send/build.
    preview_command = [arg for arg in command if arg not in {
        "--production-build", "--generate-images", "--dry-run-images"
    }]
    preview = subprocess.run(preview_command, capture_output=True, text=True)
    assert preview.returncode == 0, preview.stderr
    assert (output / "prompts/p01.txt").is_file()
    assert not list(output.rglob("*.png")) and not list(output.rglob("*.pptx"))
    second = subprocess.run(command, capture_output=True, text=True)
    assert second.returncode == 2 and "requires generated full image" in second.stderr, second.stderr
    manifest_path = output / "page_image_pairs.json"
    manifest = json.loads(manifest_path.read_text())
    prompt = manifest["pairs"][0]["full"]["prompt"]
    assert decision["relations"][0]["statement"] in prompt
    assert "保真文字合同" in prompt and "2028年" in prompt and "甲组" in prompt
    assert manifest["input_identity"]["visual_spec_sha256"]
    assert (output / "prompts/p01.txt").read_text() == prompt
    third = subprocess.run(command, capture_output=True, text=True)
    assert third.returncode == 2 and "requires generated full image" in third.stderr, third.stderr
    repeated = json.loads(manifest_path.read_text())
    assert manifest["input_identity"] == repeated["input_identity"]
    assert not list(output.glob("*.png")) and not list(output.glob("*.pptx"))
    # Stale judgment never publishes a replacement manifest/prompt.
    before = manifest_path.read_bytes()
    source.write_text(source.read_text().replace("2028", "2029"))
    stale = subprocess.run(command, capture_output=True, text=True)
    assert stale.returncode != 0 and "RELATIONSHIP_JUDGMENT_REQUIRED" in stale.stderr
    assert manifest_path.read_bytes() == before


def test_relation_change_prevents_same_run_layer_reuse(tmp_path):
    from cyberppt.stage02_production.manifest_stage import _reuse_prior_artifacts
    from cyberppt.stage02_production.page_reuse import _same_prompt_identity
    prior_pair = dict(page_number=1, relationship_judgment_sha256="old",
                      graphic_text_policy={"status": "complete", "empty_container_check": "passed"},
                      full={"prompt_sha256": "same"})
    current_pair = dict(page_number=1, relationship_judgment_sha256="new", full={"prompt_sha256": "same"})
    common = dict(source_script_sha256="same", production_mode="image-to-editable-svg", run_id="same")
    _reuse_prior_artifacts(manifest=dict(common, pairs=[current_pair]),
                          prior_manifest=dict(common, pairs=[prior_pair]), production_mode="image-to-editable-svg")
    assert "graphic_text_policy" not in current_pair
    assert not _same_prompt_identity(current_pair=current_pair, prior_pair=prior_pair, production_mode="image-to-editable-svg")
