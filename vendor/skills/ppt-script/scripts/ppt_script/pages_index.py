from __future__ import annotations

import json
import re
import shutil
from dataclasses import asdict, dataclass, field
from pathlib import Path


_PAGE_FILE_RE = re.compile(r"^p(\d+)-(.+)\.md$", re.IGNORECASE)
_PAGE_ID_RE = re.compile(r"^P(\d+)$", re.IGNORECASE)

OBSOLETE_ARCHIVE_RELATIVE = "archive/obsolete-pages"


def is_obsolete_page_name(name: str) -> bool:
    lowered = name.lower()
    return (
        lowered.startswith("_obsolete")
        or lowered.startswith("obsolete")
        or ".obsolete." in lowered
    )


def is_active_page_file(path: Path) -> bool:
    if path.suffix.lower() != ".md":
        return False
    name = path.name
    if name.lower() == "readme.md":
        return False
    if is_obsolete_page_name(name):
        return False
    return True


def active_page_files(project: Path) -> list[Path]:
    pages_dir = project / "pages"
    if not pages_dir.is_dir():
        return []
    return sorted(path for path in pages_dir.glob("*.md") if is_active_page_file(path))


def parse_page_filename(path: Path) -> tuple[int, str] | None:
    match = _PAGE_FILE_RE.match(path.name)
    if not match:
        return None
    return int(match.group(1)), match.group(2).strip()


def load_page_contracts(project: Path) -> list[dict]:
    path = project / "contracts/page-contracts.json"
    if not path.is_file():
        return []
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return []
    pages = payload.get("pages", []) if isinstance(payload, dict) else []
    return [item for item in pages if isinstance(item, dict)]


@dataclass(slots=True)
class PagesIssue:
    level: str
    code: str
    message: str
    path: str = ""


@dataclass(slots=True)
class PagesAudit:
    active_count: int = 0
    contract_count: int = 0
    obsolete_count: int = 0
    obsolete_in_pages_count: int = 0
    issues: list[PagesIssue] = field(default_factory=list)

    @property
    def passed(self) -> bool:
        return not any(issue.level == "ERROR" for issue in self.issues)

    def to_dict(self) -> dict:
        data = asdict(self)
        data["passed"] = self.passed
        return data


def audit_pages(project: Path) -> PagesAudit:
    pages_dir = project / "pages"
    obsolete_in_pages: list[Path] = []
    if pages_dir.is_dir():
        obsolete_in_pages = [
            path
            for path in pages_dir.glob("*.md")
            if is_obsolete_page_name(path.name)
        ]
    archive_dir = project / OBSOLETE_ARCHIVE_RELATIVE
    archived = list(archive_dir.glob("*.md")) if archive_dir.is_dir() else []
    active = active_page_files(project)
    contracts = load_page_contracts(project)
    issues: list[PagesIssue] = []

    for path in obsolete_in_pages:
        relative = str(path.relative_to(project)).replace("\\", "/")
        issues.append(
            PagesIssue(
                "WARN",
                "obsolete-page-in-pages-dir",
                f"废稿仍在 pages/：{path.name}；应迁入 {OBSOLETE_ARCHIVE_RELATIVE}/"
                f"（可用 retire-page）",
                relative,
            )
        )

    contract_by_number: dict[int, dict] = {}
    for item in contracts:
        page_id = item.get("page_id")
        if not isinstance(page_id, str):
            continue
        match = _PAGE_ID_RE.match(page_id.strip())
        if not match:
            issues.append(
                PagesIssue(
                    "ERROR",
                    "invalid-page-id",
                    f"页面合同 page_id 非法：{page_id!r}",
                )
            )
            continue
        number = int(match.group(1))
        if number in contract_by_number:
            issues.append(
                PagesIssue(
                    "ERROR",
                    "duplicate-contract-page",
                    f"页面合同页码重复：P{number:02d}",
                )
            )
            continue
        contract_by_number[number] = item

    matched_numbers: set[int] = set()
    for path in active:
        relative = str(path.relative_to(project)).replace("\\", "/")
        parsed = parse_page_filename(path)
        if parsed is None:
            issues.append(
                PagesIssue(
                    "ERROR",
                    "invalid-page-filename",
                    f"活动页面文件名不符合 pNN-标题.md：{path.name}",
                    relative,
                )
            )
            continue
        number, title = parsed
        contract = contract_by_number.get(number)
        if contract is None:
            issues.append(
                PagesIssue(
                    "ERROR",
                    "orphan-page-file",
                    f"活动页面不在 page-contracts 中：{path.name}",
                    relative,
                )
            )
            continue
        matched_numbers.add(number)
        expected_title = str(contract.get("title") or "").strip()
        if expected_title and title != expected_title:
            issues.append(
                PagesIssue(
                    "ERROR",
                    "page-title-drift",
                    f"第{number}页文件标题“{title}”与合同标题“{expected_title}”不一致",
                    relative,
                )
            )

    for number, contract in sorted(contract_by_number.items()):
        if number in matched_numbers:
            continue
        expected_title = str(contract.get("title") or "").strip() or f"P{number:02d}"
        expected_name = f"p{number:02d}-{expected_title}.md"
        issues.append(
            PagesIssue(
                "WARN",
                "missing-page-file",
                f"页面合同有 {contract.get('page_id', f'P{number:02d}')}（{expected_title}），尚无活动文件 {expected_name}",
            )
        )

    return PagesAudit(
        active_count=len(active),
        contract_count=len(contract_by_number),
        obsolete_count=len(obsolete_in_pages) + len(archived),
        obsolete_in_pages_count=len(obsolete_in_pages),
        issues=issues,
    )


def retire_page_file(project: Path, name_or_stem: str) -> Path:
    """Move a page draft under pages/ into archive/obsolete-pages/."""
    pages_dir = project / "pages"
    if not pages_dir.is_dir():
        raise FileNotFoundError(f"项目无 pages 目录：{project}")
    needle = name_or_stem.strip()
    if needle.lower().endswith(".md"):
        candidates = [pages_dir / Path(needle).name]
    else:
        candidates = sorted(
            path
            for path in pages_dir.glob("*.md")
            if needle.lower() in path.stem.lower() or path.name.lower() == needle.lower()
        )
    existing = [path for path in candidates if path.is_file()]
    if not existing:
        raise FileNotFoundError(f"pages/ 中未找到可废止文件：{name_or_stem}")
    if len(existing) > 1:
        names = "、".join(path.name for path in existing)
        raise ValueError(f"匹配到多个页面，请指定确切文件名：{names}")
    source = existing[0]
    archive = project / OBSOLETE_ARCHIVE_RELATIVE
    archive.mkdir(parents=True, exist_ok=True)
    dest_name = source.name
    if not is_obsolete_page_name(dest_name):
        dest_name = f"_obsolete-{dest_name}"
    destination = archive / dest_name
    if destination.exists():
        raise FileExistsError(f"目标已存在：{destination}")
    shutil.move(str(source), str(destination))
    return destination


def render_pages_audit(audit: PagesAudit) -> str:
    lines = [
        "# 页面文件与合同对齐检查",
        "",
        f"- 活动页面：{audit.active_count}",
        f"- 页面合同：{audit.contract_count}",
        f"- 废止页面合计：{audit.obsolete_count}",
        f"- 仍滞留 pages/ 的废稿：{audit.obsolete_in_pages_count}",
        f"- 结果：{'PASS' if audit.passed else 'FAIL'}",
        "",
    ]
    if not audit.issues:
        lines.append("无问题。")
        return "\n".join(lines) + "\n"
    lines.append("## 问题")
    for issue in audit.issues:
        location = f"（{issue.path}）" if issue.path else ""
        lines.append(f"- [{issue.level}] `{issue.code}` {issue.message}{location}")
    return "\n".join(lines) + "\n"
