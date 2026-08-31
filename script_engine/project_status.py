"""Project progress and semantic-audit status evaluation."""
from __future__ import annotations

from collections.abc import Callable
from datetime import datetime, timezone
from pathlib import Path

from .analysis_audit import (
    audit_deck_plan,
    audit_final_script,
    audit_foundation_analysis,
    validate_source_index_coverage,
)
from .contracts import (
    check_declared_count,
    load_json,
    validate_deck_plan,
    validate_final_script,
    validate_foundation,
)
from .render import render_stage02_markdown
from .source_index import validate_script_foundation_against_index


VALIDATORS = {
    "foundation": validate_foundation,
    "plan": validate_deck_plan,
    "final": validate_final_script,
}
FinalLintFindings = Callable[[dict, str], tuple[list[str], list[str]]]


def project_profile_for_foundation(path: Path) -> str:
    """Read the owning project's declared profile when this is a project Foundation."""

    manifest = path.parent.parent / "manifest.yml"
    if not manifest.is_file():
        return "unspecified"
    for line in manifest.read_text(encoding="utf-8-sig").splitlines():
        if line.startswith("profile:"):
            profile = line.partition(":")[2].strip()
            return profile if profile in {"script", "strict", "legacy"} else "unspecified"
    return "unspecified"


def _mtime(path: Path) -> str | None:
    if not path.exists():
        return None
    return datetime.fromtimestamp(path.stat().st_mtime, tz=timezone.utc).isoformat(timespec="seconds")


def _artifact_report(path: Path, kind: str) -> dict:
    entry: dict = {"path": str(path), "exists": path.exists(), "updated": _mtime(path)}
    if path.exists():
        try:
            issues = VALIDATORS[kind](load_json(path))
            entry["valid"] = not issues
            if issues:
                entry["issues"] = issues
        except Exception as error:
            entry["valid"] = False
            entry["issues"] = [str(error)]
    return entry


def build_project_status(
    project_dir: Path,
    *,
    final_lint_findings: FinalLintFindings,
) -> dict:
    """Build the existing CLI status payload without performing presentation I/O."""

    script_dir = project_dir / "script"
    uses_repository_layout = any(
        path.exists()
        for path in (
            script_dir / "foundation.json",
            script_dir / "deck-plan.json",
            script_dir / "dist" / "final-script.json",
        )
    )
    artifact_dir = script_dir if uses_repository_layout else project_dir
    source_candidates = (project_dir / "source", project_dir / "sources")
    sources_dir = next(
        (
            path
            for path in source_candidates
            if path.exists()
            and any(item.is_file() and item.name != ".gitkeep" for item in path.glob("*"))
        ),
        next((path for path in source_candidates if path.exists()), project_dir / "sources"),
    )
    foundation_path = artifact_dir / "foundation.json"
    plan_path = artifact_dir / "deck-plan.json"
    final_path = artifact_dir / "dist" / "final-script.json"
    source_index_path = artifact_dir / ".cache" / "source-index.json"
    sources = (
        sorted(
            path.name
            for path in sources_dir.glob("*")
            if path.is_file() and path.name != ".gitkeep"
        )
        if sources_dir.exists()
        else []
    )
    foundation = _artifact_report(foundation_path, "foundation")
    plan = _artifact_report(plan_path, "plan")
    final = _artifact_report(final_path, "final")
    analysis: dict = {}

    if foundation.get("valid"):
        foundation_payload = load_json(foundation_path)
        foundation_issues, foundation_warnings = audit_foundation_analysis(foundation_payload)
        if (
            project_profile_for_foundation(foundation_path) not in {"strict", "legacy"}
            and source_index_path.exists()
        ):
            source_index = load_json(source_index_path)
            if source_index.get("schema") == "cyberppt.source_index.v2":
                foundation_issues.extend(
                    validate_script_foundation_against_index(foundation_payload, source_index)
                )
                foundation_issues = list(dict.fromkeys(foundation_issues))
        analysis["foundation"] = {
            "status": "passed" if not foundation_issues else "failed",
            "issues": foundation_issues,
            "warnings": foundation_warnings,
        }

    if foundation.get("valid") and plan.get("valid"):
        plan_issues, plan_warnings = audit_deck_plan(
            load_json(plan_path),
            load_json(foundation_path),
        )
        analysis["plan"] = {
            "status": "passed" if not plan_issues else "failed",
            "issues": plan_issues,
            "warnings": plan_warnings,
        }

    if final.get("exists") and final.get("valid"):
        payload = load_json(final_path)
        final["page_count"] = len(payload.get("slides") or [])
        final["deck_title"] = (payload.get("deck") or {}).get("title")
        markdown = render_stage02_markdown(payload)
        lint_blockers, lint_advisories = final_lint_findings(payload, markdown)
        final["lint"] = (
            "failed"
            if lint_blockers
            else "passed_with_advisories"
            if lint_advisories
            else "passed"
        )
        if lint_blockers:
            final["lint_issues"] = lint_blockers
        if lint_advisories:
            final["lint_advisories"] = lint_advisories
        lint_warnings = check_declared_count(payload)
        if lint_warnings:
            final["lint_warnings"] = lint_warnings
        if foundation.get("valid") and plan.get("valid"):
            semantic_issues, semantic_warnings = audit_final_script(
                payload,
                load_json(plan_path),
                load_json(foundation_path),
            )
            analysis["final"] = {
                "status": "passed" if not semantic_issues else "failed",
                "issues": semantic_issues,
                "warnings": semantic_warnings,
            }
        if source_index_path.exists():
            index_issues = validate_source_index_coverage(payload, load_json(source_index_path))
            final["source_index"] = "passed" if not index_issues else "failed"
            if index_issues:
                final["source_index_issues"] = index_issues

    if not project_dir.exists():
        stage = "项目目录不存在"
    elif not sources:
        stage = "等待源材料：source/ 或 sources/ 目录为空"
    elif not foundation["exists"]:
        stage = "待理解材料：尚未生成 foundation.json"
    elif not foundation.get("valid"):
        stage = "foundation.json 校验未通过，需要修复"
    elif analysis.get("foundation", {}).get("status") == "failed":
        stage = "foundation.json 语义纪律审计未通过，需要修复"
    elif not plan["exists"]:
        stage = "待规划：foundation.json 已就绪，尚未生成 deck-plan.json"
    elif not plan.get("valid"):
        stage = "deck-plan.json 校验未通过，需要修复"
    elif analysis.get("plan", {}).get("status") == "failed":
        stage = "deck-plan.json 源结构/语义边界审计未通过，需要修复"
    elif not final["exists"]:
        stage = "脚本规划待确认 / 待写作：deck-plan.json 已就绪，尚未生成最终脚本"
    elif not final.get("valid"):
        stage = "final-script.json 校验未通过，需要修复"
    elif final.get("lint") == "failed":
        stage = "最终脚本文件已就绪，但语言风格/结构/交付清洁度检查未通过，需要修复"
    elif analysis.get("final", {}).get("status") == "failed":
        stage = "最终脚本文件已就绪，但 PLAN→AUTHOR 语义继承审计未通过，需要修复"
    else:
        stage = "最终脚本文件已就绪，确定性检查通过；作者化完成情况由当前主 Agent 按 cyberppt-script-workflow 确认"

    return {
        "project": str(project_dir.resolve()),
        "stage": stage,
        "sources": sources,
        "source_index": {
            "path": str(source_index_path),
            "exists": source_index_path.exists(),
            "updated": _mtime(source_index_path),
        },
        "foundation": foundation,
        "deck_plan": plan,
        "analysis_audit": analysis,
        "final_script": final,
    }


__all__ = ["build_project_status", "project_profile_for_foundation"]
