# PPT Master Arrow Templates

Reusable arrow assets for PPT Master. Use this library when a slide needs directional structure rather than a generic icon.

## Selection Rule

| Family | Use for | SVG form | PPTX editability |
|---|---|---|---|
| `connector_*` | Thin relationship lines, request/response flows, dependency links | `<line>` / simple orthogonal `<path>` with supported marker or inline arrowhead | Native line/path or freeform; arrow heads survive export when marker or inline head is classifiable |
| `block_*` | Main process chains, phase arrows, strategy paths, large visual arrows | Closed `<polygon>` / `<path>` | Native freeform / polygon shapes; fill and stroke remain editable |
| `split_*` | One-to-many or many-to-one logic | Closed block shapes plus connector markers | Mixed native shapes |
| `cycle_*` | Circular progress, feedback loops, lifecycle arrows | Simple arc paths plus manual arrow-head polygons | Native freeform shapes; label placement stays editable |
| `*_bus_*` | Dotted support buses, tap arrows, orthogonal dependencies | Dashed `<line>` / `<path>` with supported marker | Native line/path connectors; suited to architecture pages |
| `*_lift_*` / `solid_up_*` | Foundation-to-capability upward emphasis | Closed filled `<path>` plus shallow gradient | Native freeform shapes; matches政企 architecture lift arrows |
| `side_rail_*` | End-to-end coverage brackets across stacked rows | Orthogonal `<path>` with supported marker | Native path connectors |
| `pptpack*_gradient_*` | Local PPT-style gradient structure arrows for process, bridge, split/merge, turn, trend, vertical flow, and chevron relations | Repo-local SVG packs wrapped into the standard 1280x720 template canvas | Native paths/freeforms when exported through the SVG pipeline |

## Selection Priority

1. For connector-heavy pages, first query `connector_index.json`; it narrows the full library to relationship arrows grouped by node links, orthogonal routes, hub exchange, feedback loops, buses, and dependency lanes.
2. For a page's primary visual arrow, first check structural templates such as `pptpack*_gradient_*`, `pptpack4_connector_route_*`, `dashed_bus_up_taps`, `bottom_lift_arrow_row`, `multi_level_support_lift`, `converge_to_platform_arrow`, and `distribute_from_platform_arrow`.
3. Use connector-route templates for thin node-to-node relationships and block/gradient templates for page-level main chains.
4. Do not add icon-library-derived arrows to this directory. Arrow templates must be true relationship/action assets or structural PPT arrows, not generic icons enlarged into slide visuals.

## Hard Rules

1. Connector arrows MUST use either supported marker heads or inline arrowheads.
   - Marker heads MUST be triangle, diamond, or oval shapes defined in `<defs>` with `orient="auto"`.
   - Triangle marker heads MUST be drawn in canonical right-facing form, e.g. `M0,0 L10,5 L0,10 Z` with `refX="9"` and `refY="5"`. Do not pre-draw an "up" marker; `orient="auto"` rotates it to the line direction.
   - Inline arrowheads MUST be simple closed triangle geometry (`<polygon>`/`<polyline>` or closed `<path>`) placed with the connector path, as used by `pptpack4_connector_route_*`.
2. Block arrows MUST be closed geometry. Do not simulate a wide process arrow with `marker-end`.
3. Do not use `mask`, `<style>`, `class`, external CSS, `<symbol>`, or complex marker drawings.
4. Keep gradients shallow and shadows light. 政企汇报页优先用浅蓝/灰蓝/深蓝，避免强 3D 和高饱和箭头。
5. Every arrow template should include a short comment naming its use case, so Strategist can select it from the index without visual guessing.
6. Architecture-layer pages should check `dashed_bus_up_taps`, `bottom_lift_arrow_row`, and `multi_level_support_lift` before drawing arrows from scratch.

## Source Intake

Third-party PPTX/SVG arrow resources from `/Volumes/DOC/PPT箭头库下载清单/` are acquisition candidates, not runtime dependencies. Before adding any downloaded arrow:

1. Confirm license on the individual asset page.
2. Prefer PPTX shapes that can be ungrouped and recolored.
3. Convert accepted assets into repo-native SVG under this folder.
4. Run `python3 skills/ppt-master/scripts/verify_arrow_templates.py`.

## Local PPT Gradient Arrow Packs

`pptpack_gradient_*.svg`, `pptpack2_gradient_*.svg`, `pptpack3_gradient_*.svg`,
`pptpack4_*.svg`, `pptpack5_*.svg`, `pptpack6_*.svg`, and `pptpack7_*.svg`
files are generated from repo-local custom PPT arrow packs kept under
`assets/ppt_arrow_pack*_sources/`. These packs are not FontAwesome and are not
icon libraries; they contain PPT-style structure arrows with gradient fills,
flat editable bodies, process chains, long paths, split/merge, bridge, vertical
flow, trends, connector routes, hub-spoke exchanges, cycle loops, data-flow
lanes, and turn relations.

Refresh the generated templates and index with:

```bash
python3 skills/ppt-master/scripts/import_ppt_arrow_pack_assets.py
python3 skills/ppt-master/scripts/verify_arrow_templates.py
```

The import script also regenerates `connector_index.json`, a connector-focused
secondary index derived from `arrows_index.json`. Do not hand-edit it unless the
category rules in the import script are updated at the same time.

**Hard rule**: do not hand-edit `pptpack_gradient_*.svg` arrow paths. Change
`ppt_arrow_pack*_sources.json` or the generator instead, then regenerate.

## Raster References

`assets/reference_soft_bridge_lift.png` is a user-provided visual reference for the soft blue bridge/lift arrow seen in formal architecture slides. Use it as a high-fidelity visual reference when a native SVG approximation is not enough.
