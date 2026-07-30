from __future__ import annotations

import hashlib
import json
from pathlib import Path

from ..provenance_bindings import (
    ProvenanceSyncPhase,
    binding_groups,
    sync_files_for_phase,
)


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _sync_file(project: Path, relative: str) -> Path | None:
    path = project / relative
    if not path.is_file():
        return None
    groups = binding_groups(relative)
    if not groups:
        return None
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"无法读取 provenance 文件 {relative}：{exc}") from exc
    if not isinstance(payload, dict):
        raise ValueError(f"provenance 文件必须是 JSON 对象：{relative}")

    provenance = payload.setdefault("provenance", {})
    if not isinstance(provenance, dict):
        raise ValueError(f"{relative} 的 provenance 必须是对象")

    changed = False
    for group, relatives in groups.items():
        bucket = provenance.setdefault(group, {})
        if not isinstance(bucket, dict):
            raise ValueError(f"{relative} 的 provenance.{group} 必须是对象")
        for target_relative in relatives:
            target = project / target_relative
            if not target.is_file():
                continue
            digest = _sha256(target)
            if bucket.get(target_relative) != digest:
                bucket[target_relative] = digest
                changed = True

    if changed:
        path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        return path
    return path


def sync_provenance(project: Path, phase: ProvenanceSyncPhase = "all") -> list[Path]:
    """Recompute recorded SHA digests for editorial provenance bindings.

    Does not alter verdict/review content—only refreshes provenance digests so
    intentional human edits to decision/outline/contracts can re-enter audit.
    Bindings come from provenance_bindings.EDITORIAL_DIGEST_BINDINGS.
    """
    updated: list[Path] = []
    for relative in sync_files_for_phase(phase):
        result = _sync_file(project, relative)
        if result is not None and result not in updated:
            updated.append(result)
    return updated
