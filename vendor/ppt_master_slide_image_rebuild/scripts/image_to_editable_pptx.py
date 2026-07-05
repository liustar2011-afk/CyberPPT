#!/usr/bin/env python3
"""
PPT Master - Image to Editable PPTX (slide-image-rebuild scaffold / QA entry)

Thin orchestration for slide-image-rebuild: scaffold Phase A artifacts, then
optionally run strict QA + export when svg_output/ is ready.

Usage:
    python3 scripts/image_to_editable_pptx.py --image input.png --name demo
    python3 scripts/image_to_editable_pptx.py --project projects/demo_ppt169_20260608 --stage qa
    python3 scripts/image_to_editable_pptx.py --image input.png --name demo --stage full

Examples:
    python3 scripts/image_to_editable_pptx.py --image slide.png --name reliability_closed_loop \
      --format ppt169 --text-density dense_formal_cn --stage scaffold

Dependencies:
    Repository scripts under scripts/; Phase C needs render backend
    when --render is used (default for qa/full).
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

_SCRIPTS_DIR = Path(__file__).resolve().parent
if str(_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_DIR))

from image_to_editable_pptx_lib import (  # noqa: E402
    ALLOWED_STAGES,
    STAGE_QA,
    STAGE_SCAFFOLD,
    OrchestrationConfig,
    repo_root_from_scripts,
    run_orchestration,
)
from repo_python_lib import maybe_reexec_with_venv  # noqa: E402
from slide_image_rebuild_manifest_lib import ALLOWED_TEXT_DENSITY  # noqa: E402


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Scaffold slide-image-rebuild projects and optionally run strict QA/export.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--image", type=Path, help="Reference slide image (required for scaffold/full)")
    parser.add_argument("--name", type=str, help="Project name for project_manager init (required for scaffold/full)")
    parser.add_argument(
        "--project",
        type=Path,
        help="Existing project directory (required for --stage qa)",
    )
    parser.add_argument("--format", default="ppt169", help="Canvas format (default: ppt169)")
    parser.add_argument(
        "--text-density",
        default="dense_formal_cn",
        choices=sorted(ALLOWED_TEXT_DENSITY),
        help="Manifest text_density (default: dense_formal_cn)",
    )
    parser.add_argument(
        "--stage",
        default=STAGE_SCAFFOLD,
        choices=sorted(ALLOWED_STAGES),
        help="scaffold: Phase A artifacts; qa: strict runner; full: scaffold then qa when SVG exists",
    )
    parser.add_argument(
        "--projects-dir",
        type=Path,
        default=None,
        help="Base directory for new projects (default: <repo>/projects)",
    )
    parser.add_argument("--no-preprocess", action="store_true", help="Skip preprocess_reference_image.py")
    parser.add_argument("--no-precise-lock", action="store_true", help="Do not pass --precise-lock to strict runner")
    parser.add_argument("--no-render", action="store_true", help="Do not pass --render to strict runner")
    parser.add_argument(
        "--no-aggregate-final",
        action="store_true",
        help="Do not copy/link exports/final convenience bundle after successful qa",
    )
    parser.add_argument(
        "--reference-threshold",
        type=float,
        default=58.0,
        help="Max mean pixel diff for verify_reference_similarity (default: 58)",
    )
    return parser


def _resolve_projects_dir(repo_root: Path, projects_dir: Path | None) -> Path:
    if projects_dir is not None:
        return projects_dir.resolve()
    return (repo_root / "projects").resolve()


def main(argv: list[str] | None = None) -> int:
    maybe_reexec_with_venv()
    args = build_parser().parse_args(argv)
    scripts_dir = _SCRIPTS_DIR
    repo_root = repo_root_from_scripts(scripts_dir)
    projects_dir = _resolve_projects_dir(repo_root, args.projects_dir)

    if args.stage == STAGE_QA:
        if args.project is None:
            payload = {"valid": False, "errors": ["--project is required for --stage qa"]}
            print(json.dumps(payload, ensure_ascii=False, indent=2))
            return 2
        project_root = args.project.resolve()
    else:
        if args.image is None or args.name is None:
            payload = {
                "valid": False,
                "errors": ["--image and --name are required unless --stage qa with --project"],
            }
            print(json.dumps(payload, ensure_ascii=False, indent=2))
            return 2
        if not args.image.is_file():
            payload = {"valid": False, "errors": [f"Image not found: {args.image}"]}
            print(json.dumps(payload, ensure_ascii=False, indent=2))
            return 2
        project_root = projects_dir

    config = OrchestrationConfig(
        image=args.image.resolve() if args.image else projects_dir / "placeholder.png",
        name=args.name or project_root.name,
        canvas_format=args.format,
        text_density=args.text_density,
        projects_dir=project_root if args.stage == STAGE_QA else projects_dir,
        repo_root=repo_root,
        scripts_dir=scripts_dir,
        python_executable=sys.executable,
        stage=args.stage,
        preprocess=not args.no_preprocess,
        precise_lock=not args.no_precise_lock,
        aggregate_final=not args.no_aggregate_final,
        render=not args.no_render,
        reference_threshold=args.reference_threshold,
    )

    result = run_orchestration(config)
    print(json.dumps(result.as_dict(), ensure_ascii=False, indent=2))
    if not result.valid:
        return 1
    if args.stage == "full" and result.errors:
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
