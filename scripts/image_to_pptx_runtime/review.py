"""Review contract: local adjustments are acceptable; a page redesign is not."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from .contracts import QuickProject


@dataclass(frozen=True)
class ReviewIssue:
    page: int
    category: str
    scope: Literal["local", "whole_page"]
    description: str


def write_review(project: QuickProject, issues: list[ReviewIssue]) -> dict:
    payload = {"schema": "cyberppt.image_to_pptx.visual_review.v1", "issues": [issue.__dict__ for issue in issues], "requires_rebuild": any(issue.scope == "whole_page" for issue in issues), "valid": not any(issue.scope == "whole_page" for issue in issues)}
    path = project.root / "analysis" / "visual-review.json"
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
    payload["path"] = str(path)
    return payload
