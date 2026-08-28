"""Validation helpers for Script Engine delivery contracts."""
from __future__ import annotations
import difflib, json, re, unicodedata
from pathlib import Path
from typing import Any, Iterator
from jsonschema import Draft202012Validator

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
    return issues

_ITEM_SIMILARITY_THRESHOLD = 0.6

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
