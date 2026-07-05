# Reference Asset Harvesting

`harvest_reference_assets.py` materializes approved local image assets from a
slide reference image. It is a controlled bridge between visual fidelity and
editability: only declared non-structural crop candidates are harvested.

## Trigger

Run during Phase A/plan generation when `layout_reference.json` has
`crop_candidates[]` entries with `editability_intent: "asset"`:

```bash
scripts/repo_python.sh scripts/harvest_reference_assets.py <project>
```

`layout_reference_to_svg_plan.py` also attempts a conservative harvest before
writing `svg_build_plan.json/md`, then copies the result into
`harvested_asset_plan`.

## Output

```text
images/harvested_assets/P01/<candidate_id>.png
image_asset_manifest.json
```

These files are intentionally stored under `images/harvested_assets/`, not the
transparent-asset directories. Ordinary photos, logos, and decorative crops may
be opaque; transparent PNG gates remain reserved for explicitly transparent
assets.

## Allowed

| Candidate | Use |
|---|---|
| `editability_intent: "asset"` + decorative/photo/logo/small-icon role | Harvest by default |
| `editability_intent: "fallback"` | Harvest only with `--include-fallback` |
| `needs_review: true` | Do not harvest automatically |
| Tight functional icon crop explicitly requested for visual fidelity | Allowed only as `complex_small_icon` / `small_complex_icon`; label text and surrounding structure stay editable |

## Forbidden

Do not harvest candidates that describe text, cards, connectors, arrows,
center nodes, process nodes, or main business diagrams. These must be rebuilt as
editable SVG/PPT objects.

Icon crop priority does not relax this boundary. A visual relationship arrow,
dependency wedge, dashed callback, card border, or foundation/base band is still
structure, not an icon asset. Preserve those as editable vectors with semantic
markers such as `data-chain-connector`.

The script reuses `crop_policy_lib.validate_precrop_eligible`, so
`structure_contract.forbidden_substitutes` and required primitive conflicts are
respected.

## Executor Use

When `svg_build_plan.md` contains `## Harvested Image Assets`, use those local
crops only for the declared role. Prefer repository SVG/icon libraries and
hand-drawn semantic vectors for functional icons. Never use harvested crops as
substitutes for text, card borders, connectors, or main structure.
