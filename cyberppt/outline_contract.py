"""Solution-first outline contracts and deterministic Stage 01 audits."""

from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from cyberppt.argument_flow_contract import audit_argument_flow


SOLUTION_MATERIAL_TERMS = (
    "方案",
    "前期研究",
    "立项",
    "可研",
    "政府",
    "央企",
    "国企",
    "协会",
)
METHOD_TERMS = ("原则", "方法", "筛选", "评价维度", "选择标准")
REQUIRED_FIELDS = (
    "schema",
    "material_type",
    "audience",
    "architecture_mode",
    "architecture_reason",
    "source_section_weights",
    "pages",
    "retry",
)


@dataclass(frozen=True)
class AuditIssue:
    code: str
    message: str
    pages: tuple[str, ...] = ()
    retry_strategy: str = "rebuild_outline"

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


def load_outline(path: Path) -> dict[str, object]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8-sig"))
    except json.JSONDecodeError as exc:
        raise ValueError(f"invalid outline JSON: {exc.msg}") from exc
    if not isinstance(payload, dict):
        raise ValueError("outline root must be an object")
    for field in REQUIRED_FIELDS:
        if field not in payload:
            raise ValueError(f"missing required field: {field}")
    if payload.get("schema") != "cyberppt.outline.v1":
        raise ValueError("schema must be cyberppt.outline.v1")
    if not isinstance(payload.get("pages"), list):
        raise ValueError("pages must be an array")
    return payload


def _explicit_consulting_request(outline: dict[str, object]) -> bool:
    return outline.get("user_requested_architecture") is True


def _is_solution_material(material_type: object) -> bool:
    text = str(material_type or "").lower()
    return any(term.lower() in text for term in SOLUTION_MATERIAL_TERMS)


def resolve_architecture_mode(outline: dict[str, object]) -> str:
    requested = str(outline.get("architecture_mode") or "solution")
    if requested not in {"solution", "consulting"}:
        raise ValueError("architecture_mode must be solution or consulting")
    if requested == "consulting" and _is_solution_material(outline.get("material_type")):
        return "consulting" if _explicit_consulting_request(outline) else "solution"
    return requested


def _text(value: object) -> str:
    return re.sub(r"[\s，。；：、,.!?！？—_-]+", "", str(value or "")).casefold()


def _page_id(page: dict[str, object]) -> str:
    return str(page.get("page_id") or f"sequence-{page.get('sequence', '?')}")


def _template_issues(pages: list[dict[str, object]]) -> list[AuditIssue]:
    issues: list[AuditIssue] = []
    sequences = [page.get("sequence") for page in pages]
    if sequences and sequences != list(range(1, len(pages) + 1)):
        issues.append(
            AuditIssue(
                "TEMPLATE_PAGES_DETACHED",
                "All template and content pages must share one continuous ordered sequence.",
                tuple(_page_id(page) for page in pages),
                "continuous_page_sequence",
            )
        )
    chapter_seen: set[str] = set()
    for page in pages:
        page_type = page.get("page_type")
        chapter_id = str(page.get("chapter_id") or "")
        if page_type == "chapter":
            chapter_seen.add(chapter_id)
            content_fields = (
                page.get("main_message"),
                page.get("business_question"),
                page.get("visual_center"),
                page.get("modules"),
            )
            if any(content_fields):
                issues.append(
                    AuditIssue(
                        "CHAPTER_PAGE_HAS_CONTENT",
                        "Chapter pages may contain only the chapter number and title.",
                        (_page_id(page),),
                        "chapter_page_purity",
                    )
                )
        elif page_type == "content" and chapter_id and chapter_id not in chapter_seen:
            issues.append(
                AuditIssue(
                    "TEMPLATE_PAGES_DETACHED",
                    "Chapter content must follow its chapter page in the same sequence.",
                    (_page_id(page),),
                    "continuous_page_sequence",
                )
            )
    return issues


def _content_issues(pages: list[dict[str, object]]) -> list[AuditIssue]:
    issues: list[AuditIssue] = []
    content_pages = [page for page in pages if page.get("page_type") == "content"]
    for page in content_pages:
        if _text(page.get("title")) and _text(page.get("title")) == _text(page.get("main_message")):
            issues.append(
                AuditIssue(
                    "TITLE_CLAIM_COLLAPSED",
                    "Use a concise topic title and store the page judgment in main_message.",
                    (_page_id(page),),
                    "separate_title_and_main_message",
                )
            )
        modules = page.get("modules") if isinstance(page.get("modules"), list) else []
        method_role = any(isinstance(item, dict) and item.get("role") == "method" for item in modules)
        method_title = any(term in str(page.get("title") or "") for term in METHOD_TERMS)
        if not page.get("source_refs") and len(modules) <= 1 and (method_role or method_title):
            issues.append(
                AuditIssue(
                    "METHOD_PAGE_OVERPROMOTED",
                    "Method-only guidance without independent evidence should be a module, not a core page.",
                    (_page_id(page),),
                    "merge_method_into_business_page",
                )
            )

    for index in range(max(0, len(content_pages) - 2)):
        run = content_pages[index : index + 3]
        questions = {_text(page.get("business_question")) for page in run}
        visuals = {_text(page.get("visual_center")) for page in run}
        if "" not in questions and len(questions) == 1 and "" not in visuals and len(visuals) == 1:
            issues.append(
                AuditIssue(
                    "ATOMIC_SECTION_SPLIT",
                    "Adjacent pages repeat one business question and visual center; aggregate them into a complete analysis page.",
                    tuple(_page_id(page) for page in run),
                    "aggregate_by_business_question",
                )
            )
            break
    return issues


def _weight_issues(outline: dict[str, object], pages: list[dict[str, object]]) -> list[AuditIssue]:
    targets = outline.get("source_section_weights")
    if not isinstance(targets, dict) or not targets:
        return []
    actual: dict[str, float] = {}
    for page in pages:
        if page.get("page_type") != "content":
            continue
        chapter = str(page.get("chapter_id") or "")
        actual[chapter] = actual.get(chapter, 0.0) + float(page.get("source_weight") or 0.0)
    distorted = [chapter for chapter, target in targets.items() if float(target) - actual.get(str(chapter), 0.0) > 0.20]
    if not distorted:
        return []
    return [
        AuditIssue(
            "SOURCE_WEIGHT_DISTORTED",
            "Core source sections are underrepresented in the planned content pages.",
            tuple(str(item) for item in distorted),
            "rebalance_to_source_weight",
        )
    ]


def audit_outline(
    outline: dict[str, object],
    source_truth: dict[str, object] | None = None,
) -> list[AuditIssue]:
    issues: list[AuditIssue] = []
    if (
        outline.get("architecture_mode") == "consulting"
        and resolve_architecture_mode(outline) == "solution"
    ):
        issues.append(
            AuditIssue(
                "SOLUTION_ARCHITECTURE_REQUIRED",
                "Formal solution material defaults to solution architecture unless the user explicitly requests consulting structure.",
                retry_strategy="switch_to_solution_architecture",
            )
        )
    raw_pages = outline.get("pages")
    pages = [page for page in raw_pages if isinstance(page, dict)] if isinstance(raw_pages, list) else []
    issues.extend(_template_issues(pages))
    issues.extend(_content_issues(pages))
    issues.extend(_weight_issues(outline, pages))
    if outline.get("argument_contract_mode", "legacy") == "strict":
        if source_truth is None:
            issues.append(
                AuditIssue(
                    "SOURCE_TRUTH_REQUIRED",
                    "Strict outline audits require the authoritative Source Truth artifact.",
                    retry_strategy="reconcile_page_evidence_mapping",
                )
            )
        else:
            issues.extend(
                AuditIssue(
                    issue.code,
                    issue.message,
                    issue.pages,
                    issue.retry_strategy,
                )
                for issue in audit_argument_flow(outline, source_truth)
            )
    return sorted(issues, key=lambda item: ((item.pages or ("",))[0], item.code))


def retry_directive(issues: list[AuditIssue], previous_strategy: str = "") -> dict[str, object]:
    strategies = list(dict.fromkeys(issue.retry_strategy for issue in issues))
    if previous_strategy in strategies:
        strategies = [item for item in strategies if item != previous_strategy] + ["rebuild_from_source_roles"]
    return {
        "required": bool(issues),
        "issue_codes": list(dict.fromkeys(issue.code for issue in issues)),
        "strategies": strategies,
        "instruction": "Change planning direction, rewrite the outline, and submit the next numbered attempt.",
    }
