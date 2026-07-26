"""Shared permissive visual-expression rules with semantic boundaries."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class VisualGrammarContract:
    image_text_rule: str
    connector_rule: str
    hierarchy_rule: str
    semantic_binding_rule: str
    multi_image_rule: str
    generic_scene_rule: str

    def render(self) -> str:
        return "\n".join(
            (
                self.image_text_rule,
                self.connector_rule,
                self.hierarchy_rule,
                self.semantic_binding_rule,
                self.multi_image_rule,
                self.generic_scene_rule,
            )
        )


def default_visual_grammar() -> VisualGrammarContract:
    """Return compact ImageGen layout hygiene rules."""

    return VisualGrammarContract(
        image_text_rule=(
            "- Treat readable text modules as elements inside the dominant composition, "
            "using calm in-composition panels or annotations rather than a separate text "
            "column or rail. No body text on busy/high-contrast imagery."
        ),
        connector_rule=(
            "- No connectors through/under text; no fake flow lines; one connector style."
        ),
        hierarchy_rule=(
            "- Unequal visual weight by hierarchy — not an equal card wall."
        ),
        semantic_binding_rule=(
            "- Bind each real-world image to one specific nearby business meaning."
        ),
        multi_image_rule=(
            "- Multiple images are allowed when they carry distinct and necessary semantic roles."
        ),
        generic_scene_rule=(
            "- Do not use one generic industry scene to represent several unrelated meanings."
        ),
    )
