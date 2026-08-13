"""CyberPPT product command line interface."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

from cyberppt import __version__
from cyberppt.commands.assemble_final_script import assemble_final_script
from cyberppt.commands.compile_page_script_authoring import (
    compile_page_script_authoring,
)
from cyberppt.commands.final_script_pages import run_final_script_pages
from cyberppt.commands.init_project import init_project
from cyberppt.image_enhancer import enhance_image
from cyberppt.commands.outline_audit import run_outline_audit
from cyberppt.commands.prepare_imagegen_send import prepare_imagegen_send
from cyberppt.commands.prepare_stage01_input import (
    prepare_outline_input,
    prepare_page_script_input,
)
from cyberppt.commands.run_autonomous import run_autonomous
from cyberppt.commands.script_audit import run_script_audit
from cyberppt.commands.script_gate import approve_script, get_script_status, stage_script, status_as_json
from cyberppt.commands.script_runner import SCRIPT_ALIASES, run_script
from cyberppt.commands.source_truth_audit import run_source_truth_audit
from cyberppt.commands.visual_structure_stage import (
    execute_visual_structure_stage,
    prepare_visual_structure_stage,
    record_visual_structure_execution,
    run_visual_structure_audit,
)
from cyberppt.communication_strategy import prepare_communication_strategy
from cyberppt.paths import ASSETS_DIR, REFERENCES_DIR, SCRIPTS_DIR, SKILL_FILE
from cyberppt.semantic_understanding import (
    prepare_semantic_understanding,
    run_semantic_understanding_audit,
)
from cyberppt.source_document_map import prepare_source_map, run_source_map_audit
from cyberppt.stage02_handoff import (
    HANDOFF_AUDIT,
    HANDOFF_JSON,
    audit_stage02_handoff,
    prepare_stage02_handoff,
)
from cyberppt.stage01_compiler import compile_outline_draft, compile_source_truth


def _doctor() -> int:
    required_palette_samples = [
        ASSETS_DIR / "palette-samples" / f"palette-{style_id:02d}.png"
        for style_id in range(1, 9)
    ]
    checks = {
        "skill": SKILL_FILE.exists(),
        "references": REFERENCES_DIR.exists() and any(REFERENCES_DIR.glob("*.md")),
        "palette_samples": all(sample.exists() for sample in required_palette_samples),
        "scripts": all((SCRIPTS_DIR / name).exists() for name in SCRIPT_ALIASES.values()),
    }
    for name, passed in checks.items():
        print(f"{name}: {'ok' if passed else 'missing'}")
    return 0 if all(checks.values()) else 1


def _init_command(args: argparse.Namespace) -> int:
    try:
        created = init_project(Path(args.path), force=args.force)
    except FileExistsError as exc:
        print(str(exc), file=sys.stderr)
        return 2
    print(f"initialized CyberPPT project: {Path(args.path).expanduser().resolve()}")
    print(f"created_or_updated: {len(created)}")
    return 0


def _outline_audit_command(args: argparse.Namespace) -> int:
    try:
        code, report = run_outline_audit(
            Path(args.project),
            Path(args.input),
            source_truth_path=Path(args.source_truth) if args.source_truth else None,
        )
    except (FileNotFoundError, ValueError) as exc:
        print(str(exc), file=sys.stderr)
        return 2
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return code


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


def _compile_outline_draft_command(args: argparse.Namespace) -> int:
    try:
        output = compile_outline_draft(
            Path(args.project),
            communication_goal=args.communication_goal,
            output=Path(args.output) if args.output else None,
            source_truth=Path(args.source_truth) if args.source_truth else None,
        )
    except (FileNotFoundError, ValueError) as exc:
        print(str(exc), file=sys.stderr)
        return 2
    print(str(output))
    return 0


def _prepare_source_map_command(args: argparse.Namespace) -> int:
    try:
        report = prepare_source_map(Path(args.project))
    except (FileNotFoundError, ValueError) as exc:
        print(str(exc), file=sys.stderr)
        return 2
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


def _source_map_check_command(args: argparse.Namespace) -> int:
    try:
        code, report = run_source_map_audit(Path(args.project))
    except (FileNotFoundError, ValueError) as exc:
        print(str(exc), file=sys.stderr)
        return 2
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return code


def _run_autonomous_command(args: argparse.Namespace) -> int:
    try:
        code, report = run_autonomous(
            Path(args.contract),
            generate_images=not args.skip_image_generation,
            image_timeout=args.image_timeout,
            resume=args.resume,
        )
    except ValueError as exc:
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


def _prepare_communication_strategy_command(args: argparse.Namespace) -> int:
    try:
        payload = prepare_communication_strategy(Path(args.project))
    except (FileNotFoundError, ValueError) as exc:
        print(str(exc), file=sys.stderr)
        return 2
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0


def _prepare_visual_structure_command(args: argparse.Namespace) -> int:
    try:
        path = prepare_visual_structure_stage(
            Path(args.project),
            Path(args.script),
            lightweight_stage01_confirmed=args.lightweight_stage01_confirmed,
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
    try:
        report = prepare_stage02_handoff(
            Path(args.project),
            script=Path(args.script) if args.script else None,
            lightweight_stage01_confirmed=args.lightweight_stage01_confirmed,
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
    from cyberppt.artifact_ledger import write_json_atomic

    write_json_atomic(project / HANDOFF_AUDIT, report)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report.get("status") == "passed" else 1


def _script_audit_command(args: argparse.Namespace) -> int:
    try:
        code, report = run_script_audit(
            Path(args.project),
            Path(args.input),
            outline_path=Path(args.outline) if args.outline else None,
            source_truth_path=(
                Path(args.source_truth) if args.source_truth else None
            ),
        )
    except (FileNotFoundError, json.JSONDecodeError, ValueError) as exc:
        print(str(exc), file=sys.stderr)
        return 2
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return code


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


def _compile_page_script_authoring_command(args: argparse.Namespace) -> int:
    try:
        report = compile_page_script_authoring(
            Path(args.project),
            authoring_path=Path(args.authoring) if args.authoring else None,
            output_dir=Path(args.output_dir),
        )
    except (FileNotFoundError, json.JSONDecodeError, ValueError) as exc:
        print(str(exc), file=sys.stderr)
        return 2
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


def _prepare_outline_input_command(args: argparse.Namespace) -> int:
    try:
        print(
            prepare_outline_input(
                Path(args.project),
                communication_goal=args.communication_goal or "",
            )
        )
    except (FileNotFoundError, json.JSONDecodeError, ValueError) as exc:
        print(str(exc), file=sys.stderr)
        return 2
    return 0


def _prepare_page_script_input_command(args: argparse.Namespace) -> int:
    try:
        print(
            prepare_page_script_input(
                Path(args.project),
                args.page or "",
            )
        )
    except (FileNotFoundError, json.JSONDecodeError, ValueError) as exc:
        print(str(exc), file=sys.stderr)
        return 2
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


def _rebuild_dual_image_command(args: argparse.Namespace) -> int:
    return run_script("template-rebuild", args.rebuild_args)


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
    if args.blueprint_only and args.production_build:
        print("--blueprint-only cannot be combined with --production-build", file=sys.stderr)
        return 2
    try:
        summary = run_final_script_pages(
            project=Path(args.project),
            script=Path(args.script),
            pages_raw=args.pages,
            style_lock=Path(args.style_lock) if args.style_lock else None,
            style_id=args.style_id,
            style_name=args.style_name,
            output_dir=Path(args.output_dir) if args.output_dir else None,
            semantic_plan_dir=Path(args.semantic_plan_dir) if args.semantic_plan_dir else None,
            require_images=args.require_images,
            run_rebuild=args.run_rebuild,
            rebuild_args=args.rebuild_arg or [],
            production_build=args.production_build,
            production_mode=args.production_mode,
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
            lightweight_stage01_confirmed=args.lightweight_stage01_confirmed,
            blueprint_only=args.blueprint_only,
            no_style_reference=args.no_style_reference,
            skip_image_text_audit=args.skip_image_text_audit,
        )
    except (FileNotFoundError, RuntimeError, ValueError) as exc:
        print(str(exc), file=sys.stderr)
        return 2
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="cyberppt", description="CyberPPT product tooling.")
    parser.add_argument("--version", action="version", version=f"cyberppt {__version__}")
    subparsers = parser.add_subparsers(dest="command")

    doctor = subparsers.add_parser("doctor", help="Check repository assets and command availability.")
    doctor.set_defaults(func=lambda _args: _doctor())

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
    init.add_argument("--force", action="store_true", help="Overwrite generated project manifest and README.")
    init.set_defaults(func=_init_command)

    prepare_source_map_parser = subparsers.add_parser(
        "prepare-source-map",
        help="Compile stable source units and the original source heading tree.",
    )
    prepare_source_map_parser.add_argument("project", help="CyberPPT project directory.")
    prepare_source_map_parser.set_defaults(func=_prepare_source_map_command)

    source_map_check = subparsers.add_parser(
        "source-map-check",
        help="Audit source extraction, stable IDs, heading hierarchy, and pending image interpretation.",
    )
    source_map_check.add_argument("project", help="CyberPPT project directory.")
    source_map_check.set_defaults(func=_source_map_check_command)

    run_autonomous_parser = subparsers.add_parser(
        "run-autonomous",
        help="Run a contract-bound lightweight pipeline; stop at the first unmet gate.",
    )
    run_autonomous_parser.add_argument(
        "contract",
        help="Absolute-path JSON task contract declaring source boundaries and required production.",
    )
    run_autonomous_parser.add_argument(
        "--skip-image-generation",
        action="store_true",
        help="Diagnose up to the image gate without contacting ImageGen; contracts requiring images return failed.",
    )
    run_autonomous_parser.add_argument(
        "--resume",
        action="store_true",
        help="Resume from current artifacts but revalidate every prior gate before continuing.",
    )
    run_autonomous_parser.add_argument(
        "--image-timeout",
        type=int,
        default=600,
        help="ImageGen timeout in seconds when the contract requires images (default: 600).",
    )
    run_autonomous_parser.set_defaults(func=_run_autonomous_command)

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

    prepare_communication = subparsers.add_parser(
        "prepare-communication-strategy",
        help="Prepare the audience and reporting-direction gate before Outline authoring.",
    )
    prepare_communication.add_argument("project", help="CyberPPT project directory.")
    prepare_communication.set_defaults(func=_prepare_communication_strategy_command)

    outline_audit = subparsers.add_parser(
        "outline-audit",
        help="Audit a Stage 01 outline and direct rewrite.",
    )
    outline_audit.add_argument("project", help="CyberPPT project directory.")
    outline_audit.add_argument("--input", required=True, help="Outline JSON file to audit.")
    outline_audit.add_argument(
        "--source-truth",
        help="Optional Source Truth JSON; defaults to the project Stage 01 artifact.",
    )
    outline_audit.set_defaults(func=_outline_audit_command)

    prepare_visual_structure = subparsers.add_parser(
        "prepare-visual-structure",
        help="Prepare the ppt-visual-structure-designer execution request and locked input contract.",
    )
    prepare_visual_structure.add_argument("project", help="CyberPPT project directory.")
    prepare_visual_structure.add_argument("--script", required=True, help="Approved final script.")
    prepare_visual_structure.add_argument(
        "--lightweight-stage01-confirmed",
        action="store_true",
        help="Use the current passed lightweight full-script audit and the user's interactive final confirmation without creating Stage 01 approval artifacts.",
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
        help="Compile the validated Stage 01 to Stage 02 field contract.",
    )
    prepare_handoff.add_argument("project", help="CyberPPT project directory.")
    prepare_handoff.add_argument(
        "--script",
        help="Approved final script; defaults to workbench/scripts/final/script-final.md.",
    )
    prepare_handoff.add_argument(
        "--lightweight-stage01-confirmed",
        action="store_true",
        help="Use the current passed lightweight full-script audit and the user's interactive final confirmation without creating Stage 01 approval artifacts.",
    )
    prepare_handoff.set_defaults(func=_prepare_stage02_handoff_command)

    check_handoff = subparsers.add_parser(
        "stage02-handoff-check",
        help="Audit Stage 02 handoff fields, source paths, roles, text locks, and coordinate spaces.",
    )
    check_handoff.add_argument("project", help="CyberPPT project directory.")
    check_handoff.set_defaults(func=_stage02_handoff_check_command)

    source_truth_audit = subparsers.add_parser(
        "source-truth-audit",
        help="Audit Stage 01 source evidence and factual/semantic-evidence consistency.",
    )
    source_truth_audit.add_argument("project", help="CyberPPT project directory.")
    source_truth_audit.add_argument("--input", required=True, help="Source Truth JSON file to audit.")
    source_truth_audit.set_defaults(func=_source_truth_audit_command)

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

    script_audit = subparsers.add_parser(
        "script-audit",
        help=(
            "Audit PPT scripts against Outline, Source Truth, composition, "
            "and argument order."
        ),
    )
    script_audit.add_argument(
        "project",
        help="CyberPPT project directory.",
    )
    script_audit.add_argument(
        "--input",
        required=True,
        help="Markdown page script to audit.",
    )
    script_audit.add_argument(
        "--outline",
        help="Outline JSON; defaults to the project Stage 01 artifact.",
    )
    script_audit.add_argument(
        "--source-truth",
        help="Source Truth JSON; defaults to the project Stage 01 artifact.",
    )
    script_audit.set_defaults(func=_script_audit_command)

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

    compile_authoring = subparsers.add_parser(
        "compile-page-script-authoring",
        help=(
            "Validate page-script-authoring.json and compile unique, "
            "chapter-scoped Markdown drafts for assemble-final-script."
        ),
    )
    compile_authoring.add_argument("project", help="CyberPPT project directory.")
    compile_authoring.add_argument(
        "--authoring",
        default="",
        help="Authoring JSON; defaults to workbench/scripts/page-script-authoring.json.",
    )
    compile_authoring.add_argument(
        "--output-dir",
        required=True,
        help="New or empty output directory for compiled chapter drafts.",
    )
    compile_authoring.set_defaults(func=_compile_page_script_authoring_command)

    prepare_outline = subparsers.add_parser(
        "prepare-outline-input",
        help="Compile deterministic Outline authoring input.",
    )
    prepare_outline.add_argument("project")
    prepare_outline.add_argument(
        "--communication-goal",
        required=True,
        help="User-selected or revised communication goal.",
    )
    prepare_outline.set_defaults(func=_prepare_outline_input_command)

    compile_outline = subparsers.add_parser(
        "compile-outline-draft",
        help="Compile a complete editable Outline draft from the semantic model, Source Truth, and selected communication goal.",
    )
    compile_outline.add_argument("project", help="CyberPPT project directory.")
    compile_outline.add_argument(
        "--communication-goal",
        required=True,
        help="User-selected or revised communication goal.",
    )
    compile_outline.add_argument(
        "--output",
        default="",
        help="Optional output path; defaults to the canonical project outline.json.",
    )
    compile_outline.add_argument(
        "--source-truth",
        default="",
        help="Optional Source Truth input; defaults to the canonical project artifact.",
    )
    compile_outline.set_defaults(func=_compile_outline_draft_command)

    prepare_page = subparsers.add_parser(
        "prepare-page-script-input",
        help="Compile deterministic page-script authoring input.",
    )
    prepare_page.add_argument("project")
    prepare_page.add_argument("--page")
    prepare_page.set_defaults(func=_prepare_page_script_input_command)

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

    rebuild_dual_image_parser = subparsers.add_parser(
        "rebuild-dual-image",
        add_help=False,
        help="Run the dual-image rebuild flow from a page_image_pairs.json manifest.",
    )
    rebuild_dual_image_parser.add_argument("rebuild_args", nargs=argparse.REMAINDER)
    rebuild_dual_image_parser.set_defaults(func=_rebuild_dual_image_command)

    final_script_pages_parser = subparsers.add_parser(
        "final-script-pages",
        help="Compile selected pages from a final script into traceable full-image PPT inputs.",
    )
    final_script_pages_parser.add_argument("project", help="CyberPPT project directory.")
    final_script_pages_parser.add_argument("--script", required=True, help="Final markdown script containing page headings.")
    final_script_pages_parser.add_argument(
        "--external-script",
        action="store_true",
        help=(
            "Accept a script supplied outside Stage 01. Skips Stage 01 approval and visual-structure gates; "
            "the script remains hash-bound in Stage 02 artifacts."
        ),
    )
    final_script_pages_parser.add_argument(
        "--lightweight-stage01-confirmed",
        action="store_true",
        help=(
            "Use the interactively confirmed lightweight Stage 01 path. "
            "Re-runs the current lightweight script audit and requires a passed, "
            "matching Stage 02 handoff and visual-structure gate; creates no approval file."
        ),
    )
    final_script_pages_parser.add_argument("--pages", required=True, help="Page range, e.g. 7-8 or 7,8.")
    final_script_pages_parser.add_argument(
        "--style-lock",
        help=(
            "Optional CyberPPT visual style lock JSON (schema cyberppt.visual_style_lock.v1). "
            "Markdown confirmation files are not accepted; use --style-id/--style-name to generate the JSON lock."
        ),
    )
    final_script_pages_parser.add_argument(
        "--style-id",
        type=int,
        choices=range(1, 11),
        metavar="1-10",
        help=(
            "Required unless --style-lock or --style-name is provided; "
            "styles 1-8 are default choices; styles 9-10 are explicit extensions."
        ),
    )
    final_script_pages_parser.add_argument(
        "--style-name",
        help="Required unless --style-lock or --style-id is provided; user-selected CyberPPT default style name or slug.",
    )
    final_script_pages_parser.add_argument("--output-dir", help="Optional output directory for page_image_pairs.json.")
    final_script_pages_parser.add_argument(
        "--build-id",
        help="Stable build identifier used for resumable, versioned Stage 02 outputs.",
    )
    final_script_pages_parser.add_argument(
        "--production-mode",
        choices=("full-image", "editable-overlay", "editable-overlay-text-reference"),
        default="full-image",
        help="Select the full-image deck path or the restored editable overlay branch.",
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
        help="Do not pass the Style 09 reference image to the image backend.",
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
        "--semantic-plan-dir",
        help="Optional semantic plan directory for an editable-overlay production mode.",
    )
    final_script_pages_parser.add_argument(
        "--require-images",
        action="store_true",
        help="Fail unless expected full image files already exist.",
    )
    final_script_pages_parser.add_argument(
        "--run-rebuild",
        action="store_true",
        help="Run template-rebuild for an editable-overlay production mode.",
    )
    final_script_pages_parser.add_argument(
        "--production-build",
        action="store_true",
        help="Run the selected production branch: image-ppt or editable template-rebuild.",
    )
    final_script_pages_parser.add_argument(
        "--blueprint-only",
        action="store_true",
        help="Only create full-image prompts and page_image_pairs.json; never report production_ready.",
    )
    final_script_pages_parser.add_argument(
        "--rebuild-arg",
        action="append",
        help="Additional argument forwarded to template-rebuild in editable-overlay mode.",
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
