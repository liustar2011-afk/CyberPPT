"""Prompt-first orchestration for model-assisted Stage 1 candidates."""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import asdict
from pathlib import Path
from typing import Any

from cyberppt.commands.analysis_expression_gate import GATE_ORDER, stage_analysis_artifact
from scripts.dual_image_overlay.rebuild_engine.codex_oauth_image import run_codex_text

from cyberppt.phase1.artifacts import (
    Phase1Run,
    append_phase1_ledger_records,
    phase1_paths,
    sha256_file,
    write_phase1_run,
)
from cyberppt.phase1.grounding import ground_gate_output, ground_source_analysis
from cyberppt.phase1.prompts import build_gate_prompt, build_source_analysis_prompt
from cyberppt.phase1.renderers import render_gate_output, render_source_analysis
from cyberppt.phase1.schemas import parse_gate_output, parse_source_analysis_output
from cyberppt.phase1.source_bundle import (
    SourceBundle,
    SourceChunk,
    SourceUnit,
    build_source_bundle,
    write_source_bundle,
)


ROOT = Path(__file__).resolve().parents[2]
REFERENCE_FILES = {
    "source_analysis": ROOT / "references/source-analysis.md",
    "storyline": ROOT / "references/storyline.md",
    "internal_reporting": ROOT / "references/internal-reporting-style.md",
}
MODEL_INSTRUCTIONS = (
    "You are a precise CyberPPT internal-reporting analysis assistant. "
    "Return only valid JSON when requested. Do not add facts, numbers, sources, or external knowledge."
)
_EVIDENCE_ID_RE = re.compile(r"(?<![A-Za-z0-9])E\d+(?![A-Za-z0-9])", re.IGNORECASE)


def _read_references() -> dict[str, str]:
    return {name: path.read_text(encoding="utf-8-sig") for name, path in REFERENCE_FILES.items()}


def _sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _approved_artifact(project: Path, gate: str) -> tuple[Path, str]:
    approval = project / "workbench/analysis_expression" / f"{gate}.approved.json"
    if not approval.is_file():
        raise ValueError(f"approved {gate} is required")
    record = json.loads(approval.read_text(encoding="utf-8"))
    artifact = Path(str(record.get("artifact", ""))).expanduser().resolve()
    if not artifact.is_file():
        raise ValueError(f"approved {gate} artifact is missing: {artifact}")
    if sha256_file(artifact) != record.get("source_sha256"):
        raise ValueError(f"approved {gate} is stale")
    return artifact, artifact.read_text(encoding="utf-8")


def _dependency_hashes(paths: list[Path]) -> dict[str, str]:
    return {str(path.expanduser().resolve()): sha256_file(path) for path in paths if path.is_file()}


def _assert_dependencies_current(run: dict[str, Any]) -> None:
    for raw_path, expected in dict(run.get("dependency_hashes", {})).items():
        path = Path(raw_path).expanduser().resolve()
        if not path.is_file() or sha256_file(path) != expected:
            raise ValueError(f"dependency is stale: {path}")


def _load_source_bundle(path: Path) -> SourceBundle:
    payload = json.loads(path.read_text(encoding="utf-8"))
    units = tuple(SourceUnit(**{**item, "numbers": tuple(item.get("numbers", []))}) for item in payload["units"])
    chunks = tuple(SourceChunk(**{**item, "unit_ids": tuple(item.get("unit_ids", []))}) for item in payload["chunks"])
    return SourceBundle(payload["source_path"], payload["source_sha256"], units, chunks)


def _run_payload(paths: Any) -> dict[str, Any]:
    return json.loads(paths.run_manifest.read_text(encoding="utf-8"))


def _default_options(gate: str, payload: dict[str, Any] | None = None) -> tuple[str, list[dict[str, str]]]:
    if gate == "reporting_direction" and payload:
        return str(payload["recommendation"]), [
            {"id": str(item["id"]), "label": str(item.get("label", item["id"]))} for item in payload["options"]
        ]
    return f"confirm_{gate}", [
        {"id": f"confirm_{gate}", "label": "确认当前方案"},
        {"id": f"revise_{gate}", "label": "修改当前方案"},
    ]


def prepare_phase1_prompt(project: Path, gate: str, input_path: Path | None = None) -> dict[str, object]:
    root = project.expanduser().resolve()
    paths = phase1_paths(root, gate)
    references = _read_references()
    dependencies: list[Path] = list(REFERENCE_FILES.values())
    source_path: Path | None = None
    if gate == "source_analysis":
        if input_path is None:
            raise ValueError("source_analysis preparation requires --input source extract")
        source_path = input_path.expanduser().resolve()
        bundle = build_source_bundle(source_path)
        write_source_bundle(bundle, paths)
        prompt = build_source_analysis_prompt(bundle, references)
        dependencies.extend([source_path, paths.source_bundle_json])
    else:
        gate_index = GATE_ORDER.index(gate)
        approved: dict[str, str] = {}
        for predecessor in GATE_ORDER[:gate_index]:
            artifact, text = _approved_artifact(root, predecessor)
            approved[predecessor] = text
            dependencies.append(artifact)
        prompt = build_gate_prompt(gate, approved, approved.get("source_analysis", ""), references)
    paths.prompt.write_text(prompt, encoding="utf-8")
    run = Phase1Run(
        gate=gate,
        status="prompt_ready",
        prompt_path=str(paths.prompt),
        prompt_sha256=sha256_file(paths.prompt),
        dependency_hashes=_dependency_hashes(dependencies),
        input_path=str(source_path) if source_path else None,
    )
    run_path = write_phase1_run(run)
    append_phase1_ledger_records(
        root,
        [
            {
                "stage": "01-analysis",
                "page": None,
                "path": str(paths.prompt),
                "status": "prompt_ready",
                "depends_on": [str(path) for path in dependencies],
                "supersedes": [],
                "resume_command": f"python3 -m cyberppt phase1 generate {root} --gate {gate}",
                "sha256": sha256_file(paths.prompt),
            },
            {
                "stage": "01-analysis",
                "page": None,
                "path": str(run_path),
                "status": "generated",
                "depends_on": [str(paths.prompt)],
                "supersedes": [],
                "resume_command": f"python3 -m cyberppt phase1 generate {root} --gate {gate}",
                "sha256": sha256_file(run_path),
            },
        ],
    )
    return {"status": "prompt_ready", "gate": gate, "prompt": str(paths.prompt), "run": str(run_path)}


def _write_grounding_report(path: Path, report: Any) -> None:
    payload = {"schema": "cyberppt.phase1_grounding.v1", **asdict(report)}
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _update_run(run: dict[str, Any], **updates: Any) -> None:
    run.update(updates)
    path = Path(str(run["prompt_path"])).parent.parent / "run.json"
    path.write_text(json.dumps(run, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def generate_phase1_candidate(project: Path, gate: str, model: str | None = None, dry_run: bool = False) -> dict[str, object]:
    root = project.expanduser().resolve()
    paths = phase1_paths(root, gate)
    if not paths.prompt.is_file() or not paths.run_manifest.is_file():
        raise ValueError(f"{gate} prompt is not prepared; run phase1 prepare first")
    run = _run_payload(paths)
    _assert_dependencies_current(run)
    prompt = paths.prompt.read_text(encoding="utf-8")
    prompt_hash = sha256_file(paths.prompt)
    try:
        raw = run_codex_text(prompt=prompt, instructions=MODEL_INSTRUCTIONS, model=model, dry_run=dry_run)
        paths.raw_output.write_text(raw.strip() + "\n", encoding="utf-8")
        if dry_run:
            _update_run(run, status="dry_run", prompt_sha256=prompt_hash, model=model, raw_output_path=str(paths.raw_output))
            return {"status": "dry_run", "gate": gate, "raw_output": str(paths.raw_output)}
        if gate == "source_analysis":
            draft = parse_source_analysis_output(raw)
            bundle = _load_source_bundle(paths.source_bundle_json)
            report = ground_source_analysis(draft, bundle)
            candidate_text = render_source_analysis(draft, report)
            recommendation, options = _default_options(gate)
        else:
            draft = parse_gate_output(gate, raw)
            source_analysis_text = _approved_artifact(root, "source_analysis")[1]
            evidence_ids = {value.upper() for value in _EVIDENCE_ID_RE.findall(source_analysis_text)}
            report = ground_gate_output(gate, draft, evidence_ids)
            candidate_text = render_gate_output(gate, draft)
            recommendation, options = _default_options(gate, draft.payload)
        _write_grounding_report(paths.grounding_report, report)
        paths.candidate.write_text(candidate_text, encoding="utf-8")
        status = "candidate_ready" if not report.blocking else "grounding_failed"
        _update_run(
            run,
            status=status,
            prompt_sha256=prompt_hash,
            model=model,
            raw_output_path=str(paths.raw_output),
            candidate_path=str(paths.candidate),
            grounding_report_path=str(paths.grounding_report),
            recommendation=recommendation,
            options=options,
            candidate_sha256=sha256_file(paths.candidate),
        )
        append_phase1_ledger_records(
            root,
            [
                {
                    "stage": "01-analysis",
                    "page": None,
                    "path": str(paths.raw_output),
                    "status": "generated",
                    "depends_on": [str(paths.prompt)],
                    "supersedes": [],
                    "resume_command": f"python3 -m cyberppt phase1 critique {root} --gate {gate}",
                    "sha256": sha256_file(paths.raw_output),
                    "generator": {"model": model, "prompt": str(paths.prompt), "prompt_sha256": prompt_hash},
                },
                {
                    "stage": "01-analysis",
                    "page": None,
                    "path": str(paths.candidate),
                    "status": status,
                    "depends_on": [str(paths.raw_output), str(paths.grounding_report)],
                    "supersedes": [],
                    "resume_command": f"python3 -m cyberppt phase1 stage {root} --gate {gate}",
                    "sha256": sha256_file(paths.candidate),
                    "generator": {"model": model, "prompt": str(paths.prompt), "prompt_sha256": prompt_hash},
                },
            ],
        )
        return {
            "status": status,
            "gate": gate,
            "prompt": str(paths.prompt),
            "raw_output": str(paths.raw_output),
            "candidate": str(paths.candidate),
            "grounding_report": str(paths.grounding_report),
            "prompt_sha256": prompt_hash,
            "recommendation": recommendation,
            "options": options,
        }
    except Exception as exc:
        status = "model_failed" if not paths.raw_output.exists() else "parse_failed"
        _update_run(run, status=status, prompt_sha256=prompt_hash, model=model, error=str(exc))
        raise


def stage_phase1_candidate(
    project: Path,
    gate: str,
    recommendation: str,
    options: list[dict[str, object]],
    question: str | None = None,
) -> Path:
    root = project.expanduser().resolve()
    paths = phase1_paths(root, gate)
    if not paths.run_manifest.is_file():
        raise ValueError(f"{gate} run is missing")
    run = _run_payload(paths)
    _assert_dependencies_current(run)
    if run.get("status") != "candidate_ready":
        raise ValueError(f"{gate} candidate is not ready: {run.get('status')}")
    if not paths.candidate.is_file() or sha256_file(paths.candidate) != run.get("candidate_sha256"):
        raise ValueError(f"{gate} candidate is stale")
    qa = json.loads(paths.grounding_report.read_text(encoding="utf-8"))
    if qa.get("blocking"):
        raise ValueError(f"{gate} deterministic grounding failed")
    return stage_analysis_artifact(
        root,
        gate,
        paths.candidate.read_text(encoding="utf-8"),
        recommendation,
        options,
        question,
    )


def get_phase1_status(project: Path) -> dict[str, object]:
    root = project.expanduser().resolve()
    gates: dict[str, object] = {}
    for gate in GATE_ORDER:
        paths = phase1_paths(root, gate)
        if not paths.run_manifest.is_file():
            gates[gate] = {"status": "not_prepared"}
            continue
        run = _run_payload(paths)
        gates[gate] = {"status": run.get("status"), "run": str(paths.run_manifest), "candidate": str(paths.candidate) if paths.candidate.exists() else None}
    return {"schema": "cyberppt.phase1_status.v1", "project": str(root), "gates": gates}
