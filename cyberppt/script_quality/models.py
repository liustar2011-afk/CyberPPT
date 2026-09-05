from __future__ import annotations

from dataclasses import dataclass


# ``semantic_only`` remains an ImageGen-facing legacy mode.  The two new
# authoring modes govern Stage 01 script review without changing that consumer.
ONSCREEN_JUDGMENT_MODES = (
    "locked",
    "semantic_only",
    "semantic_alignment",
    "hidden",
)
SEMANTIC_ONLY_JUDGMENT_ROLES = {
    "relationship",
    "positioning",
    "boundary",
    "mechanism",
}
LOCKED_JUDGMENT_ROLES = {
    "fact",
    "metric",
    "milestone",
    "acceptance",
    "prohibition",
}
VALID_CONTENT_LOADS = {"light", "standard", "dense"}


def resolve_judgment_mode(explicit_mode: str = "", judgment_role: str = "") -> str:
    """Resolve display policy from an explicit override, then semantic role."""

    mode = explicit_mode.strip()
    role = judgment_role.strip()
    if mode:
        if mode not in ONSCREEN_JUDGMENT_MODES:
            raise ValueError(f"unsupported onscreen_judgment_mode: {mode}")
        return mode
    if role in SEMANTIC_ONLY_JUDGMENT_ROLES:
        return "semantic_only"
    if role in LOCKED_JUDGMENT_ROLES:
        return "locked"
    if not role:
        # The complete core message is authoring and audit truth.  It is not
        # a default audience paragraph; authors may supply a short subtitle
        # when the page needs one.
        return "semantic_only"
    raise ValueError(f"unsupported judgment_role: {role}")


@dataclass(frozen=True)
class ScriptPage:
    page_id: str
    sequence: int
    heading: str
    page_type: str
    title: str
    main_message: str
    full_prose: str
    selection_notes: str
    evidence_map: str
    evidence_map_refs: tuple[str, ...]
    source_refs: tuple[str, ...]
    boundary_source_refs: tuple[str, ...]
    boundary: str
    visual_structure: str
    onscreen_text: str
    module_titles: tuple[str, ...]
    raw_onscreen_text: str = ""
    onscreen_source: str = "authored"
    top_level_module_titles: tuple[str, ...] = ()
    subtitle: str = ""
    content_load: str = ""
    visual_proof: str = ""
    onscreen_judgment: str = ""
    judgment_role: str = ""
    onscreen_judgment_mode: str = ""
    visual_intent_type: str = ""
    visual_carrier: str = ""
    image_locked_text: str = ""
    onscreen_expression_form: str = ""
    layout_motif: str = ""
    scene_role: str = ""
    page_mission: str = ""
    argument_chain: str = ""
    provenance_refs: tuple[str, ...] = ()
    field_order: tuple[str, ...] = ()
    coaching_tip: str = ""
    speaker_notes: str = ""
    anchor_coverage_notes: str = ""
    contract_receipt: dict[str, object] | None = None
    prose_paragraph_map: tuple[tuple[tuple[str, ...], str], ...] = ()

    def __post_init__(self) -> None:
        # Callers that predate the top-level/nested distinction (hand-built
        # ScriptPage fixtures, tests) only ever set ``module_titles``. Treat
        # every module as top-level for them, preserving prior behavior.
        # ``parse_script_markdown`` explicitly passes the indentation-aware
        # value, which is the only place this can legitimately differ.
        if not self.top_level_module_titles and self.module_titles:
            object.__setattr__(
                self, "top_level_module_titles", self.module_titles
            )
        if self.content_load and self.content_load not in VALID_CONTENT_LOADS:
            raise ValueError(f"unsupported content_load: {self.content_load}")

    @property
    def core_message(self) -> str:
        """Canonical v2 semantic center; main_message remains a read alias."""

        return self.main_message

    @property
    def onscreen_conclusion(self) -> str:
        return self.onscreen_judgment

    @property
    def content_relations(self) -> tuple[dict[str, object], ...]:
        """Return explicit script-contract relations or a Stage 02 projection.

        Legacy CyberPPT scripts can carry a hidden page-contract receipt with
        ``content_relations``.  CyberPPT-Script v0.4+ instead keeps the final
        Markdown audience-clean and expresses drawable semantic relationships
        in ``### 视觉结构``.  Stage 02 owns the deterministic adapter between
        those two contracts; the source Markdown itself is never modified.
        """

        receipt = self.contract_receipt or {}
        relations = receipt.get("content_relations")
        explicit = tuple(
            item for item in relations or [] if isinstance(item, dict)
        ) if isinstance(relations, list) else ()
        if explicit:
            return explicit

        from cyberppt.stage02_relationship_adapter import derive_business_relationships

        return derive_business_relationships(
            visual_structure=self.visual_structure,
            title=self.title,
            module_titles=self.module_titles,
            top_level_module_titles=self.top_level_module_titles,
        )


@dataclass(frozen=True)
class ScriptDocument:
    pages: tuple[ScriptPage, ...]


@dataclass(frozen=True)
class ScriptQualityIssue:
    code: str
    severity: str
    message: str
    pages: tuple[str, ...] = ()
    source_ids: tuple[str, ...] = ()
    evidence: tuple[str, ...] = ()
    suggested_action: str = ""

    def to_dict(self) -> dict[str, object]:
        return {
            "code": self.code,
            "severity": self.severity,
            "message": self.message,
            "pages": list(self.pages),
            "source_ids": list(self.source_ids),
            "evidence": list(self.evidence),
            "suggested_action": self.suggested_action,
        }


def _issue(
    code: str,
    page: ScriptPage,
    message: str,
    action: str,
    source_ids: tuple[str, ...] = (),
    evidence: tuple[str, ...] = (),
    severity: str = "error",
) -> ScriptQualityIssue:
    if severity not in {"error", "warning"}:
        raise ValueError(f"unsupported severity: {severity}")
    return ScriptQualityIssue(
        code=code,
        severity=severity,
        message=message,
        pages=(page.page_id,),
        source_ids=source_ids,
        evidence=evidence,
        suggested_action=action,
    )


@dataclass(frozen=True)
class PageRelationshipSummary:
    """Structured relationship evidence used only during script auditing."""

    page_id: str
    entry_conditions: tuple[str, ...]
    page_transformation: str
    exit_handoffs: tuple[str, ...]
    excluded_scope: tuple[str, ...]
    visible_relation: bool
