"""Delivery-only cleanup for canonical final-script.md.

The machine-readable final-script.json may retain analytical labels used by the
engine. The canonical Markdown boundary must not expose those labels, page-nav
artifacts, or Critic/guardrail commentary.
"""
from __future__ import annotations

import re


_ARGUMENT_LABEL_RULES: tuple[tuple[str, str], ...] = (
    ("classification with optional progression", "分类与演进"),
    ("situation-tension-response", "问题与回应"),
    ("problem-to-response", "问题回应"),
    ("necessity / diagnosis", "问题诊断"),
    ("evidence synthesis", "证据支撑"),
    ("resource transformation", "资源转化"),
    ("operating loop", "运营闭环"),
    ("value formation", "价值形成"),
    ("classification", "分类结构"),
    ("taxonomy", "分类结构"),
    ("progression", "演进路径"),
    ("maturity", "演进路径"),
    ("risk-control-protection", "风险保障"),
    ("governance / responsibility", "职责关系"),
    ("architecture", "架构关系"),
    ("implementation", "推进流程"),
    ("mechanism", "形成机制"),
    ("value", "价值结构"),
)

_EVIDENCE_ANNOTATION_RE = re.compile(
    r"[（(]\s*(?:explicit|inferred|speculative)\b[^）)]*[）)]",
    flags=re.IGNORECASE,
)
_INTERNAL_ANALYSIS_RE = re.compile(
    r"\b(?:explicit|inferred|speculative)\b"
    r"|situation-tension-response|problem-to-response|evidence synthesis"
    r"|resource transformation|classification\s*(?:/|with)|progression\s*/"
    r"|risk-control-protection|operating loop",
    flags=re.IGNORECASE,
)
_GUARDRAIL_COMMENTARY_RE = re.compile(
    r"源文未|源材料未|分析性归纳|需要如实保留|须保留这一区别"
    r"|不宜为追求页面整齐|页面将其归纳为|两层含义均须保留"
)
_PAGE_META_RE = re.compile(
    r"上一页|下一页|本页(?:展示|说明|先|将)|第[一二三四五六七八九十0-9]+页"
    r"|后续页面|后续章节|本章后续页面|六步路径的前三步|后三步。"
    r"|接下来第[一二三四五六七八九十]+章|最后一章[，,]"
)

_DROP_SENTENCE_MARKERS = (
    "分析性归纳而非",
    "源文未逐一显式配对",
    "需要如实保留",
    "不宜为追求页面整齐",
    "不构成统一的笼统表述",
    "本章后续页面",
)

_DIRECT_REPLACEMENTS = (
    ("面对上一页所述的", "针对上述"),
    ("与上一页的", "与前述"),
    ("进入下一页的", "进入"),
    ("，本页展示其中两个", ""),
    ("本页展示其中两个", ""),
    (
        "下一页将说明它们如何组合形成不同成熟度的场景服务形态",
        "这些能力可以按业务需求组合形成不同成熟度的场景服务形态",
    ),
    (
        "这也是下一页要说明的商务机制得以落地的组织基础",
        "这为商务机制落地提供了组织基础",
    ),
    (
        "这一原则回应了资源提供方在第一章第一页所提到的关切——控制权、使用用途、成果边界和合理收益——",
        "这一原则直接回应资源提供方对控制权、使用用途、成果边界和合理收益的关切，",
    ),
    ("具体的合作深度和方式留待后续章节的合作模式与商务机制展开", ""),
    ("六步路径的前三步。", ""),
    ("后三步。", ""),
    ("接下来一次展开。", ""),
    ("须保留这一区别而非统一措辞", "现有基础类型存在差异"),
)


_CHAPTER_NAV_RE = re.compile(r"接下来第[一二三四五六七八九十]+章[^。！？]*[。！？]?")
_LAST_CHAPTER_RE = re.compile(r"最后一章[，,][^。！？]*[。！？]?")
_NEXT_PAGE_ROLE_RE = re.compile(r"具体如何组合角色，将在下一页[^。！？]*[。！？]?")


def argument_pattern_label(pattern: object) -> str:
    """Map internal analytical-model names to short Chinese delivery labels."""
    raw = str(pattern or "").strip()
    if not raw:
        return ""
    lowered = raw.lower()
    for token, label in _ARGUMENT_LABEL_RULES:
        if token in lowered:
            return label
    if re.search(r"[A-Za-z]", raw):
        return "论证关系"
    return raw


def sanitize_relation_text(value: object) -> str:
    """Remove evidence-grade annotations while preserving the semantic relation itself."""
    text = str(value or "").strip()
    text = _EVIDENCE_ANNOTATION_RE.sub("", text)
    text = text.replace("，两层含义均须保留", "")
    return re.sub(r"\s+", " ", text).strip(" ，,;；")


def _clean_paragraph(paragraph: str) -> str:
    text = paragraph
    for old, new in _DIRECT_REPLACEMENTS:
        text = text.replace(old, new)
    text = _CHAPTER_NAV_RE.sub("", text)
    text = _LAST_CHAPTER_RE.sub("", text)
    text = _NEXT_PAGE_ROLE_RE.sub("", text)

    parts = re.split(r"(?<=[。！？])", text)
    kept: list[str] = []
    for part in parts:
        sentence = part.strip()
        if not sentence:
            continue
        if any(marker in sentence for marker in _DROP_SENTENCE_MARKERS):
            continue
        kept.append(sentence)
    cleaned = "".join(kept)
    cleaned = re.sub(r"，\s*。", "。", cleaned)
    cleaned = re.sub(r"；\s*。", "。", cleaned)
    cleaned = re.sub(r"\s+", " ", cleaned)
    return cleaned.strip()


def sanitize_delivery_prose(value: object) -> str:
    """Remove presentation-navigation and Critic commentary from delivery prose.

    Paragraph breaks are preserved so `full_copy` keeps its load-bearing structure.
    """
    raw = str(value or "").strip()
    if not raw:
        return ""
    paragraphs = [_clean_paragraph(p) for p in raw.split("\n\n")]
    return "\n\n".join(p for p in paragraphs if p)


def check_delivery_cleanliness(markdown: str) -> list[str]:
    """Hard gate for the canonical Markdown delivery boundary.

    `页面使命` is workflow metadata and may describe page-to-page function, so it is
    excluded only from the page-navigation check. Internal analysis labels are forbidden
    everywhere in canonical Markdown.
    """
    issues: list[str] = []

    match = _INTERNAL_ANALYSIS_RE.search(markdown)
    if match:
        issues.append(f"delivery: internal analysis/model label leaked into Markdown: '{match.group(0)}'")

    match = _GUARDRAIL_COMMENTARY_RE.search(markdown)
    if match:
        issues.append(f"delivery: Critic/guardrail commentary leaked into Markdown: '{match.group(0)}'")

    visible_lines = [line for line in markdown.splitlines() if not line.startswith("- 页面使命：")]
    visible_text = "\n".join(visible_lines)
    match = _PAGE_META_RE.search(visible_text)
    if match:
        issues.append(f"delivery: stale page/chapter navigation leaked into audience-facing content: '{match.group(0)}'")

    return issues
