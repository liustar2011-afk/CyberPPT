from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from .source_truth import parse_source_truth_map
from .version import get_version

_SCHEMA = "ppt-script.evidence-graph.v1"
_CLAIM_ID_RE = re.compile(r"^C\d{3,4}$")
_RELATION_ID_RE = re.compile(r"^R\d{3,4}$")
_PAGE_ID_RE = re.compile(r"^P\d{2,4}$")
_VALID_CONFIDENCE = {
    "confirmed",
    "strong-inference",
    "weak-inference",
    "unverified",
    "conflicted",
}
_VALID_RELATIONS = {
    "supports",
    "causes",
    "constrains",
    "contradicts",
    "responds-to",
    "enables",
    "depends-on",
    "leads-to",
}


@dataclass(frozen=True, slots=True)
class EvidenceGraphIssue:
    code: str
    message: str
    location: str = "contracts/evidence-graph.json"
    severity: str = "error"


@dataclass(frozen=True, slots=True)
class EvidenceGraphReport:
    passed: bool
    enabled: bool
    issues: tuple[EvidenceGraphIssue, ...]
    counts: dict[str, int]

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema": "ppt-script.evidence-graph-audit.v1",
            "passed": self.passed,
            "enabled": self.enabled,
            "counts": self.counts,
            "issues": [asdict(issue) for issue in self.issues],
        }


@dataclass(frozen=True, slots=True)
class ClaimTrace:
    claim_id: str
    statement: str
    confidence: str
    source_ids: tuple[str, ...]
    counter_source_ids: tuple[str, ...]
    related_claim_ids: tuple[str, ...]
    page_ids: tuple[str, ...]
    conditions: tuple[str, ...]
    decision_relevance: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def empty_evidence_graph(version: str | None = None) -> dict[str, Any]:
    return {
        "schema": _SCHEMA,
        "skill_version": version or get_version(),
        "claims": [],
        "relations": [],
        "page_links": [],
    }


def create_evidence_graph_scaffold(project: Path, version: str | None = None) -> Path:
    path = Path(project) / "contracts/evidence-graph.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    if not path.exists():
        path.write_text(
            json.dumps(empty_evidence_graph(version), ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
    return path


def _load_graph(project: Path, issues: list[EvidenceGraphIssue]) -> dict[str, Any] | None:
    path = Path(project) / "contracts/evidence-graph.json"
    if not path.is_file():
        issues.append(EvidenceGraphIssue("missing-file", "缺少 contracts/evidence-graph.json。"))
        return None
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        issues.append(EvidenceGraphIssue("invalid-json", f"证据图谱不是有效 JSON：{exc}"))
        return None
    if not isinstance(payload, dict):
        issues.append(EvidenceGraphIssue("invalid-root", "证据图谱根节点必须是对象。"))
        return None
    if payload.get("schema") != _SCHEMA:
        issues.append(EvidenceGraphIssue("schema-mismatch", f"schema 必须为 {_SCHEMA}。"))
    return payload


def _known_source_ids(project: Path) -> set[str]:
    known: set[str] = set()
    markdown = Path(project) / "analysis/01-source-truth-map.md"
    if markdown.is_file():
        truth = parse_source_truth_map(markdown.read_text(encoding="utf-8", errors="ignore"))
        known.update(item.source_id for item in truth.items)
    contract = Path(project) / "contracts/source-truth.json"
    if contract.is_file():
        try:
            payload = json.loads(contract.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            payload = {}
        sources = payload.get("sources", []) if isinstance(payload, dict) else []
        if isinstance(sources, list):
            for item in sources:
                if isinstance(item, dict) and isinstance(item.get("source_id"), str):
                    known.add(item["source_id"])
    return known


def _string_list(
    value: Any,
    *,
    field: str,
    item_id: str,
    issues: list[EvidenceGraphIssue],
) -> list[str]:
    if not isinstance(value, list) or any(not isinstance(item, str) for item in value):
        issues.append(EvidenceGraphIssue("invalid-list", f"{item_id} 的 {field} 必须是字符串数组。"))
        return []
    return [item.strip() for item in value if item.strip()]


def validate_evidence_graph(project: str | Path) -> EvidenceGraphReport:
    project_path = Path(project)
    issues: list[EvidenceGraphIssue] = []
    payload = _load_graph(project_path, issues)
    if payload is None:
        return EvidenceGraphReport(False, False, tuple(issues), {"claims": 0, "relations": 0, "page_links": 0})

    claims = payload.get("claims", [])
    relations = payload.get("relations", [])
    page_links = payload.get("page_links", [])
    if not isinstance(claims, list):
        issues.append(EvidenceGraphIssue("invalid-claims", "claims 必须是数组。"))
        claims = []
    if not isinstance(relations, list):
        issues.append(EvidenceGraphIssue("invalid-relations", "relations 必须是数组。"))
        relations = []
    if not isinstance(page_links, list):
        issues.append(EvidenceGraphIssue("invalid-page-links", "page_links 必须是数组。"))
        page_links = []

    known_sources = _known_source_ids(project_path)
    claim_ids: set[str] = set()
    for index, claim in enumerate(claims, start=1):
        if not isinstance(claim, dict):
            issues.append(EvidenceGraphIssue("invalid-claim", f"第 {index} 个 claim 必须是对象。"))
            continue
        claim_id = claim.get("claim_id")
        if not isinstance(claim_id, str) or not _CLAIM_ID_RE.fullmatch(claim_id):
            issues.append(EvidenceGraphIssue("invalid-claim-id", f"第 {index} 个 claim_id 无效：{claim_id!r}。"))
            continue
        if claim_id in claim_ids:
            issues.append(EvidenceGraphIssue("duplicate-claim-id", f"claim_id 重复：{claim_id}。"))
        claim_ids.add(claim_id)
        for field in ("statement", "claim_type", "decision_relevance"):
            value = claim.get(field)
            if not isinstance(value, str) or not value.strip():
                issues.append(EvidenceGraphIssue("missing-claim-field", f"{claim_id} 缺少非空字段 {field}。"))
        confidence = claim.get("confidence")
        if confidence not in _VALID_CONFIDENCE:
            issues.append(EvidenceGraphIssue("invalid-confidence", f"{claim_id} 的 confidence 无效：{confidence!r}。"))
        supporting = _string_list(claim.get("supporting_sources", []), field="supporting_sources", item_id=claim_id, issues=issues)
        counter = _string_list(claim.get("counter_sources", []), field="counter_sources", item_id=claim_id, issues=issues)
        conditions = _string_list(claim.get("conditions", []), field="conditions", item_id=claim_id, issues=issues)
        for source_id in [*supporting, *counter]:
            if source_id not in known_sources:
                issues.append(EvidenceGraphIssue("unknown-source", f"{claim_id} 引用了不存在的来源 {source_id}。"))
        if confidence in {"confirmed", "strong-inference", "weak-inference", "conflicted"} and not supporting:
            issues.append(EvidenceGraphIssue("missing-support", f"{claim_id} 缺少 supporting_sources。"))
        if confidence == "conflicted" and not counter and not conditions:
            issues.append(EvidenceGraphIssue("unexplained-conflict", f"{claim_id} 标记为 conflicted，但没有反证或冲突条件。"))

    relation_ids: set[str] = set()
    for index, relation in enumerate(relations, start=1):
        if not isinstance(relation, dict):
            issues.append(EvidenceGraphIssue("invalid-relation", f"第 {index} 个 relation 必须是对象。"))
            continue
        relation_id = relation.get("relation_id")
        if not isinstance(relation_id, str) or not _RELATION_ID_RE.fullmatch(relation_id):
            issues.append(EvidenceGraphIssue("invalid-relation-id", f"第 {index} 个 relation_id 无效：{relation_id!r}。"))
            continue
        if relation_id in relation_ids:
            issues.append(EvidenceGraphIssue("duplicate-relation-id", f"relation_id 重复：{relation_id}。"))
        relation_ids.add(relation_id)
        from_claim = relation.get("from_claim")
        to_claim = relation.get("to_claim")
        if from_claim not in claim_ids:
            issues.append(EvidenceGraphIssue("unknown-claim", f"{relation_id} 的 from_claim 不存在：{from_claim!r}。"))
        if to_claim not in claim_ids:
            issues.append(EvidenceGraphIssue("unknown-claim", f"{relation_id} 的 to_claim 不存在：{to_claim!r}。"))
        relation_type = relation.get("relation_type")
        if relation_type not in _VALID_RELATIONS:
            issues.append(EvidenceGraphIssue("invalid-relation-type", f"{relation_id} 的 relation_type 无效：{relation_type!r}。"))
        refs = _string_list(relation.get("evidence_sources", []), field="evidence_sources", item_id=relation_id, issues=issues)
        for source_id in refs:
            if source_id not in known_sources:
                issues.append(EvidenceGraphIssue("unknown-source", f"{relation_id} 引用了不存在的来源 {source_id}。"))

    seen_pages: set[str] = set()
    for index, link in enumerate(page_links, start=1):
        if not isinstance(link, dict):
            issues.append(EvidenceGraphIssue("invalid-page-link", f"第 {index} 个 page_link 必须是对象。"))
            continue
        page_id = link.get("page_id")
        if not isinstance(page_id, str) or not _PAGE_ID_RE.fullmatch(page_id):
            issues.append(EvidenceGraphIssue("invalid-page-id", f"第 {index} 个 page_id 无效：{page_id!r}。"))
            continue
        if page_id in seen_pages:
            issues.append(EvidenceGraphIssue("duplicate-page-link", f"page_id 重复：{page_id}。"))
        seen_pages.add(page_id)
        refs = _string_list(link.get("claim_ids", []), field="claim_ids", item_id=page_id, issues=issues)
        for claim_id in refs:
            if claim_id not in claim_ids:
                issues.append(EvidenceGraphIssue("unknown-claim", f"{page_id} 引用了不存在的主张 {claim_id}。"))

    return EvidenceGraphReport(
        passed=not any(issue.severity == "error" for issue in issues),
        enabled=True,
        issues=tuple(issues),
        counts={"claims": len(claims), "relations": len(relations), "page_links": len(page_links)},
    )


def render_evidence_graph_report(report: EvidenceGraphReport) -> str:
    status = "PASS" if report.passed else "FAIL"
    lines = [
        "# 证据图谱检查",
        "",
        f"- 状态：**{status}**",
        f"- 主张：{report.counts.get('claims', 0)}",
        f"- 关系：{report.counts.get('relations', 0)}",
        f"- 页面关联：{report.counts.get('page_links', 0)}",
        "",
    ]
    if report.issues:
        lines.extend(["## 问题", ""])
        lines.extend(f"- `{issue.code}`：{issue.message}" for issue in report.issues)
    else:
        lines.append("主张、来源、关系、置信度和页面关联均可追溯。")
    return "\n".join(lines) + "\n"


def write_evidence_graph_report(project: str | Path) -> EvidenceGraphReport:
    project_path = Path(project)
    report = validate_evidence_graph(project_path)
    review = project_path / "review"
    review.mkdir(parents=True, exist_ok=True)
    (review / "10-evidence-graph-audit.json").write_text(
        json.dumps(report.to_dict(), ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    (review / "10-evidence-graph-audit.md").write_text(
        render_evidence_graph_report(report),
        encoding="utf-8",
    )
    return report


def trace_claim(project: str | Path, claim_id: str) -> ClaimTrace:
    project_path = Path(project)
    issues: list[EvidenceGraphIssue] = []
    payload = _load_graph(project_path, issues)
    if payload is None or issues:
        raise ValueError("证据图谱无效，无法追溯主张。")
    claims = payload.get("claims", [])
    claim = next((item for item in claims if isinstance(item, dict) and item.get("claim_id") == claim_id), None)
    if claim is None:
        raise KeyError(f"unknown claim_id: {claim_id}")
    related: set[str] = set()
    for relation in payload.get("relations", []):
        if not isinstance(relation, dict):
            continue
        if relation.get("from_claim") == claim_id and isinstance(relation.get("to_claim"), str):
            related.add(relation["to_claim"])
        if relation.get("to_claim") == claim_id and isinstance(relation.get("from_claim"), str):
            related.add(relation["from_claim"])
    pages = tuple(
        link["page_id"]
        for link in payload.get("page_links", [])
        if isinstance(link, dict)
        and isinstance(link.get("page_id"), str)
        and claim_id in link.get("claim_ids", [])
    )
    return ClaimTrace(
        claim_id=claim_id,
        statement=str(claim.get("statement", "")),
        confidence=str(claim.get("confidence", "")),
        source_ids=tuple(str(value) for value in claim.get("supporting_sources", [])),
        counter_source_ids=tuple(str(value) for value in claim.get("counter_sources", [])),
        related_claim_ids=tuple(sorted(related)),
        page_ids=pages,
        conditions=tuple(str(value) for value in claim.get("conditions", [])),
        decision_relevance=str(claim.get("decision_relevance", "")),
    )


def render_claim_trace(trace: ClaimTrace) -> str:
    return "\n".join(
        [
            f"# 主张追溯：{trace.claim_id}",
            "",
            f"- 主张：{trace.statement}",
            f"- 置信度：{trace.confidence}",
            f"- 支撑来源：{', '.join(trace.source_ids) or '无'}",
            f"- 反向来源：{', '.join(trace.counter_source_ids) or '无'}",
            f"- 相关主张：{', '.join(trace.related_claim_ids) or '无'}",
            f"- 关联页面：{', '.join(trace.page_ids) or '无'}",
            f"- 适用条件：{'；'.join(trace.conditions) or '无'}",
            f"- 决策相关性：{trace.decision_relevance}",
            "",
        ]
    )
