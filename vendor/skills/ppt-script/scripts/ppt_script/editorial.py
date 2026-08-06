from __future__ import annotations

import json
import hashlib
import re
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Iterable, Literal

from .extractors import extract_project_sources
from .source_truth import parse_source_truth_map

EditorialPhase = Literal[
    "semantic-planning",
    "independent",
    "storyline-candidates",
    "storyline",
    "outline",
    "red-team-review",
    "red-team",
]
EditorialContextMode = Literal[
    "semantic-planning",
    "independent",
    "storyline-candidates",
    "storyline",
    "outline",
    "red-team",
    "red-team-response",
]

EDITORIAL_MODULE_IDS: tuple[str, ...] = (
    "editorial-semantic-planning",
    "editorial-independent",
    "editorial-storyline-candidates",
    "editorial-storyline",
    "editorial-outline",
    "editorial-red-team",
    "editorial-red-team-response",
)

_PHASES: tuple[EditorialPhase, ...] = (
    "semantic-planning",
    "independent",
    "storyline-candidates",
    "storyline",
    "outline",
    "red-team-review",
    "red-team",
)
_BASE_FILES = (
    "contracts/semantic-core.json",
    "contracts/content-role-map.json",
    "contracts/solution-model.json",
)
_EXPECTED_SCHEMAS = {
    "contracts/semantic-core.json": "ppt-script.editorial-semantic-core.v2",
    "contracts/content-role-map.json": "ppt-script.editorial-content-role-map.v2",
    "contracts/solution-model.json": "ppt-script.editorial-solution-model.v2",
    "analysis/editorial/01-independent-judgment.json": "ppt-script.editorial-independent-judgment.v2",
    "analysis/editorial/storyline-candidates.json": "ppt-script.editorial-storyline-candidates.v2",
    "analysis/editorial/02-storyline-verdict.json": "ppt-script.editorial-storyline-verdict.v2",
    "analysis/editorial/03-outline-review.json": "ppt-script.editorial-outline-review.v2",
    "analysis/editorial/04-red-team-review.json": "ppt-script.editorial-red-team.v2",
    "analysis/editorial/05-red-team-response.json": "ppt-script.editorial-red-team-response.v1",
}
_SEMANTIC_REQUIRED_TEXT: dict[str, tuple[tuple[str, str], ...]] = {
    "contracts/semantic-core.json": (
        ("core_proposition", "missing-core-proposition"),
        ("business_subject", "missing-business-subject"),
        ("material_purpose", "missing-material-purpose"),
        ("existing_foundation", "missing-existing-foundation"),
        ("upgrade_essence", "missing-upgrade-essence"),
        ("core_construction", "missing-core-construction"),
        ("implementation_scope", "missing-implementation-scope"),
        ("project_phase", "missing-project-phase"),
    ),
    "contracts/solution-model.json": (
        ("objective", "missing-solution-objective"),
    ),
}
_PHASE_FILES: dict[EditorialPhase, tuple[str, ...]] = {
    "semantic-planning": (),
    "independent": ("analysis/editorial/01-independent-judgment.json",),
    "storyline-candidates": (
        "analysis/editorial/01-independent-judgment.json",
        "analysis/editorial/storyline-candidates.json",
    ),
    "storyline": (
        "analysis/editorial/01-independent-judgment.json",
        "analysis/editorial/storyline-candidates.json",
        "analysis/editorial/02-storyline-verdict.json",
    ),
    "outline": (
        "analysis/editorial/01-independent-judgment.json",
        "analysis/editorial/storyline-candidates.json",
        "analysis/editorial/02-storyline-verdict.json",
        "analysis/editorial/03-outline-review.json",
    ),
    "red-team": (
        "analysis/editorial/01-independent-judgment.json",
        "analysis/editorial/storyline-candidates.json",
        "analysis/editorial/02-storyline-verdict.json",
        "analysis/editorial/03-outline-review.json",
        "analysis/editorial/04-red-team-review.json",
        "analysis/editorial/05-red-team-response.json",
    ),
    "red-team-review": (
        "analysis/editorial/01-independent-judgment.json",
        "analysis/editorial/storyline-candidates.json",
        "analysis/editorial/02-storyline-verdict.json",
        "analysis/editorial/03-outline-review.json",
        "analysis/editorial/04-red-team-review.json",
    ),
}
_VALID_VERDICTS = {"ACCEPT", "MERGE", "REJECT"}
EDITORIAL_BUSINESS_ISSUE_CODES = frozenset(
    {
        "business-subject-shift",
        "existing-new-confusion",
        "background-overweight",
        "core-content-demoted",
        "missing-solution-object",
        "support-over-business",
        "framework-hard-fit",
        "chapter-weight-distortion",
        "duplicate-page",
        "mergeable-page",
        "sequence-break",
        "generic-title",
        "title-content-mismatch",
    }
)
_VALID_CONTENT_ROLES = {
    "background",
    "context",
    "constraint",
    "core",
    "core-content",
    "decision",
    "evidence",
    "problem",
    "risk",
    "solution",
    "support",
    "supporting",
    "supporting-content",
    "action",
    "outcome",
    "背景",
    "约束",
    "核心内容",
    "核心方案",
    "必要解释",
    "支撑证据",
    "实施保障",
    "补充材料",
    "决策事项",
    "依据",
    "问题",
    "风险",
    "方案",
    "支撑内容",
    "行动",
    "成效",
}
_PLACEHOLDERS = (
    "todo",
    "tbd",
    "placeholder",
    "待生成",
    "待填写",
    "待补充",
    "待完善",
    "待确认",
    "占位",
)
_SOURCE_ID_RE = re.compile(r"^S\d{3,}$")
_EDITORIAL_CASE_SCHEMA = "ppt-script.editorial-case.v1"
_EDITORIAL_CASE_ID_RE = re.compile(r"^EDITORIAL-CASE-[0-9A-Za-z][0-9A-Za-z.-]*$")
_EDITORIAL_CASE_STATUSES = frozenset({"candidate", "approved", "rejected", "superseded"})
_EDITORIAL_CASE_SOURCE_RE = re.compile(r"\bS\d{3,}\b|source\s*id", re.IGNORECASE)
_EDITORIAL_CASE_CURRENT_FACT_RE = re.compile(
    r"(?:当前项目|本项目|本次项目).{0,20}(?:主体|单位|公司|机构|\d|已|具备|能力|形成|建成|上线|运行)|"
    r"^\d+(?:\.\d+)?$|\d{4}(?:年|[-/.]\d{1,2}(?:[-/.]\d{1,2})?)|"
    r"\d+(?:\.\d+)?(?:%|万元|亿元|万|亿|个|项|台|套|人|家|次)|"
    r"(?:数字|金额|数量|规模).{0,8}\d+|"
    r"已具备|已经具备|已形成|已经形成|已建成|已经建成|已上线|已经上线|"
    r"具备.{0,12}能力|形成.{0,12}能力|建设完成|投入运行",
    re.IGNORECASE,
)
_EDITORIAL_CASE_TEXT_FIELDS = (
    "original_result",
    "user_feedback",
    "accepted_revision",
    "root_cause",
)
_EDITORIAL_TEMPLATES: tuple[tuple[str, str], ...] = (
    ("editorial-semantic-core.json", "contracts/semantic-core.json"),
    ("editorial-content-role-map.json", "contracts/content-role-map.json"),
    ("editorial-solution-model.json", "contracts/solution-model.json"),
    ("editorial-independent-judgment.json", "analysis/editorial/01-independent-judgment.json"),
    ("editorial-storyline-candidates.json", "analysis/editorial/storyline-candidates.json"),
    ("editorial-storyline-verdict.json", "analysis/editorial/02-storyline-verdict.json"),
    ("editorial-outline-review.json", "analysis/editorial/03-outline-review.json"),
    ("editorial-red-team.json", "analysis/editorial/04-red-team-review.json"),
    ("editorial-red-team-response.json", "analysis/editorial/05-red-team-response.json"),
)
_EDITORIAL_CONTEXT_FILES: dict[EditorialContextMode, str] = {
    "semantic-planning": "analysis/editorial/00-semantic-planning-context.md",
    "independent": "analysis/editorial/00-independent-context.md",
    "storyline-candidates": "analysis/editorial/00-storyline-candidates-context.md",
    "storyline": "analysis/editorial/00-storyline-context.md",
    "outline": "analysis/editorial/00-outline-context.md",
    "red-team": "analysis/editorial/00-red-team-context.md",
    "red-team-response": "analysis/editorial/00-red-team-response-context.md",
}
_CONTEXT_STATE_BY_MODE: dict[EditorialContextMode, str] = {
    "semantic-planning": "COGNITIVE_READY",
    "independent": "SEMANTIC_PLANNING_READY",
    "storyline-candidates": "EDITORIAL_JUDGMENT_READY",
    "storyline": "STORYLINE_CANDIDATES_READY",
    "outline": "PAGE_PLAN_READY",
    "red-team": "OUTLINE_EDITORIAL_APPROVED",
    "red-team-response": "RED_TEAM_REVIEW_READY",
}


@dataclass(frozen=True, slots=True)
class EditorialIssue:
    code: str
    message: str
    location: str
    severity: str = "error"


@dataclass(frozen=True, slots=True)
class EditorialAudit:
    phase: EditorialPhase
    passed: bool
    issues: tuple[EditorialIssue, ...]
    metrics: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema": "ppt-script.editorial-audit.v1",
            "phase": self.phase,
            "passed": self.passed,
            "metrics": self.metrics,
            "issues": [asdict(item) for item in self.issues],
        }


def _normalized_semantic_ids(value: Any) -> set[str]:
    if not isinstance(value, (list, tuple, set)):
        return set()
    normalized: set[str] = set()
    for item in value:
        candidate = item.get("id") if isinstance(item, dict) else item
        if isinstance(candidate, str) and candidate.strip():
            normalized.add(candidate.strip().casefold())
    return normalized


def evaluate_editorial_regression(
    actual: dict[str, Any], expected: dict[str, Any]
) -> EditorialAudit:
    """Compare stable semantic IDs without coupling regression to exact prose."""
    actual_findings = _normalized_semantic_ids(actual.get("findings"))
    actual_boundaries = _normalized_semantic_ids(actual.get("boundaries"))
    actual_interpretations = _normalized_semantic_ids(actual.get("interpretations"))
    required_findings = _normalized_semantic_ids(expected.get("required_findings"))
    required_boundaries = _normalized_semantic_ids(expected.get("required_boundaries"))
    forbidden_interpretations = _normalized_semantic_ids(expected.get("forbidden_interpretations"))

    missing_findings = sorted(required_findings - actual_findings)
    missing_boundaries = sorted(required_boundaries - actual_boundaries)
    present_forbidden = sorted(forbidden_interpretations & actual_interpretations)
    issues = [
        EditorialIssue(
            "missing-required-finding",
            f"缺少必需总编判断：{item_id}",
            "actual.findings",
        )
        for item_id in missing_findings
    ]
    issues.extend(
        EditorialIssue(
            "missing-required-boundary",
            f"缺少必需边界：{item_id}",
            "actual.boundaries",
        )
        for item_id in missing_boundaries
    )
    issues.extend(
        EditorialIssue(
            "forbidden-interpretation-present",
            f"出现禁止解读：{item_id}",
            "actual.interpretations",
        )
        for item_id in present_forbidden
    )
    return EditorialAudit(
        phase="outline",
        passed=not issues,
        issues=tuple(issues),
        metrics={
            "required_findings": sorted(required_findings),
            "required_boundaries": sorted(required_boundaries),
            "forbidden_interpretations": sorted(forbidden_interpretations),
            "actual_findings": sorted(actual_findings),
            "actual_boundaries": sorted(actual_boundaries),
            "actual_interpretations": sorted(actual_interpretations),
            "missing_required_findings": missing_findings,
            "missing_required_boundaries": missing_boundaries,
            "present_forbidden_interpretations": present_forbidden,
            "error_count": len(issues),
        },
    )


def _is_meaningful_condition_phrase(value: str) -> bool:
    return bool(re.search(r"[A-Za-z0-9_-]{2,}|[\u4e00-\u9fff]{2,}", value))


def _condition_matches(conditions: Iterable[str], issue_types: Iterable[str]) -> bool:
    normalized_conditions = tuple(condition.strip().casefold() for condition in conditions if condition.strip())
    for issue_type in issue_types:
        phrase = issue_type.strip().casefold()
        if _is_meaningful_condition_phrase(phrase) and any(phrase in condition for condition in normalized_conditions):
            return True
    return False


def _case_string_list(value: Any) -> bool:
    return isinstance(value, list) and bool(value) and all(isinstance(item, str) and item.strip() for item in value)


def _case_text_values(value: Any) -> Iterable[str]:
    if isinstance(value, str):
        yield value
    elif isinstance(value, (int, float)) and not isinstance(value, bool):
        yield str(value)
    elif isinstance(value, list):
        for item in value:
            yield from _case_text_values(item)
    elif isinstance(value, dict):
        for key, item in value.items():
            yield str(key)
            yield from _case_text_values(item)


def validate_editorial_case(payload: dict[str, Any]) -> tuple[EditorialIssue, ...]:
    """Validate reusable editorial cases and prohibit project-fact leakage."""
    issues: list[EditorialIssue] = []
    location = "editorial-case"
    if not isinstance(payload, dict):
        return (EditorialIssue("invalid-case", "总编案例必须是 JSON 对象。", location),)
    if payload.get("schema") != _EDITORIAL_CASE_SCHEMA:
        _issue(issues, "invalid-case-schema", f"schema 必须为 {_EDITORIAL_CASE_SCHEMA}。", location)
    case_id = payload.get("case_id")
    if not isinstance(case_id, str) or not _EDITORIAL_CASE_ID_RE.fullmatch(case_id):
        _issue(issues, "invalid-case-id", "case_id 必须以 EDITORIAL-CASE- 开头。", location)
    status = payload.get("status")
    if not isinstance(status, str) or status not in _EDITORIAL_CASE_STATUSES:
        _issue(issues, "invalid-case-status", f"status 必须是 {sorted(_EDITORIAL_CASE_STATUSES)} 之一。", location)
    issue_type = payload.get("issue_type")
    if not isinstance(issue_type, str) or _is_placeholder(issue_type):
        _issue(issues, "missing-case-issue-type", "缺少非占位的 issue_type。", location)
    for field in _EDITORIAL_CASE_TEXT_FIELDS:
        value = payload.get(field)
        if not isinstance(value, str) or _is_placeholder(value):
            _issue(issues, f"missing-case-{field}", f"缺少非占位的 {field}。", location)
    reusable_principle = payload.get("reusable_principle")
    if not isinstance(reusable_principle, dict):
        _issue(issues, "invalid-reusable-principle", "reusable_principle 必须是对象。", location)
    else:
        principle = reusable_principle.get("principle")
        if not isinstance(principle, str) or _is_placeholder(principle):
            _issue(issues, "missing-reusable-principle", "reusable_principle.principle 必须为非占位文本。", location)
        if not _case_string_list(reusable_principle.get("allowed_transformations")):
            _issue(
                issues,
                "invalid-allowed-transformations",
                "reusable_principle.allowed_transformations 必须是非空字符串数组。",
                location,
            )
    for field in ("applicable_conditions", "do_not_copy_conditions"):
        if not _case_string_list(payload.get(field)):
            _issue(issues, f"invalid-case-{field}", f"{field} 必须是非空字符串数组。", location)

    contaminated = any(
        _EDITORIAL_CASE_SOURCE_RE.search(text) or _EDITORIAL_CASE_CURRENT_FACT_RE.search(text)
        for text in _case_text_values(payload)
    )
    if contaminated:
        _issue(
            issues,
            "case-fact-contamination",
            "总编案例不得携带当前项目主体、数字、日期、能力或 Source ID 等事实主张。",
            location,
        )
    return tuple(issues)


def select_editorial_cases(repo_root: Path, issue_types: Iterable[str]) -> tuple[dict[str, Any], ...]:
    """Return valid approved cases, ordered by exact issue type then condition overlap."""
    requested = {value.strip() for value in issue_types if isinstance(value, str) and value.strip()}
    case_root = Path(repo_root) / "knowledge/editorial-cases"
    if not case_root.is_dir():
        return ()
    exact: list[dict[str, Any]] = []
    conditional: list[dict[str, Any]] = []
    for path in sorted(case_root.rglob("*.json")):
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        if not isinstance(payload, dict) or validate_editorial_case(payload) or payload.get("status") != "approved":
            continue
        normalized = dict(payload)
        normalized["source_file"] = str(path.relative_to(Path(repo_root)))
        if not requested or payload.get("issue_type") in requested:
            exact.append(normalized)
            continue
        conditions = payload.get("applicable_conditions", [])
        if isinstance(conditions, list) and _condition_matches(conditions, requested):
            conditional.append(normalized)
    exact.sort(key=lambda item: str(item["case_id"]))
    conditional.sort(key=lambda item: str(item["case_id"]))
    return tuple((*exact, *conditional))


def build_editorial_case_context(
    project: str | Path,
    repo_root: str | Path,
) -> Path:
    """Render approved cases as method-only records, never as historical fact excerpts."""
    project_path = Path(project)
    root = Path(repo_root)
    issue_types: list[str] = []
    state_path = project_path / "analysis/editorial/rework-state.json"
    if state_path.is_file():
        try:
            state = json.loads(state_path.read_text(encoding="utf-8"))
            raw = state.get("issue_codes", []) if isinstance(state, dict) else []
            if isinstance(raw, list):
                issue_types.extend(str(item) for item in raw if isinstance(item, str))
        except (OSError, json.JSONDecodeError):
            pass
    cases = select_editorial_cases(root, issue_types)
    lines = [
        "# 已批准总编方法案例",
        "",
        "> 本文件只保留方法原则、适用/禁用条件与允许变形；历史原稿、历史修订稿、主体、数字、日期和能力事实均不进入当前项目上下文。",
        "",
    ]
    if not cases:
        lines.append("当前没有通过治理校验且适配本阶段的 approved 总编案例。")
    for case in cases:
        principle = case.get("reusable_principle", {})
        lines.extend(
            [
                f"## {case['case_id']}｜{case['issue_type']}",
                "",
                f"- 深层原因：{case['root_cause']}",
                f"- 可复用原则：{principle.get('principle', '')}",
                "- 允许变形：" + "；".join(principle.get("allowed_transformations", [])),
                "- 适用条件：" + "；".join(case.get("applicable_conditions", [])),
                "- 禁止照搬：" + "；".join(case.get("do_not_copy_conditions", [])),
                "",
            ]
        )
    output = project_path / "analysis/editorial/00-approved-method-cases.md"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")
    return output


def _copy_editorial_template(repo_root: Path, template_name: str, target: Path) -> None:
    if target.is_file():
        return
    template = repo_root / "templates" / template_name
    if not template.is_file():
        raise FileNotFoundError(f"missing editorial template: {template}")
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(template.read_text(encoding="utf-8"), encoding="utf-8")


def initialize_editorial(project: str | Path, repo_root: str | Path) -> tuple[Path, ...]:
    """Create the chief-editor scaffolds without overwriting existing review work."""
    project_path = Path(project)
    root = Path(repo_root)
    (project_path / "analysis/editorial").mkdir(parents=True, exist_ok=True)
    (project_path / "knowledge/editorial-frameworks").mkdir(parents=True, exist_ok=True)

    outputs: list[Path] = []
    for template_name, relative in _EDITORIAL_TEMPLATES:
        target = project_path / relative
        _copy_editorial_template(root, template_name, target)
        outputs.append(target)

    metadata = project_path / "project.json"
    if metadata.is_file():
        payload = json.loads(metadata.read_text(encoding="utf-8"))
        if not isinstance(payload, dict):
            raise ValueError("project.json must be an object")
        defaults = {
            "editorial_mode": "chief-editor",
            "editorial_gate_required": True,
            "editorial_contract_version": 2,
            "editorial_migration_status": "current",
            "editorial_auto_rework_limit": 2,
            "editorial_case_status_allowed": ["approved"],
        }
        for key, value in defaults.items():
            payload.setdefault(key, value)
        metadata.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return tuple(outputs)


def _context_section(path: Path, label: str) -> str:
    if not path.is_file():
        return ""
    text = path.read_text(encoding="utf-8", errors="ignore").strip()
    if not text:
        return ""
    return f"## `{label}`\n\n{text}\n"


def build_editorial_context(
    project: str | Path,
    repo_root: str | Path,
    mode: EditorialContextMode,
) -> Path:
    """Build editorial contexts through the repository's single context-pack authority."""
    if mode not in _EDITORIAL_CONTEXT_FILES:
        raise ValueError(f"unknown editorial context mode: {mode}")
    project_path = Path(project)
    root = Path(repo_root)
    prerequisite: dict[EditorialContextMode, EditorialPhase | None] = {
        "semantic-planning": None,
        "independent": "semantic-planning",
        "storyline-candidates": "independent",
        "storyline": "storyline-candidates",
        "outline": "storyline",
        "red-team": "outline",
        "red-team-response": "red-team-review",
    }
    required_phase = prerequisite[mode]
    if required_phase is not None:
        upstream = audit_editorial(project_path, required_phase)
        if not upstream.passed:
            codes = ", ".join(issue.code for issue in upstream.issues)
            raise ValueError(
                f"{required_phase} editorial audit must pass before {mode} context: {codes}"
            )
    if not extract_project_sources(project_path).text.strip():
        raise ValueError("source/ 中没有可读取的源材料。")
    build_editorial_case_context(project_path, root)
    # Local import avoids the workflow -> editorial -> context import cycle.
    from .context import build_context_pack

    pack = build_context_pack(
        project_path,
        root,
        state_override=_CONTEXT_STATE_BY_MODE[mode],
        mode="deep",
    )
    output = project_path / _EDITORIAL_CONTEXT_FILES[mode]
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(pack.markdown, encoding="utf-8")
    return output


def _issue(issues: list[EditorialIssue], code: str, message: str, location: str) -> None:
    issues.append(EditorialIssue(code, message, location))


def _load_json(project: Path, relative: str, issues: list[EditorialIssue]) -> dict[str, Any] | None:
    path = project / relative
    if not path.is_file():
        _issue(issues, "missing-file", f"缺少编辑审计文件：{relative}", relative)
        return None
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as exc:
        _issue(issues, "unreadable-file", f"无法读取编辑审计文件：{exc}", relative)
        return None
    if not text.strip():
        _issue(issues, "empty-file", "编辑审计文件不能为空。", relative)
        return None
    try:
        payload = json.loads(text)
    except json.JSONDecodeError as exc:
        _issue(issues, "invalid-json", f"编辑审计文件不是有效 JSON：{exc}", relative)
        return None
    if not isinstance(payload, dict):
        _issue(issues, "invalid-root", "编辑审计文件根节点必须是 JSON 对象。", relative)
        return None
    return payload


def _is_placeholder(value: str) -> bool:
    compact = value.strip().lower()
    return not compact or any(marker in compact for marker in _PLACEHOLDERS)


def _check_placeholders(value: Any, relative: str, issues: list[EditorialIssue], path: str = "$") -> None:
    if isinstance(value, str):
        if _is_placeholder(value):
            _issue(issues, "placeholder-value", f"{path} 不能是空值或占位值。", relative)
    elif isinstance(value, list):
        for index, item in enumerate(value):
            _check_placeholders(item, relative, issues, f"{path}[{index}]")
    elif isinstance(value, dict):
        for key, item in value.items():
            _check_placeholders(item, relative, issues, f"{path}.{key}")


def _known_source_ids(project: Path, issues: list[EditorialIssue]) -> set[str]:
    relative = "analysis/01-source-truth-map.md"
    path = project / relative
    if not path.is_file():
        _issue(issues, "missing-source-truth", "缺少 Source Truth Map。", relative)
        return set()
    try:
        text = path.read_text(encoding="utf-8", errors="ignore")
    except OSError as exc:
        _issue(issues, "unreadable-source-truth", f"无法读取 Source Truth Map：{exc}", relative)
        return set()
    if not text.strip():
        _issue(issues, "empty-source-truth", "Source Truth Map 不能为空。", relative)
        return set()
    truth = parse_source_truth_map(text)
    if truth.issues:
        _issue(issues, "invalid-source-truth", "; ".join(truth.issues), relative)
    known = {item.source_id for item in truth.items}
    if not known:
        _issue(issues, "empty-source-truth", "Source Truth Map 没有有效 S### 条目。", relative)
    return known


def _source_ids(value: Any, *, field: str, location: str, issues: list[EditorialIssue]) -> list[str]:
    if not isinstance(value, list):
        _issue(issues, "invalid-source-list", f"{field} 必须是非空 Source ID 字符串数组。", location)
        return []
    result: list[str] = []
    for item in value:
        if not isinstance(item, str):
            _issue(issues, "invalid-source-id", f"{field} 的元素必须是字符串。", location)
            continue
        source_id = item.strip()
        if not source_id:
            _issue(issues, "empty-source-id", f"{field} 不能包含空 Source ID。", location)
            continue
        result.append(source_id)
    if not result:
        _issue(issues, "missing-source-reference", f"{field} 至少需要一个 Source ID。", location)
    for source_id in result:
        if not _SOURCE_ID_RE.fullmatch(source_id):
            _issue(issues, "invalid-source-id", f"{field} 包含无效 Source ID：{source_id!r}。", location)
    return result


def _require_source_ids(item: dict[str, Any], *, location: str, known: set[str], issues: list[EditorialIssue]) -> list[str]:
    if "source_ids" not in item:
        _issue(issues, "missing-source-reference", "缺少必填 source_ids。", location)
        return []
    source_ids = _source_ids(item["source_ids"], field="source_ids", location=location, issues=issues)
    for source_id in source_ids:
        if source_id not in known:
            _issue(issues, "unknown-source", f"引用了 Source Truth Map 中不存在的来源：{source_id}。", location)
    return source_ids


def _require_substantive_fields(
    payload: dict[str, Any],
    *,
    location: str,
    fields: tuple[tuple[str, str], ...],
    issues: list[EditorialIssue],
) -> None:
    for field, code in fields:
        value = payload.get(field)
        if not isinstance(value, str) or _is_placeholder(value):
            _issue(issues, code, f"缺少非占位的必填字段 {field}。", location)


def _require_string_list(
    payload: dict[str, Any],
    field: str,
    *,
    location: str,
    issues: list[EditorialIssue],
    code: str | None = None,
) -> list[str]:
    value = payload.get(field)
    if not isinstance(value, list) or not value or any(
        not isinstance(item, str) or _is_placeholder(item) for item in value
    ):
        _issue(
            issues,
            code or f"invalid-{field.replace('_', '-')}",
            f"{field} 必须是非空且无占位值的字符串数组。",
            location,
        )
        return []
    return [item.strip() for item in value]


def _file_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _binding_target_is_substantive(path: Path, relative: str) -> bool:
    if not path.is_file():
        return False
    try:
        text = path.read_text(encoding="utf-8", errors="ignore").strip()
    except OSError:
        return False
    if not text or any(marker in text.lower() for marker in _PLACEHOLDERS):
        return False
    if path.suffix.lower() != ".json":
        return True
    try:
        payload = json.loads(text)
    except json.JSONDecodeError:
        return False
    if not isinstance(payload, dict):
        return False
    if relative == "contracts/deck-decision.json":
        return all(
            isinstance(payload.get(field), str) and payload[field].strip()
            for field in ("audience", "objective", "decision_request", "core_conclusion")
        )
    if relative == "contracts/chapter-contracts.json":
        return isinstance(payload.get("chapters"), list) and bool(payload["chapters"])
    if relative == "contracts/page-contracts.json":
        return isinstance(payload.get("pages"), list) and bool(payload["pages"])
    return True


def _validate_digest_bindings(
    project: Path,
    payload: dict[str, Any],
    relative: str,
    *,
    inputs: tuple[str, ...] = (),
    targets: tuple[str, ...] = (),
    issues: list[EditorialIssue],
) -> None:
    provenance = payload.get("provenance")
    if not isinstance(provenance, dict):
        _issue(issues, "missing-provenance", "缺少 provenance 输入/目标摘要绑定。", relative)
        provenance = {}
    for group, required in (("inputs", inputs), ("targets", targets)):
        recorded = provenance.get(group)
        if not isinstance(recorded, dict):
            recorded = {}
        for target_relative in required:
            target = project / target_relative
            if not _binding_target_is_substantive(target, target_relative):
                code = "missing-audit-target" if group == "targets" else "missing-audit-input"
                _issue(issues, code, f"摘要绑定对象不存在或为空：{target_relative}", relative)
                continue
            digest = recorded.get(target_relative)
            if not isinstance(digest, str) or not re.fullmatch(r"[0-9a-f]{64}", digest):
                code = "missing-target-digest" if group == "targets" else "missing-input-digest"
                _issue(issues, code, f"未记录 {target_relative} 的 SHA256 摘要。", relative)
                continue
            actual = _file_sha256(target)
            if digest != actual:
                code = "stale-target-digest" if group == "targets" else "stale-input-digest"
                _issue(
                    issues,
                    code,
                    f"{target_relative} 已变更：记录摘要 {digest}，当前摘要 {actual}。",
                    relative,
                )


def _validate_registered_bindings(
    project: Path,
    payload: dict[str, Any],
    relative: str,
    issues: list[EditorialIssue],
) -> None:
    from .provenance_bindings import binding_groups

    groups = binding_groups(relative)
    if not groups:
        return
    _validate_digest_bindings(
        project,
        payload,
        relative,
        inputs=groups.get("inputs", ()),
        targets=groups.get("targets", ()),
        issues=issues,
    )


def _semantic_contract_details(
    payloads: dict[str, dict[str, Any]],
    project: Path,
    known: set[str],
    issues: list[EditorialIssue],
) -> None:
    core_relative = "contracts/semantic-core.json"
    core = payloads.get(core_relative)
    if core is not None:
        _validate_registered_bindings(project, core, core_relative, issues)
        _require_string_list(core, "boundaries", location=core_relative, issues=issues)
        _require_string_list(core, "forbidden_misreadings", location=core_relative, issues=issues)

    roles_relative = "contracts/content-role-map.json"
    roles = payloads.get(roles_relative)
    if roles is not None:
        _validate_registered_bindings(project, roles, roles_relative, issues)

    solution_relative = "contracts/solution-model.json"
    solution = payloads.get(solution_relative)
    if solution is not None:
        _validate_registered_bindings(project, solution, solution_relative, issues)
        objects = solution.get("objects")
        if not isinstance(objects, list) or not objects:
            _issue(issues, "missing-solution-objects", "solution-model 至少需要一个真实业务对象。", solution_relative)
        else:
            identifiers: set[str] = set()
            for index, item in enumerate(objects, start=1):
                location = f"{solution_relative}#objects[{index}]"
                if not isinstance(item, dict):
                    _issue(issues, "invalid-solution-object", "方案对象必须是对象。", location)
                    continue
                _require_substantive_fields(
                    item,
                    location=location,
                    fields=tuple(
                        (field, f"missing-solution-object-{field.replace('_', '-')}")
                        for field in ("object_id", "name", "role", "state", "boundary")
                    ),
                    issues=issues,
                )
                object_id = item.get("object_id")
                if isinstance(object_id, str):
                    if object_id in identifiers:
                        _issue(issues, "duplicate-solution-object", f"方案对象 ID 重复：{object_id}", location)
                    identifiers.add(object_id)
                for relation in ("upstream", "downstream"):
                    value = item.get(relation)
                    if not isinstance(value, list) or any(not isinstance(entry, str) for entry in value):
                        _issue(issues, f"invalid-solution-{relation}", f"{relation} 必须是字符串数组。", location)
                _require_source_ids(item, location=location, known=known, issues=issues)


def _independent_details(
    payload: dict[str, Any],
    project: Path,
    relative: str,
    issues: list[EditorialIssue],
) -> None:
    _validate_registered_bindings(project, payload, relative, issues)
    _require_substantive_fields(
        payload,
        location=relative,
        fields=(("material_essence", "missing-material-essence"), ("business_subject", "missing-business-subject")),
        issues=issues,
    )
    distinctions = payload.get("work_state_distinctions")
    if not isinstance(distinctions, dict):
        _issue(issues, "missing-work-state-distinctions", "必须区分 existing/upgrade/new/future。", relative)
    else:
        _require_substantive_fields(
            distinctions,
            location=f"{relative}#work_state_distinctions",
            fields=tuple((field, f"missing-work-state-{field}") for field in ("existing", "upgrade", "new", "future")),
            issues=issues,
        )
    for field in ("core_questions", "solution_backbone", "prohibited_misreadings", "listener_recall"):
        _require_string_list(payload, field, location=relative, issues=issues)
    for field in ("content_hierarchy", "recommended_weights", "forced_choices"):
        value = payload.get(field)
        if not isinstance(value, dict) or not value:
            _issue(issues, f"missing-{field.replace('_', '-')}", f"{field} 必须是非空对象。", relative)


def _check_source_references(value: Any, known: set[str], relative: str, issues: list[EditorialIssue]) -> None:
    if isinstance(value, dict):
        for field, child in value.items():
            if field in {"source_ids", "evidence_ids", "supporting_sources", "counter_sources"}:
                for source_id in _source_ids(child, field=field, location=relative, issues=issues):
                    if source_id not in known:
                        _issue(issues, "unknown-source", f"引用了 Source Truth Map 中不存在的来源：{source_id}。", relative)
            else:
                _check_source_references(child, known, relative, issues)
    elif isinstance(value, list):
        for child in value:
            _check_source_references(child, known, relative, issues)


def _judgments(
    payload: dict[str, Any],
    relative: str,
    known: set[str],
    issues: list[EditorialIssue],
    business_issue_codes: list[str],
) -> int:
    judgments = payload.get("judgments")
    if not isinstance(judgments, list) or not judgments:
        _issue(issues, "missing-judgments", "必须提供至少一项编辑判断。", relative)
        return 0
    for index, judgment in enumerate(judgments, start=1):
        location = f"{relative}#judgments[{index}]"
        if not isinstance(judgment, dict):
            _issue(issues, "invalid-judgment", "编辑判断必须是对象。", location)
            continue
        evidence = judgment.get("evidence")
        if evidence is None:
            _issue(issues, "missing-judgment-evidence", "编辑判断缺少 evidence。", location)
        else:
            for source_id in _source_ids(evidence, field="evidence", location=location, issues=issues):
                if source_id not in known:
                    _issue(issues, "unknown-source", f"判断引用了不存在的来源：{source_id}。", location)
        for field in ("reasoning", "impact", "action"):
            value = judgment.get(field)
            if not isinstance(value, str) or _is_placeholder(value):
                _issue(issues, f"missing-judgment-{field}", f"编辑判断缺少非占位 {field}。", location)
        issue_code = judgment.get("issue_code")
        if issue_code is not None:
            if not isinstance(issue_code, str) or issue_code not in EDITORIAL_BUSINESS_ISSUE_CODES:
                _issue(issues, "invalid-business-issue-code", f"未知的总编业务问题码：{issue_code!r}。", location)
            else:
                resolved = judgment.get("resolved", False)
                if not isinstance(resolved, bool):
                    _issue(issues, "invalid-issue-resolution", "resolved 必须是 JSON boolean。", location)
                elif not resolved:
                    business_issue_codes.append(issue_code)
                    _issue(issues, issue_code, "存在未解决的总编业务问题。", location)
    return len(judgments)


def _content_roles(payload: dict[str, Any], relative: str, known: set[str], issues: list[EditorialIssue]) -> int:
    entries = payload.get("items", payload.get("roles", payload.get("content_roles")))
    if not isinstance(entries, list) or not entries:
        _issue(issues, "missing-content-roles", "内容角色映射至少需要一项内容。", relative)
        return 0
    for index, entry in enumerate(entries, start=1):
        location = f"{relative}#items[{index}]"
        if not isinstance(entry, dict):
            _issue(issues, "invalid-content-role", "内容角色条目必须是对象。", location)
            continue
        role = entry.get("content_role", entry.get("role"))
        if not isinstance(role, str) or role.strip() not in _VALID_CONTENT_ROLES:
            _issue(issues, "invalid-content-role", f"内容角色无效：{role!r}。", location)
        content = entry.get("content")
        if not isinstance(content, str) or _is_placeholder(content):
            _issue(issues, "missing-role-content", "内容角色条目缺少非占位 content。", location)
        content_id = entry.get("content_id")
        if not isinstance(content_id, str) or _is_placeholder(content_id):
            _issue(issues, "missing-content-id", "内容角色条目缺少非占位 content_id。", location)
        deck_weight = entry.get("deck_weight")
        if not isinstance(deck_weight, (int, float)) or isinstance(deck_weight, bool) or not 0 <= deck_weight <= 100:
            _issue(issues, "invalid-deck-weight", "deck_weight 必须是 0—100 的数字。", location)
        compression_mode = entry.get("compression_mode")
        if compression_mode not in {"独立呈现", "合并呈现", "口头说明", "备份保留"}:
            _issue(issues, "invalid-compression-mode", "compression_mode 必须使用规定枚举。", location)
        _require_string_list(entry, "supports", location=location, issues=issues)
        misuse_risk = entry.get("misuse_risk")
        if not isinstance(misuse_risk, str) or _is_placeholder(misuse_risk):
            _issue(issues, "missing-misuse-risk", "内容角色条目缺少 misuse_risk。", location)
        _require_source_ids(entry, location=location, known=known, issues=issues)
    return len(entries)


def _candidates(payload: dict[str, Any], relative: str, known: set[str], issues: list[EditorialIssue]) -> int:
    candidates = payload.get("candidates")
    if not isinstance(candidates, list):
        _issue(issues, "invalid-storyline-candidates", "candidates 必须是数组。", relative)
        return 0
    valid_candidates = 0
    identifiers: set[str] = set()
    signatures: set[str] = set()
    for index, candidate in enumerate(candidates, start=1):
        location = f"{relative}#candidates[{index}]"
        if not isinstance(candidate, dict):
            _issue(issues, "invalid-storyline-candidate", "故事线候选必须是对象。", location)
            continue
        candidate_id = candidate.get("candidate_id")
        if not isinstance(candidate_id, str) or not re.fullmatch(r"CANDIDATE-[0-9A-Za-z.-]+", candidate_id):
            _issue(issues, "invalid-candidate-id", "candidate_id 必须使用 CANDIDATE-* 稳定 ID。", location)
        elif candidate_id in identifiers:
            _issue(issues, "duplicate-candidate-id", f"candidate_id 重复：{candidate_id}", location)
        else:
            identifiers.add(candidate_id)
        name = candidate.get("name")
        if not isinstance(name, str) or _is_placeholder(name):
            _issue(issues, "missing-candidate-name", "故事线候选缺少非占位 name。", location)
        rationale = candidate.get("rationale")
        if not isinstance(rationale, str) or _is_placeholder(rationale):
            _issue(issues, "missing-candidate-rationale", "故事线候选缺少非占位 rationale。", location)
        mainline = candidate.get("organization_mainline")
        if not isinstance(mainline, str) or _is_placeholder(mainline):
            _issue(issues, "missing-candidate-mainline", "故事线候选缺少 organization_mainline。", location)
        chapters = candidate.get("chapters")
        if not isinstance(chapters, list) or not chapters:
            _issue(issues, "missing-candidate-chapters", "候选必须给出非空章节结构。", location)
        else:
            for chapter_index, chapter in enumerate(chapters, start=1):
                chapter_location = f"{location}.chapters[{chapter_index}]"
                if not isinstance(chapter, dict):
                    _issue(issues, "invalid-candidate-chapter", "候选章节必须是对象。", chapter_location)
                    continue
                _require_substantive_fields(
                    chapter,
                    location=chapter_location,
                    fields=(("chapter_id", "missing-candidate-chapter-id"), ("title", "missing-candidate-chapter-title"), ("mission", "missing-candidate-chapter-mission")),
                    issues=issues,
                )
                _require_source_ids(chapter, location=chapter_location, known=known, issues=issues)
        _require_string_list(candidate, "solution_object_coverage", location=location, issues=issues)
        weights = candidate.get("content_weights")
        if not isinstance(weights, dict) or not weights or any(
            not isinstance(value, (int, float)) or isinstance(value, bool) or value < 0
            for value in weights.values()
        ):
            _issue(issues, "invalid-candidate-content-weights", "content_weights 必须是非空非负数字映射。", location)
        page_count = candidate.get("suggested_page_count")
        if not isinstance(page_count, int) or isinstance(page_count, bool) or page_count <= 0:
            _issue(issues, "invalid-candidate-page-count", "suggested_page_count 必须是正整数。", location)
        for field in ("compressed_content", "applicable_conditions", "risks"):
            _require_string_list(candidate, field, location=location, issues=issues)
        source_ids = _require_source_ids(candidate, location=location, known=known, issues=issues)
        signature = json.dumps(
            {
                "name": name,
                "mainline": mainline,
                "chapters": chapters,
                "weights": weights,
            },
            ensure_ascii=False,
            sort_keys=True,
        )
        if signature in signatures:
            _issue(issues, "duplicate-storyline-candidate", "候选结构与另一候选实质重复。", location)
        signatures.add(signature)
        if (
            isinstance(candidate_id, str)
            and isinstance(name, str)
            and not _is_placeholder(name)
            and isinstance(rationale, str)
            and not _is_placeholder(rationale)
            and bool(source_ids)
        ):
            valid_candidates += 1
    if valid_candidates < 2:
        _issue(issues, "insufficient-storyline-candidates", "至少需要两条故事线候选方案。", relative)
    return valid_candidates


def _verdict(
    payload: dict[str, Any],
    relative: str,
    issues: list[EditorialIssue],
    candidate_ids: set[str] | None = None,
) -> None:
    verdict = payload.get("verdict")
    if verdict not in _VALID_VERDICTS:
        _issue(issues, "invalid-verdict", f"verdict 必须是 {sorted(_VALID_VERDICTS)} 之一。", relative)
    elif verdict == "MERGE":
        merge_plan = payload.get("merge_plan")
        if not isinstance(merge_plan, dict):
            _issue(issues, "missing-merge-plan", "MERGE 必须给出机器可读 merge_plan。", relative)
        else:
            ids = merge_plan.get("candidate_ids")
            merged_id = merge_plan.get("merged_candidate_id")
            if not isinstance(ids, list) or len(set(ids)) < 2:
                _issue(issues, "invalid-merge-candidates", "merge_plan.candidate_ids 至少包含两个不同候选。", relative)
            if not isinstance(merged_id, str) or _is_placeholder(merged_id):
                _issue(issues, "missing-merged-candidate", "merge_plan 缺少 merged_candidate_id。", relative)
            if merge_plan.get("requires_re_review") is not True:
                _issue(issues, "missing-merge-rereview", "MERGE 必须声明 requires_re_review=true。", relative)
        _issue(issues, "editorial-verdict-not-approved", "verdict=MERGE 必须完成重组并重新裁决为 ACCEPT。", relative)
    elif verdict == "REJECT":
        _issue(issues, "editorial-verdict-not-approved", f"verdict={verdict} 尚未形成可推进的最终批准。", relative)
    elif candidate_ids is not None:
        selected = payload.get("selected_candidate_id")
        if not isinstance(selected, str) or selected not in candidate_ids:
            _issue(issues, "invalid-selected-candidate", "ACCEPT 必须引用已审计候选的 candidate_id。", relative)


def _review_ids(
    payload: dict[str, Any],
    field: str,
    id_field: str,
    *,
    location: str,
    issues: list[EditorialIssue],
) -> set[str]:
    reviews = payload.get(field)
    if not isinstance(reviews, list) or not reviews:
        _issue(issues, f"missing-{field.replace('_', '-')}", f"{field} 必须是非空审稿数组。", location)
        return set()
    ids: set[str] = set()
    for index, review in enumerate(reviews, start=1):
        review_location = f"{location}#{field}[{index}]"
        if not isinstance(review, dict):
            _issue(issues, "invalid-outline-review-item", "审稿条目必须是对象。", review_location)
            continue
        item_id = review.get(id_field)
        if not isinstance(item_id, str) or _is_placeholder(item_id):
            _issue(issues, f"missing-{id_field.replace('_', '-')}", f"缺少稳定 {id_field}。", review_location)
            continue
        if item_id in ids:
            _issue(issues, "duplicate-review-id", f"重复审稿 ID：{item_id}", review_location)
        ids.add(item_id)
        for field_name in ("reasoning", "impact", "action"):
            value = review.get(field_name)
            if not isinstance(value, str) or _is_placeholder(value):
                _issue(issues, f"missing-review-{field_name}", f"审稿条目缺少 {field_name}。", review_location)
    return ids


def _load_contract_ids(project: Path, relative: str, collection: str, id_field: str) -> set[str]:
    path = project / relative
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return set()
    items = payload.get(collection, []) if isinstance(payload, dict) else []
    return {
        item[id_field]
        for item in items
        if isinstance(item, dict) and isinstance(item.get(id_field), str)
    }


def _outline_details(
    project: Path,
    payload: dict[str, Any],
    relative: str,
    issues: list[EditorialIssue],
) -> None:
    _validate_registered_bindings(project, payload, relative, issues)
    expected_chapters = _load_contract_ids(project, "contracts/chapter-contracts.json", "chapters", "chapter_id")
    expected_pages = _load_contract_ids(project, "contracts/page-contracts.json", "pages", "page_id")
    reviewed_chapters = _review_ids(payload, "chapter_reviews", "chapter_id", location=relative, issues=issues)
    reviewed_pages = _review_ids(payload, "page_reviews", "page_id", location=relative, issues=issues)
    reviewed_titles = _review_ids(payload, "title_reviews", "page_id", location=relative, issues=issues)
    for code, missing in (
        ("missing-chapter-review-coverage", expected_chapters - reviewed_chapters),
        ("missing-page-review-coverage", expected_pages - reviewed_pages),
        ("missing-title-review-coverage", expected_pages - reviewed_titles),
    ):
        if missing:
            _issue(issues, code, "未覆盖稳定 ID：" + "、".join(sorted(missing)), relative)
    _audit_stale_review_language(project, payload, relative, issues)


_QUOTED_SPAN_RE = re.compile(r"[“\"「『]([^”\"」』]{2,})[”\"」』]")
_TITLE_REFERENCE_WINDOW = 12


def _contract_titles(project: Path, relative: str, collection: str, id_field: str) -> dict[str, str]:
    path = project / relative
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    items = payload.get(collection, []) if isinstance(payload, dict) else []
    titles: dict[str, str] = {}
    for item in items:
        if not isinstance(item, dict):
            continue
        item_id = item.get(id_field)
        title = item.get("title")
        if isinstance(item_id, str) and isinstance(title, str):
            titles[item_id] = title
    return titles


def _audit_stale_review_language(
    project: Path,
    payload: dict[str, Any],
    relative: str,
    issues: list[EditorialIssue],
) -> None:
    """Flag review reasoning that quotes a title claim absent from the current contract title.

    Generalizes a past incident where reasoning kept citing a retired title framing
    after the title itself was rewritten; instead of matching that one incident's
    wording, this checks any reasoning that explicitly quotes what the title
    says (near "标题"/"题目") against the title actually on record.
    """
    page_titles = _contract_titles(project, "contracts/page-contracts.json", "pages", "page_id")
    chapter_titles = _contract_titles(
        project, "contracts/chapter-contracts.json", "chapters", "chapter_id"
    )
    for collection, id_field, titles in (
        ("chapter_reviews", "chapter_id", chapter_titles),
        ("title_reviews", "page_id", page_titles),
    ):
        reviews = payload.get(collection)
        if not isinstance(reviews, list):
            continue
        for index, review in enumerate(reviews, start=1):
            if not isinstance(review, dict):
                continue
            item_id = review.get(id_field)
            reasoning = review.get("reasoning")
            if not isinstance(item_id, str) or not isinstance(reasoning, str):
                continue
            title = titles.get(item_id, "")
            for match in _QUOTED_SPAN_RE.finditer(reasoning):
                quoted = match.group(1)
                context = reasoning[max(0, match.start() - _TITLE_REFERENCE_WINDOW) : match.start()]
                if "标题" not in context and "题目" not in context:
                    continue
                if quoted in title:
                    continue
                _issue(
                    issues,
                    "stale-review-language",
                    f"{collection}[{index}]（{item_id}）审稿理由声称标题含“{quoted}”，"
                    f"但当前合同标题为“{title or '（空）'}”，未包含该表述；请核实是否引用了旧版本内容。",
                    relative,
                )


def _red_team_review_details(
    project: Path,
    payload: dict[str, Any],
    relative: str,
    known: set[str],
    issues: list[EditorialIssue],
    business_issue_codes: list[str],
) -> set[str]:
    _validate_registered_bindings(project, payload, relative, issues)
    challenges = payload.get("challenges")
    if not isinstance(challenges, list) or not challenges:
        _issue(issues, "missing-red-team-challenges", "反方审稿必须提出至少一项可回应挑战。", relative)
        return set()
    challenge_ids: set[str] = set()
    for index, challenge in enumerate(challenges, start=1):
        location = f"{relative}#challenges[{index}]"
        if not isinstance(challenge, dict):
            _issue(issues, "invalid-red-team-challenge", "反方挑战必须是对象。", location)
            continue
        challenge_id = challenge.get("challenge_id")
        if not isinstance(challenge_id, str) or not re.fullmatch(r"RT-[0-9A-Za-z.-]+", challenge_id):
            _issue(issues, "invalid-challenge-id", "challenge_id 必须使用 RT-* 稳定 ID。", location)
        elif challenge_id in challenge_ids:
            _issue(issues, "duplicate-challenge-id", f"challenge_id 重复：{challenge_id}", location)
        else:
            challenge_ids.add(challenge_id)
        evidence = challenge.get("evidence")
        for source_id in _source_ids(evidence, field="evidence", location=location, issues=issues):
            if source_id not in known:
                _issue(issues, "unknown-source", f"反方挑战引用不存在来源：{source_id}。", location)
        for field in ("reasoning", "impact", "action"):
            value = challenge.get(field)
            if not isinstance(value, str) or _is_placeholder(value):
                _issue(issues, f"missing-challenge-{field}", f"反方挑战缺少 {field}。", location)
        issue_code = challenge.get("issue_code")
        if issue_code is not None:
            if not isinstance(issue_code, str) or issue_code not in EDITORIAL_BUSINESS_ISSUE_CODES:
                _issue(issues, "invalid-business-issue-code", f"未知的总编业务问题码：{issue_code!r}。", location)
            elif challenge.get("resolved") is not True:
                business_issue_codes.append(issue_code)
                _issue(issues, issue_code, "存在未解决的反方业务问题。", location)
    return challenge_ids


def _red_team_response_details(
    project: Path,
    payload: dict[str, Any],
    relative: str,
    challenge_ids: set[str],
    known: set[str],
    issues: list[EditorialIssue],
    business_issue_codes: list[str],
) -> None:
    _validate_registered_bindings(project, payload, relative, issues)
    responses = payload.get("responses")
    if not isinstance(responses, list) or not responses:
        _issue(issues, "missing-red-team-responses", "总编必须逐项回应反方挑战。", relative)
        return
    responded: set[str] = set()
    for index, response in enumerate(responses, start=1):
        location = f"{relative}#responses[{index}]"
        if not isinstance(response, dict):
            _issue(issues, "invalid-red-team-response", "总编回应必须是对象。", location)
            continue
        challenge_id = response.get("challenge_id")
        if not isinstance(challenge_id, str) or challenge_id not in challenge_ids:
            _issue(issues, "unknown-challenge-response", f"回应未绑定已知 challenge_id：{challenge_id!r}", location)
        else:
            responded.add(challenge_id)
        for field in ("response", "action"):
            value = response.get(field)
            if not isinstance(value, str) or _is_placeholder(value):
                _issue(issues, f"missing-response-{field}", f"总编回应缺少 {field}。", location)
        evidence = response.get("evidence")
        for source_id in _source_ids(evidence, field="evidence", location=location, issues=issues):
            if source_id not in known:
                _issue(issues, "unknown-source", f"总编回应引用不存在来源：{source_id}。", location)
        if response.get("resolved") is not True:
            _issue(issues, "unresolved-red-team-challenge", "反方挑战尚未解决。", location)
            issue_code = response.get("issue_code")
            if isinstance(issue_code, str) and issue_code in EDITORIAL_BUSINESS_ISSUE_CODES:
                business_issue_codes.append(issue_code)
                _issue(issues, issue_code, "存在未解决的总编业务问题。", location)
            elif issue_code is not None:
                _issue(issues, "invalid-business-issue-code", f"未知的总编业务问题码：{issue_code!r}。", location)
    missing = challenge_ids - responded
    if missing:
        _issue(issues, "missing-red-team-response-coverage", "未回应挑战：" + "、".join(sorted(missing)), relative)
    _verdict(payload, relative, issues)


def audit_editorial(project: str | Path, phase: EditorialPhase) -> EditorialAudit:
    if phase not in _PHASES:
        raise ValueError(f"unknown editorial phase: {phase}")
    project_path = Path(project)
    issues: list[EditorialIssue] = []
    known_sources = _known_source_ids(project_path, issues)
    payloads: dict[str, dict[str, Any]] = {}
    for relative in (*_BASE_FILES, *_PHASE_FILES[phase]):
        payload = _load_json(project_path, relative, issues)
        if payload is None:
            continue
        payloads[relative] = payload
        _check_placeholders(payload, relative, issues)
        _check_source_references(payload, known_sources, relative, issues)
        expected_schema = _EXPECTED_SCHEMAS[relative]
        schema = payload.get("schema")
        if schema != expected_schema:
            _issue(
                issues,
                "schema-mismatch",
                f"schema 应为 {expected_schema}，实际为 {schema!r}。",
                relative,
            )

    for relative in ("contracts/semantic-core.json", "contracts/solution-model.json"):
        payload = payloads.get(relative)
        if payload is not None:
            _require_source_ids(payload, location=relative, known=known_sources, issues=issues)
            _require_substantive_fields(
                payload,
                location=relative,
                fields=_SEMANTIC_REQUIRED_TEXT[relative],
                issues=issues,
            )

    _semantic_contract_details(payloads, project_path, known_sources, issues)

    role_map = payloads.get("contracts/content-role-map.json")
    role_count = _content_roles(role_map, "contracts/content-role-map.json", known_sources, issues) if role_map else 0

    judgment_count = 0
    business_issue_codes: list[str] = []
    for relative, payload in payloads.items():
        if relative in {
            "analysis/editorial/01-independent-judgment.json",
            "analysis/editorial/02-storyline-verdict.json",
            "analysis/editorial/03-outline-review.json",
        }:
            judgment_count += _judgments(
                payload,
                relative,
                known_sources,
                issues,
                business_issue_codes,
            )

    independent_path = "analysis/editorial/01-independent-judgment.json"
    independent_payload = payloads.get(independent_path)
    if independent_payload is not None:
        _independent_details(independent_payload, project_path, independent_path, issues)

    candidate_count = 0
    candidate_path = "analysis/editorial/storyline-candidates.json"
    candidate_ids: set[str] = set()
    if candidate_path in _PHASE_FILES[phase]:
        candidate_payload = payloads.get(candidate_path)
        if candidate_payload:
            _validate_registered_bindings(
                project_path,
                candidate_payload,
                candidate_path,
                issues,
            )
            candidate_count = _candidates(candidate_payload, candidate_path, known_sources, issues)
            raw_candidates = candidate_payload.get("candidates", [])
            candidate_ids = {
                item["candidate_id"]
                for item in raw_candidates
                if isinstance(item, dict) and isinstance(item.get("candidate_id"), str)
            }

    verdict_path = "analysis/editorial/02-storyline-verdict.json"
    verdict_payload = payloads.get(verdict_path)
    if verdict_payload is not None:
        _validate_registered_bindings(
            project_path,
            verdict_payload,
            verdict_path,
            issues,
        )
        framework_fit = verdict_payload.get("framework_fit_rationale")
        if not isinstance(framework_fit, str) or _is_placeholder(framework_fit):
            _issue(issues, "missing-framework-fit-rationale", "结构裁决必须说明框架适配、变形或放弃依据。", verdict_path)
        _verdict(verdict_payload, verdict_path, issues, candidate_ids)

    outline_path = "analysis/editorial/03-outline-review.json"
    outline_payload = payloads.get(outline_path)
    if outline_payload is not None:
        _outline_details(project_path, outline_payload, outline_path, issues)
        _verdict(outline_payload, outline_path, issues)

    red_team_path = "analysis/editorial/04-red-team-review.json"
    challenge_ids: set[str] = set()
    red_team_payload = payloads.get(red_team_path)
    if red_team_payload is not None:
        challenge_ids = _red_team_review_details(
            project_path,
            red_team_payload,
            red_team_path,
            known_sources,
            issues,
            business_issue_codes,
        )

    response_path = "analysis/editorial/05-red-team-response.json"
    response_payload = payloads.get(response_path)
    if response_payload is not None:
        _red_team_response_details(
            project_path,
            response_payload,
            response_path,
            challenge_ids,
            known_sources,
            issues,
            business_issue_codes,
        )

    errors = sum(issue.severity == "error" for issue in issues)
    return EditorialAudit(
        phase=phase,
        passed=errors == 0,
        issues=tuple(issues),
        metrics={
            "known_source_ids": len(known_sources),
            "validated_files": len(payloads),
            "content_roles": role_count,
            "judgments": judgment_count,
            "storyline_candidates": candidate_count,
            "bound_targets": sum(
                len(payload.get("provenance", {}).get("targets", {}))
                for payload in payloads.values()
                if isinstance(payload.get("provenance"), dict)
                and isinstance(payload.get("provenance", {}).get("targets"), dict)
            ),
            "business_issue_codes": sorted(set(business_issue_codes)),
            "error_count": errors,
        },
    )


def _render_audit(report: EditorialAudit) -> str:
    lines = [
        "# 总编审计",
        "",
        f"- 阶段：{report.phase}",
        f"- 状态：{'PASS' if report.passed else 'FAIL'}",
        f"- 问题数：{report.metrics['error_count']}",
        "",
    ]
    if report.issues:
        lines.extend(["## 问题", ""])
        lines.extend(f"- `{issue.code}` `{issue.location}`：{issue.message}" for issue in report.issues)
    else:
        lines.append("所有必需合同、判断依据和阶段裁决均通过确定性校验。")
    return "\n".join(lines) + "\n"


def _editorial_rework_limit(project: Path) -> int:
    path = project / "project.json"
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return 0
    value = payload.get("editorial_auto_rework_limit", 0) if isinstance(payload, dict) else 0
    if not isinstance(value, int) or isinstance(value, bool) or value < 0:
        return 0
    return value


def _rework_targets(phase: EditorialPhase) -> list[str]:
    mapping: dict[EditorialPhase, list[str]] = {
        "semantic-planning": list(_BASE_FILES),
        "independent": ["analysis/editorial/01-independent-judgment.json"],
        "storyline-candidates": ["analysis/editorial/storyline-candidates.json"],
        "storyline": ["decision/01-decision.md", "analysis/editorial/02-storyline-verdict.json"],
        "outline": ["outline/02-outline.md", "analysis/editorial/03-outline-review.json"],
        "red-team-review": ["analysis/editorial/04-red-team-review.json"],
        "red-team": ["analysis/editorial/05-red-team-response.json"],
    }
    return mapping[phase]


def _rework_fingerprint(project: Path, report: EditorialAudit) -> str:
    material: list[tuple[str, str]] = []
    for relative in (*_BASE_FILES, *_PHASE_FILES[report.phase]):
        path = project / relative
        material.append((relative, _file_sha256(path) if path.is_file() else "MISSING"))
    payload = {
        "phase": report.phase,
        "issues": [(item.code, item.location) for item in report.issues],
        "material": material,
    }
    encoded = json.dumps(payload, ensure_ascii=False, sort_keys=True).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _persist_rework_state(project: Path, report: EditorialAudit) -> None:
    state_path = project / "analysis/editorial/rework-state.json"
    state_path.parent.mkdir(parents=True, exist_ok=True)
    previous: dict[str, Any] = {}
    if state_path.is_file():
        try:
            loaded = json.loads(state_path.read_text(encoding="utf-8"))
            if isinstance(loaded, dict):
                previous = loaded
        except (OSError, json.JSONDecodeError):
            previous = {}
    if report.passed:
        if previous.get("source_phase") == report.phase:
            previous.update(
                {
                    "status": "RESOLVED",
                    "issue_codes": [],
                    "unresolved_judgment_ids": [],
                    "last_passed_audit": f"analysis/editorial/99-{report.phase}-audit.json",
                }
            )
            state_path.write_text(json.dumps(previous, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        return

    fingerprint = _rework_fingerprint(project, report)
    same_failure = (
        previous.get("source_phase") == report.phase
        and previous.get("failure_fingerprint") == fingerprint
    )
    previous_count = previous.get("attempt_count", 0)
    if not isinstance(previous_count, int) or isinstance(previous_count, bool):
        previous_count = 0
    attempt_count = previous_count if same_failure else previous_count + 1
    limit = _editorial_rework_limit(project)
    status = "USER_DECISION_REQUIRED" if attempt_count > limit else "MANUAL_REWORK_REQUIRED"
    issue_codes = sorted({item.code for item in report.issues})
    unresolved = sorted(
        {
            match.group(1)
            for item in report.issues
            for match in [re.search(r"(?:judgments|challenges|responses)\[(\d+)\]", item.location)]
            if match
        }
    )
    payload = {
        "schema": "ppt-script.editorial-rework-state.v1",
        "status": status,
        "source_phase": report.phase,
        "attempt_count": attempt_count,
        "limit": limit,
        "automation_available": False,
        "failure_fingerprint": fingerprint,
        "issue_codes": issue_codes,
        "unresolved_judgment_ids": unresolved,
        "target_files": _rework_targets(report.phase),
        "protocol": "仓库未配置模型执行器；本状态只记录人工/外部执行器返工轮次，不声明已自动生成内容。",
        "user_options": [
            "按问题码和目标文件人工返工后重新运行 editorial-check",
            "提供补充证据或修改范围边界后重新审计",
            "达到上限时由用户裁决保留、重组或终止当前方案",
        ],
    }
    state_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def write_editorial_audit(project: str | Path, phase: EditorialPhase) -> EditorialAudit:
    project_path = Path(project)
    report = audit_editorial(project_path, phase)
    output_dir = project_path / "analysis/editorial"
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / f"99-{phase}-audit.json").write_text(
        json.dumps(report.to_dict(), ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    (output_dir / f"99-{phase}-audit.md").write_text(_render_audit(report), encoding="utf-8")
    _persist_rework_state(project_path, report)
    return report
