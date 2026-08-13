"""Read the single Markdown library of semantic expression models."""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path


DEFAULT_LIBRARY = Path(__file__).resolve().parent.parent / "references" / "semantic-expression-models.md"
_MODEL = re.compile(r"^## (?P<title>[^\n]+)\n<!-- model\n(?P<meta>.*?)\n-->\n### Expression structure\n\n(?P<structure>.*?)(?=\n## |\Z)", re.MULTILINE | re.DOTALL)


@dataclass(frozen=True)
class ModelSlot:
    name: str
    required: bool
    implicit_allowed: bool


@dataclass(frozen=True)
class ExpressionModel:
    model_id: str
    family: str
    lifecycle: str
    semantic_signature: tuple[str, ...]
    slots: tuple[ModelSlot, ...]
    expression_structure: str
    forbidden_inferences: tuple[str, ...]


def _inline_list(value: str) -> tuple[str, ...]:
    value = value.strip()
    if not value.startswith("[") or not value.endswith("]"):
        raise ValueError(f"expected bracketed list: {value}")
    return tuple(item.strip() for item in value[1:-1].split(",") if item.strip())


def _slots(value: str) -> tuple[ModelSlot, ...]:
    result: list[ModelSlot] = []
    for raw in _inline_list(value):
        values = raw.split("|")
        if len(values) not in {1, 2} or not values[0].strip():
            raise ValueError(f"invalid model slot: {raw}")
        mode = values[1].strip() if len(values) == 2 else "optional"
        if mode not in {"required", "optional", "implicit_allowed"}:
            raise ValueError(f"invalid model slot mode: {mode}")
        result.append(ModelSlot(values[0].strip(), mode == "required", mode == "implicit_allowed"))
    return tuple(result)


def load_expression_models(path: Path = DEFAULT_LIBRARY) -> dict[str, ExpressionModel]:
    """Load a single fixed-format Markdown model library."""

    text = path.read_text(encoding="utf-8")
    models: dict[str, ExpressionModel] = {}
    for match in _MODEL.finditer(text):
        fields: dict[str, str] = {}
        for line in match.group("meta").splitlines():
            key, separator, value = line.partition(":")
            if not separator or not key.strip() or not value.strip():
                raise ValueError(f"invalid model metadata line: {line}")
            fields[key.strip()] = value.strip()
        model_id = fields.get("id", "")
        family = fields.get("family", "")
        # Existing curated entries pre-date lifecycle metadata and are trusted.
        lifecycle = fields.get("lifecycle", "verified")
        if not model_id or not family or model_id in models:
            raise ValueError(f"invalid or duplicate expression model id: {model_id}")
        if lifecycle not in {"candidate", "verified", "deprecated"}:
            raise ValueError(f"invalid expression model lifecycle: {lifecycle}")
        models[model_id] = ExpressionModel(
            model_id=model_id,
            family=family,
            lifecycle=lifecycle,
            semantic_signature=_inline_list(fields.get("semantic_signature", "[]")),
            slots=_slots(fields.get("slots", "[]")),
            expression_structure=match.group("structure").strip(),
            forbidden_inferences=_inline_list(fields.get("forbidden_inferences", "[]")),
        )
    if "source_native" not in models:
        raise ValueError("expression model library must contain source_native")
    return models


def model_candidates(models: dict[str, ExpressionModel], semantic_signature: set[str]) -> list[ExpressionModel]:
    """Rank verified model signatures; source-native is always a fallback.

    Candidate entries remain inspectable in the Markdown library, but cannot
    become automatic recommendations until an author promotes them after review.
    """

    native = models["source_native"]
    ranked = sorted(
        (
            model
            for model in models.values()
            if model.model_id != "source_native" and model.lifecycle == "verified"
        ),
        key=lambda model: (-len(set(model.semantic_signature) & semantic_signature), model.model_id),
    )
    return ranked + [native]
