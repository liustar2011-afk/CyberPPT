#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path


def _connector_text(page: dict) -> str:
    return "\n".join(
        f"- {c['from']} -> {c['to']}: {c['type']} / {c['direction']} / {c['label']}"
        for c in page.get("connectors", [])
    ) or "- No business arrows; use spatial adjacency only."


def _required_text_values(page: dict) -> list[str]:
    handoff = page["generation_handoff"]
    text_ids = [str(value) for value in handoff.get("required_text_ids") or []]
    if not text_ids:
        return [str(value) for value in handoff["required_text"]]
    final_by_id: dict[str, str] = {}
    for item in page.get("final_text") or []:
        text_id = str(item.get("id") or "")
        if not text_id or text_id in final_by_id:
            raise ValueError(f"duplicate or empty final_text id: {text_id!r}")
        final_by_id[text_id] = str(item.get("text") or "")
    unknown = [text_id for text_id in text_ids if text_id not in final_by_id]
    if unknown:
        raise ValueError(f"required_text_ids reference unknown final_text ids: {unknown}")
    values = [final_by_id[text_id] for text_id in text_ids]
    declared = [str(value) for value in handoff.get("required_text") or []]
    if declared and declared != values:
        raise ValueError("required_text differs from required_text_ids/final_text")
    return values


def _binding_text(page: dict) -> str:
    lines: list[str] = []
    for item in page["structural_decision"]["text_bindings"]:
        text_ids = [str(value) for value in item.get("text_ids") or []]
        suffix = f" / locked text ids: {', '.join(text_ids)}" if text_ids else ""
        lines.append(
            f"- Text binding: {item['evidence_id']} -> {item['target_ref']} / {item['binding']}{suffix}"
        )
    return "\n".join(lines)


def _legacy_page_prompt(page: dict) -> str:
    vd = page["visual_decision"]
    structural = page.get("structural_decision") or {}
    sg = page["semantic_graph"]
    ip = page["image_plan"]
    ti = page["text_integration"]
    handoff = page["generation_handoff"]
    reading = " -> ".join(vd["reading_path"])
    focus = structural.get("semantic_focus") or {}
    grammar = ", ".join(structural.get("spatial_grammar") or [])
    dominant = vd.get("dominant_visual_carrier") or (
        f"semantic focus {focus.get('ref', '')} expressed through {grammar}"
    ).strip()
    avoid = "; ".join(page.get("avoid", []) + handoff.get("negative_constraints", []))
    required_text = "\n".join(f"- {text}" for text in _required_text_values(page))
    connectors = _connector_text(page)
    return f'''# Page {page["page_number"]}: {page["page_title"]}

[Content lock]
Preserve all required on-screen text, numbers, units, names, status words, and business relationships. Do not paraphrase unless the content lock explicitly allows it.

[Mandatory composition guidance] Apply this layout guidance before placing any on-screen text. Do not render its field names or instruction text.
[Prompt context] Page-specific visual intent (composition guidance only; do not render field names or instruction text)
- Selected visual intent type: {vd["visual_intent_type"]}
- Visual thesis: {vd["visual_thesis"]}
- Decision relationship: {sg["decision_relationship"]}
- Dominant visual carrier: {dominant}
- Recommended composition: {vd["spatial_organization"]}
- Reading path: {reading}
- Industry scene anchor: {ip["scene_type"]}; business object: {ip["business_object"]}; semantic role: {ip["semantic_role"]}; placement: {ip["placement"]}
- Text integration: {vd["text_integration_method"]}
- Relationship encoding: {vd["relationship_encoding"]}
- Avoid on this page: {avoid}

[Connector map]
{connectors}

[Text rendering]
- Font: {ti["font_family"]}
- Minimum size equivalent: {ti["minimum_font_pt"]}pt
- Body rendering mode: {ti["body_render_mode"]}
- Placement strategy: {ti["placement_strategy"]}
- {handoff["title_exclusion_instruction"]}

[Required on-screen body text]
{required_text}

[Style]
{handoff["style_guidance"]}

[Negative constraints]
{avoid}
'''


def _structural_page_prompt(page: dict) -> str:
    vd = page["visual_decision"]
    structural = page["structural_decision"]
    graph = page["semantic_graph"]
    ti = page["text_integration"]
    handoff = page["generation_handoff"]
    focus = structural["semantic_focus"]
    freedom = structural["representation_freedom"]
    required_text = "\n".join(f"- {text}" for text in _required_text_values(page))
    bindings = _binding_text(page)
    constraints = "\n".join(
        f"- Additional structural constraint: {item}"
        for item in handoff["structural_guidance"].get("additional_constraints", [])
    ) or "- Additional structural constraint: none."
    connectors = _connector_text(page)
    return f'''# Page {page["page_number"]}: {page["page_title"]}

[Content lock]
Preserve all required on-screen text, numbers, units, names, status words, and business relationships. Do not paraphrase unless the content lock explicitly allows it.

[Structural guidance]
Apply these page-level semantic relationships before placing any on-screen text. Do not render field names or instruction text. Do not infer a specific carrier, medium, or visual style unless the source constrains it.
- Selected visual intent type: {vd["visual_intent_type"]}
- Visual thesis: {vd["visual_thesis"]}
- Decision relationship: {graph["decision_relationship"]}
- Semantic focus: {focus["kind"]} / {focus["ref"]}
- Spatial grammar: {', '.join(structural["spatial_grammar"])}
- Semantic tags: {', '.join(structural["semantic_tags"])}
- Primary structure refs: {', '.join(structural["primary_refs"])}
- Secondary structure refs: {', '.join(structural["secondary_refs"]) or 'none'}
- Reading sequence: {' -> '.join(structural["reading_sequence"])}
{bindings}
- Locked text ids are internal binding references only; do not render the ids.
- Representation freedom: carrier={freedom["carrier"]}; medium={freedom["medium"]}; reason={freedom["reason"]}
{constraints}

[Connector map]
{connectors}

[Text placement]
- Body rendering mode: {ti["body_render_mode"]}
- Placement strategy: {ti["placement_strategy"]}
- {handoff["title_exclusion_instruction"]}

[Required on-screen body text]
{required_text}

[Style source]
{handoff["style_source_ref"]}
'''


def page_prompt(page: dict) -> str:
    handoff = page.get("generation_handoff") or {}
    if page.get("structural_decision") and handoff.get("structural_guidance"):
        return _structural_page_prompt(page)
    return _legacy_page_prompt(page)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("input")
    ap.add_argument("--page", type=int)
    ap.add_argument("--output", required=True)
    args = ap.parse_args()
    data = json.loads(Path(args.input).read_text(encoding="utf-8"))
    pages = data.get("pages", [data])
    if args.page is not None:
        pages = [p for p in pages if p.get("page_number") == args.page]
        if not pages:
            raise SystemExit(f"Page {args.page} not found")
    header = (
        "# Legacy structural prompt preview\n\n"
        "> Compatibility and visual-structure review artifact only. CyberPPT production uses "
        "artifact-spec-v2 over the audited Stage 02 handoff, deck visual spec, and style lock.\n"
    )
    output = header + "\n\n---\n\n".join(page_prompt(p) for p in pages)
    Path(args.output).write_text(output + "\n", encoding="utf-8")
    print(f"Created {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
