# Analysis And Expression Gates

## Objective

Make the following workflow a repository-level CyberPPT contract for every new project and for existing projects explicitly adopted into the contract:

1. Confirm the reporting-direction strategy, report structure, and page design.
2. Confirm the project-level business script.
3. Derive and confirm the drawing script from the confirmed business script.
4. Only then allow style selection, blueprint generation, ImageGen, or PPT generation.

The contract prevents a project from treating business content, drawing instructions, evidence, or visual decisions as interchangeable artifacts.

## Confirmed Workflow Contract

The repository must implement the following confirmed requirements as code and validation rules.

### Sequential Confirmation

The analysis workflow is strictly ordered:

1. reporting-direction strategy;
2. reporting-structure design;
3. page design;
4. business script;
5. drawing script;
6. visual style and blueprint generation.

No downstream artifact may be generated before its upstream gate is approved. The repository must not create page content, drawing scripts, prompts, blueprints, or images merely because an upstream draft exists.

Each gate must emit a structured pending-confirmation artifact containing the question, the current recommendation, and available choices. A Markdown file may explain the decision, but may not be the only confirmation mechanism. The CLI exposes the pending confirmation and records a selected option; the calling UI is responsible for rendering it as a choice control.

### Direction And Structure

The direction stage must first expand all applicable reporting strategies in sufficient detail, including audience, purpose, content focus, evidence, page tendency, advantage, and boundary. It then recommends one strategy and records which strengths of other strategies are retained.

The structure stage answers only what the report will cover. It must not specify page count, page splitting, single-page titles, or visual form. A report normally has four modules and must not exceed six modules. The structure title must summarize each module instead of concatenating its internal subtopics.

### Page Design

Page design is a separate gate after report structure. It decides page count, chapter-to-page allocation, page roles, and the page sequence.

Every complete deck plan must distinguish:

- cover;
- table of contents;
- chapter-transition pages;
- content pages;
- closing page.

Cover, table of contents, chapter-transition pages, and closing page do not carry business arguments, evidence, or decision content. The page design must not confuse these navigation pages with content pages.

### Internal Reporting Language

The default style is formal central-SOE/government internal reporting. The workflow rejects visible consulting-delivery language such as `MBB`, `SO WHAT`, `Caveat`, `Resolution`, `核心判断`, or conclusion-slogan titles unless a project explicitly overrides the style.

Page titles must use formal business expressions. The workflow distinguishes objective or feasibility-analysis terms such as work background, necessity, and feasibility from authority-overreaching deployment terms. It must not silently rewrite source-like formal headings into generic consulting phrases.

### Business Script

The business script is the first page-level artifact. It is a human-readable Markdown document that answers what every page expresses. It is a page-oriented decomposition and refinement of the source material, not a list of phrases or a drawing prompt.

For every content page, the business script must include:

- complete business content;
- a non-visible evidence chain with evidence ID and source location;
- a non-visible completeness check identifying information that cannot be deleted, merged away, or invented;
- an optional inline text line sketch for human review only.

Human-readable business scripts must use vertically readable Markdown sections rather than wide Markdown tables. The validation contract must ensure that non-visible metadata is explicitly marked and cannot become visible slide text.

### Drawing Script

The drawing script is generated only from the approved business script. It is a second Markdown document that answers what to draw and how to organize it.

For every page, the drawing script must include:

- page role and template title where applicable;
- concise on-screen phrases, numbers, classifications, process nodes, and request items;
- component relationships and visual hierarchy;
- high-information-density minimums;
- forbidden elements;
- non-visible evidence bindings and completeness checks inherited from the business script.

The drawing script is a concise semantic and visual translation, not a copy of long business paragraphs. It cannot add, remove, or reinterpret source-backed facts. It must not contain coordinates, fixed bounding boxes, colors, fonts, icons, or final visual composition; those belong to the later visual-blueprint stage.

### Evidence And Density

Evidence IDs, source positions, completeness checks, and high-density requirements are first-class gate data. They must survive all transitions from analysis to business script to drawing script to generation prompt.

The generation path must reject a page when a required evidence binding, source location, completeness check, or high-density unit is absent. It must also reject a drawing script that conflicts with its approved business script.

## Artifact Model

The analysis stage owns two UTF-8 Markdown artifacts.

### Business Script

The business script answers: what each page must express.

For every content page it contains:

- complete business language derived from the source material;
- non-visible evidence bindings with evidence IDs and source locations;
- a completeness check identifying facts, numbers, classifications, boundaries, and request items that must not be removed or invented;
- an optional line sketch for human review only.

The business script is the factual and semantic truth. It contains no final coordinates, colors, fonts, or visual style lock.

### Drawing Script

The drawing script answers: how the confirmed business content should be represented.

For every page it contains:

- page role and template title where applicable;
- concise visible phrases, numeric groups, classifications, process nodes, and request items;
- component relationships, visual hierarchy, high-information-density minimums, and forbidden elements;
- non-visible evidence bindings and completeness checks copied from the confirmed business script.

The drawing script is derived from an approved business script. It may not add, remove, or rewrite facts, numbers, boundaries, or decision items. It must not contain coordinates, final dimensions, colors, fonts, icons, or final visual composition.

## Gates

### Gates 0A--0C: Analysis Planning Approval

The repository records and validates three project-level planning artifacts before page-level scripting:

- direction strategy approval, including the expanded alternatives, recommendation, and retained strengths;
- report-structure approval, including four to six summarized modules and no page-level design fields;
- page-design approval, including the page sequence and all required page roles.

Each planning artifact has the same lifecycle as later scripts: staged, validated, pending confirmation, and approved. The next planning stage and the business-script stage are unavailable until the preceding approval is current.

### Gate 1: Business Script Approval

The business script is staged, validated, saved as final, and explicitly approved. Validation requires all content pages to have business text, evidence bindings, source locations, and completeness checks.

### Gate 2: Drawing Script Approval

The drawing script may only be staged after Gate 1 is ready. It records the SHA-256 of its source business script. Validation requires every page to have a role, concise visual content units, representation instructions, density requirements, forbidden elements, evidence bindings, and completeness checks. Validation rejects coordinate or fixed-layout fields.

### Generation Gate

Stage 2 and later generation commands must reject execution unless both gates are approved and the drawing script still references the hash of the currently approved business script.

## Repository Interfaces

Add a dedicated `analysis_expression_gate` command module rather than extending the per-slide `script_gate` module. The existing module remains responsible for per-slide final generation scripts and prompts.

Provide CLI commands:

- `stage-reporting-direction`
- `approve-reporting-direction`
- `stage-report-structure`
- `approve-report-structure`
- `stage-page-design`
- `approve-page-design`
- `stage-business-script`
- `approve-business-script`
- `stage-drawing-script`
- `approve-drawing-script`
- `analysis-expression-status`
- `adopt-analysis-expression-contract`

All staging and approval commands operate on project-level Markdown artifacts. The status command reports every gate state, dependency hash state, validation failures, pending confirmation choices, and the exact next command. The adoption command registers an existing project without overwriting its artifacts; it creates required directories and ledger entries, then reports missing work.

## Project Scaffolding

New projects receive analysis-expression directories, manifest keys, and an empty ledger contract. Their README flow states the two gates and the generation dependency.

Existing projects remain unchanged until `adopt-analysis-expression-contract` is run. Once adopted, they are subject to the same validation and generation gate as new projects.

## Validation And Tests

Unit tests cover:

- scaffolded directories and manifest keys;
- staged confirmation contracts with question, recommendation, options, selection, and audit record;
- direction validation requiring detailed alternatives before a recommendation and retained strengths for non-selected alternatives;
- report-structure validation requiring four to six summarized modules and rejecting page counts, page titles, and visual-form fields;
- page-design validation requiring cover, table of contents, chapter transitions, content pages, and closing page, while rejecting business arguments and evidence on navigation pages;
- planning-stage ordering: no page design before structure approval and no business script before page-design approval;
- default internal-reporting language validation rejecting consulting-delivery terms and conclusion-slogan titles, while permitting formal objective and feasibility-report terms;
- business-script validation requiring vertical page sections and explicit non-visible metadata markers;
- business-script validation failures for missing evidence, source location, or completeness checks;
- drawing-script rejection before business approval;
- drawing-script rejection when its source hash is stale;
- drawing-script rejection when it changes a required fact, number, classification, boundary, or request item from the approved business script;
- drawing-script rejection when a required high-density unit or inherited evidence/completeness item is omitted;
- drawing-script rejection for coordinates or fixed-layout fields;
- generation rejection before either approval;
- generation rejection when an evidence binding, source location, completeness check, or high-density unit is missing at any handoff;
- adoption of an existing project without overwriting existing files.

An end-to-end test stages and approves all five Markdown artifacts, verifies their dependency linkage and evidence propagation, and confirms that the existing generation entrypoint accepts the project only after every gate passes.

## Compatibility

Existing `script_gate` APIs and existing project artifacts remain compatible. The new analysis-expression contract is additive for unadopted projects and mandatory for newly scaffolded or explicitly adopted projects.
