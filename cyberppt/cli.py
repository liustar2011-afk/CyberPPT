"""CyberPPT product command line interface."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from cyberppt import __version__
from cyberppt.commands.init_project import init_project
from cyberppt.commands.script_gate import approve_script, get_script_status, stage_script, status_as_json
from cyberppt.commands.script_runner import SCRIPT_ALIASES, run_script
from cyberppt.paths import ASSETS_DIR, REFERENCES_DIR, SCRIPTS_DIR, SKILL_FILE


def _doctor() -> int:
    checks = {
        "skill": SKILL_FILE.exists(),
        "references": REFERENCES_DIR.exists() and any(REFERENCES_DIR.glob("*.md")),
        "palette_samples": len(list((ASSETS_DIR / "palette-samples").glob("palette-*.png"))) == 8,
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
