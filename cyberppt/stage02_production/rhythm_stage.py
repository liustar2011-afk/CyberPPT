from __future__ import annotations

from hashlib import sha256
from pathlib import Path
from typing import Any

from cyberppt.full_image_rhythm import build_manifest_contact_sheet
from cyberppt.full_image_rhythm_audit import audit_deck_visual_rhythm
from cyberppt.full_image_signature import build_manifest_visual_signatures

from .preflight import write_json


RHYTHM_RECEIPT_SCHEMA = "cyberppt.full_image_deck_rhythm_receipt.v1"


def run_full_image_rhythm_stage(
    manifest: dict[str, Any],
    *,
    build_dir: Path,
) -> dict[str, Any]:
    """Review audited full images before they become reconstruction authority."""

    qa_dir = build_dir.expanduser().resolve() / "qa"
    qa_dir.mkdir(parents=True, exist_ok=True)
    contact_path = qa_dir / "full_image_contact_sheet.png"
    receipt_path = qa_dir / "full_image_deck_rhythm_qa.json"

    contact = build_manifest_contact_sheet(manifest, contact_path)
    signatures = build_manifest_visual_signatures(manifest)
    audit = audit_deck_visual_rhythm(signatures)

    signature_by_page = {int(item["page_number"]): item for item in signatures}
    for pair in manifest.get("pairs") or []:
        if not isinstance(pair, dict):
            continue
        page_number = int(pair.get("page_number") or 0)
        signature = signature_by_page.get(page_number)
        full = pair.get("full")
        if signature is not None and isinstance(full, dict):
            full["visual_signature"] = signature

    receipt = {
        "schema": RHYTHM_RECEIPT_SCHEMA,
        "status": audit["status"],
        "contact_sheet": contact,
        "signatures": signatures,
        "audit": audit,
        "authority_gate": "before_reconstruction_visual_source_binding",
    }
    write_json(receipt_path, receipt)
    receipt_sha256 = sha256(receipt_path.read_bytes()).hexdigest()
    manifest["full_image_deck_rhythm_qa"] = {
        "schema": RHYTHM_RECEIPT_SCHEMA,
        "status": audit["status"],
        "receipt_path": str(receipt_path),
        "receipt_sha256": receipt_sha256,
        "contact_sheet_path": contact["path"],
        "contact_sheet_sha256": contact["sha256"],
        "page_count": audit["page_count"],
        "blocker_count": audit["blocker_count"],
        "warning_count": audit["warning_count"],
        "authority_gate": "before_reconstruction_visual_source_binding",
    }
    return manifest["full_image_deck_rhythm_qa"]


__all__ = ["RHYTHM_RECEIPT_SCHEMA", "run_full_image_rhythm_stage"]
