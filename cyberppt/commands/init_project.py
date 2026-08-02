"""Create a CyberPPT project workspace."""

from __future__ import annotations

import json
from pathlib import Path


PROJECT_DIRS = [
    "source",
    "review",
    "visual",
    "workbench",
    "workbench/stages",
    "workbench/stages/01-analysis",
    "workbench/stages/01-analysis/outline-attempts",
    "workbench/stages/01-analysis/source-truth-attempts",
    "workbench/references",
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
    "workbench/scripts/audits",
    "workbench/scripts/audits/attempts",
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
  source_truth: workbench/stages/01-analysis/source-truth.json
  source_truth_attempts: workbench/stages/01-analysis/source-truth-attempts
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
  script_audits: workbench/scripts/audits
  approvals: workbench/approvals
  runs: workbench/runs
  archive: workbench/archive
  tmp: workbench/tmp
  qa: workbench/qa
  outputs: outputs
  delivery: delivery
gates:
  script_review_before_generation: required
  visual_structure_designer: required
  imagegen_script_plaintext: required
  page_generation_after_user_approval: required
chapter_review:
  outline: required
  script: required
  require_consumption: true
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
2. Use solution architecture by default for research, construction, implementation, and initiation materials; use consulting architecture only when explicitly selected.
3. New formal solution projects use `argument_contract_mode: strict` with `cyberppt.outline.v2`. Build each page from source-grounded `core_message`, `content_units`, and `content_relations`; page types and claim taxonomies do not determine the page meaning.
4. Build `source-truth.json`, then run `python -m cyberppt source-truth-audit <project> --input <source-truth.json>`. The JSON is authoritative; the command renders `00-source-analysis.md`, preserves attempts, and changes extraction direction when coverage is incomplete.
5. Preserve the source material's actual sequence and relations. An argument chain may be used only when the material itself supports it; it is never a mandatory chapter template.
6. Only after Source Truth passes or a recorded escalation decision (`resolve-escalation --gate source_truth`), audit the Stage 01 outline with `python -m cyberppt outline-audit <project> --input <outline.json> --source-truth <source-truth.json>`.
7. Run `python -m cyberppt prepare-chapter-review <project> --level outline`, complete the Markdown reviews under `review/`, then run `python -m cyberppt chapter-review-audit <project> --level outline`.
8. Draft batch or full scripts under `workbench/scripts/drafts/`, then run `python -m cyberppt script-audit <project> --input <script.md>`. Content pages must include short-article `完整文字稿` (source-topic completeness, not on-screen granularity), mandatory `文字稿取舍说明` and `证据映射`, then `上屏文字`, plus natural spoken `【演讲者备注】` for PPT notes (no slide-meta 这一页/下一页). This is a repository-wide contract. Open exit-5 escalations without `resolve-escalation` block the next Stage 01 command.
9. Before full-script approval, run `python -m cyberppt assemble-final-script <project>` to write a clean `workbench/scripts/final/script-final.md` (no 草稿/批次 wording), then audit that final path and repeat chapter review with `--level script`.
10. Before human confirmation, run `confirmation-request --kind outline|script` (must include audit summary + open questions), then `approve-stage01 --kind outline|script`. Required chapter review must be passed and hash-current. Do not generate images or PPTX until Stage 01 approval exists in `workbench/approvals/`.
11. After script approval, automatically invoke the registered `ppt-visual-structure-designer` skill in `workbench-handoff` mode. Run `prepare-visual-structure`, create the four required `visual/` artifacts, then run `visual-structure-audit`. This gate must pass before style selection or `final-script-pages`.
12. Store title/subtitle truth for template assembly in `workbench/locks/template_text/`; if dual images are supplied mid-pipeline, create this lock before template rebuild.
13. Store stage outputs under `workbench/stages/` and register every durable artifact in `workbench/artifact-ledger.json`.
14. Store page-specific attempts and resumable intermediate runs in `workbench/runs/`; use `workbench/tmp/` only for disposable scratch files.
15. Store final scripts in `workbench/scripts/final/`, QA reports in `workbench/qa/`, renders in `outputs/renders/`, and delivery files in `delivery/`.
16. Do not write new generated images or pair manifests to the repository root `images/`; keep them inside this project workspace.
""",
        encoding="utf-8",
    )
    created.extend([manifest, ledger, readme])
    return created
