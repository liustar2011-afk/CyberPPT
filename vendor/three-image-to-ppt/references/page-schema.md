# Page schema

`page.json` is validated against `assets/schemas/page.schema.json`. `page` defines the target canvas; `images` records input paths, dimensions, and optional hashes; `containers` holds safe areas; `text_lines` holds independent visual lines; `registration` identifies the approved transform; `qa` records machine status and review items; `manual_corrections` preserves human changes without overwriting automatic results.

Each line keeps source OCR geometry, mapped geometry, automatic correction, final target geometry, and QA evidence separate. `text` and every run text must contain no CR/LF. `group_id` expresses semantic grouping only; it never authorizes line merging.

```json
{
  "line_id": "T02-L01",
  "group_id": "T02",
  "line_index": 0,
  "text": "103682 亿千瓦时",
  "bbox": {"x": 181, "y": 111, "width": 373, "height": 59},
  "polygon": [[181,111],[554,111],[554,170],[181,170]],
  "confidence": 0.99,
  "source": {"bbox": {"x":181,"y":111,"width":373,"height":59}},
  "mapping": {"transform_id":"TF-GLOBAL","mapped_bbox":{"x":181,"y":111,"width":373,"height":59},"container_id":"card-1"},
  "automatic_correction": {"dx": 0, "dy": 0, "font_scale": 1.0},
  "target": {
    "bbox_px": {"x":181,"y":111,"width":373,"height":59},
    "bbox_in": {"x":1.444,"y":0.885,"width":2.975,"height":0.470},
    "bbox_pt": {"x":103.97,"y":63.72,"width":214.20,"height":33.84},
    "inside_safe_area": true
  }
}
```

PowerPoint object names are stable: `text-<page_id>-<line_id>`. Manual adjustments belong in top-level `manual_corrections`; retain the original mapping and automatic correction unchanged.
