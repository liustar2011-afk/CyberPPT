from __future__ import annotations

import re
from dataclasses import asdict, dataclass
from pathlib import Path

from .page_composition import (
    audit_adjacent_overlap,
    audit_cross_page_fingerprints,
    audit_page_composition,
    parse_onscreen_zones,
)
from .pages_index import active_page_files
from .rules import ContentRules
from .visual_focus import parse_visual_focus, validate_visual_focus
from .visual_drawing import audit_visual_drawing


_PAGE_FILE = re.compile(r"^p(\d+)-(.+)\.md$", re.IGNORECASE)
_PAGE_HEADING = re.compile(r"^##\s*第(\d+)页[：:]\s*(.+?)\s*$", re.MULTILINE)
_OUTLINE_PAGE = re.compile(r"^###\s*第(\d+)页[｜|]\s*(.+?)\s*$", re.MULTILINE)
_CIRCLED = re.compile(r"[①②③④⑤⑥⑦⑧⑨⑩]")
_CN_ENUM = re.compile(r"(?:^|\n)\s*[一二三四五六七八九十]+[、．.]")
_SKIP_LABELS = ("标题", "副标题", "主判断", "辅助区", "注释文字")


@dataclass(frozen=True, slots=True)
class QualityIssue:
    category: str
    page: str
    message: str
    text: str = ""
    level: str = "ERROR"


@dataclass(frozen=True, slots=True)
class QualityReport:
    passed: bool
    page_count: int
    issues: tuple[QualityIssue, ...]

    def to_dict(self) -> dict:
        return {
            "passed": self.passed,
            "page_count": self.page_count,
            "issues": [asdict(issue) for issue in self.issues],
        }


def _onscreen(text: str) -> str:
    match = re.search(r"上屏文字：\s*(.*?)(?:\n---|\Z)", text, re.DOTALL)
    return match.group(1).strip() if match else ""


def _visible_title(onscreen: str) -> str:
    match = re.search(r"(?:^|\n)标题：\s*\n?\s*([^\n]+)", onscreen)
    return match.group(1).strip() if match else ""


def _subtitle_block(onscreen: str) -> str:
    """Return raw subtitle field body until the next structural marker."""
    match = re.search(
        r"(?:^|\n)副标题：\s*(.*?)(?=\n(?:①|②|③|④|⑤|主判断[：:]|辅助区[：:]|标题[：:]|\Z))",
        onscreen,
        re.DOTALL,
    )
    return match.group(1).strip() if match else ""


def _field(text: str, name: str) -> str:
    match = re.search(rf"^{re.escape(name)}[：:]\s*(.+?)\s*$", text, re.MULTILINE)
    return match.group(1).strip() if match else ""


def _estimate_module_count(onscreen: str) -> int:
    circled = _CIRCLED.findall(onscreen)
    if circled:
        return len(set(circled))
    enumerated = _CN_ENUM.findall(onscreen)
    if enumerated:
        return len(enumerated)
    blocks = 0
    for raw in re.split(r"\n\s*\n", onscreen):
        line = raw.strip().splitlines()[0].strip() if raw.strip() else ""
        if not line:
            continue
        label = line.split("：", 1)[0].split(":", 1)[0].strip()
        if label in _SKIP_LABELS or line.startswith("标题") or line.startswith("副标题"):
            continue
        if line.startswith("辅助区"):
            continue
        blocks += 1
    return blocks


def _density_floor_for_strategy(rules: ContentRules, strategy: str) -> dict | None:
    strategy = (strategy or "").strip()
    if strategy not in {"高密度专项", "超高密度专项"}:
        return None
    render = rules.render_strategies.get(strategy)
    if not isinstance(render, dict):
        return None
    levels = render.get("density_levels") or []
    if not levels:
        return None
    # Use the primary (first) density band bound to the render strategy.
    level_name = str(levels[0])
    level = rules.density_levels.get(level_name)
    return dict(level) if isinstance(level, dict) else None


def _declares_path_relation(text: str, path_cfg: dict) -> bool:
    diagram_types = tuple(path_cfg.get("diagram_types") or ())
    semantic_type = _field(text, "推荐主语义图类型")
    # Only path-diagram pages require on-screen order signals; other types may
    # use “纵向递进” as layout language without being 路径型.
    return any(item and item in semantic_type for item in diagram_types)


def _path_relation_issues(text: str, onscreen: str, page: str, rules: ContentRules) -> list[QualityIssue]:
    path_cfg = rules.onscreen_text.get("path_relation") or {}
    if not isinstance(path_cfg, dict) or not path_cfg:
        return []
    if not _declares_path_relation(text, path_cfg):
        return []
    issues: list[QualityIssue] = []
    order_signals = tuple(path_cfg.get("order_signals") or ())
    conflict_markers = tuple(path_cfg.get("conflict_markers") or ())
    has_order = any(signal and signal in onscreen for signal in order_signals)
    conflicts = [marker for marker in conflict_markers if marker and marker in onscreen]
    if not has_order:
        issues.append(
            QualityIssue(
                "path-order-signal",
                page,
                "路径型/纵向递进页上屏缺少顺序信号（如①②③、→、随之）",
                level="WARN",
            )
        )
    if conflicts:
        issues.append(
            QualityIssue(
                "path-order-conflict",
                page,
                "路径型/纵向递进页上屏含并列化措辞，易掩盖模块逻辑顺序",
                " / ".join(conflicts),
                level="WARN",
            )
        )
    return issues


def _title_issues(title: str, page: str, rules: ContentRules) -> list[QualityIssue]:
    config = rules.title_quality
    issues: list[QualityIssue] = []
    compact = re.sub(r"\s+", "", title)
    if len(compact) > int(config["max_chars"]):
        issues.append(QualityIssue("title-quality", page, f"标题超过{config['max_chars']}个字符", title))
    if any(title.startswith(prefix) for prefix in config["forbidden_prefixes"]):
        issues.append(QualityIssue("title-quality", page, "标题应使用简洁短语，不使用设问或说明性开头", title))
    if any(title.endswith(ending) for ending in config["forbidden_endings"]):
        issues.append(QualityIssue("title-quality", page, "标题应使用简洁短语，不使用完整句标点", title))
    return issues


def _from_composition(issue) -> QualityIssue:
    return QualityIssue(
        issue.category,
        issue.page,
        issue.message,
        issue.text,
        level=issue.level,
    )


def audit_project_quality(project: Path, rules: ContentRules) -> QualityReport:
    pages = active_page_files(project)
    issues: list[QualityIssue] = []
    outline_path = project / "outline/02-outline.md"
    outline = outline_path.read_text(encoding="utf-8") if outline_path.exists() else ""
    outline_titles = {int(number): title.strip() for number, title in _OUTLINE_PAGE.findall(outline)}
    seen_numbers: list[int] = []
    adjacent_payload: list[tuple[str, str]] = []

    for path in pages:
        file_match = _PAGE_FILE.match(path.name)
        text = path.read_text(encoding="utf-8")
        heading_match = _PAGE_HEADING.search(text)
        if not file_match or not heading_match:
            issues.append(QualityIssue("consistency", path.name, "文件名或页面主标题不符合 pXX-标题 / 第X页：标题格式"))
            continue
        file_number, file_title = int(file_match.group(1)), file_match.group(2).strip()
        heading_number, heading_title = int(heading_match.group(1)), heading_match.group(2).strip()
        seen_numbers.append(file_number)
        if (file_number, file_title) != (heading_number, heading_title):
            issues.append(QualityIssue("consistency", path.name, "文件名与页面主标题不一致", f"{file_title} / {heading_title}"))
        outline_title = outline_titles.get(file_number)
        if outline_title is None:
            issues.append(QualityIssue("consistency", path.name, "提纲中缺少对应页"))
        elif outline_title != heading_title:
            issues.append(QualityIssue("consistency", path.name, "页面标题与提纲不一致", f"提纲：{outline_title}；页面：{heading_title}"))

        onscreen = _onscreen(text)
        nature = _field(text, "页面性质")
        page_type = _field(text, "页面类型")
        allowed_natures = rules.page_nature["allowed"]
        if nature not in allowed_natures:
            issues.append(QualityIssue("page-nature", path.name, f"页面性质必须明确声明为{'或'.join(allowed_natures)}", nature))
        is_template_type = any(value == page_type for value in rules.page_nature["template_page_types"])
        expected_nature = "模板页" if is_template_type else "内容页"
        if nature in allowed_natures and nature != expected_nature:
            issues.append(QualityIssue("page-nature", path.name, f"页面类型“{page_type}”应声明为{expected_nature}", nature))
        for phrase in rules.onscreen_text["forbidden_meta_language"]:
            if phrase in onscreen:
                issues.append(QualityIssue("onscreen-meta", path.name, "上屏文字含来源核验、制作或审稿元语言", phrase))
        if re.search(r"(?:^|\n)注释文字[：:]", onscreen):
            issues.append(QualityIssue("onscreen-annotation", path.name, "上屏文字不得包含‘注释文字’字段；必要边界应并入正文、辅助区或后台边界字段", "注释文字"))
        module_placeholder = re.search(r"(?:^|\n)(模块[一二三四五六七八九十0-9]+)[：:]", onscreen)
        if module_placeholder:
            issues.append(QualityIssue("onscreen-placeholder", path.name, "上屏文字不得保留‘模块X’通用前缀；应直接使用实际业务标题", module_placeholder.group(1)))
        subtitle = _subtitle_block(onscreen)
        if subtitle:
            subtitle_lines = [line.strip() for line in subtitle.splitlines() if line.strip()]
            max_subtitle = int(rules.onscreen_text.get("subtitle_max_chars") or 50)
            compact_subtitle = re.sub(r"\s+", "", subtitle)
            if len(subtitle_lines) > 1:
                issues.append(
                    QualityIssue(
                        "onscreen-subtitle-block",
                        path.name,
                        "副标题只能一行短语；业务模块正文不得写入副标题字段",
                        f"{len(subtitle_lines)}行",
                    )
                )
            elif len(compact_subtitle) > max_subtitle:
                issues.append(
                    QualityIssue(
                        "onscreen-subtitle-length",
                        path.name,
                        f"副标题超过{max_subtitle}字，应压缩为短语",
                        f"实际 {len(compact_subtitle)} 字",
                    )
                )
        visible_title = _visible_title(onscreen) or heading_title
        issues.extend(_title_issues(visible_title, path.name, rules))
        density_config = rules.page_type_quality
        page_type_limit = density_config.get("types", {}).get(page_type, density_config.get("default", {}))
        max_chars = int(page_type_limit.get("max_chars", 350))
        compact_onscreen = re.sub(r"\s+", "", onscreen)
        char_count = len(compact_onscreen)
        if char_count > max_chars:
            issues.append(
                QualityIssue(
                    "page-type-density",
                    path.name,
                    f"{page_type or '未分类页面'}上屏文字超过差异化预算 {max_chars} 字",
                    f"实际 {char_count} 字",
                )
            )
        strategy = _field(text, "落图策略建议")
        default_strategy = str(rules.onscreen_text.get("default_content_render_strategy") or "").strip()
        if nature == "内容页" and default_strategy == "高密度专项" and strategy == "标准":
            issues.append(
                QualityIssue(
                    "render-density-default",
                    path.name,
                    "正文页默认高密度专项；当前为“标准”，请确认是否有意降密并补足源材料论据",
                    strategy,
                    level="WARN",
                )
            )
        floor = _density_floor_for_strategy(rules, strategy)
        module_count = _estimate_module_count(onscreen)
        if floor and nature == "内容页":
            min_chars = int(floor.get("min_chars") or 0)
            min_modules = int(floor.get("min_modules") or 0)
            if min_chars and char_count < min_chars:
                issues.append(
                    QualityIssue(
                        "render-density-floor",
                        path.name,
                        f"落图策略“{strategy}”要求上屏不少于 {min_chars} 字",
                        f"实际 {char_count} 字",
                    )
                )
            if min_modules and module_count < min_modules:
                issues.append(
                    QualityIssue(
                        "render-density-modules",
                        path.name,
                        f"落图策略“{strategy}”要求不少于 {min_modules} 个模块",
                        f"实际约 {module_count} 个",
                    )
                )
        issues.extend(_path_relation_issues(text, onscreen, path.name, rules))
        if nature == "内容页":
            zones = parse_onscreen_zones(onscreen)
            # Prefer circled/parsed zones when available; keep density estimator as fallback.
            composed_modules = zones.module_count or module_count
            for item in audit_page_composition(
                page=path.name,
                text=text,
                onscreen=onscreen,
                nature=nature,
                rules=rules,
                module_count_hint=composed_modules,
            ):
                issues.append(_from_composition(item))
            adjacent_payload.append((path.name, onscreen))
        pending = [value for value in rules.consistency["pending_markers"] if value in onscreen]
        completed = [value for value in rules.consistency["completed_markers"] if value in onscreen]
        if pending and completed:
            issues.append(QualityIssue("status-conflict", path.name, "同一上屏区域同时出现待决状态和完成状态", f"{pending} / {completed}"))
        if nature == "内容页":
            from ppt_script.visual_drawing import has_direct_image_prompt

            if not has_direct_image_prompt(text):
                focus = parse_visual_focus(text)
                for code in validate_visual_focus(focus):
                    if code == "missing-center":
                        issues.append(QualityIssue("visual-focus-missing", path.name, "内容页必须声明一个主视觉中心"))
                    elif code in {"multiple-centers", "competing-centers"}:
                        issues.append(QualityIssue("visual-focus-conflict", path.name, "内容页不得形成多个或相互竞争的视觉中心", focus.raw))
                    elif code == "missing-role":
                        issues.append(QualityIssue("visual-focus-incomplete", path.name, "主视觉中心必须说明承担的业务角色"))
                    elif code == "missing-reading-path":
                        issues.append(QualityIssue("visual-focus-incomplete", path.name, "内容页必须说明由主视觉中心组织的阅读路径"))
            for item in audit_visual_drawing(page=path.name, content=text, nature=nature, rules=rules):
                issues.append(
                    QualityIssue(
                        item.code,
                        item.page,
                        item.message,
                        item.text,
                        level=item.level,
                    )
                )

    for item in audit_adjacent_overlap(adjacent_payload, rules):
        issues.append(_from_composition(item))
    for item in audit_cross_page_fingerprints(adjacent_payload, rules):
        issues.append(_from_composition(item))

    expected = list(range(1, len(pages) + 1))
    if seen_numbers != expected:
        issues.append(QualityIssue("consistency", "pages", "页码不连续或存在重复", str(seen_numbers)))
    if outline_titles and set(outline_titles) != set(seen_numbers):
        issues.append(QualityIssue("consistency", "outline", "提纲页码与页面文件集合不一致"))
    blocking = [issue for issue in issues if issue.level == "ERROR"]
    return QualityReport(not blocking, len(pages), tuple(issues))


def render_quality_report(report: QualityReport) -> str:
    errors = [issue for issue in report.issues if issue.level == "ERROR"]
    warnings = [issue for issue in report.issues if issue.level == "WARN"]
    lines = [
        "# PPT脚本质量闸门",
        "",
        f"- 结果：{'PASS' if report.passed else 'FAIL'}",
        f"- 页面数：{report.page_count}",
        f"- 问题数：{len(report.issues)}（ERROR {len(errors)} / WARN {len(warnings)}）",
        "",
        "## 问题",
        "",
    ]
    if not report.issues:
        lines.append("- 无确定性问题")
    else:
        for issue in report.issues:
            detail = f"：{issue.text}" if issue.text else ""
            lines.append(f"- [{issue.level}/{issue.category}] {issue.page}｜{issue.message}{detail}")
    return "\n".join(lines) + "\n"
