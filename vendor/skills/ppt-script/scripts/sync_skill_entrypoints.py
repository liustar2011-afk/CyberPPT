#!/usr/bin/env python3
"""Sync ppt-script Skill entrypoints from the Codex canonical copy."""
from __future__ import annotations

import argparse
import hashlib
import sys
from pathlib import Path

CANONICAL = Path(".agents/skills/ppt-script/SKILL.md")
CLAUDE = Path(".claude/skills/ppt-script/SKILL.md")
ROOT_SKILL = Path("SKILL.md")
NESTED_LINK_PREFIX = "](../../../"


def repo_root_from_here() -> Path:
    return Path(__file__).resolve().parents[1]


def to_root_skill(canonical_text: str) -> str:
    return canonical_text.replace(NESTED_LINK_PREFIX, "](")


def to_nested_skill(root_text: str) -> str:
    """Best-effort inverse for checks when comparing root → nested."""
    # Only rewrite known top-level targets.
    out = root_text
    for target in (
        "system-prompt/",
        "config/",
        "references/",
        "templates/",
        "docs/",
    ):
        out = out.replace(f"]({target}", f"](../../../{target}")
    return out


def sync_skills(root: Path) -> dict[str, str]:
    canonical_path = root / CANONICAL
    if not canonical_path.is_file():
        raise FileNotFoundError(f"missing canonical skill: {canonical_path}")
    canonical = canonical_path.read_text(encoding="utf-8")
    root_text = to_root_skill(canonical)
    claude_path = root / CLAUDE
    claude_path.parent.mkdir(parents=True, exist_ok=True)
    claude_path.write_text(canonical, encoding="utf-8", newline="\n")
    (root / ROOT_SKILL).write_text(root_text, encoding="utf-8", newline="\n")
    return {
        "canonical": hashlib.sha256(canonical.encode("utf-8")).hexdigest(),
        "root": hashlib.sha256(root_text.encode("utf-8")).hexdigest(),
        "claude": hashlib.sha256(canonical.encode("utf-8")).hexdigest(),
    }


def skill_sync_issues(root: Path) -> list[str]:
    issues: list[str] = []
    canonical_path = root / CANONICAL
    root_path = root / ROOT_SKILL
    claude_path = root / CLAUDE
    for path in (canonical_path, root_path, claude_path):
        if not path.is_file():
            issues.append(f"missing skill entrypoint: {path.relative_to(root)}")
            return issues
    canonical = canonical_path.read_text(encoding="utf-8")
    root_text = root_path.read_text(encoding="utf-8")
    claude = claude_path.read_text(encoding="utf-8")
    if claude != canonical:
        issues.append(".claude/skills/ppt-script/SKILL.md diverges from .agents canonical skill")
    expected_root = to_root_skill(canonical)
    if root_text != expected_root:
        issues.append("SKILL.md diverges from .agents canonical skill after link rewrite")
    if NESTED_LINK_PREFIX not in canonical:
        # Soft warning only when canonical has no nested links; keep as info via issue if empty links expected.
        pass
    if "](../../../" in root_text:
        issues.append("root SKILL.md still contains nested ../../../ links")
    return issues


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="only verify sync; non-zero if drifted")
    parser.add_argument("--root", type=Path, default=None, help="repository root")
    args = parser.parse_args(argv)
    root = (args.root or repo_root_from_here()).resolve()
    if args.check:
        issues = skill_sync_issues(root)
        if issues:
            print("Skill entrypoint sync FAILED:")
            for item in issues:
                print(f"- {item}")
            return 1
        print("Skill entrypoint sync OK")
        return 0
    digests = sync_skills(root)
    print("Synced Skill entrypoints from .agents/skills/ppt-script/SKILL.md")
    for key, digest in digests.items():
        print(f"- {key}: {digest[:16]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
