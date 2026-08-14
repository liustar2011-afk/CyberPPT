# CyberPPT Extended Style 9 Implementation Plan
> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add an explicitly selectable global style 9 that migrates the Stage2 open visual grammar while preserving the original style 4 and the default eight-style chooser.

**Architecture:** Extend the JSON style library with one style record, keep default enumeration filtered to IDs 1—8, and add a focused visual-grammar contract rendered once by the deliverable prompt assembler. Add a new sample asset and contract tests that freeze the original eight styles.

**Tech Stack:** Python 3.11+, JSON, dataclasses, pytest, built-in ImageGen, existing CyberPPT prompt pipeline.

## Global Constraints

- Preserve styles 1—8 byte-for-semantic-field; do not replace style 4.
- Style 9 is extension-only and requires explicit selection.
- Open visual grammar protects readability, business semantics, state and source boundaries.
- Do not migrate the Stage2 project lifecycle, output folders, or old assembly runtime.
- Use TDD for every behavior change.

---

### Task 1: Extended Style Registration

**Files:**
- Modify: `scripts/dual_image_overlay/style_presets/cyberppt_default_styles.json`
- Modify: style-library contract tests selected after code-index inspection.

**Interfaces:**
- Consumes: existing style JSON schema.
- Produces: explicit style 9 lookup while default choices remain IDs 1—8.

- [ ] Write tests asserting the library contains unique IDs 1—9, default choices are 1—8, style 4 is unchanged, and explicit ID/slug 9 resolves.
- [ ] Run the focused tests and verify RED because style 9 is absent.
- [ ] Add style 9 with slug `ivory_deep_blue_scene`, the approved name, style4 palette, open material contract, and extension-only marker.
- [ ] Run the focused tests and verify GREEN.

### Task 2: Open Visual Grammar

**Files:**
- Create: `scripts/dual_image_overlay/visual_grammar.py`
- Modify: `scripts/dual_image_overlay/deliverable_prompt.py`
- Create or modify: focused prompt-contract tests.

**Interfaces:**
- Produces: `VisualGrammarContract` and `default_visual_grammar()`.
- Consumer: final prompt rendering function.

- [ ] Write tests requiring semantic containers, expressive connectors, clean text regions, and unequal hierarchy; require the prompt section exactly once.
- [ ] Run tests and verify RED because the contract is absent.
- [ ] Implement the immutable contract and render it once without removing source/state boundaries.
- [ ] Run tests and verify GREEN.

### Task 3: Sample, Documentation, and Regression

**Files:**
- Create: `assets/palette-samples/palette-09.png`
- Modify: `references/visual-system.md`
- Modify: relevant skill/reference contract tests.

**Interfaces:**
- Produces: visible style9 sample and documented extension route.

- [ ] Write tests requiring `palette-09.png`, the style9 name, and unchanged default-eight wording.
- [ ] Run tests and verify RED.
- [ ] Generate a standalone 16:9 sample using the migrated visual grammar and save it as `palette-09.png`.
- [ ] Document style9 as an extension, not a ninth default choice.
- [ ] Run focused tests, repository doctor, and visual asset dimension checks.
