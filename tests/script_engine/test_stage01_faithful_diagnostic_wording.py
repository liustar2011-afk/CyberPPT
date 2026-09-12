from __future__ import annotations

from script_engine.analysis_audits.final_lean import (
    _audit_lean_authored_source_consumption,
)


def _strict_page() -> dict:
    return {
        "id": "p01",
        "page_role": "content",
        "source_refs": ["F1", "F2", "F3"],
    }


def _foundation() -> dict:
    return {"source_consumption_policy": "required"}


def _items() -> dict[str, dict]:
    return {
        "F1": {"id": "F1", "statement": "行业数据持续积累并形成稳定的数据基础。"},
        "F2": {"id": "F2", "statement": "数据使用需要保留来源边界和授权条件。"},
        "F3": {"id": "F3", "statement": "页面内容应完整保留原始事实及其限定关系。"},
    }


def test_source_consumption_warning_does_not_require_a_whole_argument() -> None:
    items = _items()
    issues = _audit_lean_authored_source_consumption(
        _strict_page(),
        {
            "source_refs": ["F1"],
            "full_copy": items["F1"]["statement"],
        },
        items,
        _foundation(),
    )

    issue = next(
        value for value in issues if value.startswith("AUTHOR_SOURCE_CONSUMPTION_TOO_NARROW:")
    )
    assert "source-backed content" in issue
    assert "whole argument" not in issue


def test_full_copy_density_warning_is_content_not_argument_or_onscreen_contract() -> None:
    items = _items()
    issues = _audit_lean_authored_source_consumption(
        _strict_page(),
        {
            "source_refs": ["F1", "F2", "F3"],
            "full_copy": " ".join(item["statement"] for item in items.values()),
        },
        items,
        _foundation(),
    )

    issue = next(value for value in issues if value.startswith("AUTHOR_FULL_COPY_TOO_THIN:"))
    assert "source-backed content paragraph(s)" in issue
    assert "audience-facing content hierarchy" in issue
    assert "argument paragraph" not in issue
    assert "onscreen compression" not in issue
