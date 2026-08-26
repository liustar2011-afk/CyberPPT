# CyberPPT Scene Graph First Design

## Status

Approved for design by the user on 2026-07-05.

## Objective

CyberPPT must make `page_scene_graph.json` the mandatory intermediate layer for all future script-image-generation-to-PPT workflows. Every page must pass `page_scene_graph_gate` before editable PPTX export. The goal is to stop point fixes caused by disconnected OCR, visual registry, source capture, script truth, and layout rules.

The workflow applies to all future CyberPPT script-generated slide rebuilds, not only the current P6 page or the current project.

## Non-Goals

- Do not make every frame, icon, or decorative object editable in the first phase.
- Do not treat OCR text as final content truth.
- Do not keep a compatibility path that silently exports without a scene graph.
- Do not implement page-specific layout fixes as the primary solution.

## Architecture Principle

All script-generated PPT rebuilds must follow this chain:

```text
script / content lock / evidence chain
  + full/background image pair
  + visual_element_registry
  + OCR locator evidence
    -> page_scene_graph.json
    -> page_scene_graph_gate.json
    -> page_layout_plan.json
    -> editable PPTX export
    -> render QA
    -> source_capture.json
```

`page_scene_graph.json` is the only page-level contract consumed by layout and QA. Downstream layout code must not independently infer production geometry from OCR, registry, or ad hoc semantic plans.

## Page Scene Graph Contract

Each page scene graph has these top-level fields:

```json
{
  "schema": "cyberppt.page_scene_graph.v1",
  "page": 6,
  "coordinate_context": {},
  "truth_sources": {},
  "visual_nodes": [],
  "text_nodes": [],
  "relations": [],
  "layout_intents": [],
  "gates": {}
}
```

### coordinate_context

Records all coordinate sources and transformations:

- full image size
- background image size
- visual registry declared canvas
- visual registry bbox extent
- semantic/source bbox extent
- normalized canvas, fixed at `1280x720`
- transforms from each input source into normalized coordinates
- coordinate warnings and blocking drift issues

All bbox values used by graph, layout, and gate stages must be normalized to `1280x720`.

### truth_sources

Records available truth sources and their authority:

- script and content lock can provide final text truth
- evidence chain can validate source grounding
- explicit manual overrides can provide final text truth when declared
- OCR can provide locator evidence only

OCR-derived text must not overwrite script/content-lock text.

### visual_nodes

Represents all non-text visual elements needed for binding, layout, and QA:

- containers
- cards
- text zones
- icons
- arrows and connectors
- dividers and separators
- legends and markers
- decorative or low-priority elements when relevant to avoidance

Each visual node must include:

- `node_id`
- `node_type`
- `semantic_role`
- normalized `bbox`
- `source`
- `confidence`
- optional `component_id`

### text_nodes

Represents editable text objects. Each text node must include:

- `node_id`
- `text`
- `truth_source`
- `semantic_role`
- `binding`
- preferred or relative placement fields when available

The required binding is a semantic context, not necessarily a visual container.

Allowed binding types:

- `container_text`: text belongs inside a card, group box, table cell, panel, or other container.
- `edge_label`: text labels an arrow or connector.
- `anchor_label`: text labels an icon, node, marker, badge, or point.
- `free_annotation`: free annotation text; it still needs a page region, nearest visual anchor, and avoidance rules.
- `title_chrome`: title, subtitle, header, footer, page number, and template chrome.
- `legend_label`: legend text, swatch label, axis label, or scale label.

The gate must block only truly unbound text: text with no container, edge, anchor, legend, template region, page region, or declared annotation context.

### relations

Relations are separated into three layers.

Structural relations:

- `contains`
- `part_of`
- `flow_order`
- `paired_with`

Spatial relations:

- `left_of`
- `right_of`
- `above`
- `below`
- `overlaps`

Spatial relations must include distance, overlap length or area, direction confidence, and the coordinate context used to compute them.

Layout relations:

- `text_after_icon`
- `label_on_arrow`
- `avoid_reserved_zone`
- `honor_text_zone`
- `fit_inside_safe_area`
- `stack_within_container`
- `align_with_sibling_text`

### layout_intents

Layout intents are derived from bindings and relations. They are the only layout-facing instructions consumed by the layout solver. Examples:

- place text after a left icon
- honor a registry text zone
- stack a list vertically inside a safe area
- place an arrow label above the edge
- shrink font or wrap by semantic phrase boundaries
- align sibling text nodes within the same component

## Safe Area Rules

For `container_text`, safe area is derived in this order:

1. Use registry `text_zone` if present.
2. Otherwise subtract reserved child zones such as icons, arrows, badges, and separators from the container bbox.
3. Apply container padding.

For `edge_label`, derive a label corridor along the edge direction, avoid endpoints, and avoid source/target nodes.

For `anchor_label`, generate candidate regions around the anchor, choose a placement based on available space, and record the chosen placement.

For `free_annotation`, require a predefined page region and a weak relation to the nearest visual element.

For `title_chrome`, use template-defined regions and do not infer from body containers.

## Mandatory Gates

`page_scene_graph_gate.json` must block PPTX export if any blocking issue exists.

Truth Gate:

- all text nodes must have an authoritative truth source
- text from OCR must not become final text
- graph text must match script/content-lock text unless an explicit manual override exists

Geometry Gate:

- all production bbox values must be normalized
- coordinate drift must be explained by a recorded transform
- mixed coordinate spaces without transform are blocking

Binding Gate:

- every text node must have a valid binding context
- registry text-bearing containers or text zones must either have bound text or be explicitly marked as decorative/empty

Layout Intent Gate:

- every binding must produce a safe bbox
- safe bbox must avoid reserved visual nodes
- final text bbox must remain inside safe bbox

Render Gate:

- rendered output must not have missing text
- rendered output must not have text outside slide/body bounds
- rendered output must not have text overlapping reserved icons, arrows, or separators
- rendered output must not have invisible or clipped text

Capture Gate:

- source_capture must record scene graph, gates, layout plan, render QA, and source references
- source_capture must preserve relationships, not only raw text and bbox lists

## Gate Issue Shape

Every issue must include:

- `severity`
- `code`
- `node_id`
- `source`
- `evidence`
- `recommended_action`
- `blocking`

Required blocking issue codes include:

- `missing_truth_binding`
- `coordinate_space_unresolved`
- `registry_container_without_text`
- `script_truth_mismatch`
- `safe_bbox_conflict`
- `render_text_missing`
- `render_overlap`

## Module Boundaries

Implement scene graph functionality in a new package instead of extending `script_text_overlay.py`.

### scene_graph/schema.py

Defines scene graph, visual node, text node, relation, binding, layout intent, and gate issue data structures. Owns schema versioning and JSON serialization.

### scene_graph/coordinate.py

Owns coordinate normalization and transform recording. It consumes image sizes, registry canvas, bbox extents, and declared semantic sizes. It outputs normalized bbox values, transforms, and coordinate warnings/issues.

### scene_graph/builder.py

Builds `page_scene_graph.json` from script/content lock, visual registry, source capture, and OCR locator evidence. It owns text truth binding, visual node construction, structural relations, spatial relations, and layout intent derivation.

### scene_graph/gate.py

Runs all blocking and warning gates. It must be callable before layout and after render QA.

### scene_graph/layout.py

Generates `page_layout_plan.json` from the scene graph. It must consume bindings and layout intents only, not raw OCR or raw registry files.

### scene_graph/render_qa.py

Runs rendered-output checks and writes results back into scene graph gates and source capture.

## Main Workflow Changes

The script-image-generation-to-PPT entrypoint must:

1. Build `page_scene_graph.json` for every page.
2. Run `page_scene_graph_gate.json`.
3. Stop before PPTX export if the gate has blocking issues.
4. Generate layout from scene graph only.
5. Export editable text over the selected background image.
6. Render and run render QA.
7. Write source_capture from scene graph, layout plan, and render QA.

There must be no silent fallback to OCR-only geometry for production export.

## Phase 1 Scope

Phase 1 focuses on text fidelity, binding, coordinate normalization, safe area inference, and blocking gates.

Allowed in Phase 1:

- background can still carry frame, icon, and decorative visuals
- editable text must be real text boxes
- visual nodes for frames/icons/arrows must exist in the scene graph because they drive avoidance and QA

Deferred to Phase 2:

- converting all frames, icons, and arrows into editable PPT shapes
- advanced visual object segmentation
- visual style transfer beyond what is needed for layout and QA

## Testing Strategy

Unit tests:

- coordinate normalization
- transform selection when image size, registry canvas, and semantic extents disagree
- binding inference for container text, arrow labels, anchor labels, free annotations, and title chrome
- safe bbox derivation
- blocking gate issue generation

Golden/regression pages:

- high-density architecture page like P6
- arrow label without obvious container
- card with icon plus text
- bottom service bar
- free annotation near an element
- right-side vertical flow with icon-only visual containers

End-to-end tests:

- start from `page_image_pairs.json`
- produce `page_scene_graph.json`
- pass or intentionally fail `page_scene_graph_gate.json`
- produce PPTX only when gate passes
- render PPTX to PNG
- check render QA and source_capture completeness

## Acceptance Criteria

- All future script-image-generation-to-PPT exports require `page_scene_graph_gate` to pass.
- A page with unbound text is blocked unless the text is bound as an edge label, anchor label, free annotation, title chrome, or legend label.
- A page with coordinate drift is blocked unless the drift is explained by recorded transforms.
- A page where registry text-bearing containers lack bound text is blocked unless marked decorative/empty.
- A page where final editable text differs from script/content-lock truth is blocked unless manually overridden.
- Source capture includes scene graph, relations, layout proof, gate results, and render QA.
- Existing P6 failure classes are represented as tests, not page-specific fixes.
