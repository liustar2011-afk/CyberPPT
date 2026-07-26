"""Shared permissive visual-expression rules with semantic boundaries."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class VisualGrammarContract:
    image_text_rule: str
    connector_rule: str
    hierarchy_rule: str

    def render(self) -> str:
        return "\n".join(
            (
                self.image_text_rule,
                self.connector_rule,
                self.hierarchy_rule,
            )
        )


def default_visual_grammar() -> VisualGrammarContract:
    """Return compact ImageGen layout hygiene rules."""

    return VisualGrammarContract(
        image_text_rule="- No body text on busy/high-contrast imagery.",
        connector_rule=(
            "- No connectors through/under text; no fake flow lines; one connector style."
        ),
        hierarchy_rule=(
            "- Unequal visual weight by hierarchy — not an equal card wall."
        ),
    )
