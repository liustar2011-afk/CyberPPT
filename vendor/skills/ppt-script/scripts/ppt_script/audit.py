from __future__ import annotations

import re

from .config import AuditConfig
from .coverage import semantic_coverage, slide_similarity
from .models import AuditReport, ComparisonReport, DensityIssue, DuplicatePair, ForbiddenHit
from .script_parser import parse_script
from .source_truth import parse_source_truth_map
from .speaker_notes import audit_speaker_notes

_NUMBER_RE = re.compile(r"(?<![A-Za-z0-9])\d+(?:[.,]\d+)*(?![A-Za-z0-9])")


def _numbers(text: str) -> set[str]:
    return {match.group(0).replace(",", "") for match in _NUMBER_RE.finditer(text)}


def _excerpt(text: str, phrase: str, radius: int = 30) -> str:
    position = text.find(phrase)
    if position < 0:
        return text[: radius * 2].replace("\n", " ")
    return text[max(0, position - radius) : position + len(phrase) + radius].replace("\n", " ")


def _unverified_numbers(source_text: str, slides) -> list[str]:
    source_numbers = _numbers(source_text)
    script_numbers: set[str] = set()
    for slide in slides:
        script_numbers.update(_numbers("\n".join((slide.mission, slide.key_message, slide.body))))
    return sorted(script_numbers - source_numbers, key=lambda value: (len(value), value))


def audit_script_text(
    source_text: str,
    source_truth_text: str,
    script_text: str,
    config: AuditConfig,
) -> AuditReport:
    source_map = parse_source_truth_map(source_truth_text)
    slides = parse_script(script_text)
    mapped = sorted({source_id for slide in slides for source_id in slide.source_ids})
    required = source_map.required_ids
    unmapped = [source_id for source_id in required if source_id not in mapped]
    forbidden_hits: list[ForbiddenHit] = []
    for slide in slides:
        for phrase in config.forbidden_phrases:
            if phrase in {"不是……而是……", "并非……而是……"}:
                pattern = r"并非.{0,120}?而是" if phrase.startswith("并非") else r"不是.{0,120}?而是"
                match = re.search(pattern, slide.raw, flags=re.DOTALL)
                if match:
                    forbidden_hits.append(ForbiddenHit(slide.number, phrase, _excerpt(slide.raw, match.group(0))))
            elif phrase and phrase in slide.raw:
                forbidden_hits.append(ForbiddenHit(slide.number, phrase, _excerpt(slide.raw, phrase)))
    duplicates = [
        DuplicatePair(left, right, round(score, 4))
        for left, right, score in slide_similarity(slides)
        if score >= config.duplicate_threshold
    ]
    density = [
        DensityIssue(slide.number, len(re.sub(r"\s+", "", slide.content)), config.max_chars_per_slide)
        for slide in slides
        if len(re.sub(r"\s+", "", slide.content)) > config.max_chars_per_slide
    ]
    speaker_notes = audit_speaker_notes(source_text, slides, config)
    substantive = [
        slide for slide in slides
        if not any(value in (slide.page_type or "") for value in config.speaker_notes_simple_page_types)
    ]
    coverage = semantic_coverage(
        source_map.items,
        slides,
        config.covered_threshold,
        config.weak_threshold,
    )
    polarity_mismatches = [
        f"{item.source_id}（第{item.best_slide}页）"
        for item in coverage
        if item.status == "polarity-mismatch"
    ]
    return AuditReport(
        slide_count=len(slides),
        required_source_ids=required,
        mapped_source_ids=mapped,
        unmapped_required_source_ids=unmapped,
        semantic_coverage=coverage,
        unverified_numbers=_unverified_numbers(source_text, slides),
        forbidden_hits=forbidden_hits,
        duplicate_pairs=duplicates,
        density_issues=density,
        missing_titles=[slide.number for slide in slides if not slide.title],
        missing_missions=[slide.number for slide in slides if not slide.mission],
        missing_key_messages=[slide.number for slide in substantive if not slide.key_message],
        missing_source_ids=[slide.number for slide in substantive if not slide.source_ids],
        polarity_mismatches=polarity_mismatches,
        speaker_notes=speaker_notes,
        notes=[
            "Source ID映射用于检查P0/P1是否落实到页面；语义相似度只用于发现候选遗漏。",
            "未核实数字表示上屏脚本出现但全部源材料未出现的数字；讲解词数字单独检查。",
            "polarity_mismatches表示上屏内容与源条目的否定/肯定极性相反（例如源条目写\"不得\"，页面文字丢了这个字）。",
        ],
    )


def compare_script_texts(
    source_text: str,
    source_truth_text: str,
    original_text: str,
    revised_text: str,
    config: AuditConfig,
) -> ComparisonReport:
    original = audit_script_text(source_text, source_truth_text, original_text, config)
    revised = audit_script_text(source_text, source_truth_text, revised_text, config)
    original_mapped = set(original.mapped_source_ids)
    revised_mapped = set(revised.mapped_source_ids)
    original_notes, revised_notes = original.speaker_notes, revised.speaker_notes
    return ComparisonReport(
        original_required_coverage=round(original.p0_p1_reference_coverage, 4),
        revised_required_coverage=round(revised.p0_p1_reference_coverage, 4),
        coverage_delta=round(revised.p0_p1_reference_coverage - original.p0_p1_reference_coverage, 4),
        lost_required_source_ids=sorted((original_mapped - revised_mapped) & set(original.required_source_ids)),
        newly_mapped_source_ids=sorted((revised_mapped - original_mapped) & set(revised.required_source_ids)),
        new_unverified_numbers=sorted(set(revised.unverified_numbers) - set(original.unverified_numbers)),
        removed_unverified_numbers=sorted(set(original.unverified_numbers) - set(revised.unverified_numbers)),
        original_slide_count=original.slide_count,
        revised_slide_count=revised.slide_count,
        original_notes_coverage=round(original_notes.notes_coverage if original_notes else 1.0, 4),
        revised_notes_coverage=round(revised_notes.notes_coverage if revised_notes else 1.0, 4),
        notes_coverage_delta=round((revised_notes.notes_coverage if revised_notes else 1.0) - (original_notes.notes_coverage if original_notes else 1.0), 4),
        original_duration_seconds=original_notes.total_duration_seconds if original_notes else 0,
        revised_duration_seconds=revised_notes.total_duration_seconds if revised_notes else 0,
    )
