"""Explicit Stage 02 workflow states and pending-action classification."""

from __future__ import annotations

from typing import Any, Iterable, Mapping


STATUS_NEEDS_ACTION = "needs_action"
STATUS_PRODUCTION_READY = "production_ready"

ACTION_AUTHOR_SVG = "author_svg"
ACTION_REVIEW_QUICK_PAGE = "review_quick_page"
ACTION_REVISE_QUICK_PAGE = "revise_quick_page"

_PENDING_REVIEW_STATUSES = {"rendered_pending_visual_review", "visual_review_failed"}


def _page_number(pair: Mapping[str, Any]) -> int | None:
    value = pair.get("page_number")
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def collect_needs_actions(
    manifest: Mapping[str, Any],
    *,
    requested_pages: Iterable[int] | None = None,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Classify normal human/Agent checkpoints separately from real failures.

    Returns ``(actions, unclassified_failures)``.  The caller may convert an
    exception into ``needs_action`` only when at least one action exists and no
    unclassified failure remains.
    """

    requested = set(requested_pages or ())
    actions: list[dict[str, Any]] = []
    unclassified: list[dict[str, Any]] = []
    for raw_pair in manifest.get("pairs", []):
        if not isinstance(raw_pair, Mapping):
            continue
        page = _page_number(raw_pair)
        if page is None or (requested and page not in requested):
            continue
        checkpoint = raw_pair.get("quick_page_checkpoint")
        if not isinstance(checkpoint, Mapping):
            continue
        status = str(checkpoint.get("status") or "")
        error = str(checkpoint.get("error") or "")
        if status == "rendered_pending_visual_review":
            actions.append(
                {
                    "page": page,
                    "action": ACTION_REVIEW_QUICK_PAGE,
                    "checkpoint_status": status,
                    "preview_png": checkpoint.get("preview_png"),
                    "resume": checkpoint.get("resume") or "awaiting_visual_review",
                }
            )
            continue
        if status == "visual_review_failed":
            actions.append(
                {
                    "page": page,
                    "action": ACTION_REVISE_QUICK_PAGE,
                    "checkpoint_status": status,
                    "preview_png": checkpoint.get("preview_png"),
                    "visual_review": checkpoint.get("visual_review"),
                    "resume": checkpoint.get("resume") or "revise_then_review",
                }
            )
            continue
        if status == "failed" and "requires a hand-authored SVG" in error:
            actions.append(
                {
                    "page": page,
                    "action": ACTION_AUTHOR_SVG,
                    "checkpoint_status": status,
                    "error": error,
                    "resume": "author_svg_then_resume_same_build",
                }
            )
            continue
        if status == "failed":
            unclassified.append(
                {
                    "page": page,
                    "checkpoint_status": status,
                    "error": error,
                }
            )
    return actions, unclassified


def classify_reconstruction_checkpoint(
    manifest: Mapping[str, Any],
    *,
    requested_pages: Iterable[int] | None = None,
) -> dict[str, Any] | None:
    """Return a normal needs-action result when every blocker is actionable."""

    actions, failures = collect_needs_actions(manifest, requested_pages=requested_pages)
    if not actions or failures:
        return None
    return {
        "status": STATUS_NEEDS_ACTION,
        "actions": actions,
        "unclassified_failures": [],
    }
