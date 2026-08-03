"""Prepare and audit human-authored chapter structure reviews."""

from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from cyberppt.script_quality_contract import parse_script_markdown, text_similarity

SCHEMA = "cyberppt.chapter_review_manifest.v1"
REQUIRED_HEADINGS = ("## 总判", "## 章内推进链", "## 跨页优化", "## 建议落地顺序", "## 消费状态")


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().lower()


def _read_json(path: Path) -> dict[str, Any]:
    if not path.is_file():
        raise FileNotFoundError(path)
    payload = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(payload, dict):
        raise ValueError(f"JSON root must be an object: {path}")
    return payload


def _write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _paths(project: Path, level: str) -> tuple[Path, Path, Path]:
    if level == "outline":
        base = project / "workbench/stages/01-analysis"
        return base / "outline.json", base / "chapter-review-input.json", base / "chapter-review-audit.json"
    if level == "script":
        base = project / "workbench/scripts/audits"
        audit = _read_json(base / "script-audit.json")
        source = Path(str(audit.get("input") or "")).expanduser().resolve()
        if not source.is_file():
            raise FileNotFoundError(f"current script-audit input does not exist: {source}")
        return source, base / "chapter-review-input.json", base / "chapter-review-audit.json"
    raise ValueError("level must be 'outline' or 'script'")


def _reviewable_pages(outline: dict[str, Any]) -> list[dict[str, Any]]:
    pages = outline.get("pages")
    if not isinstance(pages, list):
        raise ValueError("outline.pages must be an array")
    return [page for page in pages if isinstance(page, dict) and page.get("page_id") and page.get("chapter_id") and (page.get("page_mission") or page.get("core_message"))]


def _chapters(outline: dict[str, Any]) -> list[dict[str, Any]]:
    titles = {str(page["chapter_id"]): str(page.get("title") or page["chapter_id"]) for page in outline.get("pages", []) if isinstance(page, dict) and page.get("chapter_id") and page.get("page_type") == "chapter"}
    grouped: dict[str, list[dict[str, Any]]] = {}
    for page in _reviewable_pages(outline):
        grouped.setdefault(str(page["chapter_id"]), []).append(page)
    fields = ("page_id", "sequence", "title", "page_mission", "audience_question", "must_not_include", "split_risk", "split_risk_reason", "core_message", "content_units", "content_relations", "source_refs", "page_necessity")
    return [{"chapter_id": chapter_id, "title": titles.get(chapter_id, chapter_id), "pages": [{key: page.get(key) for key in fields if key in page} for page in pages]} for chapter_id, pages in grouped.items()]


def _compact_overlap(left: str, right: str, size: int = 4) -> float:
    def shingles(value: str) -> set[str]:
        compact = re.sub(r"[^0-9A-Za-z\u4e00-\u9fff]", "", value or "")
        return {
            compact[index : index + size]
            for index in range(max(0, len(compact) - size + 1))
            if compact[index : index + size]
        }

    source = shingles(left)
    if not source:
        return 1.0
    return len(source & shingles(right)) / len(source)


def _actual_script_structure_issues(
    source: Path,
    outline: dict[str, Any],
) -> list[dict[str, str]]:
    """Audit the authored page body, not just review-file bookkeeping."""

    try:
        script = parse_script_markdown(source.read_text(encoding="utf-8-sig"))
    except (OSError, ValueError) as exc:
        return [{"code": "SCRIPT_PARSE_FAILED", "message": str(exc)}]
    outline_pages = {
        str(item.get("page_id")): item
        for item in outline.get("pages", [])
        if isinstance(item, dict) and item.get("page_id")
    }
    issues: list[dict[str, str]] = []
    pages_by_chapter: dict[str, list[Any]] = {}
    for page in script.pages:
        contract = outline_pages.get(page.page_id)
        if not contract or contract.get("page_type") != "content":
            continue
        chapter_id = str(contract.get("chapter_id") or "")
        pages_by_chapter.setdefault(chapter_id, []).append(page)
        if not page.full_prose.strip():
            issues.append({"code": "SCRIPT_PROSE_MISSING", "message": f"{page.page_id} has no 完整文字稿"})
        if not page.onscreen_text.strip():
            issues.append({"code": "SCRIPT_ONSCREEN_MISSING", "message": f"{page.page_id} has no 上屏文字"})
        if not page.visual_structure.strip():
            issues.append({"code": "SCRIPT_VISUAL_STRUCTURE_MISSING", "message": f"{page.page_id} has no 视觉结构"})
        units = contract.get("content_units") or []
        evidence_contract = contract.get("source_evidence_contract") or {}
        evidence_units = {
            tuple(str(item) for item in unit.get("source_refs") or []): unit
            for unit in evidence_contract.get("units", [])
            if isinstance(unit, dict)
        }
        authored = "\n".join(
            (page.full_prose, page.onscreen_text, page.speaker_notes, page.visual_structure)
        )
        for unit in units:
            if not isinstance(unit, dict) or str(unit.get("role") or "") == "boundary":
                continue
            statement = str(unit.get("statement") or "")
            evidence_unit = evidence_units.get(
                tuple(str(item) for item in unit.get("source_refs") or []),
                {},
            )
            source_statements = [
                str(item)
                for item in (
                    unit.get("source_statements")
                    or evidence_unit.get("source_statements")
                    or []
                )
                if str(item).strip()
            ]
            if not statement and not source_statements:
                issues.append({"code": "OUTLINE_CONTENT_UNIT_EMPTY", "message": f"{page.page_id} has an empty content unit"})
                continue
            if max(
                [_compact_overlap(statement, authored)]
                + [_compact_overlap(item, authored) for item in source_statements]
                + [0.0]
            ) < (0.10 if unit.get("role") == "primary" else 0.04):
                refs = "、".join(str(item) for item in unit.get("source_refs") or [])
                issues.append({
                    "code": "SCRIPT_CONTENT_UNIT_NOT_CONSUMED",
                    "message": f"{page.page_id} does not express content unit {refs or statement[:24]}",
                })
    # Adjacent pages may share vocabulary, but cannot carry the same page
    # judgment as their main contribution.  This catches repeated relation
    # explanations that a Source-ID coverage check cannot see.
    for chapter_id, pages in pages_by_chapter.items():
        ordered = sorted(pages, key=lambda item: item.sequence)
        for left, right in zip(ordered, ordered[1:]):
            similarity = text_similarity(left.main_message, right.main_message)
            if similarity >= 0.82:
                issues.append({
                    "code": "CROSS_PAGE_MAIN_MESSAGE_DUPLICATED",
                    "message": f"{left.page_id}/{right.page_id} main judgments are too similar ({similarity:.3f})",
                })
    return issues


def prepare_chapter_review_input(project: Path, level: str = "outline") -> Path:
    project = project.expanduser().resolve()
    if not project.is_dir():
        raise FileNotFoundError(f"project does not exist: {project}")
    source, output, _ = _paths(project, level)
    outline_path = project / "workbench/stages/01-analysis/outline.json"
    outline = _read_json(outline_path)
    chapters = _chapters(outline)
    _write_json(output, {"schema": "cyberppt.chapter_review_input.v1", "level": level, "input_path": str(source), "input_sha256": _sha256(source), "outline_path": str(outline_path), "outline_sha256": _sha256(outline_path), "document_semantics": outline.get("document_semantics", {}), "narrative_thesis": outline.get("narrative_thesis", ""), "chapters": chapters, "required_markdown_headings": list(REQUIRED_HEADINGS), "prepared_at": _utc_now()})
    review_dir = project / "review"
    review_dir.mkdir(parents=True, exist_ok=True)
    covered_chapters: set[str] = set()
    existing_manifest = review_dir / "chapter-review-manifest.json"
    if existing_manifest.is_file():
        try:
            manifest = _read_json(existing_manifest)
            if manifest.get("level") == level:
                for entry in manifest.get("reviews", []):
                    if isinstance(entry, dict):
                        covered_chapters.update(str(value) for value in entry.get("chapter_ids", []))
        except (json.JSONDecodeError, ValueError):
            pass
    for chapter in chapters:
        if str(chapter["chapter_id"]) in covered_chapters:
            continue
        match = re.search(r"(\d+)", str(chapter["chapter_id"]))
        prefix = f"c{int(match.group(1)):02d}" if match else str(chapter["chapter_id"])
        skeleton = review_dir / f"{prefix}-{level}-structure-review.md"
        if not skeleton.exists():
            page_ids = "、".join(str(page["page_id"]) for page in chapter["pages"])
            skeleton.write_text(f"# {chapter['title']}结构审阅\n\n- 审阅层级：{level}\n- 页面范围：{page_ids}\n\n## 总判\n\n待审阅。\n\n## 章内推进链\n\n待审阅。\n\n## 跨页优化\n\n待审阅。\n\n## 建议落地顺序\n\n待审阅。\n\n## 消费状态\n\n- [ ] 尚未消费\n", encoding="utf-8")
    return output


def run_chapter_review_audit(project: Path, level: str = "outline") -> tuple[int, dict[str, Any]]:
    project = project.expanduser().resolve()
    source, prepared_path, audit_path = _paths(project, level)
    prepared = _read_json(prepared_path)
    manifest_path = project / "review/chapter-review-manifest.json"
    manifest = _read_json(manifest_path)
    issues: list[dict[str, str]] = []
    def issue(code: str, message: str) -> None: issues.append({"code": code, "message": message})
    if manifest.get("schema") != SCHEMA: issue("MANIFEST_SCHEMA_INVALID", f"expected {SCHEMA}")
    if manifest.get("level") != level: issue("REVIEW_LEVEL_MISMATCH", f"manifest level must be {level}")
    current_hash = _sha256(source)
    if str(prepared.get("input_sha256") or "").lower() != current_hash: issue("PREPARED_INPUT_STALE", "prepared review input does not match the current artifact")
    if str(manifest.get("input_sha256") or "").lower() != current_hash: issue("REVIEW_INPUT_STALE", "review manifest does not match the current artifact")
    expected = {str(ch["chapter_id"]): {str(page["page_id"]) for page in ch.get("pages", [])} for ch in prepared.get("chapters", []) if isinstance(ch, dict)}
    covered_chapters: set[str] = set(); covered_pages: set[str] = set()
    reviews = manifest.get("reviews")
    if not isinstance(reviews, list) or not reviews: issue("REVIEWS_MISSING", "manifest.reviews must contain at least one review"); reviews = []
    for entry in reviews:
        if not isinstance(entry, dict): issue("REVIEW_ENTRY_INVALID", "each review entry must be an object"); continue
        review_path = project / str(entry.get("path") or "")
        if not review_path.is_file(): issue("REVIEW_MARKDOWN_MISSING", f"missing review Markdown: {review_path}")
        else:
            text = review_path.read_text(encoding="utf-8-sig")
            for heading in REQUIRED_HEADINGS:
                if not re.search(rf"^{re.escape(heading)}\s*$", text, flags=re.M): issue("REVIEW_SECTION_MISSING", f"{review_path.name} missing {heading}")
        if str(entry.get("status") or "") not in {"passed", "waived"}: issue("REVIEW_STATUS_INCOMPLETE", f"{review_path.name} status must be passed or waived")
        chapters = {str(value) for value in entry.get("chapter_ids", [])}; pages = {str(value) for value in entry.get("page_ids", [])}
        if len(chapters) != 1:
            issue(
                "CHAPTER_REVIEW_NOT_INDIVIDUAL",
                f"{review_path.name} must review exactly one chapter; got {sorted(chapters)}",
            )
        covered_chapters.update(chapters)
        duplicate = covered_pages.intersection(pages)
        if duplicate: issue("PAGE_REVIEW_DUPLICATED", f"pages covered more than once: {sorted(duplicate)}")
        covered_pages.update(pages)
        if entry.get("high_priority_open", []): issue("HIGH_PRIORITY_NOT_CONSUMED", f"{review_path.name} has open high-priority items")
        consume = entry.get("consumption_path")
        if consume and not (project / str(consume)).is_file(): issue("CONSUMPTION_RECORD_MISSING", f"missing consumption record: {consume}")
    expected_pages = set().union(*expected.values()) if expected else set()
    if covered_chapters != set(expected): issue("CHAPTER_COVERAGE_INCOMPLETE", f"expected {sorted(expected)}, got {sorted(covered_chapters)}")
    if covered_pages != expected_pages: issue("PAGE_COVERAGE_INCOMPLETE", f"missing={sorted(expected_pages-covered_pages)}, extra={sorted(covered_pages-expected_pages)}")
    if level == "script":
        outline = _read_json(project / "workbench/stages/01-analysis/outline.json")
        for structural_issue in _actual_script_structure_issues(source, outline):
            issue(structural_issue["code"], structural_issue["message"])
    status = "passed" if not issues else "rewrite_required"
    report = {"schema": "cyberppt.chapter_review_audit.v1", "level": level, "status": status, "input": str(source), "input_sha256": current_hash, "prepared_input": str(prepared_path), "manifest": str(manifest_path), "chapter_count": len(expected), "page_count": len(expected_pages), "issues": issues, "audited_at": _utc_now()}
    _write_json(audit_path, report)
    return (0 if status == "passed" else 4), report
