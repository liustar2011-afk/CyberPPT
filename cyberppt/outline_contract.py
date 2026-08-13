"""Solution-first outline contracts and deterministic Stage 01 audits."""

from __future__ import annotations

import json
from pathlib import Path

from cyberppt.argument_flow_contract import audit_argument_flow
from cyberppt.outline_audit_authoring import (
    _author_driven_editorial_issues,
    _editorial_control_issues,
)
from cyberppt.outline_audit_density import (
    _content_page_density_issues,
    _weight_issues,
)
from cyberppt.outline_audit_semantics import (
    _document_semantic_issues,
    _expression_model_issues,
    _onscreen_module_provenance_issues,
    _page_content_unit_contract_issues,
    _semantic_derivation_issues,
    _structural_argument_duty_issues,
)
from cyberppt.outline_audit_shared import AuditIssue
from cyberppt.outline_audit_structure import (
    _content_issues,
    _template_issues,
    _title_style_issues,
    resolve_architecture_mode,
)
from cyberppt.source_argument_model import audit_outline_consumption


REQUIRED_FIELDS = (
    "schema",
    "material_type",
    "audience",
    "architecture_mode",
    "architecture_reason",
    "source_section_weights",
    "pages",
    "retry",
)


def load_outline(path: Path, *, lightweight: bool = False) -> dict[str, object]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8-sig"))
    except json.JSONDecodeError as exc:
        raise ValueError(f"invalid outline JSON: {exc.msg}") from exc
    if not isinstance(payload, dict):
        raise ValueError("outline root must be an object")
    required_fields = (
        tuple(field for field in REQUIRED_FIELDS if field != "retry")
        if lightweight
        else REQUIRED_FIELDS
    )
    for field in required_fields:
        if field not in payload:
            raise ValueError(f"missing required field: {field}")
    if payload.get("schema") not in {"cyberppt.outline.v1", "cyberppt.outline.v2"}:
        raise ValueError("schema must be cyberppt.outline.v1 or cyberppt.outline.v2")
    if not isinstance(payload.get("pages"), list):
        raise ValueError("pages must be an array")
    return payload


def audit_outline(
    outline: dict[str, object],
    source_truth: dict[str, object] | None = None,
    semantic_argument_model: dict[str, object] | None = None,
) -> list[AuditIssue]:
    issues: list[AuditIssue] = []
    if (
        outline.get("architecture_mode") == "consulting"
        and resolve_architecture_mode(outline) == "solution"
    ):
        issues.append(
            AuditIssue(
                "SOLUTION_ARCHITECTURE_REQUIRED",
                "Formal solution material defaults to solution architecture unless the user explicitly requests consulting structure.",
                retry_strategy="switch_to_solution_architecture",
            )
        )
    raw_pages = outline.get("pages")
    pages = [page for page in raw_pages if isinstance(page, dict)] if isinstance(raw_pages, list) else []
    author_issues = _author_driven_editorial_issues(outline, pages)
    if author_issues:
        # A deterministic candidate is source inventory for the professional
        # author, not a submitted outline.  Do not turn pending editorial
        # choices into a noisy collection of formal-quality failures.
        return author_issues
    issues.extend(_title_style_issues(outline, pages))
    issues.extend(_template_issues(pages))
    issues.extend(_content_issues(pages))
    issues.extend(_editorial_control_issues(outline, pages))
    issues.extend(author_issues)
    issues.extend(_weight_issues(outline, pages))
    issues.extend(_content_page_density_issues(pages, source_truth))
    issues.extend(_document_semantic_issues(outline, source_truth))
    issues.extend(_semantic_derivation_issues(outline, pages, source_truth))
    issues.extend(_page_content_unit_contract_issues(outline, pages))
    issues.extend(_structural_argument_duty_issues(pages, source_truth))
    issues.extend(_expression_model_issues(pages, source_truth))
    issues.extend(_onscreen_module_provenance_issues(pages))
    if outline.get("semantic_argument_model_mode") == "required" or semantic_argument_model is not None:
        issues.extend(
            AuditIssue(
                item["code"],
                item["message"],
                (item["node_id"],) if item.get("node_id") else (),
                "rebuild_from_semantic_argument_model",
            )
            for item in audit_outline_consumption(
                outline, semantic_argument_model, source_truth
            )
        )
    if outline.get("argument_contract_mode", "legacy") == "strict":
        if source_truth is None:
            issues.append(
                AuditIssue(
                    "SOURCE_TRUTH_REQUIRED",
                    "Strict outline audits require the authoritative Source Truth artifact.",
                    retry_strategy="reconcile_page_evidence_mapping",
                )
            )
        else:
            issues.extend(
                AuditIssue(
                    issue.code,
                    issue.message,
                    issue.pages,
                    issue.retry_strategy,
                )
                for issue in audit_argument_flow(outline, source_truth)
            )
    return sorted(issues, key=lambda item: ((item.pages or ("",))[0], item.code))


def retry_directive(issues: list[AuditIssue], previous_strategy: str = "") -> dict[str, object]:
    strategies = list(dict.fromkeys(issue.retry_strategy for issue in issues))
    if previous_strategy in strategies:
        strategies = [item for item in strategies if item != previous_strategy] + ["rebuild_from_source_roles"]
    return {
        "required": bool(issues),
        "issue_codes": list(dict.fromkeys(issue.code for issue in issues)),
        "strategies": strategies,
        "instruction": "Change planning direction, rewrite the outline, and submit the next numbered attempt.",
    }
