"""Deterministic PPTX export boundary for the dual-image pipeline."""

from __future__ import annotations

import hashlib
import json
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

from cyberppt.artifact_ledger import write_json_atomic


def backup_existing_output(output_path: Path, output_dir: Path) -> Path:
    output_dir = output_dir.resolve()
    output_path = output_path.resolve()
    try:
        output_path.relative_to(output_dir)
    except ValueError as exc:
        raise ValueError(f"refusing to backup PPTX outside output directory: {output_path}") from exc
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    backup_root = output_dir / "backup" / timestamp
    backup_root.mkdir(parents=True, exist_ok=True)
    backup_path = backup_root / output_path.name
    suffix = 2
    while backup_path.exists():
        backup_path = backup_root / f"{output_path.stem}_{suffix:02d}{output_path.suffix}"
        suffix += 1
    shutil.move(str(output_path), str(backup_path))
    return backup_path


def write_export_pointer(project_path: Path, output_path: Path) -> Path:
    digest = hashlib.sha256(output_path.read_bytes()).hexdigest()
    pointer = project_path / "analysis" / "export_artifact.json"
    write_json_atomic(
        pointer,
        {
            "schema": "cyberppt.dual_image.export_artifact.v1",
            "created_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "project_path": str(project_path.resolve()),
            "path": str(output_path.resolve()),
            "sha256": digest,
        },
    )
    return pointer


def run_svg_export(
    project_path: Path,
    *,
    output_path: Path,
    overwrite: bool = False,
    scripts_dir: Path | None = None,
    backup_dir: Path | None = None,
) -> Path:
    """Run the SVG exporter with one explicit, auditable output path."""

    output_path = output_path.expanduser().resolve()
    if output_path.exists() and not overwrite:
        raise FileExistsError(
            f"PPTX output already exists: {output_path}; pass --overwrite to replace it"
        )
    if output_path.exists() and overwrite:
        backup_existing_output(output_path, (backup_dir or output_path.parent))
    exporter = (scripts_dir or Path(__file__).resolve().parent / "rebuild_engine") / "svg_to_pptx.py"
    result = subprocess.run(
        [sys.executable, str(exporter), str(project_path), "--output", str(output_path)],
        check=False,
    )
    if result.returncode != 0:
        raise RuntimeError(f"svg_to_pptx failed with exit code {result.returncode}")
    if not output_path.is_file():
        raise FileNotFoundError(f"No PPTX produced at requested path: {output_path}")
    write_export_pointer(project_path, output_path)
    return output_path


__all__ = ["backup_existing_output", "run_svg_export", "write_export_pointer"]
