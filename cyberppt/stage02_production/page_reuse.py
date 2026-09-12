from __future__ import annotations

import json
from hashlib import sha256
from pathlib import Path
from typing import Any

from cyberppt.stage02_input import input_page_map, load_stage02_input
from scripts.imagegen_pipeline.page_manifest import output_variants_for_mode

from .manifest_stage import _reuse_prior_artifacts
from .preflight import read_json, sha256_file, write_json


PAGE_INPUT_SHA256_FIELD = "stage02_page_input_sha256"


def _stable_sha256(payload: Any) -> str:
    encoded = json.dumps(
        payload,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return sha256(encoded).hexdigest()


def attach_page_input_sha256(*, manifest: dict[str, Any], project: Path) -> None:
    """Bind every manifest pair to its canonical Stage 02 page input.

    The deck-level source-script hash remains the build provenance identity. This
    page hash is narrower: it lets an unchanged page survive a whole-script hash
    change caused by edits to another page while still invalidating the edited
    page's image, clean-base, authored-SVG and Quick checkpoint receipts.
    """

    stage02_input = load_stage02_input(project, required=True)
    pages = input_page_map(stage02_input)
    for pair in manifest.get("pairs", []):
        if not isinstance(pair, dict) or pair.get("page_number") is None:
            continue
        page_number = int(pair["page_number"])
        page_input = pages.get(page_number)
        if isinstance(page_input, dict):
            pair[PAGE_INPUT_SHA256_FIELD] = _stable_sha256(page_input)


def _same_prompt_identity(
    *,
    current_pair: dict[str, Any],
    prior_pair: dict[str, Any],
    production_mode: str,
) -> bool:
    for variant in output_variants_for_mode(production_mode):
        current_item = current_pair.get(variant)
        prior_item = prior_pair.get(variant)
        if not isinstance(current_item, dict) or not isinstance(prior_item, dict):
            return False
        current_sha = str(current_item.get("prompt_sha256") or "")
        prior_sha = str(
            prior_item.get("generated_prompt_sha256")
            or prior_item.get("prompt_sha256")
            or ""
        )
        if not current_sha or current_sha != prior_sha:
            return False
    return True


def _same_manifest_contract(current: dict[str, Any], prior: dict[str, Any]) -> bool:
    if current.get("production_mode") != prior.get("production_mode"):
        return False
    current_source_mode = str(current.get("source_mode") or "script_file")
    prior_source_mode = str(prior.get("source_mode") or "script_file")
    if current_source_mode != prior_source_mode:
        return False
    current_compiler = str(
        (current.get("prompt_contract") or {}).get("compiler")
        or "content-first-v1"
    )
    prior_compiler = str(
        (prior.get("prompt_contract") or {}).get("compiler")
        or "content-first-v1"
    )
    return current_compiler == prior_compiler


def recover_page_local_artifacts(
    *,
    manifest: dict[str, Any],
    prior_manifest: dict[str, Any] | None,
    production_mode: str,
) -> tuple[int, ...]:
    """Reuse unchanged pages even when another page changed the script hash.

    Historical manifests without ``stage02_page_input_sha256`` intentionally do
    not enter this path. They retain the existing whole-script recovery behavior
    in ``manifest_stage._reuse_prior_artifacts``.
    """

    if not isinstance(prior_manifest, dict):
        return ()
    if not _same_manifest_contract(manifest, prior_manifest):
        return ()

    prior_pairs = {
        int(pair["page_number"]): pair
        for pair in prior_manifest.get("pairs", [])
        if isinstance(pair, dict) and pair.get("page_number") is not None
    }
    recovered: list[int] = []
    for pair in manifest.get("pairs", []):
        if not isinstance(pair, dict) or pair.get("page_number") is None:
            continue
        page_number = int(pair["page_number"])
        prior_pair = prior_pairs.get(page_number)
        if not isinstance(prior_pair, dict):
            continue
        current_page_sha = str(pair.get(PAGE_INPUT_SHA256_FIELD) or "")
        prior_page_sha = str(prior_pair.get(PAGE_INPUT_SHA256_FIELD) or "")
        if not current_page_sha or current_page_sha != prior_page_sha:
            continue
        if not _same_prompt_identity(
            current_pair=pair,
            prior_pair=prior_pair,
            production_mode=production_mode,
        ):
            continue

        # Reuse the repository's existing artifact-level validators after the
        # page-local semantic and prompt identities have proved equivalent.
        # Synthetic deck identities deliberately scope that validator to this
        # one page instead of weakening its normal whole-script contract.
        local_identity = f"page:{page_number}:{current_page_sha}"
        current_local = {
            "source_script_sha256": local_identity,
            "source_mode": manifest.get("source_mode"),
            "production_mode": manifest.get("production_mode"),
            "prompt_contract": manifest.get("prompt_contract"),
            "input_fingerprint": local_identity,
            "pairs": [pair],
        }
        prior_local = {
            "source_script_sha256": local_identity,
            "source_mode": prior_manifest.get("source_mode"),
            "production_mode": prior_manifest.get("production_mode"),
            "prompt_contract": prior_manifest.get("prompt_contract"),
            "input_fingerprint": local_identity,
            "pairs": [prior_pair],
        }
        _reuse_prior_artifacts(
            manifest=current_local,
            prior_manifest=prior_local,
            production_mode=production_mode,
        )
        recovered.append(page_number)
    return tuple(recovered)


def apply_page_local_reuse(
    *,
    manifest: dict[str, Any],
    prior_manifest: dict[str, Any] | None,
    project: Path,
    production_mode: str,
    manifest_path: Path,
    build_context_path: Path,
) -> tuple[int, ...]:
    attach_page_input_sha256(manifest=manifest, project=project)
    recovered = recover_page_local_artifacts(
        manifest=manifest,
        prior_manifest=prior_manifest,
        production_mode=production_mode,
    )
    write_json(manifest_path, manifest)

    if build_context_path.is_file():
        build_context = read_json(build_context_path)
        artifacts = build_context.get("artifacts")
        if not isinstance(artifacts, dict):
            artifacts = {}
            build_context["artifacts"] = artifacts
        artifacts["page_image_pairs"] = {
            "path": str(manifest_path),
            "sha256": sha256_file(manifest_path),
        }
        build_context["page_local_reuse"] = {
            "identity_field": PAGE_INPUT_SHA256_FIELD,
            "recovered_pages": list(recovered),
        }
        write_json(build_context_path, build_context)
    return recovered
