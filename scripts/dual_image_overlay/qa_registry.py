from __future__ import annotations

import json
from pathlib import Path
from typing import Any


RULES_PATH = Path(__file__).with_name("default_quality_rules.json")
REPORT_SCHEMA = "cyberppt.dual_image.page_quality_report.v1"


def _read_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"JSON root must be an object: {path}")
    return payload


def load_quality_rules(path: Path = RULES_PATH) -> list[dict[str, Any]]:
    payload = _read_json(path)
    rules = payload.get("rules", [])
    if not isinstance(rules, list):
        raise ValueError(f"Quality rules must be a list: {path}")
    return [rule for rule in rules if isinstance(rule, dict)]


def _is_truthy_report(report: Any) -> bool:
    return isinstance(report, dict) and bool(report.get("valid"))


def _artifact_exists(value: Any) -> bool:
    if not isinstance(value, str) or not value:
        return False
    return Path(value).expanduser().exists()


def _evidence_for_rule(rule: dict[str, Any], artifacts: dict[str, Any]) -> dict[str, Any]:
    evidence: dict[str, Any] = {}
    report_key = rule.get("report")
    artifact_key = rule.get("artifact")
    if isinstance(report_key, str) and report_key in artifacts:
        path = artifacts[report_key]
        evidence["report_path"] = path
        evidence["report_path_exists"] = _artifact_exists(path)
    if isinstance(artifact_key, str) and artifact_key in artifacts:
        path = artifacts[artifact_key]
        evidence["artifact_path"] = path
        evidence["artifact_path_exists"] = _artifact_exists(path)
    return evidence


def _has_required_evidence(evidence: dict[str, Any]) -> bool:
    if not evidence:
        return False
    exists_flags = [value for key, value in evidence.items() if key.endswith("_exists")]
    return bool(exists_flags) and all(bool(value) for value in exists_flags)


def _evaluate_rule(
    rule: dict[str, Any],
    *,
    reports: dict[str, Any],
    artifacts: dict[str, Any],
) -> dict[str, Any]:
    kind = str(rule.get("kind") or "")
    report_key = str(rule.get("report") or "")
    artifact_key = str(rule.get("artifact") or "")
    passed = False
    observed: Any = None

    if kind == "report_valid":
        observed = reports.get(report_key)
        passed = _is_truthy_report(observed)
    elif kind == "all_reports_valid":
        observed = reports.get(report_key)
        if isinstance(observed, list):
            require_non_empty = bool(rule.get("require_non_empty"))
            passed = (bool(observed) or not require_non_empty) and all(_is_truthy_report(item) for item in observed)
        else:
            passed = False
    elif kind == "artifact_exists":
        observed = artifacts.get(artifact_key)
        passed = _artifact_exists(observed)
    else:
        observed = {"error": f"Unsupported rule kind: {kind}"}
        passed = False

    evidence = _evidence_for_rule(rule, artifacts)
    evidence_required = bool(rule.get("evidence_required"))
    if evidence_required and not _has_required_evidence(evidence):
        passed = False

    severity = str(rule.get("severity") or "error")
    return {
        "id": rule.get("id"),
        "stage": rule.get("stage"),
        "severity": severity,
        "description": rule.get("description"),
        "kind": kind,
        "passed": passed,
        "blocking": severity == "error" and not passed,
        "evidence_required": evidence_required,
        "evidence": evidence,
        "observed": _summarize_observed(observed),
    }


def _summarize_observed(observed: Any) -> Any:
    if isinstance(observed, dict):
        summary: dict[str, Any] = {}
        for key in (
            "schema",
            "valid",
            "status",
            "error_count",
            "issue_count",
            "below_minimum_count",
            "gap_counts",
            "checks",
        ):
            if key in observed:
                summary[key] = observed[key]
        return summary
    if isinstance(observed, list):
        return {
            "count": len(observed),
            "valid_count": sum(1 for item in observed if _is_truthy_report(item)),
        }
    return observed


def build_page_quality_report(
    *,
    stage: str,
    page_number: int | None,
    project_path: Path,
    artifacts: dict[str, Any],
    reports: dict[str, Any],
    rules: list[dict[str, Any]] | None = None,
    extra: dict[str, Any] | None = None,
) -> dict[str, Any]:
    selected_rules = [rule for rule in (rules or load_quality_rules()) if rule.get("stage") == stage]
    checks = [_evaluate_rule(rule, reports=reports, artifacts=artifacts) for rule in selected_rules]
    blocking_errors = [check for check in checks if check["blocking"]]
    warning_failures = [check for check in checks if check["severity"] == "warning" and not check["passed"]]
    valid = not blocking_errors
    report = {
        "schema": REPORT_SCHEMA,
        "stage": stage,
        "page_number": page_number,
        "project_path": str(project_path),
        "valid": valid,
        "status": "passed" if valid else "rework_required",
        "rule_count": len(checks),
        "passed_count": sum(1 for check in checks if check["passed"]),
        "blocking_error_count": len(blocking_errors),
        "warning_count": len(warning_failures),
        "checks": checks,
        "blocking_errors": blocking_errors,
        "warnings": warning_failures,
        "artifacts": artifacts,
    }
    if extra:
        report["extra"] = extra
    return report


def write_page_quality_report(
    path: Path,
    *,
    stage: str,
    page_number: int | None,
    project_path: Path,
    artifacts: dict[str, Any],
    reports: dict[str, Any],
    rules: list[dict[str, Any]] | None = None,
    extra: dict[str, Any] | None = None,
) -> dict[str, Any]:
    report = build_page_quality_report(
        stage=stage,
        page_number=page_number,
        project_path=project_path,
        artifacts=artifacts,
        reports=reports,
        rules=rules,
        extra=extra,
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return report
