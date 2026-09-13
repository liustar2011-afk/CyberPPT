"""External page fields reach canonical production without contaminating copy."""
from copy import deepcopy
import hashlib
import json
import subprocess
import sys

import pytest

from cyberppt.stage02_script_adapter import parse_stage02_script
from cyberppt.stage02_input import (
    build_stage02_input, prepare_stage02_input, load_stage02_input,
    input_path, production_page_input, stage02_input_semantic_sha256,
)
from cyberppt.visual_stage.relationship_judgment import SCHEMA, SKILL, digest
from scripts.imagegen_pipeline.deliverable_prompt import parse_page_blocks


SAMPLE = """# 服务介绍 - Deck Plan
> 交流方式：presented

## I. Communication Contract
| Item | Value |
| --- | --- |
| Target Audience | 合作伙伴 |
| Reading Mode | balanced |
| Delivery Context | 现场讲解，兼顾会后阅读 |
| Page Count | 2 |

## IX. Content Outline
### Part 1: 服务范围
#### Slide 01 - 开场
- **Title**: 目录查询
- **Core message**: 企业可以查询目录。
- **Audience move**: 了解当前服务范围。
- **Content**: 平台目前向企业提供目录查询。
  - 数据交付：尚未开放。

  后续开放以授权完成为条件。
- **Evidence**: 来源第三段。
- **Relationships**: 授权完成是后续开放的条件。
- **Composition**: 用边界区分当前与后续。
- **Rhythm**: anchor
- **Cover impact**: 记住开放条件。
- **Custom note**: 特殊合作背景。
- **Fidelity_text**:
  - [required] 目录查询

### Part 2: 结束
#### Slide 02 - 交流
- **Title**: 欢迎交流
- **Content**: 欢迎会后交流。
- **Closing impact**: 以会后交流收束。

## X. Appendix
附件说明不进入末页。
"""


def source_file(tmp_path, text=SAMPLE):
    path = tmp_path / "deck_plan.md"
    path.write_text(text, encoding="utf-8")
    return path


def test_pages_fields_multiline_and_boundaries(tmp_path):
    doc = parse_stage02_script(SAMPLE, source_mode="external_script")
    assert len(doc.pages) == 2
    a, b = doc.pages
    assert a.title == "目录查询" and a.part == "Part 1: 服务范围"
    assert "数据交付：尚未开放" in a.content_text and "后续开放以授权" in a.content_text
    assert "来源第三段" not in a.content_text and "Composition" not in a.content_text
    assert a.evidence == "来源第三段。" and not a.source_refs
    assert a.additional_fields == {"custom note": "特殊合作背景。"}
    assert a.fidelity_text == ({"text": "目录查询", "visibility": "required"},)
    assert a.cover_impact and b.closing_impact
    assert b.content_text == "欢迎会后交流。"
    assert a.delivery_mode == "presented" and a.delivery_mode_explicit
    assert set(parse_page_blocks(source_file(tmp_path))) == {1, 2}
    from scripts.image_to_pptx_runtime.stage02_adapter import _page_title, _speaker_notes_by_page
    from cyberppt.stage02_production.delivery_stage import _final_visible_text_contract
    assert _page_title(source_file(tmp_path), 2) == "欢迎交流"
    assert _speaker_notes_by_page(source_file(tmp_path), [1, 2]) == {}
    assert "欢迎交流" in _final_visible_text_contract({}, source_file(tmp_path), 2)[0]
    with pytest.raises(ValueError, match="external-script"):
        parse_stage02_script(SAMPLE, source_mode="script_file")


@pytest.mark.parametrize("old,new,code", [
    ("Slide 02", "Slide 01", "PAGE_SEQUENCE"),
    ("Slide 02", "Slide 03", "PAGE_SEQUENCE"),
    ("Slide 02", "Slide bad", "INVALID_SLIDE"),
    ("| Page Count | 2 |", "| Page Count | 3 |", "PAGE_COUNT"),
    ("- **Content**: 欢迎会后交流。", "- **Content**: ", "MISSING_FIELD"),
    ("- **Title**: 欢迎交流", "- **Title**: 欢迎交流\n- **Title**: 重复", "DUPLICATE_FIELD"),
    ("交流方式：presented", "交流方式：unknown", "delivery_mode"),
    ("| Reading Mode | balanced |", "| Reading Mode | self_read |", "conflicting"),
])
def test_invalid_documents_fail_explicitly(old, new, code):
    with pytest.raises(ValueError, match=code):
        parse_stage02_script(SAMPLE.replace(old, new), source_mode="external_script")


def test_context_changes_invalidate_identity_and_old_cache(tmp_path):
    source = source_file(tmp_path)
    project = tmp_path / "project"
    prepare_stage02_input(project, script=source, source_mode="external_script")
    payload = load_stage02_input(project, required=True)
    page = payload["pages"][0]
    for key in ("audience_move", "evidence", "relationships", "composition", "rhythm", "cover_impact", "part"):
        changed = dict(page, **{key: "改变上下文"})
        assert digest(changed) != digest(page)
        assert key in production_page_input(page)
    changed = deepcopy(page)
    changed["communication_contract"]["Target Audience"] = "内部团队"
    assert digest(changed) != digest(page)
    payload["pages"] = [dict(page)]
    payload["pages"][0].pop("external_format")
    payload["page_order"] = ["p01"]
    payload["semantic_sha256"] = stage02_input_semantic_sha256(payload)
    input_path(project).write_text(json.dumps(payload))
    result = prepare_stage02_input(project, script=source, source_mode="external_script")
    assert not result["reused"]
    assert len(load_stage02_input(project, required=True)["pages"]) == 2


def test_formal_cli_compile_context_and_stale_decision(tmp_path):
    source = source_file(tmp_path)
    project, output = tmp_path / "project", tmp_path / "build"
    command = [sys.executable, "-m", "cyberppt", "final-script-pages", str(project),
               "--script", str(source), "--external-script", "--pages", "1-2",
               "--output-dir", str(output), "--build-id", "external-test"]
    first = subprocess.run(command, capture_output=True, text=True)
    assert first.returncode != 0 and "RELATIONSHIP_JUDGMENT_REQUIRED" in first.stderr
    payload = load_stage02_input(project, required=True)
    decisions = [dict(page_id=p["page_id"], input_sha256=digest(p), status="none",
        analysis="诊断案例按独立服务说明与交流邀请呈现。", source_check="核对测试正文与附加字段。",
        relations=[], constraints=["保留数据交付尚未开放及授权条件。"] if p["page_number"] == 1 else [],
        uncertainties=[]) for p in payload["pages"]]
    path = project / "visual/visual-design-decisions.json"
    path.write_text(json.dumps(dict(schema=SCHEMA, executor="main_agent",
        skill_sha256=hashlib.sha256(SKILL.read_bytes()).hexdigest(), pages=decisions), ensure_ascii=False))
    second = subprocess.run(command, capture_output=True, text=True)
    assert second.returncode == 0, second.stderr
    manifest = json.loads((output / "page_image_pairs.json").read_text())
    assert len(manifest["pairs"]) == 2
    prompt = (output / "prompts/p01.txt").read_text()
    for literal in ("来源第三段", "用边界区分", "了解当前服务范围", "特殊合作背景", "合作伙伴", "记住开放条件"):
        assert literal in prompt
    assert "演讲辅助" in prompt and "保真文字合同" in prompt
    assert "附件说明" not in (output / "prompts/p02.txt").read_text()
    assert not list(output.rglob("*.png")) and not list(output.rglob("*.pptx"))
    before = (output / "page_image_pairs.json").read_bytes()
    source.write_text(SAMPLE.replace("用边界区分当前与后续", "清晰呈现授权边界"))
    stale = subprocess.run(command, capture_output=True, text=True)
    assert stale.returncode != 0 and "RELATIONSHIP_JUDGMENT_REQUIRED" in stale.stderr
    assert (output / "page_image_pairs.json").read_bytes() == before


def test_balanced_is_preserved_but_not_silently_compiled(tmp_path):
    source = source_file(tmp_path, SAMPLE.replace("> 交流方式：presented\n", ""))
    page = build_stage02_input(tmp_path / "project", script=source, source_mode="external_script")["pages"][0]
    assert page["communication_contract"]["Reading Mode"] == "balanced"
    assert page["delivery_mode_explicit"] is False
    from cyberppt.stage02_production.preflight import prepare_preflight
    from cyberppt.stage02_production.models import Stage02RunOptions
    with pytest.raises(ValueError, match="DELIVERY_MODE_REQUIRED"):
        prepare_preflight(Stage02RunOptions(project=tmp_path / "project", script=source,
                                           pages_raw="1-2", external_script=True))


@pytest.mark.parametrize("declared,parsed,role", [
    ("content", "content", "content"),
    ("template: cover", "cover", "cover"),
    ("template: agenda", "contents", "agenda"),
    ("template: transition", "chapter", "section"),
    ("template: back-cover", "closing", "ending"),
])
def test_page_type_maps_to_existing_production_roles(tmp_path, declared, parsed, role):
    text = SAMPLE.replace("- **Title**: 目录查询", f"- **Page type**: {declared}\n- **Title**: 目录查询")
    doc = parse_stage02_script(text, source_mode="external_script")
    assert doc.pages[0].page_type == parsed
    page = build_stage02_input(tmp_path / "project", script=source_file(tmp_path, text), source_mode="external_script")["pages"][0]
    assert page["render_role"] == role
    assert "page type" not in page["additional_fields"]
    assert "后续开放以授权" in page["content_text"]
    changed = dict(page, render_role="different")
    assert digest(page) != digest(changed)


@pytest.mark.parametrize("value", ["", "template: unknown", "template"])
def test_unknown_declared_type_fails(value):
    with pytest.raises(ValueError, match="PAGE_TYPE"):
        parse_stage02_script(SAMPLE.replace("- **Title**: 目录查询", f"- **Page type**: {value}\n- **Title**: 目录查询"), source_mode="external_script")


def test_template_types_reach_formal_manifest(tmp_path):
    text = SAMPLE.replace("| Page Count | 2 |", "| Page Count | 3 |")
    text = text.replace("- **Title**: 目录查询", "- **Page type**: template: cover\n- **Title**: 目录查询")
    text = text.replace("## X. Appendix", "#### Slide 03 - 结束\n- **Page type**: template: back-cover\n- **Title**: 再见\n- **Content**: 谢谢大家。\n\n## X. Appendix")
    source = source_file(tmp_path, text)
    project, output = tmp_path / "project", tmp_path / "build"
    prepare_stage02_input(project, script=source, source_mode="external_script")
    payload = load_stage02_input(project, required=True)
    assert [p["render_role"] for p in payload["pages"]] == ["cover", "content", "ending"]
    page = payload["pages"][1]
    decision = dict(page_id=page["page_id"], input_sha256=digest(page), status="none",
        analysis="独立交流邀请。", source_check="核对正文。", relations=[], constraints=[], uncertainties=[])
    path = project / "visual/visual-design-decisions.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(dict(schema=SCHEMA, executor="main_agent",
        skill_sha256=hashlib.sha256(SKILL.read_bytes()).hexdigest(), pages=[decision]), ensure_ascii=False))
    result = subprocess.run([sys.executable, "-m", "cyberppt", "final-script-pages", str(project),
        "--script", str(source), "--external-script", "--pages", "1-3",
        "--output-dir", str(output), "--build-id", "typed-test"], capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
    manifest = json.loads((output / "page_image_pairs.json").read_text())
    assert manifest["content_page_numbers"] == [2]
    assert [pair["page_number"] for pair in manifest["pairs"]] == [2]
