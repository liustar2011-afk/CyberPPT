from __future__ import annotations

import json
import re
from difflib import SequenceMatcher
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any


REQUIRED_SECTIONS: dict[str, tuple[str, ...]] = {
    "business_subject": ("全文业务主语",),
    "business_objects": ("核心业务对象",),
    "scope": ("空间、时间与服务范围", "空间时间与服务范围"),
    "decision": ("材料意图与决策动作",),
    "foundation_gap": ("现有基础与能力缺口",),
    "goal_support": ("业务目标与支撑手段",),
    "term_table": ("核心概念语义表",),
    "evidence": ("跨章节证据链",),
    "state_boundary": ("状态、主体与边界",),
    "unresolved": ("待核事项与禁止推断",),
}
PLACEHOLDERS = ("待生成", "待分析", "待补充", "TODO", "TBD", "待填写")
ABSTRACT_TERMS = ("平台", "能力", "体系", "工程", "机制", "场景", "模型", "数据", "服务", "建设")
GENERIC_SUBJECT_TERMS = ("本材料", "面向", "行业级", "公共", "工作", "中电联", "形成", "开展", "完善")
BUSINESS_ACTIONS = ("分析", "预测", "研判", "评估", "预警", "决策", "生产", "运营", "治理", "管理")
DECISION_ACTIONS = ("报告", "请示", "审定", "决策", "协调", "部署", "评估", "验收")


@dataclass(frozen=True)
class SemanticIssue:
    code: str
    message: str
    severity: str = "error"
    location: str = "analysis/00-semantic-understanding.md"


@dataclass(frozen=True)
class SemanticAudit:
    passed: bool
    issues: tuple[SemanticIssue, ...]
    metrics: dict[str, Any]
    business_subject: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema": "ppt-script.semantic-audit.v1",
            "passed": self.passed,
            "metrics": self.metrics,
            "business_subject": self.business_subject,
            "issues": [asdict(issue) for issue in self.issues],
        }


@dataclass(frozen=True)
class SemanticConcept:
    short_term: str
    full_meaning: str
    context: str
    forbidden_reading: str
    required_keywords: tuple[str, ...]


@dataclass(frozen=True)
class SemanticContract:
    business_subject: str
    business_keywords: tuple[str, ...]
    concepts: tuple[SemanticConcept, ...]


def heading_sections(text: str) -> dict[str, str]:
    matches = list(re.finditer(r"(?m)^#{2,4}\s+(.+?)\s*$", text))
    sections: dict[str, str] = {}
    for index, match in enumerate(matches):
        end = matches[index + 1].start() if index + 1 < len(matches) else len(text)
        sections[match.group(1).strip()] = text[match.end():end].strip()
    return sections


def _section(sections: dict[str, str], aliases: tuple[str, ...]) -> str:
    for title, body in sections.items():
        if any(alias in title for alias in aliases):
            return body
    return ""


def _substantive(body: str, minimum: int = 18) -> bool:
    compact = re.sub(r"\s+", "", body)
    return len(compact) >= minimum and not any(term.lower() in body.lower() for term in PLACEHOLDERS)


def _specific_subject_text(subject: str) -> str:
    result = subject
    for term in (*ABSTRACT_TERMS, *GENERIC_SUBJECT_TERMS):
        result = result.replace(term, "")
    return re.sub(r"[^\w\u4e00-\u9fff]+", "", result)


def _normalized(text: str) -> str:
    return re.sub(r"[^\w\u4e00-\u9fff]+", "", text)


def _added_phrases(short_term: str, full_meaning: str) -> tuple[str, ...]:
    short = _normalized(short_term)
    full = _normalized(full_meaning)
    phrases: list[str] = []
    for tag, _i1, _i2, j1, j2 in SequenceMatcher(None, short, full).get_opcodes():
        if tag not in {"insert", "replace"}:
            continue
        phrase = full[j1:j2]
        if len(phrase) >= 2 and phrase not in ABSTRACT_TERMS and phrase not in GENERIC_SUBJECT_TERMS:
            phrases.append(phrase)
    return tuple(dict.fromkeys(phrases))


def parse_semantic_contract(text: str) -> SemanticContract:
    sections = heading_sections(text)
    subject = _section(sections, REQUIRED_SECTIONS["business_subject"])
    subject_specific = _specific_subject_text(subject)
    subject_keywords = tuple(
        dict.fromkeys(
            subject_specific[index:index + size]
            for size in (4, 3, 2)
            for index in range(max(0, len(subject_specific) - size + 1))
            if subject_specific[index:index + size] not in ABSTRACT_TERMS
            and subject_specific[index:index + size] not in GENERIC_SUBJECT_TERMS
        )
    )
    concepts: list[SemanticConcept] = []
    table = _section(sections, REQUIRED_SECTIONS["term_table"])
    for line in table.splitlines():
        if not line.strip().startswith("|"):
            continue
        cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
        if len(cells) < 4 or cells[0] == "原文简称" or set(cells[0]) == {"-"}:
            continue
        full_normalized = _normalized(cells[1])
        short_normalized = _normalized(cells[0])
        domain_keywords = tuple(
            keyword
            for keyword in subject_keywords
            if keyword in full_normalized and keyword not in short_normalized
        )
        concepts.append(
            SemanticConcept(
                short_term=cells[0],
                full_meaning=cells[1],
                context=cells[2],
                forbidden_reading=cells[3],
                required_keywords=domain_keywords or _added_phrases(cells[0], cells[1]),
            )
        )
    concept_keywords = tuple(
        dict.fromkeys(keyword for concept in concepts for keyword in concept.required_keywords)
    )
    return SemanticContract(subject.strip(), concept_keywords or subject_keywords, tuple(concepts))


def audit_semantic_understanding(project: str | Path) -> SemanticAudit:
    project_path = Path(project)
    artifact = project_path / "analysis/00-semantic-understanding.md"
    text = artifact.read_text(encoding="utf-8", errors="ignore") if artifact.is_file() else ""
    sections = heading_sections(text)
    issues: list[SemanticIssue] = []
    resolved: dict[str, str] = {}
    for key, aliases in REQUIRED_SECTIONS.items():
        body = _section(sections, aliases)
        resolved[key] = body
        if not body:
            issues.append(SemanticIssue("missing-semantic-section", f"缺少全文语义理解章节：{aliases[0]}。"))
        elif not _substantive(body):
            issues.append(SemanticIssue("shallow-semantic-section", f"全文语义理解章节内容过浅：{aliases[0]}。"))

    subject = resolved.get("business_subject", "")
    if subject and len(_specific_subject_text(subject)) < 8:
        issues.append(SemanticIssue("abstract-business-subject", "全文业务主语只有抽象词，没有具体业务限定。"))
    objects = resolved.get("business_objects", "")
    if objects and not any(action in objects for action in BUSINESS_ACTIONS):
        issues.append(SemanticIssue("missing-business-object", "未说明材料分析、预测、研判、评估、预警或建设的具体对象。"))
    scope = resolved.get("scope", "")
    scope_tokens = ("全国", "区域", "省级", "年度", "季度", "月度", "服务", "对象", "内部", "外部")
    if scope and sum(token in scope for token in scope_tokens) < 2:
        issues.append(SemanticIssue("missing-scope-grounding", "空间、时间、场景或服务范围不足。"))
    decision = resolved.get("decision", "")
    if decision and not any(action in decision for action in DECISION_ACTIONS):
        issues.append(SemanticIssue("missing-decision-action", "没有明确材料需要推动的决策或工作动作。"))
    evidence = resolved.get("evidence", "")
    evidence_refs = set(re.findall(r"第[一二三四五六七八九十百]+章|工作摘要|附件[一二三四五六七八九十]*|表\S*", evidence))
    if evidence and len(evidence_refs) < 2:
        issues.append(SemanticIssue("missing-cross-section-evidence", "核心语义缺少至少两处可回查依据。"))

    errors = sum(issue.severity == "error" for issue in issues)
    return SemanticAudit(
        passed=errors == 0,
        issues=tuple(issues),
        metrics={
            "semantic_sections_present": sum(bool(value) for value in resolved.values()),
            "semantic_sections_required": len(REQUIRED_SECTIONS),
            "error_count": errors,
        },
        business_subject=re.sub(r"\s+", " ", subject).strip(),
    )


def render_semantic_audit(report: SemanticAudit) -> str:
    lines = [
        "# 全文语义理解闸门",
        "",
        f"- 状态：**{'PASS' if report.passed else 'FAIL'}**",
        f"- 章节：{report.metrics['semantic_sections_present']}/{report.metrics['semantic_sections_required']}",
        "",
    ]
    if report.issues:
        lines.extend(["## 问题", ""])
        lines.extend(f"- `{issue.code}`：{issue.message}" for issue in report.issues)
    else:
        lines.append("全文业务主语、核心对象、适用范围、决策动作、支撑关系和证据链达到进入 Source Truth 阶段的最低要求。")
    lines.extend(["", "> 本闸门验证流程与可定义的语义锚点，不替代对源材料的持续回查。", ""])
    return "\n".join(lines)


def write_semantic_audit(project: str | Path) -> SemanticAudit:
    project_path = Path(project)
    report = audit_semantic_understanding(project_path)
    analysis = project_path / "analysis"
    analysis.mkdir(parents=True, exist_ok=True)
    (analysis / "01-semantic-gate.json").write_text(
        json.dumps(report.to_dict(), ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    (analysis / "01-semantic-gate.md").write_text(render_semantic_audit(report), encoding="utf-8")
    return report
