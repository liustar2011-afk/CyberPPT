"""Current field delivery, legacy copy selection, and versioned reuse identity."""
from copy import deepcopy
import hashlib
import json

import pytest

from script_engine.render import render_stage02_markdown
from cyberppt.script_quality.parsing import parse_script_markdown
from cyberppt.stage02_input import (
    build_stage02_input, canonical_content_text, input_page_map, load_stage02_input,
    prepare_stage02_input, production_page_input, stage02_input_semantic_sha256,
    stage02_production_input_sha256,
)
from cyberppt.visual_stage.relationship_judgment import SCHEMA, SKILL, digest, validate_decision
from scripts.imagegen_pipeline.page_manifest import build_manifest
from scripts.imagegen_pipeline.style_library import write_project_style_lock


SOURCE = "试点平台目前向企业提供目录查询；数据交付尚未开放，后续开放以授权完成为条件。"


def manuscript(version="1.2", mode="self_read"):
    slide = dict(id="P01", page_type="content", title="试点服务范围", mission="说明当前服务与开放条件",
                 full_copy=SOURCE, fidelity_text=[], source_refs=["F1"])
    if version != "1.2":
        slide["onscreen"] = [dict(heading="目录查询", items=["目前向企业开放目录查询。"])]
    return dict(version=version, deck=dict(title="试点", delivery_mode=mode), slides=[slide])


def compile_manuscript(tmp_path, text, *, source_mode="script_file"):
    source = tmp_path / "script.md"
    source.write_text(text, encoding="utf-8")
    project = tmp_path / "project"
    prepare_stage02_input(project, script=source, source_mode=source_mode)
    page = input_page_map(load_stage02_input(project, required=True))[1]
    decision = dict(page_id="p01", input_sha256=digest(page), status="supported",
                    analysis="保留当前开放状态与后续条件。", source_check="核对当前完整讲稿。",
                    relations=[dict(statement="试点平台目前向企业提供目录查询。",
                                    evidence=[dict(field="full_prose", quote=SOURCE)])],
                    constraints=["数据交付尚未开放；后续开放受授权条件限制。"], uncertainties=[])
    path = project / "visual/visual-design-decisions.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(dict(schema=SCHEMA, executor="main_agent",
        skill_sha256=hashlib.sha256(SKILL.read_bytes()).hexdigest(), pages=[decision]), ensure_ascii=False))
    lock = write_project_style_lock(project=project, style_id=9, source_script=source)
    manifest, _, compiled, _ = build_manifest(script=source, pages_raw="1", output_dir=tmp_path / "build",
        project_path=project, style_lock=lock, persist=True)
    prompt = manifest["pairs"][0]["full"]["prompt"]
    assert prompt.strip() in compiled.read_text()
    return page, prompt, decision


@pytest.mark.parametrize("mode,label", [("self_read", "独立阅读"), ("presented", "演讲辅助")])
def test_mode_roundtrip_reaches_actual_compiled_prompt(tmp_path, mode, label):
    markdown = render_stage02_markdown(manuscript(mode=mode))
    parsed = parse_script_markdown(markdown).pages[0]
    assert parsed.delivery_mode == mode
    assert parsed.full_prose == SOURCE
    page, prompt, decision = compile_manuscript(tmp_path, markdown)
    assert page["delivery_mode"] == mode
    assert page["content_text"] == SOURCE
    assert label in prompt
    assert "交流方式（不上屏）" in prompt
    assert "说明当前服务与开放条件" in prompt
    assert decision["constraints"][0] in prompt
    assert decision["analysis"] not in prompt
    assert "input_sha256" not in prompt
    assert "core_message" not in prompt


@pytest.mark.parametrize("version", ["1.0", "1.1"])
def test_legacy_copy_is_distinct_from_complete_background(tmp_path, version):
    markdown = render_stage02_markdown(manuscript(version))
    page, prompt, _ = compile_manuscript(tmp_path, markdown)
    assert page["content_text"] == page["onscreen_text"]
    assert page["content_text"] != SOURCE
    assert page["full_prose"] == SOURCE
    content_block = prompt.split("【页面内容素材｜允许提炼、改写、重组】\n", 1)[1].split("【完整语义背景", 1)[0]
    assert "目前向企业开放目录查询。" in content_block
    assert SOURCE not in content_block
    assert "【完整语义背景｜不上屏】\n" + SOURCE in prompt


@pytest.mark.parametrize("structured", [True, False])
def test_external_content_and_mode_reach_prompt(tmp_path, structured):
    text = "> 交流方式：presented\n\n## P01 试点服务范围\n\n"
    text += ("### 内容\n\n" if structured else "") + SOURCE
    page, prompt, _ = compile_manuscript(tmp_path, text, source_mode="external_script")
    assert page["content_text"] == SOURCE
    assert page["delivery_mode"] == "presented"
    assert "演讲辅助" in prompt


def test_metadata_defaults_validation_and_body_quote_scope():
    page = parse_script_markdown("## P01 内容\n### 完整文字稿\n原句。\n> 交流方式：presented").pages[0]
    assert page.delivery_mode == "self_read"
    assert "交流方式：presented" in page.full_prose
    with pytest.raises(ValueError, match="delivery_mode"):
        parse_script_markdown("> 交流方式：unknown\n## P01 测试\n### 完整文字稿\n正文。")
    with pytest.raises(ValueError, match="conflicting"):
        parse_script_markdown("> 交流方式：self_read\n> 交流方式：presented\n## P01 测试\n正文。")


def intake(tmp_path):
    source = tmp_path / "script.md"
    source.write_text(render_stage02_markdown(manuscript()))
    return build_stage02_input(tmp_path / "project", script=source)


def test_diagnostics_do_not_change_new_production_identity(tmp_path):
    payload = intake(tmp_path)
    changed = deepcopy(payload)
    page = changed["pages"][0]
    page["render_topology"] = {"primary_topology": "different_legacy_guess"}
    page["semantic_verification"] = {"diagnostic": "changed"}
    page["onscreen_expression"] = {"form": "old-layout"}
    page["stage02_visual_input"]["full_prose"] = "ignored repeated alias"
    page["editable_body_text"] = "ignored repeated alias"
    assert stage02_input_semantic_sha256(payload) != stage02_input_semantic_sha256(changed)
    assert stage02_production_input_sha256(payload) == stage02_production_input_sha256(changed)
    assert digest(payload["pages"][0]) == digest(page)
    assert production_page_input(payload["pages"][0]) == production_page_input(page)


@pytest.mark.parametrize("field,value", [
    ("content_text", "新内容"), ("full_prose", "新增背景与条件"),
    ("delivery_mode", "presented"), ("source_mode", "external_script"),
    ("title", "不同标题"), ("page_mission", "不同使命"),
    ("fidelity_text", [{"text": "试点", "visibility": "required"}]),
])
def test_semantic_changes_invalidate_new_production_identity(tmp_path, field, value):
    payload = intake(tmp_path)
    changed = deepcopy(payload)
    changed["pages"][0][field] = value
    assert stage02_production_input_sha256(payload) != stage02_production_input_sha256(changed)
    assert digest(payload["pages"][0]) != digest(changed["pages"][0])


def test_historical_identity_and_copy_adapter_are_preserved():
    page = dict(page_id="p01", content_text="旧缓存误存完整稿", full_prose="完整背景",
                onscreen_text="已编写短文案", render_topology={"old": True})
    assert canonical_content_text(page) == "已编写短文案"
    assert production_page_input(page) == page
    assert digest(page) == hashlib.sha256(json.dumps(page, ensure_ascii=False, sort_keys=True).encode()).hexdigest()
    payload = dict(pages=[page], page_order=["p01"])
    assert stage02_production_input_sha256(payload) == stage02_input_semantic_sha256(payload)
    with pytest.raises(ValueError, match="content_contract_version"):
        production_page_input(dict(page, content_contract_version=99))


def test_new_evidence_alias_cannot_use_ignored_stale_copy(tmp_path):
    page = intake(tmp_path)["pages"][0]
    page["onscreen_text"] = "仅存在于过期别名"
    decision = dict(input_sha256=digest(page), status="supported", analysis="检查", source_check="讲稿",
                    relations=[dict(statement="目录查询服务", evidence=[dict(field="onscreen_text", quote="仅存在于过期别名")])],
                    constraints=[], uncertainties=[])
    with pytest.raises(ValueError, match="absent"):
        validate_decision(decision, page)


@pytest.mark.parametrize("field,value", [
    ("content_contract_version", 99), ("delivery_mode", "unknown"),
    ("content_text", None), ("source_mode", "external_script"),
])
def test_intake_audit_rejects_invalid_new_fields_even_with_fresh_checksum(tmp_path, field, value):
    from cyberppt.stage02_input import audit_stage02_input
    payload = intake(tmp_path)
    payload["pages"][0][field] = value
    payload["semantic_sha256"] = stage02_input_semantic_sha256(payload)
    report = audit_stage02_input(tmp_path / "project", payload)
    assert report["status"] == "failed"
    assert "INPUT_CONTENT_CONTRACT_INVALID" in {issue["code"] for issue in report["blocking_issues"]}


def test_production_preflight_and_page_reuse_share_the_projected_identity(tmp_path):
    from cyberppt.stage02_input import input_path
    from cyberppt.stage02_production.models import Stage02RunOptions
    from cyberppt.stage02_production.preflight import prepare_preflight
    from cyberppt.stage02_production.page_reuse import attach_page_input_sha256, PAGE_INPUT_SHA256_FIELD
    compile_manuscript(tmp_path, render_stage02_markdown(manuscript()))
    project = tmp_path / "project"
    # Use the actual path returned by the style writer, independent of naming.
    lock = write_project_style_lock(project=project, style_id=9, source_script=tmp_path / "script.md")
    options = Stage02RunOptions(project=project, script=tmp_path / "script.md", pages_raw="1", style_lock=lock)
    before = prepare_preflight(options)
    manifest_before = {"pairs": [{"page_number": 1}]}
    assert attach_page_input_sha256(manifest=manifest_before, project=project)
    payload = load_stage02_input(project, required=True)
    payload["pages"][0]["render_topology"] = {"changed_diagnostic": True}
    payload["pages"][0]["stage02_visual_input"]["content_text"] = "unused duplicate"
    payload["semantic_sha256"] = stage02_input_semantic_sha256(payload)
    input_path(project).write_text(json.dumps(payload, ensure_ascii=False))
    after = prepare_preflight(options)
    manifest_after = {"pairs": [{"page_number": 1}]}
    assert attach_page_input_sha256(manifest=manifest_after, project=project)
    assert before.script_input_sha256 == after.script_input_sha256
    assert before.visual_spec_sha256 == after.visual_spec_sha256
    assert manifest_before["pairs"][0][PAGE_INPUT_SHA256_FIELD] == manifest_after["pairs"][0][PAGE_INPUT_SHA256_FIELD]
    payload["pages"][0]["delivery_mode"] = "presented"
    payload["semantic_sha256"] = stage02_input_semantic_sha256(payload)
    input_path(project).write_text(json.dumps(payload, ensure_ascii=False))
    with pytest.raises(ValueError, match="RELATIONSHIP_JUDGMENT_REQUIRED"):
        prepare_preflight(options)
    manifest_changed = {"pairs": [{"page_number": 1}]}
    assert attach_page_input_sha256(manifest=manifest_changed, project=project)
    assert manifest_before["pairs"][0][PAGE_INPUT_SHA256_FIELD] != manifest_changed["pairs"][0][PAGE_INPUT_SHA256_FIELD]
