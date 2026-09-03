"""Explicit Stage 02 build-state classification.

The production runtime historically represented both expected Agent work and
real failures through exceptions. This module gives manifests a stable state
model so orchestration can distinguish resumable human/Agent actions from
terminal errors without guessing from command exit codes.
"""

from __future__ import annotations

import argparse
import json
from contextlib import contextmanager
from contextvars import ContextVar
from pathlib import Path
from typing import Any, Mapping

from .models import Stage02BuildContext


_active_production: ContextVar[Stage02BuildContext | None] = ContextVar("stage02_production", default=None)


@contextmanager
def _production_invocation(context: Stage02BuildContext):
    """Invocation-local guard, owned by the orchestrator; never a disk receipt."""
    token = _active_production.set(context)
    try:
        yield
    finally:
        _active_production.reset(token)


def require_production_invocation(*, project, manifest_path, output_dir, requested_pages, assembly_mode) -> None:
    context = _active_production.get()
    if context is None:
        raise ValueError("STAGE02_OFFICIAL_ENTRY_REQUIRED: use .venv/bin/python3 -m cyberppt final-script-pages --production-build; a build_context.json alone cannot authorize direct adapter calls")
    if (
        Path(project).resolve() != context.project.resolve()
        or Path(manifest_path).resolve() != (context.build_dir / "page_image_pairs.json").resolve()
        or Path(output_dir).resolve() != (context.build_dir / "editable_svg").resolve()
        or tuple(requested_pages) != context.selected_pages
        or assembly_mode != context.assembly_mode
    ):
        raise ValueError("STAGE02_INVOCATION_MISMATCH: project, build directory, pages and assembly mode must match the active production run")


READY_FOR_IMAGE = "ready_for_image_generation"
NEEDS_IMAGE = "needs_image_generation"
IMAGE_AUDITED = "image_audited"
NEEDS_SVG_AUTHORING = "needs_svg_authoring"
NEEDS_VISUAL_REVIEW = "needs_visual_review"
VISUAL_REVIEW_FAILED = "visual_review_failed"
PAGE_READY = "page_ready_for_assembly"
FAILED = "failed"
PRODUCTION_READY = "production_ready"

ACTION_STATES = frozenset({NEEDS_IMAGE, NEEDS_SVG_AUTHORING, NEEDS_VISUAL_REVIEW, VISUAL_REVIEW_FAILED})
TERMINAL_FAILURE_STATES = frozenset({FAILED})


def _path(value: object) -> Path:
    return Path(str(value or "")).expanduser()


def classify_page(pair: Mapping[str, Any]) -> dict[str, Any]:
    page_number = int(pair.get("page_number") or 0)
    full = pair.get("full") if isinstance(pair.get("full"), Mapping) else {}
    full_path = _path(full.get("path"))
    text_audit = full.get("text_audit") if isinstance(full.get("text_audit"), Mapping) else {}
    full_audited = full.get("status") == "Generated" and full_path.is_file() and text_audit.get("valid") is True

    if not full_audited:
        last_error = str(full.get("last_error") or "").strip()
        return {
            "page": page_number,
            "state": FAILED if last_error else NEEDS_IMAGE,
            "action": None if last_error else "generate_and_audit_full_image",
            "error": last_error or None,
        }

    authored = _path(pair.get("authoring_svg"))
    checkpoint = pair.get("quick_page_checkpoint") if isinstance(pair.get("quick_page_checkpoint"), Mapping) else {}
    checkpoint_status = str(checkpoint.get("status") or "")

    if not authored.is_file():
        return {
            "page": page_number,
            "state": NEEDS_SVG_AUTHORING,
            "action": "author_svg_from_audited_full_image",
            "error": None,
        }

    clean = pair.get("clean_base") or {}
    if clean.get("schema") == "cyberppt.stage02.authored_clean_base.v1" and clean.get("status") != "complete":
        return {
            "page": page_number, "state": NEEDS_SVG_AUTHORING,
            "action": "prepare_reference_edited_layers_and_register_quick_page", "error": None,
        }

    if checkpoint_status == "rendered_pending_visual_review":
        return {
            "page": page_number,
            "state": NEEDS_VISUAL_REVIEW,
            "action": "review_quick_page_preview",
            "preview_png": checkpoint.get("preview_png"),
            "error": None,
        }
    if checkpoint_status == "visual_review_failed":
        return {
            "page": page_number,
            "state": VISUAL_REVIEW_FAILED,
            "action": "revise_authored_svg_and_rerender",
            "preview_png": checkpoint.get("preview_png"),
            "error": None,
        }
    if checkpoint_status == "passed":
        return {"page": page_number, "state": PAGE_READY, "action": None, "error": None}
    if checkpoint_status == "failed":
        return {
            "page": page_number,
            "state": FAILED,
            "action": None,
            "error": str(checkpoint.get("error") or "Stage 02 page checkpoint failed"),
        }

    return {
        "page": page_number,
        "state": IMAGE_AUDITED,
        "action": "run_editable_reconstruction",
        "error": None,
    }


def classify_manifest(manifest: Mapping[str, Any]) -> dict[str, Any]:
    pages = [classify_page(pair) for pair in manifest.get("pairs", []) if isinstance(pair, Mapping)]
    failures = [page for page in pages if page["state"] in TERMINAL_FAILURE_STATES]
    actions = [page for page in pages if page["state"] in ACTION_STATES or page["state"] == IMAGE_AUDITED]
    ready = [page for page in pages if page["state"] == PAGE_READY]

    if failures:
        state = FAILED
    elif pages and len(ready) == len(pages):
        state = "ready_for_assembly"
    elif actions:
        state = "needs_action"
    else:
        state = READY_FOR_IMAGE

    return {
        "schema": "cyberppt.stage02_build_state.v1",
        "state": state,
        "pages": pages,
        "actions": [
            {key: value for key, value in page.items() if key in {"page", "state", "action", "preview_png"} and value is not None}
            for page in actions
        ],
        "failures": [
            {"page": page["page"], "state": page["state"], "error": page.get("error")}
            for page in failures
        ],
    }


def classify_manifest_path(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"manifest root must be an object: {path}")
    return classify_manifest(payload)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Classify a CyberPPT Stage 02 manifest into resumable action states.")
    parser.add_argument("manifest", type=Path)
    args = parser.parse_args(argv)
    report = classify_manifest_path(args.manifest.expanduser().resolve())
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 2 if report["state"] == FAILED else 0


if __name__ == "__main__":
    raise SystemExit(main())
