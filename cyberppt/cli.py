"""CyberPPT product command line interface."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from cyberppt import __version__
from cyberppt.commands.assemble_final_script import assemble_final_script
from cyberppt.commands.final_script_pages import run_final_script_pages
from cyberppt.commands.init_project import init_project
from cyberppt.commands.outline_audit import run_outline_audit
from cyberppt.commands.script_audit import run_script_audit
from cyberppt.commands.script_gate import approve_script, get_script_status, stage_script, status_as_json
from cyberppt.commands.script_runner import SCRIPT_ALIASES, run_script
from cyberppt.commands.source_truth_audit import run_source_truth_audit
from cyberppt.paths import ASSETS_DIR, REFERENCES_DIR, SCRIPTS_DIR, SKILL_FILE
from cyberppt.stage01_controls import (
    write_confirmation_request,
    write_escalation_decision,
    write_stage01_approval,
)


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
            max_attempts=args.max_attempts,
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
            max_attempts=args.max_attempts,
        )
    except (FileNotFoundError, ValueError) as exc:
        print(str(exc), file=sys.stderr)
        return 2
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return code


def _script_audit_command(args: argparse.Namespace) -> int:
    try:
        code, report = run_script_audit(
            Path(args.project),
            Path(args.input),
            outline_path=Path(args.outline) if args.outline else None,
            source_truth_path=(
                Path(args.source_truth) if args.source_truth else None
            ),
            attempt=args.attempt,
            max_attempts=args.max_attempts,
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
        )
    except (FileNotFoundError, ValueError) as exc:
        print(str(exc), file=sys.stderr)
        return 2
    print(json.dumps(report, ensure_ascii=False, indent=2))
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


def _resolve_escalation_command(args: argparse.Namespace) -> int:
    try:
        path = write_escalation_decision(
            Path(args.project),
            gate=args.gate,
            option_id=args.option,
            note=args.note,
        )
    except (FileNotFoundError, ValueError) as exc:
        print(str(exc), file=sys.stderr)
        return 2
    print(f"escalation_decision_recorded: {path}")
    return 0


def _confirmation_request_command(args: argparse.Namespace) -> int:
    try:
        path = write_confirmation_request(Path(args.project), args.kind)
    except (FileNotFoundError, RuntimeError, ValueError) as exc:
        print(str(exc), file=sys.stderr)
        return 2
    print(f"confirmation_request: {path}")
    return 0


def _approve_stage01_command(args: argparse.Namespace) -> int:
    try:
        path = write_stage01_approval(
            Path(args.project),
            kind=args.kind,
            note=args.note,
        )
    except (FileNotFoundError, ValueError) as exc:
        print(str(exc), file=sys.stderr)
        return 2
    print(f"stage01_approval_recorded: {path}")
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


def _rebuild_dual_image_command(args: argparse.Namespace) -> int:
    return run_script("template-rebuild", args.rebuild_args)


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

    init = subparsers.add_parser("init", help="Create a CyberPPT project workspace.")
    init.add_argument("path", help="Target project directory.")
    init.add_argument("--force", action="store_true", help="Overwrite generated project manifest and README.")
    init.set_defaults(func=_init_command)

    outline_audit = subparsers.add_parser(
        "outline-audit",
        help="Audit a Stage 01 outline and direct rewrite or escalation.",
    )
    outline_audit.add_argument("project", help="CyberPPT project directory.")
    outline_audit.add_argument("--input", required=True, help="Outline JSON file to audit.")
    outline_audit.add_argument(
        "--source-truth",
        help="Optional Source Truth JSON; defaults to the project Stage 01 artifact.",
    )
    outline_audit.add_argument(
        "--max-attempts",
        type=int,
        default=3,
        help="Maximum changed-direction attempts (1-5; default: 3).",
    )
    outline_audit.set_defaults(func=_outline_audit_command)

    source_truth_audit = subparsers.add_parser(
        "source-truth-audit",
        help="Audit Stage 01 source evidence, change extraction direction, and render Markdown.",
    )
    source_truth_audit.add_argument("project", help="CyberPPT project directory.")
    source_truth_audit.add_argument("--input", required=True, help="Source Truth JSON file to audit.")
    source_truth_audit.add_argument(
        "--max-attempts",
        type=int,
        default=3,
        help="Maximum changed-direction attempts (1-5; default: 3).",
    )
    source_truth_audit.set_defaults(func=_source_truth_audit_command)

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
    script_audit.add_argument(
        "--attempt",
        type=int,
        help="Explicit attempt number; defaults to the next persisted attempt.",
    )
    script_audit.add_argument(
        "--max-attempts",
        type=int,
        default=3,
        help="Maximum changed-direction attempts (1-5; default: 3).",
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
    assemble_final.set_defaults(func=_assemble_final_script_command)

    resolve_escalation = subparsers.add_parser(
        "resolve-escalation",
        help="Record a user decision for an open Stage 01 exit-5 escalation.",
    )
    resolve_escalation.add_argument("project", help="CyberPPT project directory.")
    resolve_escalation.add_argument(
        "--gate",
        required=True,
        choices=["source_truth", "outline", "script"],
        help="Which escalation gate to resolve.",
    )
    resolve_escalation.add_argument(
        "--option",
        required=True,
        help="option_id from the escalation JSON options list.",
    )
    resolve_escalation.add_argument("--note", default="", help="Optional decision note.")
    resolve_escalation.set_defaults(func=_resolve_escalation_command)

    confirmation_request = subparsers.add_parser(
        "confirmation-request",
        help="Generate a Stage 01 confirmation request with audit summary and open questions.",
    )
    confirmation_request.add_argument("project", help="CyberPPT project directory.")
    confirmation_request.add_argument(
        "--kind",
        required=True,
        choices=["outline", "script"],
        help="Outline confirmation or script confirmation.",
    )
    confirmation_request.set_defaults(func=_confirmation_request_command)

    approve_stage01 = subparsers.add_parser(
        "approve-stage01",
        help="Record Stage 01 outline/script approval after a valid confirmation request.",
    )
    approve_stage01.add_argument("project", help="CyberPPT project directory.")
    approve_stage01.add_argument(
        "--kind",
        required=True,
        choices=["outline", "script"],
        help="Approve outline or script.",
    )
    approve_stage01.add_argument("--note", default="", help="Optional approval note.")
    approve_stage01.set_defaults(func=_approve_stage01_command)

    stage_script_parser = subparsers.add_parser(
        "stage-script",
        help="Save a per-slide script or ImageGen prompt before generation.",
    )
    stage_script_parser.add_argument("project", help="CyberPPT project directory.")
    stage_script_parser.add_argument("--slide", type=int, required=True, help="Slide number, 1-based.")
    stage_script_parser.add_argument(
        "--kind",
        choices=["analysis", "blueprint", "imagegen", "pptx"],
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
        choices=["analysis", "blueprint", "imagegen", "pptx"],
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
        choices=["analysis", "blueprint", "imagegen", "pptx"],
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
    final_script_pages_parser.add_argument("--pages", required=True, help="Page range, e.g. 7-8 or 7,8.")
    final_script_pages_parser.add_argument("--style-lock", help="Optional project visual lock file.")
    final_script_pages_parser.add_argument(
        "--style-id",
        type=int,
        choices=range(1, 10),
        metavar="1-9",
        help=(
            "Required unless --style-lock or --style-name is provided; "
            "styles 1-8 are default choices and style 9 is an explicit extension."
        ),
    )
    final_script_pages_parser.add_argument(
        "--style-name",
        help="Required unless --style-lock or --style-id is provided; user-selected CyberPPT default style name or slug.",
    )
    final_script_pages_parser.add_argument("--output-dir", help="Optional output directory for page_image_pairs.json.")
    final_script_pages_parser.add_argument(
        "--semantic-plan-dir",
        help="Unsupported in the Stage 02 full-image path; kept only to fail closed for old commands.",
    )
    final_script_pages_parser.add_argument(
        "--require-images",
        action="store_true",
        help="Fail unless expected full image files already exist.",
    )
    final_script_pages_parser.add_argument(
        "--run-rebuild",
        action="store_true",
        help="Unsupported in final-script-pages; Stage 02 now uses image-ppt instead of template-rebuild.",
    )
    final_script_pages_parser.add_argument(
        "--production-build",
        action="store_true",
        help="Run Stage 02 as a full-image PPT build through image-ppt.",
    )
    final_script_pages_parser.add_argument(
        "--blueprint-only",
        action="store_true",
        help="Only create full-image prompts and page_image_pairs.json; never report production_ready.",
    )
    final_script_pages_parser.add_argument(
        "--rebuild-arg",
        action="append",
        help="Unsupported legacy option for old template-rebuild commands.",
    )
    final_script_pages_parser.set_defaults(func=_final_script_pages_command)

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
