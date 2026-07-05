# Grid Contract Specification

Optional contract for icon grids, logo walls, N×N matrices, and sliced icon-sheet assets. Do not apply this contract to timelines, flow diagrams, uneven card layouts, or pages whose visual hierarchy is intentionally asymmetric.

## 1. Trigger

| Condition | Action |
|---|---|
| Project contains `grid_contract.json` or `asset_grid_contract.json` | Run `scripts/verify_grid_contract.py <project>` |
| No grid contract file exists | Skip grid checks |
| Page is a process, timeline, hub-and-spoke, or non-uniform card layout | Do not create a grid contract |

**Hard rule**: Grid checks are opt-in. The default strict runner does not enforce C×R grids globally.

---

## 2. Contract Shape

```json
{
  "workflow": "slide-image-rebuild",
  "version": "1.0",
  "pages": [
    {
      "page_id": "P01",
      "grids": [
        {
          "id": "icon_matrix",
          "rows": 3,
          "columns": 3,
          "bbox_px": [100, 80, 540, 540],
          "items": [
            {"id": "item_01", "cell": [0, 0], "bbox_px": [128, 108, 84, 84]}
          ]
        }
      ]
    }
  ]
}
```

| Field | Notes |
|---|---|
| `rows` / `columns` | Positive integers; `cell` uses zero-based `[row, column]` |
| `bbox_px` | Grid canvas `[x, y, w, h]` in the slide coordinate system |
| `items[].bbox_px` | True visible content box, not the whole image file box |
| `items[].cell` | Declared owner cell for the item |

---

## 3. Checks

| Check | Severity | Default |
|---|---|---|
| Grid bbox aspect matches `columns:rows` | Error | tolerance `3%` |
| `N×N` grid bbox is square | Error | tolerance `3%` |
| Item center matches cell center | Error | tolerance `4px` |
| Item padding inside cell | Error below `10%`; warning below `15%` | ratio of smallest cell dimension |
| Item fill safe zone | Warning | preferred `55%-70%` |

**Default — safe zone (may override)**: Use `55%-70%` as a visual target, not a hard failure. Filled icons, line icons, CJK glyph icons, and logos have different optical weights.

---

## 4. Policy Overrides

Each grid may override thresholds:

```json
{
  "policy": {
    "aspect_tolerance_ratio": 0.03,
    "center_tolerance_px": 4,
    "hard_min_padding_ratio": 0.10,
    "warning_min_padding_ratio": 0.15,
    "preferred_fill_ratio_min": 0.55,
    "preferred_fill_ratio_max": 0.70
  }
}
```

**Validation**: Overrides change only the declared grid. Do not use overrides to hide a clipped icon; fix the crop or bbox first.

---

## 5. Chroma-Key Boundary

**Reference — not a constraint**: When an icon sheet must be cut into transparent PNGs, detect the real content grid first, then compute row and column centers before deriving cell edges. Avoid slicing from `(0,0)` with `image_width / columns` unless the source image is mechanically generated and proven aligned.

**Default — chroma-key sampling (may override)**: Prefer per-cell edge color sampling over a single global threshold. This reduces shallow background blocks and semi-transparent edge contamination.

Use `scripts/grid_chroma_cut.py` when a true icon contact sheet needs to become
transparent per-cell assets. General reference crops should use
`scripts/harvest_reference_assets.py` instead.
