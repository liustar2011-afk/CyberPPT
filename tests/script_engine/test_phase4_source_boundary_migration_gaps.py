from __future__ import annotations

from script_engine.semantic_contract.source_boundary import (
    collect_source_boundary_diagnostics,
)


def _foundation() -> dict:
    return {
        "facts": [{"id": "F1", "statement": "本页说明执行安排。"}],
        "concepts": [],
        "entities": [],
        "relations": [],
        "arguments": [],
        "constraints": [],
        "numbers": [],
        "source_structure": [],
    }


def test_argument_chain_retains_legacy_numeric_boundary_coverage() -> None:
    final_script = {
        "contract": "cyberppt.final-script",
        "version": "1.0",
        "slides": [
            {
                "id": "P01",
                "page_type": "content",
                "source_refs": ["F1"],
                "argument": {"chain": ["进一步新增66项执行要求"]},
            }
        ],
    }

    diagnostics = collect_source_boundary_diagnostics(final_script, _foundation())

    assert any(
        diagnostic.code == "FINAL_NUMBER_OUTSIDE_FOUNDATION"
        and diagnostic.target == "slides.0.argument.chain[0]"
        and "66" in diagnostic.message
        for diagnostic in diagnostics
    )


def test_number_in_explicit_cited_condition_is_authorized() -> None:
    foundation = _foundation()
    foundation["facts"][0]["conditions"] = ["2028年后实施"]
    final_script = {
        "contract": "cyberppt.final-script",
        "version": "1.0",
        "slides": [
            {
                "id": "P01",
                "page_type": "content",
                "source_refs": ["F1"],
                "full_copy": "相关安排于2028年后实施。",
            }
        ],
    }

    diagnostics = collect_source_boundary_diagnostics(final_script, foundation)

    assert not any(
        diagnostic.code in {
            "FINAL_NUMBER_OUTSIDE_FOUNDATION",
            "FINAL_NUMBER_OUTSIDE_SLIDE_EVIDENCE",
        }
        for diagnostic in diagnostics
    )


def test_formal_instrument_in_explicit_typed_name_is_authorized() -> None:
    foundation = _foundation()
    foundation["facts"][0]["formal_document_name"] = "《专项管理办法》"
    final_script = {
        "contract": "cyberppt.final-script",
        "version": "1.0",
        "slides": [
            {
                "id": "P01",
                "page_type": "content",
                "source_refs": ["F1"],
                "full_copy": "按照《专项管理办法》执行。",
            }
        ],
    }

    diagnostics = collect_source_boundary_diagnostics(final_script, foundation)

    assert not any(
        diagnostic.code.startswith("FINAL_FORMAL_INSTRUMENT_OUTSIDE_")
        for diagnostic in diagnostics
    )
