# Manifest-Driven Image Generation and PPT Assembly Design

**Date:** 2026-07-24  
**Status:** Approved for implementation planning  
**Scope:** Migrate the proven Stage2 manifest-driven assembly contract into the current CyberPPT mainline.

## 1. Objective

Repair the image-generation and PPT assembly path so that:

1. Template-only pages remain in the ordered deck but never enter image generation.
2. Content pages use their approved `full` images.
3. Cover, agenda, section-transition, and ending pages use native brand SVG templates.
4. The final PPTX is assembled in the exact order of the final script.

The two hard acceptance requirements are:

- `cover`, `agenda`, `section`, and `ending` pages have no image prompt or image path and are explicitly recorded as template/skipped.
- One production run assembles native SVG template pages and approved content images into a complete PPTX in final-script order.

## 2. Migration-First Constraint

This work is a migration of the mature `D:\CyberPPT-Stage2` flow, not a greenfield redesign.

Implementation must:

- port the proven Stage2 role classification, skipped-page manifest contract, template metadata extraction, role validation, approved-image consumption, template assets, and tests;
- add only the thin adaptations required by the current mainline interfaces;
- preserve current-mainline features added after the Stage2 fork, including the current prompt compiler, visual style 9, speaker notes, and production artifact structure;
- avoid copying whole Stage2 source files over current files when that would discard newer mainline behavior;
- avoid creating a second assembler, a second prompt source, or a parallel production workflow.

The expected implementation surface is limited to:

- `scripts/dual_image_overlay/cyberppt_pair_manifest.py`;
- `scripts/dual_image_overlay/rebuild_engine/template_image_ppt_export.py`;
- `cyberppt/commands/final_script_pages.py`;
- the `中电联公共元素_轻量版` brand template directory;
- directly related tests.

OCR, overlay reconstruction, background derivation, and the legacy template-rebuild path are out of scope.

## 3. Architecture and Sources of Truth

`final-script-pages` is the sole production entry point. It produces or passes four approved inputs:

1. final script — the complete ordered page sequence;
2. `template_text_lock` — approved template text and page roles;
3. `page_image_pairs.json` — the sole authority for content-page images;
4. `visual_style_lock` — the approved visual style identity.

The production flow is:

```text
final script
  -> ordered pages and approved roles
  -> template pages: native cover/agenda/section/ending SVG
  -> content pages: approved full image from page_image_pairs.json
  -> one ordered PPTX
```

`image-ppt` must not reread an original script to create a second set of body prompts or fall back to its default consulting-infographic style. In project production mode it consumes the approved inputs and assembles them.

Agenda entries are derived from the ordered section pages. They are not maintained as a second manual list.

## 4. Page Roles and Manifest Contract

The canonical page roles are:

- `cover`;
- `agenda`;
- `section`;
- `content`;
- `ending`.

Compatibility aliases such as `contents`, `transition`, `closing`, and `back_cover` may be recognized at input boundaries, but production records normalize them to the canonical roles.

Role resolution follows this priority:

1. approved role in `template_text_lock`;
2. explicit page-type declaration in the final script;
3. page-number/title heuristics for compatibility;
4. fail if the role remains ambiguous.

Ambiguous pages must not silently default to content.

### 4.1 Required manifest sets

`page_image_pairs.json` records:

- `requested_pages`: every selected page in final-script order;
- `content_page_numbers`: pages that require approved images;
- `skipped_pages`: template-only pages;
- `pairs`: content-page image records.

Every template page:

- remains in `requested_pages`;
- appears in `skipped_pages`;
- has `render_mode: "template"`;
- has `status: "skipped"`;
- records its canonical role, template name, and `reason: "template_only_page"`;
- has no prompt, image path, or `full` record;
- never appears in `pairs`.

Every content page:

- has role `content`;
- appears exactly once in `pairs`;
- contains the already compiled deliverable prompt;
- identifies exactly one approved `full` image path;
- never appears in `skipped_pages`.

The union of `pairs` page numbers and `skipped_pages` page numbers must equal `requested_pages`, and their intersection must be empty. Pure-template selections are valid and do not require an artificial content page.

## 5. Native Template Rules

The brand mapping is:

| Role | Template |
|---|---|
| `cover` | `01_cover.svg` |
| `agenda` | `02_agenda.svg` |
| `section` | `03_section.svg` |
| `ending` | `04_ending.svg` |

`02_agenda.svg` and `03_section.svg`, together with their `brand_rules.json` mappings, are migrated from the verified Stage2 brand package.

### 5.1 Cover

Cover title, optional subtitle, author/reporting unit, and optional date come only from the approved template text lock. Script protocol fields must not become visible content. Existing title safe-area and two-line readability checks remain in force.

### 5.2 Agenda

Agenda items are extracted from section pages in final-script order. Labels are consecutive (`01`, `02`, and so on) and do not reuse slide numbers. Titles come from the corresponding approved section locks.

No cross-project default copy is allowed. An agenda page with no section pages fails production. Multiple agenda pages may share the same derived list. Agenda pagination is out of scope; exceeding template capacity fails clearly.

### 5.3 Section

Each section page receives:

- a consecutive section label;
- the approved section title;
- an optional approved subtitle.

No generic subtitle is inserted when none was approved.

### 5.4 Ending

Ending-page text comes only from that page's approved lock. It does not borrow cover or content text and never enters image generation.

All template substitutions are XML-escaped. Missing templates, unknown required fields, or unreplaced placeholders fail production.

## 6. Ordered PPT Assembly

The final script's selected-page list is the only ordering authority. The assembler must not group by role or use filename, filesystem, or `pairs` ordering.

For each ordered page:

- `cover` renders `01_cover.svg`;
- `agenda` renders `02_agenda.svg`;
- `section` renders `03_section.svg`;
- `content` places the approved `full` image in the locked content region while retaining the PPT title and enterprise chrome;
- `ending` renders `04_ending.svg`.

Content images are loaded only from `page_image_pairs.json`. Production assembly performs no prompt compilation, image generation, OCR, overlay, or background derivation.

`final-script-pages --production-build` explicitly passes the final script, template text lock, page image manifest, visual style lock, selected pages, output directory, and output name to `image-ppt`.

Any retained direct-script `image-ppt` mode is non-production preview behavior and cannot emit `production_ready`.

Before publication, the assembler verifies:

- slide count equals `requested_pages` count;
- each output position corresponds to the same position in the final script;
- every template role uses the matching SVG;
- every content page uses its page-matched approved image exactly once;
- the generated PPTX can be reopened and reports the expected slide count.

## 7. Production Readiness and Failure Handling

Production validation runs before publishing the final PPTX:

1. verify all four approved inputs exist and are readable;
2. verify they belong to the same project and production scope;
3. verify page order, page numbers, and roles;
4. verify the approved text lock covers every requested page;
5. verify the manifest partition is complete and mutually exclusive;
6. verify template assets, fields, and derived section metadata;
7. verify content-image approval status, path, file, and geometry;
8. verify the visual style lock identity;
9. write a temporary PPTX;
10. reopen it and validate slide count and traceability;
11. atomically publish it to the final output path.

Production must fail when any contract is missing, contradictory, or incomplete, including:

- a template page classified as content;
- a template page carrying a prompt or image;
- a content page marked skipped;
- missing, duplicate, or unexpected pages;
- disagreement among final script, text lock, and manifest roles;
- a missing, unapproved, empty, or geometrically invalid content image;
- a missing brand SVG;
- an agenda with no section items;
- unreplaced SVG placeholders;
- a missing or mismatched visual style lock;
- a PPTX that cannot be reopened or has the wrong slide count.

Failure records `production_failed`, the failed stage, affected pages, and a recovery instruction. It must not publish an incomplete PPTX or overwrite a previously valid output. Existing approved content images remain reusable after a template or assembly failure.

Only a fully validated run records `production_ready`. The readiness report includes page count, template page numbers, content page numbers, final PPTX path, and stable identities or hashes for the four approved inputs.

## 8. Testing Strategy

### 8.1 Manifest and role tests

Tests verify:

- all four template roles enter `skipped_pages`;
- template records contain no prompt or image fields;
- only content pages enter `pairs`;
- requested-page order is preserved;
- the partition is complete and mutually exclusive;
- approved roles override heuristics;
- missing, duplicate, and conflicting roles fail;
- pure-template selections produce a valid manifest.

### 8.2 Brand template tests

Stage2's relevant template tests are migrated and adapted to verify:

- all four SVG mappings;
- cover safe-area and protocol-field filtering;
- agenda extraction, ordering, and numbering;
- no cross-project default agenda copy;
- section ordering and optional subtitles;
- logo and brand-bar presence;
- correct XML escaping;
- no unreplaced placeholders.

### 8.3 Assembly acceptance fixture

A fixed end-to-end fixture uses:

```text
1 cover
2 agenda
3 section
4 content
5 content
6 section
7 content
8 ending
```

The test asserts:

- the PPTX contains exactly eight slides in that order;
- pages 1, 2, 3, 6, and 8 use their native SVG templates;
- pages 4, 5, and 7 use their page-matched approved full images;
- template pages require no image assets;
- no prompt compiler or image-generation path runs during assembly;
- the visual style lock is explicitly consumed and recorded;
- the PPTX reopens successfully.

### 8.4 Failure and regression tests

Negative tests cover missing templates, prompts on template pages, missing/unapproved content images, role conflicts, empty agenda metadata, incomplete page sets, wrong image-to-page mapping, missing visual locks, unreplaced placeholders, and invalid PPTX page counts.

Regression tests retain:

- reviewable non-production `final-script-pages` output;
- `--require-images` checking content pages only;
- reuse of approved full images;
- existing cover and ending behavior;
- exclusion of OCR, overlay, background derivation, and legacy rebuild;
- valid partial production for explicitly selected content-only page ranges.

## 9. Implementation Guardrails


During implementation:

- compare each target area with the Stage2 implementation before writing adaptations;
- preserve unrelated dirty-worktree changes;
- do not rename symbols with text replacement;
- do not broaden the file set beyond the migration surface without explicit review.

Before any implementation commit:

- run focused and end-to-end tests;
- confirm only the expected symbols and execution flows changed;
- stage only files belonging to this task.

## 10. Acceptance Criteria

The design is complete when implementation demonstrates both hard requirements:

1. Cover, agenda, section, and ending pages remain in the ordered production manifest as `template/skipped`, with no image prompt or image path.
2. One validated production run assembles those native SVG pages and the approved content-page full images into a complete, correctly ordered, reopenable PPTX.

