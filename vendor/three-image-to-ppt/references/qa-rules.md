# QA rules

Use inclusive boundaries as listed; when a value sits on a shared boundary, apply the safer (review) state unless the pass condition explicitly includes it. V1 always applies readability/dimension, OCR, line, and PPT rules. Structure-correlation and registration-error thresholds apply only when callers supply those measurements; V1 does not run segmentation or estimate transforms.

| Area | Passed | Review | Failed |
|---|---|---|---|
| Three-image dimensions | exactly identical | — | any mismatch |
| OCR visual-line count | >0 | — | 0 |
| Structure correlation excluding text | ≥0.95 | 0.88–<0.95 | <0.88 |
| Regional mean registration error | ≤3 px | >3–8 px | >8 px |
| Regional maximum registration error | ≤10 px | >10–20 px | >20 px |
| OCR line confidence | ≥0.95 | 0.80–<0.95 | <0.80 |
| Text-line completeness | ≥98% | 90%–<98% | <90% |
| Non-text false recognition | ≤2% | >2%–5% | >5% |
| Text-line coordinate error | ≤3 px | >3–8 px | >8 px |

All PowerPoint textboxes must remain in safe areas. `inside_safe_area: false`
can never pass: use review for positive, on-slide geometry that is bounded and
correctable, and failed for invalid or out-of-slide geometry. Single-line
retention must be 100%; overflow, visual-line merging, and automatic wrapping
must each be zero. A cumulative font-size correction over 8% fails; each
automatic or manual correction step is limited to 3%. Character-spacing
correction is limited to −0.2 pt through +0.2 pt.

Automatic correction order is position, safe-area box size, character spacing, font size, then recorded font substitution. Never merge/split/rewrite lines, move background geometry, or distort glyph width. Anything beyond these limits is a manual-review item.
