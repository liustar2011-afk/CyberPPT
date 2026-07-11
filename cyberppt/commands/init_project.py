"""Create a CyberPPT project workspace."""

from __future__ import annotations

import json
from pathlib import Path

from cyberppt.commands.analysis_expression_gate import adopt_analysis_expression_contract


PROJECT_DIRS = [
    "source",
    "workbench",
    "workbench/analysis_expression",
    "workbench/stages",
    "workbench/stages/01-analysis",
    "workbench/stages/01-analysis/model-runs",
    "workbench/stages/02-blueprint-dual-image",
    "workbench/stages/05-qa-delivery",
    "workbench/locks",
    "workbench/locks/template_text",
    "workbench/blueprints",
    "workbench/prompts",
    "workbench/prompts/imagegen",
    "workbench/scripts",
    "workbench/scripts/drafts",
    "workbench/scripts/final",
    "workbench/approvals",
    "workbench/runs",
    "workbench/archive",
    "workbench/tmp",
    "workbench/qa",
    "outputs",
    "outputs/pages",
    "outputs/renders",
    "delivery",
]


def _project_manifest(name: str) -> str:
    return f"""name: {name}
workflow: cyberppt
schema: cyberppt.project.v1
production_mode: full_image_ppt
writing_style:
  default: internal_public_sector
  structure_strategy: source_and_task_adaptive
directories:
  source: source
  workbench: workbench
  analysis_expression: workbench/analysis_expression
  stages: workbench/stages
  stage_analysis: workbench/stages/01-analysis
  stage_analysis_model_runs: workbench/stages/01-analysis/model-runs
  stage_full_image_ppt: workbench/stages/02-blueprint-dual-image
  stage_02_path_note: historical path name; current production mode is full_image_ppt
  stage_qa_delivery: workbench/stages/05-qa-delivery
  artifact_ledger: workbench/artifact-ledger.json
  locks: workbench/locks
  template_text_locks: workbench/locks/template_text
  blueprints: workbench/blueprints
  prompts: workbench/prompts
  imagegen_prompts: workbench/prompts/imagegen
  scripts: workbench/scripts
  script_drafts: workbench/scripts/drafts
  final_scripts: workbench/scripts/final
  approvals: workbench/approvals
  runs: workbench/runs
  archive: workbench/archive
  tmp: workbench/tmp
  qa: workbench/qa
  outputs: outputs
  delivery: delivery
gates:
  analysis_expression_contract: required
  script_review_before_generation: required
  imagegen_script_plaintext: required
  page_generation_after_user_approval: required
status:
  stage: initialized
  notes: "Place source files in source/ and start with the CyberPPT analysis phase."
"""


def _artifact_ledger() -> str:
    return json.dumps(
        {
            "schema": "cyberppt.artifact_ledger.v1",
            "artifacts": [],
            "analysis_expression_contracts": [],
        },
        ensure_ascii=False,
        indent=2,
    ) + "\n"


def init_project(path: Path, force: bool = False) -> list[Path]:
    root = path.expanduser().resolve()
    created: list[Path] = []
    manifest = root / "manifest.yml"
    readme = root / "README.md"
    ledger = root / "workbench" / "artifact-ledger.json"
    protected = [manifest, readme]
    if not force:
        existing = [item for item in protected if item.exists()]
        if existing:
            joined = ", ".join(str(item) for item in existing)
            raise FileExistsError(f"refusing to overwrite existing project files: {joined}")

    root.mkdir(parents=True, exist_ok=True)
    for directory in PROJECT_DIRS:
        target = root / directory
        target.mkdir(parents=True, exist_ok=True)
        keep = target / ".gitkeep"
        if not keep.exists():
            keep.write_text("", encoding="utf-8")
            created.append(keep)

    project_name = root.name
    manifest.write_text(_project_manifest(project_name), encoding="utf-8")
    ledger.write_text(_artifact_ledger(), encoding="utf-8")
    adopt_analysis_expression_contract(root)
    readme.write_text(
        f"""# {project_name}

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
python3 -m cyberppt produce prepare {project_name} --pages <range>
python3 -m cyberppt produce assemble {project_name} --pages <range>
python3 -m cyberppt produce verify {project_name} --pages <range>
```

`produce prepare` stops for speaker-notes approval. `produce assemble` consumes approved notes, template text lock, and full images without regenerating them. `produce verify` is the only step that can promote a file into `delivery/` and mark `deliverable_ready`.

""",
        encoding="utf-8",
    )
    created.extend([manifest, ledger, readme])
    return created
