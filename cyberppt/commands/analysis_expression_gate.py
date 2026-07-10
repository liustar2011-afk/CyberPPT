"""Project-level scaffold and status for analysis-expression gates."""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


GATE_ORDER = (
    "reporting_direction",
    "report_structure",
    "page_design",
    "business_script",
    "drawing_script",
)

REQUIRED_HEADINGS = {
    "reporting_direction": ("汇报对象", "汇报目的", "内容重点", "证据", "优势", "边界", "推荐方向"),
    "report_structure": ("模块一", "模块二", "模块三", "模块四"),
    "page_design": ("封面", "目录", "过渡页", "内容页", "封底"),
    "business_script": ("非上屏：证据链", "来源位置", "完整性校核"),
    "drawing_script": ("上屏文字", "组件关系", "信息密度", "禁止项", "非上屏：证据链"),
}

_STRUCTURE_PAGE_COUNT_FIELDS = ("页数", "页码", "页面数量")
_STRUCTURE_PAGE_TITLE_FIELDS = ("页面标题", "页标题")
_STRUCTURE_VISUAL_FIELDS = ("视觉形式", "视觉形态", "视觉样式")
_NAVIGATION_HEADINGS = ("封面", "目录", "过渡页", "封底")
_NAVIGATION_RESTRICTED_TERMS = ("证据", "决策", "决定")
_DRAWING_GEOMETRY_PATTERN = re.compile(
    r"(?:\b[xy]\s*=|\b(?:width|height|left|top)\s*=|\b\d+(?:\.\d+)?px\b|坐标|像素|几何)",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class AnalysisExpressionStatus:
    adopted: bool
    next_gate: str | None


def _contract_path(project: Path) -> Path:
    return project.expanduser().resolve() / "workbench" / "analysis_expression" / "contract.json"


def _analysis_root(project: Path) -> Path:
    return _contract_path(project).parent


def _artifact_path(project: Path, gate: str) -> Path:
    return _analysis_root(project) / f"{gate}.md"


def _pending_path(project: Path, gate: str) -> Path:
    return _analysis_root(project) / f"{gate}.pending-confirmation.json"


def _approval_path(project: Path, gate: str) -> Path:
    return _analysis_root(project) / f"{gate}.approved.json"


def _write_json(path: Path, payload: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def adopt_analysis_expression_contract(project: Path) -> Path:
    contract = _contract_path(project)
    if not contract.exists():
        _write_json(
            contract,
            {
                "schema": "cyberppt.analysis_expression.v1",
                "adopted": True,
                "gates": {},
            },
        )
    return contract


def _validate_gate(gate: str) -> str:
    if gate not in GATE_ORDER:
        allowed = ", ".join(GATE_ORDER)
        raise ValueError(f"unknown analysis-expression gate: {gate}; expected one of {allowed}")
    return gate


def _predecessor(gate: str) -> str | None:
    index = GATE_ORDER.index(gate)
    return GATE_ORDER[index - 1] if index else None


def _approval_exists(project: Path, gate: str) -> bool:
    path = _approval_path(project, gate)
    if not path.exists():
        return False
    try:
        return bool(json.loads(path.read_text(encoding="utf-8")).get("approved"))
    except json.JSONDecodeError:
        return False


def _utc_now() -> str:
    return datetime.now(UTC).isoformat()


def _section_text(text: str, heading: str) -> str:
    match = re.search(rf"^#+\s*{re.escape(heading)}\s*$", text, re.MULTILINE)
    if not match:
        return ""
    following = re.search(r"^#+\s+", text[match.end() :], re.MULTILINE)
    end = match.end() + following.start() if following else len(text)
    return text[match.end() : end]


def validate_analysis_artifact(gate: str, text: str) -> list[str]:
    """Return semantic validation failures for one ordered analysis artifact."""

    _validate_gate(gate)
    errors = [f"missing required heading: {heading}" for heading in REQUIRED_HEADINGS[gate] if heading not in text]

    if gate == "report_structure":
        module_count = len(re.findall(r"^#+\s*模块[一二三四五六七八九十0-9]+\s*$", text, re.MULTILINE))
        if not 4 <= module_count <= 6:
            errors.append("report_structure must contain 4-6 modules")
        if any(field in text for field in _STRUCTURE_PAGE_COUNT_FIELDS):
            errors.append("report_structure must not contain page count fields")
        if any(field in text for field in _STRUCTURE_PAGE_TITLE_FIELDS):
            errors.append("report_structure must not contain page title fields")
        if any(field in text for field in _STRUCTURE_VISUAL_FIELDS):
            errors.append("report_structure must not contain visual form fields")

    if gate == "page_design":
        navigation_text = "\n".join(_section_text(text, heading) for heading in _NAVIGATION_HEADINGS)
        if any(term in navigation_text for term in _NAVIGATION_RESTRICTED_TERMS):
            errors.append("navigation pages must not contain evidence or decisions")

    if gate == "drawing_script" and _DRAWING_GEOMETRY_PATTERN.search(text):
        errors.append("drawing_script must not contain geometry keywords")

    return errors


def _normalize_options(options: list[dict[str, Any]]) -> list[dict[str, Any]]:
    normalized: list[dict[str, Any]] = []
    for option in options:
        if not isinstance(option, dict) or not isinstance(option.get("id"), str) or not option["id"]:
            raise ValueError("each confirmation option requires a non-empty id")
        normalized.append(dict(option))
    return normalized


def stage_analysis_artifact(
    project: Path,
    gate: str,
    source: str,
    recommendation: str,
    options: list[dict[str, Any]],
) -> Path:
    """Save a validated artifact and its pending, user-selectable confirmation record."""

    gate = _validate_gate(gate)
    root = project.expanduser().resolve()
    predecessor = _predecessor(gate)
    if predecessor and not _approval_exists(root, predecessor):
        raise ValueError(f"{predecessor} approval is required before staging {gate}")

    errors = validate_analysis_artifact(gate, source)
    if errors:
        raise ValueError("; ".join(errors))

    artifact = _artifact_path(root, gate)
    artifact.parent.mkdir(parents=True, exist_ok=True)
    artifact.write_text(source, encoding="utf-8")
    pending = _pending_path(root, gate)
    normalized_options = _normalize_options(options)
    _write_json(
        pending,
        {
            "schema": "cyberppt.analysis_expression.pending_confirmation.v1",
            "gate": gate,
            "status": "pending_confirmation",
            "artifact": str(artifact),
            "source_sha256": hashlib.sha256(source.encode("utf-8")).hexdigest(),
            "recommendation": recommendation,
            "options": normalized_options,
            "created_at": _utc_now(),
        },
    )
    approval = _approval_path(root, gate)
    if approval.exists():
        approval.unlink()
    return pending


def approve_analysis_artifact(project: Path, gate: str, option_id: str, note: str = "") -> Path:
    """Persist the selected option after a staged confirmation record is reviewed."""

    gate = _validate_gate(gate)
    root = project.expanduser().resolve()
    pending = _pending_path(root, gate)
    if not pending.exists():
        raise FileNotFoundError(f"no pending confirmation for {gate}; stage the artifact before approval")
    data = json.loads(pending.read_text(encoding="utf-8"))
    option_ids = {option.get("id") for option in data.get("options", []) if isinstance(option, dict)}
    if option_id not in option_ids:
        raise ValueError(f"option_id is not available for {gate}: {option_id}")

    approval = _approval_path(root, gate)
    _write_json(
        approval,
        {
            "schema": "cyberppt.analysis_expression.approval.v1",
            "gate": gate,
            "approved": True,
            "approved_at": _utc_now(),
            "pending_confirmation": str(pending),
            "artifact": data["artifact"],
            "source_sha256": data["source_sha256"],
            "option_id": option_id,
            "note": note,
        },
    )
    return approval


def get_analysis_expression_status(project: Path) -> AnalysisExpressionStatus:
    contract = _contract_path(project)
    if not contract.exists():
        return AnalysisExpressionStatus(adopted=False, next_gate=None)
    root = project.expanduser().resolve()
    next_gate = next((gate for gate in GATE_ORDER if not _approval_exists(root, gate)), None)
    return AnalysisExpressionStatus(adopted=True, next_gate=next_gate)
