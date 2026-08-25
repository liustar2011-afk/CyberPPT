# CyberPPT-Stage02 Boundary

## Product boundary

CyberPPT-Stage02 consumes an approved PPT semantic script and produces visual assets and PPTX deliverables. Source-document analysis, outline planning and PPT script authoring belong to CyberPPT-Script and are outside this repository's public API.

## Input

Preferred producer: CyberPPT-Script.

Accepted v0.1 input:

- canonical `final-script.md` following the CyberPPT Final Script contract;
- legacy CyberPPT final scripts remain supported during migration.

Stage 02 may derive internal `business_relationships` from the script's locked `视觉结构`; this derivation never edits the source script.

## Semantic ownership

The script owns facts, actors, business relations, wording and factual strength. Stage 02 owns:

1. Stage 02 handoff;
2. business-relation adapter;
3. layout-neutral reading contracts;
4. visual topology and composition;
5. style selection and style lock;
6. ImageGen prompts and image production;
7. text-free base and authored SVG;
8. Quick/editable PPTX assembly;
9. visual, text, geometry and delivery QA.

Business semantic relations must not be treated as one-to-one aliases for visual topology.

## Public CLI

The standalone public entrypoint is `cyberppt-stage02`. The migration alias `cyberppt` points to the same Stage 02-only command boundary.

Stage 01 source, outline and authoring commands are intentionally not exposed.

## Compatibility namespace

v0.1 retains the internal Python namespace `cyberppt` so the mature production chain can be separated without rewriting every internal import at once. This is an implementation compatibility detail, not a product-boundary statement. Subsequent releases may prune unused legacy modules after dependency tests prove they are unnecessary.
