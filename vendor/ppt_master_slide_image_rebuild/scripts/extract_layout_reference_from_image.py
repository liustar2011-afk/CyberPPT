#!/usr/bin/env python3
"""
PPT Master - Layout Reference Image Intake

Create a draft layout_reference.json and an extraction prompt from a reference
slide image. This script performs deterministic image intake only; semantic
page role, zones, and chain details must be completed by the main agent.

Usage:
    python3 scripts/extract_layout_reference_from_image.py <image> --project <project_path>

Examples:
    python3 scripts/extract_layout_reference_from_image.py reference.png --project projects/demo
    python3 scripts/extract_layout_reference_from_image.py reference.png --output projects/demo/layout_reference.draft.json --trusted-text

Dependencies:
    Pillow
"""

from __future__ import annotations

import argparse
import json
import shutil
from pathlib import Path
from typing import Any

try:
    from PIL import Image
except ImportError as exc:  # pragma: no cover - environment setup
    raise SystemExit("Pillow is required. Install project requirements first.") from exc

try:
    from layout_reference_rebuild2_lib import (
        WORKFLOW_ID,
        apply_measured_geometry_to_layout,
        classify_layout_page_type,
        detect_structure_signals,
        measure_layout_geometry_from_image,
        seed_structure_contract,
        write_layout_measurement_artifacts,
    )
except ImportError:  # pragma: no cover
    from scripts.layout_reference_rebuild2_lib import (  # type: ignore
        WORKFLOW_ID,
        apply_measured_geometry_to_layout,
        classify_layout_page_type,
        detect_structure_signals,
        measure_layout_geometry_from_image,
        seed_structure_contract,
        write_layout_measurement_artifacts,
    )


def _aspect_label(width: int, height: int) -> str:
    ratio = width / height if height else 0
    if abs(ratio - 16 / 9) < 0.08:
        return "16:9"
    if abs(ratio - 4 / 3) < 0.08:
        return "4:3"
    return f"{ratio:.3f}:1"


def _canvas_from_image(width: int, height: int) -> dict[str, Any]:
    aspect = _aspect_label(width, height)
    if aspect == "16:9":
        return {
            "aspect": "16:9",
            "width_px": 1280,
            "height_px": 720,
            "safe_margin_px": 48,
            "title_height_px": 72,
            "footer_height_px": 42,
        }
    return {
        "aspect": aspect,
        "width_px": width,
        "height_px": height,
        "safe_margin_px": round(min(width, height) * 0.06),
    }


def _bbox_ratio(bbox: list[int], width: int, height: int) -> list[float]:
    x, y, w, h = bbox
    return [
        round(x / width, 4) if width else 0.0,
        round(y / height, 4) if height else 0.0,
        round(w / width, 4) if width else 0.0,
        round(h / height, 4) if height else 0.0,
    ]


def _layout_intelligence_defaults(canvas: dict[str, Any]) -> dict[str, Any]:
    width = int(canvas.get("width_px") or 1280)
    height = int(canvas.get("height_px") or 720)
    title_h = int(canvas.get("title_height_px") or round(height * 0.1))
    footer_h = int(canvas.get("footer_height_px") or round(height * 0.06))
    footer_y = max(0, height - footer_h)
    margin = int(canvas.get("safe_margin_px") or round(min(width, height) * 0.06))
    body_y = title_h
    body_h = max(0, footer_y - body_y)
    title_bbox = [margin, 0, max(0, width - margin * 2), title_h]
    body_bbox = [margin, body_y, max(0, width - margin * 2), body_h]
    footer_bbox = [0, footer_y, width, footer_h]
    return {
        "visual_layering": {
            "content_layer": ["title", "body_text", "labels", "metrics", "footer_text"],
            "structure_layer": ["panels", "cards", "arrows", "connectors", "tables", "simple_charts"],
            "semantic_icon_layer": ["functional_icons"],
            "decorative_layer": ["background_illustration", "glow_rings", "texture", "atmospheric_lines"],
            "noise_layer": ["non_semantic_light_effects", "decorative_repeated_marks"],
        },
        "decorative_noise": [
            {
                "id": "background_decorative_context",
                "bbox_px": [0, 0, width, height],
                "bbox_ratio": [0, 0, 1, 1],
                "type": "background_illustration",
                "layer": "decorative_layer",
                "treatment": "ignore_or_simplified_vector",
                "semantic_weight": "none",
                "reason": "Decorative/background context only; do not treat as content, icon, or connector.",
            }
        ],
        "layout_grammar": {
            "primary_axis": "to_be_completed_by_agent",
            "reading_order": ["title", "body", "footer"],
            "composition_type": "to_be_completed_by_agent",
            "alignment_system": "to_be_completed_by_agent",
            "repetition_pattern": "to_be_completed_by_agent",
            "page_type_hint": "custom",
        },
        "page_type_classifier": {
            "page_type_hint": "custom",
            "confidence": 0.25,
            "reason": "deterministic classifier not run for non-rebuild2 intake",
            "signals": {},
            "needs_review": ["Confirm page type by visual inspection before SVG rebuild."],
        },
        "visual_anchors": [
            {
                "id": "title_band",
                "type": "band",
                "bbox_px": title_bbox,
                "bbox_ratio": _bbox_ratio(title_bbox, width, height),
                "confidence": 0.35,
            },
            {
                "id": "body_area",
                "type": "band",
                "bbox_px": body_bbox,
                "bbox_ratio": _bbox_ratio(body_bbox, width, height),
                "confidence": 0.35,
            },
            {
                "id": "footer_band",
                "type": "band",
                "bbox_px": footer_bbox,
                "bbox_ratio": _bbox_ratio(footer_bbox, width, height),
                "confidence": 0.35,
            },
        ],
        "crop_candidates": [],
        "text_background_relation": [],
        "confidence": {
            "layout_type": 0.25,
            "main_chain": 0.2,
            "text_regions": 0.2,
            "crop_candidates": 0.2,
        },
        "needs_review": [
            "Complete layout_grammar from visual inspection.",
            "Map visible text regions before SVG rebuild.",
            "Declare crop candidates for complex decorative/background regions.",
        ],
    }


def build_draft(
    image_path: Path,
    *,
    trusted_text: bool = False,
    copied_path: str | None = None,
    rebuild2: bool = False,
    artifact_dir: Path | None = None,
    normalized_image_path: Path | None = None,
) -> dict[str, Any]:
    size_path = normalized_image_path if normalized_image_path is not None and normalized_image_path.is_file() else image_path
    with Image.open(image_path) as image:
        mode = image.mode
        if size_path == image_path:
            width, height = image.size
        else:
            with Image.open(size_path) as sized:
                width, height = sized.size
    canvas = _canvas_from_image(width, height)
    layout_intel = _layout_intelligence_defaults(canvas)
    detected = detect_structure_signals(image_path) if rebuild2 else {}
    if rebuild2 and "error" not in detected:
        classifier = detected.get("page_type_classifier")
        if not isinstance(classifier, dict):
            classifier = classify_layout_page_type(detected)
        layout_intel["page_type_classifier"] = classifier
        layout_intel["layout_grammar"]["page_type_hint"] = classifier.get("page_type_hint", "custom")
        try:
            from layout_family_lib import classify_detected_layout_family

            layout_intel["detected_layout_family"] = classify_detected_layout_family(
                layout_type="to_be_completed_by_agent",
                signals=detected,
            )
        except ImportError:  # pragma: no cover
            pass
    structure_contract = seed_structure_contract(detected) if rebuild2 and "error" not in detected else None
    draft: dict[str, Any] = {
        "version": "2.0" if rebuild2 else "1.0",
        "workflow": WORKFLOW_ID if rebuild2 else "",
        "source_reference": {
            "type": "image",
            "purpose": "layout_only",
            "content_trust": "trusted_for_final_text_by_user" if trusted_text else "untrusted_for_final_text",
            "copy_text_from_reference": trusted_text,
            "path": copied_path or str(image_path),
            "image_width_px": width,
            "image_height_px": height,
            "image_mode": mode,
            **(
                {"normalized_path": str(normalized_image_path)}
                if normalized_image_path is not None and normalized_image_path.is_file()
                else {}
            ),
        },
        "canvas": canvas,
        "page_role": "custom",
        "layout_type": "to_be_completed_by_agent",
        "main_message_slot": "title_area",
        **layout_intel,
        "visual_structure": {
            "title_area": {
                "position": "top",
                "role": "page_judgment",
                "height_ratio": 0.1,
            },
            "body_area": {
                "position": "middle",
                "role": "main_logic",
                "height_ratio": 0.82,
            },
            "footer_area": {
                "position": "bottom",
                "role": "page_number_or_source",
                "height_ratio": 0.08,
            },
        },
        "main_chain": {
            "chain_type": "to_be_completed_by_agent",
            "direction": "to_be_completed_by_agent",
            "nodes": [],
            "relationship_style": "to_be_completed_by_agent",
            "support_layer": "",
        },
        "zones": [],
        "style_reference": {
            "tone": "to_be_completed_by_agent",
            "primary_color": "",
            "accent_color": "",
            "background": "",
            "card_style": "",
            "line_style": "",
            "font_family": "Microsoft YaHei",
            "density": "",
            "decoration_level": "",
        },
        "icon_reconstruction": {
            "policy": "repo_library_first",
            "preferred_libraries": ["tabler-outline", "tabler-filled", "chunk-filled", "phosphor-duotone"],
            "fallback": "hand_vector_only_when_no_repository_match",
            "slot_model": "centered_square_with_optical_adjustment",
            "level_rules": {
                "intro": {"circle_r_px": 40, "icon_size_px": 55, "text_gap_px": 29, "min_clearance_px": 18},
                "card_section": {"circle_r_px": 22, "icon_size_px": 26, "text_gap_px": 18, "min_clearance_px": 14},
                "consensus": {"circle_r_px": 34, "icon_size_px": 45, "text_gap_px": 14, "min_clearance_px": 20},
                "action": {"circle_r_px": 32, "icon_size_px": 42, "text_gap_px": 41, "min_clearance_px": 18}
            },
            "alignment_rules": [
                "icon_cy = text_block_top + text_block_height / 2",
                "text_gap_px is the clearance from icon circle right edge to text left",
                "icon_cx = text_left - text_gap_px - circle_r_px",
                "same_level_icons_share_visual_weight",
                "icon_right_edge_to_text_left >= level.text_gap_px - circle_r_px",
                "icon_circle_to_border_or_divider >= level.min_clearance_px"
            ],
            "icons": [],
            "quality_rules": [
                "match_reference_semantics_before_matching_exact_shape",
                "use_repository_icons_before_hand_vectors",
                "fit_each_icon_inside_its_visual_slot",
                "preserve_aspect_ratio",
                "avoid_touching_text_dividers_or_card_borders",
                "keep_composite_badges_inside_parent_icon_slot",
            ],
        },
        "editability_policy": {
            "native_editable": ["title", "body_text", "cards", "arrows", "tables", "simple_charts"],
            "image_allowed": ["logo", "screenshot", "complex_icon", "decorative_pattern"],
            "never_flatten_full_slide": True,
            "reference_image_as_background": "only_for_temporary_alignment",
        },
        "render_notes": {
            "text_density": "to_be_completed_by_agent",
            "title_style": "short_judgment",
            "body_style": "formal_business_phrases",
            "avoid": ["pixel_copy", "ocr_dependency", "generic_card_stack", "rendering_instructions_on_slide"],
        },
    }
    if rebuild2 and structure_contract:
        draft["structure_contract"] = structure_contract
        draft["main_chain"]["connectors"] = []
        draft["render_notes"]["avoid"].append("isolated_rounded_card_grid")
        draft["render_notes"]["avoid"].append("footer_chevron_chain_without_principle_chips")
        measured = measure_layout_geometry_from_image(image_path)
        if measured.get("measured"):
            apply_measured_geometry_to_layout(draft, measured)
            if artifact_dir is not None:
                paths = write_layout_measurement_artifacts(image_path, artifact_dir, measured)
                draft["layout_measurement_artifacts"] = paths
            draft["layout_type"] = structure_contract.get("layout_type") or draft["layout_type"]
    return draft


def build_prompt(draft_path: Path, image_ref: str, trusted_text: bool) -> str:
    trust_rule = (
        "The user explicitly allowed reference-image text to be used as final content."
        if trusted_text
        else "Treat all visible reference-image text as untrusted unless the user explicitly authorizes it."
    )
    return f"""# Layout Reference Extraction Prompt

Use the reference image at `{image_ref}` and complete `{draft_path.name}` into `layout_reference.json`.

Rules:

- {trust_rule}
- Intake may pre-fill `zones`, `geometry_measurement`, and icon slots from CV (`measure_layout_geometry_from_image`). **Refine** those ratios if the image differs; do not replace measured geometry with generic 0.21×4 grids unless the image truly has equal columns.
- Select one primary `page_role`.
- Fill `layout_type`, `main_chain`, `style_reference`, and `render_notes`.
- Complete `layout_grammar` with page type, reading order, alignment system, repetition pattern, and main composition grammar.
- Review `page_type_classifier`; if its confidence is below 0.70, confirm or override `layout_grammar.page_type_hint` before SVG rebuild.
- Complete `visual_layering` and `decorative_noise`: separate content, structure, semantic icons, decorative elements, and noise before rebuilding icons/arrows.
- Mark wind turbines, power towers, solar-grid line art, glow rings, faint data streams, decorative dots, and non-semantic background lines as `decorative_noise` unless they carry content or flow meaning.
- Refine `visual_anchors`; keep both `bbox_px` and `bbox_ratio` for stable Executor positioning and future regression checks.
- Review `geometry_locks[]` seeded by intake measurement; confirm title rule, column frames, footer bar, and connector anchors before SVG rebuild. Add `data-geometry-lock-id` on matching SVG elements.
- Fill `crop_candidates` only for pure decorative backgrounds, footer line art, textures, and tightly bounded complex small icons. Do not list cards, arrows, connectors, center nodes, text regions, or main business diagrams as crop candidates.
- For each `crop_candidates[]` entry, set `editability_intent` (`editable`, `asset`, or `fallback`), `needs_review` when uncertain, and `precrop.enabled: false` until Phase 3 precrop tooling is enabled.
- Prefer `vector-hifi`: main structure fidelity comes from measured bbox/anchor coordinates and editable vector reconstruction, not from large raster underlays.
- Fill `text_background_relation` for every visible text region, especially text over decorative/complex backgrounds that needs underlay removal.
- Give every reusable visual region a stable `zone_id`.
- `x_ratio` / `y_ratio` / `w_ratio` / `h_ratio` must match visible bands in the reference (footer navy bar, chevron row, column gutters).
- Fill `icon_reconstruction.icons[]` for every visible functional icon. Record semantic intent, level, parent zone, visual slot ratios, text anchor, and optical adjustment notes. Use repository icons by default; hand-draw only when no repository icon can carry the semantic role, and use tight crops only when the user explicitly opts into icon crops.
- Keep `editability_policy.never_flatten_full_slide = true`.
- Do not invent unreadable text.

After completion, run:

```bash
python3 scripts/validate_layout_reference.py {draft_path}
python3 scripts/validate_layout_reference.py {draft_path} --allow-draft
```
"""


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Create a draft layout_reference.json and extraction prompt from an image.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("image", type=Path, help="Reference image path")
    parser.add_argument("--project", type=Path, help="Project directory; outputs default there")
    parser.add_argument("--output", type=Path, help="Output draft JSON path")
    parser.add_argument("--prompt-output", type=Path, help="Output prompt Markdown path")
    parser.add_argument("--copy-image", action="store_true", help="Copy image into <project>/images/reference_layout.<ext>")
    parser.add_argument("--trusted-text", action="store_true", help="Mark reference image text as user-approved final content")
    parser.add_argument(
        "--rebuild2",
        action="store_true",
        help="复刻流程2 intake: workflow 2.0, structure_contract seed, column heuristics",
    )
    parser.add_argument(
        "--normalized-image",
        type=Path,
        help="Optional normalized reference PNG; canvas dimensions are taken from this file when present",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    image_path = args.image
    if not image_path.exists():
        print(f"File not found: {image_path}")
        return 1

    copied_ref: str | None = None
    if args.copy_image:
        if args.project is None:
            print("--copy-image requires --project")
            return 1
        images_dir = args.project / "images"
        images_dir.mkdir(parents=True, exist_ok=True)
        copied = images_dir / f"reference_layout{image_path.suffix.lower()}"
        if image_path.resolve() != copied.resolve():
            shutil.copy2(image_path, copied)
        copied_ref = str(copied.relative_to(args.project))

    if args.output:
        output = args.output
    elif args.project:
        output = args.project / "layout_reference.draft.json"
    else:
        output = image_path.with_suffix(".layout_reference.draft.json")

    if args.prompt_output:
        prompt_output = args.prompt_output
    elif args.project:
        prompt_output = args.project / "layout_reference_extraction_prompt.md"
    else:
        prompt_output = image_path.with_suffix(".layout_reference_extraction_prompt.md")

    draft = build_draft(
        image_path,
        trusted_text=args.trusted_text,
        copied_path=copied_ref,
        rebuild2=args.rebuild2,
        artifact_dir=args.project,
        normalized_image_path=args.normalized_image.resolve() if args.normalized_image else None,
    )
    output.parent.mkdir(parents=True, exist_ok=True)
    prompt_output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(draft, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    prompt_output.write_text(build_prompt(output, copied_ref or str(image_path), args.trusted_text), encoding="utf-8")
    print(f"Wrote {output}")
    print(f"Wrote {prompt_output}")
    if copied_ref:
        print(f"Copied image to {args.project / copied_ref}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
