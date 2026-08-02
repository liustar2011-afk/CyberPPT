"""Create a CyberPPT project workspace."""

from __future__ import annotations

import json
from pathlib import Path

from cyberppt.semantic_understanding import semantic_template


PROJECT_DIRS = [
    "source",
    "review",
    "visual",
    "workbench",
    "workbench/stages",
    "workbench/stages/00-semantic-understanding",
    "workbench/stages/00-communication-strategy",
    "workbench/stages/00-storyline-director",
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
    "workbench/decisions",
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
  stage_semantic_understanding: workbench/stages/00-semantic-understanding
  semantic_understanding: workbench/stages/00-semantic-understanding/semantic-understanding.md
  semantic_understanding_audit: workbench/stages/00-semantic-understanding/semantic-understanding-audit.json
  semantic_argument_model: workbench/stages/00-semantic-understanding/semantic-argument-model.json
  semantic_model_input: workbench/stages/00-semantic-understanding/semantic-model-input.md
  semantic_generation_receipt: workbench/stages/00-semantic-understanding/semantic-generation-receipt.json
  semantic_approval: workbench/approvals/semantic-understanding-approved.json
  stage_communication_strategy: workbench/stages/00-communication-strategy
  communication_strategy: workbench/stages/00-communication-strategy/communication-strategy.json
  communication_strategy_audit: workbench/stages/00-communication-strategy/communication-strategy-audit.json
  communication_strategy_confirmation: workbench/stages/00-communication-strategy/communication-strategy-confirmation.md
  communication_strategy_approval: workbench/approvals/communication-strategy-approved.json
  stage_storyline_director: workbench/stages/00-storyline-director
  storyline_director_input: workbench/stages/00-storyline-director/storyline-director-input.md
  storyline_director: workbench/stages/00-storyline-director/storyline-director.json
  storyline_director_audit: workbench/stages/00-storyline-director/storyline-director-audit.json
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
  decisions: workbench/decisions/user-decisions.json
  runs: workbench/runs
  archive: workbench/archive
  tmp: workbench/tmp
  qa: workbench/qa
  outputs: outputs
  delivery: delivery
gates:
  semantic_understanding: required
  communication_strategy: required
  storyline_director: required
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
    semantic_understanding = root / "workbench" / "stages" / "00-semantic-understanding" / "semantic-understanding.md"
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
    decisions = root / "workbench" / "decisions" / "user-decisions.json"
    if not decisions.exists():
        decisions.write_text(
            json.dumps({"schema": "cyberppt.user_decisions.v1", "decisions": []}, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        created.append(decisions)
    if not semantic_understanding.exists():
        semantic_understanding.write_text(semantic_template(), encoding="utf-8")
        created.append(semantic_understanding)
    readme.write_text(
        f"""# {project_name}

CyberPPT project workspace.

## Flow

1. Put source materials in `source/`.
2. Run `python -m cyberppt prepare-semantic-understanding <project>` to compile the complete, source-hashed model task at `semantic-model-input.md`. Execute that fixed task with the chosen model and write only `semantic-understanding.md`; the artifact must include the marked `cyberppt.semantic_argument_model.v1` JSON block containing the source thesis, chapter/subchapter nodes, evidence-backed argument relations, MECE rules, statuses, actors, and source gaps.
3. Record the execution with `record-semantic-generation --executor <surface> --model <model>`, run `semantic-check`, then obtain human confirmation with `approve-semantic-understanding`. Source Truth is blocked until all three receipts are current.
4. Before Outline authoring, run `prepare-communication-strategy`, complete the 2-3 audience-specific reporting-direction options in `communication-strategy.json`, including source-anchored `audience_concerns`, and run `communication-strategy-check`. Show `communication-strategy-confirmation.md` to the user and record the selected option with `approve-communication-strategy --option <option_id>`. The choice is also written to `workbench/decisions/user-decisions.json`; the Outline is blocked until this human choice is current and consumed by the Director.
5. Use the approved communication strategy's architecture mode and structure principle. Solution architecture remains the default for research, construction, implementation, and initiation materials; consulting architecture is used only when the approved user choice explicitly selects it.
6. Build `source-truth.json` from the approved semantic understanding, bind both semantic and source-bundle SHA-256 values at the JSON root, then run `python -m cyberppt source-truth-audit <project> --input <source-truth.json>`. The JSON is authoritative; the command renders `00-source-analysis.md`, preserves attempts, rejects flattened long-form priority inventories, and changes extraction direction when coverage is incomplete.
7. After Source Truth passes, run `prepare-storyline-director`, complete `storyline-director.json`, and run `storyline-director-check`. The Director must bind the complete approved semantic understanding, audience concern contract, source-grounded chapter missions, and user-decision consumption receipt. It does not write pages and may organize evidence but may not replace source meaning. Outline authoring is blocked until this hash-current internal gate passes.
8. New formal solution projects use `argument_contract_mode: strict`, `editorial_control_mode: required`, `storyline_contract_mode: required`, and `cyberppt.outline.v2`. Copy the Director contract and hash exactly. Build each page from one concrete storyline role plus source-grounded `core_message`, `content_units`, and `content_relations`; page types and claim taxonomies do not determine the page meaning. Every content page must declare specific transitions from the previous question and to the next, one concrete `audience_question`, approved `audience_concern_ids`, `audience_relevance`, a non-empty `must_not_include` list, and `split_risk`. Preserve all source evidence, but never give it equal page weight: P0 is page-forming, P1 supports grouped modules, and P2 remains in `detail_refs` for prose, notes, parameters, or traceability.
9. Preserve the source material's actual meanings and relations, while selecting and organizing evidence around the approved theme. Source sections are not a page inventory; a story chain may be used only when supported by the material, must remain bound to Source Truth, and is never a mandatory chapter template.
10. Only after the Director gate passes or a recorded escalation decision (`resolve-escalation --gate source_truth`), audit the Stage 01 outline with `python -m cyberppt outline-audit <project> --input <outline.json> --source-truth <source-truth.json>`.
11. Run `python -m cyberppt prepare-chapter-review <project> --level outline`, complete the Markdown reviews under `review/`, then run `python -m cyberppt chapter-review-audit <project> --level outline`.
12. Draft batch or full scripts under `workbench/scripts/drafts/`, then run `python -m cyberppt script-audit <project> --input <script.md>`. Content pages must include short-article `完整文字稿` (source-topic completeness, not on-screen granularity), mandatory `文字稿取舍说明` and `证据映射`, then `上屏文字`, plus natural spoken `【演讲者备注】` for PPT notes (no slide-meta 这一页/下一页). This is a repository-wide contract. Open exit-5 escalations without `resolve-escalation` block the next Stage 01 command.
13. Before full-script approval, run `python -m cyberppt assemble-final-script <project>` to write a clean `workbench/scripts/final/script-final.md` (no 草稿/批次 wording), then audit that final path and repeat chapter review with `--level script`.
14. Before human confirmation, run `confirmation-request --kind outline|script` (must include audit summary + open questions), then `approve-stage01 --kind outline|script`. Required chapter review must be passed and hash-current. Do not generate images or PPTX until Stage 01 approval exists in `workbench/approvals/`.
15. After script approval, automatically invoke the registered `ppt-visual-structure-designer` skill in `workbench-handoff` mode. Run `prepare-visual-structure`, create the four required `visual/` artifacts, then run `visual-structure-audit`. This gate must pass before style selection or `final-script-pages`.
16. Store title/subtitle truth for template assembly in `workbench/locks/template_text/`; if dual images are supplied mid-pipeline, create this lock before template rebuild.
17. Store stage outputs under `workbench/stages/` and register every durable artifact in `workbench/artifact-ledger.json`.
18. Store page-specific attempts and resumable intermediate runs in `workbench/runs/`; use `workbench/tmp/` only for disposable scratch files.
19. Store final scripts in `workbench/scripts/final/`, QA reports in `workbench/qa/`, renders in `outputs/renders/`, and delivery files in `delivery/`.
20. Do not write new generated images or pair manifests to the repository root `images/`; keep them inside this project workspace.
""",
        encoding="utf-8",
    )
    created.extend([manifest, ledger, readme])
    return created
