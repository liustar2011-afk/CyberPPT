# Visual Quality Rules

`visual_quality_rules.py` provides deterministic quality helpers for image-to-editable-PPT flows where the slide background is image-locked and the text layer remains editable.

It is intentionally separate from the SVG-only gate:

- The editable layer keeps independent PowerPoint text boxes.
- QA may group related text boxes without merging them.
- A rendered visual comparison is never implied unless the caller explicitly provides it.

## Layers

`summarize_visual_quality()` returns five status blocks.

| Layer | Purpose |
|---|---|
| `deterministic_status` | Text fit, vertical-wrap risk, text overlap, container overflow, dark-background readability fixes |
| `content_lock_status` | Required script strings are present and no observed editable text falls outside the locked source text |
| `text_group_status` | QA-only grouping checks whether related text boxes overflow a shared visual container |
| `visual_similarity_status` | Rendered PPT output compared with the source image; remains `not_evaluated` until the caller performs that comparison |
| `manual_review_status` | Aggregates all unresolved items that must not be reported as passed |

Status values:

| Status | Meaning |
|---|---|
| `passed` | Checked and no unresolved issue |
| `fixed` | Checked; deterministic fixes were applied and no unresolved issue remains |
| `needs_human` | Checked but one or more unresolved items remain |
| `not_evaluated` | The layer was not checked; do not describe it as passed |

## Text Group Rule

Do not merge across visual lines for editability. For a layout such as:

```text
存证凭证
固化成果权属与    研发时间线，司法互认
```

the editable PPT layer should keep three text boxes. The QA layer may group all three boxes for one shared container-boundary check and records:

- `editable_text_box_count: 3`
- `visual_line_count: 2`
- `container_overflow_unresolved`
- `overflow_sides`

Only text fragments that belong to the same visual line should be merged before export.

## Caller Contract

Typical flow:

```python
adjusted_boxes, records = apply_visual_quality_rules(text_boxes, background_image, (1280, 720))
groups = build_text_quality_groups(adjusted_boxes, records)
summary = summarize_visual_quality(
    records,
    groups,
    required_texts=locked_script_strings,
    observed_texts=[box.text for box in adjusted_boxes],
    visual_similarity_checked=False,
)
manifest["quality"] = summary.to_dict()
```

After exporting PPTX and rendering it back to PNG, callers may set:

```python
summary = summarize_visual_quality(
    records,
    groups,
    required_texts=locked_script_strings,
    observed_texts=[box.text for box in adjusted_boxes],
    visual_similarity_checked=True,
    visual_similarity_unresolved=render_diff_failed,
    visual_similarity_details=render_diff_notes,
)
```

Do not report "quality passed" unless every checked layer is `passed` or `fixed`, and `visual_similarity_status` is checked when the claim is visual fidelity.
