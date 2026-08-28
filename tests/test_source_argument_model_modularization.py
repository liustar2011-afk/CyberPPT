from __future__ import annotations

import importlib


def test_source_argument_model_keeps_contract_constants_as_legacy_facade() -> None:
    model = importlib.import_module("cyberppt.source_argument_model")
    contract = importlib.import_module("cyberppt.source_argument_contract")

    for name in (
        "SCHEMA", "MODEL_JSON", "MODEL_BLOCK_MARKER", "ROOT_NODE_IDS", "RELATIONS",
        "ARGUMENT_WEIGHTS", "ARGUMENT_DUTIES", "ARGUMENT_ROLES", "STATUS_VALUES",
        "INTERPRETATION_CONTRACT_MODES", "CLAIM_ORIGINS", "SOURCE_TRUTH_CLAIM_ROLES",
        "INFERENCE_ORIGINS", "CONCEPT_RESOLUTIONS", "_LEGACY_EVIDENCE_RE", "_SOURCE_UNIT_RE",
    ):
        assert getattr(model, name) is getattr(contract, name)


def test_source_argument_contract_has_no_runtime_model_dependency() -> None:
    contract = importlib.import_module("cyberppt.source_argument_contract")

    assert "source_argument_model" not in contract.__dict__
