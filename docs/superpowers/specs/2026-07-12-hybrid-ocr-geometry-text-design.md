# Hybrid OCR Geometry and Text Design

## Goal

Improve editable-text reconstruction by separating two OCR responsibilities:
macOS Vision supplies visual-line geometry, while local PaddleOCR supplies the
authoritative Chinese text. Validate the design on page 004 before changing the
project default or running other pages.

## Scope

- Reuse the existing FULL, BACKGROUND, and TEXT images.
- Do not regenerate slide images.
- Do not change canvas sizing or registration behavior.
- Produce a vendor-compatible canonical OCR JSON file.
- Rebuild only page 004 during validation.

## Components

### Vision geometry adapter

Run the existing `vision_ocr.swift` implementation in accurate Chinese/English
mode. Preserve each detected visual line's bounding box and confidence. Vision
text is evidence, not authoritative output.

### Paddle text source

Run the existing repository-local PaddleOCR adapter. Preserve Paddle text and
confidence. Paddle bounding boxes are matching evidence but are not used when a
valid Vision geometry match exists.

### Deterministic matcher

Match observations using vertical overlap, horizontal overlap, center distance,
and reading order. Permit one-to-many matching when Vision splits a Paddle line,
such as `同比增长 5.0%`. Allocate Paddle text to Vision boxes only when the split
can be supported by normalized Vision text or an unambiguous substring boundary.

For a one-to-one match, output Paddle text with the Vision bounding box. For an
unambiguous one-to-many match, output one canonical line per Vision box with the
corresponding Paddle substring. Never invent, rewrite, or silently discard text.

### Review evidence

Each canonical line records both source observations, match type, match score,
and whether text or geometry required fallback. Unmatched, ambiguous, or
conflicting observations become review items. The pipeline must not silently
mark such lines as passed.

## Failure and fallback rules

- Use Paddle geometry when no safe Vision match exists.
- Preserve the full Paddle text when a split is ambiguous.
- Mark low-confidence Vision recognition as geometry-only evidence rather than
  rejecting an otherwise valid spatial match.
- Fail the OCR build only when no canonical lines are produced or an output box
  is invalid/outside the image.

## Page 004 acceptance

Page 004 is the sole initial validation page. Acceptance requires:

1. All intended source text remains present in the canonical OCR JSON.
2. Mixed-size rows such as `同比增长 / 5.0%` and `约占总装机 / 60%` are split into
   separate visual boxes where Vision supplies reliable geometry.
3. Rebuilt editable text no longer produces the extreme overlap shown in the
   rejected screenshot.
4. Any remaining uncertain line is explicitly reported for review.
5. Existing OCR, pipeline, and renderer tests remain green.

Only after visual approval of page 004 may hybrid OCR become selectable/default
for the three-image CyberPPT adapter and be applied to the remaining pages.

## Testing

- Unit tests for one-to-one, one-to-many, unmatched, ambiguous, and out-of-bounds
  observations.
- Adapter test proving canonical JSON includes provenance and review evidence.
- Page 004 A/B artifact comparison using identical FULL/BACKGROUND/TEXT inputs.
- Regression tests for the existing Paddle-only path.
