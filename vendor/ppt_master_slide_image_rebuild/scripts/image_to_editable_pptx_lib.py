#!/usr/bin/env python3
"""
Slide-image-rebuild one-click scaffold / QA orchestration helpers.
"""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

_SCRIPTS_DIR = Path(__file__).resolve().parent
if str(_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_DIR))

try:
    from project_manager import ProjectManager
except ImportError:  # pragma: no cover
    from scripts.project_manager import ProjectManager  # type: ignore

try:
    from slide_image_rebuild_manifest_lib import (
        default_text_layout_policy,
        resolve_text_granularity,
        resolve_text_layout_policy,
    )
except ImportError:  # pragma: no cover
    from scripts.slide_image_rebuild_manifest_lib import (  # type: ignore
        default_text_layout_policy,
        resolve_text_granularity,
        resolve_text_layout_policy,
    )


STAGE_SCAFFOLD = "scaffold"
STAGE_QA = "qa"
STAGE_FULL = "full"
ALLOWED_STAGES = frozenset({STAGE_SCAFFOLD, STAGE_QA, STAGE_FULL})

STRICT_PATH_DOC = "workflows/strict-path.md"


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


try:  # shared helper; see scripts/json_io.py
    from json_io import load_json
except ImportError:  # pragma: no cover - package-context import
    from scripts.json_io import load_json  # type: ignore


@dataclass
class StepResult:
    step_id: str
    command: list[str]
    returncode: int
    stdout: str = ""
    stderr: str = ""
    skipped: bool = False

    @property
    def ok(self) -> bool:
        return self.skipped or self.returncode == 0


@dataclass
class OrchestrationResult:
    valid: bool
    stage: str
    project: Path
    steps: list[StepResult] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    next_actions: list[str] = field(default_factory=list)
    artifacts: dict[str, str] = field(default_factory=dict)
    trace_path: str | None = None

    def as_dict(self) -> dict[str, Any]:
        return {
            "valid": self.valid,
            "stage": self.stage,
            "project": str(self.project),
            "errors": self.errors,
            "warnings": self.warnings,
            "next_actions": self.next_actions,
            "artifacts": self.artifacts,
            "trace_path": self.trace_path,
            "steps": [
                {
                    "step_id": step.step_id,
                    "command": step.command,
                    "returncode": step.returncode,
                    "skipped": step.skipped,
                    "ok": step.ok,
                }
                for step in self.steps
            ],
        }


@dataclass(frozen=True)
class OrchestrationConfig:
    image: Path
    name: str
    canvas_format: str
    text_density: str
    projects_dir: Path
    repo_root: Path
    scripts_dir: Path
    python_executable: str
    stage: str = STAGE_SCAFFOLD
    preprocess: bool = True
    precise_lock: bool = True
    aggregate_final: bool = True
    render: bool = True
    reference_threshold: float = 58.0


def repo_root_from_scripts(scripts_dir: Path) -> Path:
    return scripts_dir.parent


def build_manifest(config: OrchestrationConfig, reference_image: str) -> dict[str, Any]:
    text_resolved = resolve_text_granularity({
        "text_density": config.text_density,
        "pptx_export_mode": "hifi",
    })
    export_mode = "hifi" if text_resolved.force_hifi_export else "hifi"
    manifest: dict[str, Any] = {
        "workflow": "slide-image-rebuild",
        "format": config.canvas_format,
        "rebuild_mode": "vector-hifi",
        "pptx_export_mode": export_mode,
        "rebuild_quality_mode": "balanced",
        "execution_profile": "chatgpt_precise_rebuild",
        "text_density": config.text_density,
        "qa": {"preview_render_backend": "cairo"},
        "pages": [
            {
                "page_id": "P01",
                "reference_image": reference_image,
                "page_dir": ".",
                "content_source": "image_text_draft",
                "notes_style": "formal_briefing",
            },
        ],
    }
    if config.text_density == "dense_formal_cn":
        manifest["text_layout_policy"] = default_text_layout_policy(text_density=config.text_density)
    policy_resolved = resolve_text_layout_policy(manifest)
    if policy_resolved.errors:
        raise ValueError("; ".join(policy_resolved.errors))
    return manifest


def scaffold_text_region_map() -> dict[str, Any]:
    return {
        "workflow": "slide-image-rebuild",
        "version": "1.0",
        "draft": True,
        "pages": [
            {
                "page_id": "01",
                "regions": [],
            },
        ],
    }


def scaffold_content_mapping(layout: dict[str, Any]) -> dict[str, Any]:
    layout_type = layout.get("layout_type")
    if not isinstance(layout_type, str) or not layout_type.strip():
        layout_type = "custom"

    title = "参考页标题"
    for key in ("page_title", "title"):
        value = layout.get(key)
        if isinstance(value, str) and value.strip():
            title = value.strip()
            break

    modules: list[dict[str, Any]] = []
    for zone in layout.get("zones", []):
        if not isinstance(zone, dict):
            continue
        zone_id = zone.get("id")
        if not isinstance(zone_id, str) or not zone_id.strip():
            continue
        label = zone.get("label") or zone.get("title") or zone_id
        modules.append({
            "zone_id": zone_id,
            "title": str(label),
            "body": ["待完善正文"],
        })

    main_chain_labels: list[str] = []
    nodes = layout.get("main_chain", {}).get("nodes", [])
    if isinstance(nodes, list):
        for node in nodes:
            if isinstance(node, dict):
                label = node.get("label")
                if isinstance(label, str) and label.strip():
                    main_chain_labels.append(label.strip())

    renderable: dict[str, Any] = {
        "title": title,
        "modules": modules,
    }
    if main_chain_labels:
        renderable["main_chain_labels"] = main_chain_labels

    return {
        "version": "1.0",
        "page_role": "slide_image_rebuild_draft",
        "layout_type": layout_type,
        "renderable_content": renderable,
        "render_contract": {
            "render_only": ["renderable_content"],
            "never_render": ["qa_checklist", "prompt", "placeholder"],
        },
    }


def _run_command(
    config: OrchestrationConfig,
    step_id: str,
    script_name: str,
    args: list[str],
    *,
    runner: Callable[[list[str]], subprocess.CompletedProcess[str]] | None = None,
) -> StepResult:
    command = [config.python_executable, str(config.scripts_dir / script_name), *args]
    if runner is not None:
        completed = runner(command)
    else:
        completed = subprocess.run(command, text=True, capture_output=True, check=False)
    return StepResult(
        step_id=step_id,
        command=command,
        returncode=completed.returncode,
        stdout=completed.stdout,
        stderr=completed.stderr,
    )


def init_project(config: OrchestrationConfig) -> Path:
    manager = ProjectManager(base_dir=str(config.projects_dir))
    project_path = Path(
        manager.init_project(config.name, config.canvas_format, base_dir=str(config.projects_dir)),
    )
    return project_path.resolve()


def copy_reference_image(config: OrchestrationConfig, project: Path) -> str:
    images_dir = project / "images"
    images_dir.mkdir(parents=True, exist_ok=True)
    suffix = config.image.suffix.lower() or ".png"
    destination = images_dir / f"reference_layout{suffix}"
    shutil.copy2(config.image, destination)
    return str(destination.relative_to(project))


def has_svg_output(project: Path) -> bool:
    for folder in ("svg_output", "svg_final"):
        svg_dir = project / folder
        if svg_dir.is_dir() and any(svg_dir.glob("*.svg")):
            return True
    return False


def write_conversion_trace(project: Path, result: OrchestrationResult) -> Path:
    trace_dir = project / "exports" / "qa"
    trace_dir.mkdir(parents=True, exist_ok=True)
    trace_path = trace_dir / "image_to_editable_pptx_trace.json"
    payload = result.as_dict()
    payload["generated_at"] = utc_now()
    trace_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return trace_path


def aggregate_final_exports(project: Path) -> dict[str, str]:
    final_dir = project / "exports" / "final"
    final_dir.mkdir(parents=True, exist_ok=True)
    artifacts: dict[str, str] = {}

    pptx_candidates = sorted(
        (path for path in project.glob("exports/*.pptx") if not path.name.startswith("~$")),
        key=lambda path: path.stat().st_mtime,
        reverse=True,
    )
    if pptx_candidates:
        target = final_dir / "presentation.pptx"
        _link_or_copy(pptx_candidates[0], target)
        artifacts["presentation.pptx"] = str(target.relative_to(project))

    preview_candidates = sorted((project / "exports" / "preview_qa").glob("*.preview.png"))
    if preview_candidates:
        target = final_dir / "preview.png"
        _link_or_copy(preview_candidates[0], target)
        artifacts["preview.png"] = str(target.relative_to(project))

    for rel_src, rel_dst in (
        ("exports/qa/strict_run_summary.json", "qa_summary.json"),
        ("exports/pptx/conversion_trace.json", "conversion_trace.json"),
    ):
        source = project / rel_src
        if source.is_file():
            target = final_dir / rel_dst
            _link_or_copy(source, target)
            artifacts[rel_dst] = str(target.relative_to(project))

    return artifacts


def _link_or_copy(source: Path, target: Path) -> None:
    if target.exists() or target.is_symlink():
        target.unlink()
    try:
        target.symlink_to(source.resolve())
    except OSError:
        shutil.copy2(source, target)


def run_scaffold(
    config: OrchestrationConfig,
    *,
    runner: Callable[[list[str]], subprocess.CompletedProcess[str]] | None = None,
) -> OrchestrationResult:
    result = OrchestrationResult(valid=True, stage=STAGE_SCAFFOLD, project=config.projects_dir)

    try:
        project = init_project(config)
    except FileExistsError as exc:
        result.valid = False
        result.errors.append(str(exc))
        return result
    except ValueError as exc:
        result.valid = False
        result.errors.append(str(exc))
        return result

    result.project = project
    reference_rel = copy_reference_image(config, project)
    manifest_path = project / "slide_image_rebuild_manifest.json"
    manifest_path.write_text(
        json.dumps(build_manifest(config, reference_rel), ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    result.artifacts["manifest"] = str(manifest_path.relative_to(project))
    result.artifacts["reference_image"] = reference_rel

    if config.preprocess:
        step = _run_command(
            config,
            "preprocess_reference_image",
            "preprocess_reference_image.py",
            [str(project / reference_rel), "--project", str(project)],
            runner=runner,
        )
        result.steps.append(step)
        if not step.ok:
            result.warnings.append("preprocess_reference_image failed; continuing with source image.")

    extract_args = [
        str(project / reference_rel),
        "--project",
        str(project),
        "--copy-image",
        "--rebuild2",
        "--output",
        str(project / "layout_reference.json"),
    ]
    normalized = project / "images" / "reference_layout.normalized.png"
    if normalized.is_file():
        extract_args.extend(["--normalized-image", str(normalized)])

    step = _run_command(
        config,
        "extract_layout_reference",
        "extract_layout_reference_from_image.py",
        extract_args,
        runner=runner,
    )
    result.steps.append(step)
    if not step.ok:
        result.valid = False
        result.errors.append("extract_layout_reference_from_image.py failed.")
        trace = write_conversion_trace(project, result)
        result.trace_path = str(trace.relative_to(project))
        return result

    layout_path = project / "layout_reference.json"
    layout = load_json(layout_path)
    content_mapping_path = project / "content_mapping.json"
    content_mapping_path.write_text(
        json.dumps(scaffold_content_mapping(layout), ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    text_region_path = project / "text_region_map.json"
    text_region_path.write_text(
        json.dumps(scaffold_text_region_map(), ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    result.artifacts["layout_reference"] = str(layout_path.relative_to(project))
    result.artifacts["content_mapping"] = str(content_mapping_path.relative_to(project))
    result.artifacts["text_region_map"] = str(text_region_path.relative_to(project))

    validate_step = _run_command(
        config,
        "validate_layout_reference",
        "validate_layout_reference.py",
        [str(layout_path), "--rebuild2", "--allow-draft", "--mapping", str(content_mapping_path)],
        runner=runner,
    )
    result.steps.append(validate_step)
    if not validate_step.ok:
        result.warnings.append(
            "layout_reference.json is still a draft; complete zones in Phase A before export.",
        )

    for step_id, script_name, args in (
        (
            "layout_reference_to_design_spec",
            "layout_reference_to_design_spec.py",
            [str(project), "--write-design-spec"],
        ),
        ("layout_reference_to_svg_plan", "layout_reference_to_svg_plan.py", [str(project)]),
    ):
        step = _run_command(config, step_id, script_name, args, runner=runner)
        result.steps.append(step)
        if not step.ok:
            result.valid = False
            result.errors.append(f"{script_name} failed.")

    result.next_actions.extend([
        f"Complete layout_reference.json zones and text_region_map.json (see {STRICT_PATH_DOC} Phase A).",
        "Phase B: build svg_output/*.svg with a UTF-8-safe writer (_gen.py) or svg_editor.",
        (
            "Phase C: scripts/repo_python.sh "
            "scripts/image_to_editable_pptx.py "
            f"--project {project} --stage qa"
        ),
    ])
    trace = write_conversion_trace(project, result)
    result.trace_path = str(trace.relative_to(project))
    return result


def _invalidate_stale_previews(project: Path) -> None:
    preview_dir = project / "exports" / "preview_qa"
    if not preview_dir.is_dir():
        return
    svg_times: list[float] = []
    for folder in ("svg_output", "svg_final"):
        svg_dir = project / folder
        if svg_dir.is_dir():
            svg_times.extend(path.stat().st_mtime for path in svg_dir.glob("*.svg"))
    if not svg_times:
        return
    newest_svg = max(svg_times)
    for preview in preview_dir.glob("*.preview.png"):
        if preview.stat().st_mtime < newest_svg:
            preview.unlink(missing_ok=True)


def _clear_preview_pngs(project: Path) -> None:
    """Remove cached preview PNGs so strict runner must re-render."""
    preview_dir = project / "exports" / "preview_qa"
    if not preview_dir.is_dir():
        return
    for preview in preview_dir.glob("*.preview.png"):
        preview.unlink(missing_ok=True)


def run_qa(
    config: OrchestrationConfig,
    project: Path,
    *,
    runner: Callable[[list[str]], subprocess.CompletedProcess[str]] | None = None,
) -> OrchestrationResult:
    result = OrchestrationResult(valid=True, stage=STAGE_QA, project=project.resolve())
    _invalidate_stale_previews(project)
    if config.render:
        # Strict runner owns preview render (step 5.2); drop cached PNGs so icon
        # contract never reads a stale or mismatched pre-render.
        _clear_preview_pngs(project)
    if not has_svg_output(project):
        result.valid = False
        result.errors.append("svg_output/ is empty; complete Phase B before --stage qa.")
        result.next_actions.append(f"See {STRICT_PATH_DOC} Phase B.")
        trace = write_conversion_trace(project, result)
        result.trace_path = str(trace.relative_to(project))
        return result

    strict_args = [
        "--project",
        str(project),
        "--stage",
        "full",
        "--export-mode",
        "hifi",
        "--agent-summary",
    ]
    if config.precise_lock:
        strict_args.append("--precise-lock")
    if config.render:
        strict_args.append("--render")
    strict_args.extend(["--reference-threshold", str(config.reference_threshold)])

    step = _run_command(
        config,
        "run_slide_image_rebuild_strict",
        "run_slide_image_rebuild_strict.py",
        strict_args,
        runner=runner,
    )
    result.steps.append(step)
    if not step.ok:
        result.valid = False
        result.errors.append("strict runner failed; read exports/qa/strict_run_summary.json.")

    summary_path = project / "exports" / "qa" / "strict_run_summary.json"
    if summary_path.is_file():
        summary = load_json(summary_path)
        result.artifacts["strict_run_summary"] = str(summary_path.relative_to(project))
        if summary.get("valid") is not True:
            result.valid = False
            blocking = summary.get("blocking_errors", [])
            if isinstance(blocking, list):
                result.errors.extend(str(item) for item in blocking[:5])
            resume = summary.get("next_action", {}).get("resume_command")
            if isinstance(resume, str) and resume.strip():
                result.next_actions.append(resume.strip())
    elif step.ok:
        result.valid = False
        result.errors.append("strict_run_summary.json was not written.")

    if config.aggregate_final and result.valid:
        result.artifacts.update(aggregate_final_exports(project))

    trace = write_conversion_trace(project, result)
    result.trace_path = str(trace.relative_to(project))
    return result


def run_orchestration(
    config: OrchestrationConfig,
    *,
    runner: Callable[[list[str]], subprocess.CompletedProcess[str]] | None = None,
) -> OrchestrationResult:
    if config.stage == STAGE_SCAFFOLD:
        return run_scaffold(config, runner=runner)

    if config.stage == STAGE_QA:
        if not config.projects_dir.is_dir():
            return OrchestrationResult(
                valid=False,
                stage=STAGE_QA,
                project=config.projects_dir,
                errors=[f"Project directory not found: {config.projects_dir}"],
            )
        return run_qa(config, config.projects_dir.resolve(), runner=runner)

    scaffold_result = run_scaffold(config, runner=runner)
    if not scaffold_result.valid:
        return scaffold_result
    if not has_svg_output(scaffold_result.project):
        scaffold_result.valid = False
        scaffold_result.stage = STAGE_FULL
        scaffold_result.errors.append(
            "Phase B SVG not found after scaffold; --stage full stops before QA.",
        )
        scaffold_result.next_actions.append(
            "Build svg_output/*.svg, then re-run with --stage qa or --stage full.",
        )
        return scaffold_result

    qa_result = run_qa(config, scaffold_result.project, runner=runner)
    qa_result.steps = scaffold_result.steps + qa_result.steps
    qa_result.warnings = scaffold_result.warnings + qa_result.warnings
    qa_result.stage = STAGE_FULL
    return qa_result
