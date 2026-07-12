# Semantic Font Fitting Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace OCR-box-height font sizing with semantic limits and real-font reverse fitting, then validate only page 004.

**Architecture:** Classify each visual line into a small reusable text-role vocabulary, obtain role-specific point-size bounds, and search downward using the resolved Microsoft YaHei face until measured glyphs fit the available box with width/height safety margins. The OCR box remains positioning evidence and is never directly converted to a PowerPoint font size.

**Tech Stack:** Python 3.14, Pillow ImageFont, existing font resolver, pytest, vendor three-image pipeline.

## Global Constraints

- Do not regenerate FULL, BACKGROUND, or TEXT.
- Do not change canvas sizing, registration, OCR matching, or background cleanup.
- Do not hardcode page-004 text strings.
- Use 0.5pt output granularity.
- Validate only page 004 before any batch run.

---

### Task 1: Semantic role classification and bounds

**Files:**
- Modify: `vendor/three-image-to-ppt/scripts/recover_text_styles.py`
- Modify: `vendor/three-image-to-ppt/tests/test_recover_text_styles.py`

- [ ] Write failing tests for headline numbers, percentages, labels, body text, and titles using generic text/geometry features.
- [ ] Run the focused tests and verify the new classifier is absent.
- [ ] Implement `classify_text_role()` and `FONT_LIMITS_PT` without page-specific strings.
- [ ] Verify each role receives the documented bounds and commit.

### Task 2: Real-font reverse fitting

**Files:**
- Modify: `vendor/three-image-to-ppt/scripts/recover_text_styles.py`
- Modify: `vendor/three-image-to-ppt/tests/test_recover_text_styles.py`

- [ ] Write failing tests proving short body text cannot exceed 18pt, percentages cannot exceed 28pt, and headline numbers cannot exceed 40pt.
- [ ] Implement `fit_ppt_font_size()` using the resolved YaHei face, 90% usable width, 82% usable height, and a downward search in pixel space.
- [ ] Convert px to pt at 96 DPI and round to 0.5pt.
- [ ] Replace direct OCR-height sizing in `fit_font_style()` while preserving color, weight, and alignment recovery.
- [ ] Run focused tests and commit.

### Task 3: Pre-render font-fit QA

**Files:**
- Modify: `vendor/three-image-to-ppt/scripts/run_pipeline.py`
- Modify: `vendor/three-image-to-ppt/tests/test_pipeline.py`

- [ ] Write failing tests for role-limit violation and measured width/height overflow.
- [ ] Add line-level fit evidence to QA; unresolved fit must be review or failed, never passed silently.
- [ ] Run pipeline tests and commit.

### Task 4: Page 004 validation

**Files:**
- Input: existing page-004 FULL/BACKGROUND/TEXT and hybrid OCR JSON.
- Output: `editable_text/fontfit_page_004/`.

- [ ] Rebuild page 004 without regenerating source images.
- [ ] Render and visually compare with the rejected page and reference PPTX.
- [ ] Confirm catastrophic overlaps are removed and record remaining background-residue issues separately.
- [ ] Run all focused CyberPPT and vendor tests plus GitNexus staged change detection.
- [ ] Do not run other pages or change defaults without user approval.
