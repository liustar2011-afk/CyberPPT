# power-trusted-data-space-p12-p13

CyberPPT project workspace.

## Flow

1. Put source materials in `source/`.
2. Use `$cyber-ppt` to complete evidence analysis, storyline, and page planning.
3. Before any ImageGen or PPTX generation, save the current slide script or prompt in `workbench/scripts/drafts/` or `workbench/prompts/imagegen/`.
4. Stop for user review. Do not generate images or PPTX until an approval record exists in `workbench/approvals/`.
5. Store title/subtitle truth for template assembly in `workbench/locks/template_text/`; if dual images are supplied mid-pipeline, create this lock before template rebuild.
6. Store stage outputs under `workbench/stages/` and register every durable artifact in `workbench/artifact-ledger.json`.
7. Store page-specific attempts and resumable intermediate runs in `workbench/runs/`; use `workbench/tmp/` only for disposable scratch files.
8. Store final scripts in `workbench/scripts/final/`, QA reports in `workbench/qa/`, renders in `outputs/renders/`, and delivery files in `delivery/`.
9. Do not write new generated images or pair manifests to the repository root `images/`; keep them inside this project workspace.
