from __future__ import annotations

from script_engine.semantic_contract.source_boundary import (
    collect_source_boundary_diagnostics,
)


def _foundation() -> dict:
    return {
        "facts": [
            {
                "id": "F1",
                "statement": "方案A包含12项要求，并依据《甲办法》执行。",
            },
            {
                "id": "F2",
                "statement": "方案B包含18项要求，并依据《乙办法》执行。",
            },
        ],
        "concepts": [],
        "entities": [],
        "relations": [],
        "arguments": [],
        "constraints": [],
        "numbers": [],
        "source_structure": [],
    }


def _module(text: str, *, text_refs: list[str], items: list[dict] | None = None) -> dict:
    bindings = [
        {
            "target": "heading",
            "source_refs": ["F1"],
            "relation": "expresses",
        },
        {
            "target": "text",
            "source_refs": text_refs,
            "relation": "expresses",
        },
    ]
    for item in items or []:
        bindings.append(
            {
                "target": item["id"],
                "source_refs": item["source_refs"],
                "relation": "supports",
            }
        )
    payload = {
        "id": "M01",
        "heading": "方案A",
        "text": text,
        "provenance": {
            "derivation": "direct",
            "claim_refs": ["F1"],
            "bindings": bindings,
        },
    }
    if items:
        payload["items"] = [
            {"id": item["id"], "text": item["text"]}
            for item in items
        ]
    return payload


def _script(module: dict) -> dict:
    return {
        "contract": "cyberppt.final-script",
        "version": "1.1",
        "slides": [
            {
                "id": "P01",
                "page_type": "content",
                "source_refs": ["F1", "F2"],
                "onscreen": [module],
            }
        ],
    }


def test_v11_text_cannot_borrow_number_from_another_slide_ref() -> None:
    diagnostics = collect_source_boundary_diagnostics(
        _script(_module("方案A包含18项要求。", text_refs=["F1"])),
        _foundation(),
    )

    assert any(
        diagnostic.code == "FINAL_NUMBER_OUTSIDE_SLIDE_EVIDENCE"
        and diagnostic.target == "slides.0.onscreen[0].text"
        and diagnostic.evidence_refs == ("F1",)
        and "18" in diagnostic.message
        for diagnostic in diagnostics
    )


def test_v11_text_accepts_number_from_its_exact_binding() -> None:
    diagnostics = collect_source_boundary_diagnostics(
        _script(_module("方案B包含18项要求。", text_refs=["F2"])),
        _foundation(),
    )

    assert not any(
        diagnostic.target == "slides.0.onscreen[0].text"
        and diagnostic.code.startswith("FINAL_NUMBER_OUTSIDE_")
        for diagnostic in diagnostics
    )


def test_v11_item_uses_item_binding_for_formal_instrument_boundary() -> None:
    module = _module(
        "方案A包含12项要求。",
        text_refs=["F1"],
        items=[
            {
                "id": "M01-I01",
                "text": "执行依据：《乙办法》",
                "source_refs": ["F1"],
            }
        ],
    )

    diagnostics = collect_source_boundary_diagnostics(_script(module), _foundation())

    assert any(
        diagnostic.code == "FINAL_FORMAL_INSTRUMENT_OUTSIDE_SLIDE_EVIDENCE"
        and diagnostic.target == "slides.0.onscreen[0].items[0].text"
        and diagnostic.evidence_refs == ("F1",)
        and "《乙办法》" in diagnostic.message
        for diagnostic in diagnostics
    )
