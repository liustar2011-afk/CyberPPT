# When to Skip the Full Stage 00/01 Pipeline

## Interaction belongs in the conversation

The lightweight path does not change or duplicate the project's draft files.
It reduces the control layer around the existing Source Truth, Outline,
chapter scripts and final script.

The agent pauses in the conversation to present source-grounded communication
goal recommendations, present the chapter/page outline, present detailed page
content, and present the final manuscript. At the first pause, run
`python -m cyberppt prepare-communication-strategy <project> --lightweight`,
read its source outline and decision evidence, propose 2-3 materially different
options, and mark one as recommended. Do not ask the user to invent the
audience, scenario, or desired action from a blank slate. Feedback is applied
directly to the existing Outline or chapter scripts. These pauses must not be
represented by checkpoint Markdown, approval JSON, hashes, receipts, attempts,
manifests or another run directory.

Default internal work is limited to one source-registration check, one
semantic check, one Source Truth check, one Outline check, scoped checks while
editing, and one whole-script check after assembly. These lightweight checks
retain the substantive business validators but do not persist gates, attempts,
receipts, escalation or audit state. The full audited pipeline remains
available only when the user explicitly requests it or the deliverable
genuinely needs a multi-author or regulatory audit trail.

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

CyberPPT retains a full controlled path — semantic understanding →
semantic-argument-model → source-truth → communication-strategy →
storyline-director → outline — for multi-author and regulated work. The
lightweight default uses the same business artifacts and validators through
the existing `python -m cyberppt` commands, but removes the hash-gated cascade,
approval files, attempts, escalation and audit persistence.

It does not automatically earn its cost for a single-session, single-author
word-document-to-script conversion. An earlier project exposed the cost by
stopping partway through the controlled cascade; that historical workaround
is not the current design. The supported replacement is now the official
`python -m cyberppt ... --lightweight` chain described here.

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

Use the lightweight official Stage 01 path when:

- one person is turning one Word document into one script in one sitting;
- the source document's structure can be resolved by one semantic pass and
  one lightweight Outline check without a persistent retry/escalation chain;
- speed and reviewability of the *content* (on-screen text, speaker notes)
  matter more than a hash-verified provenance chain.

In the lightweight case, keep the repository-native chain: source map →
semantic understanding → Source Truth → source-grounded communication goal →
embedded storyline/Outline reasoning → chapter scripts → final script. Use
the existing lightweight CLI flags; do not substitute a project-local
generation script or a manual parallel workflow. Read
`vendor/word-to-ppt-script/references/17-density-and-coverage.md` for the
on-screen text density/coverage baseline and the nested-heading rule for
items that bundle parallel facts, and
`vendor/word-to-ppt-script/references/18-full-prose-assembly.md` for
assembling 完整文字稿 with `vendor/word-to-ppt-script/scripts/
assemble_full_prose.py` instead of naive concatenation, before writing
content.

## What the lightweight Stage 01 path must still do

Even without the hash-gate machinery, keep three things:

1. **Traceability.** Every page's on-screen content should still cite the
   source-truth record IDs it came from (`source_refs` / `detail_refs` in
   this project), even if nothing enforces it with a hash check.
2. **One check at each semantic boundary, with no repeated audit chain.** Run
   `semantic-check --lightweight`, `source-truth-audit --lightweight`, and
   `outline-audit --lightweight` once when their corresponding business
   artifact is ready. After assembly run
   `python -m cyberppt script-audit <project> --input <final-script>.md
   --lightweight`. It uses the existing Outline and Source Truth, but skips
   approval/hash gates and writes no audit, attempt, receipt, escalation or
   artifact-ledger state. The vendored standalone equivalent remains
   `vendor/word-to-ppt-script/scripts/validate_script.py <final-script>.md
   --strict` for use outside CyberPPT.
3. **No dependency on files outside the CyberPPT repo.** Chapter drafts live
   under the project's own `workbench/scripts/drafts/` and read source data
   only from that project's registered source, semantic model, Source Truth
   and Outline. Shared logic may come only from code vendored inside this
   repo — never reach across to a sibling repo path at runtime.
   `vendor/word-to-ppt-script/` is the one deliberate exception to "read only
   from the project's own workbench/": it is shared, cross-project
   infrastructure vendored into CyberPPT itself, not an external dependency.

For Stage 01 and the per-page script gate, an affirmative approval records
workflow intent instead of freezing the approved file bytes. Stage 01 approval
records contain no SHA-256 bindings. Artifact hashes may still be written to
audits and manifests for troubleshooting, but an
in-place edit to a staged final script or ImageGen prompt does not force a
stage/approve cycle. Missing or negative approval, missing files, malformed
scripts, failed content checks, and missing generated assets remain blocking.

The Stage 02 handoff is also deliberately not hash-bound. Its source bindings
record paths only; handoff audits verify that those files exist and that the
handoff schema, page coverage, roles, required text, and body canvas are valid.
Changing the handoff or an upstream script does not invalidate an already
passed visual-structure report merely because a SHA-256 value changed.

## What this does and does not change

`python -m cyberppt init <project> --lightweight` scaffolds only the source,
Stage 00/01 business-artifact directories, chapter drafts and final-script
directory. It does not create approval, decision, attempt, run, ledger or
Stage 02 directories. Plain `init` retains the complete controlled scaffold.

For a single-person, single-session compilation, the existing CyberPPT
commands with `--lightweight` are the default. The full controlled cascade is
the exception and must be a deliberate choice when one of the "Use the full
Stage 00/01 pipeline" conditions actually holds.
