from __future__ import annotations

import re
from difflib import SequenceMatcher

from .config import AuditConfig
from .models import ScriptSlide, SpeakerNotesAudit

_NUMBER_RE = re.compile(r"(?<![A-Za-z0-9])\d+(?:[.,]\d+)*(?![A-Za-z0-9])")
_PAGE_DIRECTION_RE = re.compile(r"(?:上|本|下|前一|后一|上一|下一|这)页")
_NOT_BUT_RE = re.compile(r"(?:不是|并非).{0,120}?而是", re.DOTALL)
# 讲解方法 / 制作者口吻：应写演讲汇报语气，不谈怎么讲、怎么排版
_METHOD_META_PHRASES = (
    "上屏摊开",
    "辅助信息里",
    "辅助区里",
    "对照写在",
    "按这个结构",
    "按逻辑顺序看",
    "这里按",
    "材料把",
    "记住问题结构",
    "请记下来",
    "写成升级",
    "不要写成",
    "不能写成",
    "第一层，",
    "第二层，",
    "第三层，",
    "对照材料口径",
    "不能收成笼统",
    "要上屏",
    "页面上",
    "模块标题",
)


def _numbers(text: str) -> set[str]:
    return {match.group(0).replace(",", "") for match in _NUMBER_RE.finditer(text)}


def _compact(text: str) -> str:
    return re.sub(r"[\s\W_]+", "", text, flags=re.UNICODE)


def _bigrams(text: str) -> set[str]:
    return {text[index:index + 2] for index in range(max(0, len(text) - 1))}


def _repetition_ratio(onscreen: str, notes: str) -> float:
    left, right = _compact(onscreen), _compact(notes)
    if not left or not right:
        return 0.0
    sequence_ratio = SequenceMatcher(None, left, right).ratio()
    left_pairs, right_pairs = _bigrams(left), _bigrams(right)
    overlap_ratio = len(left_pairs & right_pairs) / len(left_pairs) if left_pairs else 0.0
    return max(sequence_ratio, overlap_ratio)


def _is_simple_page(slide: ScriptSlide, config: AuditConfig) -> bool:
    value = f"{slide.page_type} {slide.title}".lower().replace(" ", "")
    return any(page_type.lower().replace(" ", "") in value for page_type in config.speaker_notes_simple_page_types)


def audit_speaker_notes(source_text: str, slides: list[ScriptSlide], config: AuditConfig) -> SpeakerNotesAudit:
    substantive = [slide for slide in slides if not _is_simple_page(slide, config)]
    present = [slide for slide in substantive if slide.has_speaker_notes]
    source_numbers = _numbers(source_text)
    note_numbers = {number for slide in slides for number in _numbers(slide.speaker_notes_text)}
    target_seconds = int(round(config.target_duration_minutes * 60)) if config.target_duration_minutes is not None else None
    total_seconds = sum(slide.speaker_notes_seconds or 0 for slide in slides)
    out_of_range = bool(target_seconds and abs(total_seconds - target_seconds) > target_seconds * config.duration_tolerance_ratio)
    audit = SpeakerNotesAudit(
        slide_count=len(slides), substantive_slide_count=len(substantive), notes_present_count=len(present),
        total_duration_seconds=total_seconds, target_duration_seconds=target_seconds,
        duration_out_of_range=out_of_range,
        unverified_numbers=sorted(note_numbers - source_numbers, key=lambda value: (len(value), value)),
        notes=[
            "讲解词按自然演讲汇报语气处理，依靠观点、因果和问题演进衔接，不使用页面指示词。",
            "核心讲解说业务判断与依据，不谈讲解方法、版式操作或制作者口吻。",
            "讲解词补充图表解读、业务含义、判断依据和行动建议，不复述标题及上屏文字。",
            "封面、目录、章节过渡和封底等简化页可不设置完整讲解词。",
        ],
    )
    if not config.speaker_notes_enabled:
        return audit
    last_substantive_number = substantive[-1].number if substantive else None
    for slide in substantive:
        if config.speaker_notes_required_for_substantive and not slide.has_speaker_notes:
            audit.missing_notes.append(slide.number)
            continue
        if not slide.has_speaker_notes:
            continue
        if not slide.speaker_opening: audit.missing_opening.append(slide.number)
        if not slide.speaker_explanation: audit.missing_core_explanation.append(slide.number)
        if not slide.speaker_emphasis: audit.missing_emphasis.append(slide.number)
        if not slide.speaker_boundary: audit.missing_boundary.append(slide.number)
        if slide.number != last_substantive_number and not slide.speaker_transition: audit.missing_transition.append(slide.number)
        if slide.speaker_notes_seconds is None: audit.missing_duration.append(slide.number)
        if len(_compact(slide.speaker_notes_text)) < config.speaker_notes_min_chars: audit.short_notes.append(slide.number)
        if _repetition_ratio(slide.body, slide.speaker_notes_text) > config.speaker_notes_max_repetition: audit.high_repetition_slides.append(slide.number)
        if _PAGE_DIRECTION_RE.search(slide.speaker_notes_text):
            audit.page_direction_slides.append(slide.number)
        if _NOT_BUT_RE.search(slide.speaker_notes_text):
            audit.not_but_slides.append(slide.number)
        if any(phrase in slide.speaker_notes_text for phrase in _METHOD_META_PHRASES):
            audit.method_meta_slides.append(slide.number)
    return audit
