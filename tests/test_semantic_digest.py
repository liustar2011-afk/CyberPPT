from __future__ import annotations

import json
from pathlib import Path

from cyberppt.semantic_digest import (
    chapter_manifest_semantic_digest,
    outline_semantic_digest,
    script_semantic_digest,
    stage02_handoff_semantic_digest,
)


def test_script_markdown_decoration_does_not_change_semantic_digest(tmp_path: Path) -> None:
    legacy = tmp_path / "legacy.md"
    plain = tmp_path / "plain.md"
    common_head = """## 第1页：示例
- 页面类型：内容页
- 页面标题：示例
- 主判断：业务关系发生变化。
### 完整文字稿

业务关系发生变化，需要形成协同机制。
### 上屏文字（严格锁定）

"""
    common_tail = """
### 视觉结构（不上屏）

左右双区表达同一业务关系。
【演讲者备注】
业务关系发生变化，需要形成协同机制。
"""
    legacy.write_text(
        common_head + "#### 业务演进\n- **系统运行**：关系更加复杂。\n" + common_tail,
        encoding="utf-8",
    )
    plain.write_text(
        common_head + "业务演进\n系统运行：关系更加复杂。\n" + common_tail,
        encoding="utf-8",
    )
    assert script_semantic_digest(legacy) == script_semantic_digest(plain)


def test_script_text_change_changes_semantic_digest(tmp_path: Path) -> None:
    path = tmp_path / "script.md"
    path.write_text("## 第1页：示例\n- 页面类型：内容页\n- 上屏文字：原结论\n", encoding="utf-8")
    before = script_semantic_digest(path)
    path.write_text("## 第1页：示例\n- 页面类型：内容页\n- 上屏文字：新结论\n", encoding="utf-8")
    assert script_semantic_digest(path) != before


def test_outline_json_formatting_does_not_change_semantic_digest(tmp_path: Path) -> None:
    path = tmp_path / "outline.json"
    payload = {"schema": "cyberppt.outline.v2", "pages": [{"page_id": "p01", "core_message": "结论"}]}
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    before = outline_semantic_digest(path)
    path.write_text(json.dumps(payload, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    assert outline_semantic_digest(path) == before


def test_manifest_timestamp_and_paths_do_not_change_semantic_digest(tmp_path: Path) -> None:
    path = tmp_path / "manifest.json"
    payload = {
        "schema": "cyberppt.chapter_review_manifest.v1",
        "level": "script",
        "input_semantic_sha256": "abc",
        "reviewed_at": "first",
        "reviews": [{"path": "a.md", "chapter_ids": ["CH01"], "page_ids": ["p01"], "status": "passed", "high_priority_open": []}],
    }
    path.write_text(json.dumps(payload), encoding="utf-8")
    before = chapter_manifest_semantic_digest(path)
    payload["reviewed_at"] = "second"
    payload["reviews"][0]["path"] = "renamed.md"
    path.write_text(json.dumps(payload), encoding="utf-8")
    assert chapter_manifest_semantic_digest(path) == before


def test_manifest_open_high_priority_issue_changes_semantic_digest(tmp_path: Path) -> None:
    path = tmp_path / "manifest.json"
    payload = {
        "schema": "cyberppt.chapter_review_manifest.v1",
        "level": "script",
        "input_semantic_sha256": "abc",
        "reviews": [{"chapter_ids": ["c1"], "page_ids": ["p01"], "status": "passed", "high_priority_open": []}],
    }
    path.write_text(json.dumps(payload), encoding="utf-8")
    before = chapter_manifest_semantic_digest(path)
    payload["reviews"][0]["high_priority_open"] = ["p01 mission conflict"]
    path.write_text(json.dumps(payload), encoding="utf-8")
    assert chapter_manifest_semantic_digest(path) != before


def test_handoff_receipt_changes_do_not_change_semantics_but_page_text_does(tmp_path: Path) -> None:
    path = tmp_path / "handoff.json"
    payload = {
        "schema": "cyberppt.stage02_handoff.v1",
        "project": "old/path",
        "created_at": "first",
        "source_bindings": {"script": {"path": "old.md", "sha256": "raw-a", "semantic_sha256": "sem-a"}},
        "page_order": ["p01"],
        "pages": [{"page_id": "p01", "core_message": "approved conclusion"}],
    }
    path.write_text(json.dumps(payload), encoding="utf-8")
    before = stage02_handoff_semantic_digest(path)
    payload["project"] = "new/path"
    payload["created_at"] = "second"
    payload["source_bindings"]["script"]["path"] = "new.md"
    payload["source_bindings"]["script"]["sha256"] = "raw-b"
    path.write_text(json.dumps(payload), encoding="utf-8")
    assert stage02_handoff_semantic_digest(path) == before
    payload["pages"][0]["core_message"] = "changed conclusion"
    path.write_text(json.dumps(payload), encoding="utf-8")
    assert stage02_handoff_semantic_digest(path) != before
