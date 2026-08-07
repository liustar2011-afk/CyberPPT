# 18. Assembling 完整文字稿 (Full Manuscript) — Avoiding the "Pile of Facts" Defect

`完整文字稿` is not just a container for the raw source_refs a page consumes.
It is the page's argument in prose, and `上屏文字` is supposed to be its
abbreviation (see `17-density-and-coverage.md`). If 完整文字稿 itself is an
unstructured pile of source-truth statements, the abbreviation inherits the
same flatness — there is no logical skeleton to abbreviate *from*.

## The defect this fixes

The naive approach is:

```python
full_prose = "".join(records[r]["statement"] for r in unit_refs)
```

Plain concatenation, in whatever order `unit_refs` happens to list them. This
produces two concrete, observed problems:

1. **Orphaned enumeration markers.** Formal source documents commonly write
   clauses as "一是……二是……三是……". A page's `content_units` frequently pull
   only a subset of that original list — item 1 may belong to an earlier
   page's argument. Concatenating verbatim reproduces the *document-global*
   numbering, so a page can open mid-list ("二是……三是……四是……") with "一是"
   never appearing on that page, or skip a number outright
   ("一是……二是……四是……"). Both read as an unexplained fragment.
2. **No framing.** A bare, un-introduced list of clauses reads as a pile of
   facts even when each clause is individually well-formed and accurate.

## The fix

**When an LLM agent is compiling the script (the normal case), write
完整文字稿 yourself.** Read the page's source-truth records — statement,
role, weight — and compose connected argument prose: background/evidence
before judgment before mechanism before recommendation before boundary, with
real transition language ("基于此""由此""需要说明的是"), not a restatement
of whatever enumeration markers the source document happened to use. This is
ordinary paragraph writing applied to a well-defined set of facts, not a
mechanical transform — treat it with the same judgment as any other prose you
write for this skill, and do not introduce a claim, number or entity the
records do not support (§8, no-fabrication rule).

**When no LLM agent is present** — a scheduled unattended regeneration, a
pure-script CI run, or a generation script invoked without an agent in the
loop — there are two fallback tiers, in preference order:

1. `scripts/llm_draft_page.py` calls the Anthropic API directly to draft
   完整文字稿 (and optionally 上屏文字) with the same argument-writing and
   no-fabrication instructions an agent would follow. It requires
   `ANTHROPIC_API_KEY` and the `anthropic` package, and its output still has
   to pass `scripts/validate_script.py --strict` — it is not a separate,
   lower quality bar, just an automated way to get agent-quality prose when
   no agent is actually running the compilation.
2. `scripts/assemble_full_prose.py`'s `assemble_full_prose(records)` is the
   last-resort, no-network, no-API-key fallback. It cannot write an
   argument, but it mechanically fixes the two most damaging symptoms
   without needing judgment or an API call:

- strips each statement's original enumeration marker and re-issues fresh,
  page-local, contiguous markers (starting at 一是) when at least half the
  page's records originally carried one — so the list is self-contained and
  never opens mid-sequence;
- prepends one framing sentence, chosen from a small template table keyed by
  the page's dominant `semantic_argument_role` (`references/02-source-compilation.md`
  already requires this classification at Gate 1 — this step spends it
  instead of discarding it after Gate 1 ends);
- stable-sorts records first by `semantic_argument_weight`
  (core > supporting > detail > constraint), then by a fixed
  `semantic_argument_role` priority: thesis/positioning, then
  foundation/evidence/definition, then architecture/capability/operation/
  cooperation, then recommendation, then boundary/constraint. On pages where
  every record shares one role and weight — the common case — this is a
  no-op (stable sort preserves original order). On pages that do mix roles,
  it orders the prose as background/evidence before judgment before
  mechanism before recommendation before caveats, which is a more legible
  default than whatever order `source_refs` happened to list them in.

It deliberately does **not** auto-generate a closing synthesis sentence.
Writing a new sentence that paraphrases "what these facts add up to" risks
asserting a conclusion beyond what source-truth states, which conflicts with
this skill's no-fabrication rule (§8, Stop and repair conditions). If a
page's argument genuinely needs an explicit close, write it by hand and keep
it traceable to a specific record — don't let the assembly function invent
one.

## When this doesn't fire

If a page's records carry no `semantic_argument_role` /
`semantic_argument_weight` fields (older source-truth extractions, or a
lite-mode run that skipped full Gate 1 classification), the function
degrades to the same ordering as naive concatenation, plus marker
normalization if markers are present in the raw statements — it never
errors or drops content for missing fields.

## Where this runs

Wherever `完整文字稿` is produced — in `full` mode that's Gate 6 (Final
assembly); in `lite` mode that's Gate L step 4 (Final script assembly) —
default to writing it yourself. Reach for
`vendor/word-to-ppt-script/scripts/assemble_full_prose.py` only in the
no-agent case described above. Either way, run
`scripts/validate_script.py --strict` afterward: density, coverage,
banned-pattern and defensive-coaching checks apply identically to
agent-written and mechanically-assembled prose, so writing it yourself is
not an exemption from the quality gate.
