from __future__ import annotations

from dataclasses import dataclass, fields
from pathlib import Path
from typing import Any

import yaml

from .rules import load_rules


_RULES = load_rules(Path(__file__).resolve().parents[2] / "config/rules.yaml")
_DEFAULT_MAX_CHARS = int(_RULES.density_levels["high"]["max_chars"])


@dataclass(frozen=True, slots=True)
class AuditConfig:
    covered_threshold: float = 0.42
    weak_threshold: float = 0.20
    duplicate_threshold: float = 0.64
    max_chars_per_slide: int = _DEFAULT_MAX_CHARS
    forbidden_phrases: tuple[str, ...] = (
        "需关注事项",
        "总体判断",
        "不是……而是……",
        "并非……而是……",
    )
    speaker_notes_enabled: bool = True
    speaker_notes_required_for_substantive: bool = True
    speaker_notes_min_chars: int = 80
    speaker_notes_max_repetition: float = 0.78
    speaker_notes_default_seconds: int = 60
    speaker_notes_simple_page_types: tuple[str, ...] = (
        "封面", "目录", "章节过渡", "过渡页", "封底", "结束页",
    )
    target_duration_minutes: float | None = None
    duration_tolerance_ratio: float = 0.15
    writing_profile: str = "general-formal"
    report_subtype: str = "work-report"
    decision_intent: str = "inform"
    audience_level: str = "executive-leadership"
    project_phase: str = "planning"
    reporting_modes_path: str = "config/reporting-modes.yaml"
    formal_title_min_chars: int = 4
    formal_title_max_chars: int = 18
    formal_chapter_title_max_chars: int = 20
    generic_chapter_titles: tuple[str, ...] = (
        "背景", "现状", "问题", "方案", "建议", "措施", "保障", "总结", "思考",
    )
    hard_consulting_phrases: tuple[str, ...] = (
        "颠覆", "引爆", "破局", "赛道", "打法", "飞轮", "第二曲线", "指数级",
        "重塑格局", "绝对领先", "全面领先", "顶层设计牵引跃迁",
    )
    soft_consulting_phrases: tuple[str, ...] = (
        "赋能", "抓手", "方法论", "商业闭环", "增长引擎", "价值飞跃",
    )
    overclaim_phrases: tuple[str, ...] = (
        "彻底解决", "全面实现", "重大突破", "跨越式发展", "行业第一", "唯一",
        "绝对优势", "全面领先",
    )
    meta_narrative_phrases: tuple[str, ...] = (
        "本报告认为", "本方案旨在", "编制过程中", "资料显示", "研究发现",
    )
    action_title_markers: tuple[str, ...] = (
        "将推动", "将实现", "将驱动", "将助力", "引领", "打造", "重塑", "释放", "撬动",
    )
    work_arrangement_title_terms: tuple[str, ...] = (
        "重点任务", "工作安排", "实施路径", "推进计划", "责任分工", "保障措施", "主要措施",
    )

    @classmethod
    def from_yaml(cls, path: str | Path) -> "AuditConfig":
        data: dict[str, Any] = yaml.safe_load(Path(path).read_text(encoding="utf-8")) or {}
        valid = {field.name for field in fields(cls)}
        values = {key: value for key, value in data.items() if key in valid}
        tuple_fields = (
            "forbidden_phrases", "speaker_notes_simple_page_types", "generic_chapter_titles",
            "hard_consulting_phrases", "soft_consulting_phrases", "overclaim_phrases",
            "meta_narrative_phrases", "action_title_markers", "work_arrangement_title_terms",
        )
        for key in tuple_fields:
            if key in values:
                values[key] = tuple(values[key] or ())
        return cls(**values)
