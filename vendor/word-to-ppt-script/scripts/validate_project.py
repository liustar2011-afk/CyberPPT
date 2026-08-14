#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

from validate_script import validate
from validate_imagegen_contract import validate as validate_imagegen_contract

REQUIRED = [
    "00-task-brief.md",
    "01-source-normalized.md",
    "02-source-truth-map.md",
    "03-argument-map.md",
    "04-deck-outline.md",
    "05-page-boundary-matrix.md",
    "06-transition-script.md",
    "07-on-screen-text.md",
    "08-speaker-notes.md",
    "09-visual-design-spec.md",
    "10-script-final.md",
    "11-quality-review.md",
    "machine/source-truth-map.json",
    "machine/page-contracts.json",
    "machine/visual-spec.json",
    "machine/final-manifest.json",
]

SOURCE_RE = re.compile(r"\b(?:SRC|SU|A|P0)-[A-Za-z0-9_-]+\b|\bSRC-[A-Za-z0-9_-]+\b")


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate full Word-to-PPT project")
    parser.add_argument("project", type=Path)
    parser.add_argument("--strict", action="store_true")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    root = args.project
    issues = []
    for rel in REQUIRED:
        if not (root / rel).exists():
            issues.append({"level": "error", "code": "MISSING_OUTPUT", "message": rel})

    final = root / "10-script-final.md"
    page_payload = {"passed": False, "issues": []}
    if final.exists():
        pages, page_issues = validate(final, strict=args.strict)
        page_payload = {
            "passed": not any(i.level == "error" for i in page_issues),
            "pages": len(pages),
            "issues": [i.__dict__ for i in page_issues],
        }
        issues.extend(page_payload["issues"])

    truth = root / "02-source-truth-map.md"
    if truth.exists() and final.exists():
        t = truth.read_text(encoding="utf-8")
        p0_ids = set()
        for line in t.splitlines():
            if not line.lstrip().startswith("|"):
                continue
            cells = [c.strip().strip("`") for c in line.strip().strip("|").split("|")]
            if "P0" in cells and cells:
                p0_ids.add(cells[0])
        final_ids = set(SOURCE_RE.findall(final.read_text(encoding="utf-8")))
        missing = sorted(x for x in p0_ids if x and x not in final_ids)
        if missing:
            issues.append({"level": "error", "code": "P0_COVERAGE", "message": f"P0未覆盖：{missing}"})

    for rel in ["machine/source-truth-map.json", "machine/page-contracts.json", "machine/visual-spec.json", "machine/final-manifest.json"]:
        path = root / rel
        if path.exists():
            try:
                json.loads(path.read_text(encoding="utf-8"))
            except Exception as exc:
                issues.append({"level": "error", "code": "INVALID_JSON", "message": f"{rel}: {exc}"})

    handoff = root / "12-imagegen-review.md"
    if handoff.exists():
        _, handoff_issues = validate_imagegen_contract(handoff, strict=args.strict)
        issues.extend([i.__dict__ for i in handoff_issues])

    errors = [i for i in issues if i.get("level") == "error"]
    warnings = [i for i in issues if i.get("level") == "warning"]
    payload = {"passed": not errors, "errors": len(errors), "warnings": len(warnings), "issues": issues}
    report = root / "machine" / "quality-report.json"
    report.parent.mkdir(parents=True, exist_ok=True)
    report.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    if args.json:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        print(f"passed={payload['passed']} errors={len(errors)} warnings={len(warnings)}")
        for issue in issues:
            print(f"[{issue.get('level','').upper()}] {issue.get('code')}: {issue.get('message')}")
    return 0 if not errors else 2


if __name__ == "__main__":
    raise SystemExit(main())
