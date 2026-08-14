# `run-autonomous` contract

`python -m cyberppt run-autonomous /absolute/path/contract.json` composes the existing lightweight Stage 01 and Stage 02 gates. It verifies authored artifacts; it does not generate semantic interpretation, professional page authoring, or visual decisions by template, and it does not replace the conversation delivery of the communication goal, author-edited Outline, or detailed pages. Those remain required inputs and cause a fail-closed report if missing.

An Outline is accepted only when it declares `editorial_authoring_mode: author_driven` and `editorial_authoring_status: author_edited`; the deterministic candidate is rejected even if its structural audit otherwise passes. Page authoring is verified from the official Markdown drafts under `workbench/scripts/drafts/`: each content page must contain complete prose, on-screen copy, visual structure, speaker notes, evidence mapping, and the three-bucket selection rationale. The lightweight route never requires or writes `page-script-authoring.json`.

```json
{
  "schema_version": 1,
  "mode": "autonomous_lightweight",
  "project": "/absolute/path/to/project",
  "source": {
    "allow": ["/absolute/path/to/project/source/material.docx"],
    "deny_prefixes": ["/absolute/path/to/old-project/workbench"]
  },
  "required": {
    "stage01": true,
    "stage02": true,
    "style_id": 9,
    "production_mode": "editable-overlay",
    "images": true,
    "prompt_files": true,
    "image_qa": true
  }
}
```

The source directory must contain exactly the `source.allow` files (the repository placeholder `source/.gitkeep` is ignored). The runner also rejects saved workbench artifacts that name a denied prefix. A failed run writes `workbench/stages/00-autonomous/run-report.json` with the first failed gate and blocking artifact.

The visual stage is deliberately two-step: the runner prepares the handoff, then stops at `visual-structure-authoring` until the registered `ppt-visual-structure-designer` has authored `visual/visual-design-decisions.json`. On resume it compiles the decision package, records execution, audits it, and rebuilds the current visual prompt package. The explicit autonomous contract is the only authority that lets the downstream generator use the current audited visual prompts without fabricating per-page user-approval records.

It writes `status: completed` only after the current script audit, Stage 02 handoff, visual execution receipt, visual structure audit, every expected content-page image pair, passed full-image text QA, and a hash-bound actual ImageGen send record for every generated variant.

Use `--skip-image-generation` only to diagnose the chain before ImageGen. When the contract requires images, that option returns a failed `image-production` gate and cannot produce a completed report.

`--resume` reuses current artifacts but never skips validation: the command reruns the source boundary and every upstream gate before continuing.
