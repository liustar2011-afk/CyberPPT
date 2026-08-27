"""Root-aware post-generation coverage diagnostics for locked ImageGen text.

This module does not infer layout ownership from OCR geometry.  Root/text-id
ownership comes only from the audited FinalPromptIR debug receipt. OCR and
vision observations are used conservatively to report whether the locked text
for each root is observable at all.
"""

from __future__ import annotations

import re
from typing import Any, Mapping, Sequence

CONTENT_ROOT_QA_SCHEMA = "cyberppt.image_content_root_qa.v1"


def _normalize(value: object) -> str:
    return re.sub(r"[\s\W_]+", "", str(value or ""), flags=re.UNICODE).casefold()


def _observation_corpus(text_audit: Mapping[str, Any]) -> tuple[str, ...]:
    values: list[str] = []
    observed = text_audit.get("observed_text")
    if isinstance(observed, list):
        values.extend(str(item) for item in observed if str(item).strip())
    ocr_items = text_audit.get("ocr_items")
    if isinstance(ocr_items, list):
        for item in ocr_items:
            if isinstance(item, Mapping) and str(item.get("text") or "").strip():
                values.append(str(item["text"]))
    return tuple(values)


def _is_observed(required: str, observations: Sequence[str]) -> bool:
    """Return a conservative coverage match without fuzzy semantic guessing.

    Full normalized equality is preferred. For multi-line OCR segmentation,
    concatenated observation text may also contain the full required string.
    No edit-distance or synonym matching is allowed because that would make a
    malformed or altered locked string look present.
    """

    target = _normalize(required)
    if not target:
        return False
    normalized = tuple(_normalize(item) for item in observations if _normalize(item))
    if target in normalized:
        return True
    joined = "".join(normalized)
    return len(target) >= 4 and target in joined


def build_content_root_qa(
    *,
    page_number: int,
    debug_receipt: Mapping[str, Any],
    text_audit: Mapping[str, Any],
) -> dict[str, Any]:
    """Build a per-root text coverage receipt from authoritative bindings."""

    raw_bindings = debug_receipt.get("text_bindings")
    if not isinstance(raw_bindings, list) or not raw_bindings:
        return {
            "schema": CONTENT_ROOT_QA_SCHEMA,
            "page_number": page_number,
            "status": "not_applicable",
            "reason": "no_visible_text_bindings_in_prompt_debug_receipt",
            "roots": [],
        }

    observations = _observation_corpus(text_audit)
    roots: list[dict[str, Any]] = []
    for raw in raw_bindings:
        if not isinstance(raw, Mapping):
            continue
        root_id = str(raw.get("root_id") or "").strip()
        text_ids = tuple(str(item) for item in raw.get("text_ids") or [])
        exact_text = tuple(str(item) for item in raw.get("exact_text") or [])
        if not root_id or len(text_ids) != len(exact_text):
            raise ValueError("content-root QA received malformed debug text binding")
        matched_ids = tuple(
            text_id
            for text_id, text in zip(text_ids, exact_text)
            if _is_observed(text, observations)
        )
        missing_ids = tuple(text_id for text_id in text_ids if text_id not in matched_ids)
        roots.append(
            {
                "root_id": root_id,
                "required_text_ids": list(text_ids),
                "matched_text_ids": list(matched_ids),
                "missing_text_ids": list(missing_ids),
                "status": "passed" if not missing_ids else "incomplete",
            }
        )

    incomplete = [root for root in roots if root["status"] != "passed"]
    return {
        "schema": CONTENT_ROOT_QA_SCHEMA,
        "page_number": page_number,
        "scope": "root_text_coverage_diagnostic",
        "spatial_root_assignment": "not_inferred_from_ocr",
        "roots": roots,
        "status": "passed" if not incomplete else "incomplete",
        "missing_text_ids": [
            text_id
            for root in incomplete
            for text_id in root["missing_text_ids"]
        ],
    }


__all__ = ["CONTENT_ROOT_QA_SCHEMA", "build_content_root_qa"]
