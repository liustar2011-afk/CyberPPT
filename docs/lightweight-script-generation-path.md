# When to Skip the Full Stage 00/01 Pipeline

This project's outcome is now the documented default for new projects: the
`word-to-ppt-script` skill, vendored into this repo at
`vendor/word-to-ppt-script/` (see `docs/repository-layout.md`'s `vendor/`
contract), defines a `lite` mode in its `SKILL.md` (see its "Gate L — Lite
pipeline") that is the default invocation mode, with `full` mode as the
opt-in exception. What follows is the decision reasoning behind that default
and how it applied to this specific project.

`word-to-ppt-script` was vendored in as a one-time copy from the
`business-semantic-content-pipeline-v0.2.0` repo. CyberPPT now owns and
maintains its own copy under `vendor/word-to-ppt-script/`; changes made to
the upstream repo after the vendor date do not propagate here automatically
and must be pulled in deliberately if ever needed.

CyberPPT's default path — semantic understanding → semantic-argument-model →
source-truth → communication-strategy → storyline-director → outline —
is a hash-gated cascade: every stage records a sha256 of the previous stage's
current on-disk content, and re-running any upstream edit means re-running
every downstream `*-check` / `approve-*` command in sequence to re-sync the
chain. That machinery earns its cost when a deck is built by more than one
person over time, gets revised after review, or needs an audit trail proving
each page's claims trace back to specific source text.

It does not automatically earn its cost for a single-session, single-author
word-document-to-script conversion. This file documents when to skip it, based
on `projects/power-data-infrastructure-cooperation-v12-20260807/`, where the
full cascade was run once to get `outline.json` past `outline-audit`, and then
abandoned — chapter-review-audit and script-audit never ran; the actual
deliverable (`workbench/scripts/final/script-final.md`) was produced by a
hand-authored generation script reading directly from `source-truth.json` and
`outline.json`.

## Decision

Use the full Stage 00/01 pipeline when any of these hold:

- multiple people will edit the source material or the outline over time and
  need the hash bindings to know what's stale;
- the deliverable needs a durable, replayable audit trail (e.g. regulatory or
  multi-round internal review) showing which validator passed on which
  content hash;
- the outline itself is contested or needs `outline-audit`'s structural
  checks (argument-node coverage, relation declarations, source-consumption
  manifest) because the source material's argument structure is genuinely
  unclear.

Skip straight to a lightweight, hand-authored script when:

- one person is turning one Word document into one script in one sitting;
- the source document's structure (chapters, sections, argument flow) is
  already clear from the document itself — there is no real ambiguity for
  `outline-audit` to catch;
- speed and reviewability of the *content* (on-screen text, speaker notes)
  matter more than a hash-verified provenance chain.

In the skip case, use the vendored `word-to-ppt-script` skill's four-step
shape instead — extract source → page boundaries → on-screen text → speaker
notes — without running its own 12-gate pipeline either. Read
`vendor/word-to-ppt-script/references/17-density-and-coverage.md` for the
on-screen text density/coverage baseline and the nested-heading rule for
items that bundle parallel facts, and
`vendor/word-to-ppt-script/references/18-full-prose-assembly.md` for
assembling 完整文字稿 with `vendor/word-to-ppt-script/scripts/
assemble_full_prose.py` instead of naive concatenation, before writing
content.

## What a lightweight generation script should still do

Even without the hash-gate machinery, keep three things:

1. **Traceability.** Every page's on-screen content should still cite the
   source-truth record IDs it came from (`source_refs` / `detail_refs` in
   this project), even if nothing enforces it with a hash check.
2. **A quality gate, run automatically — not just a human read-through.**
   The authoritative check is the vendored, cross-project validator:
   `vendor/word-to-ppt-script/scripts/validate_script.py <final-script>.md
   --strict`, which reads its thresholds from that skill's
   `config/quality-rules.yaml` and `config/cec-formal.yaml`
   (on-screen/full-manuscript coverage ratio, minimum bullet count, absolute
   density band, banned rhetorical and defensive-coaching patterns). A
   project-local generation script may keep a fast in-process pre-check for
   immediate feedback while drafting — see
   `projects/power-data-infrastructure-cooperation-v12-20260807/workbench/scripts/drafts/generate_script_final.py::audit_script()`
   for a working example — but it must defer to `validate_script.py` as the
   source of truth, not duplicate thresholds that can drift out of sync with
   it.
3. **No dependency on files outside the CyberPPT repo.** The generation
   script should live under the project's own `workbench/scripts/`, read
   source data only from that project's `workbench/stages/01-analysis/`
   artifacts, and import shared logic only from `vendor/word-to-ppt-script/`
   inside this repo — never reach across to a sibling repo path at runtime.
   `vendor/word-to-ppt-script/` is the one deliberate exception to "read only
   from the project's own workbench/": it is shared, cross-project
   infrastructure vendored into CyberPPT itself, not an external dependency.

## What this does and does not change

`python3 -m cyberppt init` still scaffolds the full Stage 00/01 project
structure — this file does not change what `cyberppt init` generates on disk.

What it does change: for the actual script-compilation work that happens
inside a project, `vendor/word-to-ppt-script/SKILL.md`'s `lite` mode is now
the default invocation mode for a single-person, single-session compilation, per
the decision criteria above. Running the full hash-gated cascade to
completion (`outline-audit` through `script-audit`) is the exception, not the
default, and should be a deliberate choice made and documented (e.g. in the
project's own README or workbench notes) when one of the "Use the full
Stage 00/01 pipeline when" conditions actually holds.
