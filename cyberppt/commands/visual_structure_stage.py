"""Register and gate the visual-structure-designer stage."""

from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from cyberppt.artifact_ledger import append_artifacts, write_json_atomic


SKILL_RELATIVE = Path("vendor/skills/ppt-visual-structure-designer")
VISUAL_FILES = {
    "spec_json": Path("visual/deck-visual-spec.json"),
    "spec_markdown": Path("visual/script-visual-structure.md"),
    "generation_prompts": Path("visual/generation-prompts.md"),
    "validation": Path("visual/validation-report.json"),
}


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _read_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(value, dict):
        raise ValueError(f"JSON root must be an object: {path}")
    return value


def visual_structure_required(project: Path) -> bool:
    manifest = project / "manifest.yml"
    if not manifest.is_file():
        return False
    text = manifest.read_text(encoding="utf-8-sig")
    return "visual_structure_designer: required" in text


def prepare_visual_structure_stage(project: Path, script: Path) -> Path:
    project = project.expanduser().resolve()
    script = script.expanduser().resolve()
    from cyberppt.stage01_controls import assert_stage01_script_approval

    assert_stage01_script_approval(project, script)
    skill = (Path(__file__).resolve().parents[2] / SKILL_RELATIVE / "SKILL.md").resolve()
    if not skill.is_file():
        raise FileNotFoundError(f"registered visual structure skill is missing: {skill}")
    output = project / "visual" / "skill-invocation.md"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        "\n".join(
            [
                "# PPT Visual Structure Designer Invocation",
                "",
                "- skill: ppt-visual-structure-designer",
                f"- skill_path: {skill}",
                f"- skill_sha256: {_sha256(skill)}",
                f"- approved_script: {script}",
                f"- approved_script_sha256: {_sha256(script)}",
                "- mode: workbench-handoff",
                "- content_lock: strict",
                "",
                "## Required action",
                "",
                "Automatically invoke the registered skill now. Read its required references, preserve the approved page set and locked text, and write:",
                "",
                "- `visual/deck-visual-spec.json`",
                "- `visual/script-visual-structure.md`",
                "- `visual/generation-prompts.md`",
                "- `visual/validation-report.json`",
                "",
                "Do not select a visual style, generate images, SVG, HTML, or PPTX in this stage.",
                "",
            ]
        ),
        encoding="utf-8",
    )
    return output


def run_visual_structure_audit(project: Path, script: Path) -> tuple[int, dict[str, Any]]:
    project = project.expanduser().resolve()
    script = script.expanduser().resolve()
    skill_root = (Path(__file__).resolve().parents[2] / SKILL_RELATIVE).resolve()
    validator = skill_root / "scripts" / "validate_visual_spec.py"
    prompt_builder = skill_root / "scripts" / "build_generation_prompt.py"
    spec_json = project / VISUAL_FILES["spec_json"]
    spec_md = project / VISUAL_FILES["spec_markdown"]
    prompts = project / VISUAL_FILES["generation_prompts"]
    report_path = project / VISUAL_FILES["validation"]
    previous_report = _read_json(report_path) if report_path.is_file() else {}
    for path in (validator, prompt_builder, script, spec_json, spec_md):
        if not path.is_file():
            raise FileNotFoundError(f"visual structure stage artifact is missing: {path}")

    results: dict[str, Any] = {}
    for label, path in (("markdown", spec_md), ("json", spec_json)):
        completed = subprocess.run(
            [sys.executable, str(validator), str(path), "--strict", "--json-report"],
            check=False,
            capture_output=True,
            text=True,
            encoding="utf-8",
        )
        results[label] = json.loads(completed.stdout)
        results[label]["status"] = "passed" if completed.returncode == 0 else "failed"

    current_inputs_match = (
        previous_report.get("script_sha256") == _sha256(script)
        and previous_report.get("artifact_sha256", {}).get("spec_json") == _sha256(spec_json)
        and previous_report.get("artifact_sha256", {}).get("spec_markdown") == _sha256(spec_md)
        and prompts.is_file()
        and previous_report.get("artifact_sha256", {}).get("generation_prompts") == _sha256(prompts)
    )
    if not current_inputs_match:
        subprocess.run(
            [sys.executable, str(prompt_builder), str(spec_json), "--output", str(prompts)],
            check=True,
            capture_output=True,
            text=True,
            encoding="utf-8",
        )
    passed = all(result["status"] == "passed" for result in results.values())
    report = {
        "schema": "cyberppt.visual_structure_stage.v1",
        "build_id": f"visual-{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}-{_sha256(script)[:10]}",
        "status": "passed" if passed else "failed",
        "validated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "skill": "ppt-visual-structure-designer",
        "skill_sha256": _sha256(skill_root / "SKILL.md"),
        "script": str(script),
        "script_sha256": _sha256(script),
        "artifacts": {key: str(project / value) for key, value in VISUAL_FILES.items() if key != "validation"},
        "artifact_sha256": {
            "spec_json": _sha256(spec_json),
            "spec_markdown": _sha256(spec_md),
            "generation_prompts": _sha256(prompts),
        },
        "results": results,
    }
    if isinstance(previous_report.get("semantic_review"), dict):
        report["semantic_review"] = previous_report["semantic_review"]
    write_json_atomic(report_path, report)
    _register_visual_artifacts(project, script, report_path, build_id=str(report["build_id"]))
    return (0 if passed else 1), report


def _register_visual_artifacts(
    project: Path,
    script: Path,
    report_path: Path,
    *,
    build_id: str,
) -> None:
    ledger_path = project / "workbench" / "artifact-ledger.json"
    registered_paths = [
        VISUAL_FILES["spec_json"],
        VISUAL_FILES["spec_markdown"],
        VISUAL_FILES["generation_prompts"],
        VISUAL_FILES["validation"],
    ]
    try:
        script_dependency = script.relative_to(project).as_posix()
    except ValueError:
        script_dependency = str(script)
    resume = f"python -m cyberppt visual-structure-audit {project} --script {script}"
    records: list[dict[str, Any]] = []
    status = "passed" if _read_json(report_path).get("status") == "passed" else "failed"
    for relative in registered_paths:
        path = project / relative
        records.append(
            {
                "stage": "02-visual-structure",
                "page": None,
                "path": relative.as_posix(),
                "status": status,
                "depends_on": [script_dependency],
                "resume_command": resume,
                "sha256": _sha256(path),
            }
        )
    append_artifacts(ledger_path, records, build_id=build_id)


def assert_visual_structure_ready(project: Path, script: Path) -> Path | None:
    project = project.expanduser().resolve()
    script = script.expanduser().resolve()
    if not visual_structure_required(project):
        return None
    report_path = project / VISUAL_FILES["validation"]
    if not report_path.is_file():
        raise FileNotFoundError(
            "required visual structure stage is missing; automatically invoke "
            "ppt-visual-structure-designer and run visual-structure-audit before Stage 02"
        )
    report = _read_json(report_path)
    if report.get("schema") != "cyberppt.visual_structure_stage.v1" or report.get("status") != "passed":
        raise ValueError("visual structure stage is not passed; rerun visual-structure-audit")
    if report.get("script_sha256") != _sha256(script):
        raise ValueError("visual structure stage is stale for the approved script; rerun the skill and audit")
    for key in ("spec_json", "spec_markdown", "generation_prompts"):
        path = project / VISUAL_FILES[key]
        if not path.is_file() or report.get("artifact_sha256", {}).get(key) != _sha256(path):
            raise ValueError(f"visual structure artifact is missing or changed: {path}")
    return report_path
