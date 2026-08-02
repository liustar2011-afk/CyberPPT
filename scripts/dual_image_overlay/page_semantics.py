"""Page-semantic routing primitives shared by prompt compilers.

The legacy handoff module still owns the detailed routing rules for backward
compatibility.  This module owns the *decision bundle* passed between parsing,
visual routing, and prompt compilation so those stages no longer exchange a
long list of loosely-related dictionaries.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, Mapping

from cyberppt.script_quality_contract import ScriptPage


IntentResolver = Callable[
    [ScriptPage, str, Mapping[str, str] | None, Mapping[str, str] | None],
    tuple[str, str],
]
RelationExtractor = Callable[[ScriptPage], str]


@dataclass(frozen=True)
class PageSemanticContext:
    """Immutable semantic inputs for one prompt compilation."""

    page_id: str
    mission: str
    relation: str
    intent_source: str
    visual_context: dict[str, str] = field(default_factory=dict)
    visual_intent_override: dict[str, str] = field(default_factory=dict)
    semantic_relations: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "page_id": self.page_id,
            "mission": self.mission,
            "relation": self.relation,
            "intent_source": self.intent_source,
            "visual_context": dict(self.visual_context),
            "visual_intent_override": dict(self.visual_intent_override),
            "semantic_relations": self.semantic_relations,
        }


def derive_page_semantics(
    page: ScriptPage,
    *,
    page_mission: str = "",
    visual_context: Mapping[str, str] | None = None,
    visual_intent_override: Mapping[str, str] | None = None,
    resolve_intent: IntentResolver,
    extract_relations: RelationExtractor,
) -> PageSemanticContext:
    """Build a deterministic semantic bundle from the approved page contract."""

    context = {
        str(key): str(value)
        for key, value in (visual_context or {}).items()
        if str(value).strip()
    }
    override = {
        str(key): str(value)
        for key, value in (visual_intent_override or {}).items()
        if str(value).strip()
    }
    relation, source = resolve_intent(page, page_mission, context, override)
    relations = extract_relations(page)
    return PageSemanticContext(
        page_id=page.page_id,
        mission=page_mission.strip(),
        relation=relation,
        intent_source=source,
        visual_context=context,
        visual_intent_override=override,
        semantic_relations=relations,
    )


def relation_is_confident(context: PageSemanticContext) -> bool:
    """Whether the relation can be safely forwarded as semantic context."""

    return context.relation != "judgment_evidence" and context.intent_source in {
        "explicit",
        "hint",
        "contract_relation",
        "scored",
    }


__all__ = [
    "PageSemanticContext",
    "derive_page_semantics",
    "relation_is_confident",
]
