# ChatGPT Precise Rebuild Icon Contract

## Purpose

For ChatGPT precise slide-image rebuilds, functional icons are release-critical objects, not decorative details. Each functional icon must be declared, rebuilt, marked, and verified independently.

## Three-Tier Implementation Priority

| Priority | Strategy | When to use |
|---|---|---|
| **P1** | Repository SVG with matching style | Default. Use the shared icon library first so icons stay editable and style-consistent. Set `implementation: asset_svg`. |
| **P2** | Tight icon-slot crop | Use only when the user explicitly prioritizes reference-icon visual fidelity over icon editability, or explicitly requests icon crops. Set `implementation: tight_icon_crop` and `fallback_allowed: true`. |
| **P3** | Hand-drawn semantic vector | Fallback only when no adequate repository icon exists or editability of the icon geometry itself is explicitly required; unified stroke width, bbox padding, and visual weight. |

For slide screenshots and ChatGPT-generated reference pages, icon visual style
often carries the look of the page. The default still remains **repository-icon
first** because it preserves editability and avoids mixed raster/vector outputs.
Use tight local crops only after the user explicitly chooses visual fidelity for
icons over icon editability. Do not spend time approximating a bespoke icon with
hand-drawn strokes when a repository icon can carry the same semantic role.

Pick one stylistic repository library per page/deck (`tabler-outline`,
`tabler-filled`, `chunk-filled`, or `phosphor-duotone`) and stay within it unless
the user explicitly asks for a different treatment.

Style consistency (P1/P2): icons in the same page should share stroke width, bbox fill ratio, and padding inside the declared slot.

`verify_icon_contract.py --style-check --write-report` validates:

| Check | Policy field | Default |
|---|---|---|
| Max stroke width | `max_stroke_width_px` | `2.5` |
| Cross-icon stroke spread | `max_stroke_width_spread_px` | `0.75` |
| Per-icon expected stroke | icon `stroke_width_px` + `stroke_tolerance_px` | tolerance `0.6` |
| Slot fill ratio (with `--render`) | `min_bbox_fill_ratio` / `max_bbox_fill_ratio` | `0.12` / `0.85` |
| Minimum padding (with `--render`) | `min_padding_ratio` | `0.08` |

Set `policy.style_check: false` to disable style checks for a project. `chatgpt_precise_rebuild` auto-enables `--style-check`.

## Project Artifact

Create this file when `execution_profile` is `chatgpt_precise_rebuild` and the reference page contains functional icons:

```text
<project_path>/icon_manifest.json
```

Minimum shape:

```json
{
  "workflow": "slide-image-rebuild",
  "version": "1.0",
  "profile": "chatgpt_precise_rebuild_icon_contract",
  "policy": {
    "require_bbox": true,
    "bbox_position_tolerance_px": 3,
    "bbox_size_tolerance_px": 4,
    "min_visible_pixel_ratio": 0.015,
    "style_check": true,
    "max_stroke_width_px": 2.5,
    "min_bbox_fill_ratio": 0.12,
    "max_bbox_fill_ratio": 0.85,
    "min_padding_ratio": 0.08,
    "max_stroke_width_spread_px": 0.75
  },
  "pages": [
    {
      "page_id": "01",
      "svg": "svg_output/01.svg",
      "icons": [
        {
          "id": "core_service_target",
          "bbox_px": [445, 178, 28, 28],
          "semantic": "target or precision service",
          "required": true,
          "implementation": "asset_svg",
          "fallback_allowed": false,
          "implementation_priority": 1
        }
      ]
    }
  ]
}
```

## SVG Markers

Every required icon must carry a matching `data-icon-id` in the rebuilt SVG:

```xml
<g data-icon-id="core_service_target" data-icon-role="semantic_icon" data-icon-bbox="445 178 28 28">
  <path d="..."/>
</g>
```

Use `data-icon-bbox` for complex path icons so the verifier does not need to infer geometry from path data.

For crop-first icons, mark the image explicitly:

```xml
<g data-icon-id="core_service_target" data-icon-role="semantic_icon" data-icon-bbox="445 178 28 28">
  <image
    id="core_service_target_crop"
    data-crop-id="core_service_target_crop"
    data-crop-role="complex_small_icon"
    data-crop-purpose="tight_icon_slot_crop"
    href="../images/icon_crops/core_service_target.png"
    x="445" y="178" width="28" height="28" />
</g>
```

The crop must contain only the icon. If the crop includes adjacent label text,
card borders, connector lines, or another visual object, tighten the source
crop box and regenerate. Prefer explicit source bbox overrides for crowded
bands, especially footer/base capability rows.

## Requirements

| Rule | Requirement |
|---|---|
| Unique id | `icon_manifest.json` id must match SVG `data-icon-id` exactly |
| Reference bbox | `bbox_px` records the reference icon location and size in 1280x720 canvas coordinates |
| SVG bbox | Complex icons should include `data-icon-bbox="x y w h"` |
| Fallback | Do not silently substitute missing icons with default placeholders |
| Implementation | Prefer repository SVG assets by default; use tight crops only by explicit user choice; use hand vectors only as a last resort |
| Emoji | Do not use emoji as functional icons in precise rebuild output |
| Required icons | Missing required icons are release blockers |
| Crop hygiene | Cropped icons must be text-free and declared as `complex_small_icon` / `small_complex_icon` |
| Relationship separation | Never classify arrows, dependency wedges, connector bundles, card borders, or main diagrams as icons |

## Verification

Run before export on the precise rebuild path:

```bash
python3 scripts/verify_icon_contract.py <project_path> --style-check --write-report --enforce
```

Use rendered fill/padding metrics when Cairo/Pillow preview rendering is available:

```bash
python3 scripts/verify_icon_contract.py <project_path> --render --style-check --write-report --enforce
```

The verifier checks required icon presence, bbox drift, stroke/style consistency, unmanifested SVG icons, and optional rendered pixel visibility. Style failures are aggregated into `repair_tasks.json` via `icon_contract_report.json`.
