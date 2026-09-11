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
from .audit_reports import final_audit_report
from .author_preflight import author_preflight_gate_report, author_preflight_report
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


def _artifact_state(entry: dict) -> str:
    if not entry.get("exists"):
        return "missing"
    return "passed" if entry.get("valid") else "failed"


def _source_index_report(path: Path) -> dict:
    report: dict = {
        "path": str(path),
        "exists": path.exists(),
        "updated": _mtime(path),
        "status": "missing",
    }
    if not path.exists():
        return report
    try:
        payload = load_json(path)
    except Exception as error:
        report["status"] = "failed"
        report["issues"] = [str(error)]
        return report
    if payload.get("schema") != "cyberppt.source_index.v2":
        report["status"] = "failed"
        report["issues"] = ["SOURCE_INDEX_SCHEMA_INVALID: expected cyberppt.source_index.v2"]
        return report
    report["status"] = "passed"
    return report


def _author_preflight_status(
    plan_path: Path,
    foundation_path: Path,
    source_index_path: Path,
    *,
    upstream_ready: bool,
) -> dict:
    manifest_path = foundation_path.parent / ".cache" / "author-preflight.json"
    packet_dir = foundation_path.parent / ".cache" / "page-source"
    status: dict = {
        "manifest": str(manifest_path),
        "manifest_exists": manifest_path.is_file(),
        "packet_dir": str(packet_dir),
        "status": "not_run" if not upstream_ready else "blocked",
        "pages": [],
        "issues": [],
    }
    if not upstream_ready:
        return status

    current, _current_exit = author_preflight_report(
        plan_path,
        foundation_path,
        source_index_path=source_index_path,
        packet_dir=packet_dir,
    )
    if current.get("schema") == "cyberppt.author_preflight.v2":
        status["current_summary"] = current.get("summary") or {}
        status["pages"] = current.get("pages") or []
        if current.get("issues"):
            status["current_issues"] = current.get("issues")
    else:
        status["current_status"] = current.get("status", "blocked")
        status["current_issues"] = current.get("issues") or []

    gate_report, gate_exit = author_preflight_gate_report(
        plan_path,
        foundation_path,
        source_index_path=source_index_path,
        packet_dir=packet_dir,
        manifest_path=manifest_path,
    )
    status["issues"] = gate_report.get("issues") or []
    if gate_exit == 0:
        status["status"] = "passed"
    elif not manifest_path.is_file():
        status["status"] = "missing"
    else:
        status["status"] = "blocked"
    return status


def build_project_status(
    project_dir: Path,
    *,
    final_lint_findings: FinalLintFindings,
) -> dict:
    """Build project status from current Stage1 artifacts and hard gates."""

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
    source_index = _source_index_report(source_index_path)
    analysis: dict = {}

    if foundation.get("valid"):
        foundation_payload = load_json(foundation_path)
        foundation_issues, foundation_warnings = audit_foundation_analysis(foundation_payload)
        if (
            project_profile_for_foundation(foundation_path) not in {"strict", "legacy"}
            and source_index_path.exists()
        ):
            indexed_payload = load_json(source_index_path)
            if indexed_payload.get("schema") == "cyberppt.source_index.v2":
                foundation_issues.extend(
                    validate_script_foundation_against_index(foundation_payload, indexed_payload)
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

    upstream_ready = bool(
        foundation.get("valid")
        and plan.get("valid")
        and source_index.get("status") == "passed"
    )
    preflight = _author_preflight_status(
        plan_path,
        foundation_path,
        source_index_path,
        upstream_ready=upstream_ready,
    )

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

    final_audit: dict = {"status": "not_run", "issues": []}
    if final.get("valid") and foundation.get("valid") and plan.get("valid"):
        report, audit_exit = final_audit_report(final_path, plan_path, foundation_path)
        final_audit = {
            "status": "passed" if audit_exit == 0 else "failed",
            "issues": report.get("issues") or [],
            "source_provenance_issues": report.get("source_provenance_issues") or [],
            "native_source_fidelity_issues": report.get("native_source_fidelity_issues") or [],
        }

    stage1 = {
        "source_index": source_index,
        "foundation": {
            "status": _artifact_state(foundation),
            "analysis_status": analysis.get("foundation", {}).get("status", "not_run"),
        },
        "deck_plan": {
            "status": _artifact_state(plan),
            "analysis_status": analysis.get("plan", {}).get("status", "not_run"),
        },
        "author_preflight": preflight,
        "final_script": {
            "status": _artifact_state(final),
            "lint": final.get("lint", "not_run"),
        },
        "final_audit": final_audit,
    }

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
    elif preflight.get("status") != "passed":
        stage = "Stage1 Author Preflight 未通过：待补齐或刷新逐页精确来源证据"
    elif not final["exists"]:
        stage = "Stage1 Author Preflight 已通过，待写作最终脚本"
    elif not final.get("valid"):
        stage = "final-script.json 校验未通过，需要修复"
    elif final.get("lint") == "failed":
        stage = "最终脚本文件已就绪，但语言风格/结构/交付清洁度检查未通过，需要修复"
    elif final_audit.get("status") == "failed":
        stage = "最终脚本文件已就绪，但 Stage1 最终审计未通过，不得进入 Stage02"
    else:
        stage = "最终脚本文件已就绪，Stage1 确定性门禁与最终审计通过，可进入 Stage02"

    return {
        "project": str(project_dir.resolve()),
        "stage": stage,
        "sources": sources,
        "source_index": source_index,
        "foundation": foundation,
        "deck_plan": plan,
        "analysis_audit": analysis,
        "final_script": final,
        "stage1": stage1,
    }


__all__ = ["build_project_status", "project_profile_for_foundation"]
