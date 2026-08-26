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
    unsupported_summary_rule: str

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
                self.unsupported_summary_rule,
            )
        )


def default_visual_grammar() -> VisualGrammarContract:
    """Return compact ImageGen layout hygiene rules."""

    return VisualGrammarContract(
        image_text_rule=(
            "- Treat readable text modules as elements inside the dominant composition, "
            "using calm in-composition panels or annotations rather than a separate text "
            "column or rail. No body text on busy/high-contrast imagery. Do not fabricate "
            "dates, versions, IDs, tracking codes, status values, sample records, UI data, "
            "or any other realistic-looking examples."
        ),
        integrated_composition_rule=(
            "- Do not split the canvas into a text-only half and an image-only half, and do "
            "not create a separate photo rail or image collage beside the text. Build one "
            "integrated composition in which image-native forms, paths, bands, depth, and "
            "spatial relationships organize the text into one reading field. Use small "
            "semantic images only as subordinate accents where they clarify meaning."
        ),
        semantic_scene_rule=(
            "- First distinguish subject, support, input, output, convergence, branching, loop, "
            "hierarchy, contrast, and causality. Choose the visual grammar that best explains "
            "those relationships: an architecture diagram, process flow, layered system, "
            "relationship field, or another designed composition may all be appropriate. "
            "Avoid only mechanically repeated cards, nodes, or connectors that do not clarify "
            "the page logic; let hierarchy and content determine visual weight and reading order."
        ),
        connector_rule=(
            "- No connectors through/under text; no fake flow lines; one connector style."
        ),
        hierarchy_rule=(
            "- Unequal visual weight by hierarchy — not an equal card wall."
        ),
        semantic_binding_rule=(
            "- Bind each real-world image to one specific nearby business meaning. Do not use "
            "generic offices, skylines, campuses, server rooms, or technology scenes merely to "
            "fill whitespace."
        ),
        multi_image_rule=(
            "- Multiple images are allowed when they carry distinct and necessary semantic roles."
        ),
        generic_scene_rule=(
            "- Do not use one generic industry scene to represent several unrelated meanings. "
            "Icons may be low-contrast micro-annotations only, never primary nodes, repeated "
            "module markers, card headings, or the visual mainline."
        ),
        unsupported_summary_rule=(
            "- Do not invent summary, goal, value, outcome, or conclusion sections or labels. "
            "Any outcome inferred from the relationships may be expressed only as an unlabeled "
            "graphical state unless that text is present in the locked on-screen content."
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
            "integrated composition in which image-native forms, paths, bands, depth, and "
            "spatial relationships organize the text into one reading field. Use small "
            "semantic images only as subordinate accents where they clarify meaning.",
            "- First distinguish subject, support, input, output, convergence, branching, loop, "
            "hierarchy, contrast, and causality. Choose the visual grammar that best explains "
            "those relationships: an architecture diagram, process flow, layered system, "
            "relationship field, or another designed composition may all be appropriate. "
            "Avoid only mechanically repeated cards, nodes, or connectors that do not clarify "
            "the page logic; let hierarchy and content determine visual weight and reading order.",
            "- Do not run connectors, decorative lines, or image details through body text.",
            "- Supporting imagery, charts, interface-like forms, and concise auxiliary labels "
            "are allowed when they improve the overall visual idea. They do not need a "
            "one-to-one mapping to every locked module.",
            "- Do not repeat the page relationship as a second miniature flow, icon chain, "
            "summary strip, or duplicate diagram. Render supplied relationship or business-meaning "
            "copy once as a calm annotation integrated into the main composition.",
            "- Make the relationship between modules the visual protagonist, not a literal symbol "
            "of the topic. Do not enlarge shields, locks, databases, clouds, chips, people, or charts "
            "into a hero object. For abstract system, governance, security, architecture, or operations "
            "pages, interface-like composition is allowed but must not be suggested as the default. "
            "The model may choose it only when the content benefits. All visible text, numbers, "
            "states, and records must come from the locked content; do not fabricate UI facts or "
            "default any page to a dashboard.",
            "- Aim for mature restraint: generous quiet space, precise thin strokes, limited deep-blue "
            "mass, flat materials, and almost no shadow. Avoid bevels, heavy drop shadows, 3D badges, "
            "and template-like decoration.",
            "- Use photography only when it directly explains a specific business object. Do not "
            "fill whitespace with generic offices, skylines, campuses, server rooms, or technology scenes.",
            "- Default to an empty auxiliary-label allowlist. Do not derive or summarize new "
            "node names, stage names, input/output terms, status words, legends, icon captions, "
            "side labels, Latin letters, or abbreviations. Unlabeled interface shapes are allowed; "
            "text-bearing interface tokens remain subject to the allowlist. Auxiliary "
            "labels may appear only when the upstream script explicitly supplies a non-empty "
            "allowlist, and then only the allowlisted text may be rendered.",
            "- Do not invent summary, goal, value, outcome, or conclusion sections or labels. "
            "Any outcome inferred from the relationships may be expressed only as an unlabeled "
            "graphical state unless that text is present in the locked on-screen content.",
        )
    )
