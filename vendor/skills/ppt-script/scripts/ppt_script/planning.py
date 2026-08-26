from __future__ import annotations

import re
from collections import Counter
from collections.abc import Iterable

from .models import ChapterPlan, PlannedSlide, PlanningAudit, PlanningIssue, PresentationPlan

_SOURCE_ID_RE = re.compile(r"\bS\d{3,4}\b", re.IGNORECASE)
_CHAPTER_RE = re.compile(
    r"^\s*#{1,6}\s*(?:第\s*)?(?P<num>[一二三四五六七八九十百\d]+)\s*章\s*(?:[｜|:：—\-]\s*)?(?P<title>.*?)\s*$"
)
_SLIDE_RE = re.compile(
    r"^\s*#{1,6}\s*(?:第\s*)?(?P<num>\d+)\s*(?:页|頁|slide)\s*(?:[｜|:：—\-]\s*)?(?P<title>.*?)\s*$",
    re.IGNORECASE,
)
_TEMPLATE_SECTION_RE = re.compile(r"^\s*#{1,6}\s*全篇模板页(?:[｜|:：—\-].*)?$")
_FIELD_RE = re.compile(r"^\s*(?:[-*]\s*)?(?P<label>[^:：]{2,16})\s*[:：]\s*(?P<value>.*?)\s*$")

_DECK_FIELDS = {
    "汇报目标": "goal",
    "汇报对象": "audience",
    "决策对象": "audience",
    "核心结论": "core_conclusion",
    "主线": "storyline",
    "故事线": "storyline",
}
_CHAPTER_FIELDS = {
    "章节使命": "mission",
    "章节核心结论": "conclusion",
    "输入依据": "source_ids",
    "材料依据": "source_ids",
    "页面范围": "page_range",
    "承接前章": "previous_link",
    "引出后章": "next_link",
    "内容边界": "boundary",
}
_SLIDE_FIELDS = {
    "页面性质": "page_nature",
    "页面使命": "mission",
    "页面职能": "mission",
    "核心结论": "key_message",
    "页面结论": "key_message",
    "材料依据ID": "source_ids",
    "材料依据": "source_ids",
    "引用Source ID": "source_ids",
    "页面类型": "page_type",
    "页面形态": "visual_form",
    "图形结构": "visual_form",
    "与前页关系": "previous_relation",
    "与后页关系": "next_relation",
    "页面必要性": "necessity",
}

# Formal internal-reporting: no consulting-style conclusion-first opening.
_OPENING_CLAIM_TITLE_MARKERS = (
    "升级方向",
    "为什么升级",
    "为何升级",
    "任务为什么升级",
    "能力升级方向",
    "研判能力升级",
    "总体方法论",
)
_OPENING_CLAIM_BODY_PATTERNS = (
    re.compile(r"必须升级"),
    re.compile(r"需要升级"),
    re.compile(r"任务升级"),
    re.compile(r"为任务升级"),
    re.compile(r"四个升级维度"),
    re.compile(r"四维升级"),
    re.compile(r"汇聚至.?研判复杂度"),
    re.compile(r"汇聚至.+复杂度"),
    re.compile(r"研判工作要升级"),
    re.compile(r"提升研判颗粒度"),
    re.compile(r"必须提升"),
)
_OPENING_FORBIDDEN_PAGE_TYPES = frozenset({"方向页", "主张页", "方法论页"})
_FACTLIKE_TITLE_RE = re.compile(r"形势|规模|结构变化|结构与规模")
_CHAPTER1_UPGRADE_FRAME_RE = re.compile(r"升级基础|能力升级基础")


def _opening_content_slide(plan: PresentationPlan) -> PlannedSlide | None:
    slides = [
        slide
        for chapter in plan.chapters
        for slide in chapter.slides
        if (slide.page_nature or "") != "模板页"
    ]
    slides.extend(
        slide for slide in plan.orphan_slides if (slide.page_nature or "") != "模板页"
    )
    if not slides:
        return None
    return sorted(slides, key=lambda item: item.number)[0]


def _audit_no_conclusion_first(plan: PresentationPlan, issues: list[PlanningIssue]) -> None:
    if plan.chapters:
        chapter = plan.chapters[0]
        identifier = f"第{chapter.number}章｜{chapter.title}"
        if _CHAPTER1_UPGRADE_FRAME_RE.search(chapter.title or ""):
            issues.append(
                PlanningIssue(
                    "chapter",
                    identifier,
                    "正式内部汇报第一章不得以“升级基础”等预判章题开篇；应先陈述形势/事实与工作条件。",
                )
            )

    opening = _opening_content_slide(plan)
    if opening is None:
        return
    identifier = f"第{opening.number}页｜{opening.title}"
    title = opening.title or ""
    page_type = (opening.page_type or "").strip()
    body = "\n".join(
        part
        for part in (
            opening.mission,
            opening.key_message,
            opening.visual_form,
            opening.necessity,
            opening.previous_relation,
            opening.next_relation,
        )
        if part
    )

    if page_type in _OPENING_FORBIDDEN_PAGE_TYPES:
        issues.append(
            PlanningIssue(
                "slide",
                identifier,
                f"开篇页类型不得为“{page_type}”（结论/主张先行）；应使用形势数据页等事实页。",
            )
        )
    for marker in _OPENING_CLAIM_TITLE_MARKERS:
        if marker in title:
            issues.append(
                PlanningIssue(
                    "slide",
                    identifier,
                    f"开篇页标题含结论先行表述“{marker}”，正式内部汇报禁止咨询式开篇主张页。",
                )
            )
            break
    claim_hit = None
    for pattern in _OPENING_CLAIM_BODY_PATTERNS:
        match = pattern.search(body) or pattern.search(title)
        if match:
            claim_hit = match.group(0)
            break
    if claim_hit:
        if _FACTLIKE_TITLE_RE.search(title) and any(
            pattern.search(body) for pattern in _OPENING_CLAIM_BODY_PATTERNS
        ):
            issues.append(
                PlanningIssue(
                    "slide",
                    identifier,
                    f"开篇页标题呈事实态，但使命/结论/形态仍含“{claim_hit}”，属于换皮未改正。",
                )
            )
        else:
            issues.append(
                PlanningIssue(
                    "slide",
                    identifier,
                    f"开篇页正文/标题含结论先行表述“{claim_hit}”；换标题不算改正。",
                )
            )


def extract_source_ids(text: str) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for match in _SOURCE_ID_RE.finditer(text or ""):
        value = match.group(0).upper()
        if value not in seen:
            seen.add(value)
            result.append(value)
    return result


def _chinese_number(value: str) -> int:
    if value.isdigit():
        return int(value)
    digits = {"零": 0, "一": 1, "二": 2, "三": 3, "四": 4, "五": 5, "六": 6, "七": 7, "八": 8, "九": 9}
    if value == "十":
        return 10
    if "百" in value:
        left, _, right = value.partition("百")
        return digits.get(left, 1) * 100 + (_chinese_number(right) if right else 0)
    if "十" in value:
        left, _, right = value.partition("十")
        return digits.get(left, 1) * 10 + digits.get(right, 0)
    total = 0
    for char in value:
        total = total * 10 + digits.get(char, 0)
    return total


def _split_row(line: str) -> list[str]:
    return [cell.strip() for cell in line.strip().strip("|").split("|")]


def _append_table_slides(lines: list[str], plan: PresentationPlan) -> None:
    current_chapter: ChapterPlan | None = None
    header: list[str] | None = None
    for line in lines:
        chapter_match = _CHAPTER_RE.match(line)
        if chapter_match:
            number = _chinese_number(chapter_match.group("num"))
            current_chapter = next((chapter for chapter in plan.chapters if chapter.number == number), None)
            header = None
            continue
        if not line.strip().startswith("|"):
            header = None
            continue
        cells = _split_row(line)
        if "页码" in cells and "页面标题" in cells:
            header = cells
            continue
        if header is None or all(re.fullmatch(r":?-+:?", cell) for cell in cells):
            continue
        if len(cells) < len(header):
            cells.extend([""] * (len(header) - len(cells)))
        data = dict(zip(header, cells))
        if not re.fullmatch(r"\d+", data.get("页码", "")):
            continue
        number = int(data["页码"])
        existing = [slide for chapter in plan.chapters for slide in chapter.slides]
        existing.extend(plan.orphan_slides)
        if any(slide.number == number for slide in existing):
            continue
        transition = data.get("前后页承接", "")
        slide = PlannedSlide(
            number=number,
            title=data.get("页面标题", ""),
            chapter_number=current_chapter.number if current_chapter else None,
            chapter_title=current_chapter.title if current_chapter else "",
            mission=data.get("页面职能", ""),
            key_message=data.get("副标题或主判断", ""),
            source_ids=extract_source_ids(data.get("材料依据ID", "")),
            page_type=data.get("页面类型", ""),
            visual_form=data.get("推荐主语义图类型", ""),
            previous_relation=transition,
            next_relation=transition,
            necessity=data.get("页面职能", ""),
            raw=line,
        )
        if current_chapter:
            current_chapter.slides.append(slide)
        else:
            plan.orphan_slides.append(slide)


def parse_plan(text: str) -> PresentationPlan:
    lines = text.replace("\r\n", "\n").splitlines()
    plan = PresentationPlan()
    current_chapter: ChapterPlan | None = None
    current_slide: PlannedSlide | None = None
    chapter_lines: list[str] = []
    slide_lines: list[str] = []

    def finish_slide() -> None:
        nonlocal slide_lines
        if current_slide is not None:
            current_slide.raw = "\n".join(slide_lines).strip()
        slide_lines = []

    def finish_chapter() -> None:
        nonlocal chapter_lines
        finish_slide()
        if current_chapter is not None:
            current_chapter.raw = "\n".join(chapter_lines).strip()
        chapter_lines = []

    for raw_line in lines:
        line = raw_line.rstrip()
        if _TEMPLATE_SECTION_RE.match(line):
            finish_chapter()
            current_chapter = None
            current_slide = None
            continue
        chapter_match = _CHAPTER_RE.match(line)
        if chapter_match:
            finish_chapter()
            current_chapter = ChapterPlan(
                number=_chinese_number(chapter_match.group("num")),
                title=chapter_match.group("title").strip().strip("|｜:：—- "),
            )
            plan.chapters.append(current_chapter)
            current_slide = None
            chapter_lines = [line]
            continue
        slide_match = _SLIDE_RE.match(line)
        if slide_match:
            finish_slide()
            current_slide = PlannedSlide(
                number=int(slide_match.group("num")),
                title=slide_match.group("title").strip().strip("|｜:：—- "),
                chapter_number=current_chapter.number if current_chapter else None,
                chapter_title=current_chapter.title if current_chapter else "",
            )
            if current_chapter:
                current_chapter.slides.append(current_slide)
                chapter_lines.append(line)
            else:
                plan.orphan_slides.append(current_slide)
            slide_lines = [line]
            continue

        if current_slide is not None:
            slide_lines.append(line)
        if current_chapter is not None:
            chapter_lines.append(line)

        field_match = _FIELD_RE.match(line)
        if not field_match:
            continue
        label = field_match.group("label").strip()
        value = field_match.group("value").strip()
        if current_slide is not None and label in _SLIDE_FIELDS:
            attribute = _SLIDE_FIELDS[label]
            if attribute == "source_ids":
                current_slide.source_ids = extract_source_ids(value)
            else:
                setattr(current_slide, attribute, value)
            continue
        if current_chapter is not None and label in _CHAPTER_FIELDS:
            attribute = _CHAPTER_FIELDS[label]
            if attribute == "source_ids":
                current_chapter.source_ids = extract_source_ids(value)
            else:
                setattr(current_chapter, attribute, value)
            continue
        if current_chapter is None and label in _DECK_FIELDS:
            setattr(plan, _DECK_FIELDS[label], value)
    finish_chapter()
    _append_table_slides(lines, plan)
    return plan


def audit_plan_text(
    text: str,
    required_source_ids: Iterable[str] = (),
    *,
    formal_internal_reporting: bool = False,
) -> PlanningAudit:
    plan = parse_plan(text)
    issues: list[PlanningIssue] = []
    for attribute, label in (
        ("goal", "汇报目标"),
        ("audience", "汇报对象"),
        ("core_conclusion", "核心结论"),
        ("storyline", "主线"),
    ):
        if not getattr(plan, attribute):
            issues.append(PlanningIssue("deck", "整套汇报", f"缺少{label}"))
    if not plan.chapters:
        issues.append(PlanningIssue("deck", "整套汇报", "缺少章节规划"))

    for title, count in Counter(chapter.title for chapter in plan.chapters if chapter.title).items():
        if count > 1:
            issues.append(PlanningIssue("chapter", title, f"章节标题重复：{title}"))

    all_slides: list[PlannedSlide] = []
    for chapter in plan.chapters:
        identifier = f"第{chapter.number}章｜{chapter.title}"
        for attribute, label in (
            ("title", "章节名称"),
            ("mission", "章节使命"),
            ("conclusion", "章节核心结论"),
            ("source_ids", "输入依据"),
            ("page_range", "页面范围"),
            ("previous_link", "承接前章"),
            ("next_link", "引出后章"),
            ("boundary", "内容边界"),
        ):
            if not getattr(chapter, attribute):
                issues.append(PlanningIssue("chapter", identifier, f"缺少{label}"))
        if not chapter.slides:
            issues.append(PlanningIssue("chapter", identifier, "章节未规划页面"))
        page_ids = {source_id for slide in chapter.slides for source_id in slide.source_ids}
        for source_id in chapter.source_ids:
            if source_id not in page_ids:
                issues.append(PlanningIssue("chapter", identifier, f"章节输入依据{source_id}尚未分配到具体页面"))
        all_slides.extend(chapter.slides)

    for slide in plan.orphan_slides:
        if slide.page_nature != "模板页":
            issues.append(PlanningIssue("slide", f"第{slide.number}页｜{slide.title}", "内容页未归属任何章节"))
    all_slides.extend(plan.orphan_slides)

    for number, count in Counter(slide.number for slide in all_slides).items():
        if count > 1:
            issues.append(PlanningIssue("slide", f"第{number}页", f"页码重复：第{number}页"))

    for slide in all_slides:
        identifier = f"第{slide.number}页｜{slide.title}"
        for attribute, label in (
            ("page_nature", "页面性质"),
            ("title", "页面标题"),
            ("mission", "页面使命"),
            ("key_message", "页面核心结论"),
            ("source_ids", "材料依据"),
            ("page_type", "页面类型"),
            ("visual_form", "页面形态"),
            ("previous_relation", "与前页关系"),
            ("next_relation", "与后页关系"),
            ("necessity", "页面必要性"),
        ):
            if not getattr(slide, attribute):
                issues.append(PlanningIssue("slide", identifier, f"缺少{label}"))

    if formal_internal_reporting:
        _audit_no_conclusion_first(plan, issues)

    mapped = sorted({source_id for slide in all_slides for source_id in slide.source_ids})
    required = sorted({source_id.upper() for source_id in required_source_ids if source_id})
    unmapped = [source_id for source_id in required if source_id not in mapped]
    return PlanningAudit(
        chapter_count=len(plan.chapters),
        slide_count=len(all_slides),
        mapped_source_ids=mapped,
        unmapped_source_ids=unmapped,
        issues=issues,
    )
