"""CyberPPT product command line interface."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

from cyberppt import __version__
from cyberppt.commands.assemble_final_script import assemble_final_script
from cyberppt.commands.final_script_pages import run_final_script_pages
from cyberppt.foundation_projection import project_source_truth_to_foundation
from cyberppt.foundation_authoring import prepare_script_foundation
from script_engine.contracts import validate_foundation
from scripts.image_to_pptx_runtime.quick_page_review import record_quick_page_review
from cyberppt.commands.init_project import init_project
from cyberppt.image_enhancer import enhance_image
from cyberppt.officecli import install_officecli, officecli_status
from cyberppt.commands.prepare_imagegen_send import prepare_imagegen_send
from cyberppt.commands.preview_onscreen_markdown import preview_onscreen_markdown
from cyberppt.commands.script_gate import approve_script, get_script_status, stage_script, status_as_json
from cyberppt.commands.script_runner import SCRIPT_ALIASES, run_script
from cyberppt.commands.source_truth_audit import run_source_truth_audit
from cyberppt.commands.visual_structure_stage import (
    execute_visual_structure_stage,
    prepare_visual_structure_stage,
    record_visual_structure_execution,
    run_visual_structure_audit,
)
from cyberppt.paths import ASSETS_DIR, REFERENCES_DIR, SCRIPTS_DIR, WORKFLOW_FILE
from cyberppt.project_status import build_project_status
from cyberppt.semantic_understanding import (
    prepare_semantic_understanding,
    run_semantic_understanding_audit,
)
from cyberppt.source_document_map import (
    prepare_source_context,
    prepare_source_map,
    run_source_map_audit,
)
from cyberppt.source_foundation_projection import project_source_foundation_truth
from cyberppt.stage02_handoff import (
    HANDOFF_AUDIT,
    HANDOFF_JSON,
    audit_stage02_handoff,
    prepare_stage02_handoff,
)
from cyberppt.stage01_compiler import compile_source_truth


def _warn_deprecated_compatibility_flag(name: str) -> None:
    print(
        f"warning: {name} is deprecated compatibility-only; it does not alter current gates and is planned for removal in the next major CLI revision.",
        file=sys.stderr,
    )

def _doctor() -> int:
    required_palette_samples = [
        ASSETS_DIR / "palette-samples" / f"palette-{style_id:02d}.png"
        for style_id in range(1, 9)
    ]
    checks = {
        "workflow": WORKFLOW_FILE.exists(),
        "references": REFERENCES_DIR.exists() and any(REFERENCES_DIR.glob("*.md")),
        "palette_samples": all(sample.exists() for sample in required_palette_samples),
        "scripts": all((SCRIPTS_DIR / name).exists() for name in SCRIPT_ALIASES.values()),
    }
    for name, passed in checks.items():
        print(f"{name}: {'ok' if passed else 'missing'}")
    return 0 if all(checks.values()) else 1


def _officecli_command(args: argparse.Namespace) -> int:
    try:
        if args.officecli_action == "install":
            path = install_officecli(force=args.force)
            print(json.dumps({"installed": str(path), **officecli_status()}, ensure_ascii=False, indent=2))
        else:
            print(json.dumps(officecli_status(), ensure_ascii=False, indent=2))
    except (OSError, RuntimeError) as exc:
        print(str(exc), file=sys.stderr)
        return 2
    return 0


def _init_command(args: argparse.Namespace) -> int:
    try:
        created = init_project(Path(args.path), force=args.force, profile=args.profile)
    except FileExistsError as exc:
        print(str(exc), file=sys.stderr)
        return 2
    print(f"initialized CyberPPT project: {Path(args.path).expanduser().resolve()}")
    print(f"created_or_updated: {len(created)}")
    return 0


def _project_status_command(args: argparse.Namespace) -> int:
    try:
        report = build_project_status(Path(args.project))
    except (FileNotFoundError, OSError, ValueError, json.JSONDecodeError) as exc:
        print(str(exc), file=sys.stderr)
        return 2
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 1 if report.get("status") == "blocked" else 0


def _source_truth_audit_command(args: argparse.Namespace) -> int:
    try:
        code, report = run_source_truth_audit(
            Path(args.project),
            Path(args.input),
        )
    except (FileNotFoundError, ValueError) as exc:
        print(str(exc), file=sys.stderr)
        return 2
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return code


def _project_foundation_command(args: argparse.Namespace) -> int:
    project = Path(args.project)
    input_path = Path(args.input) if args.input else project / "workbench/stages/01-analysis/source-truth.json"
    output_path = Path(args.output) if args.output else project / "script/foundation.json"
    try:
        source_truth = json.loads(input_path.read_text(encoding="utf-8-sig"))
    except FileNotFoundError as exc:
        print(str(exc), file=sys.stderr)
        return 2
    foundation = project_source_truth_to_foundation(source_truth)
    errors = validate_foundation(foundation)
    if errors:
        print(json.dumps({"errors": errors}, ensure_ascii=False, indent=2), file=sys.stderr)
        return 3
    if output_path.is_file():
        try:
            existing = json.loads(output_path.read_text(encoding="utf-8-sig"))
        except (OSError, json.JSONDecodeError):
            existing = None
        if isinstance(existing, dict) and existing.get("source_consumption_contract_version") != 2:
            print(
                "warning: overwriting this foundation.json will enable "
                "source_consumption_policy='required' with "
                "source_consumption_contract_version=2; update deck-plan "
                "source_consumption.unit_dispositions and rerun the PLAN gate before AUTHOR.",
                file=sys.stderr,
            )
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(foundation, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    print(str(output_path))
    return 0


def _compile_source_truth_command(args: argparse.Namespace) -> int:
    try:
        output = compile_source_truth(
            Path(args.project),
            Path(args.output) if args.output else None,
        )
    except (FileNotFoundError, ValueError) as exc:
        print(str(exc), file=sys.stderr)
        return 2
    print(str(output))
    return 0


def _source_foundation_truth_command(args: argparse.Namespace) -> int:
    try:
        model_path, truth_path = project_source_foundation_truth(
            Path(args.project),
            foundation_dir=Path(args.foundation_dir) if args.foundation_dir else None,
            semantic_dir=Path(args.semantic_dir) if args.semantic_dir else None,
            model_output=Path(args.model_output) if args.model_output else None,
            truth_output=Path(args.output) if args.output else None,
        )
    except (FileNotFoundError, ValueError) as exc:
        print(str(exc), file=sys.stderr)
        return 2
    print(json.dumps({"semantic_argument_model": str(model_path), "source_truth": str(truth_path)}, ensure_ascii=False, indent=2))
    return 0


def _prepare_source_map_command(args: argparse.Namespace) -> int:
    try:
        report = prepare_source_map(Path(args.project))
    except (FileNotFoundError, ValueError) as exc:
        print(str(exc), file=sys.stderr)
        return 2
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


def _prepare_source_context_command(args: argparse.Namespace) -> int:
    try:
        payload = prepare_source_context(Path(args.project))
    except (FileNotFoundError, ValueError) as exc:
        print(str(exc), file=sys.stderr)
        return 2
    report = {
        "schema": payload.get("schema"),
        "profile": payload.get("profile"),
        "status": payload.get("status"),
        "source_index": payload.get("source_index"),
        "source_count": len(payload.get("sources") or []),
        "heading_count": len(payload.get("source_structure") or []),
        "unit_count": len(payload.get("units") or []),
        "reading_load": payload.get("reading_load"),
        "reading_recommendation": payload.get("reading_recommendation"),
        "issues": payload.get("issues") or [],
        "warnings": payload.get("warnings") or [],
    }
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if payload.get("status") == "passed" else 4


def _prepare_script_foundation_command(args: argparse.Namespace) -> int:
    try:
        payload = prepare_script_foundation(Path(args.project), profile=args.profile)
    except (FileNotFoundError, ValueError) as exc:
        print(str(exc), file=sys.stderr)
        return 2
    print(payload["authoring_task"], end="")
    return 0


def _source_map_check_command(args: argparse.Namespace) -> int:
    try:
        code, report = run_source_map_audit(Path(args.project))
    except (FileNotFoundError, ValueError) as exc:
        print(str(exc), file=sys.stderr)
        return 2
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return code


def _prepare_semantic_understanding_command(args: argparse.Namespace) -> int:
    try:
        payload = prepare_semantic_understanding(Path(args.project))
    except (FileNotFoundError, ValueError) as exc:
        print(str(exc), file=sys.stderr)
        return 2
    print(payload["authoring_task"], end="")
    return 0


def _semantic_check_command(args: argparse.Namespace) -> int:
    try:
        code, report = run_semantic_understanding_audit(Path(args.project))
    except (FileNotFoundError, ValueError) as exc:
        print(str(exc), file=sys.stderr)
        return 2
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return code


def _prepare_visual_structure_command(args: argparse.Namespace) -> int:
    if getattr(args, "lightweight_stage01_confirmed", False):
        _warn_deprecated_compatibility_flag("--lightweight-stage01-confirmed")
    try:
        path = prepare_visual_structure_stage(
            Path(args.project),
            Path(args.script),
        )
    except (FileNotFoundError, ValueError) as exc:
        print(str(exc), file=sys.stderr)
        return 2
    print(f"visual_structure_skill_request: {path}")
    return 0


def _execute_visual_structure_command(args: argparse.Namespace) -> int:
    try:
        artifacts = execute_visual_structure_stage(Path(args.project), Path(args.script))
    except (FileNotFoundError, ValueError, KeyError, TypeError) as exc:
        print(str(exc), file=sys.stderr)
        return 2
    print(json.dumps({key: str(value) for key, value in artifacts.items()}, ensure_ascii=False, indent=2))
    return 0


def _record_visual_structure_execution_command(args: argparse.Namespace) -> int:
    try:
        path = record_visual_structure_execution(
            Path(args.project),
            Path(args.script),
            executor=args.executor,
            model=args.model,
            note=args.note,
        )
    except (FileNotFoundError, ValueError) as exc:
        print(str(exc), file=sys.stderr)
        return 2
    print(f"visual_structure_execution_receipt: {path}")
    return 0


def _visual_structure_audit_command(args: argparse.Namespace) -> int:
    try:
        code, report = run_visual_structure_audit(Path(args.project), Path(args.script))
    except (FileNotFoundError, ValueError, subprocess.CalledProcessError) as exc:
        print(str(exc), file=sys.stderr)
        return 2
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return code


def _prepare_stage02_handoff_command(args: argparse.Namespace) -> int:
    if getattr(args, "lightweight_stage01_confirmed", False):
        _warn_deprecated_compatibility_flag("--lightweight-stage01-confirmed")
    try:
        report = prepare_stage02_handoff(
            Path(args.project),
            script=Path(args.script) if args.script else None,
        )
    except (FileNotFoundError, json.JSONDecodeError, ValueError) as exc:
        print(str(exc), file=sys.stderr)
        return 2
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report.get("status") == "passed" else 1


def _stage02_handoff_check_command(args: argparse.Namespace) -> int:
    project = Path(args.project).expanduser().resolve()
    try:
        report = audit_stage02_handoff(project)
    except (FileNotFoundError, json.JSONDecodeError, ValueError) as exc:
        print(str(exc), file=sys.stderr)
        return 2
    if not args.no_write:
        from cyberppt.artifact_ledger import write_json_atomic

        write_json_atomic(project / HANDOFF_AUDIT, report)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report.get("status") == "passed" else 1


def _assemble_final_script_command(args: argparse.Namespace) -> int:
    try:
        report = assemble_final_script(
            Path(args.project),
            drafts_dir=Path(args.drafts_dir) if args.drafts_dir else None,
            output_path=Path(args.output) if args.output else None,
            title=args.title or "",
            enrichment_source=(
                Path(args.enrichment_source) if args.enrichment_source else None
            ),
        )
    except (FileNotFoundError, ValueError) as exc:
        print(str(exc), file=sys.stderr)
        return 2
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


def _preview_onscreen_markdown_command(args: argparse.Namespace) -> int:
    try:
        output = Path(args.output) if args.output else None
        result = preview_onscreen_markdown(Path(args.script), output_path=output)
    except FileNotFoundError as exc:
        print(str(exc), file=sys.stderr)
        return 2
    if isinstance(result, Path):
        print(f"rendered: {result}")
    else:
        print(result)
    return 0


def _stage_script_command(args: argparse.Namespace) -> int:
    try:
        target = stage_script(
            Path(args.project),
            slide=args.slide,
            kind=args.kind,
            phase=args.phase,
            source=Path(args.source),
            note=args.note,
        )
    except (FileNotFoundError, ValueError) as exc:
        print(str(exc), file=sys.stderr)
        return 2
    print(f"saved_script: {target}")
    print("next_step: stop for user review before generation")
    return 0


def _approve_script_command(args: argparse.Namespace) -> int:
    try:
        path = approve_script(Path(args.project), slide=args.slide, kind=args.kind, note=args.note)
    except (FileNotFoundError, ValueError) as exc:
        print(str(exc), file=sys.stderr)
        return 2
    print(f"approval_recorded: {path}")
    return 0


def _script_status_command(args: argparse.Namespace) -> int:
    try:
        status = get_script_status(Path(args.project), slide=args.slide, kind=args.kind)
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        return 2
    if args.json:
        print(status_as_json(status))
    else:
        print(f"project: {status.project}")
        print(f"slide: {status.slide:02d}")
        print(f"kind: {status.kind}")
        print(f"draft_saved: {'yes' if status.draft_paths else 'no'}")
        print(f"final_saved: {'yes' if status.final_paths else 'no'}")
        print(f"approval_recorded: {'yes' if status.approval_exists else 'no'}")
        print(f"ready_to_generate: {'yes' if status.ready_to_generate else 'no'}")
        print(f"reason: {status.reason}")
    return 0 if status.ready_to_generate else 3


def _prepare_imagegen_send_command(args: argparse.Namespace) -> int:
    try:
        summary = prepare_imagegen_send(
            project=Path(args.project),
            pages_raw=args.pages,
            write_llm_brief=not args.no_llm_brief,
            stage_draft=not args.no_stage,
            note=args.note,
        )
    except (FileNotFoundError, PermissionError, ValueError) as exc:
        print(str(exc), file=sys.stderr)
        return 2
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


def _image_to_editable_svg_command(args: argparse.Namespace) -> int:
    completed = subprocess.run(
        [sys.executable, "-m", "scripts.image_to_editable_svg", *args.reconstruction_args],
        cwd=Path(__file__).resolve().parents[1],
        check=False,
    )
    return completed.returncode


def _enhance_image_command(args: argparse.Namespace) -> int:
    try:
        result = enhance_image(
            Path(args.input), output=Path(args.output) if args.output else None,
            backend=args.backend, scale=args.scale, mode=args.mode,
        )
    except (FileNotFoundError, RuntimeError, ValueError) as exc:
        print(str(exc), file=sys.stderr)
        return 2
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


def _final_script_pages_command(args: argparse.Namespace) -> int:
    if getattr(args, "lightweight_stage01_confirmed", False):
        _warn_deprecated_compatibility_flag("--lightweight-stage01-confirmed")
    if getattr(args, "allow_script_edit", False):
        _warn_deprecated_compatibility_flag("--allow-script-edit")
    if args.blueprint_only and args.production_build:
        print("--blueprint-only cannot be combined with --production-build", file=sys.stderr)
        return 2
    try:
        summary = run_final_script_pages(
            project=Path(args.project),
            script=Path(args.script),
            pages_raw=args.pages,
            style_lock=Path(args.style_lock) if args.style_lock else None,
            output_dir=Path(args.output_dir) if args.output_dir else None,
            require_images=args.require_images,
            production_build=args.production_build,
            production_mode=args.production_mode,
            assembly_mode=args.assembly_mode,
            generate_images=args.generate_images,
            image_model=args.image_model,
            image_quality=args.image_quality,
            image_timeout=args.image_timeout,
            force_images=args.force_images,
            dry_run_images=args.dry_run_images,
            prompt_enrich=args.prompt_enrich,
            require_send_approval=args.require_send_approval,
            build_id=args.build_id,
            external_script=args.external_script,
            allow_script_edit=args.allow_script_edit,
            allow_prompt_edit=args.allow_prompt_edit,
            prompt_overrides_dir=Path(args.prompt_overrides_dir) if args.prompt_overrides_dir else None,
            reuse_audited_images_from=(
                Path(args.reuse_audited_images_from)
                if args.reuse_audited_images_from else None
            ),
            approved_full_image=Path(args.approved_full_image) if args.approved_full_image else None,
            blueprint_only=args.blueprint_only,
            no_style_reference=args.no_style_reference,
            skip_image_text_audit=args.skip_image_text_audit,
        )
    except (FileNotFoundError, RuntimeError, ValueError) as exc:
        print(str(exc), file=sys.stderr)
        return 2
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


def _register_quick_page_command(args: argparse.Namespace) -> int:
    from scripts.image_to_pptx_runtime.authored_layers import REVIEW_CHECKS, register_quick_page
    try:
        result = register_quick_page(
            Path(args.manifest), page_number=args.page, authored_svg=Path(args.svg),
            clean_base=Path(args.clean_base), source_sha256=args.source_sha256,
            reviewer=args.reviewer, checks={name: getattr(args, name) for name in REVIEW_CHECKS},
            notes=args.notes,
        )
    except (OSError, ValueError) as exc:
        print(str(exc), file=sys.stderr)
        return 1
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


def _review_quick_page_command(args: argparse.Namespace) -> int:
    checks = {
        name: getattr(args, name)
        for name in (
            "layout_fidelity",
            "typography_fidelity",
            "color_weight_fidelity",
            "text_wrapping",
            "residual_chinese",
            "readability",
        )
    }
    try:
        result = record_quick_page_review(
            Path(args.manifest),
            page_number=args.page,
            status=args.status,
            reviewer=args.reviewer,
            checks=checks,
            notes=args.notes,
        )
    except (FileNotFoundError, json.JSONDecodeError, ValueError) as exc:
        print(str(exc), file=sys.stderr)
        return 2
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="cyberppt", description="CyberPPT product tooling.")
    parser.add_argument("--version", action="version", version=f"cyberppt {__version__}")
    subparsers = parser.add_subparsers(dest="command")

    doctor = subparsers.add_parser("doctor", help="Check repository assets and command availability.")
    doctor.set_defaults(func=lambda _args: _doctor())

    officecli = subparsers.add_parser(
        "officecli", help="Manage the pinned repository-local OfficeCLI renderer."
    )
    officecli_subparsers = officecli.add_subparsers(dest="officecli_action", required=True)
    officecli_status_parser = officecli_subparsers.add_parser("status", help="Show OfficeCLI resolution and version.")
    officecli_status_parser.set_defaults(func=_officecli_command)
    officecli_install_parser = officecli_subparsers.add_parser(
        "install", help="Install the pinned OfficeCLI binary under .tools/ after SHA-256 verification."
    )
    officecli_install_parser.add_argument("--force", action="store_true", help="Redownload the pinned binary.")
    officecli_install_parser.set_defaults(func=_officecli_command)

    enhance = subparsers.add_parser(
        "enhance-image", help="Enhance one image through the registered ppt-image-enhancer skill."
    )
    enhance.add_argument("input")
    enhance.add_argument("--output")
    enhance.add_argument(
        "--backend", choices=("auto", "builtin", "realesrgan_ncnn", "realesrgan", "swinir"), default="auto"
    )
    enhance.add_argument("--scale", type=float, choices=(1.0, 1.5, 2.0, 4.0), default=1.0)
    enhance.add_argument(
        "--mode", choices=("ppt_page", "chart_heavy", "scene_plus_text", "screenshot")
    )
    enhance.set_defaults(func=_enhance_image_command)

    init = subparsers.add_parser("init", help="Create a CyberPPT project workspace.")
    init.add_argument("path", help="Target project directory.")
    init.add_argument(
        "--profile",
        choices=("script", "strict", "legacy"),
        default="script",
        help="script is the default fast source-faithful route; strict/legacy are explicit verification routes.",
    )
    init.add_argument("--force", action="store_true", help="Overwrite generated project manifest and README.")
    init.set_defaults(func=_init_command)

    project_status = subparsers.add_parser(
        "status",
        help="Compute live Stage 01 and Stage 02 project status from current artifacts.",
    )
    project_status.add_argument("project", help="CyberPPT project directory.")
    project_status.set_defaults(func=_project_status_command)

    prepare_source_map_parser = subparsers.add_parser(
        "prepare-source-map",
        help="Compile stable source units and the original source heading tree.",
    )
    prepare_source_map_parser.add_argument("project", help="CyberPPT project directory.")
    prepare_source_map_parser.set_defaults(func=_prepare_source_map_command)

    prepare_source_context_parser = subparsers.add_parser(
        "prepare-source-context",
        help="Build the script profile's single deterministic source index.",
    )
    prepare_source_context_parser.add_argument("project", help="CyberPPT project directory.")
    prepare_source_context_parser.set_defaults(func=_prepare_source_context_command)

    prepare_script_foundation_parser = subparsers.add_parser(
        "prepare-script-foundation",
        help="Prepare direct Foundation authoring from the script source index.",
    )
    prepare_script_foundation_parser.add_argument("project", help="CyberPPT project directory.")
    prepare_script_foundation_parser.add_argument(
        "--profile",
        choices=("script", "strict", "legacy"),
        default="script",
        help="script uses direct Foundation authoring; strict/legacy retain the Source Truth route.",
    )
    prepare_script_foundation_parser.set_defaults(func=_prepare_script_foundation_command)

    source_map_check = subparsers.add_parser(
        "source-map-check",
        help="Audit source extraction, stable IDs, heading hierarchy, and pending image interpretation.",
    )
    source_map_check.add_argument("project", help="CyberPPT project directory.")
    source_map_check.set_defaults(func=_source_map_check_command)

    prepare_semantic = subparsers.add_parser(
        "prepare-semantic-understanding",
        help="Prepare the source-bound whole-document semantic-understanding gate.",
    )
    prepare_semantic.add_argument("project", help="CyberPPT project directory.")
    prepare_semantic.set_defaults(func=_prepare_semantic_understanding_command)

    semantic_check = subparsers.add_parser(
        "semantic-check",
        help="Audit whole-document semantic understanding before Source Truth.",
    )
    semantic_check.add_argument("project", help="CyberPPT project directory.")
    semantic_check.set_defaults(func=_semantic_check_command)

    prepare_visual_structure = subparsers.add_parser(
        "prepare-visual-structure",
        help="Prepare the ppt-visual-structure-designer execution request and locked input contract.",
    )
    prepare_visual_structure.add_argument("project", help="CyberPPT project directory.")
    prepare_visual_structure.add_argument("--script", required=True, help="Approved final script.")
    prepare_visual_structure.add_argument(
        "--lightweight-stage01-confirmed",
        action="store_true",
        help="Deprecated compatibility-only flag; retained for old callers and does not change the current Stage 02 authorization gate.",
    )
    prepare_visual_structure.set_defaults(func=_prepare_visual_structure_command)

    execute_visual_structure = subparsers.add_parser(
        "execute-visual-structure",
        help="Compile the executed visual-design decision receipt into official Stage 02 visual specs.",
    )
    execute_visual_structure.add_argument("project", help="CyberPPT project directory.")
    execute_visual_structure.add_argument("--script", required=True, help="Approved final script.")
    execute_visual_structure.set_defaults(func=_execute_visual_structure_command)

    record_visual_structure = subparsers.add_parser(
        "record-visual-structure-execution",
        help="Record an actual ppt-visual-structure-designer execution and bind its outputs.",
    )
    record_visual_structure.add_argument("project", help="CyberPPT project directory.")
    record_visual_structure.add_argument("--script", required=True, help="Approved final script.")
    record_visual_structure.add_argument("--executor", required=True, help="Execution surface, e.g. codex-desktop.")
    record_visual_structure.add_argument("--model", required=True, help="Model identifier recorded by the executor.")
    record_visual_structure.add_argument("--note", default="", help="Optional execution note.")
    record_visual_structure.set_defaults(func=_record_visual_structure_execution_command)

    visual_structure_audit = subparsers.add_parser(
        "visual-structure-audit",
        help="Validate and bind visual-structure-designer outputs to the approved script.",
    )
    visual_structure_audit.add_argument("project", help="CyberPPT project directory.")
    visual_structure_audit.add_argument("--script", required=True, help="Approved final script.")
    visual_structure_audit.set_defaults(func=_visual_structure_audit_command)

    prepare_handoff = subparsers.add_parser(
        "prepare-stage02-handoff",
        help="Compile a script-driven Stage 02 field contract.",
    )
    prepare_handoff.add_argument("project", help="CyberPPT project directory.")
    prepare_handoff.add_argument(
        "--script",
        help="Stage 02 content script; accepts an absolute external path and defaults to workbench/scripts/final/script-final.md.",
    )
    prepare_handoff.add_argument(
        "--lightweight-stage01-confirmed",
        action="store_true",
        help="Deprecated compatibility-only flag; retained for old callers and does not change the current Stage 02 handoff gate.",
    )
    prepare_handoff.set_defaults(func=_prepare_stage02_handoff_command)

    check_handoff = subparsers.add_parser(
        "stage02-handoff-check",
        help="Audit Stage 02 handoff fields, source paths, roles, text locks, and coordinate spaces.",
    )
    check_handoff.add_argument("project", help="CyberPPT project directory.")
    check_handoff.add_argument(
        "--no-write",
        action="store_true",
        help="Print the live audit result without updating the persisted audit receipt.",
    )
    check_handoff.set_defaults(func=_stage02_handoff_check_command)

    source_truth_audit = subparsers.add_parser(
        "source-truth-audit",
        help="Audit Stage 01 source evidence and factual/semantic-evidence consistency.",
    )
    source_truth_audit.add_argument("project", help="CyberPPT project directory.")
    source_truth_audit.add_argument("--input", required=True, help="Source Truth JSON file to audit.")
    source_truth_audit.set_defaults(func=_source_truth_audit_command)

    project_foundation = subparsers.add_parser(
        "project-foundation",
        help=(
            "Project validated Source Truth into foundation.json and enable strict "
            "source-consumption checks."
        ),
        description=(
            "Mechanically project an already-validated Source Truth into script_engine "
            "foundation.json. The result sets source_consumption_policy='required'. "
            "Reprojecting a historical foundation is a one-way strict-mode migration: "
            "update Deck Plan source_consumption contracts and rerun the PLAN gate "
            "before AUTHOR."
        ),
    )
    project_foundation.add_argument("project", help="CyberPPT project directory.")
    project_foundation.add_argument(
        "--input",
        help="Source Truth JSON file; defaults to workbench/stages/01-analysis/source-truth.json.",
    )
    project_foundation.add_argument(
        "--output",
        help="Destination foundation.json path; defaults to <project>/script/foundation.json.",
    )
    project_foundation.set_defaults(func=_project_foundation_command)

    compile_truth = subparsers.add_parser(
        "compile-source-truth",
        help="Project canonical semantic atomic items into Source Truth without rereading or reauthoring the source.",
    )
    compile_truth.add_argument("project", help="CyberPPT project directory.")
    compile_truth.add_argument(
        "--output",
        default="",
        help="Optional output path; defaults to the canonical project source-truth.json.",
    )
    compile_truth.set_defaults(func=_compile_source_truth_command)

    foundation_truth = subparsers.add_parser(
        "source-foundation-truth",
        help="Mechanically project one validated Source Foundation semantic set into canonical Source Truth.",
    )
    foundation_truth.add_argument("project", help="CyberPPT project directory.")
    foundation_truth.add_argument(
        "--foundation-dir",
        default="",
        help="Optional layer-two foundation directory; pair with --semantic-dir. Defaults to the unique successful source-foundation manifest item.",
    )
    foundation_truth.add_argument(
        "--semantic-dir",
        default="",
        help="Optional validated semantic directory; pair with --foundation-dir.",
    )
    foundation_truth.add_argument(
        "--model-output",
        default="",
        help="Optional projection-model destination; defaults to the canonical semantic-argument-model.json.",
    )
    foundation_truth.add_argument(
        "--output",
        default="",
        help="Optional Source Truth destination; defaults to the canonical source-truth.json.",
    )
    foundation_truth.set_defaults(func=_source_foundation_truth_command)

    assemble_final = subparsers.add_parser(
        "assemble-final-script",
        help=(
            "Merge draft batch scripts into a clean final manuscript under "
            "workbench/scripts/final/ (no 草稿/批次 wording)."
        ),
    )
    assemble_final.add_argument("project", help="CyberPPT project directory.")
    assemble_final.add_argument(
        "--drafts-dir",
        help="Draft directory; defaults to workbench/scripts/drafts.",
    )
    assemble_final.add_argument(
        "--output",
        help="Output path; defaults to workbench/scripts/final/script-final.md.",
    )
    assemble_final.add_argument(
        "--title",
        default="",
        help="Optional document title for the final manuscript header.",
    )
    assemble_final.add_argument(
        "--enrichment-source",
        default="",
        help="Optional prior full script used only to restore missing visual-structure lines.",
    )
    assemble_final.set_defaults(func=_assemble_final_script_command)

    preview_onscreen_md = subparsers.add_parser(
        "preview-onscreen-markdown",
        help=(
            "Render a page script's 上屏文字 as real nested Markdown bullets for "
            "human review. Does not edit the source script; the authoritative "
            "file stays plain-text-with-indentation for script-audit."
        ),
    )
    preview_onscreen_md.add_argument("script", help="Path to the page script .md file.")
    preview_onscreen_md.add_argument(
        "--output",
        help="Optional path to write the rendered Markdown; prints to stdout if omitted.",
    )
    preview_onscreen_md.set_defaults(func=_preview_onscreen_markdown_command)

    stage_script_parser = subparsers.add_parser(
        "stage-script",
        help="Save a per-slide script or ImageGen prompt before generation.",
    )
    stage_script_parser.add_argument("project", help="CyberPPT project directory.")
    stage_script_parser.add_argument("--slide", type=int, required=True, help="Slide number, 1-based.")
    stage_script_parser.add_argument(
        "--kind",
        choices=["analysis", "blueprint", "imagegen", "imagegen-send", "pptx"],
        required=True,
        help="Script type.",
    )
    stage_script_parser.add_argument(
        "--phase",
        choices=["draft", "final"],
        required=True,
        help="Whether this is a review draft or the final approved script text.",
    )
    stage_script_parser.add_argument("--source", required=True, help="UTF-8 plaintext script file to save.")
    stage_script_parser.add_argument("--note", default="", help="Optional operator note.")
    stage_script_parser.set_defaults(func=_stage_script_command)

    approve_script_parser = subparsers.add_parser(
        "approve-script",
        help="Record user approval for a saved final per-slide script.",
    )
    approve_script_parser.add_argument("project", help="CyberPPT project directory.")
    approve_script_parser.add_argument("--slide", type=int, required=True, help="Slide number, 1-based.")
    approve_script_parser.add_argument(
        "--kind",
        choices=["analysis", "blueprint", "imagegen", "imagegen-send", "pptx"],
        required=True,
        help="Script type.",
    )
    approve_script_parser.add_argument("--note", default="", help="Optional approval note.")
    approve_script_parser.set_defaults(func=_approve_script_command)

    script_status_parser = subparsers.add_parser(
        "script-status",
        help="Check whether a slide script is saved and approved for generation.",
    )
    script_status_parser.add_argument("project", help="CyberPPT project directory.")
    script_status_parser.add_argument("--slide", type=int, required=True, help="Slide number, 1-based.")
    script_status_parser.add_argument(
        "--kind",
        choices=["analysis", "blueprint", "imagegen", "imagegen-send", "pptx"],
        required=True,
        help="Script type.",
    )
    script_status_parser.add_argument("--json", action="store_true", help="Print machine-readable status.")
    script_status_parser.set_defaults(func=_script_status_command)

    image_to_editable_svg_parser = subparsers.add_parser(
        "image-to-editable-svg",
        add_help=False,
        help="Deprecated OCR route; disabled. Use final-script-pages --production-build for Quick.",
    )
    image_to_editable_svg_parser.add_argument("reconstruction_args", nargs=argparse.REMAINDER)
    image_to_editable_svg_parser.set_defaults(func=_image_to_editable_svg_command)

    quick_register_parser = subparsers.add_parser(
        "register-quick-page", help="Register reviewed local SVG and reference-edited layers in an active production build.",
    )
    quick_register_parser.add_argument("manifest")
    quick_register_parser.add_argument("--page", type=int, required=True)
    quick_register_parser.add_argument("--svg", required=True)
    quick_register_parser.add_argument("--clean-base", required=True)
    quick_register_parser.add_argument("--source-sha256", required=True)
    quick_register_parser.add_argument("--reviewer", required=True)
    quick_register_parser.add_argument("--notes", default="")
    for check in ("source-layout", "graphic-identity", "text-removed", "background-continuity"):
        quick_register_parser.add_argument(f"--{check}", choices=("passed", "failed"), required=True)
    quick_register_parser.set_defaults(func=_register_quick_page_command)

    quick_review_parser = subparsers.add_parser(
        "review-quick-page",
        help="Record a human visual review bound to an exact Stage 02 Quick preview PNG.",
    )
    quick_review_parser.add_argument("manifest", help="Production page_image_pairs.json path.")
    quick_review_parser.add_argument("--page", type=int, required=True, help="Page number to review.")
    quick_review_parser.add_argument("--status", choices=("passed", "failed"), required=True)
    quick_review_parser.add_argument("--reviewer", required=True)
    quick_review_parser.add_argument("--notes", default="")
    for check in (
        "layout-fidelity",
        "typography-fidelity",
        "color-weight-fidelity",
        "text-wrapping",
        "residual-chinese",
        "readability",
    ):
        quick_review_parser.add_argument(
            f"--{check}",
            choices=("passed", "failed"),
            required=True,
        )
    quick_review_parser.set_defaults(func=_review_quick_page_command)

    final_script_pages_parser = subparsers.add_parser(
        "final-script-pages",
        help="Compile selected pages from a final script into traceable full-image PPT inputs.",
    )
    final_script_pages_parser.add_argument("project", help="CyberPPT project directory.")
    final_script_pages_parser.add_argument("--script", required=True, help="Stage 02 content script; project-local or external path.")
    final_script_pages_parser.add_argument(
        "--external-script",
        action="store_true",
        help=(
            "Mark an external manuscript as a traceable Stage 02 input; it uses the standard content-first presentation contract."
        ),
    )
    final_script_pages_parser.add_argument(
        "--allow-script-edit",
        action="store_true",
        help=(
            "Deprecated compatibility-only flag; retained for old callers and does not change the current Stage 02, prompt, or production gates."
        ),
    )
    final_script_pages_parser.add_argument(
        "--allow-prompt-edit",
        action="store_true",
        help=(
            "Use direct Stage 02 prompt override files as the image-generation source; "
            "requires --prompt-overrides-dir and preserves image-text and production QA."
        ),
    )
    final_script_pages_parser.add_argument(
        "--prompt-overrides-dir",
        help="Directory containing direct prompt overrides named pXX.txt or pXX.md.",
    )
    final_script_pages_parser.add_argument(
        "--lightweight-stage01-confirmed",
        action="store_true",
        help=(
            "Deprecated compatibility-only flag; retained for old callers and does not grant Stage 02 authorization or change the current content gate."
        ),
    )
    final_script_pages_parser.add_argument("--pages", required=True, help="Page range, e.g. 7-8 or 7,8.")
    final_script_pages_parser.add_argument(
        "--style-lock",
        help=(
            "Optional CyberPPT visual style lock JSON (schema cyberppt.visual_style_lock.v1). "
            "If omitted, the main flow automatically creates the Style 09 lock."
        ),
    )
    # Accepted silently for old automation; the main flow ignores selection and uses Style 09.
    final_script_pages_parser.add_argument("--style-id", type=int, help=argparse.SUPPRESS)
    final_script_pages_parser.add_argument("--style-name", help=argparse.SUPPRESS)
    final_script_pages_parser.add_argument("--output-dir", help="Optional output directory for page_image_pairs.json.")
    final_script_pages_parser.add_argument(
        "--reuse-audited-images-from",
        help=(
            "Import same-script, text-audited full images from an official Stage 02 "
            "manifest for editable or dual Quick reconstruction; images are not regenerated."
        ),
    )
    final_script_pages_parser.add_argument(
        "--approved-full-image",
        help="Import a user-approved local full image, re-audit it, then use it as the current build's visual authority.",
    )
    final_script_pages_parser.add_argument(
        "--build-id",
        help="Stable build identifier used for resumable, versioned Stage 02 outputs.",
    )
    final_script_pages_parser.add_argument(
        "--production-mode",
        choices=("image-to-editable-svg",),
        default="image-to-editable-svg",
        help="Generate one audited full image and reconstruct it as editable SVG.",
    )
    final_script_pages_parser.add_argument(
        "--assembly-mode",
        choices=("image", "editable", "both"),
        default="editable",
        help=(
            "Stage 02 output route: image places the 2:1 body image in the template, "
            "editable places the 2:1 Quick SVG in the template, both emits both PPTX files."
        ),
    )
    final_script_pages_parser.add_argument(
        "--generate-images",
        action="store_true",
        help="Generate pending image variants through the Codex OAuth image backend.",
    )
    final_script_pages_parser.add_argument("--image-model", default="gpt-image-2")
    final_script_pages_parser.add_argument(
        "--image-quality",
        choices=("low", "medium", "high", "auto"),
        default="high",
    )
    final_script_pages_parser.add_argument("--image-timeout", type=int, default=600)
    final_script_pages_parser.add_argument("--force-images", action="store_true")
    final_script_pages_parser.add_argument(
        "--no-style-reference",
        action="store_true",
        help="Do not pass the selected style reference image to the image backend.",
    )
    final_script_pages_parser.add_argument("--dry-run-images", action="store_true")
    final_script_pages_parser.add_argument(
        "--skip-image-text-audit",
        action="store_true",
        help=(
            "Generate each image once without OCR/vision text audit or correction retries. "
            "The default production text gate remains enabled."
        ),
    )
    final_script_pages_parser.add_argument(
        "--prompt-enrich",
        choices=("off", "deterministic", "send"),
        default="off",
        help=(
            "Send-time prompt enrich (default: off — consume the approved prompt verbatim; "
            "deterministic mode explicitly appends structure/material/people/ban cues). "
            "off=approved prompt only; "
            "send=prefer approved imagegen-send final (else deterministic unless --require-send-approval)."
        ),
    )
    final_script_pages_parser.add_argument(
        "--require-send-approval",
        action="store_true",
        help="With --prompt-enrich send, fail unless each page has an approved imagegen-send final.",
    )
    final_script_pages_parser.add_argument(
        "--require-images",
        action="store_true",
        help="Fail unless expected full image files already exist.",
    )
    final_script_pages_parser.add_argument(
        "--production-build",
        action="store_true",
        help="Run the image-to-editable-SVG production build.",
    )
    final_script_pages_parser.add_argument(
        "--blueprint-only",
        action="store_true",
        help="Only create full-image prompts and page_image_pairs.json; never report production_ready.",
    )
    final_script_pages_parser.set_defaults(func=_final_script_pages_command)

    prepare_send = subparsers.add_parser(
        "prepare-imagegen-send",
        help=(
            "Build deterministic ImageGen send drafts (+ LLM briefs) from approved "
            "imagegen finals for optional per-page rewrite and secondary approval."
        ),
    )
    prepare_send.add_argument("project", help="CyberPPT project directory.")
    prepare_send.add_argument("--pages", required=True, help="Page range, e.g. 15 or 4,5,6.")
    prepare_send.add_argument(
        "--no-llm-brief",
        action="store_true",
        help="Skip writing per-page LLM enrich brief files.",
    )
    prepare_send.add_argument(
        "--no-stage",
        action="store_true",
        help="Write files only; do not stage imagegen-send drafts into the script ledger.",
    )
    prepare_send.add_argument("--note", default="", help="Optional staging note.")
    prepare_send.set_defaults(func=_prepare_imagegen_send_command)

    for alias in sorted(SCRIPT_ALIASES):
        command = subparsers.add_parser(alias, add_help=False, help=f"Run scripts/{SCRIPT_ALIASES[alias]}.")
        command.add_argument("script_args", nargs=argparse.REMAINDER)
        command.set_defaults(func=lambda args, alias=alias: run_script(alias, args.script_args))

    return parser


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    if argv and argv[0] in SCRIPT_ALIASES:
        return run_script(argv[0], argv[1:])
    parser = build_parser()
    args = parser.parse_args(argv)
    if not hasattr(args, "func"):
        parser.print_help()
        return 0
    return int(args.func(args))
