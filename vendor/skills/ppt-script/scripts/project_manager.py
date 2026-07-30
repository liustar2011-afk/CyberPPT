#!/usr/bin/env python3
"""
PPT Script Project Manager

用法：
    python3 scripts/project_manager.py version
    python3 scripts/project_manager.py doctor
    python3 scripts/project_manager.py route <项目名> [task_type] [source_state] [primary_goal]
    python3 scripts/project_manager.py state <项目名>
    python3 scripts/project_manager.py semantic-check <项目名>
    python3 scripts/project_manager.py understanding-check <项目名>
    python3 scripts/project_manager.py cognitive-init <项目名>
    python3 scripts/project_manager.py cognitive-pack <项目名> <faithful|decision|reconcile>
    python3 scripts/project_manager.py cognitive-check <项目名>
    python3 scripts/project_manager.py evidence-check <项目名>
    python3 scripts/project_manager.py trace-claim <项目名> <C###>
    python3 scripts/project_manager.py case-index
    python3 scripts/project_manager.py case-search <查询词> [数量]
    python3 scripts/project_manager.py experience-pack <项目名> [数量]
    python3 scripts/project_manager.py case-capture <项目名>
    python3 scripts/project_manager.py contract-check <项目名>
    python3 scripts/project_manager.py context-pack <项目名> [deep|compact]
    python3 scripts/project_manager.py editorial-init <项目名>
    python3 scripts/project_manager.py editorial-pack <项目名> <semantic-planning|independent|storyline-candidates|storyline|outline|red-team|red-team-response>
    python3 scripts/project_manager.py editorial-check <项目名> <semantic-planning|independent|storyline-candidates|storyline|outline|red-team-review|red-team>
    python3 scripts/project_manager.py init <项目名>
    python3 scripts/project_manager.py list
    python3 scripts/project_manager.py status <项目名>
    python3 scripts/project_manager.py assemble <项目名>
    python3 scripts/project_manager.py new-page <项目名> <页码> <标题>
    python3 scripts/project_manager.py rhythm-check <项目名>
    python3 scripts/project_manager.py custom-types <项目名>
    python3 scripts/project_manager.py check-coverage <项目名> [页码或pXX文件名]
    python3 scripts/project_manager.py evidence-usage <项目名>
    python3 scripts/project_manager.py gap-summary <项目名>
    python3 scripts/project_manager.py source-inventory <项目名>
    python3 scripts/project_manager.py plan-check <项目名>
    python3 scripts/project_manager.py pages-check <项目名>
    python3 scripts/project_manager.py retire-page <项目名> <页面文件名或片段>
    python3 scripts/project_manager.py handoff <项目名> <decision|expression|outline|authoring|pages> [--reveal]
    python3 scripts/project_manager.py provenance-sync <项目名> [storyline|outline|red-team-review|red-team|all]
    python3 scripts/project_manager.py audit <项目名>
    python3 scripts/project_manager.py notes-check <项目名>
    python3 scripts/project_manager.py style-check <项目名>
    python3 scripts/project_manager.py compare <项目名> <原稿文件> <修订稿文件>
    python3 scripts/project_manager.py approve <项目名> <步骤或页面> [备注]
    python3 scripts/project_manager.py authoring-check <项目名>
    python3 scripts/project_manager.py run <项目名>
"""

import sys
import os
import hashlib
import json
import re
import shutil
import zipfile
from datetime import datetime
from pathlib import Path
from xml.etree import ElementTree

REPO_ROOT = Path(__file__).parent.parent
PROJECTS_DIR = REPO_ROOT / "projects"


# ── 工具函数 ──────────────────────────────────────────────────────────────────

def load_meta(project_path: Path) -> dict:
    meta_file = project_path / "project.json"
    if not meta_file.exists():
        print(f"[错误] 不是有效项目目录（缺少 project.json）：{project_path}")
        sys.exit(1)
    with open(meta_file, encoding="utf-8") as f:
        return json.load(f)


def save_meta(project_path: Path, meta: dict):
    with open(project_path / "project.json", "w", encoding="utf-8") as f:
        json.dump(meta, f, ensure_ascii=False, indent=2)


def resolve_project(name_or_path: str) -> Path:
    p = Path(name_or_path)
    if p.exists() and (p / "project.json").exists():
        return p
    candidate = PROJECTS_DIR / name_or_path
    if candidate.exists() and (candidate / "project.json").exists():
        return candidate
    print(f"[错误] 找不到项目：{name_or_path}")
    sys.exit(1)


def file_has_content(filepath: Path, min_bytes: int = 80) -> bool:
    return filepath.exists() and filepath.stat().st_size > min_bytes


def status_icon(ok: bool) -> str:
    return "✓" if ok else "·"


# ── list ──────────────────────────────────────────────────────────────────────

def cmd_list():
    """列出所有项目。"""
    if not PROJECTS_DIR.exists() or not any(PROJECTS_DIR.iterdir()):
        print("暂无项目。使用 `python3 scripts/project_manager.py init <名称>` 创建。")
        return

    projects = sorted(
        [d for d in PROJECTS_DIR.iterdir() if d.is_dir() and (d / "project.json").exists()]
    )

    if not projects:
        print("暂无项目。")
        return

    print(f"\n{'项目名称':<28} {'创建时间':<18} {'状态':<16} 页面数")
    print("─" * 75)
    for p in projects:
        try:
            meta = load_meta(p)
            created = meta.get("created", "")[:10]
            stage = meta.get("stage", "?")
            pages_dir = p / "pages"
            page_count = len([f for f in pages_dir.iterdir()
                              if f.suffix == ".md" and f.name != "README.md"]) if pages_dir.exists() else 0
            print(f"{p.name:<28} {created:<18} {stage:<16} {page_count}")
        except Exception:
            print(f"{p.name:<28} {'?':<18} {'?':<16} ?")


# ── status ────────────────────────────────────────────────────────────────────

def cmd_status(name_or_path: str):
    """显示项目各阶段文件状态。"""
    project_path = resolve_project(name_or_path)
    meta = load_meta(project_path)

    print(f"\n项目：{meta['name']}")
    print(f"创建：{meta.get('created', '?')[:16]}")
    print(f"状态：{meta.get('stage', '?')}")

    print("\n── 源材料 ──────────────────────────────")
    source_dir = project_path / "source"
    files = [f for f in source_dir.iterdir() if not f.name.startswith(".")] if source_dir.exists() else []
    if files:
        for f in sorted(files):
            size_kb = f.stat().st_size / 1024
            print(f"  ✓ {f.name}  ({size_kb:.1f} KB)")
    else:
        print("  （空）放入源材料后开始生成")

    print("\n── 各阶段文件 ───────────────────────────")
    stage_files = [
        ("Step 0  材料分析", project_path / "analysis" / "00-analysis.md"),
        ("Gate 1  来源底稿", project_path / "analysis" / "01-source-truth-map.md"),
        ("Step 1  决策稿  ", project_path / "decision" / "01-decision.md"),
        ("Step 2  正式提纲", project_path / "outline" / "02-outline.md"),
        ("Gate 2  规划审计", project_path / "outline" / "02-plan-audit.md"),
        ("Step 4  自检结果", project_path / "review" / "04-review.md"),
        ("Gate 3  质量评价", project_path / "review" / "05-evaluation.md"),
        ("机器审计报告   ", project_path / "review" / "05-machine-audit.md"),
        ("output 完整脚本 ", project_path / "output" / "script-final.md"),
        ("output 构图脚本 ", project_path / "output" / "script-imagegen.md"),
    ]
    for label, filepath in stage_files:
        ok = file_has_content(filepath)
        size = f"{filepath.stat().st_size / 1024:.1f} KB" if filepath.exists() else "—"
        print(f"  {status_icon(ok)}  {label}  {size}")

    print("\n── pages/ 页面文件 ──────────────────────")
    pages_dir = project_path / "pages"
    page_files = sorted([
        f for f in pages_dir.iterdir()
        if f.suffix == ".md" and f.name != "README.md"
    ]) if pages_dir.exists() else []

    if page_files:
        for f in page_files:
            ok = file_has_content(f)
            size = f"{f.stat().st_size / 1024:.1f} KB"
            print(f"  {status_icon(ok)}  {f.name}  ({size})")
        print(f"\n  共 {len(page_files)} 页")
    else:
        print("  （空）Step 3 生成后出现")

    print("\n── 确认记录（approvals/）──────────────")
    approvals_dir = project_path / "approvals"
    approval_files = sorted(approvals_dir.glob("*-approval.json")) if approvals_dir.exists() else []
    if approval_files:
        for af in approval_files:
            record = json.loads(af.read_text(encoding="utf-8"))
            target = project_path / record["file"]
            if target.exists():
                stale = _sha256_file(target) != record["sha256"]
            else:
                stale = True
            mark = "⚠ 文件已变更，需重新确认" if stale else "✓ 与确认时一致"
            print(f"  {record['step']:<10} 确认于 {record['approved_at'][:16]}  {mark}")
    else:
        print("  （空）尚未记录任何确认（可选：使用 approve 命令留痕）")


# ── approve ───────────────────────────────────────────────────────────────────
# 把"用户确认"从对话记忆落成文件凭证：记录被确认文件在确认时刻的 SHA-256，
# 后续 status 命令据此判断该文件确认后是否又被改动过。非阻断，仅留痕和提示。

STEP_FILE_MAP = {
    "analysis": "analysis/00-analysis.md",
    "truth": "analysis/01-source-truth-map.md",
    "decision": "decision/01-decision.md",
    "outline": "outline/02-outline.md",
    "evaluation": "review/05-evaluation.md",
    "review": "review/04-review.md",
}


def _sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _legacy_cmd_approve(name_or_path: str, step: str, note: str = ""):
    """记录一次用户确认：把目标文件当前内容的SHA-256和确认时间写入 approvals/。"""
    project_path = resolve_project(name_or_path)

    if step in STEP_FILE_MAP:
        target = project_path / STEP_FILE_MAP[step]
        step_id = step
    else:
        pages_dir = project_path / "pages"
        matches = sorted([
            f for f in pages_dir.iterdir()
            if f.suffix == ".md" and f.name != "README.md" and step.lower() in f.stem.lower()
        ]) if pages_dir.exists() else []
        if not matches:
            print(f"[错误] 未知确认步骤或页面：{step}")
            print("可用步骤：analysis / truth / decision / outline / evaluation / review，或页面文件名片段（如 p05）")
            sys.exit(1)
        target = matches[0]
        step_id = target.stem

    if not file_has_content(target):
        print(f"[错误] 目标文件不存在或仍是占位内容，无法确认：{target}")
        sys.exit(1)

    approvals_dir = project_path / "approvals"
    approvals_dir.mkdir(exist_ok=True)
    record = {
        "step": step_id,
        "file": str(target.relative_to(project_path)),
        "sha256": _sha256_file(target),
        "approved_at": datetime.now().isoformat(timespec="seconds"),
        "note": note,
    }
    record_path = approvals_dir / f"{step_id}-approval.json"
    with open(record_path, "w", encoding="utf-8") as f:
        json.dump(record, f, ensure_ascii=False, indent=2)

    print(f"[✓] 已记录确认：{record_path}")
    print(f"    文件：{record['file']}")
    print(f"    SHA-256：{record['sha256'][:16]}…")
    if note:
        print(f"    备注：{note}")


# ── rhythm-check ──────────────────────────────────────────────────────────────

def _extract_field(content: str, field_name: str) -> str:
    """提取字段值，兼容字段名与值分行书写的页面模板。"""
    pattern = rf"^{re.escape(field_name)}[：:][ \t]*(.*)$"
    m = re.search(pattern, content, re.MULTILINE)
    if not m:
        return ""

    value = m.group(1).strip()
    if value:
        return value

    for raw in content[m.end():].splitlines():
        candidate = raw.strip()
        if not candidate:
            continue
        if candidate == "---" or FIELD_LINE_RE.match(candidate):
            return ""
        return candidate
    return ""


FIELD_LINE_RE = re.compile(r"^[^\n：:]{2,24}[：:][ \t]*.*$", re.MULTILINE)


def _extract_block(content: str, marker: str) -> str:
    """提取 `字段名：` 后的多行内容，遇到分隔线或下一个顶级字段停止。"""
    pattern = rf"^{re.escape(marker)}[：:][ \t]*(.*)$"
    m = re.search(pattern, content, re.MULTILINE)
    if not m:
        return ""

    lines = []
    first = m.group(1).strip()
    if first:
        lines.append(first)

    rest = content[m.end():].splitlines()
    for raw in rest:
        line = raw.rstrip()
        stripped = line.strip()
        if stripped == "---":
            break
        if stripped and FIELD_LINE_RE.match(stripped) and not line.startswith((" ", "\t", "-")):
            break
        lines.append(line)

    return "\n".join(lines).strip()


def _extract_section(content: str, marker: str) -> str:
    """提取 `上屏文字：`、`内容关系草图：` 等段落，遇到 `---` 停止。"""
    pattern = rf"^{re.escape(marker)}[：:][ \t]*$"
    m = re.search(pattern, content, re.MULTILINE)
    if not m:
        inline = _extract_block(content, marker)
        return inline

    rest = content[m.end():]
    end = rest.find("\n---")
    section = rest[:end] if end != -1 else rest
    return section.strip()


def _extract_page_heading(content: str, fallback_name: str) -> str:
    m = re.search(r"^##\s+(.+)$", content, re.MULTILINE)
    if m:
        return m.group(1).strip()
    return fallback_name


def _clean_interface_value(value: str) -> str:
    """清理模板占位说明，避免进入构图输入稿。"""
    value = value.strip()
    placeholders = {
        "后台字段，不上屏。",
        "后台字段，不上屏",
        "可省略",
        "无",
    }
    return "" if value in placeholders else value


def _clean_onscreen_for_imagegen(onscreen: str) -> str:
    """移除页面合同字段名，只保留实际可见文字。"""
    cleaned: list[str] = []
    for raw in onscreen.splitlines():
        stripped = raw.strip()
        if re.fullmatch(r"(?:标题|副标题|主判断)[：:]", stripped):
            continue
        auxiliary = re.fullmatch(r"辅助区[：:]\s*(.*)", stripped)
        if auxiliary:
            value = auxiliary.group(1).strip()
            if value:
                cleaned.append(value)
            continue
        cleaned.append(raw)
    return re.sub(r"\n{3,}", "\n\n", "\n".join(cleaned)).strip()


def _first_sentence(text: str) -> str:
    """取一段中文说明的第一句，用作构图稿中的短语义提示。"""
    text = re.sub(r"\s+", " ", text.strip())
    if not text:
        return ""
    m = re.search(r"(.+?。)", text)
    return m.group(1).strip() if m else text


def _trim_sentence_end(text: str) -> str:
    return text.strip().rstrip("。；;，,：:！？!?")


def _density_instruction(value: str) -> str:
    mapping = {
        "标准": "保持适中信息密度和充足留白",
        "高密度专项": "在一页内完整呈现多组关键信息，通过明显层级和分区保证快速阅读",
        "超高密度专项": "优先建立清晰阅读路径，必要时压缩装饰元素，为核心信息保留空间",
    }
    return mapping.get(value, "保证信息完整、层级清晰并具有充足留白")


def _derive_core_semantic_relation(content: str, semantic_skeleton: str, relation_sketch: str) -> str:
    relation = _clean_interface_value(_extract_block(content, "本页内容关系判断"))
    if relation:
        return relation
    return _first_sentence(semantic_skeleton) or _first_sentence(relation_sketch)


def _derive_visual_priority(visual_focus: str, semantic_skeleton: str) -> str:
    if visual_focus and semantic_skeleton:
        return f"主视觉中心：{visual_focus}；辅助组织关系：{_first_sentence(semantic_skeleton)}"
    if visual_focus:
        return f"主视觉中心：{visual_focus}"
    if semantic_skeleton:
        return f"主视觉中心与辅助信息按语义骨架组织：{_first_sentence(semantic_skeleton)}"
    return ""


def _derive_compact_visual_priority(visual_focus: str, semantic_skeleton: str) -> str:
    if visual_focus:
        return f"主视觉中心：{visual_focus}"
    if semantic_skeleton:
        return f"主视觉中心：{_first_sentence(semantic_skeleton)}"
    return ""


def _build_imagegen_page(content: str, fallback_name: str) -> str:
    """生成可逐页直接提交给 IMAGE-2 的自然语言视觉提示词。"""
    from ppt_script.imagegen import build_semantic_summary
    from ppt_script.visual_drawing import extract_image_prompt, format_sketch_for_imagegen, has_direct_image_prompt
    from ppt_script.visual_focus import parse_visual_focus, render_visual_narrative

    heading = _extract_page_heading(content, fallback_name)
    onscreen = _clean_onscreen_for_imagegen(_extract_section(content, "上屏文字"))
    direct_prompt = extract_image_prompt(content) if has_direct_image_prompt(content) else ""
    if direct_prompt:
        cleaned = format_sketch_for_imagegen(direct_prompt)
        return "\n\n".join(
            [
                f"## {heading}",
                "【全局】中文正式汇报PPT内容页；克制、层级清晰；禁止装饰图标堆与无关科技感背景。画布比例由制作环境决定。",
                "【生图提示词】",
                cleaned,
                "【画面文字白名单】块内文字必须逐字使用下列原文，禁止改写、禁止新增：",
                onscreen,
            ]
        ).strip()

    relation_sketch = _extract_section(content, "内容关系草图")
    must_keep = _extract_block(content, "必须保留内容")
    key_message = _clean_interface_value(
        _extract_block(content, "页面结论") or _extract_block(content, "核心结论")
    )
    visual_focus = _clean_interface_value(_extract_block(content, "视觉转译重点"))
    focus_contract = parse_visual_focus(content)
    semantic_skeleton = _clean_interface_value(_extract_block(content, "语义骨架说明"))
    avoid = _clean_interface_value(_extract_block(content, "不建议的直译方式"))
    landing = _clean_interface_value(_extract_block(content, "落图策略建议"))
    core_semantic_relation = _derive_core_semantic_relation(content, semantic_skeleton, relation_sketch)
    semantic_summary = build_semantic_summary(content)

    paragraphs = [
        f"## {heading}",
        "",
        "【IMAGE-2 逐页提示词】",
        "",
        "请生成一张完整的中文PPT内容页。整体采用正式、克制、专业的内部汇报视觉语言，信息层级清晰，留白充足，避免通用卡片墙、装饰性图标堆叠和与业务无关的科技感背景。画布比例由实际制作环境或调用方确定，脚本不作固定约定。",
    ]
    if key_message:
        paragraphs.append(f"本页要让观众首先理解：{key_message}")
    if semantic_summary:
        paragraphs.append(f"理解页面时请把握以下业务语义，但不要把这段说明生成到画面中：{semantic_summary}")
    if core_semantic_relation:
        paragraphs.append(f"画面必须准确呈现这一内容关系：{core_semantic_relation}")
    composition = []
    if focus_contract.center and focus_contract.role and key_message:
        composition.append(_trim_sentence_end(render_visual_narrative(key_message, focus_contract)))
    elif visual_focus:
        composition.append(_trim_sentence_end(visual_focus))
    if semantic_skeleton:
        composition.append(_trim_sentence_end(semantic_skeleton))
    if composition:
        paragraphs.append("具体构图要求：" + "；".join(composition) + "。")
    if landing:
        paragraphs.append(_density_instruction(landing) + "，优先保证阅读顺序、核心关系和关键文字清晰可辨。")
    if avoid:
        paragraphs.append(f"避免以下错误表达：{_trim_sentence_end(avoid)}。")
    cleaned_sketch = format_sketch_for_imagegen(relation_sketch) if relation_sketch else ""
    if cleaned_sketch:
        paragraphs.append(
            "绘制说明书（必须遵守，但其中的分段标题如【可绘制节点】不得生成到画面文字中）：\n"
            + cleaned_sketch
        )
    if must_keep:
        paragraphs.append(f"保真要求：必须完整保留这些关键信息——{_trim_sentence_end(must_keep)}。这些说明本身不得作为新增画面文字。")
    paragraphs.extend([
        "画面文字实行严格白名单：只有下方【画面文字白名单】中的文字允许出现在页面上。不得新增、改写或遗漏文字，不得把提示词、字段名、Markdown标记、业务理解说明或构图说明生成到画面中。",
        "",
        "【画面文字白名单】",
        onscreen,
    ])
    return "\n\n".join(part for part in paragraphs if part is not None).strip()


def _build_imagegen_compact_page(content: str, fallback_name: str) -> str:
    """生成直接投喂生图模型的紧凑构图输入页。"""
    from ppt_script.imagegen import build_compact_understanding_context
    from ppt_script.visual_drawing import extract_image_prompt, format_sketch_for_imagegen, has_direct_image_prompt
    from ppt_script.visual_focus import parse_visual_focus, render_compact_visual_priority

    heading = _extract_page_heading(content, fallback_name)
    onscreen = _clean_onscreen_for_imagegen(_extract_section(content, "上屏文字"))
    if has_direct_image_prompt(content):
        cleaned = format_sketch_for_imagegen(extract_image_prompt(content))
        return "\n\n".join(
            [
                f"## {heading}",
                "【任务】",
                "生成一张完整的PPT内容页画面；画布比例由实际制作环境或调用方确定。",
                "【生图提示词】",
                cleaned,
                "【内容锁定】",
                onscreen or "",
            ]
        ).strip()

    relation_sketch = _extract_section(content, "内容关系草图")

    structure = _clean_interface_value(_extract_block(content, "结构意图") or _extract_block(content, "结构说明"))
    business_relation = _clean_interface_value(_extract_block(content, "业务关系"))
    visual_focus = _clean_interface_value(_extract_block(content, "视觉转译重点"))
    focus_contract = parse_visual_focus(content)
    semantic_type = _clean_interface_value(_extract_block(content, "推荐主语义图类型"))
    semantic_skeleton = _clean_interface_value(_extract_block(content, "语义骨架说明"))
    avoid = _clean_interface_value(_extract_block(content, "不建议的直译方式"))
    landing = _clean_interface_value(_extract_block(content, "落图策略建议"))
    core_semantic_relation = _derive_core_semantic_relation(content, semantic_skeleton, relation_sketch)
    visual_priority = render_compact_visual_priority(focus_contract) if focus_contract.center and focus_contract.role else _derive_compact_visual_priority(visual_focus, semantic_skeleton)

    lines = [f"## {heading}", "", "页面性质：内容页", "", "【任务】", "生成一张完整的PPT内容页画面；画布比例由实际制作环境或调用方确定。", ""]
    lines.append("【内容锁定】")
    if onscreen:
        lines.append(onscreen)
    lines.append("")
    lines.append("保真约束：必须保留关键数字、主体名称、产品名称、阶段节点和合规边界；不得新增画面文字。")
    understanding = build_compact_understanding_context(content)
    if understanding:
        lines.extend(["", understanding])
    lines.append("")
    lines.append("【构图指令】")
    if core_semantic_relation:
        lines.append(f"核心语义关系：{core_semantic_relation}")
    if visual_priority:
        lines.append(f"视觉主次：{visual_priority}")
    if structure:
        lines.append(f"结构意图：{structure}")
    if business_relation:
        lines.append(f"业务关系：{business_relation}")
    if semantic_type:
        lines.append(f"推荐主语义图类型：{semantic_type}")
    if relation_sketch.strip():
        lines.append("绘制说明书：")
        lines.append(relation_sketch.strip())
    if avoid:
        lines.append(f"不建议的直译方式：{avoid}")
    if landing:
        lines.append(f"落图策略：{landing}")
    lines.append("")
    lines.append("【执行约束】")
    lines.append("1. 一个页面只表达一个核心观点，主视觉必须直接服务核心语义关系。")
    lines.append("2. 保持正式、克制、清晰的中文汇报风格，信息层级明确，避免装饰性图形喧宾夺主。")
    lines.append("3. 只有【内容锁定】具有文字渲染权限；【页面理解上下文】、【构图指令】和【执行约束】仅供理解，不得出现在画面中。")
    lines.append("4. 画面文字逐字使用【内容锁定】，不得新增、改写、遗漏，不得生成字段名和Markdown标记。")

    return "\n".join(lines).strip()


def cmd_rhythm_check(name_or_path: str):
    """扫描 pages/ 目录，检查连续页是否过度重复同一种结构说明或主语义图类型。"""
    project_path = resolve_project(name_or_path)
    pages_dir = project_path / "pages"
    page_files = sorted([
        f for f in pages_dir.iterdir()
        if f.suffix == ".md" and f.name != "README.md"
    ]) if pages_dir.exists() else []

    if not page_files:
        print("[错误] pages/ 目录为空，尚无页面文件可检查。")
        sys.exit(1)

    rows = []
    for f in page_files:
        content = f.read_text(encoding="utf-8")
        structure = _extract_field(content, "结构说明") or _extract_field(content, "结构意图")
        semantic = _extract_field(content, "推荐主语义图类型")
        rows.append((f.name, structure, semantic))

    print(f"\n项目：{project_path.name}　共 {len(rows)} 页\n")
    for name, structure, semantic in rows:
        print(f"{name}\n  结构说明：{structure or '(空)'}\n  推荐主语义图类型：{semantic or '(空)'}")

    # 连续三页（含）以上字段值相同，视为节奏重复，需要提示
    def find_runs(values):
        runs = []
        i = 0
        n = len(values)
        while i < n:
            j = i
            while j + 1 < n and values[j + 1] and values[j + 1] == values[i]:
                j += 1
            if values[i] and (j - i + 1) >= 3:
                runs.append((i, j, values[i]))
            i = j + 1
        return runs

    structures = [r[1] for r in rows]
    semantics = [r[2] for r in rows]

    warnings = []
    for i, j, val in find_runs(structures):
        pages = "、".join(rows[k][0] for k in range(i, j + 1))
        warnings.append(f"结构说明连续重复 {j - i + 1} 页（{val}）：{pages}")
    for i, j, val in find_runs(semantics):
        pages = "、".join(rows[k][0] for k in range(i, j + 1))
        warnings.append(f"推荐主语义图类型连续重复 {j - i + 1} 页（{val}）：{pages}")

    print("\n── 节奏检查结果 ─────────────────────────")
    if warnings:
        for w in warnings:
            print(f"  ⚠ {w}")
        print("\n建议：对照页面业务关系重新判断其中部分页面的结构意图，避免连续三页以上同构图。")
    else:
        print("  ✓ 未发现连续三页以上重复使用同一结构说明或主语义图类型。")


# ── custom-types ──────────────────────────────────────────────────────────────

CUSTOM_TYPE_FIELDS = ["推荐主语义图类型", "结构说明", "业务关系"]


def cmd_custom_types(name_or_path: str):
    """扫描 pages/ 目录，列出所有标注为"自定义"的字段值，并标记同项目内重复出现的自定义类型。"""
    project_path = resolve_project(name_or_path)
    pages_dir = project_path / "pages"
    page_files = sorted([
        f for f in pages_dir.iterdir()
        if f.suffix == ".md" and f.name != "README.md"
    ]) if pages_dir.exists() else []

    if not page_files:
        print("[错误] pages/ 目录为空，尚无页面文件可检查。")
        sys.exit(1)

    # entries: field -> custom_label -> [page_name, ...]
    entries = {field: {} for field in CUSTOM_TYPE_FIELDS}

    for f in page_files:
        content = f.read_text(encoding="utf-8")
        for field in CUSTOM_TYPE_FIELDS:
            value = _extract_field(content, field)
            if value.startswith("自定义"):
                # 取"自定义："之后、"+ 理由"之前的部分作为类型名称
                label = value.split("+")[0].strip()
                entries[field].setdefault(label, []).append(f.name)

    print(f"\n项目：{project_path.name}　自定义类型扫描\n")

    found_any = False
    repeated_any = False
    for field in CUSTOM_TYPE_FIELDS:
        labels = entries[field]
        if not labels:
            continue
        found_any = True
        print(f"【{field}】")
        for label, pages in labels.items():
            mark = "⚠ 重复" if len(pages) >= 2 else ""
            print(f"  {label}  （{len(pages)}页：{'、'.join(pages)}）{mark}")
            if len(pages) >= 2:
                repeated_any = True
        print()

    if not found_any:
        print("  本项目未使用「自定义」，标准词表已覆盖所有页面。")
        return

    if repeated_any:
        print("── 建议 ─────────────────────────────")
        print("  以上标记⚠的自定义类型在本项目内重复出现2次以上，说明标准词表确实覆盖不到这类常见关系。")
        print("  建议在 review/04-review.md 中提出补充标准词表的建议（词条名称+定义+适用场景），")
        print("  由用户决定是否人工同步进 templates/full-page.md 和第二段视觉制作规则的对应表格。")
    else:
        print("── 建议 ─────────────────────────────")
        print("  自定义类型均为一次性使用，暂不构成补充标准词表的理由。")


# ── evidence-usage ───────────────────────────────────────────────────────────
# V3 新项目统一使用 Source Truth Map 的 S### 来源ID；旧项目的 F01 编号继续兼容。
# 工具优先读取 analysis/01-source-truth-map.md，并核查页面材料依据字段的双向覆盖。

SOURCE_ID_RE = re.compile(r"\bS\d{3,4}\b", re.IGNORECASE)
LEGACY_FACT_ID_RE = re.compile(r"\bF\d+\b", re.IGNORECASE)
SOURCE_TABLE_ID_RE = re.compile(r"^\|\s*(S\d{3,4})\s*\|", re.MULTILINE | re.IGNORECASE)
FACT_ID_RE = re.compile(r"^\|\s*(F\d+)\s*\|", re.MULTILINE | re.IGNORECASE)


def _dedupe_ids(ids: list[str]) -> list[str]:
    seen: list[str] = []
    for value in ids:
        normalized = value.upper()
        if normalized not in seen:
            seen.append(normalized)
    return seen


def _read_fact_ids(project_path: Path) -> list:
    """读取项目来源条目ID；V3 S###优先，旧版F##仅作回退。"""
    truth_file = project_path / "analysis" / "01-source-truth-map.md"
    if truth_file.exists():
        source_ids = _dedupe_ids(SOURCE_TABLE_ID_RE.findall(truth_file.read_text(encoding="utf-8")))
        if source_ids:
            return source_ids

    analysis_file = project_path / "analysis" / "00-analysis.md"
    if not analysis_file.exists():
        return []
    return _dedupe_ids(FACT_ID_RE.findall(analysis_file.read_text(encoding="utf-8")))


def _read_page_fact_refs(page_text: str) -> list:
    """读取页面中的V3来源ID和旧版事实ID，保持字段出现顺序并去重。"""
    ids: list[str] = []
    for field in ("材料依据ID", "引用Source ID", "引用来源ID", "引用事实清单ID"):
        raw = _extract_block(page_text, field)
        if not raw:
            continue
        ids.extend(SOURCE_ID_RE.findall(raw))
        ids.extend(LEGACY_FACT_ID_RE.findall(raw))
    return _dedupe_ids(ids)


def _read_page_source_refs(page_text: str) -> list:
    """仅读取V3 S###来源ID。"""
    return [value for value in _read_page_fact_refs(page_text) if value.startswith("S")]


def cmd_evidence_usage(name_or_path: str):
    """核查Source Truth Map（S###）或旧事实清单（F##）与页面引用之间的双向覆盖。"""
    from ppt_script.commands.coverage import page_files

    project_path = resolve_project(name_or_path)
    fact_ids = _read_fact_ids(project_path)

    if not fact_ids:
        print("[提示] 未发现 Source Truth Map 的 S### 来源ID或旧版F##事实编号，无法执行引用核查。")
        print("V3正式项目必须先生成 analysis/01-source-truth-map.md；旧项目可继续使用 analysis/00-analysis.md 中的F##编号。")
        return

    pages = page_files(project_path)

    if not pages:
        print("[错误] pages/ 目录为空，尚无页面文件可核查。")
        sys.exit(1)

    used = {}
    for f in pages:
        content = f.read_text(encoding="utf-8")
        for fid in _read_page_fact_refs(content):
            used.setdefault(fid, []).append(f.name)

    print(f"\n来源条目引用核查：{project_path.name}")
    print(f"来源条目共 {len(fact_ids)} 条：{'、'.join(fact_ids)}\n")

    unused = [fid for fid in fact_ids if fid not in used]
    unknown = sorted(fid for fid in used if fid not in fact_ids)

    if unused:
        print("⚠ 以下来源条目未被任何页面引用（核实是否遗漏，或确属有意不用）：")
        for fid in unused:
            print(f"  - {fid}")
    else:
        print("✓ 所有来源条目均被至少一页引用。")

    if unknown:
        print("\n⚠ 以下页面引用的编号在来源底稿中不存在（核实是否编号写错）：")
        for fid in unknown:
            print(f"  - {fid}：{'、'.join(used[fid])}")

    print(f"\n共 {len(pages)} 页，来源条目 {len(fact_ids)} 条，未引用 {len(unused)} 条，未知引用 {len(unknown)} 处。")
    print("提示：本工具仅提示疑点，不做自动判定；未引用不代表错误，只是提醒复核。")


# ── gap-summary ──────────────────────────────────────────────────────────────
# 汇总所有页面的「字段缺口声明」，供 Step 4 自检和用户判断是否需要补充或
# 外部核实，避免缺口被声明后就被默默忽略。非阻断，仅汇总提示。

GAP_FIELD = "字段缺口声明"


def cmd_gap_summary(name_or_path: str):
    """汇总各页「字段缺口声明」字段，列出仍未处理的内容缺口。"""
    from ppt_script.commands.coverage import page_files

    project_path = resolve_project(name_or_path)
    pages = page_files(project_path)

    if not pages:
        print("[错误] pages/ 目录为空，尚无页面文件可核查。")
        sys.exit(1)

    print(f"\n字段缺口声明汇总：{project_path.name}\n")
    total = 0
    for f in pages:
        content = f.read_text(encoding="utf-8")
        gap = _clean_interface_value(_extract_block(content, GAP_FIELD))
        if gap:
            total += 1
            print(f"── {f.name} ──\n  {gap}\n")

    if total == 0:
        print("  未发现任何页面声明字段缺口（或本项目未使用该字段）。")
    else:
        print(f"共 {total} 页声明了字段缺口，请核实是否需要用户补充或外部核实，再运行 assemble 组装。")


# ── assemble ──────────────────────────────────────────────────────────────────

PAGE_NUM_RE = re.compile(r"^p(\d+)-")


def _build_outline_index_entry(content: str, filename: str) -> dict:
    """从单页文件提取机器可读的索引字段，供脚本化校验使用（人工审阅仍以Markdown为准）。"""
    m = PAGE_NUM_RE.match(filename)
    page_num = int(m.group(1)) if m else None

    from ppt_script.script_parser import parse_script
    parsed = parse_script(content)
    slide = parsed[0] if parsed else None
    return {
        "file": f"pages/{filename}",
        "page": page_num,
        "title": _extract_page_heading(content, filename),
        "page_nature": _clean_interface_value(_extract_block(content, "页面性质")),
        "page_role": _clean_interface_value(_extract_block(content, "页面职能")),
        "expression_node": _clean_interface_value(_extract_block(content, "表达节点")),
        "semantic_type": _clean_interface_value(_extract_block(content, "推荐主语义图类型")),
        "structure": _clean_interface_value(
            _extract_block(content, "结构意图") or _extract_block(content, "结构说明")
        ),
        "business_relation": _clean_interface_value(_extract_block(content, "业务关系")),
        "source_ids": _read_page_source_refs(content),
        "evidence_ids": _read_page_fact_refs(content),
        "gap_declaration": _clean_interface_value(_extract_block(content, GAP_FIELD)),
        "speaker_notes_present": bool(slide and slide.has_speaker_notes),
        "speaker_notes_seconds": slide.speaker_notes_seconds if slide else None,
    }


def _legacy_cmd_assemble(name_or_path: str):
    """将 pages/ 目录下页面文件组装为完整审稿版和构图输入版。"""
    project_path = resolve_project(name_or_path)
    meta = load_meta(project_path)

    pages_dir = project_path / "pages"
    page_files = sorted([
        f for f in pages_dir.iterdir()
        if f.suffix == ".md" and f.name != "README.md"
    ]) if pages_dir.exists() else []

    if not page_files:
        print("[错误] pages/ 目录为空，尚无页面文件可组装。")
        sys.exit(1)

    output_path = project_path / "output" / "script-final.md"
    imagegen_path = project_path / "output" / "script-imagegen.md"
    index_path = project_path / "output" / "outline-index.json"

    lines = []
    imagegen_lines = []
    index_entries = []

    # 文件头
    lines.append(f"# {meta['name']} · PPT内容脚本")
    lines.append(f"\n生成时间：{datetime.now().strftime('%Y-%m-%d %H:%M')}")
    lines.append(f"页面总数：{len(page_files)}")
    lines.append("\n用途说明：本文件为完整审稿版，保留页面职能、表达节点、原文依据、内容关系草图、语义骨架、自检接口和视觉转译接口，用于人工审稿、溯源、自检和返修。直接用于IMAGE-2生图时，使用同目录下的 `script-imagegen.md`。")
    lines.append("\n---\n")

    imagegen_lines.append(f"# {meta['name']} · PPT构图输入脚本")
    imagegen_lines.append(f"\n生成时间：{datetime.now().strftime('%Y-%m-%d %H:%M')}")
    imagegen_lines.append(f"页面总数：{len(page_files)}")
    imagegen_lines.append("\n用途说明：本文件用于传入第二段视觉制作规则或生图Prompt生成流程。已删除详细溯源和审稿说明，保留内容锁定、保真约束、核心语义关系、视觉主次、结构意图、业务关系、语义骨架、内容关系草图和直译风险。")
    imagegen_lines.append("\n全局约束：页面可见文字只能来自各页【内容锁定】；【构图接口】仅用于判断构图，不得作为画面文字生成。")
    imagegen_lines.append("\n---\n")


    # 引用提纲（如存在）
    outline_file = project_path / "outline" / "02-outline.md"
    if file_has_content(outline_file):
        lines.append("## 提纲索引\n")
        lines.append(outline_file.read_text(encoding="utf-8").strip())
        lines.append("\n\n---\n")

    # 逐页合并
    lines.append("## 页面脚本\n")
    for i, f in enumerate(page_files, 1):
        content = f.read_text(encoding="utf-8").strip()
        if not content:
            print(f"  [跳过] {f.name}（文件为空）")
            continue
        lines.append(content)
        lines.append("\n\n---\n")
        imagegen_lines.append(_build_imagegen_page(content, f.stem))
        imagegen_lines.append("\n\n---\n")
        index_entries.append(_build_outline_index_entry(content, f.name))

    output_path.write_text("\n".join(lines), encoding="utf-8")
    imagegen_path.write_text("\n".join(imagegen_lines), encoding="utf-8")

    index_data = {
        "schema": "ppt-script.outline_index.v1",
        "project": meta["name"],
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "pages": index_entries,
    }
    index_path.write_text(
        json.dumps(index_data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )

    # 更新元数据
    meta["stage"] = "assembled"
    meta["assembled"] = datetime.now().isoformat()
    meta["imagegen_assembled"] = datetime.now().isoformat()
    save_meta(project_path, meta)

    size_kb = output_path.stat().st_size / 1024
    imagegen_size_kb = imagegen_path.stat().st_size / 1024
    print(f"\n[✓] 完整审稿版已生成：{output_path}")
    print(f"    页面数：{len(page_files)}  文件大小：{size_kb:.1f} KB")
    print(f"[✓] 构图输入版已生成：{imagegen_path}")
    print(f"    页面数：{len(page_files)}  文件大小：{imagegen_size_kb:.1f} KB")
    print(f"[✓] 派生索引已生成：{index_path}（供脚本化校验用，非人工阅读文件）")
    print(f"\n下一步：将 output/script-imagegen.md 按页直接提交给 IMAGE-2；output/script-final.md 用于审稿、溯源和自检。")


# ── new-page ──────────────────────────────────────────────────────────────────

def cmd_new_page(name_or_path: str, page_num: str, title: str):
    """在 pages/ 目录新建一个空白页面文件。"""
    project_path = resolve_project(name_or_path)
    from ppt_script.workflow import assert_page_authoring_allowed

    try:
        assert_page_authoring_allowed(project_path)
    except ValueError as exc:
        print(f"[错误] {exc}")
        sys.exit(1)
    pages_dir = project_path / "pages"
    pages_dir.mkdir(exist_ok=True)

    # 格式化页码为两位数
    try:
        num = int(page_num)
    except ValueError:
        print(f"[错误] 页码必须是数字：{page_num}")
        sys.exit(1)

    filename = f"p{num:02d}-{title}.md"
    filepath = pages_dir / filename

    if filepath.exists():
        print(f"[错误] 文件已存在：{filepath}")
        sys.exit(1)

    # 内容组成契约见 config/rules.yaml → page_composition
    content = f"""## 第{num}页：{title}

页面性质：内容页

---

上屏文字：

标题：
{title}

副标题：

主判断：

辅助区：

---

生图提示词：

（布局/主次/箭头/禁画。标题与模块文字全部逐字来自上屏，禁止改写、禁止新增。）

---

页面类型：
推荐主语义图类型：
落图策略建议：高密度专项

---

审稿字段（不进生图）：

所属章节：
页面使命：
核心结论：
页面职能：
表达节点：
页面必要性：
与前页关系：
与后页关系：
页面形态：

原文依据：
对应原文章节：
对应段落或小标题：
关键数字或主体来源：
材料依据ID：
引用事实清单ID：
必须保留内容：
可压缩内容：
字段缺口声明：无

---

备注讲解词（不进生图）：

开场承接：

核心讲解：

重点强调：

边界说明：

转场语：

预计讲解时长：60秒
"""
    filepath.write_text(content, encoding="utf-8")

    print(f"[✓] 已创建：{filepath}")


# ── check-coverage ───────────────────────────────────────────────────────────
# 轻量级"源文件覆盖面核查"：扫描原文中的并列枚举词组与数字，逐项检查是否在
# 对应页面文件的"原文依据"/"上屏文字"字段中出现，列出疑似遗漏项供人工复核。
# 不做强匹配判定，只提示疑点。

_ITEM = r"[一-鿿A-Za-z0-9]{2,10}"
# 枚举末项后常见的"延伸词"，用于在没有顿号/标点收尾时判断枚举边界
_ENUM_TAIL = r"等|的|全流程|全要素|全周期|全方位|全链条|全产业链|[，。：；、\s]|$"
ENUM_RE = re.compile(rf"({_ITEM}(?:、{_ITEM}){{2,}})(?={_ENUM_TAIL})")

# 枚举首项常见的引导词（动词/连接词），核查时从首项中剥离，避免把动词误当作枚举内容
_HEAD_WORDS = [
    "解决", "支持", "实现", "制定", "聚焦", "促进", "联合", "构建", "纳入",
    "包括", "涉及", "将", "对接", "形成", "打造", "建立", "开展", "推动",
]


def _strip_head_word(item: str) -> str:
    for w in sorted(_HEAD_WORDS, key=len, reverse=True):
        if item.startswith(w) and len(item) > len(w):
            return item[len(w):]
    return item
NUM_RE = re.compile(
    r"\d+(?:\.\d+)?\s?(?:%|万元|亿元|万|亿|个|项|家|人|年|倍|户|次|套|条)(?:以上|以下|以内)?"
)

# 顶级/次级标题行：用于把原文切分为"章节块"，给页面定位对应原文区段
_HEADING_RE = re.compile(
    r"^([一二三四五六七八九十]+、.+"
    r"|（[一二三四五六七八九十]+）.+"
    r"|场景[一二三四五六七八九十\d]+[:：].+"
    r"|\d+\.\s?\S.+)$"
)


def _bigrams(s: str) -> set:
    s = re.sub(r"[\s\W]", "", s)
    return {s[i:i + 2] for i in range(len(s) - 1)} if len(s) > 1 else {s}


def _title_overlap_score(title: str, heading: str) -> float:
    a, b = _bigrams(title), _bigrams(heading)
    if not a or not b:
        return 0.0
    return len(a & b) / min(len(a), len(b))


def _read_docx_lines(docx_path: Path) -> list:
    """读取DOCX正文段落，供覆盖率核查使用。"""
    try:
        with zipfile.ZipFile(docx_path) as archive:
            document_xml = archive.read("word/document.xml")
    except (KeyError, OSError, zipfile.BadZipFile):
        return []

    root = ElementTree.fromstring(document_xml)
    namespace = {"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"}
    lines = []
    for paragraph in root.findall(".//w:p", namespace):
        text = "".join(node.text or "" for node in paragraph.findall(".//w:t", namespace)).strip()
        if text:
            lines.append(text)
    return lines


def _read_source_lines(project_path: Path) -> list:
    source_dir = project_path / "source"
    lines = []
    if not source_dir.exists():
        return lines
    for f in sorted(source_dir.iterdir()):
        suffix = f.suffix.lower()
        if suffix in (".txt", ".md"):
            source_text = f.read_text(encoding="utf-8", errors="ignore").splitlines()
        elif suffix == ".docx":
            source_text = _read_docx_lines(f)
        else:
            continue
        for i, raw in enumerate(source_text, 1):
            lines.append((f.name, i, raw))
    return lines


def _locate_source_block(source_lines: list, page_title: str) -> list:
    """根据页面标题定位最匹配的原文章节标题，返回该标题到下一个标题之间的行。"""
    headings = [
        (idx, fname, lineno, text)
        for idx, (fname, lineno, text) in enumerate(source_lines)
        if _HEADING_RE.match(text.strip())
    ]
    if not headings:
        return None  # 没有可识别的标题结构，无法定位，跳过核查

    best = max(headings, key=lambda h: _title_overlap_score(page_title, h[3]))
    if _title_overlap_score(page_title, best[3]) <= 0.15:
        return None  # 匹配度太低，无法可靠定位，跳过核查（不退化为全文，避免误报）

    start_idx = best[0]
    end_idx = len(source_lines)
    for idx, _fname, _lineno, _text in headings:
        if idx > start_idx:
            end_idx = idx
            break
    return source_lines[start_idx:end_idx]


def _extract_enums_and_nums(block_lines: list) -> tuple:
    enums = []  # (fname, lineno, [items])
    nums = []   # (fname, lineno, text)
    for fname, lineno, text in block_lines:
        for m in ENUM_RE.finditer(text):
            items = m.group(1).split("、")
            enums.append((fname, lineno, items))
        for m in NUM_RE.finditer(text):
            nums.append((fname, lineno, m.group(0).strip()))
    return enums, nums


def _extract_page_check_text(page_text: str) -> str:
    """提取页面文件中的'原文依据'与'上屏文字'字段文本，作为核查范围。"""
    parts = []
    for marker in ("原文依据：", "上屏文字："):
        idx = page_text.find(marker)
        if idx == -1:
            continue
        end = page_text.find("\n---", idx)
        segment = page_text[idx: end if end != -1 else len(page_text)]
        parts.append(segment)
    return "\n".join(parts) if parts else page_text


def _check_page_coverage(project_path: Path, page_file: Path, source_lines: list) -> dict:
    page_text = page_file.read_text(encoding="utf-8")
    check_text = _extract_page_check_text(page_text)
    check_text_compact = re.sub(r"\s", "", check_text)

    # 从文件名提取标题，如 p08-场景一-成果可信存证与鉴定.md → 场景一-成果可信存证与鉴定
    title = re.sub(r"^p\d+-", "", page_file.stem).replace("-", "")

    block = _locate_source_block(source_lines, title)
    if block is None:
        return {"page": page_file.name, "located": False, "missing_enum_groups": [], "missing_nums": []}
    enums, nums = _extract_enums_and_nums(block)

    missing_enum_groups = []
    for fname, lineno, items in enums:
        cleaned = [_strip_head_word(items[0])] + items[1:]
        if "的" in cleaned[-1]:
            cleaned[-1] = cleaned[-1].split("的")[0]
        cleaned = [it for it in cleaned if it]
        missing = [it for it in cleaned if it not in check_text_compact]
        # 同一组里只有 1 项缺失也提示，但全组都缺（说明该枚举整体未提及）单独标注
        if missing:
            missing_enum_groups.append({
                "source": f"{fname}:{lineno}",
                "all_items": cleaned,
                "missing_items": missing,
            })

    missing_nums = []
    for fname, lineno, text in nums:
        compact = text.replace(" ", "")
        if compact not in check_text_compact and text not in check_text_compact:
            missing_nums.append({"source": f"{fname}:{lineno}", "value": text})

    return {
        "page": page_file.name,
        "located": True,
        "missing_enum_groups": missing_enum_groups,
        "missing_nums": missing_nums,
    }


def cmd_check_coverage(name_or_path: str, page_selector: str = None):
    """核查页面文件对原文枚举/数字信息的覆盖面，列出疑似遗漏项。"""
    from ppt_script.commands.coverage import select_pages

    project_path = resolve_project(name_or_path)
    page_files = select_pages(project_path, page_selector)

    if not page_files:
        print("[错误] pages/ 目录为空，没有可核查的页面文件。")
        sys.exit(1)

    if page_selector and not page_files:
        print(f"[错误] 找不到匹配 '{page_selector}' 的页面文件。")
        sys.exit(1)

    source_lines = _read_source_lines(project_path)
    if not source_lines:
        print("[错误] source/ 目录为空或无 txt/md 源文件，无法核查。")
        sys.exit(1)

    print(f"\n源文件覆盖面核查：{project_path.name}")
    print("=" * 70)

    total_doubt = 0
    for page_file in page_files:
        result = _check_page_coverage(project_path, page_file, source_lines)
        n_doubt = len(result["missing_enum_groups"]) + len(result["missing_nums"])
        total_doubt += n_doubt

        print(f"\n── {result['page']} ──")
        if not result.get("located", True):
            print("  - 未能在原文中定位到对应章节标题，跳过核查（请人工核对）")
            continue
        if n_doubt == 0:
            print("  ✓ 未发现疑似遗漏（枚举/数字均在原文依据或上屏文字中找到对应）")
            continue

        for g in result["missing_enum_groups"]:
            print(f"  [枚举疑似遗漏] 原文 {g['source']}：")
            print(f"      原文完整列表：{'、'.join(g['all_items'])}")
            print(f"      页面中未找到：{'、'.join(g['missing_items'])}")

        for n in result["missing_nums"]:
            print(f"  [数字疑似遗漏] 原文 {n['source']}：{n['value']}")

    print("\n" + "=" * 70)
    print(f"共 {len(page_files)} 个页面，发现 {total_doubt} 处疑似遗漏。")
    print("提示：本工具仅提示疑点，不做自动判定。若该项已在页面'可压缩内容'字段")
    print("中声明为有意压缩，可视为正常；否则建议对照原文核实是否需要补回。")






def cmd_route(
    name_or_path: str,
    task_type: str | None = None,
    source_state: str | None = None,
    primary_goal: str | None = None,
):
    """解析并保存项目工作流路由。"""
    from ppt_script.workflow import update_project_route

    project_path = resolve_project(name_or_path)
    meta = load_meta(project_path)
    try:
        route = update_project_route(
            project_path,
            REPO_ROOT,
            task_type=task_type or str(meta.get("task_type", "full-presentation")),
            source_state=source_state or meta.get("source_state"),
            primary_goal=primary_goal or meta.get("primary_goal"),
        )
    except (FileNotFoundError, ValueError) as exc:
        print(f"[错误] {exc}")
        sys.exit(1)
    print(f"[✓] 工作流路由：{route.task_type}｜{route.source_state}｜{route.primary_goal}")
    print("    " + " → ".join(route.stages))


def cmd_state(name_or_path: str):
    """根据项目实际成果推导并保存状态。"""
    from ppt_script.workflow import write_project_state

    project_path = resolve_project(name_or_path)
    state = write_project_state(project_path)
    print(f"[✓] 当前状态：{state.current}")
    if state.next_state:
        print(f"    下一状态：{state.next_state}")
    for item in state.missing_for_next:
        print(f"    缺口：{item}")


def cmd_context_pack(name_or_path: str, mode: str | None = None):
    from ppt_script.context import build_context_pack

    project_path = resolve_project(name_or_path)
    pack = build_context_pack(project_path, REPO_ROOT, mode=mode)
    print(f"[PASS] 已生成活动上下文：{project_path / 'analysis/00-active-context.md'}")
    print(f"  状态：{pack.state}")
    print(f"  模式：{pack.mode}")
    print(f"  模块：{', '.join(pack.module_ids) or '无'}")


def cmd_editorial_init(name_or_path: str):
    from ppt_script.editorial import initialize_editorial

    project_path = resolve_project(name_or_path)
    try:
        outputs = initialize_editorial(project_path, REPO_ROOT)
    except (FileNotFoundError, ValueError, json.JSONDecodeError) as exc:
        print(f"[错误] {exc}")
        raise SystemExit(1)
    print("[PASS] 已初始化汇报总编工作区")
    for output in outputs:
        print(f"  - {output}")


def cmd_editorial_pack(name_or_path: str, mode: str):
    from ppt_script.editorial import build_editorial_context

    project_path = resolve_project(name_or_path)
    try:
        output = build_editorial_context(project_path, REPO_ROOT, mode)  # type: ignore[arg-type]
    except (FileNotFoundError, ValueError) as exc:
        print(f"[错误] {exc}")
        raise SystemExit(1)
    print(f"[PASS] 已生成 {mode} 汇报总编上下文：{output}")


def cmd_editorial_check(name_or_path: str, phase: str):
    from ppt_script.editorial import write_editorial_audit

    project_path = resolve_project(name_or_path)
    try:
        report = write_editorial_audit(project_path, phase)  # type: ignore[arg-type]
    except ValueError as exc:
        print(f"[错误] {exc}")
        raise SystemExit(1)
    status = "PASS" if report.passed else "FAIL"
    output_dir = project_path / "analysis/editorial"
    print(f"[{status}] 汇报总编 {phase} 审计：{output_dir / f'99-{phase}-audit.json'}")
    print(f"  - {output_dir / f'99-{phase}-audit.md'}")
    for issue in report.issues:
        print(f"  - {issue.code}: {issue.message}")


def cmd_understanding_check(name_or_path: str):
    from ppt_script.understanding import write_understanding_audit

    project_path = resolve_project(name_or_path)
    report = write_understanding_audit(project_path)
    status = "PASS" if report.passed else "FAIL"
    print(f"[{status}] 源材料理解闸门：{project_path / 'analysis/02-understanding-gate.md'}")
    for issue in report.issues:
        print(f"  - {issue.code}: {issue.message}")
    if not report.passed:
        raise SystemExit(1)


def cmd_semantic_check(name_or_path: str):
    from ppt_script.semantics import write_semantic_audit

    project_path = resolve_project(name_or_path)
    report = write_semantic_audit(project_path)
    status = "PASS" if report.passed else "FAIL"
    print(f"[{status}] 全文语义理解闸门：{project_path / 'analysis/01-semantic-gate.md'}")
    for issue in report.issues:
        print(f"  - {issue.code}: {issue.message}")
    if not report.passed:
        raise SystemExit(1)


def cmd_cognitive_init(name_or_path: str):
    from ppt_script.cognition import initialize_cognition

    project_path = resolve_project(name_or_path)
    outputs = initialize_cognition(project_path, REPO_ROOT)
    print("[PASS] 已初始化认知增强工作区")
    for output in outputs:
        print(f"  - {output}")


def cmd_cognitive_pack(name_or_path: str, mode: str):
    from ppt_script.cognition import build_reading_context

    project_path = resolve_project(name_or_path)
    try:
        output = build_reading_context(project_path, REPO_ROOT, mode)  # type: ignore[arg-type]
    except (FileNotFoundError, ValueError) as exc:
        print(f"[错误] {exc}")
        raise SystemExit(1)
    print(f"[PASS] 已生成 {mode} 独立认知上下文：{output}")


def cmd_cognitive_check(name_or_path: str):
    from ppt_script.cognition import write_cognitive_audit

    project_path = resolve_project(name_or_path)
    report = write_cognitive_audit(project_path)
    status = "PASS" if report.passed else "FAIL"
    print(f"[{status}] 认知增强闸门：{project_path / 'review/10-cognitive-audit.md'}")
    for issue in report.issues:
        print(f"  - {issue.code}: {issue.message}")
    if not report.passed:
        raise SystemExit(1)


def cmd_evidence_check(name_or_path: str):
    from ppt_script.evidence_graph import write_evidence_graph_report

    project_path = resolve_project(name_or_path)
    report = write_evidence_graph_report(project_path)
    status = "PASS" if report.passed else "FAIL"
    print(f"[{status}] 证据图谱检查：{project_path / 'review/10-evidence-graph-audit.md'}")
    for issue in report.issues:
        print(f"  - {issue.code}: {issue.message}")
    if not report.passed:
        raise SystemExit(1)


def cmd_trace_claim(name_or_path: str, claim_id: str):
    from ppt_script.evidence_graph import render_claim_trace, trace_claim

    project_path = resolve_project(name_or_path)
    try:
        trace = trace_claim(project_path, claim_id)
    except (KeyError, ValueError) as exc:
        print(f"[错误] {exc}")
        raise SystemExit(1)
    print(render_claim_trace(trace), end="")



def cmd_case_index():
    from ppt_script.experience import build_case_index

    result = build_case_index(REPO_ROOT)
    print(f"[PASS] 经验案例索引：{result.index_path}")
    print(f"  已批准案例：{len(result.cases)}")
    for issue in result.issues:
        print(f"  - {issue.code}: {issue.path}: {issue.message}")


def cmd_case_search(query: str, limit: int = 5):
    from ppt_script.experience import search_cases

    hits = search_cases(REPO_ROOT, query, limit=limit)
    if not hits:
        print("未检索到已批准案例。")
        return
    for hit in hits:
        penalty = f" penalties={','.join(hit.penalties)}" if hit.penalties else ""
        print(f"{hit.case_id}	{hit.score:.3f}	{hit.title}{penalty}")


def cmd_experience_pack(name_or_path: str, limit: int = 5):
    from ppt_script.experience import build_experience_pack

    project_path = resolve_project(name_or_path)
    pack = build_experience_pack(project_path, REPO_ROOT, limit=limit)
    print(f"[PASS] 历史经验上下文：{pack.markdown_path}")
    print(f"  命中已批准案例：{len(pack.hits)}")


def cmd_case_capture(name_or_path: str):
    from ppt_script.experience import capture_case

    project_path = resolve_project(name_or_path)
    try:
        output = capture_case(project_path, REPO_ROOT)
    except (FileNotFoundError, FileExistsError, ValueError, json.JSONDecodeError) as exc:
        print(f"[错误] {exc}")
        raise SystemExit(1)
    print(f"[PASS] 已批准经验案例：{output}")


def cmd_contract_check(name_or_path: str):
    from ppt_script.contracts import write_contract_report

    project_path = resolve_project(name_or_path)
    report = write_contract_report(project_path)
    status = "PASS" if report.passed else "FAIL"
    print(f"[{status}] 结构化合同检查：{project_path / 'review/09-contract-audit.md'}")
    if report.issues:
        for issue in report.issues:
            print(f"  - {issue.code}: {issue.message}")
    if not report.passed:
        raise SystemExit(1)


def cmd_version():
    """显示当前发布版本。"""
    from ppt_script.version import get_version

    print(get_version(REPO_ROOT))


def cmd_doctor():
    """检查依赖、配置、Skill入口和仓库一致性。"""
    from ppt_script.doctor import render_doctor_report, run_doctor

    report = run_doctor(REPO_ROOT)
    print(render_doctor_report(report), end="")
    if not report.passed:
        sys.exit(1)


# ── V3 source truth / planning / evaluation commands ─────────────────────────

def cmd_init(project_name: str):
    """初始化项目；实现位于 ppt_script.commands.init。"""
    from ppt_script.commands.init import initialize_project

    try:
        project_path = initialize_project(PROJECTS_DIR, project_name)
    except FileExistsError as exc:
        print(f"[错误] {exc}")
        sys.exit(1)
    print(f"\n[✓] 项目已初始化：{project_path}")
    print(f"\n下一步：将源材料放入 {project_path / 'source'}，然后运行 run {project_name}")


def cmd_approve(name_or_path: str, step: str, note: str = ""):
    """记录确认；实现位于 ppt_script.commands.approval。"""
    from ppt_script.commands.approval import approve_artifact

    project_path = resolve_project(name_or_path)
    try:
        output = approve_artifact(project_path, step, note)
    except ValueError as exc:
        print(f"[错误] {exc}")
        sys.exit(1)
    print(f"[✓] 已记录确认：{output}")


def cmd_authoring_check(name_or_path: str):
    """检查写页前总编状态与人审批准凭证是否齐全且 SHA 仍有效。"""
    from ppt_script.commands.approval import (
        STEP_FILE_MAP,
        approval_is_fresh,
        load_approval,
        required_authoring_approvals,
    )
    from ppt_script.workflow import assert_page_authoring_allowed

    project_path = resolve_project(name_or_path)
    try:
        assert_page_authoring_allowed(project_path)
    except ValueError as exc:
        print(f"[错误] {exc}")
        sys.exit(1)

    steps = required_authoring_approvals(project_path)
    if not steps:
        print("[✓] 写页检查通过：本项目不要求 decision/outline/expression 人审批准。")
        return

    print("[✓] 写页前人审批准检查通过：")
    for step in steps:
        record = load_approval(project_path, step) or {}
        relative = STEP_FILE_MAP[step]
        approved_at = record.get("approved_at", "")
        note = record.get("note", "")
        fresh = approval_is_fresh(project_path, step)
        suffix = f"；备注：{note}" if note else ""
        print(
            f"  - {step}: {relative}；批准时间 {approved_at}；"
            f"SHA {'有效' if fresh else '无效'}{suffix}"
        )


def cmd_assemble(name_or_path: str):
    """组装项目；文件编排实现位于 ppt_script.commands.assembly。"""
    from ppt_script.commands.assembly import assemble_project

    project_path = resolve_project(name_or_path)
    try:
        outputs = assemble_project(
            project_path,
            load_meta(project_path),
            build_imagegen=_build_imagegen_page,
            build_index=_build_outline_index_entry,
        )
    except ValueError as exc:
        print(f"[错误] {exc}")
        sys.exit(1)
    for output in outputs:
        print(f"[✓] 已生成：{output}")

def cmd_source_inventory(name_or_path: str):
    project_path = resolve_project(name_or_path)
    from ppt_script.cli import source_inventory_command
    output = source_inventory_command(project_path)
    print(f"[✓] 源材料概览已生成：{output}")


def cmd_plan_check(name_or_path: str):
    project_path = resolve_project(name_or_path)
    from ppt_script.cli import plan_check_command
    output = plan_check_command(project_path)
    data = json.loads(output.with_suffix(".json").read_text(encoding="utf-8"))
    mark = "✓" if data.get("passed") else "!"
    print(f"[{mark}] 规划检查已生成：{output}")
    if not data.get("passed"):
        for issue in data.get("issues", [])[:8]:
            if isinstance(issue, dict):
                print(f"  - {issue.get('identifier', '')}: {issue.get('message', '')}")
            else:
                print(f"  - {issue}")
        sys.exit(1)


def cmd_pages_check(name_or_path: str):
    from ppt_script.commands.pages_check import pages_check_command

    project_path = resolve_project(name_or_path)
    output = pages_check_command(project_path)
    data = json.loads(output.with_suffix(".json").read_text(encoding="utf-8"))
    mark = "✓" if data.get("passed") else "!"
    print(f"[{mark}] 页面合同对齐检查已生成：{output}")
    for issue in data.get("issues", [])[:12]:
        if isinstance(issue, dict):
            print(f"  - [{issue.get('level')}] {issue.get('code')}: {issue.get('message')}")
    if not data.get("passed"):
        sys.exit(1)


def cmd_retire_page(name_or_path: str, name_or_stem: str):
    from ppt_script.commands.retire_page import retire_page_command

    project_path = resolve_project(name_or_path)
    try:
        destination = retire_page_command(project_path, name_or_stem)
    except (FileNotFoundError, FileExistsError, ValueError) as exc:
        print(f"[错误] {exc}")
        sys.exit(1)
    print(f"[✓] 已废止并迁入：{destination}")


def cmd_handoff(name_or_path: str, target: str, *, reveal: bool = False):
    from ppt_script.commands.handoff import format_handoff_links, handoff_command

    project_path = resolve_project(name_or_path)
    try:
        paths = handoff_command(project_path, target, reveal=reveal if reveal else None)
    except (ValueError, FileNotFoundError) as exc:
        print(f"[错误] {exc}")
        sys.exit(1)
    print(f"[✓] 交付物链接已列出（{target}）" + ("；已打开目录" if reveal else "（默认不打开资源管理器）") + "：")
    for line in format_handoff_links(paths):
        print(line)


def cmd_provenance_sync(name_or_path: str, phase: str = "all"):
    """Refresh editorial provenance digests after intentional human edits."""
    import os

    from ppt_script.commands.provenance import sync_provenance
    from ppt_script.context import build_context_pack

    project_path = resolve_project(name_or_path)
    try:
        updated = sync_provenance(project_path, phase)  # type: ignore[arg-type]
    except ValueError as exc:
        print(f"[错误] {exc}")
        sys.exit(1)
    if not updated:
        print("[!] 未找到可同步的 editorial provenance 文件")
        sys.exit(1)
    print(f"[✓] 已同步 provenance 摘要（阶段：{phase}）：")
    for path in updated:
        print(f"  - {path}")

    if os.environ.get("PPT_SCRIPT_NO_AUTO_CONTEXT", "").strip() in {"1", "true", "yes"}:
        return
    try:
        pack = build_context_pack(project_path, REPO_ROOT, mode="deep")
    except Exception as exc:  # noqa: BLE001 — surface soft failure, digests already synced
        print(f"[!] provenance 已同步，但自动 context-pack 失败：{exc}")
        return
    print(f"[✓] 已自动刷新活动上下文：{project_path / 'analysis/00-active-context.md'}")
    print(f"  状态：{pack.state}  模式：{pack.mode}")


def cmd_audit(name_or_path: str):
    project_path = resolve_project(name_or_path)
    from ppt_script.cli import audit_command
    output = audit_command(project_path, REPO_ROOT)
    print(f"[✓] 脚本机器预审已生成：{output}")


def cmd_notes_check(name_or_path: str):
    project_path = resolve_project(name_or_path)
    from ppt_script.cli import notes_check_command
    output = notes_check_command(project_path, REPO_ROOT)
    print(f"[✓] 演讲者备注检查已生成：{output}")


def cmd_quality_check(name_or_path: str):
    project_path = resolve_project(name_or_path)
    from ppt_script.cli import quality_check_command
    output = quality_check_command(project_path, REPO_ROOT)
    data = json.loads(output.with_suffix(".json").read_text(encoding="utf-8"))
    mark = "✓" if data.get("passed") else "!"
    print(f"[{mark}] PPT脚本质量闸门已生成：{output}")


def cmd_style_check(name_or_path: str):
    from ppt_script.commands.style import style_check_command

    project_path = resolve_project(name_or_path)
    output = style_check_command(project_path, REPO_ROOT)
    data = json.loads(output.with_suffix(".json").read_text(encoding="utf-8"))
    mark = "✓" if data.get("passed") else "!"
    print(f"[{mark}] 正式汇报文体检查已生成：{output}")


def cmd_compare(name_or_path: str, original_path: str, revised_path: str):
    project_path = resolve_project(name_or_path)
    from ppt_script.cli import compare_command
    output = compare_command(project_path, original_path, revised_path, REPO_ROOT)
    print(f"[✓] 版本比较已生成：{output}")


def cmd_run(name_or_path: str):
    """按项目当前状态执行可运行的检查，并在需要模型或人工输入时暂停。"""
    from ppt_script.commands.run import run_project

    project_path = resolve_project(name_or_path)
    result = run_project(
        project_path,
        REPO_ROOT,
        assemble=cmd_assemble,
        evidence_usage=cmd_evidence_usage,
    )
    mark = "✓" if result.status == "completed" else "·"
    print(f"[{mark}] run {result.stage}：{result.message}")
    for output in result.outputs:
        print(f"    {output}")


# ── 入口 ──────────────────────────────────────────────────────────────────────

def main():
    args = sys.argv[1:]

    if not args:
        print(__doc__)
        sys.exit(0)

    command = args[0]

    if command == "version":
        cmd_version()

    elif command == "doctor":
        cmd_doctor()

    elif command == "route":
        if len(args) < 2:
            print("用法：python3 scripts/project_manager.py route <项目名或路径> [task_type] [source_state] [primary_goal]")
            sys.exit(1)
        cmd_route(
            args[1],
            args[2] if len(args) > 2 else None,
            args[3] if len(args) > 3 else None,
            args[4] if len(args) > 4 else None,
        )

    elif command == "state":
        if len(args) < 2:
            print("用法：python3 scripts/project_manager.py state <项目名或路径>")
            sys.exit(1)
        cmd_state(args[1])

    elif command == "understanding-check":
        if len(args) < 2:
            print("用法：python3 scripts/project_manager.py understanding-check <项目名或路径>")
            sys.exit(1)
        cmd_understanding_check(args[1])

    elif command == "semantic-check":
        if len(args) < 2:
            print("用法：python3 scripts/project_manager.py semantic-check <项目名或路径>")
            sys.exit(1)
        cmd_semantic_check(args[1])

    elif command == "cognitive-init":
        if len(args) < 2:
            print("用法：python3 scripts/project_manager.py cognitive-init <项目名或路径>")
            sys.exit(1)
        cmd_cognitive_init(args[1])

    elif command == "cognitive-pack":
        if len(args) < 3:
            print("用法：python3 scripts/project_manager.py cognitive-pack <项目名或路径> <faithful|decision|reconcile>")
            sys.exit(1)
        cmd_cognitive_pack(args[1], args[2])

    elif command == "cognitive-check":
        if len(args) < 2:
            print("用法：python3 scripts/project_manager.py cognitive-check <项目名或路径>")
            sys.exit(1)
        cmd_cognitive_check(args[1])

    elif command == "evidence-check":
        if len(args) < 2:
            print("用法：python3 scripts/project_manager.py evidence-check <项目名或路径>")
            sys.exit(1)
        cmd_evidence_check(args[1])

    elif command == "trace-claim":
        if len(args) < 3:
            print("用法：python3 scripts/project_manager.py trace-claim <项目名或路径> <C###>")
            sys.exit(1)
        cmd_trace_claim(args[1], args[2])

    elif command == "case-index":
        cmd_case_index()

    elif command == "case-search":
        if len(args) < 2:
            print("用法：python3 scripts/project_manager.py case-search <查询词> [数量]")
            sys.exit(1)
        cmd_case_search(args[1], int(args[2]) if len(args) > 2 else 5)

    elif command == "experience-pack":
        if len(args) < 2:
            print("用法：python3 scripts/project_manager.py experience-pack <项目名或路径> [数量]")
            sys.exit(1)
        cmd_experience_pack(args[1], int(args[2]) if len(args) > 2 else 5)

    elif command == "case-capture":
        if len(args) < 2:
            print("用法：python3 scripts/project_manager.py case-capture <项目名或路径>")
            sys.exit(1)
        cmd_case_capture(args[1])

    elif command == "contract-check":
        if len(args) < 2:
            print("用法：python3 scripts/project_manager.py contract-check <项目名或路径>")
            sys.exit(1)
        cmd_contract_check(args[1])

    elif command == "context-pack":
        if len(args) < 2:
            print("用法：python3 scripts/project_manager.py context-pack <项目名或路径> [deep|compact]")
            sys.exit(1)
        cmd_context_pack(args[1], args[2] if len(args) > 2 else None)

    elif command == "editorial-init":
        if len(args) != 2:
            print("用法：python3 scripts/project_manager.py editorial-init <项目名或路径>")
            sys.exit(1)
        cmd_editorial_init(args[1])

    elif command == "editorial-pack":
        if len(args) != 3:
            print("用法：python3 scripts/project_manager.py editorial-pack <项目名或路径> <semantic-planning|independent|storyline-candidates|storyline|outline|red-team|red-team-response>")
            sys.exit(1)
        cmd_editorial_pack(args[1], args[2])

    elif command == "editorial-check":
        if len(args) != 3:
            print("用法：python3 scripts/project_manager.py editorial-check <项目名或路径> <semantic-planning|independent|storyline-candidates|storyline|outline|red-team-review|red-team>")
            sys.exit(1)
        cmd_editorial_check(args[1], args[2])

    elif command == "init":
        if len(args) < 2:
            print("用法：python3 scripts/project_manager.py init <项目名称>")
            sys.exit(1)
        cmd_init(args[1])

    elif command == "list":
        cmd_list()

    elif command == "status":
        if len(args) < 2:
            print("用法：python3 scripts/project_manager.py status <项目名或路径>")
            sys.exit(1)
        cmd_status(args[1])

    elif command == "assemble":
        if len(args) < 2:
            print("用法：python3 scripts/project_manager.py assemble <项目名或路径>")
            sys.exit(1)
        cmd_assemble(args[1])

    elif command == "new-page":
        if len(args) < 4:
            print("用法：python3 scripts/project_manager.py new-page <项目名> <页码> <标题>")
            print("示例：python3 scripts/project_manager.py new-page my-project 05 数据平台架构")
            sys.exit(1)
        cmd_new_page(args[1], args[2], args[3])

    elif command == "rhythm-check":
        if len(args) < 2:
            print("用法：python3 scripts/project_manager.py rhythm-check <项目名或路径>")
            sys.exit(1)
        cmd_rhythm_check(args[1])

    elif command == "custom-types":
        if len(args) < 2:
            print("用法：python3 scripts/project_manager.py custom-types <项目名或路径>")
            sys.exit(1)
        cmd_custom_types(args[1])

    elif command == "check-coverage":
        if len(args) < 2:
            print("用法：python3 scripts/project_manager.py check-coverage <项目名> [页码或pXX文件名]")
            sys.exit(1)
        cmd_check_coverage(args[1], args[2] if len(args) > 2 else None)

    elif command == "evidence-usage":
        if len(args) < 2:
            print("用法：python3 scripts/project_manager.py evidence-usage <项目名或路径>")
            sys.exit(1)
        cmd_evidence_usage(args[1])

    elif command == "gap-summary":
        if len(args) < 2:
            print("用法：python3 scripts/project_manager.py gap-summary <项目名或路径>")
            sys.exit(1)
        cmd_gap_summary(args[1])

    elif command == "source-inventory":
        if len(args) < 2:
            print("用法：python3 scripts/project_manager.py source-inventory <项目名或路径>")
            sys.exit(1)
        cmd_source_inventory(args[1])

    elif command == "plan-check":
        if len(args) < 2:
            print("用法：python3 scripts/project_manager.py plan-check <项目名或路径>")
            sys.exit(1)
        cmd_plan_check(args[1])

    elif command == "pages-check":
        if len(args) < 2:
            print("用法：python3 scripts/project_manager.py pages-check <项目名或路径>")
            sys.exit(1)
        cmd_pages_check(args[1])

    elif command == "retire-page":
        if len(args) < 3:
            print("用法：python3 scripts/project_manager.py retire-page <项目名> <页面文件名或片段>")
            sys.exit(1)
        cmd_retire_page(args[1], args[2])

    elif command == "handoff":
        if len(args) < 3:
            print(
                "用法：python3 scripts/project_manager.py handoff <项目名> "
                "<decision|expression|outline|authoring|pages> [--reveal]"
            )
            sys.exit(1)
        reveal = "--reveal" in args[3:]
        cmd_handoff(args[1], args[2], reveal=reveal)

    elif command == "provenance-sync":
        if len(args) < 2:
            print(
                "用法：python3 scripts/project_manager.py provenance-sync <项目名> "
                "[storyline|outline|red-team-review|red-team|all]"
            )
            sys.exit(1)
        cmd_provenance_sync(args[1], args[2] if len(args) > 2 else "all")

    elif command == "audit":
        if len(args) < 2:
            print("用法：python3 scripts/project_manager.py audit <项目名或路径>")
            sys.exit(1)
        cmd_audit(args[1])

    elif command == "notes-check":
        if len(args) < 2:
            print("用法：python3 scripts/project_manager.py notes-check <项目名或路径>")
            sys.exit(1)
        cmd_notes_check(args[1])

    elif command == "quality-check":
        if len(args) < 2:
            print("用法：python3 scripts/project_manager.py quality-check <项目名或路径>")
            sys.exit(1)
        cmd_quality_check(args[1])

    elif command == "style-check":
        if len(args) < 2:
            print("用法：python3 scripts/project_manager.py style-check <项目名或路径>")
            sys.exit(1)
        cmd_style_check(args[1])

    elif command == "compare":
        if len(args) < 4:
            print("用法：python3 scripts/project_manager.py compare <项目名或路径> <原稿文件> <修订稿文件>")
            sys.exit(1)
        cmd_compare(args[1], args[2], args[3])

    elif command == "run":
        if len(args) < 2:
            print("用法：python3 scripts/project_manager.py run <项目名或路径>")
            sys.exit(1)
        cmd_run(args[1])

    elif command == "approve":
        if len(args) < 3:
            print(
                "用法：python3 scripts/project_manager.py approve "
                "<项目名> <analysis|truth|decision|outline|expression|evaluation|review|pXX> [备注]"
            )
            sys.exit(1)
        cmd_approve(args[1], args[2], " ".join(args[3:]) if len(args) > 3 else "")

    elif command == "authoring-check":
        if len(args) < 2:
            print("用法：python3 scripts/project_manager.py authoring-check <项目名>")
            sys.exit(1)
        cmd_authoring_check(args[1])

    else:
        print(f"未知命令：{command}")
        print(__doc__)
        sys.exit(1)


if __name__ == "__main__":
    main()
