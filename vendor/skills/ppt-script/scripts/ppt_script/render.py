from __future__ import annotations

from datetime import datetime

from .models import AuditReport, ComparisonReport, FormalStyleAudit, PlanningAudit, ScriptSlide, SourceInventory, SpeakerNotesAudit


def render_source_inventory(
    inventory: SourceInventory,
    unsupported_files: list[str] | None = None,
    low_quality_files: list[str] | None = None,
    original_titles: list[str] | None = None,
) -> str:
    unsupported_files = unsupported_files or []
    low_quality_files = low_quality_files or []
    original_titles = original_titles or []
    lines = [
        "# 源材料机器概览",
        "",
        "> 本报告只提供确定性概览，不替代对材料意图、重要性、冲突和边界的语义判断。",
        "",
        f"- 源文件数：{inventory.file_count}",
        f"- 源材料字符数：{inventory.char_count}",
        f"- 非空段落数：{inventory.paragraph_count}",
        f"- 候选内容条目：{inventory.candidate_item_count}",
        f"- 文件：{', '.join(inventory.file_names) or '无'}",
        f"- 未支持文件：{', '.join(unsupported_files) or '无'}",
        f"- 疑似扫描件/OCR质量过低：{', '.join(low_quality_files) or '无'}",
        f"- 原文自带标题：{'；'.join(original_titles) or '无'}",
        f"- 数字：{', '.join(inventory.numbers) or '无'}",
        f"- 状态词：{', '.join(f'{key}={value}' for key, value in inventory.state_terms.items()) or '无'}",
        f"- 边界词：{', '.join(f'{key}={value}' for key, value in inventory.boundary_terms.items()) or '无'}",
    ]
    return "\n".join(lines) + "\n"


def render_planning_audit(audit: PlanningAudit) -> str:
    lines = [
        "# 故事线、章节与页面规划机器检查",
        "",
        f"- 结果：{'PASS' if audit.passed else 'FAIL'}",
        f"- 章节数：{audit.chapter_count}",
        f"- 页面数：{audit.slide_count}",
        f"- 已映射Source ID：{', '.join(audit.mapped_source_ids) or '无'}",
        f"- 未映射Source ID：{', '.join(audit.unmapped_source_ids) or '无'}",
        "",
        "## 问题",
        "",
    ]
    if audit.issues:
        lines.extend(f"- [{issue.level}] {issue.identifier}：{issue.message}" for issue in audit.issues)
    else:
        lines.append("- 无确定性结构问题")
    return "\n".join(lines) + "\n"


def render_speaker_notes_audit(audit: SpeakerNotesAudit) -> str:
    lines = ["# 演讲者备注质量检查", "", f"- 结果：{'PASS' if audit.passed else 'FAIL'}", f"- 正文页：{audit.substantive_slide_count}", f"- 已有讲解词：{audit.notes_present_count}", f"- 讲解词覆盖率：{audit.notes_coverage:.1%}", f"- 预计总时长：{audit.total_duration_seconds}秒", f"- 目标时长：{audit.target_duration_seconds if audit.target_duration_seconds is not None else '未设置'}", f"- 讲解词新增未核实数字：{', '.join(audit.unverified_numbers) or '无'}", "", "## 问题", ""]
    fields = (
        ("缺少完整讲解词", audit.missing_notes),
        ("缺少开场承接", audit.missing_opening),
        ("缺少核心讲解", audit.missing_core_explanation),
        ("缺少重点强调", audit.missing_emphasis),
        ("缺少边界说明", audit.missing_boundary),
        ("缺少转场语", audit.missing_transition),
        ("缺少预计讲解时长", audit.missing_duration),
        ("讲解词过短", audit.short_notes),
        ("讲解词与上屏文字高度重复", audit.high_repetition_slides),
        ("讲解词含页面指示词", audit.page_direction_slides),
        ("讲解词使用‘不是……而是……’句式", audit.not_but_slides),
        ("讲解词含讲解方法/制作者口吻", audit.method_meta_slides),
    )
    found = False
    for label, pages in fields:
        if pages:
            found = True
            lines.append(f"- {label}：{pages}")
    if audit.unverified_numbers:
        found = True
        lines.append(f"- 讲解词含源材料未出现数字：{', '.join(audit.unverified_numbers)}")
    if audit.duration_out_of_range:
        found = True
        lines.append("- 预计总时长与项目目标时长偏差超过允许范围")
    if not found:
        lines.append("- 无确定性问题")
    return "\n".join(lines) + "\n"


def render_speaker_notes(project_name: str, slides: list[ScriptSlide]) -> str:
    total = sum(slide.speaker_notes_seconds or 0 for slide in slides)
    lines = [f"# {project_name} · 演讲者备注讲稿", "", f"生成时间：{datetime.now():%Y-%m-%d %H:%M}", f"页面总数：{len(slides)}", f"预计总讲解时长：{total}秒", "", "> 本文件只汇总演讲者备注，不作为页面可见文字或生图输入。", "", "---"]
    for slide in slides:
        review_markers = ("原文未提供", "源材料口径", "待复核", "字段缺口", "需法务复核", "无来源指标")
        speech = "\n\n".join(
            part.strip() for part in (
                slide.speaker_opening,
                slide.speaker_explanation,
                slide.speaker_emphasis,
                slide.speaker_boundary,
                slide.speaker_transition,
            ) if part and part.strip() and not any(marker in part for marker in review_markers)
        )
        duration = f"约{slide.speaker_notes_seconds}秒" if slide.speaker_notes_seconds is not None else "未填写"
        lines.extend([
            "", f"## 第{slide.number}页｜{slide.title}", "",
            f"> 建议讲解时长：{duration}", "",
            speech or "本页无讲解词。", "", "---",
        ])
    return "\n".join(lines).strip() + "\n"


def build_speaker_notes_payload(project_name: str, slides: list[ScriptSlide]) -> dict:
    pages = [{"page": slide.number, "title": slide.title, "source_ids": slide.source_ids, "duration_seconds": slide.speaker_notes_seconds, "opening": slide.speaker_opening, "core_explanation": slide.speaker_explanation, "emphasis": slide.speaker_emphasis, "boundary": slide.speaker_boundary, "transition": slide.speaker_transition, "notes_text": "\n\n".join(part for part in (slide.speaker_opening, slide.speaker_explanation, slide.speaker_emphasis, slide.speaker_boundary, slide.speaker_transition) if part)} for slide in slides]
    return {"schema": "ppt-script.speaker_notes.v1", "project": project_name, "generated_at": datetime.now().isoformat(timespec="seconds"), "total_duration_seconds": sum(page["duration_seconds"] or 0 for page in pages), "pages": pages}


def render_audit(report: AuditReport) -> str:
    speaker = report.speaker_notes
    lines = [
        "# PPT脚本机器预审报告",
        "",
        "> 确定性检查不替代100分语义评价和四道质量闸门判定。",
        "",
        "## 概览",
        "",
        f"- 页数：{report.slide_count}",
        f"- P0/P1 Source ID引用覆盖率：{report.p0_p1_reference_coverage:.1%}",
        f"- 未映射P0/P1：{', '.join(report.unmapped_required_source_ids) or '无'}",
        f"- 未核实数字：{', '.join(report.unverified_numbers) or '无'}",
        f"- 演讲者备注闸门：{'PASS' if speaker and speaker.passed else 'FAIL' if speaker else '未检查'}",
        f"- 演讲者备注覆盖率：{speaker.notes_coverage:.1%}" if speaker else "- 演讲者备注覆盖率：未检查",
        f"- 禁用语命中：{len(report.forbidden_hits)}",
        f"- 高相似页面对：{len(report.duplicate_pairs)}",
        f"- 超密度页面：{len(report.density_issues)}",
        "",
        "## Source ID与语义覆盖",
        "",
        "| Source ID | 重要性 | 引用状态 | 语义状态 | 最佳页 | 相似度 | 内容 |",
        "|---|---|---|---|---:|---:|---|",
    ]
    mapped = set(report.mapped_source_ids)
    for item in report.semantic_coverage:
        lines.append(
            f"| {item.source_id} | {item.importance} | {'已引用' if item.source_id in mapped else '未引用'} | "
            f"{item.status} | {item.best_slide or '-'} | {item.score:.3f} | {item.content.replace('|', '\\|')} |"
        )
    lines.extend(["", "## 确定性问题", ""])
    for hit in report.forbidden_hits:
        lines.append(f"- 第{hit.slide_number}页命中 `{hit.phrase}`：{hit.excerpt}")
    for pair in report.duplicate_pairs:
        lines.append(f"- 第{pair.slide_a}页与第{pair.slide_b}页高度相似：{pair.similarity:.1%}")
    for issue in report.density_issues:
        lines.append(f"- 第{issue.slide_number}页文字{issue.char_count}字，超过阈值{issue.limit}字")
    if report.missing_titles:
        lines.append(f"- 缺少标题：{report.missing_titles}")
    if report.missing_missions:
        lines.append(f"- 缺少页面使命：{report.missing_missions}")
    if report.missing_key_messages:
        lines.append(f"- 缺少页面结论：{report.missing_key_messages}")
    if report.missing_source_ids:
        lines.append(f"- 缺少材料依据ID：{report.missing_source_ids}")
    if report.polarity_mismatches:
        lines.append(f"- 否定/肯定极性与源条目相反（请核实是否颠倒了原意）：{'、'.join(report.polarity_mismatches)}")
    if not any((report.forbidden_hits, report.duplicate_pairs, report.density_issues, report.missing_titles, report.missing_missions, report.missing_key_messages, report.missing_source_ids, report.unmapped_required_source_ids, report.unverified_numbers, report.polarity_mismatches)):
        lines.append("- 无确定性问题")
    lines.extend(["", "## 说明", ""])
    lines.extend(f"- {note}" for note in report.notes)
    return "\n".join(lines) + "\n"


def render_comparison(report: ComparisonReport) -> str:
    lines = [
        "# PPT脚本版本比较报告",
        "",
        f"- 结果：{'PASS' if report.passed else 'FAIL'}",
        f"- 原稿P0/P1引用覆盖率：{report.original_required_coverage:.1%}",
        f"- 修订稿P0/P1引用覆盖率：{report.revised_required_coverage:.1%}",
        f"- 覆盖变化：{report.coverage_delta:+.1%}",
        f"- 丢失Source ID：{', '.join(report.lost_required_source_ids) or '无'}",
        f"- 新增映射Source ID：{', '.join(report.newly_mapped_source_ids) or '无'}",
        f"- 新增未核实数字：{', '.join(report.new_unverified_numbers) or '无'}",
        f"- 已移除未核实数字：{', '.join(report.removed_unverified_numbers) or '无'}",
        f"- 页数：{report.original_slide_count} → {report.revised_slide_count}",
        f"- 讲解词覆盖率：{report.original_notes_coverage:.1%} → {report.revised_notes_coverage:.1%}",
        f"- 预计讲解时长：{report.original_duration_seconds}秒 → {report.revised_duration_seconds}秒",
    ]
    return "\n".join(lines) + "\n"


def render_formal_style_audit(report: FormalStyleAudit) -> str:
    lines = [
        "# 政府、央企正式汇报文体检查",
        "",
        f"- 结果：{'PASS' if report.passed else 'FAIL'}",
        f"- 写作配置：{report.profile}",
        f"- 汇报类型：{report.report_subtype_label or report.report_subtype}",
        f"- 汇报目的：{report.decision_intent_label or report.decision_intent}",
        f"- 受众层级：{report.audience_level_label or report.audience_level}",
        f"- 项目阶段：{report.project_phase_label or report.project_phase}",
        f"- ERROR：{report.error_count}",
        f"- WARN：{report.warning_count}",
        "",
        "## 问题清单",
        "",
    ]
    if report.issues:
        for issue in report.issues:
            excerpt = f"；示例：{issue.excerpt}" if issue.excerpt else ""
            lines.append(f"- [{issue.level}] {issue.identifier} `{issue.code}`：{issue.message}{excerpt}")
    else:
        lines.append("- 未发现确定性文体问题")
    lines.extend(["", "## 说明", ""])
    lines.extend(f"- {note}" for note in report.notes)
    return "\n".join(lines) + "\n"
