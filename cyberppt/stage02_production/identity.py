"""Deterministic input identity for Stage 02 builds."""

from __future__ import annotations

import hashlib
import json
from typing import Any, Mapping

from .models import Stage02BuildContext, Stage02RunOptions


def input_identity_payload(context: Stage02BuildContext, options: Stage02RunOptions) -> dict[str, Any]:
    """Return only inputs that can change production output.

    ``build_id`` is intentionally excluded: it is a run identity. This payload
    is stable for equivalent production inputs and can therefore drive cache,
    invalidation and audit comparisons independently of when the run started.
    """

    return {
        "schema": "cyberppt.stage02_input_identity.v1",
        "source_script_sha256": context.source_script_sha256,
        "script_input_sha256": context.script_input_sha256,
        "visual_spec_sha256": context.visual_spec_sha256,
        "style_lock_sha256": context.style_lock_sha256,
        "pages": list(context.selected_pages),
        "production_mode": context.production_mode,
        "assembly_mode": context.assembly_mode,
        "image_model": options.image_model,
        "image_quality": options.image_quality,
        "prompt_enrich": options.prompt_enrich,
        "allow_prompt_edit": options.allow_prompt_edit,
    }


def input_fingerprint(context: Stage02BuildContext, options: Stage02RunOptions) -> str:
    payload = input_identity_payload(context, options)
    canonical = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def same_input_identity(left: Mapping[str, Any], right: Mapping[str, Any]) -> bool:
    return bool(left.get("input_fingerprint")) and left.get("input_fingerprint") == right.get("input_fingerprint")
