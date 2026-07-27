"""Semantic contracts and natural-language creative briefs for ImageGen.

The structures in this module help the compiler preserve meaning and control
risk.  They deliberately avoid coordinates, topology, panel counts, and other
layout prescriptions: ImageGen remains responsible for finding the visual
solution.
"""

from __future__ import annotations

import re
from dataclasses import asdict, dataclass
from typing import Iterable


_EXACT_FACT_RE = re.compile(
    r"(?<![A-Za-z])(?:\d+(?:\.\d+)?%|\d+(?:\.\d+)?(?:亿|万|千|百)?"
    r"(?:千瓦时|千瓦|小时|天|月|年)|\d+(?:\.\d+)?)"
)

_RELATION_CREATIVE_LANGUAGE: dict[str, tuple[str, str]] = {
    "decision_admission": (
        "The viewer should understand why the initial choice is justified and why later "
        "items remain conditional.",
        "Find a convincing visual expression for selection, readiness, and conditional entry "
        "without turning the page into an administrative process diagram.",
    ),
    "comparison": (
        "The compared meanings must remain aligned to the same basis, with only supported "
        "differences and priorities made visible.",
        "Find a visually immediate way to reveal the meaningful contrast while preserving "
        "the shared basis and avoiding invented scores or rankings.",
    ),
    "scenario_application": (
        "The business setting, the value created there, and the conditions that enable it "
        "must remain connected.",
        "Create one credible business world in which the scenario, its value, and its "
        "readiness can be understood naturally.",
    ),
    "multi_semantic_foundation": (
        "The distinct existing foundations must all remain recognizable, and their combined "
        "support is the essential meaning of the page.",
        "Make the foundations feel like parts of one credible, continuously operating "
        "business reality rather than isolated capabilities.",
    ),
    "causal": (
        "The stated causes or changes must remain connected to the business consequence and "
        "the need for action.",
        "Find a visually convincing way to make change and consequence feel connected in one "
        "coherent business world.",
    ),
    "closed_loop": (
        "Inputs, usable results, validation, and feedback must remain understandable as a "
        "continuing business relationship.",
        "Express continuous operation and improvement through a coherent business situation; "
        "the visual solution does not need to resemble a software workflow.",
    ),
    "phase": (
        "The different purpose and conditional nature of each stage must remain clear.",
        "Create a strong sense of progression and readiness while choosing the visual form "
        "freely.",
    ),
    "capability_relationship": (
        "The capabilities must remain connected to the business value they jointly support.",
        "Find an integrated visual expression in which the capabilities feel useful and "
        "mutually supportive rather than like isolated software modules.",
    ),
    "judgment_evidence": (
        "The supporting meanings must jointly substantiate the page's central judgment.",
        "Create a coherent editorial visual in which the judgment is felt first and the "
        "supporting meanings remain easy to recognize.",
    ),
}

_RELATION_AVOIDS: dict[str, tuple[str, ...]] = {
    "decision_admission": ("generic administration steps", "equal criterion cards"),
    "comparison": ("invented scores or rankings", "unaligned comparison cards"),
    "scenario_application": ("product-feature showcase", "unrelated technology interface"),
    "multi_semantic_foundation": ("one picture per foundation", "equal card wall"),
    "causal": ("unrelated fact list", "decorative trend arrows"),
    "closed_loop": ("software workflow", "lifecycle icon circle"),
    "phase": ("equal-weight timeline", "decorative milestone roadmap"),
    "capability_relationship": ("generic software architecture", "center-satellite icon diagram"),
    "judgment_evidence": ("equal card wall", "unrelated decorative scene"),
}


@dataclass(frozen=True)
class SemanticContract:
    core_judgment: str
    required_meanings: tuple[str, ...]
    exact_facts: tuple[str, ...]
    forbidden_inferences: tuple[str, ...]

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


@dataclass(frozen=True)
class CreativeFreedom:
    semantic: str
    text: str
    composition: str
    scene: str

    def to_dict(self) -> dict[str, str]:
        return asdict(self)


@dataclass(frozen=True)
class CreativeBrief:
    relation: str
    page_purpose: str
    visual_message: str
    semantic_contract: SemanticContract
    freedom: CreativeFreedom
    page_specific_avoids: tuple[str, ...]
    source_composition_reference: str = ""

    def to_dict(self) -> dict[str, object]:
        return {
            "relation": self.relation,
            "page_purpose": self.page_purpose,
            "visual_message": self.visual_message,
            "semantic_contract": self.semantic_contract.to_dict(),
            "freedom": self.freedom.to_dict(),
            "page_specific_avoids": list(self.page_specific_avoids),
            "source_composition_reference": self.source_composition_reference,
        }


def _clean_meanings(values: Iterable[str]) -> tuple[str, ...]:
    result: list[str] = []
    for value in values:
        cleaned = re.sub(r"\s+", " ", str(value or "")).strip(" -*：:")
        if cleaned and cleaned not in result:
            result.append(cleaned)
    return tuple(result)


def extract_exact_facts(text: str) -> tuple[str, ...]:
    """Return locked numeric facts in stable first-seen order."""

    result: list[str] = []
    for value in _EXACT_FACT_RE.findall(text):
        if value not in result:
            result.append(value)
    return tuple(result)


def build_semantic_contract(
    *,
    core_judgment: str,
    required_meanings: Iterable[str],
    onscreen_text: str,
) -> SemanticContract:
    return SemanticContract(
        core_judgment=core_judgment.strip(),
        required_meanings=_clean_meanings(required_meanings),
        exact_facts=extract_exact_facts(onscreen_text),
        forbidden_inferences=(
            "Do not add facts, numbers, organization claims, or conclusions that are not "
            "present in the locked on-screen text.",
        ),
    )


def _freedom_for(*, onscreen_text: str, exact_fact_count: int) -> CreativeFreedom:
    text_chars = len(re.sub(r"\s+", "", onscreen_text))
    text_guidance = (
        "The locked wording is exact. Do not add, paraphrase, shorten, or replace it."
    )
    scene_guidance = (
        "Keep imagery restrained and calm enough that it never competes with the body text."
        if text_chars >= 320
        else "Choose imagery freely when it clarifies the business meaning."
    )
    if exact_fact_count:
        text_guidance += " Preserve every locked number and unit exactly; generate no extra values."
    return CreativeFreedom(
        semantic=(
            "The required meanings and their business relationship are fixed; their visual "
            "representation is open."
        ),
        text=text_guidance,
        composition=(
            "Choose the strongest overall composition, visual carrier, spatial organization, "
            "and hierarchy yourself. No diagram topology or panel arrangement is prescribed."
        ),
        scene=scene_guidance,
    )


def build_creative_brief(
    *,
    relation: str,
    page_purpose: str,
    core_judgment: str,
    required_meanings: Iterable[str],
    onscreen_text: str,
    override: dict[str, str] | None = None,
) -> CreativeBrief:
    contract = build_semantic_contract(
        core_judgment=core_judgment,
        required_meanings=required_meanings,
        onscreen_text=onscreen_text,
    )
    invariant, creative_language = _RELATION_CREATIVE_LANGUAGE.get(
        relation,
        _RELATION_CREATIVE_LANGUAGE["judgment_evidence"],
    )
    override = override if isinstance(override, dict) else {}
    visual_message = (
        override.get("visual_thesis")
        or override.get("decision_relationship")
        or core_judgment
        or invariant
    ).strip()
    avoids = list(_RELATION_AVOIDS.get(relation, _RELATION_AVOIDS["judgment_evidence"]))
    explicit_avoid = str(override.get("avoid_on_this_page") or "").strip()
    if explicit_avoid:
        avoids[0] = explicit_avoid
    return CreativeBrief(
        relation=relation,
        page_purpose=page_purpose.strip(),
        visual_message=f"{visual_message} {invariant}".strip(),
        semantic_contract=contract,
        freedom=_freedom_for(
            onscreen_text=onscreen_text,
            exact_fact_count=len(contract.exact_facts),
        ),
        page_specific_avoids=tuple(avoids[:2]),
        source_composition_reference=str(
            override.get("recommended_composition") or ""
        ).strip(),
    )


def render_creative_brief(brief: CreativeBrief) -> str:
    """Render a concise natural-language brief, not a layout specification."""

    meanings = "; ".join(brief.semantic_contract.required_meanings) or "the locked meanings"
    lines = [
        "[Page-specific creative brief — context only; do not render these labels or instructions]",
        f"Purpose: {brief.page_purpose or brief.semantic_contract.core_judgment}",
        f"Visual message: {brief.visual_message}",
        (
            "Meanings that must remain recognizable: "
            f"{meanings}. Their wording and business meaning are fixed."
        ),
    ]
    lines.extend(
        (
            brief.freedom.semantic,
            brief.freedom.text,
            brief.freedom.composition,
            brief.freedom.scene,
            "Avoid on this page: " + "; ".join(brief.page_specific_avoids) + ".",
        )
    )
    return "\n".join(lines)
