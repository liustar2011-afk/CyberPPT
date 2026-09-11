from __future__ import annotations

from script_engine.analysis_audit import audit_final_script


def _foundation() -> dict:
    return {
        "facts": [{"id": "F1", "statement": "计划推进服务能力建设。"}],
        "concepts": [],
        "entities": [],
        "relations": [],
        "arguments": [],
        "constraints": [],
        "numbers": [],
        "source_structure": [],
    }


def _plan() -> dict:
    return {
        "authoring_mode": "faithful",
        "pages": [
            {"id": "P01", "page_role": "content", "source_refs": ["F1"]}
        ],
    }


def _final(full_copy: str) -> dict:
    return {
        "deck": {"authoring_mode": "faithful"},
        "slides": [
            {
                "id": "P01",
                "page_type": "content",
                "title": "服务能力",
                "source_refs": ["F1"],
                "full_copy": full_copy,
                "onscreen": [{"heading": "服务能力", "text": full_copy}],
            }
        ],
    }


def test_outside_narrator_phrase_routes_to_review_not_blocker() -> None:
    issues, warnings = audit_final_script(
        _final("材料指出，计划推进服务能力建设。"),
        _plan(),
        _foundation(),
    )

    assert not any("FAITHFUL_OUTSIDE_NARRATOR" in issue for issue in issues)
    assert any("FAITHFUL_OUTSIDE_NARRATOR" in warning for warning in warnings)


def test_new_numeric_fact_remains_blocking() -> None:
    issues, _ = audit_final_script(
        _final("计划推进8项服务能力建设。"),
        _plan(),
        _foundation(),
    )

    assert any("FAITHFUL_NUMBER_ADDED" in issue for issue in issues)


def test_new_formal_instrument_name_remains_blocking() -> None:
    issues, _ = audit_final_script(
        _final("计划依据《新增管理办法》推进服务能力建设。"),
        _plan(),
        _foundation(),
    )

    assert any("FAITHFUL_FORMAL_INSTRUMENT_ADDED" in issue for issue in issues)
