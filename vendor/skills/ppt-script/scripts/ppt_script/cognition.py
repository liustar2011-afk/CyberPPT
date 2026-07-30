from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Literal

from .evidence_graph import create_evidence_graph_scaffold, validate_evidence_graph
from .extractors import extract_project_sources

ReadingMode = Literal["faithful", "decision", "reconcile"]

_READING_FILES = {
    "faithful": "analysis/readings/01-faithful-reading.md",
    "decision": "analysis/readings/02-decision-reading.md",
    "reconcile": "analysis/readings/03-reconciliation.md",
}
_CONTEXT_FILES = {
    "faithful": "analysis/readings/00-faithful-context.md",
    "decision": "analysis/readings/00-decision-context.md",
    "reconcile": "analysis/readings/00-reconciliation-context.md",
}
_PROMPT_FILES = {
    "faithful": "system-prompt/stage1/12-faithful-reading.md",
    "decision": "system-prompt/stage1/13-decision-reading.md",
    "reconcile": "system-prompt/stage1/14-reconciliation.md",
}
_REQUIRED_HEADINGS = {
    "faithful": (
        "原文明示事实",
        "原文明示判断",
        "主体、状态与边界",
        "原文结构与关系",
        "冲突与歧义",
        "不得推断事项",
    ),
    "decision": (
        "汇报对象需要形成的判断",
        "主要矛盾",
        "决策相关内容",
        "可压缩内容",
        "研究空白",
        "风险与反方问题",
    ),
    "reconcile": (
        "一致结论",
        "可合并差异",
        "真实冲突",
        "共同遗漏与研究空白",
        "最终核心命题",
        "不确定性与置信度",
    ),
}
_PLACEHOLDERS = ("待生成", "待填写", "TODO", "TBD", "> 待")


@dataclass(frozen=True, slots=True)
class CognitiveIssue:
    code: str
    message: str
    location: str = ""
    severity: str = "error"


@dataclass(frozen=True, slots=True)
class CognitiveAudit:
    passed: bool
    issues: tuple[CognitiveIssue, ...]
    metrics: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema": "ppt-script.cognitive-audit.v1",
            "passed": self.passed,
            "metrics": self.metrics,
            "issues": [asdict(issue) for issue in self.issues],
        }


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="ignore") if path.is_file() else ""


def _substantive(text: str, minimum: int = 80) -> bool:
    compact = re.sub(r"\s+", "", text)
    return len(compact) >= minimum and not any(marker.lower() in text.lower() for marker in _PLACEHOLDERS)


def _copy_template(repo_root: Path, template_name: str, target: Path) -> None:
    if target.exists():
        return
    source = repo_root / "templates" / template_name
    if not source.is_file():
        raise FileNotFoundError(f"missing cognition template: {source}")
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(source.read_text(encoding="utf-8"), encoding="utf-8")


def initialize_cognition(project: str | Path, repo_root: str | Path) -> tuple[Path, ...]:
    project_path = Path(project)
    root = Path(repo_root)
    outputs: list[Path] = []
    for mode, template in (
        ("faithful", "faithful-reading.md"),
        ("decision", "decision-reading.md"),
        ("reconcile", "reconciliation.md"),
    ):
        target = project_path / _READING_FILES[mode]
        _copy_template(root, template, target)
        outputs.append(target)
    outputs.append(create_evidence_graph_scaffold(project_path))
    meta_path = project_path / "project.json"
    if meta_path.is_file():
        meta = json.loads(meta_path.read_text(encoding="utf-8"))
        meta["cognitive_mode"] = "enhanced"
        meta["cognitive_gate_required"] = True
        meta_path.write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
    return tuple(outputs)


def _artifact_section(project: Path, relative: str, title: str) -> str:
    path = project / relative
    text = _read(path).strip()
    if not text:
        return ""
    return f"# {title}\n\n来源：`{relative}`\n\n{text}\n"


def _source_section(project: Path) -> tuple[str, tuple[str, ...]]:
    bundle = extract_project_sources(project)
    return bundle.text.strip(), tuple(bundle.file_names)


def build_reading_context(
    project: str | Path,
    repo_root: str | Path,
    mode: ReadingMode,
) -> Path:
    if mode not in _READING_FILES:
        raise ValueError(f"unknown reading mode: {mode}")
    project_path = Path(project)
    root = Path(repo_root)
    source_text, source_files = _source_section(project_path)
    if not source_text:
        raise ValueError("source/ 中没有可读取的源材料。")
    prompt_path = root / _PROMPT_FILES[mode]
    if not prompt_path.is_file():
        raise FileNotFoundError(f"missing cognition prompt: {prompt_path}")
    deep_kernel = root / "system-prompt/stage1/05-deep-reading-kernel.md"

    sections = [
        f"# {mode} 独立认知上下文",
        "",
        "本文件是一次独立阅读的完整工作集。当前项目源材料和 Source Truth Map 是事实权威。",
        "不得读取其他独立阅读成果、综合裁决成果或历史案例后再完成本次阅读。",
        "",
        "## 输出位置",
        "",
        f"将结果写入 `{_READING_FILES[mode]}`。",
        "",
        "## 源文件清单",
        "",
        *[f"- `{name}`" for name in source_files],
        "",
        "# 源材料正文",
        "",
        source_text,
        "",
        _artifact_section(project_path, "analysis/00-analysis.md", "现有材料分析").strip(),
        "",
        _artifact_section(project_path, "analysis/01-source-truth-map.md", "Source Truth Map").strip(),
        "",
        "# 常驻深度阅读规则",
        "",
        _read(deep_kernel).strip(),
        "",
        "# 本次独立阅读规则",
        "",
        _read(prompt_path).strip(),
        "",
    ]
    if mode == "reconcile":
        faithful_path = project_path / _READING_FILES["faithful"]
        decision_path = project_path / _READING_FILES["decision"]
        faithful = _read(faithful_path)
        decision = _read(decision_path)
        if not _substantive(faithful) or not _substantive(decision):
            raise ValueError("忠实阅读和决策阅读均完成后，才能生成综合裁决上下文。")
        sections.extend(
            [
                "# 忠实阅读成果",
                "",
                faithful.strip(),
                "",
                "# 决策阅读成果",
                "",
                decision.strip(),
                "",
            ]
        )
    output = project_path / _CONTEXT_FILES[mode]
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text("\n".join(part for part in sections if part is not None).strip() + "\n", encoding="utf-8")
    return output


def _heading_bodies(text: str) -> dict[str, str]:
    matches = list(re.finditer(r"(?m)^#{2,4}\s+(.+?)\s*$", text))
    result: dict[str, str] = {}
    for index, match in enumerate(matches):
        end = matches[index + 1].start() if index + 1 < len(matches) else len(text)
        result[match.group(1).strip()] = text[match.end():end].strip()
    return result


def _audit_reading(project: Path, mode: ReadingMode, issues: list[CognitiveIssue]) -> bool:
    relative = _READING_FILES[mode]
    text = _read(project / relative)
    if not _substantive(text):
        issues.append(CognitiveIssue("incomplete-reading", f"{mode} 阅读未完成或仍为占位内容。", relative))
        return False
    sections = _heading_bodies(text)
    for heading in _REQUIRED_HEADINGS[mode]:
        body = next((value for title, value in sections.items() if heading in title), "")
        if not _substantive(body, 8):
            issues.append(CognitiveIssue("missing-reading-section", f"{mode} 阅读缺少实质章节：{heading}。", relative))
    return True


def audit_cognition(project: str | Path) -> CognitiveAudit:
    project_path = Path(project)
    issues: list[CognitiveIssue] = []
    completed = {mode: _audit_reading(project_path, mode, issues) for mode in _READING_FILES}

    faithful_context = _read(project_path / _CONTEXT_FILES["faithful"])
    decision_context = _read(project_path / _CONTEXT_FILES["decision"])
    faithful_result = _read(project_path / _READING_FILES["faithful"]).strip()
    decision_result = _read(project_path / _READING_FILES["decision"]).strip()
    if faithful_result and faithful_result in decision_context:
        issues.append(CognitiveIssue("reading-leakage", "决策阅读上下文包含忠实阅读成果。", _CONTEXT_FILES["decision"]))
    if decision_result and decision_result in faithful_context:
        issues.append(CognitiveIssue("reading-leakage", "忠实阅读上下文包含决策阅读成果。", _CONTEXT_FILES["faithful"]))
    for relative, text in ((_CONTEXT_FILES["faithful"], faithful_context), (_CONTEXT_FILES["decision"], decision_context)):
        if "knowledge/cases" in text or "00-experience-context" in text:
            issues.append(CognitiveIssue("experience-contamination", "独立阅读上下文不得包含历史案例。", relative))

    graph = validate_evidence_graph(project_path)
    if not graph.passed:
        for issue in graph.issues:
            issues.append(CognitiveIssue(f"graph-{issue.code}", issue.message, issue.location, issue.severity))
    if graph.counts.get("claims", 0) == 0:
        issues.append(CognitiveIssue("empty-evidence-graph", "证据图谱至少需要一个核心主张。", "contracts/evidence-graph.json"))

    metrics = {
        "faithful_completed": completed["faithful"],
        "decision_completed": completed["decision"],
        "reconciliation_completed": completed["reconcile"],
        "claims": graph.counts.get("claims", 0),
        "relations": graph.counts.get("relations", 0),
        "error_count": sum(1 for issue in issues if issue.severity == "error"),
    }
    return CognitiveAudit(
        passed=metrics["error_count"] == 0,
        issues=tuple(issues),
        metrics=metrics,
    )


def render_cognitive_audit(report: CognitiveAudit) -> str:
    status = "PASS" if report.passed else "FAIL"
    lines = [
        "# 认知增强闸门",
        "",
        f"- 状态：**{status}**",
        f"- 忠实阅读：{'完成' if report.metrics.get('faithful_completed') else '未完成'}",
        f"- 决策阅读：{'完成' if report.metrics.get('decision_completed') else '未完成'}",
        f"- 综合裁决：{'完成' if report.metrics.get('reconciliation_completed') else '未完成'}",
        f"- 证据主张：{report.metrics.get('claims', 0)}",
        f"- 主张关系：{report.metrics.get('relations', 0)}",
        "",
    ]
    if report.issues:
        lines.extend(["## 问题", ""])
        for issue in report.issues:
            location = f" `{issue.location}`" if issue.location else ""
            lines.append(f"- `{issue.code}`{location}：{issue.message}")
    else:
        lines.append("两次独立阅读、综合裁决和证据图谱均达到进入故事线阶段的最低要求。")
    lines.extend(["", "> 通过本闸门不等于结论必然正确，后续仍须持续回查源材料和 Source Truth Map。", ""])
    return "\n".join(lines)


def write_cognitive_audit(project: str | Path) -> CognitiveAudit:
    project_path = Path(project)
    report = audit_cognition(project_path)
    review = project_path / "review"
    review.mkdir(parents=True, exist_ok=True)
    (review / "10-cognitive-audit.json").write_text(
        json.dumps(report.to_dict(), ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    (review / "10-cognitive-audit.md").write_text(render_cognitive_audit(report), encoding="utf-8")
    return report
