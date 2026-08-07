#!/usr/bin/env python3
from __future__ import annotations

import argparse
import shutil
from pathlib import Path

FILES = {
    "00-task-brief.md": "00-task-brief.md",
    "02-source-truth-map.md": "02-source-truth-map.md",
    "03-argument-map.md": "03-argument-map.md",
    "04-deck-outline.md": "04-deck-outline.md",
    "05-page-boundary-matrix.md": "05-page-boundary-matrix.md",
    "06-transition-script.md": "06-transition-script.md",
    "07-on-screen-text.md": "07-on-screen-text.md",
    "08-speaker-notes.md": "08-speaker-notes.md",
    "09-visual-design-spec.md": "09-visual-design-spec.md",
    "10-script-final.md": "10-script-final.md",
    "11-quality-review.md": "11-quality-review.md",
}


def main() -> int:
    parser = argparse.ArgumentParser(description="Initialize a Word-to-PPT compilation project")
    parser.add_argument("project", type=Path)
    parser.add_argument("--name", default="项目名称")
    parser.add_argument("--mode", default="full", choices=["full", "outline", "text", "visual", "compile", "revise", "audit"])
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()

    root = args.project
    skill_root = Path(__file__).resolve().parents[1]
    if root.exists() and any(root.iterdir()) and not args.force:
        parser.error(f"project is not empty: {root}; use --force")
    root.mkdir(parents=True, exist_ok=True)
    (root / "machine").mkdir(exist_ok=True)
    for output, template in FILES.items():
        src = skill_root / "templates" / template
        dst = root / output
        text = src.read_text(encoding="utf-8").replace("项目名称", args.name)
        dst.write_text(text, encoding="utf-8")
    (root / "01-source-normalized.md").write_text(f"# 规范化源文：{args.name}\n", encoding="utf-8")
    (root / "machine" / "source-truth-map.json").write_text("{\n  \"sources\": []\n}\n", encoding="utf-8")
    (root / "machine" / "page-contracts.json").write_text("{\n  \"pages\": []\n}\n", encoding="utf-8")
    (root / "machine" / "visual-spec.json").write_text("{\n  \"pages\": []\n}\n", encoding="utf-8")
    (root / "machine" / "final-manifest.json").write_text("{}\n", encoding="utf-8")
    (root / "machine" / "quality-report.json").write_text("{}\n", encoding="utf-8")
    brief = root / "00-task-brief.md"
    brief.write_text(brief.read_text(encoding="utf-8").replace("- 模式：full", f"- 模式：{args.mode}"), encoding="utf-8")
    print(root)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
