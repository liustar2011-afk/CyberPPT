"""Shared machinery for independent editorial content-review gates.

Both the outline stage and the script stage need an editorial pass that
mechanical checks cannot reliably perform: whether each page carries a
single genuine mission, whether sibling pages actually add distinct value
instead of duplicating each other, whether content stays within its own
declared scope. These are judgment calls, not string matches — so this
gate requires a reviewer who is genuinely independent of whoever authored
or last edited the material (a fresh, memory-less agent session or a human,
never the same session that just wrote or fixed the content), recorded with
provenance so the gate can't be self-certified.

Both stages share this verification logic; each stage supplies its own
review-file path, schema name, decision-dimension list, and required page
IDs. See ``cyberppt/commands/script_audit.py`` for the script-stage
decisions and ``cyberppt/commands/outline_audit.py`` for the outline-stage
decisions.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from cyberppt.semantic_digest import chapter_manifest_semantic_digest


def sha256_upper(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def content_review_status(
    review_path: Path,
    *,
    schema: str,
    decision_keys: tuple[str, ...],
    required_page_ids: list[str],
    content_sha256: str,
    content_semantic_sha256: str | None = None,
    manifest_path: Path | None = None,
) -> dict[str, Any]:
    """Return the verified status of an independent content-review file.

    ``review_path`` must contain, at minimum:

    - ``schema``: must equal the caller's ``schema`` string.
    - ``script_sha256`` (or the caller's equivalent content hash field —
      always read/written under the key ``content_sha256`` in this shared
      representation) matching ``content_sha256``, so a stale review
      (written before the last content edit) is rejected.
    - ``decisions``: an object with every key in ``decision_keys`` set to
      ``True`` for the whole deck/outline.
    - ``pages``: an object keyed by page ID; each entry must set every key
      in ``decision_keys`` to ``True`` and provide a non-empty ``note``
      string — an empty or missing note invalidates that page's review,
      since it is evidence the reviewer actually looked rather than
      bulk-approving.
    - ``review_provenance``: ``authoring_separated: true``,
      ``reviewer_type`` in ``{"human", "independent_model"}``,
      non-empty ``reviewed_at`` and ``review_summary``, and — when
      ``manifest_path`` is supplied — a ``chapter_review_manifest_sha256``
      matching that file's current hash (binds the review to the current
      chapter-structure state, not a stale one).  Model reviews must also
      carry distinct, non-empty ``authoring_run_id`` and ``reviewer_run_id``;
      human reviews must carry a non-empty ``reviewer_id``.

    Returns a dict with ``status`` one of ``missing``, ``invalid``,
    ``stale``, ``unverified``, ``incomplete``, ``approved``.
    """

    if not review_path.exists():
        return {"status": "missing", "path": str(review_path), "decisions": {}}
    try:
        payload = json.loads(review_path.read_text(encoding="utf-8-sig"))
    except (json.JSONDecodeError, OSError):
        return {"status": "invalid", "path": str(review_path), "decisions": {}}

    decisions = payload.get("decisions")
    decision_map = decisions if isinstance(decisions, dict) else {}
    page_reviews = payload.get("pages")
    page_map = page_reviews if isinstance(page_reviews, dict) else {}

    pages_approved = all(
        isinstance(page_map.get(page_id), dict)
        and all(page_map[page_id].get(key) is True for key in decision_keys)
        and bool(str(page_map[page_id].get("note") or "").strip())
        for page_id in required_page_ids
    )
    schema_valid = payload.get("schema") == schema

    provenance = payload.get("review_provenance")
    provenance_map = provenance if isinstance(provenance, dict) else {}
    reviewer_type = str(provenance_map.get("reviewer_type") or "")
    authoring_run_id = str(provenance_map.get("authoring_run_id") or "").strip()
    reviewer_run_id = str(provenance_map.get("reviewer_run_id") or "").strip()
    reviewer_id = str(provenance_map.get("reviewer_id") or "").strip()
    identity_valid = (
        bool(authoring_run_id)
        and bool(reviewer_run_id)
        and authoring_run_id != reviewer_run_id
        if reviewer_type == "independent_model"
        else bool(reviewer_id)
        if reviewer_type == "human"
        else False
    )
    manifest_hash = sha256_upper(manifest_path) if manifest_path and manifest_path.exists() else ""
    manifest_semantic_hash = (
        chapter_manifest_semantic_digest(manifest_path).upper()
        if manifest_path and manifest_path.exists()
        else ""
    )
    stored_manifest_semantic = str(
        provenance_map.get("chapter_review_manifest_semantic_sha256") or ""
    ).upper()
    provenance_valid = (
        provenance_map.get("authoring_separated") is True
        and identity_valid
        and bool(str(provenance_map.get("reviewed_at") or "").strip())
        and bool(str(provenance_map.get("review_summary") or "").strip())
        and (
            manifest_path is None
            or (
                stored_manifest_semantic == manifest_semantic_hash
                if stored_manifest_semantic
                else str(provenance_map.get("chapter_review_manifest_sha256") or "").upper()
                == manifest_hash.upper()
            )
        )
    )

    stored_hash = str(payload.get("content_sha256") or payload.get("script_sha256") or "")
    stored_semantic_hash = str(payload.get("content_semantic_sha256") or "")
    if stored_semantic_hash and content_semantic_sha256:
        content_matches = stored_semantic_hash.upper() == content_semantic_sha256.upper()
    else:
        content_matches = stored_hash.upper() == content_sha256.upper()
    if not content_matches:
        status = "stale"
    elif not schema_valid or not provenance_valid:
        status = "unverified"
    elif not all(decision_map.get(key) is True for key in decision_keys) or not pages_approved:
        status = "incomplete"
    else:
        status = "approved"

    return {
        "status": status,
        "path": str(review_path),
        "decisions": decision_map,
        "reviewed_pages": len(page_map),
        "required_pages": len(required_page_ids),
        "schema_valid": schema_valid,
        "provenance_valid": provenance_valid,
        "identity_valid": identity_valid,
        "chapter_review_manifest_sha256": manifest_hash,
        "chapter_review_manifest_semantic_sha256": manifest_semantic_hash,
        "content_semantic_sha256": content_semantic_sha256 or "",
    }
