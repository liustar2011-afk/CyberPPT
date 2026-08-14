from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass
from difflib import SequenceMatcher
from pathlib import Path
from typing import Any

from .source_truth import UNREALIZED_STATE_TERMS, parse_source_truth_map
from .version import get_version

_MAX_TITLES_FOR_HEADING_CHECK = 8
_MIN_HEADING_SPAN = 4

SOURCE_ID_RE = re.compile(r"^S\d{3,}$")
CHAPTER_ID_RE = re.compile(r"^C\d{2,}$")
PAGE_ID_RE = re.compile(r"^P\d{2,}$")

_CERTAINTY_TERMS = (
    "已建成",
    "已实现",
    "全面建成",
    "全面完成",
    "圆满完成",
    "高质量完成",
    "建成投用",
    "实现全覆盖",
    "率先",
    "引领",
    "树立标杆",
    "全国领先",
)

CONTRACT_FILES = {
    "source-truth.json": ("ppt-script.source-truth.v1", "sources"),
    "deck-decision.json": ("ppt-script.deck-decision.v1", None),
    "chapter-contracts.json": ("ppt-script.chapter-contracts.v1", "chapters"),
    "page-contracts.json": ("ppt-script.page-contracts.v1", "pages"),
}


@dataclass(frozen=True)
class ContractIssue:
    code: str
    file: str
    message: str
    severity: str = "error"


@dataclass(frozen=True)
class ContractReport:
    enabled: bool
    passed: bool
    issues: tuple[ContractIssue, ...]
    counts: dict[str, int]

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema": "ppt-script.contract-audit.v1",
            "enabled": self.enabled,
            "passed": self.passed,
            "counts": self.counts,
            "issues": [asdict(issue) for issue in self.issues],
        }


def _empty_payload(filename: str, version: str) -> dict[str, Any]:
    schema, collection = CONTRACT_FILES[filename]
    payload: dict[str, Any] = {"schema": schema, "skill_version": version}
    if collection:
        payload[collection] = []
    else:
        payload.update(
            {
                "audience": "",
                "objective": "",
                "decision_request": "",
                "core_conclusion": "",
                "argument_chain": [],
            }
        )
    return payload


def create_contract_scaffolds(project: Path, version: str | None = None) -> Path:
    contract_dir = project / "contracts"
    contract_dir.mkdir(parents=True, exist_ok=True)
    resolved_version = version or get_version()
    for filename in CONTRACT_FILES:
        path = contract_dir / filename
        if not path.exists():
            path.write_text(
                json.dumps(_empty_payload(filename, resolved_version), ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8",
            )
    (contract_dir / "README.md").write_text(
        "# 结构化合同\n\n"
        "本目录保存 Source Truth、整套汇报决策、章节合同和页面合同的机器可读版本。\n"
        "Markdown 仍用于人工阅读，JSON 用于引用检查、断点恢复和跨工具传递。\n",
        encoding="utf-8",
    )
    return contract_dir


def _load_payload(path: Path, issues: list[ContractIssue]) -> dict[str, Any] | None:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        issues.append(ContractIssue("invalid-json", path.name, f"无法读取有效 JSON：{exc}"))
        return None
    if not isinstance(payload, dict):
        issues.append(ContractIssue("invalid-root", path.name, "合同根节点必须是 JSON 对象。"))
        return None
    expected_schema = CONTRACT_FILES[path.name][0]
    if payload.get("schema") != expected_schema:
        issues.append(
            ContractIssue(
                "schema-mismatch",
                path.name,
                f"schema 应为 {expected_schema}，实际为 {payload.get('schema')!r}。",
            )
        )
    return payload


def _required_text(item: dict[str, Any], fields: tuple[str, ...], *, file: str, item_id: str, issues: list[ContractIssue]) -> None:
    for field in fields:
        value = item.get(field)
        if not isinstance(value, str) or not value.strip():
            issues.append(ContractIssue("missing-field", file, f"{item_id} 缺少非空字段 {field}。"))


def _id_set(
    items: Any,
    *,
    key: str,
    pattern: re.Pattern[str],
    file: str,
    issues: list[ContractIssue],
) -> set[str]:
    if not isinstance(items, list):
        issues.append(ContractIssue("invalid-collection", file, f"字段必须是数组：{key.replace('_id', 's')}。"))
        return set()
    identifiers: set[str] = set()
    for index, item in enumerate(items, start=1):
        if not isinstance(item, dict):
            issues.append(ContractIssue("invalid-item", file, f"第 {index} 个条目必须是对象。"))
            continue
        value = item.get(key)
        if not isinstance(value, str) or not pattern.fullmatch(value):
            issues.append(ContractIssue("invalid-id", file, f"第 {index} 个条目的 {key} 格式无效：{value!r}。"))
            continue
        if value in identifiers:
            issues.append(ContractIssue("duplicate-id", file, f"{key} 重复：{value}。"))
        identifiers.add(value)
    return identifiers


def _source_refs(item: dict[str, Any], *, item_id: str, file: str, known: set[str], issues: list[ContractIssue]) -> None:
    refs = item.get("source_ids", [])
    if not isinstance(refs, list) or any(not isinstance(ref, str) for ref in refs):
        issues.append(ContractIssue("invalid-reference-list", file, f"{item_id} 的 source_ids 必须是字符串数组。"))
        return
    for ref in refs:
        if ref not in known:
            issues.append(ContractIssue("unknown-source", file, f"{item_id} 引用了不存在的来源 {ref}。"))


def _unrealized_source_ids(project: Path) -> set[str]:
    path = project / "analysis/01-source-truth-map.md"
    if not path.is_file():
        return set()
    truth = parse_source_truth_map(path.read_text(encoding="utf-8", errors="ignore"))
    return {
        item.source_id
        for item in truth.items
        if any(term in item.state for term in UNREALIZED_STATE_TERMS)
    }


def _check_certainty_overreach(
    item: dict[str, Any],
    *,
    text_fields: tuple[str, ...],
    unrealized: set[str],
    item_id: str,
    file: str,
    issues: list[ContractIssue],
) -> None:
    refs = item.get("source_ids", [])
    if not isinstance(refs, list):
        return
    cited_unrealized = [ref for ref in refs if isinstance(ref, str) and ref in unrealized]
    if not cited_unrealized:
        return
    text = " ".join(str(item.get(field, "")) for field in text_fields)
    hits = [term for term in _CERTAINTY_TERMS if term in text]
    if hits:
        issues.append(
            ContractIssue(
                "title-overstates-certainty",
                file,
                f"{item_id} 使用既成事实措辞（{'、'.join(hits)}），"
                f"但引用来源 {'、'.join(cited_unrealized)} 在 Source Truth Map 中状态未完成（拟/计划/正在/待核实）；"
                "请核实措辞是否与来源状态相符。",
                severity="warning",
            )
        )


def _load_original_titles(project: Path) -> list[str]:
    from .extractors import extract_project_sources

    try:
        return extract_project_sources(project).original_titles
    except (FileNotFoundError, ImportError, OSError, ValueError):
        return []


def _shares_meaningful_span(a: str, b: str, *, minimum: int = _MIN_HEADING_SPAN) -> bool:
    match = SequenceMatcher(None, a, b).find_longest_match(0, len(a), 0, len(b))
    return match.size >= minimum


def _check_title_ignores_source_heading(
    item: dict[str, Any],
    *,
    original_titles: list[str],
    item_id: str,
    file: str,
    issues: list[ContractIssue],
) -> None:
    # Only fire for materials simple enough that "which heading applies" isn't ambiguous;
    # multi-section materials are expected to be restructured, not heading-matched 1:1.
    if not original_titles or len(original_titles) > _MAX_TITLES_FOR_HEADING_CHECK:
        return
    title = item.get("title")
    if not isinstance(title, str) or not title.strip():
        return
    if any(_shares_meaningful_span(title, heading) for heading in original_titles):
        return
    issues.append(
        ContractIssue(
            "title-ignores-source-heading",
            file,
            f"{item_id} 的标题“{title}”与原文自带标题（{'、'.join(original_titles)}）均无重合，"
            "请核实是否应优先复用原文已有的合规标题措辞（见 references/government-soe-title-rules.md 第0节）。",
            severity="warning",
        )
    )


def validate_contracts(project: Path) -> ContractReport:
    contract_dir = project / "contracts"
    if not contract_dir.exists():
        return ContractReport(enabled=False, passed=True, issues=(), counts={"sources": 0, "chapters": 0, "pages": 0})

    issues: list[ContractIssue] = []
    payloads: dict[str, dict[str, Any]] = {}
    for filename in CONTRACT_FILES:
        path = contract_dir / filename
        if not path.is_file():
            issues.append(ContractIssue("missing-file", filename, f"缺少合同文件：contracts/{filename}。"))
            continue
        payload = _load_payload(path, issues)
        if payload is not None:
            payloads[filename] = payload

    source_payload = payloads.get("source-truth.json", {})
    chapter_payload = payloads.get("chapter-contracts.json", {})
    page_payload = payloads.get("page-contracts.json", {})
    deck_payload = payloads.get("deck-decision.json", {})

    sources = source_payload.get("sources", [])
    chapters = chapter_payload.get("chapters", [])
    pages = page_payload.get("pages", [])

    source_ids = _id_set(sources, key="source_id", pattern=SOURCE_ID_RE, file="source-truth.json", issues=issues)
    chapter_ids = _id_set(chapters, key="chapter_id", pattern=CHAPTER_ID_RE, file="chapter-contracts.json", issues=issues)
    _id_set(pages, key="page_id", pattern=PAGE_ID_RE, file="page-contracts.json", issues=issues)

    if isinstance(sources, list):
        for item in sources:
            if isinstance(item, dict) and isinstance(item.get("source_id"), str):
                _required_text(item, ("type", "priority", "statement"), file="source-truth.json", item_id=item["source_id"], issues=issues)

    unrealized_source_ids = _unrealized_source_ids(project)
    original_titles = _load_original_titles(project)

    if isinstance(chapters, list):
        for item in chapters:
            if isinstance(item, dict) and isinstance(item.get("chapter_id"), str):
                item_id = item["chapter_id"]
                _required_text(item, ("mission", "core_conclusion"), file="chapter-contracts.json", item_id=item_id, issues=issues)
                _source_refs(item, item_id=item_id, file="chapter-contracts.json", known=source_ids, issues=issues)
                _check_certainty_overreach(
                    item,
                    text_fields=("title", "mission", "core_conclusion"),
                    unrealized=unrealized_source_ids,
                    item_id=item_id,
                    file="chapter-contracts.json",
                    issues=issues,
                )
                _check_title_ignores_source_heading(
                    item,
                    original_titles=original_titles,
                    item_id=item_id,
                    file="chapter-contracts.json",
                    issues=issues,
                )

    if isinstance(pages, list):
        for item in pages:
            if not isinstance(item, dict) or not isinstance(item.get("page_id"), str):
                continue
            item_id = item["page_id"]
            _required_text(
                item,
                ("mission", "key_message", "page_type", "visual_form"),
                file="page-contracts.json",
                item_id=item_id,
                issues=issues,
            )
            chapter_ref = item.get("chapter_id")
            if chapter_ref and chapter_ref not in chapter_ids:
                issues.append(ContractIssue("unknown-chapter", "page-contracts.json", f"{item_id} 引用了不存在的章节 {chapter_ref}。"))
            _source_refs(item, item_id=item_id, file="page-contracts.json", known=source_ids, issues=issues)
            _check_certainty_overreach(
                item,
                text_fields=("title", "mission", "key_message"),
                unrealized=unrealized_source_ids,
                item_id=item_id,
                file="page-contracts.json",
                issues=issues,
            )
            _check_title_ignores_source_heading(
                item,
                original_titles=original_titles,
                item_id=item_id,
                file="page-contracts.json",
                issues=issues,
            )

    deck_has_content = any(
        isinstance(deck_payload.get(field), str) and deck_payload.get(field, "").strip()
        for field in ("audience", "objective", "decision_request", "core_conclusion")
    )
    if deck_has_content:
        _required_text(
            deck_payload,
            ("audience", "objective", "decision_request", "core_conclusion"),
            file="deck-decision.json",
            item_id="deck-decision",
            issues=issues,
        )
        chain = deck_payload.get("argument_chain")
        if not isinstance(chain, list) or not all(isinstance(value, str) and value.strip() for value in chain):
            issues.append(ContractIssue("invalid-argument-chain", "deck-decision.json", "argument_chain 必须是非空字符串数组。"))

    counts = {
        "sources": len(sources) if isinstance(sources, list) else 0,
        "chapters": len(chapters) if isinstance(chapters, list) else 0,
        "pages": len(pages) if isinstance(pages, list) else 0,
    }
    error_count = sum(1 for issue in issues if issue.severity == "error")
    return ContractReport(enabled=True, passed=error_count == 0, issues=tuple(issues), counts=counts)


def render_contract_report(report: ContractReport) -> str:
    status = "PASS" if report.passed else "FAIL"
    lines = [
        "# 结构化合同检查",
        "",
        f"- 状态：**{status}**",
        f"- 合同模式：{'已启用' if report.enabled else '未启用（旧项目兼容模式）'}",
        f"- 来源：{report.counts.get('sources', 0)}",
        f"- 章节：{report.counts.get('chapters', 0)}",
        f"- 页面：{report.counts.get('pages', 0)}",
        "",
    ]
    if report.issues:
        lines.extend(["## 问题", ""])
        for issue in report.issues:
            lines.append(f"- `{issue.code}` `{issue.file}`：{issue.message}")
    else:
        lines.append("未发现结构、标识符或跨合同引用问题。")
    return "\n".join(lines) + "\n"


def write_contract_report(project: Path) -> ContractReport:
    report = validate_contracts(project)
    review_dir = project / "review"
    review_dir.mkdir(parents=True, exist_ok=True)
    (review_dir / "09-contract-audit.json").write_text(
        json.dumps(report.to_dict(), ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    (review_dir / "09-contract-audit.md").write_text(render_contract_report(report), encoding="utf-8")
    return report
