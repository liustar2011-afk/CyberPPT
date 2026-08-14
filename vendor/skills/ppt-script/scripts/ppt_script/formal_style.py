from __future__ import annotations

import re
from pathlib import Path
from difflib import SequenceMatcher

from .config import AuditConfig
from .models import FormalStyleAudit, FormalStyleIssue
from .planning import parse_plan
from .report_profiles import load_reporting_profiles, resolve_reporting_context
from .script_parser import parse_script

_TITLE_PUNCTUATION = "。！？!?"
_INTERROGATIVE_PREFIXES = ("为什么", "为何", "如何", "是否", "能否", "怎样", "怎么")
_EXECUTION_CATEGORIES = {
    "actor": ("由", "牵头", "负责", "配合", "统筹", "组织"),
    "action": ("推动", "开展", "建立", "完善", "形成", "落实", "实施", "建设", "梳理", "明确"),
    "mechanism": ("依托", "通过", "按照", "机制", "流程", "标准", "制度", "平台"),
    "output": ("成果", "清单", "目录", "台账", "报告", "方案", "产品", "服务", "完成"),
    "boundary": ("依法合规", "授权", "边界", "条件", "安全", "受控"),
}

def _compact(text: str) -> str:
    return re.sub(r"[\s，。；：、（）()\-—|｜]+", "", text or "")


def _similarity(left: str, right: str) -> float:
    a, b = _compact(left), _compact(right)
    if not a or not b:
        return 0.0
    if a in b or b in a:
        return min(len(a), len(b)) / max(len(a), len(b))
    return SequenceMatcher(None, a, b).ratio()


def _body_field(body: str, name: str) -> str:
    match = re.search(rf"^{re.escape(name)}[：:]\s*(.+)$", body or "", re.MULTILINE)
    return match.group(1).strip() if match else ""


def _add(issues: list[FormalStyleIssue], level: str, scope: str, identifier: str, code: str, message: str, excerpt: str = "") -> None:
    issues.append(FormalStyleIssue(level, scope, identifier, code, message, excerpt))


def _check_title(issues: list[FormalStyleIssue], title: str, scope: str, identifier: str, config: AuditConfig, max_chars: int) -> None:
    value = (title or "").strip()
    if not value:
        return
    if value[-1:] in _TITLE_PUNCTUATION:
        _add(issues, "ERROR", scope, identifier, "title-punctuation", "正式汇报标题不得使用句号、问号或感叹号收尾。", value)
    if value.startswith(_INTERROGATIVE_PREFIXES) or any(mark in value for mark in "？?"):
        _add(issues, "ERROR", scope, identifier, "interrogative-title", "标题应采用正式主题表达，不使用提问式标题。", value)
    char_count = len(_compact(value))
    if char_count > max_chars:
        _add(issues, "WARN", scope, identifier, "title-too-long", f"标题{char_count}字，建议压缩至{max_chars}字以内并将判断移入副标题或正文。", value)
    for phrase in config.hard_consulting_phrases:
        if phrase and phrase in value:
            _add(issues, "ERROR", scope, identifier, "hard-consulting-phrase", f"标题命中外部咨询或营销化用语“{phrase}”。", value)
    for phrase in config.soft_consulting_phrases:
        if phrase and phrase in value:
            _add(issues, "WARN", scope, identifier, "soft-consulting-phrase", f"标题使用“{phrase}”，建议改为具体任务、机制或成果表述。", value)
    if any(marker in value for marker in config.action_title_markers) and char_count > 10:
        _add(issues, "WARN", scope, identifier, "action-title-like", "主标题呈现外部咨询式长结论句，建议改为主题型短标题，将判断放入副标题。", value)


def _phrase_checks(issues: list[FormalStyleIssue], text: str, scope: str, identifier: str, config: AuditConfig) -> None:
    for phrase in config.hard_consulting_phrases:
        if phrase and phrase in text:
            _add(issues, "ERROR", scope, identifier, "hard-consulting-phrase", f"命中外部咨询或营销化用语“{phrase}”。", phrase)
    for phrase in config.soft_consulting_phrases:
        if phrase and phrase in text:
            _add(issues, "WARN", scope, identifier, "soft-consulting-phrase", f"使用“{phrase}”，应优先改为明确任务、机制、主体或成果。", phrase)
    for phrase in config.overclaim_phrases:
        if phrase and phrase in text:
            _add(issues, "WARN", scope, identifier, "overclaim-phrase", f"使用强承诺或绝对化表述“{phrase}”，需核验依据并适当收敛。", phrase)
    for phrase in config.meta_narrative_phrases:
        if phrase and phrase in text:
            _add(issues, "ERROR", scope, identifier, "meta-narrative", f"正式汇报不应出现元叙事表述“{phrase}”。", phrase)


def _execution_element_count(text: str) -> int:
    return sum(1 for terms in _EXECUTION_CATEGORIES.values() if any(term in text for term in terms))


def audit_government_soe_style(
    plan_text: str,
    script_text: str,
    config: AuditConfig,
    repo_root=None,
) -> FormalStyleAudit:
    plan = parse_plan(plan_text or "")
    slides = parse_script(script_text or "")
    issues: list[FormalStyleIssue] = []

    for chapter in plan.chapters:
        identifier = f"第{chapter.number}章"
        _check_title(issues, chapter.title, "chapter", identifier, config, config.formal_chapter_title_max_chars)
        if chapter.title in config.generic_chapter_titles:
            _add(issues, "WARN", "chapter", identifier, "generic-chapter-title", "章节名称过于笼统，应补充对象、范围或工作属性。", chapter.title)

    root = Path(repo_root) if repo_root is not None else Path(__file__).resolve().parents[2]
    modes_path = Path(config.reporting_modes_path)
    if not modes_path.is_absolute():
        modes_path = root / modes_path
    registry = load_reporting_profiles(modes_path)
    context = resolve_reporting_context(
        registry,
        report_subtype=config.report_subtype,
        decision_intent=config.decision_intent,
        audience_level=config.audience_level,
        project_phase=config.project_phase,
    )
    chapter_text = " ".join(chapter.title for chapter in plan.chapters)

    def role_present(role: str) -> bool:
        compact = _compact(role)
        if compact and compact in _compact(chapter_text):
            return True
        tokens = [token for token in re.split(r"[与和及、/]", role) if len(_compact(token)) >= 2]
        return any(_compact(token) in _compact(chapter_text) for token in tokens)

    for role in context.expected_chapter_roles:
        if not role_present(role):
            _add(issues, "WARN", "deck", config.report_subtype, "missing-chapter-role", f"“{context.report_subtype_label}”通常需要体现章节职能：{role}。")
    if context.required_intent_roles and not any(role_present(role) for role in context.required_intent_roles):
        _add(issues, "WARN", "deck", config.decision_intent, "missing-intent-role", f"汇报目的为“{context.decision_intent_label}”，章节中应体现：{'／'.join(context.required_intent_roles)}。")

    for slide in slides:
        identifier = f"第{slide.number}页"
        visible_title = _body_field(slide.body, "标题") or slide.title
        subtitle = _body_field(slide.body, "副标题")
        main_judgment = _body_field(slide.body, "主判断") or slide.key_message
        _check_title(issues, visible_title, "slide", identifier, config, config.formal_title_max_chars)
        visible = "\n".join(part for part in (visible_title, subtitle, main_judgment, slide.body) if part)
        _phrase_checks(issues, visible, "slide", identifier, config)
        _phrase_checks(issues, slide.speaker_notes_text, "speaker-notes", identifier, config)
        combined_text = f"{visible}\n{slide.speaker_notes_text}"
        for phrase in context.forbidden_state_upgrades:
            if phrase and phrase in combined_text:
                _add(issues, "WARN", "slide", identifier, "phase-state-upgrade", f"当前处于“{context.project_phase_label}”，出现可能超前的状态表述“{phrase}”，应核验材料依据。", phrase)
        compact_title = _compact(visible_title)
        compact_subtitle = _compact(subtitle)
        subtitle_repeats_title = bool(
            compact_title
            and compact_subtitle
            and compact_title in compact_subtitle
            and len(compact_subtitle) <= len(compact_title) * 4
        )
        if subtitle and (_similarity(visible_title, subtitle) >= 0.72 or subtitle_repeats_title):
            _add(issues, "WARN", "slide", identifier, "title-subtitle-repetition", "主标题与副标题语义重复；副标题应补充判断、范围或任务安排。", f"{visible_title} / {subtitle}")
        action_like = any(marker in visible_title for marker in config.action_title_markers)
        if any(term in visible_title for term in config.work_arrangement_title_terms) or action_like:
            execution_text = re.sub(r"^(标题|副标题|主判断)[：:].*$", "", slide.body, flags=re.MULTILINE)
            count = _execution_element_count(execution_text)
            if count < 3:
                _add(issues, "WARN", "slide", identifier, "weak-execution-elements", "工作安排类页面应至少明确主体、任务、机制、成果、边界中的三项。", execution_text[:120])

    return FormalStyleAudit(
        profile=config.writing_profile,
        report_subtype=config.report_subtype,
        chapter_count=len(plan.chapters),
        slide_count=len(slides),
        decision_intent=config.decision_intent,
        audience_level=config.audience_level,
        project_phase=config.project_phase,
        report_subtype_label=context.report_subtype_label,
        decision_intent_label=context.decision_intent_label,
        audience_level_label=context.audience_level_label,
        project_phase_label=context.project_phase_label,
        expected_chapter_roles=list(context.expected_chapter_roles),
        emphasis=list(context.emphasis),
        state_guidance=list(context.state_guidance),
        issues=issues,
        notes=[
            "ERROR用于明确不符合政府、央企正式汇报文体的硬问题；WARN用于需要人工判断的结构和措辞风险。",
            "章节结构由汇报类型决定，结尾动作由汇报目的决定，信息深度由受众层级决定，时态口径由项目阶段决定。",
            "机器检查不能替代对章节使命、职责边界、政策口径和工作逻辑的语义审查。",
        ],
    )
