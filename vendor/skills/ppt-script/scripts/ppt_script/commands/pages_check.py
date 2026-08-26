from __future__ import annotations

import json
from pathlib import Path

from ..pages_index import audit_pages, render_pages_audit


def pages_check_command(project: Path) -> Path:
    audit = audit_pages(project)
    review = project / "review"
    review.mkdir(parents=True, exist_ok=True)
    output = review / "08-pages-alignment.md"
    output.write_text(render_pages_audit(audit), encoding="utf-8")
    output.with_suffix(".json").write_text(
        json.dumps(audit.to_dict(), ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return output
