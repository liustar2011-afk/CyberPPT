from __future__ import annotations

import json
import math
import re
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

import yaml

CASE_SCHEMA = "ppt-script.experience-case.v1"
INDEX_SCHEMA = "ppt-script.experience-index.v1"
CONTEXT_SCHEMA = "ppt-script.experience-context.v1"
VALID_STATUSES = {"draft", "approved", "rejected", "archived"}
REQUIRED_TEXT_FIELDS = (
    "case_id",
    "title",
    "task_type",
    "report_subtype",
    "audience_level",
    "issue_type",
    "original_output",
    "revised_output",
    "source_project",
    "created_at",
    "status",
)
REQUIRED_LIST_FIELDS = (
    "tags",
    "reasons",
    "applicable_conditions",
    "do_not_apply_when",
    "positive_patterns",
    "anti_patterns",
)
_CASE_ID = re.compile(r"^CASE-[0-9A-Za-z][0-9A-Za-z.-]*$")
_TOKEN = re.compile(r"[A-Za-z0-9_-]+|[\u4e00-\u9fff]")


@dataclass(frozen=True, slots=True)
class ExperienceIssue:
    code: str
    path: str
    message: str


@dataclass(frozen=True, slots=True)
class CaseIndexResult:
    cases: tuple[dict[str, Any], ...]
    issues: tuple[ExperienceIssue, ...]
    index_path: Path


@dataclass(frozen=True, slots=True)
class CaseHit:
    case_id: str
    title: str
    score: float
    matched_by: tuple[str, ...]
    penalties: tuple[str, ...]
    case: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return {
            "case_id": self.case_id,
            "title": self.title,
            "score": round(self.score, 6),
            "matched_by": list(self.matched_by),
            "penalties": list(self.penalties),
            "case": self.case,
        }


@dataclass(frozen=True, slots=True)
class ExperiencePack:
    markdown_path: Path
    json_path: Path
    hits: tuple[CaseHit, ...]


def _nonempty_text(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _string_list(value: Any) -> bool:
    return isinstance(value, list) and all(isinstance(item, str) and item.strip() for item in value)


def validate_case(payload: Mapping[str, Any], source: str = "") -> tuple[ExperienceIssue, ...]:
    issues: list[ExperienceIssue] = []
    if payload.get("schema") != CASE_SCHEMA:
        issues.append(ExperienceIssue("invalid-schema", source, f"schema must be {CASE_SCHEMA}"))
    for field in REQUIRED_TEXT_FIELDS:
        if not _nonempty_text(payload.get(field)):
            issues.append(ExperienceIssue(f"missing-{field}", source, f"{field} must be non-empty text"))
    for field in REQUIRED_LIST_FIELDS:
        if not _string_list(payload.get(field)):
            issues.append(ExperienceIssue(f"invalid-{field}", source, f"{field} must be a string list"))
    if _nonempty_text(payload.get("case_id")) and not _CASE_ID.fullmatch(str(payload["case_id"])):
        issues.append(ExperienceIssue("invalid-case-id", source, "case_id must start with CASE-"))
    status = payload.get("status")
    if _nonempty_text(status) and status not in VALID_STATUSES:
        issues.append(ExperienceIssue("invalid-status", source, f"status must be one of {sorted(VALID_STATUSES)}"))
    if isinstance(payload.get("reasons"), list) and not payload.get("reasons"):
        issues.append(ExperienceIssue("empty-reasons", source, "reasons must explain why the revision is better"))
    if isinstance(payload.get("applicable_conditions"), list) and not payload.get("applicable_conditions"):
        issues.append(
            ExperienceIssue(
                "empty-applicable-conditions",
                source,
                "applicable_conditions must define when the case may be reused",
            )
        )
    return tuple(issues)


def _load_markdown_case(path: Path) -> dict[str, Any]:
    text = path.read_text(encoding="utf-8", errors="replace")
    if not text.startswith("---"):
        raise ValueError("Markdown case must begin with YAML frontmatter")
    parts = text.split("---", 2)
    if len(parts) < 3:
        raise ValueError("Markdown frontmatter is not closed")
    payload = yaml.safe_load(parts[1]) or {}
    if not isinstance(payload, dict):
        raise ValueError("Markdown frontmatter must be a mapping")
    body = parts[2].strip()
    if body and not payload.get("revised_output"):
        payload["revised_output"] = body
    return dict(payload)


def _load_case(path: Path) -> dict[str, Any]:
    if path.suffix.lower() == ".json":
        payload = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(payload, dict):
            raise ValueError("case JSON must contain an object")
        return payload
    if path.suffix.lower() in {".md", ".markdown"}:
        return _load_markdown_case(path)
    raise ValueError(f"unsupported case format: {path.suffix}")


def _case_files(repo_root: Path) -> list[Path]:
    case_root = repo_root / "knowledge/cases"
    if not case_root.is_dir():
        return []
    return sorted(
        path
        for path in case_root.rglob("*")
        if path.is_file() and path.suffix.lower() in {".json", ".md", ".markdown"} and path.name != "README.md"
    )


def build_case_index(repo_root: str | Path) -> CaseIndexResult:
    root = Path(repo_root).resolve()
    cases: list[dict[str, Any]] = []
    issues: list[ExperienceIssue] = []
    seen: set[str] = set()
    for path in _case_files(root):
        relative = str(path.relative_to(root))
        try:
            payload = _load_case(path)
        except (OSError, ValueError, json.JSONDecodeError, yaml.YAMLError) as exc:
            issues.append(ExperienceIssue("invalid-case-file", relative, str(exc)))
            continue
        validation = validate_case(payload, relative)
        if validation:
            issues.extend(validation)
            continue
        case_id = str(payload["case_id"])
        if case_id in seen:
            issues.append(ExperienceIssue("duplicate-case-id", relative, f"duplicate case_id: {case_id}"))
            continue
        seen.add(case_id)
        if payload.get("status") != "approved":
            issues.append(ExperienceIssue("not-approved", relative, f"case {case_id} excluded because status is not approved"))
            continue
        normalized = dict(payload)
        normalized["source_file"] = relative
        cases.append(normalized)

    cases.sort(key=lambda item: str(item.get("case_id", "")))
    index_dir = root / "knowledge/index"
    index_dir.mkdir(parents=True, exist_ok=True)
    index_path = index_dir / "case-index.json"
    index_payload = {
        "schema": INDEX_SCHEMA,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "case_count": len(cases),
        "cases": cases,
        "issues": [asdict(issue) for issue in issues],
    }
    index_path.write_text(json.dumps(index_payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return CaseIndexResult(tuple(cases), tuple(issues), index_path)


def _tokens(text: str) -> set[str]:
    return {token.lower() for token in _TOKEN.findall(text or "") if token.strip()}


def _case_text(case: Mapping[str, Any]) -> str:
    parts: list[str] = []
    for field in (
        "title",
        "task_type",
        "report_subtype",
        "audience_level",
        "issue_type",
        "original_output",
        "revised_output",
    ):
        value = case.get(field)
        if isinstance(value, str):
            parts.append(value)
    for field in REQUIRED_LIST_FIELDS:
        value = case.get(field)
        if isinstance(value, list):
            parts.extend(str(item) for item in value)
    return " ".join(parts)


def _text_similarity(query: str, case_text: str) -> float:
    if not query.strip() or not case_text.strip():
        return 0.0
    try:
        from sklearn.feature_extraction.text import TfidfVectorizer
        from sklearn.metrics.pairwise import cosine_similarity

        matrix = TfidfVectorizer(analyzer="char", ngram_range=(1, 3), min_df=1).fit_transform([query, case_text])
        return float(cosine_similarity(matrix[0:1], matrix[1:2])[0][0])
    except (ImportError, ValueError):
        left = _tokens(query)
        right = _tokens(case_text)
        if not left or not right:
            return 0.0
        return len(left & right) / math.sqrt(len(left) * len(right))


def _load_index(repo_root: Path) -> list[dict[str, Any]]:
    index_path = repo_root / "knowledge/index/case-index.json"
    if not index_path.is_file():
        return list(build_case_index(repo_root).cases)
    try:
        payload = json.loads(index_path.read_text(encoding="utf-8"))
        cases = payload.get("cases", [])
        if isinstance(cases, list):
            return [dict(case) for case in cases if isinstance(case, dict) and case.get("status") == "approved"]
    except (OSError, json.JSONDecodeError, TypeError):
        pass
    return list(build_case_index(repo_root).cases)


def search_cases(
    repo_root: str | Path,
    query: str,
    filters: Mapping[str, str] | None = None,
    limit: int = 5,
) -> tuple[CaseHit, ...]:
    root = Path(repo_root).resolve()
    filters = dict(filters or {})
    query_tokens = _tokens(query)
    hits: list[CaseHit] = []
    weights = {
        "task_type": 0.24,
        "audience_level": 0.20,
        "report_subtype": 0.14,
        "issue_type": 0.18,
    }
    for case in _load_index(root):
        score = 0.44 * _text_similarity(query, _case_text(case))
        matched: list[str] = []
        penalties: list[str] = []
        metadata_score = 0.0
        for field, weight in weights.items():
            requested = str(filters.get(field, "")).strip()
            if not requested:
                continue
            actual = str(case.get(field, "")).strip()
            if requested == actual:
                metadata_score += weight
            elif actual:
                metadata_score -= weight * 0.30
        if metadata_score > 0:
            matched.append("metadata")
        score += metadata_score

        tags = _tokens(" ".join(str(item) for item in case.get("tags", [])))
        if query_tokens and tags:
            overlap = len(query_tokens & tags) / max(1, len(query_tokens))
            if overlap:
                score += min(0.16, 0.16 * overlap)
                matched.append("tags")

        negative_text = " ".join(str(item) for item in case.get("do_not_apply_when", []))
        negative_tokens = _tokens(negative_text)
        if query_tokens & negative_tokens:
            score -= 0.55
            penalties.append("negative-scope")
        if not matched and score > 0:
            matched.append("semantic")
        hits.append(
            CaseHit(
                case_id=str(case.get("case_id", "")),
                title=str(case.get("title", "")),
                score=score,
                matched_by=tuple(dict.fromkeys(matched)),
                penalties=tuple(penalties),
                case=case,
            )
        )
    hits.sort(key=lambda item: (-item.score, item.case_id))
    return tuple(hits[: max(0, int(limit))])


def _read_project_text(project: Path, paths: Iterable[str], limit: int = 30000) -> str:
    chunks: list[str] = []
    used = 0
    for relative in paths:
        path = project / relative
        if not path.is_file():
            continue
        text = path.read_text(encoding="utf-8", errors="replace")
        remaining = limit - used
        if remaining <= 0:
            break
        chunks.append(text[:remaining])
        used += min(len(text), remaining)
    return "\n\n".join(chunks)


def _project_query(project: Path, meta: Mapping[str, Any]) -> str:
    core = " ".join(
        str(meta.get(field, ""))
        for field in ("name", "task_type", "report_subtype", "audience_level", "primary_goal", "decision_intent")
    )
    artifacts = _read_project_text(
        project,
        (
            "analysis/00-analysis.md",
            "analysis/readings/03-reconciliation.md",
            "decision/01-decision.md",
            "outline/02-outline.md",
            "review/04-review.md",
        ),
    )
    return f"{core}\n{artifacts}".strip()


def build_experience_pack(project: str | Path, repo_root: str | Path, limit: int = 5) -> ExperiencePack:
    project_path = Path(project).resolve()
    root = Path(repo_root).resolve()
    meta_path = project_path / "project.json"
    meta = json.loads(meta_path.read_text(encoding="utf-8")) if meta_path.is_file() else {}
    if str(meta.get("experience_mode", "enabled")) == "disabled":
        hits: tuple[CaseHit, ...] = ()
        query = ""
    else:
        query = _project_query(project_path, meta)
        hits = search_cases(
            root,
            query,
            filters={
                "task_type": str(meta.get("task_type", "")),
                "report_subtype": str(meta.get("report_subtype", "")),
                "audience_level": str(meta.get("audience_level", "")),
                "issue_type": str(meta.get("experience_issue_type", "")),
            },
            limit=limit,
        )
        hits = tuple(hit for hit in hits if hit.score > -0.10)

    analysis = project_path / "analysis"
    analysis.mkdir(parents=True, exist_ok=True)
    markdown_path = analysis / "00-experience-context.md"
    json_path = analysis / "00-experience-context.json"
    payload = {
        "schema": CONTEXT_SCHEMA,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "reference_only": True,
        "source_evidence_allowed": False,
        "query": query,
        "hits": [hit.to_dict() for hit in hits],
    }
    json_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    lines = [
        "# 历史经验上下文",
        "",
        "> 以下案例仅供方法参考，不得作为事实来源、政策依据、Source ID 或当前项目已经具备能力的证明。",
        "> 所有项目事实、数字、状态和边界仍须回溯到当前项目 `source/`、Source Truth Map 和证据图谱。",
        "",
    ]
    if not hits:
        lines.append("未检索到达到当前阈值的已批准案例。不得为了使用经验库而强行套用不相关案例。")
    for hit in hits:
        case = hit.case
        lines.extend(
            [
                f"## {hit.case_id}｜{hit.title}",
                "",
                "**标记：仅供方法参考**",
                "",
                f"- 相关度：{hit.score:.3f}",
                f"- 适用条件：{'；'.join(case.get('applicable_conditions', []))}",
                f"- 不适用条件：{'；'.join(case.get('do_not_apply_when', [])) or '无明确记录'}",
                f"- 原问题：{case.get('original_output', '')}",
                f"- 修订方式：{case.get('revised_output', '')}",
                f"- 修改原因：{'；'.join(case.get('reasons', []))}",
                f"- 正向模式：{'；'.join(case.get('positive_patterns', []))}",
                f"- 反模式：{'；'.join(case.get('anti_patterns', []))}",
                "",
            ]
        )
    markdown_path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")
    return ExperiencePack(markdown_path, json_path, hits)


def capture_case(project: str | Path, repo_root: str | Path) -> Path:
    project_path = Path(project).resolve()
    root = Path(repo_root).resolve()
    feedback = project_path / "experience/feedback-capture.json"
    if not feedback.is_file():
        raise FileNotFoundError(f"feedback capture file not found: {feedback}")
    payload = json.loads(feedback.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("feedback-capture.json must contain an object")
    issues = validate_case(payload, str(feedback))
    if issues:
        raise ValueError("; ".join(f"{issue.code}: {issue.message}" for issue in issues))
    if payload.get("status") != "approved":
        raise ValueError("only status=approved feedback can be promoted to the knowledge base")
    output_dir = root / "knowledge/cases"
    output_dir.mkdir(parents=True, exist_ok=True)
    output = output_dir / f"{payload['case_id']}.json"
    if output.exists():
        existing = json.loads(output.read_text(encoding="utf-8"))
        if existing != payload:
            raise FileExistsError(f"case already exists with different content: {output}")
        return output
    output.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    build_case_index(root)
    return output


def initialize_experience(project: str | Path, repo_root: str | Path) -> tuple[Path, ...]:
    project_path = Path(project).resolve()
    root = Path(repo_root).resolve()
    experience_dir = project_path / "experience"
    experience_dir.mkdir(parents=True, exist_ok=True)
    output = experience_dir / "feedback-capture.json"
    template = root / "templates/experience-feedback.json"
    if not output.exists():
        if template.is_file():
            output.write_text(template.read_text(encoding="utf-8"), encoding="utf-8")
        else:
            output.write_text(json.dumps({"schema": CASE_SCHEMA, "status": "draft"}, ensure_ascii=False, indent=2), encoding="utf-8")
    return (output,)
