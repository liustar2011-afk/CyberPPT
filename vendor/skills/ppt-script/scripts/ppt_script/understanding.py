from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from .extractors import extract_project_sources
from .semantics import audit_semantic_understanding, parse_semantic_contract
from .source_truth import build_source_inventory, parse_source_truth_map

_REQUIRED_SECTIONS: dict[str, tuple[str, ...]] = {
    "material_intent": ("材料意图", "汇报意图", "决策请求"),
    "material_type": ("材料类型",),
    "structure_assessment": ("原文结构评估", "结构评估"),
    "core_claim": ("核心主张", "核心结论"),
    "argument_architecture": ("表达架构", "论证架构", "汇报主线"),
    "cross_section": ("跨章节证据综合", "跨章节综合", "跨章节证据"),
    "conflicts": ("矛盾与待核", "冲突与待核", "待核事项"),
    "state_boundary": ("状态与边界核验", "状态、主体、数字和边界核验", "状态和边界核验"),
}
_PLACEHOLDER_TERMS = ("待生成", "待分析", "待补充", "TODO", "TBD", "待填写")
_CONFLICT_TERMS = ("矛盾", "冲突", "不一致", "但正文", "口径不同", "两种口径")


@dataclass(frozen=True)
class UnderstandingIssue:
    code: str
    message: str
    severity: str = "error"
    location: str = ""


@dataclass(frozen=True)
class UnderstandingAudit:
    passed: bool
    issues: tuple[UnderstandingIssue, ...]
    metrics: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema": "ppt-script.understanding-audit.v1",
            "passed": self.passed,
            "metrics": self.metrics,
            "issues": [asdict(issue) for issue in self.issues],
        }


def _heading_sections(text: str) -> dict[str, str]:
    matches = list(re.finditer(r"(?m)^#{2,4}\s+(.+?)\s*$", text))
    sections: dict[str, str] = {}
    for index, match in enumerate(matches):
        start = match.end()
        end = matches[index + 1].start() if index + 1 < len(matches) else len(text)
        sections[match.group(1).strip()] = text[start:end].strip()
    return sections


def _find_section(sections: dict[str, str], aliases: tuple[str, ...]) -> tuple[str, str] | None:
    for title, body in sections.items():
        if any(alias in title for alias in aliases):
            return title, body
    return None


def _substantive(body: str, *, minimum: int = 12) -> bool:
    compact = re.sub(r"\s+", "", body)
    return len(compact) >= minimum and not any(term.lower() in body.lower() for term in _PLACEHOLDER_TERMS)


def _truth_text(project: Path) -> str:
    path = project / "analysis/01-source-truth-map.md"
    return path.read_text(encoding="utf-8", errors="ignore") if path.is_file() else ""


def audit_source_understanding(project: str | Path) -> UnderstandingAudit:
    project_path = Path(project)
    issues: list[UnderstandingIssue] = []
    analysis_path = project_path / "analysis/00-analysis.md"
    analysis_text = analysis_path.read_text(encoding="utf-8", errors="ignore") if analysis_path.is_file() else ""
    sections = _heading_sections(analysis_text)

    section_status: dict[str, bool] = {}
    for key, aliases in _REQUIRED_SECTIONS.items():
        found = _find_section(sections, aliases)
        if found is None:
            section_status[key] = False
            issues.append(UnderstandingIssue("missing-analysis-section", f"材料分析缺少章节：{aliases[0]}。", location="analysis/00-analysis.md"))
            continue
        title, body = found
        ok = _substantive(body)
        section_status[key] = ok
        if not ok:
            issues.append(UnderstandingIssue("shallow-analysis-section", f"材料分析章节内容过浅或仍为占位：{title}。", location="analysis/00-analysis.md"))

    truth_text = _truth_text(project_path)
    truth = parse_source_truth_map(truth_text)
    for item in truth.issues:
        issues.append(UnderstandingIssue("invalid-source-truth", item, location="analysis/01-source-truth-map.md"))
    if not truth.items:
        issues.append(UnderstandingIssue("empty-source-truth", "Source Truth Map 没有有效条目。", location="analysis/01-source-truth-map.md"))

    p0_items = [item for item in truth.items if item.importance == "P0"]
    if not p0_items:
        issues.append(UnderstandingIssue("missing-p0", "Source Truth Map 至少需要一个 P0 核心条目。", location="analysis/01-source-truth-map.md"))
    for item in p0_items:
        for field, label in ((item.content, "内容"), (item.subject, "主体"), (item.source_location, "原文出处")):
            if not field.strip():
                issues.append(UnderstandingIssue("incomplete-p0", f"{item.source_id} 的 {label} 不能为空。", location="analysis/01-source-truth-map.md"))
        if item.source_location.strip() in {"源材料", "相关章节", "原文", "附件"}:
            issues.append(UnderstandingIssue("vague-source-location", f"{item.source_id} 的原文出处过于宽泛，无法回查。", location="analysis/01-source-truth-map.md"))

    semantic_enabled = False
    meta_path = project_path / "project.json"
    if meta_path.is_file():
        try:
            semantic_enabled = bool(
                json.loads(meta_path.read_text(encoding="utf-8")).get("semantic_gate_required", False)
            )
        except (OSError, json.JSONDecodeError):
            semantic_enabled = False
    detached_terms: list[str] = []
    semantic_keywords: tuple[str, ...] = ()
    semantic_path = project_path / "analysis/00-semantic-understanding.md"
    if semantic_enabled and semantic_path.is_file():
        semantic_report = audit_semantic_understanding(project_path)
        if semantic_report.passed:
            contract = parse_semantic_contract(
                semantic_path.read_text(encoding="utf-8", errors="ignore")
            )
            semantic_keywords = contract.business_keywords
            p0_text = "\n".join(item.content for item in p0_items)
            if semantic_keywords and not any(keyword in p0_text for keyword in semantic_keywords):
                issues.append(
                    UnderstandingIssue(
                        "missing-semantic-inheritance",
                        "P0定位条目没有继承全文业务主语中的具体业务限定。",
                        location="analysis/01-source-truth-map.md",
                    )
                )
            for concept in contract.concepts:
                if not concept.required_keywords:
                    continue
                for item in p0_items:
                    if concept.short_term not in item.content or any(
                        keyword in item.content for keyword in concept.required_keywords
                    ):
                        continue
                    marker = f"{item.source_id}:{concept.short_term}"
                    if marker in detached_terms:
                        continue
                    detached_terms.append(marker)
                    issues.append(
                        UnderstandingIssue(
                            "detached-core-term",
                            f"{item.source_id} 使用‘{concept.short_term}’，但未保留完整业务限定。",
                            location="analysis/01-source-truth-map.md",
                        )
                    )

    try:
        bundle = extract_project_sources(project_path)
        inventory = build_source_inventory(bundle.text, bundle.file_names)
        source_text = bundle.text
    except (FileNotFoundError, ImportError, OSError, ValueError):
        inventory = build_source_inventory("")
        source_text = ""

    if inventory.state_terms and not any(item.state.strip() for item in p0_items):
        issues.append(UnderstandingIssue("missing-state-grounding", "源材料包含事项状态，但 P0 条目未记录状态。", location="analysis/01-source-truth-map.md"))
    if inventory.boundary_terms and not any(item.boundary.strip() or item.category == "B" for item in p0_items):
        issues.append(UnderstandingIssue("missing-boundary-grounding", "源材料包含条件或合规边界，但 P0 条目未建立边界。", location="analysis/01-source-truth-map.md"))

    source_has_conflict = any(term in source_text for term in _CONFLICT_TERMS)
    truth_has_conflict = any(item.conflict.strip() or item.category == "U" for item in truth.items)
    if source_has_conflict and not truth_has_conflict:
        issues.append(UnderstandingIssue("untracked-conflict", "源材料存在冲突或不同口径，但 Source Truth Map 未记录。", location="analysis/01-source-truth-map.md"))

    analysis_has_cross_section = section_status.get("cross_section", False)
    if inventory.file_count > 1 and not analysis_has_cross_section:
        issues.append(UnderstandingIssue("missing-multisource-synthesis", "多源材料必须说明跨文件、跨章节证据如何归并。", location="analysis/00-analysis.md"))

    error_count = sum(1 for issue in issues if issue.severity == "error")
    metrics = {
        "source_file_count": inventory.file_count,
        "source_character_count": inventory.char_count,
        "analysis_sections_present": sum(1 for value in section_status.values() if value),
        "analysis_sections_required": len(_REQUIRED_SECTIONS),
        "source_truth_items": len(truth.items),
        "p0_items": len(p0_items),
        "boundary_items": sum(1 for item in truth.items if item.category == "B" or item.boundary.strip()),
        "conflict_items": sum(1 for item in truth.items if item.category == "U" or item.conflict.strip()),
        "semantic_gate_enabled": semantic_enabled,
        "semantic_business_keywords": list(semantic_keywords),
        "detached_core_terms": detached_terms,
        "error_count": error_count,
    }
    return UnderstandingAudit(passed=error_count == 0, issues=tuple(issues), metrics=metrics)


def render_understanding_audit(report: UnderstandingAudit) -> str:
    status = "PASS" if report.passed else "FAIL"
    lines = [
        "# 源材料理解闸门",
        "",
        f"- 状态：**{status}**",
        f"- 源文件：{report.metrics.get('source_file_count', 0)}",
        f"- 源材料字符：{report.metrics.get('source_character_count', 0)}",
        f"- 分析章节：{report.metrics.get('analysis_sections_present', 0)}/{report.metrics.get('analysis_sections_required', 0)}",
        f"- Source Truth 条目：{report.metrics.get('source_truth_items', 0)}",
        f"- P0 条目：{report.metrics.get('p0_items', 0)}",
        "",
    ]
    if report.issues:
        lines.extend(["## 问题", ""])
        for issue in report.issues:
            location = f" `{issue.location}`" if issue.location else ""
            lines.append(f"- `{issue.code}`{location}：{issue.message}")
    else:
        lines.append("材料意图、结构、跨章节证据、状态、主体、边界和冲突已达到进入故事线阶段的最低要求。")
    lines.extend(
        [
            "",
            "> 本工具检查可验证的完整性，不替代人工或模型对材料结论质量的判断。通过后仍须持续回查原文。",
        ]
    )
    return "\n".join(lines) + "\n"


def write_understanding_audit(project: str | Path) -> UnderstandingAudit:
    project_path = Path(project)
    report = audit_source_understanding(project_path)
    analysis_dir = project_path / "analysis"
    analysis_dir.mkdir(parents=True, exist_ok=True)
    (analysis_dir / "02-understanding-gate.json").write_text(
        json.dumps(report.to_dict(), ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    (analysis_dir / "02-understanding-gate.md").write_text(render_understanding_audit(report), encoding="utf-8")
    return report
