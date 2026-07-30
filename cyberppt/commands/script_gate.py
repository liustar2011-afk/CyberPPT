"""Persist and gate per-slide generation scripts before producing artifacts."""

from __future__ import annotations

import json
import hashlib
import shutil
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


SCRIPT_KINDS = {"pptx", "imagegen", "blueprint", "analysis"}
SCRIPT_PHASES = {"draft", "final"}


@dataclass(frozen=True)
class ScriptStatus:
    project: str
    slide: int
    kind: str
    draft_paths: list[str]
    final_paths: list[str]
    approval_path: str
    approval_exists: bool
    ready_to_generate: bool
    reason: str


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _project_root(project: Path) -> Path:
    return project.expanduser().resolve()


def _slide_slug(slide: int) -> str:
    if slide < 1:
        raise ValueError("slide must be >= 1")
    return f"slide-{slide:02d}"


def _validate_kind(kind: str) -> str:
    if kind not in SCRIPT_KINDS:
        allowed = ", ".join(sorted(SCRIPT_KINDS))
        raise ValueError(f"unknown script kind: {kind}; expected one of: {allowed}")
    return kind


def _validate_phase(phase: str) -> str:
    if phase not in SCRIPT_PHASES:
        allowed = ", ".join(sorted(SCRIPT_PHASES))
        raise ValueError(f"unknown script phase: {phase}; expected one of: {allowed}")
    return phase


def _ensure_plaintext(source: Path) -> None:
    try:
        source.read_text(encoding="utf-8")
    except UnicodeDecodeError as exc:
        raise ValueError(f"script must be UTF-8 plaintext: {source}") from exc


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest().lower()


def _script_dir(project: Path, kind: str, phase: str) -> Path:
    if kind == "imagegen":
        return project / "workbench" / "prompts" / "imagegen"
    if phase == "draft":
        return project / "workbench" / "scripts" / "drafts"
    return project / "workbench" / "scripts" / "final"


def _script_path(project: Path, slide: int, kind: str, phase: str, suffix: str) -> Path:
    suffix = suffix if suffix.startswith(".") else f".{suffix}"
    return _script_dir(project, kind, phase) / f"{_slide_slug(slide)}-{kind}-{phase}{suffix}"


def _manifest_path(project: Path) -> Path:
    return project / "workbench" / "scripts" / "script-manifest.json"


def _approval_path(project: Path, slide: int, kind: str) -> Path:
    return project / "workbench" / "approvals" / f"{_slide_slug(slide)}-{kind}-script-approved.json"


def _read_manifest(project: Path) -> dict[str, Any]:
    path = _manifest_path(project)
    if not path.exists():
        return {"schema": "cyberppt.script_manifest.v1", "entries": []}
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def stage_script(
    project: Path,
    slide: int,
    kind: str,
    phase: str,
    source: Path,
    note: str = "",
) -> Path:
    """Copy a UTF-8 script or prompt into the project script ledger."""

    root = _project_root(project)
    kind = _validate_kind(kind)
    phase = _validate_phase(phase)
    source = source.expanduser().resolve()
    if not source.exists():
        raise FileNotFoundError(f"script source not found: {source}")
    _ensure_plaintext(source)

    target = _script_path(root, slide, kind, phase, source.suffix or ".txt")
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(source, target)

    manifest = _read_manifest(root)
    manifest.setdefault("entries", []).append(
        {
            "slide": slide,
            "kind": kind,
            "phase": phase,
            "source": str(source),
            "saved_path": str(target),
            "saved_at": _utc_now(),
            "note": note,
            "requires_user_review_before_generation": True,
        }
    )
    _write_json(_manifest_path(root), manifest)
    return target


def approve_script(project: Path, slide: int, kind: str, note: str = "") -> Path:
    """Record user approval for a staged final script."""

    root = _project_root(project)
    kind = _validate_kind(kind)
    if kind == "analysis":
        from cyberppt.stage01_controls import assert_escalation_resolved

        assert_escalation_resolved(root, "script")
    status = get_script_status(root, slide, kind)
    if not status.final_paths:
        raise FileNotFoundError(
            f"no final {kind} script saved for {_slide_slug(slide)}; stage a final script before approval"
        )

    path = _approval_path(root, slide, kind)
    _write_json(
        path,
        {
            "schema": "cyberppt.script_approval.v1",
            "slide": slide,
            "kind": kind,
            "approved": True,
            "approved_at": _utc_now(),
            "approved_artifacts": status.final_paths,
            "approved_hashes": {
                artifact: _sha256(Path(artifact)) for artifact in status.final_paths
            },
            "approved_manifest_entry_count": len(
                _read_manifest(root).get("entries", [])
            ),
            "note": note,
        },
    )
    return path


def assert_approved_final_script(project: Path, slide: int, kind: str) -> Path:
    """Return the approved final artifact, rejecting stale or incomplete approvals."""

    root = _project_root(project)
    kind = _validate_kind(kind)
    status = get_script_status(root, slide, kind)
    if not status.final_paths:
        raise FileNotFoundError(
            f"no final {kind} script saved for {_slide_slug(slide)}; stage a final script before generation"
        )
    approval_path = Path(status.approval_path)
    if not approval_path.is_file():
        raise PermissionError(
            f"missing user approval for final {kind} script on {_slide_slug(slide)}: {approval_path}"
        )
    approval = json.loads(approval_path.read_text(encoding="utf-8-sig"))
    if approval.get("approved") is not True:
        raise PermissionError(f"final {kind} script approval is not affirmative: {approval_path}")
    approved_hashes = approval.get("approved_hashes")
    if not isinstance(approved_hashes, dict):
        raise PermissionError(
            f"final {kind} script approval is not hash-bound; reapprove before generation: {approval_path}"
        )
    for artifact in status.final_paths:
        expected = approved_hashes.get(artifact)
        if not expected or expected != _sha256(Path(artifact)):
            raise PermissionError(
                f"final {kind} script changed after approval; reapprove before generation: {artifact}"
            )
    if not status.ready_to_generate:
        raise PermissionError(status.reason)
    return Path(status.final_paths[0])


def get_script_status(project: Path, slide: int, kind: str) -> ScriptStatus:
    root = _project_root(project)
    kind = _validate_kind(kind)
    draft_dir = _script_dir(root, kind, "draft")
    final_dir = _script_dir(root, kind, "final")
    draft_paths = sorted(str(path) for path in draft_dir.glob(f"{_slide_slug(slide)}-{kind}-draft.*"))
    final_paths = sorted(str(path) for path in final_dir.glob(f"{_slide_slug(slide)}-{kind}-final.*"))
    approval_path = _approval_path(root, slide, kind)
    approval_exists = approval_path.exists()
    ready = False
    if not final_paths:
        reason = "final script is not saved"
    elif not approval_exists:
        reason = "user approval is not recorded"
    else:
        try:
            approval = json.loads(approval_path.read_text(encoding="utf-8-sig"))
        except (OSError, json.JSONDecodeError):
            reason = "user approval record is unreadable"
        else:
            approved_hashes = approval.get("approved_hashes")
            hashes_match = (
                approval.get("approved") is True
                and isinstance(approved_hashes, dict)
                and all(
                    approved_hashes.get(artifact) == _sha256(Path(artifact))
                    for artifact in final_paths
                )
            )
            if not hashes_match:
                reason = "final script changed after approval; reapprove before generation"
            else:
                manifest_entries = _read_manifest(root).get("entries", [])
                approved_count = approval.get("approved_manifest_entry_count")
                if isinstance(approved_count, int):
                    newer_entries = manifest_entries[approved_count:]
                else:
                    approved_at = str(approval.get("approved_at") or "")
                    newer_entries = [
                        entry
                        for entry in manifest_entries
                        if str(entry.get("saved_at") or "") > approved_at
                    ]
                newer_draft = any(
                    entry.get("slide") == slide
                    and entry.get("kind") == kind
                    and entry.get("phase") == "draft"
                    for entry in newer_entries
                )
                if newer_draft:
                    reason = "a newer draft is waiting for final staging and user approval"
                else:
                    ready = True
                    reason = "final script is saved and user approval is recorded"
    return ScriptStatus(
        project=str(root),
        slide=slide,
        kind=kind,
        draft_paths=draft_paths,
        final_paths=final_paths,
        approval_path=str(approval_path),
        approval_exists=approval_exists,
        ready_to_generate=ready,
        reason=reason,
    )


def status_as_json(status: ScriptStatus) -> str:
    return json.dumps(asdict(status), ensure_ascii=False, indent=2)
