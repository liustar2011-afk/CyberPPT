"""CyberPPT product command line interface."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from cyberppt import __version__
from cyberppt.commands.analysis_expression_gate import (
    GATE_ORDER,
    adopt_analysis_expression_contract,
    analysis_expression_status_as_json,
    approve_analysis_artifact,
    get_analysis_expression_status,
    stage_analysis_artifact,
)
from cyberppt.commands.blueprint_gate import (
    approve_blueprint_input,
    approve_blueprint_image_review,
    approve_speaker_notes_review,
    approve_visual_style,
    stage_blueprint_input,
    stage_blueprint_image_review,
    stage_speaker_notes_review,
    stage_visual_style_options,
)
from cyberppt.commands.final_script_pages import run_final_script_pages
from cyberppt.commands.imagegen_run import run_imagegen_page
from cyberppt.commands.image_text_qa import run_project_image_text_qa
from cyberppt.commands.init_project import init_project
from cyberppt.commands.produce import (
    assemble_production,
    get_production_status,
    prepare_editable_text_production,
    prepare_production,
    verify_production,
)
from cyberppt.commands.script_gate import approve_script, get_script_status, stage_script, status_as_json
from cyberppt.commands.script_runner import _STAGE_2_PLUS_GENERATION_ALIASES, SCRIPT_ALIASES, run_script
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


def _stage_analysis_expression_command(args: argparse.Namespace) -> int:
    try:
        options = json.loads(args.options_json)
        if not isinstance(options, list):
            raise ValueError("--options-json must decode to a JSON array")
        pending = stage_analysis_artifact(
            Path(args.project),
            args.gate,
            Path(args.source).read_text(encoding="utf-8"),
            args.recommendation,
            options,
            args.question,
        )
    except (FileNotFoundError, ValueError, json.JSONDecodeError) as exc:
        print(str(exc), file=sys.stderr)
        return 2
    print(f"pending_confirmation: {pending}")
    return 0


def _approve_analysis_expression_command(args: argparse.Namespace) -> int:
    try:
        approval = approve_analysis_artifact(Path(args.project), args.gate, args.option_id, args.note)
    except (FileNotFoundError, ValueError) as exc:
        print(str(exc), file=sys.stderr)
        return 2
    print(f"approval_recorded: {approval}")
    return 0


def _analysis_expression_status_command(args: argparse.Namespace) -> int:
    status = get_analysis_expression_status(Path(args.project))
    if args.json:
        print(analysis_expression_status_as_json(status))
    else:
        print(f"adopted: {'yes' if status.adopted else 'no'}")
        print(f"next_gate: {status.next_gate or 'none'}")
        for gate in GATE_ORDER:
            gate_status = status.gates.get(gate, {"status": "not_applicable"})
            print(f"{gate}: {gate_status['status']}")
            if gate_status["status"] == "pending_confirmation":
                print(f"  recommendation: {gate_status.get('recommendation', '')}")
                print(f"  question: {gate_status.get('question', '')}")
                print(f"  options: {json.dumps(gate_status.get('options', []), ensure_ascii=False)}")
            failures = gate_status.get("validation_failures", [])
            if failures:
                print(f"  validation_failures: {json.dumps(failures, ensure_ascii=False)}")
    return 0 if status.adopted and status.next_gate is None else 3


def _adopt_analysis_expression_contract_command(args: argparse.Namespace) -> int:
    contract = adopt_analysis_expression_contract(Path(args.project))
    status = get_analysis_expression_status(Path(args.project))
    print(f"analysis_expression_contract: {contract}")
    print(f"next_gate: {status.next_gate or 'none'}")
    return 0


def _stage_visual_style_command(args: argparse.Namespace) -> int:
    try:
        pending = stage_visual_style_options(Path(args.project))
    except (FileNotFoundError, ValueError) as exc:
        print(str(exc), file=sys.stderr)
        return 2
    print(f"pending_confirmation: {pending}")
    return 0


def _approve_visual_style_command(args: argparse.Namespace) -> int:
    try:
        approval = approve_visual_style(Path(args.project), args.option_id, args.note)
    except (FileNotFoundError, ValueError) as exc:
        print(str(exc), file=sys.stderr)
        return 2
    print(f"approval_recorded: {approval}")
    return 0


def _stage_blueprint_input_command(args: argparse.Namespace) -> int:
    try:
        options = json.loads(args.options_json)
        if not isinstance(options, list):
            raise ValueError("--options-json must decode to a JSON array")
        pending = stage_blueprint_input(
            Path(args.project),
            Path(args.source).read_text(encoding="utf-8"),
            args.recommendation,
            options,
            args.question,
        )
    except (FileNotFoundError, ValueError, json.JSONDecodeError) as exc:
        print(str(exc), file=sys.stderr)
        return 2
    print(f"pending_confirmation: {pending}")
    return 0


def _approve_blueprint_input_command(args: argparse.Namespace) -> int:
    try:
        approval = approve_blueprint_input(Path(args.project), args.option_id, args.note)
    except (FileNotFoundError, ValueError) as exc:
        print(str(exc), file=sys.stderr)
        return 2
    print(f"approval_recorded: {approval}")
    return 0


def _stage_blueprint_image_review_command(args: argparse.Namespace) -> int:
    try:
        pending = stage_blueprint_image_review(Path(args.project), Path(args.manifest))
    except (FileNotFoundError, ValueError) as exc:
        print(str(exc), file=sys.stderr)
        return 2
    print(f"pending_confirmation: {pending}")
    return 0


def _approve_blueprint_image_review_command(args: argparse.Namespace) -> int:
    try:
        approval = approve_blueprint_image_review(Path(args.project), args.option_id, args.note)
    except (FileNotFoundError, ValueError) as exc:
        print(str(exc), file=sys.stderr)
        return 2
    print(f"approval_recorded: {approval}")
    return 0


def _stage_speaker_notes_review_command(args: argparse.Namespace) -> int:
    try:
        pending = stage_speaker_notes_review(Path(args.project), Path(args.manifest), args.pages)
    except (FileNotFoundError, ValueError) as exc:
        print(str(exc), file=sys.stderr)
        return 2
    print(f"pending_confirmation: {pending}")
    return 0


def _approve_speaker_notes_review_command(args: argparse.Namespace) -> int:
    try:
        approval = approve_speaker_notes_review(Path(args.project), args.option_id, args.note)
    except (FileNotFoundError, ValueError) as exc:
        print(str(exc), file=sys.stderr)
        return 2
    print(f"approval_recorded: {approval}")
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
            require_images=args.require_images,
            production_build=args.production_build,
        )
    except (FileNotFoundError, RuntimeError, ValueError) as exc:
        print(str(exc), file=sys.stderr)
        return 2
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


def _produce_prepare_command(args: argparse.Namespace) -> int:
    try:
        result = prepare_production(Path(args.project), args.pages)
    except (FileNotFoundError, RuntimeError, ValueError) as exc:
        print(str(exc), file=sys.stderr)
        return 2
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


def _produce_status_command(args: argparse.Namespace) -> int:
    result = get_production_status(Path(args.project), args.pages)
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(f"status: {result['status']}")
        print(f"next_gate: {result.get('next_gate', 'none')}")
        print(f"next_command: {result.get('next_command', '')}")
        for failure in result.get("failures", []):
            print(f"failure: {failure}")
    return 0


def _produce_assemble_command(args: argparse.Namespace) -> int:
    try:
        result = assemble_production(Path(args.project), args.pages)
    except (FileNotFoundError, RuntimeError, ValueError) as exc:
        print(str(exc), file=sys.stderr)
        return 2
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


def _produce_editable_text_command(args: argparse.Namespace) -> int:
    try:
        result = prepare_editable_text_production(Path(args.project), args.pages, input_mode=args.input_mode)
    except (FileNotFoundError, RuntimeError, ValueError) as exc:
        print(str(exc), file=sys.stderr)
        return 2
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


def _produce_verify_command(args: argparse.Namespace) -> int:
    try:
        result = verify_production(Path(args.project), args.pages)
    except (FileNotFoundError, RuntimeError, ValueError) as exc:
        print(str(exc), file=sys.stderr)
        return 2
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


def _image_text_qa_command(args: argparse.Namespace) -> int:
    try:
        result = run_project_image_text_qa(
            Path(args.project),
            args.pages,
            ocr_json=Path(args.ocr_json) if args.ocr_json else None,
            model=args.model,
        )
    except (FileNotFoundError, RuntimeError, ValueError) as exc:
        print(str(exc), file=sys.stderr)
        return 2
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


def _imagegen_run_command(args: argparse.Namespace) -> int:
    try:
        result = run_imagegen_page(Path(args.project), args.pages, model=args.model)
    except (FileNotFoundError, RuntimeError, ValueError) as exc:
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

    for gate in GATE_ORDER:
        stage_parser = subparsers.add_parser(
            f"stage-{gate.replace('_', '-')}",
            help=f"Stage the {gate.replace('_', ' ')} artifact for confirmation.",
        )
        stage_parser.add_argument("project", help="CyberPPT project directory.")
        stage_parser.add_argument("--source", required=True, help="UTF-8 Markdown artifact file.")
        stage_parser.add_argument("--recommendation", required=True, help="Recommended confirmation option.")
        stage_parser.add_argument("--question", help="Question recorded in the pending confirmation.")
        stage_parser.add_argument("--options-json", required=True, help="JSON array of selectable confirmation options.")
        stage_parser.set_defaults(func=_stage_analysis_expression_command, gate=gate)

        approve_parser = subparsers.add_parser(
            f"approve-{gate.replace('_', '-')}",
            help=f"Record a selected confirmation option for {gate.replace('_', ' ')}.",
        )
        approve_parser.add_argument("project", help="CyberPPT project directory.")
        approve_parser.add_argument("--option-id", required=True, help="Selected confirmation option id.")
        approve_parser.add_argument("--note", default="", help="Optional approval note.")
        approve_parser.set_defaults(func=_approve_analysis_expression_command, gate=gate)

    analysis_status_parser = subparsers.add_parser(
        "analysis-expression-status",
        help="Show project-level analysis-expression approvals and pending choices.",
    )
    analysis_status_parser.add_argument("project", help="CyberPPT project directory.")
    analysis_status_parser.add_argument("--json", action="store_true", help="Print machine-readable status.")
    analysis_status_parser.set_defaults(func=_analysis_expression_status_command)

    adopt_analysis_parser = subparsers.add_parser(
        "adopt-analysis-expression-contract",
        help="Adopt the analysis-expression contract for an existing project without overwriting artifacts.",
    )
    adopt_analysis_parser.add_argument("project", help="CyberPPT project directory.")
    adopt_analysis_parser.set_defaults(func=_adopt_analysis_expression_contract_command)

    stage_visual_style_parser = subparsers.add_parser(
        "stage-visual-style",
        help="Persist the selectable visual styles after business-script approval.",
    )
    stage_visual_style_parser.add_argument("project", help="CyberPPT project directory.")
    stage_visual_style_parser.set_defaults(func=_stage_visual_style_command)

    approve_visual_style_parser = subparsers.add_parser(
        "approve-visual-style",
        help="Record the selected visual style and write its locked prompt contract.",
    )
    approve_visual_style_parser.add_argument("project", help="CyberPPT project directory.")
    approve_visual_style_parser.add_argument("--option-id", required=True, help="Selected style option id, e.g. style_4.")
    approve_visual_style_parser.add_argument("--note", default="", help="Optional approval note.")
    approve_visual_style_parser.set_defaults(func=_approve_visual_style_command)

    stage_blueprint_input_parser = subparsers.add_parser(
        "stage-blueprint-input",
        help="Stage the reviewed, style-bound drawing input before image generation.",
    )
    stage_blueprint_input_parser.add_argument("project", help="CyberPPT project directory.")
    stage_blueprint_input_parser.add_argument("--source", required=True, help="UTF-8 Markdown drawing input.")
    stage_blueprint_input_parser.add_argument("--recommendation", required=True, help="Recommended confirmation option.")
    stage_blueprint_input_parser.add_argument("--question", help="Question recorded in the pending confirmation.")
    stage_blueprint_input_parser.add_argument("--options-json", required=True, help="JSON array of selectable confirmation options.")
    stage_blueprint_input_parser.set_defaults(func=_stage_blueprint_input_command)

    approve_blueprint_input_parser = subparsers.add_parser(
        "approve-blueprint-input",
        help="Record approval of drawing input before image generation.",
    )
    approve_blueprint_input_parser.add_argument("project", help="CyberPPT project directory.")
    approve_blueprint_input_parser.add_argument("--option-id", required=True, help="Selected confirmation option id.")
    approve_blueprint_input_parser.add_argument("--note", default="", help="Optional approval note.")
    approve_blueprint_input_parser.set_defaults(func=_approve_blueprint_input_command)

    stage_blueprint_image_review_parser = subparsers.add_parser(
        "stage-blueprint-image-review",
        help="Save generated full images as a separate review artifact before PPT assembly.",
    )
    stage_blueprint_image_review_parser.add_argument("project", help="CyberPPT project directory.")
    stage_blueprint_image_review_parser.add_argument("--manifest", required=True, help="Generated page_image_pairs.json file.")
    stage_blueprint_image_review_parser.set_defaults(func=_stage_blueprint_image_review_command)

    approve_blueprint_image_review_parser = subparsers.add_parser(
        "approve-blueprint-image-review",
        help="Record approval of generated full images before image-PPT assembly.",
    )
    approve_blueprint_image_review_parser.add_argument("project", help="CyberPPT project directory.")
    approve_blueprint_image_review_parser.add_argument("--option-id", required=True, help="Selected confirmation option id.")
    approve_blueprint_image_review_parser.add_argument("--note", default="", help="Optional approval note.")
    approve_blueprint_image_review_parser.set_defaults(func=_approve_blueprint_image_review_command)

    stage_speaker_notes_review_parser = subparsers.add_parser(
        "stage-speaker-notes-review",
        help="Stage generated speaker notes for explicit review before image-PPT assembly.",
    )
    stage_speaker_notes_review_parser.add_argument("project", help="CyberPPT project directory.")
    stage_speaker_notes_review_parser.add_argument("--manifest", required=True, help="Generated speaker_notes_manifest.json file.")
    stage_speaker_notes_review_parser.add_argument("--pages", required=True, help="Page range represented by the speaker notes.")
    stage_speaker_notes_review_parser.set_defaults(func=_stage_speaker_notes_review_command)

    approve_speaker_notes_review_parser = subparsers.add_parser(
        "approve-speaker-notes-review",
        help="Record the speaker-notes review decision before image-PPT assembly.",
    )
    approve_speaker_notes_review_parser.add_argument("project", help="CyberPPT project directory.")
    approve_speaker_notes_review_parser.add_argument("--option-id", required=True, help="Selected speaker-notes review option id.")
    approve_speaker_notes_review_parser.add_argument("--note", default="", help="Optional approval note.")
    approve_speaker_notes_review_parser.set_defaults(func=_approve_speaker_notes_review_command)

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
        choices=range(1, 9),
        metavar="1-8",
        help="Required unless --style-lock or --style-name is provided; user-selected CyberPPT default visual style id.",
    )
    final_script_pages_parser.add_argument(
        "--style-name",
        help="Required unless --style-lock or --style-id is provided; user-selected CyberPPT default style name or slug.",
    )
    final_script_pages_parser.add_argument("--output-dir", help="Optional output directory for page_image_pairs.json.")
    final_script_pages_parser.add_argument(
        "--require-images",
        action="store_true",
        help="Fail unless expected full image files already exist.",
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
    final_script_pages_parser.set_defaults(func=_final_script_pages_command)

    image_text_qa_parser = subparsers.add_parser(
        "image-text-qa", help="Check generated full-image text against the approved page content."
    )
    image_text_qa_parser.add_argument("project", help="CyberPPT project directory.")
    image_text_qa_parser.add_argument("--pages", required=True, help="Page range, e.g. 7-8 or 7,8.")
    image_text_qa_parser.add_argument("--ocr-json", help="Offline OCR fixture JSON for deterministic review/tests.")
    image_text_qa_parser.add_argument("--model", help="Optional Codex vision model for live OCR.")
    image_text_qa_parser.set_defaults(func=_image_text_qa_command)

    imagegen_run_parser = subparsers.add_parser(
        "imagegen-run", help="Generate exactly one approved content page from its current manifest."
    )
    imagegen_run_parser.add_argument("project", help="CyberPPT project directory.")
    imagegen_run_parser.add_argument("--pages", required=True, help="Exactly one approved content-page number.")
    imagegen_run_parser.add_argument("--model", help="Optional Codex image model.")
    imagegen_run_parser.set_defaults(func=_imagegen_run_command)

    produce_parser = subparsers.add_parser("produce", help="Run the project-scoped production state machine.")
    produce_subparsers = produce_parser.add_subparsers(dest="produce_command", required=True)
    produce_prepare_parser = produce_subparsers.add_parser(
        "prepare", help="Compile approved inputs and stage speaker notes for review."
    )
    produce_prepare_parser.add_argument("project", help="CyberPPT project directory.")
    produce_prepare_parser.add_argument("--pages", required=True, help="Page range, e.g. 7-8 or 7,8.")
    produce_prepare_parser.set_defaults(func=_produce_prepare_command)
    produce_assemble_parser = produce_subparsers.add_parser(
        "assemble", help="Assemble approved images, notes, and template text into a PPTX."
    )
    produce_assemble_parser.add_argument("project", help="CyberPPT project directory.")
    produce_assemble_parser.add_argument("--pages", required=True, help="Page range, e.g. 7-8 or 7,8.")
    produce_assemble_parser.set_defaults(func=_produce_assemble_command)
    produce_editable_parser = produce_subparsers.add_parser(
        "editable-text", help="Run the editable-body two-image or three-image page pipeline."
    )
    produce_editable_parser.add_argument("project", help="CyberPPT project directory.")
    produce_editable_parser.add_argument("--pages", required=True, help="Page range, e.g. 7-8 or 7,8.")
    produce_editable_parser.add_argument(
        "--input-mode",
        choices=("two-image", "three-image"),
        default="two-image",
        help="Vendor input mode. Defaults to two-image; use three-image only when a TEXT image is required.",
    )
    produce_editable_parser.set_defaults(func=_produce_editable_text_command)
    produce_verify_parser = produce_subparsers.add_parser(
        "verify", help="Run render QA, strict validation, and promote a deliverable PPTX."
    )
    produce_verify_parser.add_argument("project", help="CyberPPT project directory.")
    produce_verify_parser.add_argument("--pages", required=True, help="Page range, e.g. 7-8 or 7,8.")
    produce_verify_parser.set_defaults(func=_produce_verify_command)
    produce_status_parser = produce_subparsers.add_parser(
        "status", help="Show the next legal production transition."
    )
    produce_status_parser.add_argument("project", help="CyberPPT project directory.")
    produce_status_parser.add_argument("--pages", required=True, help="Page range, e.g. 7-8 or 7,8.")
    produce_status_parser.add_argument("--json", action="store_true", help="Emit machine-readable status.")
    produce_status_parser.set_defaults(func=_produce_status_command)

    for alias in sorted(SCRIPT_ALIASES):
        help_text = f"Run scripts/{SCRIPT_ALIASES[alias]}."
        if alias in _STAGE_2_PLUS_GENERATION_ALIASES:
            help_text = f"{alias} requires --project <path>. {help_text}"
        command = subparsers.add_parser(alias, add_help=False, help=help_text)
        command.add_argument("script_args", nargs=argparse.REMAINDER)
        command.set_defaults(func=lambda args, alias=alias: run_script(alias, args.script_args))

    return parser


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    try:
        if argv and argv[0] in SCRIPT_ALIASES:
            return run_script(argv[0], argv[1:])
        parser = build_parser()
        args = parser.parse_args(argv)
        if not hasattr(args, "func"):
            parser.print_help()
            return 0
        return int(args.func(args))
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        return 2
