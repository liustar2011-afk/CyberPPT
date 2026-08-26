"""Create a CyberPPT project workspace (lightweight scaffold)."""

from __future__ import annotations

from pathlib import Path


PROJECT_DIRS = [
    "source",
    "workbench",
    "workbench/stages",
    "workbench/stages/00-source-map",
    "workbench/stages/00-semantic-understanding",
    "workbench/stages/01-analysis",
    "workbench/scripts",
    "workbench/scripts/drafts",
    "workbench/scripts/final",
    # script_engine (vendored CyberPPT-Script) project workspace: PLAN/AUTHOR
    # consume workbench/stages/01-analysis/source-truth.json (via
    # `project-foundation`) and produce script/deck-plan.json and
    # script/dist/final-script.md, which prepare-stage02-handoff can consume
    # directly with --script.
    "script",
    "script/sources",
    "script/.cache",
    "script/dist",
]


def _project_manifest(name: str) -> str:
    return f"""name: {name}
workflow: cyberppt
schema: cyberppt.project.v1
mode: lightweight
authority_mode: authoritative
directories:
  source: source
  workbench: workbench
  stages: workbench/stages
  stage_source_map: workbench/stages/00-source-map
  source_registry: workbench/stages/00-source-map/source-registry.json
  source_units: workbench/stages/00-source-map/source-units.jsonl
  source_heading_tree: workbench/stages/00-source-map/source-heading-tree.json
  source_map: workbench/stages/00-source-map/source-map.md
  source_map_audit: workbench/stages/00-source-map/source-map-audit.json
  stage_semantic_understanding: workbench/stages/00-semantic-understanding
  semantic_understanding: workbench/stages/00-semantic-understanding/semantic-understanding.md
  semantic_argument_model: workbench/stages/00-semantic-understanding/semantic-argument-model.json
  stage_analysis: workbench/stages/01-analysis
  source_truth: workbench/stages/01-analysis/source-truth.json
  outline: workbench/stages/01-analysis/outline.json
  scripts: workbench/scripts
  script_drafts: workbench/scripts/drafts
  final_scripts: workbench/scripts/final
  script_engine_project: script
  foundation: script/foundation.json
  deck_plan: script/deck-plan.json
  final_script_md: script/dist/final-script.md
  final_script_json: script/dist/final-script.json
status:
  stage: initialized
  notes: "Authoritative Stage 01 uses canonical Markdown drafts/final script as the source of truth; lightweight controls omit approval ledgers and hash-freshness state."
"""


def _readme(project_name: str) -> str:
    return f"""# {project_name}

CyberPPT authoritative Stage 01 workspace (lightweight controls).

## Flow

**Understand** (source-material parsing, unchanged):

1. Put the only authoritative source materials in `source/`; run `prepare-source-map` and one `source-map-check`.
2. Run `prepare-semantic-understanding`, complete the canonical semantic understanding, then run one `semantic-check`. Preserve source-native thesis, actors, status, argument roles, weights, relations, concept distinctions and source gaps.
3. Build canonical `workbench/stages/01-analysis/source-truth.json`; run one `source-truth-audit`. Source Truth remains factual authority and never stores page assignments.

**Plan and author** (vendored `script_engine`, see `.agents/skills/cyberppt-script-workflow/SKILL.md`):

4. Run `project-foundation` to mechanically project the validated Source Truth into `script/foundation.json` (no re-analysis; every fact keeps its source refs).
5. Follow `cyberppt-script-workflow` to reach `script/deck-plan.json` (stop at **脚本规划待确认** for user confirmation) and then `script/dist/final-script.md` (stop at **最终脚本已生成**). `cyberppt-script lint`/`audit-foundation`/`audit-plan` are diagnostics run after writing, not per-page blocking gates.

**Hand off to Stage 02**:

6. Run `prepare-stage02-handoff --script script/dist/final-script.md`, then `stage02-handoff-check`.

The authoritative lightweight path creates no page-script-authoring JSON, approval JSON, interaction state, generation receipt, retry attempt, escalation, artifact ledger or hash-freshness gate. `script/foundation.json`, `script/deck-plan.json` and `script/dist/final-script.md` are the three authoritative Stage 01 planning/writing artifacts.
"""


def init_project(path: Path, force: bool = False) -> list[Path]:
    root = path.expanduser().resolve()
    created: list[Path] = []
    manifest = root / "manifest.yml"
    readme = root / "README.md"
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
            keep.write_text("", encoding="utf-8", newline="\n")
            created.append(keep)

    project_name = root.name
    manifest.write_text(_project_manifest(project_name), encoding="utf-8", newline="\n")
    readme.write_text(_readme(project_name), encoding="utf-8", newline="\n")
    created.extend([manifest, readme])
    return created
