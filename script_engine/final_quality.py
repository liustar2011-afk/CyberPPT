"""Final Script deterministic quality evaluation shared by CLI workflows."""
from __future__ import annotations

from collections.abc import Callable

from .contracts import (
    check_full_copy_duplication,
    check_onscreen_detail_length,
    check_onscreen_structure,
    check_onscreen_terminal_punctuation,
    check_speaker_notes_length,
    lint_final_script,
)
from .delivery_cleanliness import check_delivery_cleanliness
from .quality_policy import partition_issues


IssueCollector = Callable[[dict, str], list[str]]


def collect_final_lint_issues(payload: dict, markdown: str) -> list[str]:
    """Return every deterministic finding required at the Final Script boundary."""

    return (
        lint_final_script(payload)
        + check_onscreen_structure(payload)
        + check_full_copy_duplication(payload)
        + check_speaker_notes_length(payload)
        + check_delivery_cleanliness(markdown)
        + check_onscreen_terminal_punctuation(payload)
        + check_onscreen_detail_length(payload)
    )


def partition_final_lint_findings(
    payload: dict,
    markdown: str,
    *,
    issue_collector: IssueCollector = collect_final_lint_issues,
) -> tuple[list[str], list[str]]:
    """Collect Final Script findings, then apply the shared blocker/advisory policy."""

    return partition_issues(issue_collector(payload, markdown))


__all__ = [
    "collect_final_lint_issues",
    "partition_final_lint_findings",
]
