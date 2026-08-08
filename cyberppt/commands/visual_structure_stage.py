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
from cyberppt.semantic_digest import script_semantic_digest


SKILL_RELATIVE = Path("vendor/skills/ppt-visual-structure-designer")
VISUAL_FILES = {
    "design_input": Path("visual/visual-design-input.json"),
    "spec_json": Path("visual/deck-visual-spec.json"),
    "spec_markdown": Path("visual/script-visual-structure.md"),
    "generation_prompts": Path("visual/generation-prompts.md"),
    "validation": Path("visual/validation-report.json"),
}


def _write_visual_design_input(project: Path, handoff: Path) -> Path:
    payload = _read_json(handoff)
    source_pages = payload.get("pages") or []
    content_pages = [page for page in source_pages if page.get("render_role") == "content"]
    pages: list[dict[str, Any]] = []
    for index, page in enumerate(content_pages):
        visual = page.get("stage02_visual_input") or {}
        previous_page = content_pages[index - 1] if index else None
        next_page = content_pages[index + 1] if index + 1 < len(content_pages) else None
        pages.append(
            {
                "page_id": page.get("page_id"),
                "page_number": page.get("page_number"),
                "page_title": page.get("title"),
                "argument_role": page.get("argument_role"),
                "page_mission": page.get("page_mission"),
                "core_judgment": page.get("core_message"),
                "semantic_context": page.get("full_prose"),
                "locked_on_screen_text": page.get("onscreen_text"),
                "locked_on_screen_items": page.get("onscreen_items") or [],
                "upstream_relationship": visual.get("approved_stage01_visual_structure"),
                "source_refs": page.get("source_refs") or [],
                "must_not_include": page.get("must_not_include") or [],
                "body_image_canvas": visual.get("body_image_canvas"),
                "title_render_mode": visual.get("title_render_mode"),
                "subtitle_render_mode": visual.get("subtitle_render_mode"),
                "previous_content_page": (
                    {"page_id": previous_page.get("page_id"), "title": previous_page.get("title")}
                    if previous_page
                    else None
                ),
                "next_content_page": (
                    {"page_id": next_page.get("page_id"), "title": next_page.get("title")}
                    if next_page
                    else None
                ),
            }
        )
    output = project / VISUAL_FILES["design_input"]
    write_json_atomic(
        output,
        {
            "schema": "cyberppt.visual_design_input.v1",
            "source": str(handoff),
            "content_lock": "strict",
            "style_policy": "visual structure must not select or embed a visual style",
            "decision_policy": (
                "ppt-visual-structure-designer must compare at least three materially different "
                "candidates per page; deterministic keyword routing is not authoritative"
            ),
            "pages": pages,
        },
    )
    return output


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
    from cyberppt.stage02_handoff import HANDOFF_JSON, prepare_stage02_handoff

    report = prepare_stage02_handoff(project, script=script)
    if report.get("status") != "passed":
        raise ValueError("Stage 01 to Stage 02 handoff is not passed")
    handoff = project / HANDOFF_JSON
    design_input = _write_visual_design_input(project, handoff)
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
                f"- approved_script_semantic_sha256: {script_semantic_digest(script)}",
                f"- stage02_handoff: {handoff}",
                f"- visual_design_input: {design_input}",
                "- mode: workbench-handoff",
                "- content_lock: strict",
                "",
                "## Required action",
                "",
                "Automatically invoke the registered skill now. Use visual-design-input.json, derived only from stage02_handoff.json, as the visual-design interface. Do not read or reuse any existing Stage 02 visual/ or workbench/prompts/imagegen outputs as authority. Generate and compare at least three materially different candidates per content page; deterministic keyword matching must not choose the final visual intent or carrier. Preserve the approved page set and locked text, and write:",
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
    from cyberppt.stage02_handoff import HANDOFF_JSON, load_stage02_handoff

    handoff = load_stage02_handoff(project, required=False)
    handoff_path = project / HANDOFF_JSON
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
        (
            previous_report.get("script_semantic_sha256") == script_semantic_digest(script)
            if previous_report.get("script_semantic_sha256")
            else previous_report.get("script_sha256") == _sha256(script)
        )
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
        "script_semantic_sha256": script_semantic_digest(script),
        "stage02_handoff": str(handoff_path) if handoff is not None else None,
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
        VISUAL_FILES["design_input"],
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
    from cyberppt.stage02_handoff import HANDOFF_JSON, load_stage02_handoff

    handoff = load_stage02_handoff(project, required=False)
    handoff_path = project / HANDOFF_JSON
    if report.get("schema") != "cyberppt.visual_structure_stage.v1" or report.get("status") != "passed":
        raise ValueError("visual structure stage is not passed; rerun visual-structure-audit")
    # A completed visual-structure package is reusable across downstream
    # style-lock refreshes. Stage 02 style changes must not force the visual
    # designer workflow to run again; the current approved script is already
    # protected by the Stage 01 approval gate above this check.
    for key in ("spec_json", "spec_markdown", "generation_prompts"):
        path = project / VISUAL_FILES[key]
        if not path.is_file() or report.get("artifact_sha256", {}).get(key) != _sha256(path):
            raise ValueError(f"visual structure artifact is missing or changed: {path}")
    return report_path
