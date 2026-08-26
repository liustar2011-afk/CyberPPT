#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable

try:
    import yaml
except ImportError:  # pragma: no cover
    yaml = None

PAGE_RE = re.compile(r"^##\s*第(\d+)页[：:]\s*(.+?)\s*$", re.M)
FIELD_RE = re.compile(r"^-\s*([^：:\n]+)[：:]\s*(.*)$", re.M)
SECTION_RE = re.compile(r"^###\s+(.+?)\s*$", re.M)
BOLD_TITLE_RE = re.compile(r"^-\s*\*\*(.+?)\*\*\s*$", re.M)
# Any indented detail line under a bold small-title, including the nested
# "- **子标题**：子文字明细" form used when one item bundles two or more
# parallel facts (see references/17-density-and-coverage.md). Counts both
# plain detail lines and nested sub-heading lines as one on-screen "bullet"
# each, matching how a reader actually perceives page density.
INDENTED_BULLET_RE = re.compile(r"^  - ", re.M)
DEFAULT_SOURCE_ID_PATTERNS = [
    r"\b(?:SRC|SU|A|P0)-[A-Za-z0-9_-]+\b",
    r"\bSRC-[A-Za-z0-9_-]+\b",
    # Some source-truth extractions use a bare "S" + digits scheme
    # (e.g. S0008) instead of the SRC-/SU-/A-/P0- prefix convention above.
    # Recognize both rather than treating one project's ID format as
    # canonical; override via quality-rules.yaml's source_id_patterns.
    r"\bS\d{3,}\b",
]
PAGE_CONTRACT_RE = re.compile(r"<!--\s*cyberppt-page-contract\s+(\{.*?\})\s*-->", re.S)
# Document-level scope declaration. Gate L (lite mode) explicitly allows a
# script to skip visual design entirely: "Visual structure/visual_intent_type
# fields are only required when visual design is in scope for this task —
# state explicitly in the script's own header when it is not." This is the
# fixed string that declaration must contain for the validator to recognize
# it and skip the visual-contract checks below, instead of reporting every
# content page as failing them. Searched against the whole document (the
# declaration lives in the script's own "## 说明" header, before the first
# "## 第X页" match, which parse_pages() does not otherwise parse).
VISUAL_OUT_OF_SCOPE_RE = re.compile(r"视觉设计范围[：:]\s*不含视觉设计")
COUNT_RE = re.compile(r"([一二三四五六七八九十两])(?:类|项|层|个|种|方|条)")
CHINESE_NUM = {"一": 1, "二": 2, "两": 2, "三": 3, "四": 4, "五": 5, "六": 6, "七": 7, "八": 8, "九": 9, "十": 10}
# Module-group headings in real scripts are written one level deeper than the
# "上屏文字（严格锁定）" heading itself (e.g. "#### 业务演进"), not always as
# flat "###" siblings the way templates/07-on-screen-text.md shows them.
# Recognize both so module counting and the order-signal check below see the
# actual module boundaries instead of collapsing a whole page into one block.
MODULE_SECTION_RE = re.compile(r"^#{3,4}\s+(.+?)\s*$", re.M)
# Explicit order/relationship signals a reader can see without the logic
# skeleton or a later visual-design pass. Mirrors the ppt-script skill's
# `hierarchy_signals` list (config/rules.yaml) so the two pipelines judge
# "is this relationship visible on screen" the same way.
ORDER_SIGNALS = [
    "①", "②", "③", "④", "⑤", "⑥",
    "→", "->", "随之", "先看", "再看",
    "第一层", "第二层", "第三层",
    "一、", "二、", "三、", "四、", "五、", "六、",
]
# A "chain" in 逻辑骨架 — two or more nodes connected by an arrow — signals a
# sequential/causal relationship that must survive into the locked on-screen
# text (see references/06-on-screen-text.md "顺序与关系信号"). A skeleton with
# no connector (e.g. a single node, or a pure "A＋B" combination with no
# downstream step) is not claiming an order, so it is not held to this rule.
LOGIC_SKELETON_CHAIN_RE = re.compile(r"[↓→]|->")


@dataclass
class Issue:
    level: str
    code: str
    page: int | None
    message: str


@dataclass
class Page:
    number: int
    title: str
    raw: str
    fields: dict[str, str] = field(default_factory=dict)
    sections: dict[str, str] = field(default_factory=dict)

    @property
    def page_type(self) -> str:
        return self.fields.get("页面类型", "")

    def _between(self, start_pattern: str, end_pattern: str | None = None) -> str:
        start = re.search(start_pattern, self.raw, flags=re.M)
        if not start:
            return ""
        begin = start.end()
        if end_pattern:
            end = re.search(end_pattern, self.raw[begin:], flags=re.M)
            if end:
                return self.raw[begin:begin + end.start()].strip()
        return self.raw[begin:].strip()

    @property
    def visible(self) -> str:
        return self._between(r"^###\s+上屏文字[^\n]*$", r"^###\s+(?:逻辑骨架|视觉结构|视觉意图与生图构图|演讲者备注)\s*$")

    @property
    def notes(self) -> str:
        return self._between(r"^###\s+演讲者备注\s*$")

    @property
    def visual(self) -> str:
        start = re.search(r"^###\s+视觉结构[^\n]*$", self.raw, flags=re.M)
        if start:
            end = re.search(r"^###\s+演讲者备注\s*$", self.raw[start.end():], flags=re.M)
            return self.raw[start.end(): start.end() + end.start()].strip() if end else self.raw[start.end():].strip()
        start = re.search(r"^###\s+视觉意图与生图构图\s*$", self.raw, flags=re.M)
        if start:
            end = re.search(r"^###\s+演讲者备注\s*$", self.raw[start.end():], flags=re.M)
            return self.raw[start.end(): start.end() + end.start()].strip() if end else self.raw[start.end():].strip()
        return ""



def parse_page_contract(raw: str) -> dict:
    match = PAGE_CONTRACT_RE.search(raw)
    if not match:
        return {}
    try:
        value = json.loads(match.group(1))
        return value if isinstance(value, dict) else {}
    except json.JSONDecodeError:
        return {}

def load_yaml(path: Path) -> dict:
    if yaml is None or not path.exists():
        return {}
    return yaml.safe_load(path.read_text(encoding="utf-8")) or {}


def parse_pages(text: str) -> list[Page]:
    matches = list(PAGE_RE.finditer(text))
    pages: list[Page] = []
    for idx, match in enumerate(matches):
        start = match.start()
        end = matches[idx + 1].start() if idx + 1 < len(matches) else len(text)
        raw = text[start:end].strip()
        fields = {m.group(1).strip(): m.group(2).strip() for m in FIELD_RE.finditer(raw)}
        sections: dict[str, str] = {}
        sec_matches = list(SECTION_RE.finditer(raw))
        for s_idx, sec in enumerate(sec_matches):
            s_start = sec.end()
            s_end = sec_matches[s_idx + 1].start() if s_idx + 1 < len(sec_matches) else len(raw)
            sections[sec.group(1).strip()] = raw[s_start:s_end].strip()
        pages.append(Page(int(match.group(1)), match.group(2).strip(), raw, fields, sections))
    return pages


def plain(text: str) -> str:
    text = re.sub(r"<!--.*?-->", "", text, flags=re.S)
    text = re.sub(r"```.*?```", "", text, flags=re.S)
    text = re.sub(r"[#>*_`\-]", "", text)
    text = re.sub(r"\s+", "", text)
    return text


def char_bigrams(text: str) -> set[str]:
    value = plain(text)
    return {value[i:i + 2] for i in range(max(0, len(value) - 1))}


def similarity(a: str, b: str) -> float:
    aa, bb = char_bigrams(a), char_bigrams(b)
    if not aa or not bb:
        return 0.0
    return len(aa & bb) / len(aa | bb)


def module_blocks(visible: str) -> list[tuple[str, str]]:
    matches = list(MODULE_SECTION_RE.finditer(visible))
    blocks = []
    for i, m in enumerate(matches):
        end = matches[i + 1].start() if i + 1 < len(matches) else len(visible)
        blocks.append((m.group(1).strip(), visible[m.end():end].strip()))
    if not blocks and visible.strip():
        blocks.append(("", visible))
    return blocks


def sibling_titles(block: str) -> list[str]:
    return [m.group(1).strip() for m in BOLD_TITLE_RE.finditer(block)]


def dimension(title: str, dims: dict[str, list[str]]) -> set[str]:
    result = set()
    for name, words in dims.items():
        if any(word in title for word in words):
            result.add(name)
    compact = plain(title)
    if compact.endswith("服务") and not any(x in compact for x in ["服务费", "收费", "价格", "结算"]):
        result.add("service_type")
    if any(x in compact for x in ["服务费", "使用费", "实施费", "资源费", "保障费", "运营费", "收费", "结算价"]):
        result.add("fee_type")
    return result


def add(issues: list[Issue], level: str, code: str, page: int | None, message: str) -> None:
    issues.append(Issue(level, code, page, message))


def validate(path: Path, strict: bool = False) -> tuple[list[Page], list[Issue]]:
    text = path.read_text(encoding="utf-8")
    root = Path(__file__).resolve().parents[1]
    rules = load_yaml(root / "config" / "quality-rules.yaml")
    profile = load_yaml(root / "config" / "cec-formal.yaml")
    q = rules.get("quality", {})
    dims = rules.get("classification_dimensions", {})
    source_id_patterns = q.get("source_id_patterns", DEFAULT_SOURCE_ID_PATTERNS)
    source_id_re = re.compile("|".join(f"(?:{p})" for p in source_id_patterns))
    pages = parse_pages(text)
    issues: list[Issue] = []
    visual_out_of_scope = bool(VISUAL_OUT_OF_SCOPE_RE.search(text))

    if not pages:
        add(issues, "error", "NO_PAGES", None, "未识别到页面标题：应使用‘## 第X页：标题’")
        return pages, issues

    expected = list(range(1, len(pages) + 1))
    actual = [p.number for p in pages]
    if actual != expected:
        add(issues, "error", "PAGE_SEQUENCE", None, f"页码不连续：{actual}")

    if visual_out_of_scope:
        add(issues, "info", "VISUAL_SCOPE_DECLARED_OUT", None, "检测到「视觉设计范围：不含视觉设计」声明，已跳过MISSING_VISUAL/MISSING_VISUAL_INTENT/TITLE_LAYER_UNCLEAR检查")

    titles = {}
    intents = []
    template_types = {"封面", "目录", "章节过渡页", "封底", "cover", "agenda", "contents", "chapter", "back_cover", "closing"}
    content_types = {"内容页", "content"}
    banned = profile.get("writing", {}).get("banned_contrast_frames", ["不是.*而是", "不能只.*还要"])
    min_chars = profile.get("text", {}).get("target_visible_chars_min", 180)
    max_chars = profile.get("text", {}).get("target_visible_chars_max", 520)

    for page in pages:
        if page.title in titles:
            add(issues, "warning", "DUPLICATE_TITLE", page.number, f"与第{titles[page.title]}页标题重复")
        titles[page.title] = page.number

        ptype = page.page_type
        if not ptype:
            add(issues, "error", "MISSING_PAGE_TYPE", page.number, "缺少页面类型")
        is_template = ptype in template_types
        is_content = ptype in content_types or not is_template

        if is_template:
            # 目录/agenda pages are expected to list chapter/section titles,
            # which routinely exceed 25 plain chars without containing the
            # literal word "模板" — that is the page doing its job, not a
            # business-content leak. Only cover/chapter/closing pages are
            # checked against the length threshold.
            agenda_types = {"目录", "contents", "agenda"}
            body = plain(page.visible)
            if ptype not in agenda_types and body and "模板" not in body and len(body) > 25:
                add(issues, "error", "TEMPLATE_BUSINESS_TEXT", page.number, "模板页包含疑似业务正文")
            if page.notes and len(plain(page.notes)) > 120:
                add(issues, "warning", "TEMPLATE_NOTES_DENSE", page.number, "模板页备注过长")
        else:
            # 正式完整脚本采用“主判断＋完整文字稿＋证据映射＋页级合同注释”的富格式。
            # 兼容旧格式中的“本页只回答/本页不得包含”，但不再强制它们作为可见字段。
            required_fields = ["页面标题", "主判断"]
            for name in required_fields:
                if not page.fields.get(name):
                    add(issues, "error", "MISSING_FIELD", page.number, f"缺少字段：{name}")
            if page.fields.get("页面标题") and page.fields.get("页面标题") != page.title:
                add(issues, "warning", "TITLE_FIELD_MISMATCH", page.number, "页面标题字段与页标题不一致")

            rich_sections = ["完整文字稿", "文字稿取舍说明", "证据映射", "上屏文字", "逻辑骨架", "演讲者备注"]
            for keyword in rich_sections:
                if not any(keyword in key for key in page.sections):
                    add(issues, "error", "MISSING_SECTION", page.number, f"缺少章节：{keyword}")
            if not page.visual and not visual_out_of_scope:
                add(issues, "error", "MISSING_VISUAL", page.number, "缺少视觉结构/视觉意图合同")
            if q.get("require_source_refs", True) and not source_id_re.search(page.raw):
                add(issues, "warning" if not strict else "error", "MISSING_SOURCE_REFS", page.number, "未识别到Source IDs/证据编号")

            contract = parse_page_contract(page.raw)
            if not contract:
                add(issues, "warning" if not strict else "error", "MISSING_PAGE_CONTRACT", page.number, "缺少cyberppt页级合同注释")
            else:
                for key in ["page_mission", "core_message", "must_not_include"]:
                    if not contract.get(key):
                        add(issues, "warning" if not strict else "error", "INCOMPLETE_PAGE_CONTRACT", page.number, f"页级合同缺少：{key}")
                main = page.fields.get("主判断", "").strip()
                core = str(contract.get("core_message") or "").strip()
                if main and core and similarity(main, core) < 0.72:
                    add(issues, "warning", "CORE_MESSAGE_MISMATCH", page.number, "主判断与页级合同core_message差异较大")

            vlen = len(plain(page.visible))
            if vlen < min_chars:
                add(issues, "warning", "LOW_DENSITY", page.number, f"上屏文字密度偏低：{vlen}字")
            if vlen > max_chars:
                add(issues, "warning", "HIGH_DENSITY", page.number, f"上屏文字密度偏高：{vlen}字")

            # 上屏文字应是完整文字稿的简版：单条更短，但整体条目数和覆盖率不能
            # 跟着一起缩水。见 references/17-density-and-coverage.md。
            bullet_count = len(INDENTED_BULLET_RE.findall(page.visible))
            min_bullets = q.get("min_visible_bullets", 6)
            if bullet_count < min_bullets:
                add(issues, "warning", "LOW_BULLET_COUNT", page.number, f"上屏条目数偏少：{bullet_count}条（含二级嵌套），建议不少于{min_bullets}条")

            full_text_len = len(plain(page.sections.get("完整文字稿", "")))
            if full_text_len:
                ratio = vlen / full_text_len
                min_ratio = q.get("min_onscreen_full_ratio", 0.20)
                max_ratio = q.get("max_onscreen_full_ratio", 0.45)
                ratio_floor_chars = q.get("max_onscreen_full_ratio_min_full_chars", 300)
                if ratio < min_ratio:
                    add(issues, "warning", "LOW_COVERAGE_RATIO", page.number, f"上屏/文字稿字数比{ratio:.2f}低于{min_ratio}，疑似丢失文字稿中的具体信息")
                if full_text_len >= ratio_floor_chars and ratio > max_ratio:
                    add(issues, "warning", "HIGH_COVERAGE_RATIO", page.number, f"上屏/文字稿字数比{ratio:.2f}高于{max_ratio}，疑似接近逐句复制文字稿")

            notes_len = len(plain(page.notes))
            if notes_len < q.get("speaker_notes_min_chars", 70):
                add(issues, "warning" if not strict else "error", "SHORT_NOTES", page.number, f"演讲备注偏短：{notes_len}字")
            if notes_len > q.get("speaker_notes_max_chars", 520):
                add(issues, "warning", "LONG_NOTES", page.number, f"演讲备注偏长：{notes_len}字")
            if similarity(page.visible, page.notes) > 0.64:
                add(issues, "warning", "NOTES_DUPLICATE_VISIBLE", page.number, "演讲备注与上屏文字重复度较高")

            must_not_values: list[str] = []
            legacy_must_not = page.fields.get("本页不得包含", "")
            if legacy_must_not:
                must_not_values.extend(re.split(r"[；;]", legacy_must_not))
            contract = parse_page_contract(page.raw)
            contract_must_not = contract.get("must_not_include", []) if contract else []
            if isinstance(contract_must_not, str):
                must_not_values.append(contract_must_not)
            elif isinstance(contract_must_not, list):
                must_not_values.extend(str(x) for x in contract_must_not)
            for phrase in must_not_values:
                token = plain(phrase)
                # 只对足够具体的禁止项做机械包含检查；泛化边界由语义审计处理。
                if len(token) >= 8 and token in plain(page.visible):
                    add(issues, "error", "PAGE_LEAKAGE", page.number, f"上屏文字包含本页禁止内容：{phrase.strip()}")

            module_blocks_found = module_blocks(page.visible)
            module_count = len(module_blocks_found)
            if module_count > q.get("max_content_modules", 5):
                add(issues, "warning", "TOO_MANY_MODULES", page.number, f"上屏模块过多：{module_count}")

            # A role-suggestive heading (e.g. "现实制约") is not the same as a
            # visible order signal. When there are enough modules that their
            # sequence actually matters, and this page's relationship is the
            # kind that has a sequence (checked via the logic-skeleton chain
            # below, or simply because there are more than the configured
            # threshold of modules), require an explicit marker in the
            # headings themselves — see references/06-on-screen-text.md
            # "顺序与关系信号".
            min_order_signal_modules = q.get("min_order_signal_modules", 3)
            module_headings = " ".join(heading for heading, _ in module_blocks_found if heading)
            has_order_signal_in_headings = any(sig in module_headings for sig in ORDER_SIGNALS)
            if module_count > min_order_signal_modules and not has_order_signal_in_headings:
                add(
                    issues,
                    "warning" if not strict else "error",
                    "MISSING_ORDER_SIGNAL",
                    page.number,
                    f"上屏模块数为{module_count}（>{min_order_signal_modules}），但模块标题中未发现①②③/一二三/→/随之等顺序信号，"
                    "读者只能看到并列卡片，读不出模块间的先后或因果关系",
                )

            # The logic skeleton is where a writer records a page's causal or
            # sequential judgment (references/07-logic-and-parallelism.md).
            # Excluding it from the downstream ImageGen contract (see
            # references/16-single-page-imagegen-contract.md 3.6) only means
            # its raw text should not become image-prompt copy — it does not
            # mean the relationship it records is allowed to stay invisible
            # to the reader. If the skeleton declares a chain, the same
            # relationship must already be legible in the locked on-screen
            # text; otherwise Gate 4 is not actually complete yet.
            skeleton_text = page.sections.get("逻辑骨架", "")
            if LOGIC_SKELETON_CHAIN_RE.search(skeleton_text) and not any(
                sig in page.visible for sig in ORDER_SIGNALS
            ):
                add(
                    issues,
                    "error",
                    "LOGIC_SKELETON_NOT_ONSCREEN",
                    page.number,
                    "逻辑骨架记录了顺序/因果链，但完整上屏内容中没有对应的顺序信号"
                    "（①②③/一二三/→/随之），该关系只存在于后台字段，观众读不到",
                )

        for pattern in banned:
            try:
                if re.search(pattern, page.raw):
                    add(issues, "error", "BANNED_CONTRAST", page.number, f"出现禁用对立式结构：{pattern}")
            except re.error:
                if pattern in page.raw:
                    add(issues, "error", "BANNED_CONTRAST", page.number, f"出现禁用表达：{pattern}")

        # 防御性边界提示（如"不构成承诺""避免误解"）属于后台自述，不是可直接
        # 讲述的正式陈述句，只检查演讲者备注——这是 cyberppt/script_quality_
        # contract.py 里 NARRATION_BOUNDARY_COACHING 规则在本仓库的对应版本。
        for pattern in profile.get("writing", {}).get("banned_defensive_coaching_frames", []):
            try:
                if re.search(pattern, page.notes):
                    add(issues, "warning", "DEFENSIVE_COACHING_NOTES", page.number, f"演讲者备注出现防御性边界提示：{pattern}")
            except re.error:
                if pattern in page.notes:
                    add(issues, "warning", "DEFENSIVE_COACHING_NOTES", page.number, f"演讲者备注出现防御性边界提示：{pattern}")

        if "overlay" in page.raw.lower():
            add(issues, "error", "OVERLAY_FIELD", page.number, "出现禁用overlay字段")
        if re.search(r"(?:同上|沿用前页|略)$", page.visible, re.M):
            add(issues, "error", "CROSS_PAGE_PLACEHOLDER", page.number, "上屏文字包含跨页占位表达")

        for heading, block in module_blocks(page.visible):
            titles_in_block = sibling_titles(block)
            declared = [CHINESE_NUM[m.group(1)] for m in COUNT_RE.finditer(heading)]
            if declared and titles_in_block and declared[0] != len(titles_in_block):
                add(issues, "error", "COUNT_MISMATCH", page.number, f"模块‘{heading}’声明{declared[0]}项，实际可见{len(titles_in_block)}项")

            dim_sets = [(title, dimension(title, dims)) for title in titles_in_block]
            used_dims = set().union(*(d for _, d in dim_sets)) if dim_sets else set()
            if "service_type" in used_dims and "fee_type" in used_dims:
                add(issues, "error", "SERVICE_FEE_MIX", page.number, f"模块‘{heading}’将服务类别与费用类别并列")
            delivery_dims = used_dims & {"access_method", "deployment_mode", "processing_location", "service_cycle", "service_type"}
            if len(delivery_dims) >= 2 and not any(word in heading for word in ["维度", "组合", "适配", "关系"]):
                add(issues, "warning" if not strict else "error", "MIXED_CLASSIFICATION_DIMENSIONS", page.number, f"模块‘{heading}’混合分类维度：{sorted(delivery_dims)}")

            for title in titles_in_block:
                if len(plain(title)) > q.get("max_small_title_chars", 10):
                    add(issues, "warning", "LONG_SMALL_TITLE", page.number, f"小标题偏长：{title}")

        visual_intent_match = re.search(r"visual_intent_type[：:]\s*`?([A-Za-z0-9_-]+)", page.raw)
        if visual_intent_match:
            intents.append((page.number, visual_intent_match.group(1)))
        elif not is_template and not visual_out_of_scope:
            add(issues, "error", "MISSING_VISUAL_INTENT", page.number, "缺少visual_intent_type")

        positive_visual = "\n".join(
            line for line in page.visual.splitlines()
            if not any(k in line for k in ["禁止", "避免", "avoid_on_this_page"])
        )
        if re.search(r"(?:等权|等宽|卡片墙|图标阵列|左文右图)", positive_visual):
            add(issues, "warning" if not strict else "error", "GENERIC_VISUAL_SKELETON", page.number, "视觉正向字段疑似采用通用卡片/图标/左右分栏骨架")
        if not is_template and not visual_out_of_scope and not re.search(r"(?:PPT文字层|不绘制标题|标题区.*不绘制)", page.raw):
            add(issues, "warning", "TITLE_LAYER_UNCLEAR", page.number, "未明确标题由PPT文字层处理")

    max_consecutive = q.get("max_consecutive_visual_intent", 2)
    for i in range(len(intents)):
        streak = 1
        for j in range(i + 1, len(intents)):
            if intents[j][1] == intents[i][1]:
                streak += 1
            else:
                break
        if streak > max_consecutive:
            add(issues, "warning", "REPEATED_VISUAL_INTENT", intents[i][0], f"连续{streak}页使用同一视觉意图：{intents[i][1]}")
            break

    dup_warn = q.get("duplicate_similarity_warning", 0.72)
    dup_error = q.get("duplicate_similarity_error", 0.86)
    dup_min = q.get("duplicate_min_chars", 45)
    content_pages = [p for p in pages if p.page_type not in template_types and len(plain(p.visible)) >= dup_min]
    for i, a in enumerate(content_pages):
        for b in content_pages[i + 1:]:
            score = similarity(a.visible, b.visible)
            if score >= dup_error:
                add(issues, "error", "CROSS_PAGE_DUPLICATE", b.number, f"与第{a.number}页上屏文字高度重复：{score:.2f}")
            elif score >= dup_warn:
                add(issues, "warning", "CROSS_PAGE_SIMILAR", b.number, f"与第{a.number}页上屏文字较相似：{score:.2f}")

    return pages, issues


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate Word-to-PPT final script")
    parser.add_argument("script", type=Path)
    parser.add_argument("--strict", action="store_true")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    if not args.script.exists():
        parser.error(f"not found: {args.script}")
    pages, issues = validate(args.script, strict=args.strict)
    errors = [i for i in issues if i.level == "error"]
    warnings = [i for i in issues if i.level == "warning"]
    payload = {
        "passed": not errors,
        "pages": len(pages),
        "errors": len(errors),
        "warnings": len(warnings),
        "issues": [i.__dict__ for i in issues],
    }
    if args.json:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        print(f"pages={len(pages)} errors={len(errors)} warnings={len(warnings)}")
        for item in issues:
            where = f"P{item.page}" if item.page else "DECK"
            print(f"[{item.level.upper()}] {where} {item.code}: {item.message}")
    return 0 if not errors else 2


if __name__ == "__main__":
    raise SystemExit(main())
