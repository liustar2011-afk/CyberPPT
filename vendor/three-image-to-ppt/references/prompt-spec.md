# Prompt specification

## FULL image

Before writing this prompt, append the resolved canvas instruction: `Canvas: <width>×<height> (<source>)`. The source is the script-declared pixel size, script-declared ratio, or global default `1920×1080 (16:9)`. FULL, text-free background, and TEXT must use this identical canvas.

Request a modern Chinese sans-serif appearance similar to Microsoft YaHei: open counters, natural horizontal proportions, balanced strokes, clear interiors, moderate spacing, and coordinated Chinese/numeric baselines. Do not claim the image uses the actual Microsoft YaHei font. Avoid condensed, rigid, overly heavy, or excessively geometric forms.

Mark every intended visual line as `[LINE] exact text`. Require one independent rendered line per marker, in marker order, with no merging, splitting, rewriting, or semantic reflow.

Reserve horizontal safety space of 12%–18% and vertical safety space of 10%–15%; use 15%–20% for multiline body areas. Aim for text to occupy 80%–88% of safe width and 80%–90% of safe height. Do not force fit by condensing glyphs, abnormal tracking, or new line breaks.

## Text-free background

Edit the approved FULL image and remove only letters and numbers. Lock the canvas, containers, icons, borders, arrows, color blocks, shadows, spacing, and all non-text geometry. Preserve every vacated text safe area; do not move icons into it, shrink containers, recenter remaining elements, or rebalance the composition.

## Text layer and OCR

The text image may be independently generated and may be RGB or RGBA; transparency and same-pixel provenance are not required. Keep its canvas dimensions identical to FULL and background, maximize text legibility, minimize non-text clutter, and preserve the `[LINE]` protocol. OCR consumes this image and must return at least one record, with one record per visual line.

FULL remains the visual reference/coordinate bridge and the background remains the final target coordinate system. If generated text geometry drifts, supply an approved global transform and record manual per-line corrections separately. Original-pixel extraction, segmentation, automatic registration, and high-precision regional alignment belong only to an optional future advanced mode.
