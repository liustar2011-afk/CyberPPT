---
name: ppt-image-enhancer
description: Improve the resolution, sharpness and clarity of existing images, especially PPT/report page images, screenshots, diagrams and AI-generated slide visuals. Use when the user asks to enhance image quality, upscale, sharpen, deblur, reduce artifacts, or prepare images for PPT without redesigning them.
---

# PPT Image Enhancer

## Goal

Enhance an existing image while preserving its wording, layout, geometry and business meaning. This Skill includes executable code and optional real AI super-resolution backends.

The user should not need to choose Real-ESRGAN vs SwinIR, model names, tile sizes, CUDA settings or YAML presets for ordinary use.

## Ordinary invocation

When the user gives one image and asks to improve quality:

1. Locate the image file.
2. Run `python tools/doctor.py` if backend readiness is unknown.
3. If no AI backend is installed and the image is not a text/diagram-dominant page, bootstrap the portable backend with `python tools/bootstrap.py --backend auto` when network access is available.
4. Run:

```bash
python enhance.py "<input-image>"
```

5. Return the generated `*_enhanced.png` file and briefly state which backend was actually used.

For a directory of images:

```bash
python batch.py "<input-directory>"
```

Do not ask the user to select a backend unless automatic setup is impossible and the available choices materially affect execution.

## Automatic policy

`enhance.py` performs two independent decisions:

### Page mode

- `chart_heavy`: high fine-edge density; text, lines and geometry dominate.
- `ppt_page`: typical white/light presentation page with mixed text and graphics.
- `scene_plus_text`: scene/illustration content is visually significant.
- `screenshot`: use only when explicitly known or selected.

### Backend

- `chart_heavy` → default to `builtin` conservative enhancement to protect text/line fidelity.
- otherwise prefer installed `realesrgan_ncnn` portable backend.
- if unavailable, use installed Real-ESRGAN Python backend.
- if unavailable, use installed SwinIR Python backend.
- if none are available, use `builtin` rather than fail.

If an automatically selected AI backend fails, retry once using `builtin` and still produce an output.

For AI backends, structural fidelity is a hard gate. The pipeline compares the
enhanced result with the source/Lanczos reference using structural correlation,
mean absolute change, original-edge recall and new-edge precision. A failed
model result is rejected and the image is regenerated with `builtin`; the
report retains the rejected backend and metrics under `rejected_model_result`.

## AI super-resolution integration

This repository integrates:

- Real-ESRGAN NCNN Vulkan portable executable;
- official Real-ESRGAN Python repository;
- official SwinIR Python repository;
- built-in OpenCV/Lanczos enhancement.

Large third-party binaries and pretrained weights are not embedded in the Skill archive. `tools/bootstrap.py` installs them into `runtime/` or `third_party/`. See `MANIFEST.md`.

## PPT text and line protection

Never treat raw AI-SR output as authoritative for PPT text.

For AI backends, the pipeline must:

1. create a Lanczos reference from the original image at the final target size;
2. run AI super-resolution;
3. normalize the AI result to the final target dimensions;
4. build a high-frequency/fine-structure mask from the original reference;
5. blend original-reference detail back into those regions;
6. protect near-white slide backgrounds;
7. apply only restrained denoise, local contrast and sharpening;
8. validate aspect ratio, white-background stability, blockiness and extreme sharpening.

This is intended to reduce stroke drift on Chinese characters, arrows, borders and chart geometry.

## Hard boundaries

- Enhancement is not redesign.
- Do not OCR-rewrite or guess Chinese characters.
- Do not add icons, illustrations or decorative elements.
- Do not change layout hierarchy or composition.
- Do not claim that AI SR recovered factual detail that was absent in the source.
- Do not use face enhancement unless the user explicitly asks for portrait restoration.
- Do not force AI SR on a crisp, text-heavy page merely to make the file larger.

## Output

Default single-image outputs:

```text
<name>_enhanced.png
<name>_enhanced.png.report.json
```

The report records:

- detected page mode;
- selected and actually used backend;
- source/output dimensions;
- sharpness, edge density, white ratio, blockiness and noise indicators;
- warnings and automatic fallback information.

## Setup details

For normal desktop use:

```bash
python tools/bootstrap.py --backend auto
```

For all optional backends:

```bash
python tools/bootstrap.py --backend all
```

Python Real-ESRGAN/SwinIR backends require a PyTorch build appropriate to the machine. The portable Real-ESRGAN NCNN route does not depend on the repository's Python/PyTorch inference stack.

See `README.md` for human-facing setup and `MANIFEST.md` for bundled vs downloaded components.
