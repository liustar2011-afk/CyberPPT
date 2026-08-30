"""Create a CyberPPT project workspace (lightweight scaffold)."""

from __future__ import annotations

from pathlib import Path


PROJECT_DIRS = [
    "source",
    "script",
    "script/.cache",
    "script/dist",
]


def _project_manifest(name: str, profile: str) -> str:
    strict_directories = "" if profile == "script" else """  source_foundation: workbench/source-foundation
  semantic_argument_model: workbench/stages/00-semantic-understanding/semantic-argument-model.json
  source_truth: workbench/stages/01-analysis/source-truth.json
"""
    return f"""name: {name}
workflow: cyberppt
schema: cyberppt.project.v1
mode: lightweight
profile: {profile}
authority_mode: authoritative
directories:
  source: source
  script_engine_project: script
  source_index: script/.cache/source-index.json
  foundation: script/foundation.json
  deck_plan: script/deck-plan.json
  final_script_md: script/dist/final-script.md
  final_script_json: script/dist/final-script.json
{strict_directories}status:
  stage: initialized
  live: false
  notes: "Initialization metadata only. Run `python -m cyberppt status <project>` for live Stage 01 and Stage 02 status."
"""


def _readme(project_name: str, profile: str) -> str:
    if profile != "script":
        return f"""# {project_name}

CyberPPT Stage 01 workspace (`{profile}` profile).

## Flow

This profile is reserved for contracts, regulation, fact-by-fact verification,
full Source Truth work, or legacy migration. Follow
`.agents/skills/cyberppt-source-foundation/SKILL.md`:

1. Build and validate Source Foundation once.
2. Complete business semantic understanding once.
3. Run `project-foundation` as a mechanical projection into `script/foundation.json`.
4. Continue with `cyberppt-script-workflow` for the plan and author stages.

Reuse validated upstream artifacts. Rerun semantic understanding only when the
source changed or the existing semantic authority failed validation.
"""

    return f"""# {project_name}

CyberPPT Stage 01 workspace (`script` profile).

## Flow

1. Put the only authoritative source materials in `source/`.
2. Run `.venv/bin/python3 -m cyberppt prepare-source-context <project>` once.
3. Run `.venv/bin/python3 -m cyberppt prepare-script-foundation <project> --profile script` and complete UNDERSTAND once in `script/foundation.json`.
4. Follow `cyberppt-script-workflow` to create the lean `script/deck-plan.json`, stop at **脚本规划待确认**, then author `script/dist/final-script.md` and stop at **最终脚本已生成**.
5. After the final script is locked, run `prepare-stage02-handoff` and continue to Stage 02.

For this profile, do not run `prepare-source-map`, `prepare-semantic-understanding`,
`semantic-check`, Source Truth compilation, or `project-foundation`. Those commands
belong to explicit `strict/legacy` work.

AUTHOR loads the document thesis and structure once per deck, then reads only the
source evidence bound to the current page and its adjacent-page scope. Critic and
Rewrite operate on that authored page and its bound evidence; they do not rerun
whole-document semantic understanding.

The three authoritative Stage 01 content artifacts are `script/foundation.json`,
`script/deck-plan.json`, and `script/dist/final-script.md`.
"""


def init_project(path: Path, force: bool = False, *, profile: str = "strict") -> list[Path]:
    if profile not in {"script", "strict", "legacy"}:
        raise ValueError("profile must be script, strict, or legacy")
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
    manifest.write_text(_project_manifest(project_name, profile), encoding="utf-8", newline="\n")
    readme.write_text(_readme(project_name, profile), encoding="utf-8", newline="\n")
    created.extend([manifest, readme])
    return created
