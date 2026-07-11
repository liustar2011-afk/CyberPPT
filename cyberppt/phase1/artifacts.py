"""Paths and provenance records for model-assisted Stage 1 runs."""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from cyberppt.commands.analysis_expression_gate import GATE_ORDER


MODEL_RUN_ROOT = Path("workbench/stages/01-analysis/model-runs")


@dataclass(frozen=True)
class Phase1Paths:
    root: Path
    source_bundle_json: Path
    source_bundle_markdown: Path
    chunks_dir: Path
    prompt: Path
    raw_output: Path
    candidate: Path
    grounding_report: Path
    critic_prompt: Path
    critic_raw: Path
    critic_report: Path
    run_manifest: Path


@dataclass(frozen=True)
class Phase1Run:
    gate: str
    status: str
    prompt_path: str
    prompt_sha256: str
    dependency_hashes: dict[str, str]
    model: str | None = None
    raw_output_path: str | None = None
    candidate_path: str | None = None
    grounding_report_path: str | None = None
    error: str | None = None


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def phase1_paths(project: Path, gate: str) -> Phase1Paths:
    if gate not in GATE_ORDER:
        raise ValueError(f"unknown Stage 1 gate: {gate}")
    root = project.expanduser().resolve() / MODEL_RUN_ROOT / gate
    root.mkdir(parents=True, exist_ok=True)
    chunks_dir = root / "chunks"
    chunks_dir.mkdir(parents=True, exist_ok=True)
    for directory in (root / "prompts", root / "llm", root / "candidates", root / "qa"):
        directory.mkdir(parents=True, exist_ok=True)
    return Phase1Paths(
        root=root,
        source_bundle_json=root / "source_bundle.json",
        source_bundle_markdown=root / "source_bundle.md",
        chunks_dir=chunks_dir,
        prompt=root / "prompts" / f"{gate}_prompt.md",
        raw_output=root / "llm" / f"{gate}_raw.json",
        candidate=root / "candidates" / f"{gate}.md",
        grounding_report=root / "qa" / f"{gate}_grounding.json",
        critic_prompt=root / "qa" / f"{gate}_critic_prompt.md",
        critic_raw=root / "qa" / f"{gate}_critic_raw.json",
        critic_report=root / "qa" / f"{gate}_critic.json",
        run_manifest=root / "run.json",
    )


def sha256_file(path: Path) -> str:
    return _sha256(path.expanduser().resolve())


def write_phase1_run(run: Phase1Run) -> Path:
    prompt_path = Path(run.prompt_path).expanduser().resolve()
    target = prompt_path.parent.parent / "run.json"
    project_root = next(
        (parent.parent for parent in prompt_path.parents if parent.name == "workbench"),
        prompt_path.parent,
    )
    payload: dict[str, Any] = {
        "schema": "cyberppt.phase1_run.v1",
        **asdict(run),
        "created_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "resume_command": f"python3 -m cyberppt phase1 generate {project_root}",
    }
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return target


def append_phase1_ledger_records(project: Path, records: list[dict[str, object]]) -> Path:
    path = project.expanduser().resolve() / "workbench" / "artifact-ledger.json"
    if path.exists():
        ledger = json.loads(path.read_text(encoding="utf-8"))
    else:
        ledger = {"schema": "cyberppt.artifact_ledger.v1", "artifacts": []}
    artifacts = ledger.setdefault("artifacts", [])
    existing = {str(item.get("path")): item for item in artifacts if isinstance(item, dict)}
    for record in records:
        existing[str(record["path"])] = dict(record)
    ledger["artifacts"] = list(existing.values())
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(ledger, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return path
