"""Build and verify the Stage 02 content-structure integrity contract.

Locked body text (``stage02_handoff._locked_text_items``) guarantees that
individual sentences survive Stage 02 unchanged.  It says nothing about the
relationships *between* sentences: which lines are root modules, which are
nested details, and what order they came in.  ``ContentIntegrityContract``
is the companion structural lock -- built from the same ordered, deduplicated
line list used for ``text_id`` assignment, so the two can never drift apart
by construction.
"""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass, field
from typing import Any

from cyberppt.visual_structure_contract import normalize_page_id

CONTENT_INTEGRITY_SCHEMA = "cyberppt.content_integrity.v1"

_TRAILING_PUNCTUATION = "。；，、：？！.!?;,:"


def _compact(value: object) -> str:
    return re.sub(r"\s+", "", str(value or ""))


def _line_indent(line: str) -> int:
    return len(line) - len(line.lstrip(" "))


def extract_onscreen_line_items(text: str) -> list[tuple[str, int]]:
    """Clean, dedupe, and index onscreen text lines, preserving indentation.

    Mirrors the cleaning rules of the locked-text extractor exactly (strip
    heading markers, list markers, bold markers, and trailing punctuation;
    drop blanks; dedupe by compacted text) so the resulting order and text
    are identical to ``stage02_handoff``'s ``text_id`` assignment. The only
    difference is that indentation is retained here for tree construction.
    """

    items: list[tuple[str, int]] = []
    seen: set[str] = set()
    for raw in text.splitlines():
        indent = _line_indent(raw)
        line = raw.strip()
        if not line:
            continue
        line = re.sub(r"^#{1,6}\s*", "", line)
        line = re.sub(r"^[-*+]\s*", "", line)
        line = line.replace("**", "").strip()
        if not line:
            continue
        line = line.rstrip(_TRAILING_PUNCTUATION)
        if not line:
            continue
        key = _compact(line)
        if key in seen:
            continue
        seen.add(key)
        items.append((line, indent))
    return items


@dataclass(frozen=True)
class ContentNode:
    text_id: str
    text: str
    source_level: int
    parent_id: str | None
    root_id: str
    children: tuple[str, ...]
    ordinal: int
    content_role: str
    promotion_policy: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "text_id": self.text_id,
            "text": self.text,
            "source_level": self.source_level,
            "parent_id": self.parent_id,
            "root_id": self.root_id,
            "children": list(self.children),
            "ordinal": self.ordinal,
            "content_role": self.content_role,
            "promotion_policy": self.promotion_policy,
        }


@dataclass(frozen=True)
class ContentIntegrityContract:
    schema: str
    page_id: str
    source_hash: str
    root_nodes: tuple[str, ...]
    nodes: tuple[ContentNode, ...] = field(default_factory=tuple)
    source_order: tuple[str, ...] = field(default_factory=tuple)
    structure_hash: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema": self.schema,
            "page_id": self.page_id,
            "source_hash": self.source_hash,
            "root_nodes": list(self.root_nodes),
            "nodes": [node.to_dict() for node in self.nodes],
            "source_order": list(self.source_order),
            "structure_hash": self.structure_hash,
        }


def _structure_hash(nodes: list[ContentNode]) -> str:
    return structure_hash_from_node_dicts([node.to_dict() for node in nodes])


def structure_hash_from_node_dicts(nodes: list[dict[str, Any]]) -> str:
    """Recompute the structure hash from serialized node dicts.

    Used by ``stage02_handoff.audit_stage02_handoff`` to check that a
    persisted contract's ``structure_hash`` still matches its own ``nodes``
    (internal self-consistency, not a re-parse of the source script).
    """

    canonical = [
        [node.get("text_id"), node.get("parent_id"), node.get("source_level"), node.get("ordinal")]
        for node in nodes
    ]
    payload = json.dumps(canonical, ensure_ascii=False, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _source_hash(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def build_content_integrity_contract(page: Any) -> ContentIntegrityContract:
    """Build the content-structure contract for one content page.

    Uses only explicit Markdown indentation (no NLP-based guessing) to
    resolve parent/child relationships: a stack of ``(indent, text_id)``
    pairs is popped whenever a new line's indent is not strictly deeper than
    the stack top, so the remaining top is the new line's parent (or the
    line is a root when the stack is empty). A page with uniformly flat
    indentation legitimately degrades to an all-root, childless tree; that
    is not treated as an error.
    """

    page_id = normalize_page_id(page.page_id, page.sequence).upper()
    line_items = extract_onscreen_line_items(page.onscreen_text)

    nodes: list[ContentNode] = []
    children_map: dict[str, list[str]] = {}
    root_ids: list[str] = []
    stack: list[tuple[int, str]] = []
    parent_of: dict[str, str | None] = {}
    root_of: dict[str, str] = {}

    for ordinal, (text, indent) in enumerate(line_items, start=1):
        text_id = f"{page_id}-T{ordinal:02d}"
        while stack and stack[-1][0] >= indent:
            stack.pop()
        parent_id = stack[-1][1] if stack else None
        parent_of[text_id] = parent_id
        source_level = _depth(parent_of, text_id)
        root_id = text_id if parent_id is None else root_of[parent_id]
        root_of[text_id] = root_id
        if parent_id is None:
            root_ids.append(text_id)
        else:
            children_map.setdefault(parent_id, []).append(text_id)
        content_role = "root_module" if parent_id is None else "detail"
        promotion_policy = "root_only" if parent_id is None else "forbidden"
        nodes.append(
            ContentNode(
                text_id=text_id,
                text=text,
                source_level=source_level,
                parent_id=parent_id,
                root_id=root_id,
                children=(),
                ordinal=ordinal,
                content_role=content_role,
                promotion_policy=promotion_policy,
            )
        )
        stack.append((indent, text_id))

    nodes = [
        ContentNode(
            text_id=node.text_id,
            text=node.text,
            source_level=node.source_level,
            parent_id=node.parent_id,
            root_id=node.root_id,
            children=tuple(children_map.get(node.text_id, ())),
            ordinal=node.ordinal,
            content_role=node.content_role,
            promotion_policy=node.promotion_policy,
        )
        for node in nodes
    ]

    return ContentIntegrityContract(
        schema=CONTENT_INTEGRITY_SCHEMA,
        page_id=page_id,
        source_hash=_source_hash(page.onscreen_text),
        root_nodes=tuple(root_ids),
        nodes=tuple(nodes),
        source_order=tuple(node.text_id for node in nodes),
        structure_hash=_structure_hash(nodes),
    )


def _depth(parent_of: dict[str, str | None], text_id: str) -> int:
    depth = 1
    current = parent_of.get(text_id)
    while current is not None:
        depth += 1
        current = parent_of.get(current)
    return depth
