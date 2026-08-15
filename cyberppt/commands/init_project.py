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
status:
  stage: initialized
  notes: "Authoritative Stage 01 uses canonical Markdown drafts/final script as the source of truth; lightweight controls omit approval ledgers and hash-freshness state."
"""


def _readme(project_name: str) -> str:
    return f"""# {project_name}

CyberPPT authoritative Stage 01 workspace (lightweight controls).

## Flow

1. Put the only authoritative source materials in `source/`; run `prepare-source-map` and one `source-map-check`.
2. Run `prepare-semantic-understanding`, complete the canonical semantic understanding, then run one `semantic-check`. Preserve source-native thesis, actors, status, argument roles, weights, relations, concept distinctions and source gaps.
3. Build canonical `workbench/stages/01-analysis/source-truth.json`; run one `source-truth-audit`. Source Truth remains factual authority and never stores page assignments.
4. Run `prepare-communication-strategy`. The agent must analyze the source and present one source-faithful communication-goal direction; do not offer multiple options or ask blank audience/scenario/action questions. User wording may constrain audience, use, or delivery, but cannot become a source fact or page conclusion without source support.
5. Run `prepare-outline-input --communication-goal <selected-goal>`. The command preserves one source-faithful Storyline Director route inside the authoring task without creating a Director gate. Prefer `source_logic_focused` when the source has an explicit argument sequence; preserve the source-native thesis and major progression while selectively compressing repetition and detail. Present the chapter/page outline to the user before drafting details.
6. Run `outline-audit` once before presenting the outline. Fix only affected outline content; do not create attempts or escalation state.
7. Run `prepare-page-script-input` for all pages or the current chapter/page. Write the authoritative chapter Markdown drafts directly and present detailed page content to the user.
8. Run `assemble-final-script`, then one final `script-audit`. The drafts and assembled final script are authoritative Stage 01 artifacts; present the final script and wait for confirmation.

The authoritative lightweight path creates no page-script-authoring JSON, approval JSON, interaction state, generation receipt, retry attempt, escalation, artifact ledger or hash-freshness gate. `workbench/scripts/drafts/` and `workbench/scripts/final/script-final.md` are the canonical Stage 01 writing artifacts.
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
            keep.write_text("", encoding="utf-8")
            created.append(keep)

    project_name = root.name
    manifest.write_text(_project_manifest(project_name), encoding="utf-8")
    readme.write_text(_readme(project_name), encoding="utf-8")
    created.extend([manifest, readme])
    return created
