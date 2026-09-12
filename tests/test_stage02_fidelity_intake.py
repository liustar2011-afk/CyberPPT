from __future__ import annotations

from dataclasses import replace
import json
from pathlib import Path

from cyberppt.stage02_input import (
    audit_stage02_input,
    build_stage02_input,
    input_path,
    prepare_stage02_input,
)
from cyberppt.stage02_production.identity import input_fingerprint
from cyberppt.stage02_production.models import Stage02BuildContext, Stage02RunOptions


def _write(path: Path, text: str) -> Path:
    path.write_text(text.strip() + "\n", encoding="utf-8")
    return path


def _internal_v12(path: Path, *, fidelity: str = "2028年") -> Path:
    return _write(
        path,
        f"""
## P01 内部稿

- 页面类型：内容页
- 页面标题：内部稿
- 页面使命：说明建设目标。
- 核心结论：形成稳定的数据服务能力。

### 完整文字稿

到2028年形成稳定的数据服务能力，并持续服务真实业务场景。

### 保真文字

- [required] {fidelity}
""",
    )


def _context(tmp_path: Path, *, script_input_sha256: str) -> Stage02BuildContext:
    script = tmp_path / "canonical.md"
    style = tmp_path / "style.json"
    script.write_text("script", encoding="utf-8")
    style.write_text("{}", encoding="utf-8")
    return Stage02BuildContext(
        project=tmp_path,
        canonical_script=script,
        selected_pages=(1,),
        pages_raw="1",
        build_id="run",
        build_dir=tmp_path / "run",
        style_lock=style,
        source_script_sha256="source",
        script_input_sha256=script_input_sha256,
        visual_spec_sha256="",
        style_lock_sha256="style",
        production_mode="image-to-editable-svg",
        assembly_mode="editable",
        source_mode="script_file",
    )


def test_internal_v12_projects_full_copy_to_stage02_runtime_text(tmp_path: Path) -> None:
    script = _internal_v12(tmp_path / "internal.md")

    payload = build_stage02_input(tmp_path / "project", script=script)
    page = payload["pages"][0]

    assert payload["source_mode"] == "script_file"
    assert page["content_text"] == page["full_prose"]
    assert page["onscreen_text"] == page["full_prose"]
    assert page["onscreen_source"] == "full_copy_stage02_source"
    assert page["fidelity_text"] == [{"text": "2028年", "visibility": "required"}]
    assert page["stage02_visual_input"]["fidelity_text"] == page["fidelity_text"]
    assert payload["semantic_sha256"]
    assert audit_stage02_input(tmp_path / "project", payload)["status"] == "passed"


def test_external_structured_content_alias_is_stage02_only(tmp_path: Path) -> None:
    script = _write(
        tmp_path / "external.md",
        """
## P01 外部稿

### 内容

外部正文明确到2030年完成阶段目标。

### 保真文字

- [required] 2030年
""",
    )

    payload = build_stage02_input(
        tmp_path / "project",
        script=script,
        source_mode="external_script",
    )
    page = payload["pages"][0]

    assert payload["source_mode"] == "external_script"
    assert page["full_prose"] == "外部正文明确到2030年完成阶段目标。"
    assert page["onscreen_text"] == page["full_prose"]
    assert page["onscreen_source"] == "external_content_stage02_source"
    assert page["fidelity_text"] == [{"text": "2030年", "visibility": "required"}]


def test_external_numbered_free_markdown_uses_page_body_as_content(tmp_path: Path) -> None:
    script = _write(
        tmp_path / "free.md",
        """
## P01 第一页

第一段自由正文。
第二段继续说明业务条件。

## P02 第二页

第二页正文不要求 CyberPPT 字段标签。
""",
    )

    payload = build_stage02_input(
        tmp_path / "project",
        script=script,
        source_mode="external_script",
    )

    assert [page["title"] for page in payload["pages"]] == ["第一页", "第二页"]
    assert payload["pages"][0]["full_prose"] == "第一段自由正文。\n第二段继续说明业务条件。"
    assert payload["pages"][1]["full_prose"] == "第二页正文不要求 CyberPPT 字段标签。"
    assert all(page["fidelity_text"] == [] for page in payload["pages"])
    assert all(
        page["onscreen_source"] == "external_content_stage02_source"
        for page in payload["pages"]
    )


def test_prepare_rebuilds_same_source_when_source_mode_changes(tmp_path: Path) -> None:
    script = _internal_v12(tmp_path / "same.md")
    project = tmp_path / "project"

    first = prepare_stage02_input(project, script=script, source_mode="script_file")
    second = prepare_stage02_input(project, script=script, source_mode="external_script")
    payload = json.loads(input_path(project).read_text(encoding="utf-8"))

    assert first["reused"] is False
    assert second["reused"] is False
    assert payload["source_mode"] == "external_script"


def test_semantic_hash_detects_fidelity_mutation(tmp_path: Path) -> None:
    script = _internal_v12(tmp_path / "internal.md")
    project = tmp_path / "project"
    payload = build_stage02_input(project, script=script)

    payload["pages"][0]["fidelity_text"][0]["text"] = "2030年"
    report = audit_stage02_input(project, payload)

    assert report["status"] == "failed"
    assert "INPUT_SEMANTIC_HASH_STALE" in {
        issue["code"] for issue in report["blocking_issues"]
    }


def test_fidelity_change_flows_into_production_input_fingerprint(tmp_path: Path) -> None:
    script_a = _internal_v12(tmp_path / "a.md", fidelity="2028年")
    script_b = _write(
        tmp_path / "b.md",
        """
## P01 内部稿

- 页面类型：内容页
- 页面标题：内部稿
- 页面使命：说明建设目标。
- 核心结论：形成稳定的数据服务能力。

### 完整文字稿

到2028年形成稳定的数据服务能力，并持续服务真实业务场景。

### 保真文字

- [required] 形成稳定的数据服务能力
""",
    )
    payload_a = build_stage02_input(tmp_path / "project-a", script=script_a)
    payload_b = build_stage02_input(tmp_path / "project-b", script=script_b)
    options = Stage02RunOptions(project=tmp_path, script=script_a, pages_raw="1")

    context_a = _context(tmp_path, script_input_sha256=payload_a["semantic_sha256"])
    context_b = replace(
        context_a,
        script_input_sha256=payload_b["semantic_sha256"],
    )

    assert payload_a["semantic_sha256"] != payload_b["semantic_sha256"]
    assert input_fingerprint(context_a, options) != input_fingerprint(context_b, options)
