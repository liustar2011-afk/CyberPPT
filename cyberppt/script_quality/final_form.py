"""Final-manuscript path and form checks."""

from __future__ import annotations

from pathlib import Path
import re

from .models import ScriptQualityIssue


FINAL_BATCH_HEADING_RE = re.compile(
    r"^#\s+第\s*\d+\s*[—\-~～－]+\s*\d+\s*页"
)
FINAL_DRAFT_HEADING_RE = re.compile(r"^#\s+.*草稿")
FINAL_BATCH_META_RE = re.compile(r"^>\s*批次\s*[：:]")
FINAL_DRAFT_STATUS_RE = re.compile(r"^>\s*状态\s*[：:].*草稿")
FINAL_PENDING_AUDIT_RE = re.compile(
    r"待\s*`?script-audit`?\s*通过后审稿"
)


def is_final_script_path(path: Path) -> bool:
    """True when the path is under workbench/scripts/final/."""

    parts = [part.lower() for part in Path(path).parts]
    try:
        scripts_index = parts.index("scripts")
    except ValueError:
        return False
    return scripts_index + 1 < len(parts) and parts[scripts_index + 1] == "final"


def audit_final_manuscript_form(text: str) -> list[ScriptQualityIssue]:
    """Reject draft/batch wording that must not appear in final manuscripts."""

    evidence: list[str] = []
    for index, raw_line in enumerate(text.splitlines(), start=1):
        line = raw_line.strip()
        if not line:
            continue
        banner_hit = (
            FINAL_DRAFT_HEADING_RE.match(line)
            or FINAL_BATCH_HEADING_RE.match(line)
            or FINAL_BATCH_META_RE.match(line)
            or FINAL_DRAFT_STATUS_RE.match(line)
            or FINAL_PENDING_AUDIT_RE.search(line)
        )
        # Only reject manuscript-state banners. Business prose may legitimately
        # contain terms such as “账单草稿” or “处理批次”.
        if banner_hit:
            evidence.append(f"L{index}:{line[:100]}")
    if not evidence:
        return []
    return [
        ScriptQualityIssue(
            code="FINAL_MANUSCRIPT_DRAFT_BANNER",
            severity="error",
            message=(
                "Final manuscript must not contain draft/batch status banners."
            ),
            pages=(),
            evidence=tuple(evidence[:12]),
            suggested_action=(
                "Run `python -m cyberppt assemble-final-script <project>` or "
                "remove every draft/batch status label before auditing files under "
                "workbench/scripts/final/."
            ),
        )
    ]
