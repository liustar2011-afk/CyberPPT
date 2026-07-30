#!/usr/bin/env python3
from __future__ import annotations

import ast
import json
import re
import sys

import yaml
from collections import Counter
from dataclasses import asdict, dataclass
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

from ppt_script.version import get_version  # noqa: E402

_LINK = re.compile(r"\[[^\]]+\]\(([^)]+)\)")


@dataclass(frozen=True, slots=True)
class ConsistencyIssue:
    code: str
    path: str
    message: str


@dataclass(frozen=True, slots=True)
class ConsistencyReport:
    version: str
    issues: tuple[ConsistencyIssue, ...]

    @property
    def passed(self) -> bool:
        return not self.issues

    def to_dict(self) -> dict:
        return {
            "version": self.version,
            "passed": self.passed,
            "issues": [asdict(issue) for issue in self.issues],
        }


def _duplicate_headings(path: Path) -> list[str]:
    headings = [line.strip() for line in path.read_text(encoding="utf-8").splitlines() if line.startswith("## ")]
    return [heading for heading, count in Counter(headings).items() if count > 1]


def _duplicate_top_level_definitions(path: Path) -> list[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    names = [node.name for node in tree.body if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef))]
    return [name for name, count in Counter(names).items() if count > 1]


def _broken_links(path: Path) -> list[str]:
    broken: list[str] = []
    for raw in _LINK.findall(path.read_text(encoding="utf-8")):
        target = raw.strip().split("#", 1)[0]
        if not target or "://" in target or target.startswith("mailto:"):
            continue
        resolved = (path.parent / target).resolve()
        if not resolved.exists():
            broken.append(raw)
    return broken


def check_repository(repo_root: str | Path) -> ConsistencyReport:
    root = Path(repo_root).resolve()
    issues: list[ConsistencyIssue] = []
    try:
        version = get_version(root)
    except (FileNotFoundError, ValueError) as exc:
        version = "unknown"
        issues.append(ConsistencyIssue("version", "VERSION", str(exc)))

    repository_mode = any((root / marker).exists() for marker in (".git", ".agents", ".claude"))
    required = [
        "VERSION",
        "SKILL.md",
        "config/rules.yaml",
        "config/workflow-routes.yaml",
        "config/prompt-modules.yaml",
        "system-prompt/stage1.md",
        "system-prompt/stage1/12-faithful-reading.md",
        "system-prompt/stage1/13-decision-reading.md",
        "system-prompt/stage1/14-reconciliation.md",
        "system-prompt/stage1/15-evidence-graph.md",
        "system-prompt/stage1/16-experience-retrieval.md",
        "scripts/ppt_script/experience.py",
        "knowledge/schemas/experience-case.schema.json",
        "templates/experience-feedback.json",
        "evaluations/cognition/complex-material-scorecard.yaml",
        "evaluations/experience/retrieval-scorecard.yaml",
        "system-prompt/stage2.md",
        "scripts/project_manager.py",
        "scripts/ppt_script/cognition.py",
        "scripts/ppt_script/evidence_graph.py",
    ]
    if repository_mode:
        required.extend((".agents/skills/ppt-script/SKILL.md", ".claude/skills/ppt-script/SKILL.md"))
    for relative in required:
        if not (root / relative).exists():
            issues.append(ConsistencyIssue("missing-file", relative, "required repository file is missing"))

    skill_candidates = ["SKILL.md"]
    if repository_mode:
        skill_candidates.extend((".agents/skills/ppt-script/SKILL.md", ".claude/skills/ppt-script/SKILL.md"))
    for relative in skill_candidates:
        path = root / relative
        if not path.exists():
            continue
        for heading in _duplicate_headings(path):
            issues.append(ConsistencyIssue("duplicate-heading", relative, f"duplicate heading: {heading}"))
        for link in _broken_links(path):
            issues.append(ConsistencyIssue("broken-link", relative, f"broken local link: {link}"))

    for path in (root / "scripts").rglob("*.py"):
        try:
            duplicates = _duplicate_top_level_definitions(path)
        except SyntaxError as exc:
            issues.append(ConsistencyIssue("syntax", str(path.relative_to(root)), str(exc)))
            continue
        for name in duplicates:
            issues.append(
                ConsistencyIssue(
                    "duplicate-definition",
                    str(path.relative_to(root)),
                    f"duplicate top-level definition: {name}",
                )
            )


    prompt_registry = root / "config/prompt-modules.yaml"
    if prompt_registry.is_file():
        try:
            payload = yaml.safe_load(prompt_registry.read_text(encoding="utf-8")) or {}
            modules = payload.get("modules", {})
            if not isinstance(modules, dict) or not modules:
                issues.append(ConsistencyIssue("prompt-registry", "config/prompt-modules.yaml", "modules mapping is empty or invalid"))
            else:
                for module_id, definition in modules.items():
                    relative_path = definition.get("path") if isinstance(definition, dict) else None
                    if not relative_path or not (root / str(relative_path)).is_file():
                        issues.append(
                            ConsistencyIssue(
                                "prompt-module",
                                "config/prompt-modules.yaml",
                                f"prompt module path is missing: {module_id} -> {relative_path}",
                            )
                        )
                persistent = payload.get("persistent_stage1_modules", [])
                if not isinstance(persistent, list):
                    issues.append(
                        ConsistencyIssue(
                            "persistent-prompt-module",
                            "config/prompt-modules.yaml",
                            "persistent_stage1_modules must be a list",
                        )
                    )
                else:
                    for module_id in persistent:
                        definition = modules.get(module_id)
                        if not isinstance(definition, dict):
                            issues.append(
                                ConsistencyIssue(
                                    "persistent-prompt-module",
                                    "config/prompt-modules.yaml",
                                    f"unknown persistent prompt module: {module_id}",
                                )
                            )
                            continue
                        if definition.get("stage") != "stage1":
                            issues.append(
                                ConsistencyIssue(
                                    "persistent-prompt-module",
                                    "config/prompt-modules.yaml",
                                    f"persistent module must belong to stage1: {module_id}",
                                )
                            )
                methodology = payload.get("methodology_references") or {}
                if methodology and not isinstance(methodology, dict):
                    issues.append(
                        ConsistencyIssue(
                            "methodology-references",
                            "config/prompt-modules.yaml",
                            "methodology_references must be a mapping",
                        )
                    )
                elif isinstance(methodology, dict):
                    workflow_stages = set((payload.get("workflow_stage_modules") or {}).keys())
                    path_buckets: list[tuple[str, list]] = [
                        ("persistent", list(methodology.get("persistent") or [])),
                        ("when_pages_present", list(methodology.get("when_pages_present") or [])),
                    ]
                    by_profile = methodology.get("by_writing_profile") or {}
                    if isinstance(by_profile, dict):
                        for profile, items in by_profile.items():
                            path_buckets.append((f"by_writing_profile.{profile}", list(items or [])))
                    by_stage = methodology.get("by_workflow_stage") or {}
                    if isinstance(by_stage, dict):
                        for stage, items in by_stage.items():
                            if stage not in workflow_stages:
                                issues.append(
                                    ConsistencyIssue(
                                        "methodology-references",
                                        "config/prompt-modules.yaml",
                                        f"unknown methodology workflow stage: {stage}",
                                    )
                                )
                            path_buckets.append((f"by_workflow_stage.{stage}", list(items or [])))
                    for bucket, items in path_buckets:
                        if not isinstance(items, list):
                            issues.append(
                                ConsistencyIssue(
                                    "methodology-references",
                                    "config/prompt-modules.yaml",
                                    f"{bucket} must be a list",
                                )
                            )
                            continue
                        for relative in items:
                            if not (root / str(relative)).is_file():
                                issues.append(
                                    ConsistencyIssue(
                                        "methodology-references",
                                        "config/prompt-modules.yaml",
                                        f"methodology path missing ({bucket}): {relative}",
                                    )
                                )
        except Exception as exc:
            issues.append(ConsistencyIssue("prompt-registry", "config/prompt-modules.yaml", f"invalid prompt registry: {exc}"))

    try:
        from sync_skill_entrypoints import skill_sync_issues

        # Installed skill packages only ship root SKILL.md; sync applies to the full repository.
        if repository_mode:
            for message in skill_sync_issues(root):
                issues.append(ConsistencyIssue("skill-entrypoint-sync", "SKILL.md", message))
    except Exception as exc:
        issues.append(ConsistencyIssue("skill-entrypoint-sync", "scripts/sync_skill_entrypoints.py", str(exc)))

    runtime_files = (
        root / "scripts/ppt_script/commands/init.py",
        root / "scripts/project_manager.py",
        root / "install.sh",
    )
    for path in runtime_files:
        if not path.exists():
            continue
        text = path.read_text(encoding="utf-8")
        for stale in ("3.0.0", "3.3.0"):
            if stale in text:
                issues.append(
                    ConsistencyIssue(
                        "hardcoded-version",
                        str(path.relative_to(root)),
                        f"runtime file hardcodes historical version {stale}; read VERSION dynamically",
                    )
                )

    return ConsistencyReport(version, tuple(issues))


def render_report(report: ConsistencyReport) -> str:
    lines = [
        "# Repository consistency",
        "",
        f"- Version: {report.version}",
        f"- Result: {'PASS' if report.passed else 'FAIL'}",
        f"- Issues: {len(report.issues)}",
        "",
        "## Issues",
        "",
    ]
    if not report.issues:
        lines.append("- None")
    else:
        lines.extend(f"- [{item.code}] {item.path}: {item.message}" for item in report.issues)
    return "\n".join(lines) + "\n"


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    report = check_repository(root)
    output_dir = root / "docs"
    output_dir.mkdir(exist_ok=True)
    (output_dir / "repository-consistency.json").write_text(
        json.dumps(report.to_dict(), ensure_ascii=False, indent=2), encoding="utf-8"
    )
    (output_dir / "repository-consistency.md").write_text(render_report(report), encoding="utf-8")
    print(render_report(report), end="")
    return 0 if report.passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
