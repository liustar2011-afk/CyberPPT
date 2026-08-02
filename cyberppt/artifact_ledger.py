"""Versioned, atomic artifact-ledger helpers.

The ledger is deliberately append-only at the artifact-record level.  A
single filesystem path can therefore have multiple records belonging to
different builds; ``supersedes`` links a new record to the previous version
without destroying the audit trail.
"""

from __future__ import annotations

import hashlib
import json
import os
from datetime import datetime, timezone
from pathlib import Path
import tempfile
from typing import Any, Iterable


LEDGER_SCHEMA = "cyberppt.artifact_ledger.v1"
LEDGER_REVISION = 2


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def sha256_path(path: Path) -> str | None:
    if not path.is_file():
        return None
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def read_ledger(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {"schema": LEDGER_SCHEMA, "ledger_revision": LEDGER_REVISION, "artifacts": []}
    payload = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(payload, dict):
        raise ValueError(f"artifact ledger root must be an object: {path}")
    artifacts = payload.get("artifacts")
    if artifacts is None:
        payload["artifacts"] = []
    elif not isinstance(artifacts, list):
        raise ValueError(f"artifact ledger artifacts must be a list: {path}")
    payload.setdefault("schema", LEDGER_SCHEMA)
    payload.setdefault("ledger_revision", LEDGER_REVISION)
    return payload


def write_json_atomic(path: Path, payload: dict[str, Any]) -> None:
    """Write JSON through a same-directory temporary file and atomic replace."""

    path.parent.mkdir(parents=True, exist_ok=True)
    fd, raw_tmp = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=path.parent)
    tmp = Path(raw_tmp)
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as handle:
            json.dump(payload, handle, ensure_ascii=False, indent=2)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(tmp, path)
    finally:
        if tmp.exists():
            tmp.unlink()


def _logical_key(record: dict[str, Any]) -> str:
    if record.get("id"):
        return f"id:{record['id']}"
    return f"path:{record.get('path', '')}"


def _artifact_id(record: dict[str, Any], build_id: str) -> str:
    explicit = record.get("artifact_id")
    if explicit:
        return str(explicit)
    source = "|".join(
        (
            build_id,
            str(record.get("stage", "")),
            str(record.get("page", "")),
            str(record.get("id", "")),
            str(record.get("path", "")),
        )
    )
    return f"artifact-{hashlib.sha256(source.encode('utf-8')).hexdigest()[:20]}"


def append_artifacts(
    ledger_path: Path,
    records: Iterable[dict[str, Any]],
    *,
    build_id: str,
) -> Path:
    """Append records without path-based replacement.

    If the same ``artifact_id`` is written twice with identical content, the
    second write is idempotent.  A conflicting rewrite is rejected rather than
    silently replacing an audited artifact.
    """

    ledger = read_ledger(ledger_path)
    artifacts = ledger.setdefault("artifacts", [])
    prior_by_key: dict[str, dict[str, Any]] = {}
    existing_by_id: dict[str, dict[str, Any]] = {}
    for item in artifacts:
        if not isinstance(item, dict):
            continue
        prior_by_key[_logical_key(item)] = item
        if item.get("artifact_id"):
            existing_by_id[str(item["artifact_id"])] = item

    for raw in records:
        record = dict(raw)
        record["build_id"] = str(record.get("build_id") or build_id)
        record["artifact_id"] = _artifact_id(record, record["build_id"])
        record.setdefault("created_at", record.get("updated_at") or utc_now())
        record.setdefault("supersedes", [])
        logical = _logical_key(record)
        previous = prior_by_key.get(logical)
        if previous and not record["supersedes"]:
            previous_id = previous.get("artifact_id") or previous.get("id") or previous.get("path")
            if previous_id:
                record["supersedes"] = [str(previous_id)]

        existing = existing_by_id.get(record["artifact_id"])
        if existing is not None:
            comparable_existing = {
                key: existing.get(key)
                for key in ("path", "sha256", "status", "build_id", "stage", "page")
            }
            comparable_new = {
                key: record.get(key)
                for key in ("path", "sha256", "status", "build_id", "stage", "page")
            }
            if comparable_existing != comparable_new:
                raise ValueError(
                    f"artifact id already exists with different content: {record['artifact_id']}"
                )
            continue
        artifacts.append(record)
        prior_by_key[logical] = record
        existing_by_id[record["artifact_id"]] = record

    ledger["schema"] = ledger.get("schema") or LEDGER_SCHEMA
    ledger["ledger_revision"] = max(int(ledger.get("ledger_revision", 1) or 1), LEDGER_REVISION)
    write_json_atomic(ledger_path, ledger)
    return ledger_path
