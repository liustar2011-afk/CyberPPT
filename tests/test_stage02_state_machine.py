from __future__ import annotations

from cyberppt.stage02_production.state import (
    ACTION_AUTHOR_SVG,
    ACTION_REVIEW_QUICK_PAGE,
    ACTION_REVISE_QUICK_PAGE,
    STATUS_NEEDS_ACTION,
    classify_reconstruction_checkpoint,
    collect_needs_actions,
)


def test_collects_authoring_and_review_actions() -> None:
    manifest = {
        "pairs": [
            {
                "page_number": 1,
                "quick_page_checkpoint": {
                    "status": "failed",
                    "error": "requires a hand-authored SVG from the image-to-PPTX runtime",
                },
            },
            {
                "page_number": 2,
                "quick_page_checkpoint": {
                    "status": "rendered_pending_visual_review",
                    "preview_png": "/tmp/p2.png",
                },
            },
            {
                "page_number": 3,
                "quick_page_checkpoint": {
                    "status": "visual_review_failed",
                    "preview_png": "/tmp/p3.png",
                },
            },
        ]
    }

    actions, failures = collect_needs_actions(manifest, requested_pages=(1, 2, 3))

    assert failures == []
    assert [item["action"] for item in actions] == [
        ACTION_AUTHOR_SVG,
        ACTION_REVIEW_QUICK_PAGE,
        ACTION_REVISE_QUICK_PAGE,
    ]
    assert classify_reconstruction_checkpoint(manifest, requested_pages=(1, 2, 3))["status"] == STATUS_NEEDS_ACTION


def test_unknown_failure_remains_fail_closed() -> None:
    manifest = {
        "pairs": [
            {
                "page_number": 1,
                "quick_page_checkpoint": {
                    "status": "rendered_pending_visual_review",
                    "preview_png": "/tmp/p1.png",
                },
            },
            {
                "page_number": 2,
                "quick_page_checkpoint": {
                    "status": "failed",
                    "error": "native text geometry is invalid",
                },
            },
        ]
    }

    actions, failures = collect_needs_actions(manifest, requested_pages=(1, 2))

    assert len(actions) == 1
    assert len(failures) == 1
    assert classify_reconstruction_checkpoint(manifest, requested_pages=(1, 2)) is None


def test_requested_page_filter_keeps_resume_scope() -> None:
    manifest = {
        "pairs": [
            {
                "page_number": 1,
                "quick_page_checkpoint": {
                    "status": "failed",
                    "error": "requires a hand-authored SVG from the image-to-PPTX runtime",
                },
            },
            {
                "page_number": 9,
                "quick_page_checkpoint": {
                    "status": "failed",
                    "error": "unrelated failure",
                },
            },
        ]
    }

    checkpoint = classify_reconstruction_checkpoint(manifest, requested_pages=(1,))

    assert checkpoint is not None
    assert checkpoint["actions"][0]["page"] == 1
