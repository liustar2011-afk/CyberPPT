#!/usr/bin/env python3
"""
PPT Master - Strict Slide Image Rebuild Runner

Orchestrate slide-image-rebuild quality gates and export with a single strict entry.
Writes exports/qa/strict_run_report.json (full) and strict_run_summary.json (agent triage).

Usage:
    python3 scripts/run_slide_image_rebuild_strict.py --project projects/demo
    python3 scripts/run_slide_image_rebuild_strict.py --project projects/demo --stage pre-export --render
    python3 scripts/run_slide_image_rebuild_strict.py --project projects/demo --stage full --precise-lock --render
    python3 scripts/run_slide_image_rebuild_strict.py --project projects/demo --stage svg --agent-summary

Examples:
    python3 scripts/run_slide_image_rebuild_strict.py --project projects/demo --stage intake
    python3 scripts/run_slide_image_rebuild_strict.py --project projects/demo --skip-export --stage svg --render --agent-summary

Dependencies:
    Repository scripts under scripts/; Cairo when --render is used.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

_SCRIPTS_DIR = Path(__file__).resolve().parent
if str(_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_DIR))

from repo_python_lib import maybe_reexec_with_venv  # noqa: E402
from slide_image_rebuild_strict_lib import (  # noqa: E402
    RunConfig,
    repo_root_from_scripts,
    resolve_modes,
    resolve_precise_lock,
    resolve_strict_preview_render_backend,
    run_pipeline,
    stage_index,
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Run strict slide-image-rebuild gates and optional export.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "project_pos",
        type=Path,
        nargs="?",
        default=None,
        help="Project directory (positional alias for --project)",
    )
    parser.add_argument("--project", type=Path, default=None, help="Project directory")
    parser.add_argument("--reference", type=Path, default=None, help="Reference image for optional preprocess")
    parser.add_argument(
        "--rebuild-mode",
        default="auto",
        choices=["auto", "vector-hifi", "text-editable-snapshot", "full-editable", "hifi", "editable", "wps-hifi"],
        help="Rebuild mode (default: auto from manifest)",
    )
    parser.add_argument(
        "--export-mode",
        default="auto",
        choices=["auto", "hifi", "editable", "wps-hifi"],
        help="PPTX export mode (default: auto from manifest)",
    )
    parser.add_argument("--precise-lock", action="store_true", help="Force icon contract and precise rebuild lock")
    parser.add_argument(
        "--reference-threshold",
        type=float,
        default=58.0,
        help="Max mean pixel diff for verify_reference_similarity (default: 58)",
    )
    parser.add_argument(
        "--icon-enforce",
        action="store_true",
        help="Pass --enforce to verify_icon_contract and require icon_manifest.json",
    )
    parser.add_argument("--render", action="store_true", help="Run render-dependent preview and similarity checks")
    parser.add_argument(
        "--stage",
        default="pre-export",
        choices=[
            "bootstrap",
            "intake",
            "layout",
            "mapped",
            "icon",
            "svg",
            "pre-export",
            "export",
            "post-export",
            "package",
            "full",
        ],
        help="Last stage to run (default: pre-export)",
    )
    parser.add_argument("--stop-on-error", action="store_true", default=True, help="Stop at first hard failure")
    parser.add_argument("--no-stop-on-error", dest="stop_on_error", action="store_false")
    parser.add_argument("--dry-run", action="store_true", help="List steps without executing commands")
    parser.add_argument("--skip-export", action="store_true", help="Do not run export/post-export/package stages")
    parser.add_argument(
        "--agent-summary",
        action="store_true",
        help="Print strict_run_summary.json to stdout instead of the full report (summary is always written)",
    )
    parser.add_argument(
        "--auto-repair",
        action="store_true",
        help="After repair_tasks aggregation, apply safe auto patches (<=5px drift, text reflow) then re-enforce",
    )
    parser.add_argument(
        "--incremental",
        action="store_true",
        help="Skip svg-stage re-verification when svg_output/ is byte-identical to the last validated run (opt-in; default off)",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    maybe_reexec_with_venv()
    args = build_parser().parse_args(argv)
    scripts_dir = _SCRIPTS_DIR
    repo_root = repo_root_from_scripts(scripts_dir)
    project_arg = args.project if args.project is not None else args.project_pos
    if project_arg is None:
        payload = {
            "valid": False,
            "errors": ["Project directory required: pass it positionally or via --project"],
        }
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return 1
    project = project_arg.resolve()
    if not project.is_dir():
        payload = {
            "valid": False,
            "errors": [f"Project directory not found: {project}"],
        }
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return 1

    stage_requested = args.stage
    if args.skip_export and stage_index(stage_requested) > stage_index("svg"):
        stage_requested = "svg"

    rebuild_mode, export_mode = resolve_modes(project, args.rebuild_mode, args.export_mode)
    precise_lock = resolve_precise_lock(project, args.precise_lock)
    render = args.render or stage_index(stage_requested) >= stage_index("svg")
    preview_render_backend = resolve_strict_preview_render_backend(project)

    config = RunConfig(
        project=project,
        reference=args.reference.resolve() if args.reference else None,
        rebuild_mode=rebuild_mode,
        export_mode=export_mode,
        precise_lock=precise_lock,
        render=render,
        stage_requested=stage_requested,
        stop_on_error=args.stop_on_error,
        dry_run=args.dry_run,
        skip_export=args.skip_export,
        preview_render_backend=preview_render_backend,
        repo_root=repo_root,
        scripts_dir=scripts_dir,
        agent_summary_stdout=args.agent_summary,
        reference_threshold=args.reference_threshold,
        icon_enforce=args.icon_enforce,
        auto_repair=args.auto_repair,
        incremental=args.incremental,
    )
    report = run_pipeline(config)
    payload = report.get("agent_summary", report) if config.agent_summary_stdout else report
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0 if report.get("valid") else 1


if __name__ == "__main__":
    raise SystemExit(main())
