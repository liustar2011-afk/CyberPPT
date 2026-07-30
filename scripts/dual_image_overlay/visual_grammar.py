"""Shared permissive visual-expression rules with semantic boundaries."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class VisualGrammarContract:
    image_text_rule: str
    integrated_composition_rule: str
    semantic_scene_rule: str
    connector_rule: str
    hierarchy_rule: str
    semantic_binding_rule: str
    multi_image_rule: str
    generic_scene_rule: str

    def render(self) -> str:
        return "\n".join(
            (
                self.image_text_rule,
                self.integrated_composition_rule,
                self.semantic_scene_rule,
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
        integrated_composition_rule=(
            "- Do not split the canvas into a text-only half and an image-only half, and do "
            "not create a separate photo rail or image collage beside the text. Build one "
            "integrated composition: place semantic visuals within the same overall reading "
            "field as the nearby text modules, with varied scale, staggered placement, and "
            "shared whitespace. Each visual must directly clarify the adjacent statement."
        ),
        semantic_scene_rule=(
            "- Use process, hierarchy, paths, convergence, branching, and causal relationships "
            "when they make the locked text easier to understand and give its reading order "
            "clear visual motion. Let the graphic forms embody the relationships instead of "
            "reducing them to plain boxes and generic connector lines. Do not replace the text "
            "relationships with a decorative scene or generic office photo."
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


def creative_brief_visual_grammar() -> str:
    """Return only universal hygiene rules for the creative-brief compiler.

    Page-specific failure modes belong in the creative brief.  Keeping them out
    of this shared contract prevents every page from inheriting the same visual
    anxieties and converging on one defensive layout.
    """

    return "\n".join(
        (
            "- Keep all locked body text clear and readable; do not place it over busy or "
            "high-contrast imagery.",
            "- Do not split the canvas into a text-only half and an image-only half, and do "
            "not create a separate photo rail or image collage beside the text. Build one "
            "integrated composition with semantic visuals embedded among the nearby text "
            "modules through varied scale, staggered placement, and shared whitespace.",
            "- Use process, hierarchy, paths, convergence, branching, and causal relationships "
            "when they make the locked text easier to understand and give its reading order "
            "clear visual motion. Let the graphic forms embody the relationships instead of "
            "reducing them to plain boxes and generic connector lines. Do not replace the text "
            "relationships with a decorative scene or generic office photo.",
            "- Do not run connectors, decorative lines, or image details through body text.",
            "- Supporting imagery, charts, interface-like forms, and concise auxiliary labels "
            "are allowed when they improve the overall visual idea. They do not need a "
            "one-to-one mapping to every locked module.",
            "- Auxiliary text may appear. Keep it brief and coherent, and do not use it to "
            "invent new factual numbers, organization claims, or unsupported conclusions.",
        )
    )
