"""Validation helpers for Script Engine delivery contracts."""
from __future__ import annotations
import difflib, json, re, unicodedata
from pathlib import Path
from typing import Any, Iterator
from jsonschema import Draft202012Validator
from .delivery_cleanliness import argument_pattern_topology

ROOT = Path(__file__).resolve().parents[1]
CONTRACTS = ROOT / "contracts"

def load_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(payload, dict):
        raise ValueError(f"JSON root must be an object: {path}")
    return payload

def load_schema(name: str) -> dict[str, Any]:
    return load_json(CONTRACTS / name)

def validate_payload(payload: dict[str, Any], schema_name: str) -> list[str]:
    schema = load_schema(schema_name)
    validator = Draft202012Validator(schema)
    errors = sorted(validator.iter_errors(payload), key=lambda item: list(item.absolute_path))
    result: list[str] = []
    for error in errors:
        location = ".".join(str(part) for part in error.absolute_path) or "$"
        result.append(f"{location}: {error.message}")
    return result

def validate_final_script(payload: dict[str, Any]) -> list[str]:
    return validate_payload(payload, "final-script.schema.json")

def validate_deck_plan(payload: dict[str, Any]) -> list[str]:
    return validate_payload(payload, "deck-plan.schema.json")


def validate_foundation(payload: dict[str, Any]) -> list[str]:
    return validate_payload(payload, "foundation.schema.json")

FOUNDATION_CITABLE_KEYS = ("facts", "concepts", "entities", "relations", "arguments", "constraints", "numbers")

def collect_foundation_source_codes(foundation: dict[str, Any]) -> set[str]:
    codes: set[str] = set()
    for key in FOUNDATION_CITABLE_KEYS:
        for item in foundation.get(key) or []:
            if not isinstance(item, dict):
                continue
            item_id = item.get("id")
            if isinstance(item_id, str) and item_id:
                codes.add(item_id)
            for ref in item.get("source_refs") or []:
                if isinstance(ref, str) and ref:
                    codes.add(ref)
    return codes

def validate_source_refs_coverage(final_script: dict[str, Any], foundation: dict[str, Any]) -> list[str]:
    """Structural check only: every source_refs code cited in final-script must trace back to
    a citation already used somewhere in foundation.json. This catches invented or orphaned
    citation codes; it cannot verify that the surrounding prose faithfully represents the source."""
    known = collect_foundation_source_codes(foundation)
    issues: list[str] = []
    for index, slide in enumerate(final_script.get("slides") or []):
        if not isinstance(slide, dict):
            continue
        slide_id = slide.get("id") or f"#{index}"
        for ref in slide.get("source_refs") or []:
            if isinstance(ref, str) and ref and ref not in known:
                issues.append(f"slides.{index} ({slide_id}).source_refs: '{ref}' does not match any citation in foundation.json")
    return issues

BANNED_PHRASING_PATH = CONTRACTS / "banned-phrasing.json"

def load_banned_phrasing() -> list[dict[str, Any]]:
    return load_json(BANNED_PHRASING_PATH).get("rules", [])

def iter_final_script_text_fields(final_script: dict[str, Any]) -> Iterator[tuple[str, str, str]]:
    """Yield (field-path, field-key, text) for every prose field in a final-script payload.
    `field-key` identifies the field's role (e.g. `mission`, `onscreen.heading`) so rules can be
    scoped to specific fields. Excludes `source_refs` (traceability codes, not prose) and
    `relationships.from`/`.to` (short entity labels, not sentences)."""
    deck = final_script.get("deck") or {}
    for key in ("title", "communication_goal", "audience", "narrative"):
        value = deck.get(key)
        if isinstance(value, str) and value:
            yield f"deck.{key}", f"deck.{key}", value

    for index, slide in enumerate(final_script.get("slides") or []):
        if not isinstance(slide, dict):
            continue
        prefix = f"slides.{index} ({slide.get('id') or f'#{index}'})"
        for key in ("title", "subtitle", "mission", "core_message", "full_copy", "visual_thesis", "speaker_notes"):
            value = slide.get(key)
            if isinstance(value, str) and value:
                yield f"{prefix}.{key}", key, value

        argument = slide.get("argument") or {}
        pattern = argument.get("pattern")
        if isinstance(pattern, str) and pattern:
            yield f"{prefix}.argument.pattern", "argument.pattern", pattern
        for step_index, step in enumerate(argument.get("chain") or []):
            if isinstance(step, str) and step:
                yield f"{prefix}.argument.chain[{step_index}]", "argument.chain", step

        for module_index, module in enumerate(slide.get("onscreen") or []):
            if not isinstance(module, dict):
                continue
            for key in ("heading", "text"):
                value = module.get(key)
                if isinstance(value, str) and value:
                    yield f"{prefix}.onscreen[{module_index}].{key}", f"onscreen.{key}", value
            for item_index, item in enumerate(module.get("items") or []):
                if isinstance(item, str) and item:
                    yield f"{prefix}.onscreen[{module_index}].items[{item_index}]", "onscreen.items", item

        for rel_index, relation in enumerate(slide.get("relationships") or []):
            if not isinstance(relation, dict):
                continue
            value = relation.get("relation")
            if isinstance(value, str) and value:
                yield f"{prefix}.relationships[{rel_index}].relation", "relationships.relation", value

def lint_final_script(final_script: dict[str, Any]) -> list[str]:
    """Mechanical scan of every prose field against contracts/banned-phrasing.json. This is a
    deterministic safety net for patterns an LLM Critic pass can miss when re-reading its own
    long draft (register drift, self-reference, contrastive-reveal sentences) — it does not
    replace the Critic's judgment-based checks (argument quality, evidence adequacy, etc.).

    `mission` is exempt from the `self-reference` rule (and any other rule that opts in via
    `exclude_fields`): mission's job is to state the page's function within the deck's own
    narrative (e.g. "呼应第一章…"), so referencing deck structure there is correct usage, not a
    leak — the rule only protects fields the audience actually sees or hears.

    A rule may instead opt in via `include_fields`, restricting it to only the listed fields
    (e.g. the speaker_notes-only rules that check the note actually sounds spoken, not written
    about a speech)."""
    rules = [
        (
            rule["id"],
            re.compile(rule["pattern"]),
            rule.get("description", ""),
            set(rule.get("exclude_fields") or []),
            set(rule["include_fields"]) if rule.get("include_fields") else None,
        )
        for rule in load_banned_phrasing()
    ]
    issues: list[str] = []
    for field_path, field_key, text in iter_final_script_text_fields(final_script):
        for rule_id, regex, description, exclude_fields, include_fields in rules:
            if field_key in exclude_fields:
                continue
            if include_fields is not None and field_key not in include_fields:
                continue
            match = regex.search(text)
            if match:
                issues.append(f"{field_path}: [{rule_id}] {description} — matched '{match.group(0)}'")
    issues.extend(check_author_field_contract(final_script))
    issues.extend(check_full_copy_structure(final_script))
    issues.extend(check_full_copy_topic_semantics(final_script))
    issues.extend(check_full_copy_parallel_subconclusions(final_script))
    issues.extend(check_onscreen_heading_semantics(final_script))
    issues.extend(check_onscreen_detail_semantics(final_script))
    issues.extend(check_onscreen_projection_structure(final_script))
    issues.extend(check_onscreen_hierarchy_punctuation(final_script))
    issues.extend(check_onscreen_code_context(final_script))
    issues.extend(check_onscreen_core_alignment(final_script))
    return issues

_ITEM_SIMILARITY_THRESHOLD = 0.6
_MISSION_GENERIC_RE = re.compile(
    r"^(?:说明|明确|解释|呈现|组织|界定|梳理).{0,12}(?:相关|有关|主要)(?:内容|情况|工作|事项|关系)[。.]?$"
)
_VISUAL_RELATION_GRAMMAR_RE = re.compile(
    r"共同|并列|汇聚|进入|形成|推动|驱动|衔接|决定|贯通|分层|分步|分为|归入|管理|依次|映射|对应|支撑|保障|承接|转化|闭环|递进|循环|流向|接受"
)
_PARALLEL_VISUAL_GRAMMAR_RE = re.compile(
    r"共同|并列|分组|分类|分层|贯穿|纵向|横向|三类|四类|五类|六类|七类|八类"
)
_CONVERGENCE_VISUAL_GRAMMAR_RE = re.compile(r"共同|汇聚|形成|构成|支撑|保障|接受|落到|指向")
_HIDDEN_RELATION_STEP_RE = re.compile(r"[，,；;].{0,24}(?:再|随后|进而|继而|并通过)")


def _field_is_blank(value: object) -> bool:
    return not isinstance(value, str) or not value.strip()


def _onscreen_lines(slide: dict[str, Any]) -> list[str]:
    lines: list[str] = []
    for module in slide.get("onscreen") or []:
        if not isinstance(module, dict):
            continue
        for key in ("heading", "text"):
            value = module.get(key)
            if isinstance(value, str) and value.strip():
                lines.append(value.strip())
        lines.extend(
            item.strip() for item in module.get("items") or []
            if isinstance(item, str) and item.strip()
        )
    return lines


def check_author_field_contract(final_script: dict[str, Any]) -> list[str]:
    """Enforce the mechanical floor of the mandatory supporting-field pass.

    Semantic quality remains an AUTHOR/Critic responsibility. This gate checks only
    high-confidence failures: missing fields, unregistered topology, unusable chains,
    non-relational visual theses, abstract or multi-step edges and direct note restatement.
    """
    issues: list[str] = []
    for index, slide in enumerate(final_script.get("slides") or []):
        if not isinstance(slide, dict) or slide.get("page_type") != "content":
            continue
        slide_id = slide.get("id") or f"#{index}"
        prefix = f"slides.{index} ({slide_id})"

        for field in ("mission", "core_message", "full_copy", "visual_thesis", "speaker_notes"):
            if _field_is_blank(slide.get(field)):
                issues.append(f"AUTHOR_FIELD_REQUIRED: {prefix}.{field}: content pages require a non-empty {field}")

        mission = str(slide.get("mission") or "").strip()
        if mission and _MISSION_GENERIC_RE.fullmatch(mission):
            issues.append(
                f"AUTHOR_MISSION_GENERIC: {prefix}.mission: '{mission}' names a generic review topic; "
                "state the single audience question or page duty"
            )

        argument = slide.get("argument")
        if not isinstance(argument, dict):
            issues.append(f"AUTHOR_ARGUMENT_REQUIRED: {prefix}.argument: content pages require an argument object")
            topology = None
            chain: list[object] = []
        else:
            pattern = str(argument.get("pattern") or "").strip()
            topology = argument_pattern_topology(pattern)
            if topology is None:
                issues.append(
                    f"AUTHOR_ARGUMENT_PATTERN_UNREGISTERED: {prefix}.argument.pattern: "
                    f"'{pattern}' has no registered topology"
                )
            chain = argument.get("chain") if isinstance(argument.get("chain"), list) else []
            usable_chain = [item.strip() for item in chain if isinstance(item, str) and item.strip()]
            if len(usable_chain) < 2 or len(usable_chain) != len(chain):
                issues.append(
                    f"AUTHOR_ARGUMENT_CHAIN_INVALID: {prefix}.argument.chain: provide at least two non-empty semantic nodes"
                )

        visual_thesis = str(slide.get("visual_thesis") or "").strip()
        if visual_thesis and not _VISUAL_RELATION_GRAMMAR_RE.search(visual_thesis):
            issues.append(
                f"AUTHOR_VISUAL_THESIS_NONRELATIONAL: {prefix}.visual_thesis: '{visual_thesis}' "
                "does not state a visible direction, grouping, mapping, convergence or closed loop"
            )
        if topology == "parallel" and visual_thesis and not _PARALLEL_VISUAL_GRAMMAR_RE.search(visual_thesis):
            issues.append(
                f"AUTHOR_VISUAL_TOPOLOGY_CONFLICT: {prefix}.visual_thesis: registered parallel pattern "
                "requires visible parallel, grouping or shared-dimension grammar"
            )
        if topology == "convergence" and visual_thesis and not _CONVERGENCE_VISUAL_GRAMMAR_RE.search(visual_thesis):
            issues.append(
                f"AUTHOR_VISUAL_TOPOLOGY_CONFLICT: {prefix}.visual_thesis: registered convergence pattern "
                "requires inputs to share a visible landing"
            )

        core = _normalize_item_text(str(slide.get("core_message") or ""))
        visual = _normalize_item_text(visual_thesis)
        if core and visual and len(core) >= 16 and difflib.SequenceMatcher(None, core, visual).ratio() >= 0.9:
            issues.append(
                f"AUTHOR_VISUAL_THESIS_RESTATEMENT: {prefix}.visual_thesis restates core_message "
                "instead of declaring the visual relationship"
            )

        for relation_index, relation in enumerate(slide.get("relationships") or []):
            if not isinstance(relation, dict):
                issues.append(f"AUTHOR_RELATION_INVALID: {prefix}.relationships[{relation_index}] must be an object")
                continue
            source = str(relation.get("from") or "").strip()
            target = str(relation.get("to") or "").strip()
            action = str(relation.get("relation") or "").strip()
            if not source or not target or not action:
                issues.append(
                    f"AUTHOR_RELATION_INCOMPLETE: {prefix}.relationships[{relation_index}] requires from, to and relation"
                )
                continue
            if _HIDDEN_RELATION_STEP_RE.search(action):
                issues.append(
                    f"AUTHOR_RELATION_HIDDEN_INTERMEDIATE: {prefix}.relationships[{relation_index}].relation: "
                    f"'{action}' hides more than one process step inside one edge"
                )
            combined = _normalize_item_text(f"{source}{action}{target}")
            if _GENERIC_TRANSFORMATION_CLAIM_RE.search(combined):
                issues.append(
                    f"AUTHOR_RELATION_ABSTRACT_TRANSFORMATION: {prefix}.relationships[{relation_index}]: "
                    "name the concrete operating mechanism and observable result at both ends"
                )

        notes = _normalize_item_text(str(slide.get("speaker_notes") or ""))
        comparison_lines = [
            _normalize_item_text(str(slide.get("core_message") or "")),
            *(_normalize_item_text(line) for line in _onscreen_lines(slide)),
        ]
        if notes and any(
            line and len(line) >= 12 and difflib.SequenceMatcher(None, notes, line).ratio() >= 0.88
            for line in comparison_lines
        ):
            issues.append(
                f"AUTHOR_SPEAKER_NOTES_RESTATEMENT: {prefix}.speaker_notes directly restates a visible judgment; "
                "add basis, subordinate evidence, a non-material boundary, audience focus or natural transition"
            )
    return issues

def _normalize_item_text(text: str) -> str:
    """Strip whitespace and punctuation so near-duplicate items compare on their actual content,
    not incidental formatting differences."""
    return re.sub(r"[\s、，,。.；;：:！!？?（）()【】\[\]“”\"'—-]", "", str(text or ""))

def check_onscreen_structure(final_script: dict[str, Any]) -> list[str]:
    """Structural checks on `onscreen` that are safe to enforce mechanically because they have no
    legitimate exception.

    - Flags two `onscreen` modules on the same slide sharing the exact same heading — always
      either a copy-paste slip or an unintended merge, never an intentional structure.
    - Flags two `items` (or a `text` and an `items` entry) within the *same module* that are near-
      duplicates of each other (normalized text similarity >= 0.6, via `difflib.SequenceMatcher`).
      This is the mechanical guardrail against restating the same point in slightly different words
      instead of adding a genuinely new sub-fact. The threshold is deliberately loose (catches paraphrase-level overlap, not just
      exact repeats) because that failure mode rarely produces byte-identical strings."""
    issues: list[str] = []
    for index, slide in enumerate(final_script.get("slides") or []):
        if not isinstance(slide, dict):
            continue
        slide_id = slide.get("id") or f"#{index}"
        headings = [m.get("heading") for m in (slide.get("onscreen") or []) if isinstance(m, dict) and m.get("heading")]
        seen: set[str] = set()
        for heading in headings:
            if heading in seen:
                issues.append(f"slides.{index} ({slide_id}).onscreen: duplicate module heading '{heading}' — same slide has two onscreen modules with the same heading")
            seen.add(heading)

        for module in slide.get("onscreen") or []:
            if not isinstance(module, dict):
                continue
            module_heading = module.get("heading") or "?"
            lines: list[str] = []
            text = module.get("text")
            if isinstance(text, str) and text.strip():
                lines.append(text)
            for item in module.get("items") or []:
                if isinstance(item, str) and item.strip():
                    lines.append(item)
            normalized = [_normalize_item_text(line) for line in lines]
            for i in range(len(lines)):
                for j in range(i + 1, len(lines)):
                    if not normalized[i] or not normalized[j]:
                        continue
                    ratio = difflib.SequenceMatcher(None, normalized[i], normalized[j]).ratio()
                    if ratio >= _ITEM_SIMILARITY_THRESHOLD:
                        issues.append(f"slides.{index} ({slide_id}).onscreen module '{module_heading}': near-duplicate lines ({ratio:.0%} similar) — '{lines[i]}' / '{lines[j]}' restate the same point instead of adding a new one")
    return issues

_FULL_COPY_SENTENCE_SIMILARITY_THRESHOLD = 0.75
_FULL_COPY_SENTENCE_MIN_CHARS = 12

def check_full_copy_duplication(final_script: dict[str, Any]) -> list[str]:
    """Flags near-duplicate sentences within the same slide's `full_copy`.

    `check_onscreen_structure` already guards near-duplicate onscreen items within a
    module; `full_copy` has no equivalent, so AUTHOR can restate the same source fact
    across two argument paragraphs without any mechanical check catching it. The
    threshold here is stricter than the onscreen check (0.75, not 0.6) because two full
    sentences restating each other read as an obvious defect, while two evidence
    phrases sharing vocabulary is common and legitimate."""
    issues: list[str] = []
    for index, slide in enumerate(final_script.get("slides") or []):
        if not isinstance(slide, dict):
            continue
        slide_id = slide.get("id") or f"#{index}"
        full_copy = slide.get("full_copy")
        if not isinstance(full_copy, str) or not full_copy.strip():
            continue
        sentences = [s.strip() for s in re.split(r"(?<=[。！？])", full_copy) if s.strip()]
        normalized = [_normalize_item_text(s) for s in sentences]
        for i in range(len(sentences)):
            if len(normalized[i]) < _FULL_COPY_SENTENCE_MIN_CHARS:
                continue
            for j in range(i + 1, len(sentences)):
                if len(normalized[j]) < _FULL_COPY_SENTENCE_MIN_CHARS:
                    continue
                ratio = difflib.SequenceMatcher(None, normalized[i], normalized[j]).ratio()
                if ratio >= _FULL_COPY_SENTENCE_SIMILARITY_THRESHOLD:
                    issues.append(
                        f"FULL_COPY_DUPLICATION: slides.{index} ({slide_id}).full_copy: "
                        f"near-duplicate sentences ({ratio:.0%} similar) — '{sentences[i]}' / '{sentences[j]}' "
                        "restate the same source fact instead of advancing the argument"
                    )
    return issues

_FULL_COPY_STRUCTURE_MIN_CHARS = 180
_FULL_COPY_PARAGRAPH_MIN_CHARS = 24

_SEMANTIC_PREDICATES = (
    "已经", "可以", "需要", "应当", "形成", "明确", "承担", "提供", "覆盖",
    "缺少", "不足", "制约", "推动", "建立", "落实", "决定", "负责", "规范",
    "衔接", "承接", "服务", "完成", "保持", "安排", "界定", "匹配", "促进",
    "实现", "贯通", "增加", "提出", "转化", "构成", "支撑", "保障",
    "导致", "滞后", "已有", "校准", "承载", "对应", "建成", "推进",
    "确立", "体现", "规定", "检验", "固化", "纳入", "发布", "启动",
    "扩展", "接入", "帮助", "辅助", "记录", "采用", "补充", "检查",
)
_ABSTRACT_TOPIC_SENTENCE_RE = re.compile(
    r"(?:任务|要求|工作|建设|内容).{0,8}(?:具体化|更加明确|进一步明确|更为清晰|具有重要意义|意义重大)"
)
_SOURCE_STRENGTH_ABSTRACTION_RE = re.compile(
    r"(?:形成|建立).{0,40}(?:建设内容|阶段进度|技术规则).{0,40}(?:安排|框架)"
)
_GENERIC_TRANSFORMATION_CLAIM_RE = re.compile(
    r"(?:"
    r"[一二三四五六七八九十\d]+(?:类|项|方面)(?:体系化|系统化|一体化|综合性|整体性)?"
    r"|(?:体系化|系统化|一体化|综合性|整体性)"
    r")"
    r"(?:建设|举措|措施|工作|机制)"
    r".{0,18}(?:推动|促进|支撑|实现|转化(?:为)?|形成|提升)"
    r".{0,18}(?:能力|体系|水平|效能|基础|服务)$"
)
_FORMAL_TAXONOMY_HEADING_RE = re.compile(r"^(?:[A-Z]\s+|\d{1,2}[.、．\s]+)\S+")
_CONTEXT_DEPENDENT_HEADING_RE = re.compile(
    r"^(?:国家|行业|项目|研究|体系)(?:已|将|需|应|可|形成|明确|推进|承担|负责|提供|支撑)"
    r"|^后续(?:推进|开展|落实)"
)
_DANGLING_MODIFIER_RE = re.compile(r"^(?:以|基于|围绕|结合|按照|通过|面向|依托|针对)")
_PASS_RESULT_RE = re.compile(r"^通过.{2,}(?:评价|认证|验收|审核|审查)$")
_GENERIC_DETAIL_TAIL_RE = re.compile(
    r"^(?:国家政策|行业特点|协同实施|形成支撑|相关要求|有关工作|持续推进)$"
)
_CODE_ONLY_MAPPING_RE = re.compile(
    r"^[A-G](?:\d+|类)(?:\s*(?:\+|＋|、|/|／)\s*[A-G](?:\d+|类))*$",
    re.IGNORECASE,
)


def _has_complete_semantic_predicate(text: str) -> bool:
    compact = _normalize_item_text(text)
    for predicate in _SEMANTIC_PREDICATES:
        start = compact.find(predicate)
        if start >= 2 and len(compact) - start - len(predicate) >= 2:
            return True
    return False


def check_full_copy_topic_semantics(final_script: dict[str, Any]) -> list[str]:
    """Require each substantive full-copy paragraph to open with a complete point.

    This is intentionally a narrow semantic guardrail. It catches label-only openings and
    abstract evaluation sentences while leaving longer natural-language judgment to AUTHOR and
    Critic. Source-defined numbered prose with a substantive clause after a colon remains valid.
    """
    issues: list[str] = []
    for index, slide in enumerate(final_script.get("slides") or []):
        if not isinstance(slide, dict) or slide.get("page_type") != "content":
            continue
        slide_id = slide.get("id") or f"#{index}"
        paragraphs = [p.strip() for p in re.split(r"\n\s*\n", str(slide.get("full_copy") or "")) if p.strip()]
        for paragraph_index, paragraph in enumerate(paragraphs):
            topic = re.split(r"(?<=[。！？])", paragraph, maxsplit=1)[0].strip()
            compact = _normalize_item_text(topic)
            colon_tail = re.split(r"[：:]", topic, maxsplit=1)
            has_substantive_colon_tail = len(colon_tail) == 2 and len(_normalize_item_text(colon_tail[1])) >= 8
            if _SOURCE_STRENGTH_ABSTRACTION_RE.search(topic):
                issues.append(
                    f"FULL_COPY_TOPIC_SOURCE_STRENGTH_ABSTRACTED: slides.{index} ({slide_id}).full_copy paragraph "
                    f"{paragraph_index + 1}: opening '{topic}' replaces source-level actions, status, milestones or "
                    "formal outputs with author-created summary dimensions; restore the strongest source conclusion "
                    "and move its complete supporting facts into the paragraph body"
                )
                continue
            if _ABSTRACT_TOPIC_SENTENCE_RE.search(topic) or (
                len(compact) < 16
                and not has_substantive_colon_tail
                and not _has_complete_semantic_predicate(topic)
            ):
                issues.append(
                    f"FULL_COPY_TOPIC_INCOMPLETE: slides.{index} ({slide_id}).full_copy paragraph "
                    f"{paragraph_index + 1}: opening '{topic}' is a label or abstract evaluation, not a "
                    "complete audience-facing point with an object and substantive judgment"
                )
    return issues


_FULL_COPY_ORDINAL_RE = re.compile(r"(?:^|[：:，,。；;])\s*([一二三四五六七八九十]+)是")


def check_full_copy_parallel_subconclusions(final_script: dict[str, Any]) -> list[str]:
    """Reject label-led branches in an explicit full-copy enumeration.

    Whether source material is genuinely parallel remains an AUTHOR/Critic decision. This
    narrow outcome gate activates only after an author has explicitly used at least two
    ``一是/二是/三是`` branches, then verifies that each branch starts with a complete
    sub-conclusion instead of a generic category label.
    """
    issues: list[str] = []
    for index, slide in enumerate(final_script.get("slides") or []):
        if not isinstance(slide, dict) or slide.get("page_type") != "content":
            continue
        slide_id = slide.get("id") or f"#{index}"
        paragraphs = [
            paragraph.strip()
            for paragraph in re.split(r"\n\s*\n", str(slide.get("full_copy") or ""))
            if paragraph.strip()
        ]
        for paragraph_index, paragraph in enumerate(paragraphs):
            matches = list(_FULL_COPY_ORDINAL_RE.finditer(paragraph))
            if len(matches) < 2:
                continue
            for branch_index, match in enumerate(matches):
                branch_end = matches[branch_index + 1].start() if branch_index + 1 < len(matches) else len(paragraph)
                branch = paragraph[match.end():branch_end].lstrip("，,：: ")
                opening = re.split(r"[。；;]", branch, maxsplit=1)[0].strip()
                compact = _normalize_item_text(opening)
                if _GENERIC_TRANSFORMATION_CLAIM_RE.search(compact):
                    issues.append(
                        f"FULL_COPY_PARALLEL_SUBCONCLUSION_ABSTRACT: slides.{index} ({slide_id}).full_copy "
                        f"paragraph {paragraph_index + 1}, branch {match.group(1)}: opening '{opening}' names an "
                        "abstract construction-to-capability transformation without stating the concrete business "
                        "mechanism or observable operating result"
                    )
                elif len(compact) < 12 or not _has_complete_semantic_predicate(opening):
                    issues.append(
                        f"FULL_COPY_PARALLEL_SUBCONCLUSION_INCOMPLETE: slides.{index} ({slide_id}).full_copy "
                        f"paragraph {paragraph_index + 1}, branch {match.group(1)}: opening '{opening}' is a label "
                        "or incomplete clause; begin the numbered branch with an independently intelligible "
                        "business sub-conclusion before its supporting detail"
                    )
    return issues


def check_onscreen_heading_semantics(final_script: dict[str, Any]) -> list[str]:
    """Reject short category labels that force readers to infer a module's business meaning.

    Formal taxonomy codes stay valid because the adjacent module body defines the category. A
    claim heading, a source-defined taxonomy heading, or a heading that states both category and
    criterion remains valid.
    """
    issues: list[str] = []
    for index, slide in enumerate(final_script.get("slides") or []):
        if not isinstance(slide, dict) or slide.get("page_type") != "content":
            continue
        slide_id = slide.get("id") or f"#{index}"
        for module_index, module in enumerate(slide.get("onscreen") or []):
            if not isinstance(module, dict):
                continue
            heading = str(module.get("heading") or "").strip()
            compact = _normalize_item_text(heading)
            parts = [part for part in re.split(r"[｜|]", heading) if _normalize_item_text(part)]
            category_with_criterion = len(parts) >= 2 and all(len(_normalize_item_text(part)) >= 4 for part in parts)
            source_defined_taxonomy = bool(
                _FORMAL_TAXONOMY_HEADING_RE.match(heading)
                or heading.endswith("层")
                or ("贯穿" in heading and "贯穿" in str(slide.get("core_message") or ""))
            ) and bool(module.get("text") or module.get("items"))
            if _CONTEXT_DEPENDENT_HEADING_RE.search(heading):
                issues.append(
                    f"ONSCREEN_HEADING_OBJECT_OMITTED: slides.{index} ({slide_id}).onscreen[{module_index}].heading: "
                    f"'{heading}' relies on page context to supply the business matter; name the exact deployment, "
                    "project, research output or work item in the heading itself"
                )
                continue
            if _GENERIC_TRANSFORMATION_CLAIM_RE.search(compact):
                issues.append(
                    f"ONSCREEN_HEADING_ABSTRACT_TRANSFORMATION: slides.{index} ({slide_id}).onscreen[{module_index}].heading: "
                    f"'{heading}' is grammatically complete but leaves both the construction mechanism and operating "
                    "result abstract; name what will work differently in the business"
                )
                continue
            if (
                heading
                and len(compact) < 16
                and not source_defined_taxonomy
                and not category_with_criterion
                and not _has_complete_semantic_predicate(heading)
            ):
                issues.append(
                    f"ONSCREEN_HEADING_INCOMPLETE: slides.{index} ({slide_id}).onscreen[{module_index}].heading: "
                    f"'{heading}' is only a category label; state the object and its action, status, role or judgment"
                )
    return issues


def check_onscreen_detail_semantics(final_script: dict[str, Any]) -> list[str]:
    """Reject detail lines that stop at a basis, condition, method or scope.

    A detail may inherit the module's subject, and a semantic label may establish the
    relation. It may not leave an introductory modifier such as ``以…`` or ``围绕…``
    without the action or result that completes the business meaning.
    """
    issues: list[str] = []
    for index, slide in enumerate(final_script.get("slides") or []):
        if not isinstance(slide, dict) or slide.get("page_type") != "content":
            continue
        slide_id = slide.get("id") or f"#{index}"
        for module_index, module in enumerate(slide.get("onscreen") or []):
            if not isinstance(module, dict):
                continue
            lines: list[tuple[str, str]] = []
            text = module.get("text")
            if isinstance(text, str) and text.strip():
                lines.append(("text", text.strip()))
            lines.extend(
                (f"items[{item_index}]", item.strip())
                for item_index, item in enumerate(module.get("items") or [])
                if isinstance(item, str) and item.strip()
            )
            for field, line in lines:
                parts = _LABEL_SPLIT_RE.split(line, maxsplit=1)
                body = parts[1].strip() if len(parts) == 2 else line
                if (
                    _DANGLING_MODIFIER_RE.search(body)
                    and not _has_complete_semantic_predicate(body)
                    and not _PASS_RESULT_RE.search(body)
                ):
                    issues.append(
                        f"ONSCREEN_DANGLING_MODIFIER: slides.{index} ({slide_id}).onscreen[{module_index}].{field}: "
                        f"'{line}' states only a basis, condition, method or scope; add the business action or result"
                    )
                elif len(parts) == 2 and _GENERIC_DETAIL_TAIL_RE.fullmatch(_normalize_item_text(body)):
                    issues.append(
                        f"ONSCREEN_DETAIL_GENERIC: slides.{index} ({slide_id}).onscreen[{module_index}].{field}: "
                        f"'{line}' uses a semantic label but leaves the business matter abstract"
                    )
    return issues


def check_onscreen_projection_structure(final_script: dict[str, Any]) -> list[str]:
    """Require a mechanical evidence floor for normal multi-module self-read pages.

    The semantic relationship between modules remains an AUTHOR/Critic decision. This check
    only rejects the high-confidence failure where a content page presents several module
    judgments but none has child text or items, leaving no visible evidence layer at all.
    A short single-module page remains valid, and one module may carry an integrated judgment
    without a child when other modules establish the page's evidence layer.
    """
    issues: list[str] = []
    for index, slide in enumerate(final_script.get("slides") or []):
        if not isinstance(slide, dict) or slide.get("page_type") != "content":
            continue
        modules = [module for module in slide.get("onscreen") or [] if isinstance(module, dict)]
        if len(modules) < 2:
            continue
        has_evidence_layer = any(
            (isinstance(module.get("text"), str) and module.get("text", "").strip())
            or any(isinstance(item, str) and item.strip() for item in module.get("items") or [])
            for module in modules
        )
        if not has_evidence_layer:
            slide_id = slide.get("id") or f"#{index}"
            issues.append(
                f"ONSCREEN_EVIDENCE_LAYER_MISSING: slides.{index} ({slide_id}).onscreen: "
                "multiple module judgments are presented without any child text or items; "
                "retain the decisive evidence, condition, scope or result that establishes "
                "the projected argument layer"
            )
    return issues


def check_onscreen_hierarchy_punctuation(final_script: dict[str, Any]) -> list[str]:
    """Reject one visible detail line that encodes multiple hierarchy levels with colons."""

    issues: list[str] = []
    nested_colon_re = re.compile(r"^[^：:\n]{1,24}[：:][^：:\n]+[：:]")
    for index, slide in enumerate(final_script.get("slides") or []):
        if not isinstance(slide, dict) or slide.get("page_type") != "content":
            continue
        slide_id = slide.get("id") or f"#{index}"
        for module_index, module in enumerate(slide.get("onscreen") or []):
            if not isinstance(module, dict):
                continue
            lines: list[tuple[str, str]] = []
            text = module.get("text")
            if isinstance(text, str) and text.strip():
                lines.append(("text", text.strip()))
            lines.extend(
                (f"items[{item_index}]", item.strip())
                for item_index, item in enumerate(module.get("items") or [])
                if isinstance(item, str) and item.strip()
            )
            for field, line in lines:
                if nested_colon_re.search(line):
                    issues.append(
                        f"ONSCREEN_MULTILEVEL_COLON_CHAIN: slides.{index} ({slide_id}).onscreen"
                        f"[{module_index}].{field}: '{line}' encodes multiple hierarchy levels in one line; "
                        "keep one label-content relation per line and express parent-child structure with nesting"
                    )
    return issues


def check_onscreen_code_context(final_script: dict[str, Any]) -> list[str]:
    """Reject taxonomy-code mappings that require the previous page to decode.

    The check is deliberately narrow: it only fires when the complete detail body is
    one or more codes such as ``A3 + D3`` or ``F类``. Codes accompanied by their
    business names remain valid, and richer semantic judgment stays with AUTHOR.
    """
    issues: list[str] = []
    for index, slide in enumerate(final_script.get("slides") or []):
        if not isinstance(slide, dict) or slide.get("page_type") != "content":
            continue
        slide_id = slide.get("id") or f"#{index}"
        for module_index, module in enumerate(slide.get("onscreen") or []):
            if not isinstance(module, dict):
                continue
            for item_index, item in enumerate(module.get("items") or []):
                if not isinstance(item, str) or not item.strip():
                    continue
                parts = _LABEL_SPLIT_RE.split(item.strip(), maxsplit=1)
                body = parts[1].strip() if len(parts) == 2 else item.strip()
                if _CODE_ONLY_MAPPING_RE.fullmatch(body):
                    issues.append(
                        f"ONSCREEN_CODE_WITHOUT_NAME: slides.{index} ({slide_id}).onscreen[{module_index}].items[{item_index}]: "
                        f"'{item}' exposes only taxonomy codes; add each code's business name or role so the page is self-readable"
                    )
    return issues

def check_full_copy_structure(final_script: dict[str, Any]) -> list[str]:
    """Require long, multi-step arguments to retain visible paragraph structure.

    Short narrative pages and genuinely simple arguments remain valid.  The gate only fires
    when AUTHOR declares at least three argument steps and then collapses a long full copy into
    one paragraph; duplicate detection separately guards fake progression by repetition.
    """
    issues: list[str] = []
    for index, slide in enumerate(final_script.get("slides") or []):
        if not isinstance(slide, dict) or slide.get("page_type") != "content":
            continue
        full_copy = slide.get("full_copy")
        if not isinstance(full_copy, str):
            continue
        chain = (slide.get("argument") or {}).get("chain") or []
        if len(chain) < 3 or len(_normalize_item_text(full_copy)) < _FULL_COPY_STRUCTURE_MIN_CHARS:
            continue
        paragraphs = [
            paragraph.strip()
            for paragraph in re.split(r"\n\s*\n", full_copy)
            if len(_normalize_item_text(paragraph)) >= _FULL_COPY_PARAGRAPH_MIN_CHARS
        ]
        if len(paragraphs) < 2:
            slide_id = slide.get("id") or f"#{index}"
            issues.append(
                f"FULL_COPY_STRUCTURE_FLAT: slides.{index} ({slide_id}).full_copy: "
                "a long multi-step argument is collapsed into one paragraph; preserve at least "
                "two substantive paragraphs so the complete copy exposes its reasoning hierarchy"
            )
    return issues

_ONSCREEN_CORE_MIN_BIGRAMS = 4
_ONSCREEN_CORE_MIN_COVERAGE = 0.25
_ONSCREEN_BODY_MIN_COVERAGE = 0.15

def _semantic_bigrams(text: object) -> set[str]:
    compact = _normalize_item_text(str(text or "")).lower()
    return {compact[index:index + 2] for index in range(len(compact) - 1)}

def _onscreen_text(slide: dict[str, Any]) -> str:
    values: list[str] = []
    for module in slide.get("onscreen") or []:
        if not isinstance(module, dict):
            continue
        values.extend(str(module.get(key) or "") for key in ("heading", "text"))
        values.extend(str(item) for item in module.get("items") or [] if isinstance(item, str))
    return " ".join(values)

def check_onscreen_core_alignment(final_script: dict[str, Any]) -> list[str]:
    """Treat ``core_message`` as page meaning and ``onscreen`` as its visible projection.

    The check measures aggregate semantic-character coverage, so onscreen copy may decompose,
    evidence or paraphrase the conclusion without repeating it verbatim.  Very short conclusions
    are skipped because lexical coverage is not meaningful at that size.
    """
    issues: list[str] = []
    for index, slide in enumerate(final_script.get("slides") or []):
        if not isinstance(slide, dict) or slide.get("page_type") != "content":
            continue
        core_bigrams = _semantic_bigrams(slide.get("core_message"))
        if len(core_bigrams) < _ONSCREEN_CORE_MIN_BIGRAMS:
            continue
        body_bigrams = _semantic_bigrams(_onscreen_text(slide))
        projection_bigrams = body_bigrams | _semantic_bigrams(
            f"{slide.get('title') or ''} {slide.get('subtitle') or ''}"
        )
        body_coverage = len(core_bigrams & body_bigrams) / len(core_bigrams)
        coverage = len(core_bigrams & projection_bigrams) / len(core_bigrams)
        if (
            coverage < _ONSCREEN_CORE_MIN_COVERAGE
            or body_coverage < _ONSCREEN_BODY_MIN_COVERAGE
        ):
            slide_id = slide.get("id") or f"#{index}"
            issues.append(
                f"ONSCREEN_CORE_MISALIGNED: slides.{index} ({slide_id}).onscreen: "
                f"title + body cover {coverage:.0%} and body modules cover {body_coverage:.0%} "
                "of the core conclusion's semantic anchors (minimum 25% / 15%); organize the "
                "whole onscreen expression around core_message"
            )
    return issues

SPEAKER_NOTES_MIN_CHARS = 12

def check_speaker_notes_length(final_script: dict[str, Any], min_chars: int = SPEAKER_NOTES_MIN_CHARS) -> list[str]:
    """Flags a present-but-too-short `speaker_notes` field — a near-empty placeholder rather than
    an actual spoken elaboration. `min_chars` is deliberately low (12, not the 60 a denser-prose
    house style might use): this engine's `speaker_notes` are terse formal spoken sentences by
    design (see the Default register table in the AUTHOR skill), not full paragraphs, so the bar
    only needs to catch genuine stubs, not judge substance — substance is a Critic judgment call.
    Does not fire when `speaker_notes` is absent; the field is optional."""
    issues: list[str] = []
    for index, slide in enumerate(final_script.get("slides") or []):
        if not isinstance(slide, dict):
            continue
        notes = slide.get("speaker_notes")
        if isinstance(notes, str) and notes.strip() and len(notes.strip()) < min_chars:
            slide_id = slide.get("id") or f"#{index}"
            issues.append(f"slides.{index} ({slide_id}).speaker_notes: only {len(notes.strip())} characters (minimum {min_chars}) — looks like a placeholder rather than an actual spoken line")
    return issues

_COUNT_TOKEN = re.compile(r"([二两三四五六七八九十])(类|项|个|步|层|重|种|方面|大)")
_COUNT_WORDS = {"二": 2, "两": 2, "三": 3, "四": 4, "五": 5, "六": 6, "七": 7, "八": 8, "九": 9, "十": 10}
_ADDENDUM_MARKERS = ("此外", "另", "补充")

def _declared_count(text: str | None) -> int | None:
    """Extract a single unambiguous count claim from `text`, or None if there is zero or more
    than one candidate (ambiguous — e.g. a compound subtitle like "六类角色·四类模式" carries two
    distinct counts for two different sub-groupings; comparing either against a single onscreen
    module count would be a false positive, so it is deliberately left uncompared)."""
    if not text:
        return None
    matches = list(_COUNT_TOKEN.finditer(text))
    if len(matches) != 1:
        return None
    return _COUNT_WORDS.get(matches[0].group(1))

def check_declared_count(final_script: dict[str, Any]) -> list[str]:
    """Check an explicitly declared visible peer count against onscreen modules.

    Titles often name an object's intrinsic size (for example, a seven-category
    framework) without enumerating those seven categories on the current page.
    Regex-only inference therefore creates predictable false positives.  AUTHOR
    opts into this advisory check with ``onscreen_expected_peer_count`` only when
    the page actually promises a visible peer set.
    """
    warnings: list[str] = []
    for index, slide in enumerate(final_script.get("slides") or []):
        if not isinstance(slide, dict):
            continue
        onscreen = slide.get("onscreen") or []
        if not onscreen:
            continue
        expected = slide.get("onscreen_expected_peer_count")
        if not isinstance(expected, int) or isinstance(expected, bool) or expected < 1:
            continue
        declared = _declared_count(slide.get("subtitle")) or _declared_count(slide.get("title"))
        if declared is not None and declared != expected:
            slide_id = slide.get("id") or f"#{index}"
            warnings.append(
                f"slides.{index} ({slide_id}): title/subtitle declares a count of {declared} "
                f"but onscreen_expected_peer_count is {expected}"
            )
        counted = sum(
            1 for m in onscreen
            if isinstance(m, dict) and m.get("heading")
            and not str(m["heading"]).startswith(_ADDENDUM_MARKERS)
        )
        if counted != expected:
            slide_id = slide.get("id") or f"#{index}"
            warnings.append(f"slides.{index} ({slide_id}): expects {expected} visible peers but {counted} onscreen modules are in the enumerated set (excluding any 此外/另/补充-marked addendum)")
    return warnings

ONSCREEN_DETAIL_PHRASE_MAX_CHARS = 30
ONSCREEN_COMPLETE_PROPOSITION_MAX_CHARS = 90
_MEANINGFUL_CHAR_RE = re.compile(r"[一-鿿A-Za-z0-9]")
_LABEL_SPLIT_RE = re.compile(r"[：:]", flags=re.UNICODE)
_PHRASE_SEPARATOR_RE = re.compile(r"[、，,；;]")

def _meaningful_char_count(text: str) -> int:
    """Count visible Chinese/Latin/numeric characters only (whitespace and punctuation excluded),
    matching CyberPPT Stage 02's `meaningful_char_count` so this check predicts the same outcome
    as the downstream ImageGen readiness gate (`assert_imagegen_onscreen_readiness`)."""
    return len(_MEANINGFUL_CHAR_RE.findall(str(text or "")))


def _ends_with_punctuation_or_symbol(value: str) -> bool:
    stripped = str(value or "").rstrip()
    return bool(stripped) and unicodedata.category(stripped[-1])[0] in {"P", "S"}


def check_onscreen_terminal_punctuation(final_script: dict[str, Any]) -> list[str]:
    """Reject terminal punctuation/symbols in visible content-page copy.

    JSON already separates a module's heading, lead text and evidence items,
    so a terminal glyph only adds manuscript styling when Stage 02 lays the
    line into a PPT container. Internal notation and the renderer's structural
    heading-to-text separator remain unaffected.
    """
    issues: list[str] = []
    for index, slide in enumerate(final_script.get("slides") or []):
        if not isinstance(slide, dict) or slide.get("page_type") != "content":
            continue
        slide_id = slide.get("id") or f"#{index}"
        for module_index, module in enumerate(slide.get("onscreen") or []):
            if not isinstance(module, dict):
                continue
            fields: list[tuple[str, object]] = [
                ("heading", module.get("heading")),
                ("text", module.get("text")),
            ]
            fields.extend(
                (f"items[{item_index}]", item)
                for item_index, item in enumerate(module.get("items") or [])
            )
            for field, value in fields:
                if isinstance(value, str) and value.strip() and _ends_with_punctuation_or_symbol(value):
                    issues.append(
                        f"slides.{index} ({slide_id}).onscreen[{module_index}].{field}: "
                        f"visible onscreen copy must not end with punctuation or a symbol: '{value}'"
                    )
    return issues

def check_onscreen_detail_length(final_script: dict[str, Any], max_chars: int = ONSCREEN_DETAIL_PHRASE_MAX_CHARS) -> list[str]:
    """Flags an onscreen `text`/`items` phrase segment that exceeds `max_chars` meaningful
    characters (Chinese/Latin/numeric, punctuation and whitespace excluded). Compact details remain
    capped at `max_chars`, while a module's structurally declared lead `text` may use up to
    `ONSCREEN_COMPLETE_PROPOSITION_MAX_CHARS` without terminal punctuation. This keeps natural
    sentence-led copy available without allowing a paragraph to enter the visible layer. For a
    "label：body" line only `body` is measured, matching
    how a reader actually parses the line. For compact copy, the 30-character ceiling applies per
    short phrase, not to the whole line: a PPT line may hold several distinct, punctuation-separated
    phrases (e.g. "供得出、流得动、用得好、保安全"). Module headings are exempt — they carry their
    own length discipline and are not paragraph-risk the way detail lines are. Only `page_type == "content"`
    slides are checked, matching `assert_imagegen_onscreen_readiness`'s own scope: cover, chapter,
    and closing pages carry their body text through the template layer, not ImageGen, so Stage 02
    never enforces this ceiling on them."""
    issues: list[str] = []
    for index, slide in enumerate(final_script.get("slides") or []):
        if not isinstance(slide, dict) or slide.get("page_type") != "content":
            continue
        slide_id = slide.get("id") or f"#{index}"
        for module in slide.get("onscreen") or []:
            if not isinstance(module, dict):
                continue
            lines: list[tuple[str, str]] = []
            text = module.get("text")
            if isinstance(text, str) and text.strip():
                lines.append(("text", text))
            for item_index, item in enumerate(module.get("items") or []):
                if isinstance(item, str) and item.strip():
                    lines.append((f"items[{item_index}]", item))
            for field, line in lines:
                parts = _LABEL_SPLIT_RE.split(line, maxsplit=1)
                labelled_detail = len(parts) == 2 and bool(parts[1].strip())
                body = parts[1] if labelled_detail else line
                body_chars = _meaningful_char_count(body)
                if field == "text" and body_chars <= ONSCREEN_COMPLETE_PROPOSITION_MAX_CHARS:
                    continue
                for segment in _PHRASE_SEPARATOR_RE.split(body):
                    segment = segment.strip()
                    if not segment:
                        continue
                    chars = _meaningful_char_count(segment)
                    if chars > max_chars:
                        issues.append(f"slides.{index} ({slide_id}).onscreen.{field}: phrase '{segment}' has {chars} meaningful characters (> {max_chars}), will fail Stage 02's ImageGen readiness gate: '{line}'")
    return issues

def outline_final_script(final_script: dict[str, Any]) -> list[dict[str, Any]]:
    """Per-slide summary for human/Critic review: id, title, page_type, and the onscreen module
    headings with a count. Built specifically to make the Count-claim test fast to eyeball — e.g.
    a title claiming "五个维度" should visibly line up with 5 onscreen module headings here,
    without re-reading the full prose. Not a pass/fail check; a review aid."""
    rows: list[dict[str, Any]] = []
    for index, slide in enumerate(final_script.get("slides") or []):
        if not isinstance(slide, dict):
            continue
        headings = [m.get("heading") for m in (slide.get("onscreen") or []) if isinstance(m, dict) and m.get("heading")]
        rows.append({
            "id": slide.get("id") or f"#{index}",
            "title": slide.get("title"),
            "page_type": slide.get("page_type"),
            "onscreen_module_count": len(headings),
            "onscreen_headings": headings,
        })
    return rows
