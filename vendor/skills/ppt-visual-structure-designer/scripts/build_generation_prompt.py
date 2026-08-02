#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path


def page_prompt(page: dict) -> str:
    vd = page["visual_decision"]
    sg = page["semantic_graph"]
    ip = page["image_plan"]
    ti = page["text_integration"]
    handoff = page["generation_handoff"]
    reading = " -> ".join(vd["reading_path"])
    avoid = "; ".join(page.get("avoid", []) + handoff.get("negative_constraints", []))
    required_text = "\n".join(f"- {text}" for text in handoff["required_text"])
    connectors = "\n".join(
        f"- {c['from']} -> {c['to']}: {c['type']} / {c['direction']} / {c['label']}"
        for c in page.get("connectors", [])
    ) or "- No business arrows; use spatial adjacency only."
    return f'''# Page {page["page_number"]}: {page["page_title"]}

[Content lock]
Preserve all required on-screen text, numbers, units, names, status words, and business relationships. Do not paraphrase unless the content lock explicitly allows it.

[Mandatory composition guidance] Apply this layout guidance before placing any on-screen text. Do not render its field names or instruction text.
[Prompt context] Page-specific visual intent (composition guidance only; do not render field names or instruction text)
- Selected visual intent type: {vd["visual_intent_type"]}
- Visual thesis: {vd["visual_thesis"]}
- Decision relationship: {sg["decision_relationship"]}
- Dominant visual carrier: {vd["dominant_visual_carrier"]}
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
    output = "\n\n---\n\n".join(page_prompt(p) for p in pages)
    Path(args.output).write_text(output + "\n", encoding="utf-8")
    print(f"Created {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
