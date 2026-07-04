---
description: Script-imagegen to PPT workflow — generate page images from a compact script and export either image-based PPTX or background + editable text overlay PPTX
---

# Script Imagegen to PPT Workflow

> Run when the user provides a `script-imagegen-compact.md` style script and asks to generate images, then convert those generated pages into a PPTX. Typical requests include "脚本生图转ppt", "按这个脚本生成第12-14页", "用脚本生成全图并做成PPT", or "底图不编辑，文字可编辑".

This workflow is **independent** from the main hand-written SVG pipeline. It uses `page_image_pair_batch.py` to plan page prompts and generate page images through the host-native Codex OAuth image path. For editable-text delivery, `script_imagegen_rebuild_template.py` keeps the no-text background image as the bottom visual asset, locates text from the full image, corrects it with the script as truth, and exports editable PPT text on top.

## When to Run

Recognize requests where the source of truth is an image-generation script rather than a source document to be re-architected:

| Pattern | Example |
|---|---|
| Compact script + page range | "按 `script-imagegen-compact.md` 生成第12页-14页" |
| Script to PPT | "把这条脚本生图转ppt" |
| Page image generation with export | "生成全图并转成PPT" |
| Editable text over background | "底图不编辑，文字可编辑", "用全图定位文字、底图放底层" |
| Resume prior script-imagegen project | "继续这个脚本生图项目，断点续跑" |
| Explicit full/background pair need | "这几页需要双图：全图和无字背景图" |

**Hard rule**: Do not enter the main Strategist -> Executor SVG authoring pipeline for this workflow. The script already contains page-level visual and copy instructions. In the editable overlay route, only text is editable; the generated visual structure remains an image asset.

**Default output**: Generate and export **full images only**. Use the editable-text overlay route when the user asks for editable text, OCR/text reconstruction, or "底图 + 可编辑文字". Generate no-text background images only when the user explicitly asks for dual images/editable overlay or the command includes `--dual-image`.

---

## 1. Inputs

🚧 **GATE**: The user has provided a script file or an exact script path.

| Input | Required | Notes |
|---|---:|---|
| Script file | Yes | Usually `script-imagegen-compact.md`; may be any compatible Markdown script |
| Page selection | Optional | Accepts `12-14`, `1,3,5-7`, or `all`; default is all script pages |
| Project path / name | Optional | Reuse `--project-path` for continuation; use `--project-name` for a new project |
| Style preset | Optional | `--image-style` accepts a preset name or JSON/Markdown style path |
| Dual-image requirement | Optional | Only explicit requests use `--dual-image` |

**Default style**: When `--image-style` is omitted, the image prompt style is `象牙白深蓝强调` (`象牙白 + 深蓝强调`, migrated from CyberPPT option 04).

---

## 2. Output Contract

`run` creates or reuses a PPT Master project and keeps all artifacts inside it.

| Path | Contents |
|---|---|
| `<project>/sources/` | Archived source script |
| `<project>/images/script_imagegen/` | `page_image_pairs.json`, generated image files, and task sidecars |
| `<project>/exports/script_imagegen_to_ppt/` | Exported image-based PPTX |

| Mode | Generated variants | Export behavior |
|---|---|---|
| Default | `full` | One PPT slide per script page |
| `--dual-image` | `full`, `background` | Two PPT slides per script page: full image first, no-text background second |
| Editable overlay | `full`, `background`, OCR mapping | One PPT slide per script page: no-text background image at bottom, editable text boxes on top |

**Hard rule**: Unless the user explicitly requests dual images or editable-text overlay, do not generate or export background images.

---

## 3. One-Command Run

Use `run` for normal production work.

```bash
python3 skills/ppt-master/scripts/page_image_pair_batch.py run \
  --script "<script.md>" \
  --pages 12-14 \
  --project-name "<name>" \
  --parallel-pages 3
```

For a faster review pass:

```bash
python3 skills/ppt-master/scripts/page_image_pair_batch.py run \
  --script "<script.md>" \
  --pages 12-14 \
  --project-name "<name>" \
  --parallel-pages 3 \
  --draft
```

For continuation inside an existing project:

```bash
python3 skills/ppt-master/scripts/page_image_pair_batch.py run \
  --script "<script.md>" \
  --pages 12-14 \
  --project-path "<project>" \
  --resume \
  --parallel-pages 3
```

For explicit full/background generation:

```bash
python3 skills/ppt-master/scripts/page_image_pair_batch.py run \
  --script "<script.md>" \
  --pages 12-14 \
  --project-name "<name>" \
  --dual-image \
  --parallel-pages 3
```

For editable text over a no-text background:

```bash
python3 skills/ppt-master/scripts/script_imagegen_rebuild_template.py run \
  --script "<script.md>" \
  --pages 12-14 \
  --project-name "<name>" \
  --parallel-pages 3 \
  --ocr-backend vision-json
```

This route internally forces full/background generation because it needs both assets. The full image is used only for text location; the exported slide uses the background image plus editable text.

---

## 4. Speed Controls

| Control | Command option | Behavior |
|---|---|---|
| Page-level parallelism | `--parallel-pages N` | Runs independent pages concurrently; inside each page, dual-image mode still preserves `full -> background` order |
| Draft generation | `--draft` | Uses medium quality, `1x-content-region` image size, and a 1x content-region canvas unless explicitly overridden |
| Resume | `--resume` | Reuses an existing `page_image_pairs.json` in the image directory instead of rebuilding the plan |
| Cache reuse | default | Existing generated images are kept and skipped |
| Forced overwrite | `--force` | Overwrites existing images and regenerates them |

**Default — practical speed setting**: For page ranges such as `12-14`, use `--parallel-pages 3`. For a larger range, choose a conservative value that does not saturate the local image backend or trigger request failures.

---

## 5. Step-by-Step Mode

Use this when debugging, reviewing prompts before generation, or rerunning only one phase.

### 5.1 Plan

```bash
python3 skills/ppt-master/scripts/page_image_pair_batch.py plan \
  --script "<script.md>" \
  --pages 12-14 \
  -o "<project>/images/script_imagegen"
```

Output: `<project>/images/script_imagegen/page_image_pairs.json`.

### 5.2 Generate

```bash
python3 skills/ppt-master/scripts/page_image_pair_batch.py generate \
  "<project>/images/script_imagegen/page_image_pairs.json" \
  --parallel-pages 3
```

Use `--dual-image` only when background images are explicitly required:

```bash
python3 skills/ppt-master/scripts/page_image_pair_batch.py generate \
  "<project>/images/script_imagegen/page_image_pairs.json" \
  --dual-image \
  --parallel-pages 3
```

### 5.3 Verify

```bash
python3 skills/ppt-master/scripts/page_image_pair_batch.py verify \
  "<project>/images/script_imagegen/page_image_pairs.json"
```

### 5.4 Export PPTX

```bash
python3 skills/ppt-master/scripts/page_image_pair_batch.py export-pptx \
  "<project>/images/script_imagegen/page_image_pairs.json" \
  -o "<project>/exports/script_imagegen_to_ppt"
```

Use `--dual-image` only when the PPTX must include both variants:

```bash
python3 skills/ppt-master/scripts/page_image_pair_batch.py export-pptx \
  "<project>/images/script_imagegen/page_image_pairs.json" \
  -o "<project>/exports/script_imagegen_to_ppt" \
  --dual-image
```

### 5.5 Rebuild Editable Text Overlay

Use this when `page_image_pairs.json` already exists and contains both `full` and `background` variants:

```bash
python3 skills/ppt-master/scripts/script_imagegen_rebuild_template.py rebuild \
  "<project>/images/script_imagegen/page_image_pairs.json" \
  --ocr-backend vision-json \
  --export
```

For debugging without OCR/backend calls, prewrite `<project>/analysis/ocr/page_XXX_text_layout.json` and use `--ocr-backend none`.

---

## 6. Quality Gates

| Gate | Check |
|---|---|
| Manifest exists | `<project>/images/script_imagegen/page_image_pairs.json` exists and includes the requested page range |
| Variant scope | Default manifests / exports contain `full` only; dual-image runs contain `full` and `background` |
| Image status | Requested variants reach `Generated` and image files exist with non-zero size |
| OCR mapping | Editable overlay route writes `<project>/analysis/ocr/page_XXX_text_layout.json` and `page_XXX_text_mapping.json` |
| PPTX output | Image-based route writes `<project>/exports/script_imagegen_to_ppt/*.pptx`; editable overlay route writes `<project>/exports/*.pptx` |
| Office validation | Validate or render the PPTX with repository-local OfficeCLI when available |

Recommended PPTX validation:

```bash
skills/officecli/bin/release/officecli-mac-arm64 validate \
  "<project>/exports/script_imagegen_to_ppt/<deck>.pptx"
```

**Manual visual pass**: Inspect the exported PPTX or rendered screenshots for legible text, adequate contrast, full-page coverage, and correct page order. For dual-image mode, verify each full/background pair belongs to the same script page.

---

## 7. Failure Handling

| Symptom | Action |
|---|---|
| A page image failed | Rerun `run` or `generate` with `--resume`; cached successful images are kept |
| A cached image is visually wrong | Rerun with `--force` or delete that image before resuming |
| Generation is too slow | Add or raise `--parallel-pages`; add `--draft` for review runs |
| Background images were generated unintentionally | Rerun without `--dual-image`; default mode exports full images only |
| Need to keep prompts stable | Reuse the existing project and pass `--resume` |

**Hard rule**: Do not silently switch from full-only to dual-image mode as a troubleshooting step. Dual-image mode changes the deck structure and must be user-directed.
