# power-supply-demand-forecast-three-image-0711

CyberPPT project workspace.

## Flow

1. Put source materials in `source/`.
2. Use `$cyber-ppt` to complete evidence analysis, material-type and reporting-task identification, adaptive storyline planning, and page planning. New projects default to the formal central-SOE/government internal-reporting writing style; do not impose a fixed chapter order.
3. Complete the analysis-expression gates in order: source analysis, reporting direction, report structure, page design, and business script. Then confirm the visual style, blueprint input, generated full images, speaker notes, image-PPT assembly, and delivery QA in sequence.
4. Before any ImageGen or PPTX generation, save the current slide script or prompt in `workbench/scripts/drafts/` or `workbench/prompts/imagegen/`.
5. Stop for user review. Do not generate images or PPTX until an approval record exists in `workbench/approvals/`.
6. Store title/subtitle truth for template assembly in `workbench/locks/template_text/`; if full images are supplied mid-pipeline, create this lock before image-PPT assembly.
7. Store stage outputs under `workbench/stages/` and register every durable artifact in `workbench/artifact-ledger.json`.
8. Store page-specific attempts and resumable intermediate runs in `workbench/runs/`; use `workbench/tmp/` only for disposable scratch files.
9. Store final scripts in `workbench/scripts/final/`, QA reports in `workbench/qa/`, renders in `outputs/renders/`, and delivery files in `delivery/`.
10. Do not write new generated images or pair manifests to the repository root `images/`; keep them inside this project workspace.

## Production Commands

The default mainline is `full_image_ppt`. The historical path `workbench/stages/02-blueprint-dual-image/` is retained for compatibility, but it now stores approved full-image PPT production artifacts.

```bash
python3 -m cyberppt produce prepare power-supply-demand-forecast-three-image-0711 --pages <range>
python3 -m cyberppt produce assemble power-supply-demand-forecast-three-image-0711 --pages <range>
python3 -m cyberppt produce verify power-supply-demand-forecast-three-image-0711 --pages <range>
```

`produce prepare` stops for speaker-notes approval. `produce assemble` consumes approved notes, template text lock, and full images without regenerating them. `produce verify` is the only step that can promote a file into `delivery/` and mark `deliverable_ready`.
