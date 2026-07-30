from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass(slots=True)
class SourceItem:
    source_id: str
    category: str
    importance: str
    state: str
    subject: str
    content: str
    numbers_time: str = ""
    boundary: str = ""
    source_location: str = ""
    conflict: str = ""


@dataclass(slots=True)
class SourceTruthMap:
    items: list[SourceItem] = field(default_factory=list)
    issues: list[str] = field(default_factory=list)

    @property
    def required_ids(self) -> list[str]:
        return [item.source_id for item in self.items if item.importance in {"P0", "P1"}]

    @property
    def p0_ids(self) -> list[str]:
        return [item.source_id for item in self.items if item.importance == "P0"]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class SourceInventory:
    file_names: list[str]
    file_count: int
    char_count: int
    paragraph_count: int
    candidate_item_count: int
    numbers: list[str] = field(default_factory=list)
    state_terms: dict[str, int] = field(default_factory=dict)
    boundary_terms: dict[str, int] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class PlannedSlide:
    number: int
    title: str = ""
    chapter_number: int | None = None
    chapter_title: str = ""
    mission: str = ""
    key_message: str = ""
    source_ids: list[str] = field(default_factory=list)
    page_type: str = ""
    page_nature: str = ""
    visual_form: str = ""
    previous_relation: str = ""
    next_relation: str = ""
    necessity: str = ""
    raw: str = ""


@dataclass(slots=True)
class ChapterPlan:
    number: int
    title: str = ""
    mission: str = ""
    conclusion: str = ""
    source_ids: list[str] = field(default_factory=list)
    page_range: str = ""
    previous_link: str = ""
    next_link: str = ""
    boundary: str = ""
    slides: list[PlannedSlide] = field(default_factory=list)
    raw: str = ""


@dataclass(slots=True)
class PresentationPlan:
    goal: str = ""
    core_conclusion: str = ""
    audience: str = ""
    storyline: str = ""
    chapters: list[ChapterPlan] = field(default_factory=list)
    orphan_slides: list[PlannedSlide] = field(default_factory=list)


@dataclass(slots=True)
class PlanningIssue:
    level: str
    identifier: str
    message: str


@dataclass(slots=True)
class PlanningAudit:
    chapter_count: int
    slide_count: int
    mapped_source_ids: list[str] = field(default_factory=list)
    unmapped_source_ids: list[str] = field(default_factory=list)
    issues: list[PlanningIssue] = field(default_factory=list)

    @property
    def passed(self) -> bool:
        return not self.issues and not self.unmapped_source_ids

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["passed"] = self.passed
        return data


@dataclass(slots=True)
class ScriptSlide:
    number: int
    title: str = ""
    mission: str = ""
    key_message: str = ""
    source_ids: list[str] = field(default_factory=list)
    necessity: str = ""
    previous_relation: str = ""
    next_relation: str = ""
    page_type: str = ""
    body: str = ""
    raw: str = ""
    speaker_opening: str = ""
    speaker_explanation: str = ""
    speaker_emphasis: str = ""
    speaker_boundary: str = ""
    speaker_transition: str = ""
    speaker_notes_raw: str = ""
    speaker_notes_seconds: int | None = None

    @property
    def content(self) -> str:
        return "\n".join(
            part for part in (self.title, self.mission, self.key_message, self.body) if part
        )

    @property
    def speaker_notes_text(self) -> str:
        return "\n".join(
            part for part in (
                self.speaker_opening, self.speaker_explanation, self.speaker_emphasis,
                self.speaker_boundary, self.speaker_transition,
            ) if part
        )

    @property
    def has_speaker_notes(self) -> bool:
        return bool(self.speaker_notes_text.strip())


@dataclass(slots=True)
class ForbiddenHit:
    slide_number: int
    phrase: str
    excerpt: str


@dataclass(slots=True)
class DuplicatePair:
    slide_a: int
    slide_b: int
    similarity: float


@dataclass(slots=True)
class DensityIssue:
    slide_number: int
    char_count: int
    limit: int


@dataclass(slots=True)
class SemanticCoverageItem:
    source_id: str
    importance: str
    content: str
    status: str
    best_slide: int | None
    score: float


@dataclass(slots=True)
class SpeakerNotesAudit:
    slide_count: int
    substantive_slide_count: int
    notes_present_count: int
    total_duration_seconds: int = 0
    target_duration_seconds: int | None = None
    duration_out_of_range: bool = False
    missing_notes: list[int] = field(default_factory=list)
    missing_core_explanation: list[int] = field(default_factory=list)
    missing_opening: list[int] = field(default_factory=list)
    missing_emphasis: list[int] = field(default_factory=list)
    missing_boundary: list[int] = field(default_factory=list)
    missing_transition: list[int] = field(default_factory=list)
    missing_duration: list[int] = field(default_factory=list)
    short_notes: list[int] = field(default_factory=list)
    high_repetition_slides: list[int] = field(default_factory=list)
    page_direction_slides: list[int] = field(default_factory=list)
    not_but_slides: list[int] = field(default_factory=list)
    method_meta_slides: list[int] = field(default_factory=list)
    unverified_numbers: list[str] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)

    @property
    def notes_coverage(self) -> float:
        return 1.0 if self.substantive_slide_count == 0 else self.notes_present_count / self.substantive_slide_count

    @property
    def passed(self) -> bool:
        return not any((
            self.missing_notes, self.missing_core_explanation, self.missing_opening,
            self.missing_emphasis, self.missing_boundary, self.missing_transition,
            self.missing_duration, self.short_notes, self.high_repetition_slides,
            self.page_direction_slides, self.not_but_slides, self.method_meta_slides,
            self.unverified_numbers, self.duration_out_of_range,
        ))

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["notes_coverage"] = self.notes_coverage
        data["passed"] = self.passed
        return data


@dataclass(slots=True)
class FormalStyleIssue:
    level: str
    scope: str
    identifier: str
    code: str
    message: str
    excerpt: str = ""


@dataclass(slots=True)
class FormalStyleAudit:
    profile: str
    report_subtype: str
    chapter_count: int
    slide_count: int
    decision_intent: str = "inform"
    audience_level: str = "executive-leadership"
    project_phase: str = "planning"
    report_subtype_label: str = ""
    decision_intent_label: str = ""
    audience_level_label: str = ""
    project_phase_label: str = ""
    expected_chapter_roles: list[str] = field(default_factory=list)
    emphasis: list[str] = field(default_factory=list)
    state_guidance: list[str] = field(default_factory=list)
    issues: list[FormalStyleIssue] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)

    @property
    def error_count(self) -> int:
        return sum(1 for issue in self.issues if issue.level == "ERROR")

    @property
    def warning_count(self) -> int:
        return sum(1 for issue in self.issues if issue.level == "WARN")

    @property
    def passed(self) -> bool:
        return self.error_count == 0

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["error_count"] = self.error_count
        data["warning_count"] = self.warning_count
        data["passed"] = self.passed
        return data


@dataclass(slots=True)
class AuditReport:
    slide_count: int
    required_source_ids: list[str] = field(default_factory=list)
    mapped_source_ids: list[str] = field(default_factory=list)
    unmapped_required_source_ids: list[str] = field(default_factory=list)
    semantic_coverage: list[SemanticCoverageItem] = field(default_factory=list)
    unverified_numbers: list[str] = field(default_factory=list)
    forbidden_hits: list[ForbiddenHit] = field(default_factory=list)
    duplicate_pairs: list[DuplicatePair] = field(default_factory=list)
    density_issues: list[DensityIssue] = field(default_factory=list)
    missing_titles: list[int] = field(default_factory=list)
    missing_missions: list[int] = field(default_factory=list)
    missing_key_messages: list[int] = field(default_factory=list)
    missing_source_ids: list[int] = field(default_factory=list)
    speaker_notes: SpeakerNotesAudit | None = None
    notes: list[str] = field(default_factory=list)

    @property
    def p0_p1_reference_coverage(self) -> float:
        if not self.required_source_ids:
            return 1.0
        return len(set(self.required_source_ids) - set(self.unmapped_required_source_ids)) / len(
            set(self.required_source_ids)
        )

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["p0_p1_reference_coverage"] = self.p0_p1_reference_coverage
        if self.speaker_notes is not None:
            data["speaker_notes"]["notes_coverage"] = self.speaker_notes.notes_coverage
            data["speaker_notes"]["passed"] = self.speaker_notes.passed
        return data


@dataclass(slots=True)
class ComparisonReport:
    original_required_coverage: float
    revised_required_coverage: float
    coverage_delta: float
    lost_required_source_ids: list[str] = field(default_factory=list)
    newly_mapped_source_ids: list[str] = field(default_factory=list)
    new_unverified_numbers: list[str] = field(default_factory=list)
    removed_unverified_numbers: list[str] = field(default_factory=list)
    original_slide_count: int = 0
    revised_slide_count: int = 0
    original_notes_coverage: float = 1.0
    revised_notes_coverage: float = 1.0
    notes_coverage_delta: float = 0.0
    original_duration_seconds: int = 0
    revised_duration_seconds: int = 0

    @property
    def passed(self) -> bool:
        return not self.lost_required_source_ids and not self.new_unverified_numbers and self.notes_coverage_delta >= 0

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["passed"] = self.passed
        return data
