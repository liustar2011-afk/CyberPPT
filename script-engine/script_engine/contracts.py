"""Validation helpers for Script Engine delivery contracts."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator


ROOT = Path(__file__).resolve().parents[1]
CONTRACTS = ROOT / "contracts"


def load_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(payload, dict):
        raise ValueError(f"JSON root must be an object: {path}")
    return payload


def load_schema(name: str) -> dict[str, Any]:
    return load_json(CONTRACTS / name)


def validate_payload(payload: dict[str, Any], schema_name: str) -> list[str]:
    schema = load_schema(schema_name)
    validator = Draft202012Validator(schema)
    errors = sorted(validator.iter_errors(payload), key=lambda item: list(item.absolute_path))
    result: list[str] = []
    for error in errors:
        location = ".".join(str(part) for part in error.absolute_path) or "$"
        result.append(f"{location}: {error.message}")
    return result


def validate_final_script(payload: dict[str, Any]) -> list[str]:
    return validate_payload(payload, "final-script.schema.json")


def validate_deck_plan(payload: dict[str, Any]) -> list[str]:
    return validate_payload(payload, "deck-plan.schema.json")


def validate_foundation(payload: dict[str, Any]) -> list[str]:
    return validate_payload(payload, "foundation.schema.json")
