"""Create a CyberPPT project workspace."""

from __future__ import annotations

import json
from pathlib import Path


PROJECT_DIRS = [
    "source",
    "workbench",
    "workbench/stages",
    "workbench/stages/01-analysis",
    "workbench/stages/02-blueprint-dual-image",
    "workbench/stages/03-overlay",
    "workbench/stages/04-template-rebuild",
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
directories:
  source: source
  workbench: workbench
  stages: workbench/stages
  stage_analysis: workbench/stages/01-analysis
  stage_blueprint_dual_image: workbench/stages/02-blueprint-dual-image
  stage_overlay: workbench/stages/03-overlay
  stage_template_rebuild: workbench/stages/04-template-rebuild
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
    readme.write_text(
        f"""# {project_name}

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
""",
        encoding="utf-8",
    )
    created.extend([manifest, ledger, readme])
    return created
