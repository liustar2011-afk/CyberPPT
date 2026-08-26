# Stage 01 Editorial Delivery and On-Screen Hierarchy

## Purpose

Lightweight Stage 01 must preserve its author-first character when an agent is
working autonomously.  It must not treat a successful structural audit as a
substitute for showing the decision, the authored Outline, or the page-level
expression to the user.  A content page must also render business meaning as a
small-title group followed by complete detail sentences, rather than a flat
sequence of reusable labels.

## Scope

This change is limited to lightweight Stage 01 authoring guidance, the
autonomous-runner boundary, and the native script-quality audit.  It does not
change source registration, semantic modelling, Source Truth, Stage 02, or the
editable-text image path.

## Design

### 1. Visible editorial delivery before automation

`prepare-communication-strategy` remains the deterministic source-grounded
input.  Its existing instructions will explicitly define the required
conversation sequence:

1. show 2–3 source-supported communication-goal proposals and the
   recommendation;
2. show the author-edited chapter/page Outline and its argument chain;
3. show the detailed page scripts before treating a final script as submitted.

`run-autonomous` will state the same boundary in its operator-facing failure
message and documentation: it verifies author-supplied content; it does not
create, approve, or hide the three editorial deliveries.  It will continue to
allow an explicit autonomous contract, but that contract cannot be cited as a
reason to omit those deliveries from the conversation.

### 2. Canonical on-screen composition

For a content page whose visible material needs more than short phrases, the
canonical form is:

```
业务小标题
  完整、自然的明细句。
  另一条完整、自然的明细句。
```

Small titles name a business dimension; detail lines carry the actual
proposition.  A compact `小标题：短语` remains valid only for genuinely short
information.  Generic authoring labels such as `需求`、`措施`、`价值` are not a
substitute for either a business title or a complete proposition.

The repository page-writing skill and the script-input preparation prompt will
make this the default output form and will show the compact exception next to
it, so a writer does not flatten a page merely to satisfy source-anchor checks.

### 3. Audit role and diagnostics

The quality audit will add a narrow error for a content page that contains a
substantial flat run of labelled long details without a parent business title.
It will not require a fixed label vocabulary, a fixed number of modules, or a
specific visual layout.  Its action text will require grouping related
propositions under source-faithful business titles and retaining complete
detail sentences.

Existing checks for false parent-child relations, false parallelism, long
detail fragments, Markdown leakage, and source coverage stay intact.  The new
check is deliberately structural: it accepts any meaningful title and does
not infer the page thesis from word overlap.

## Verification

- Unit tests: a grouped title/detail page passes; a flat run of long labelled
  details raises the new issue; a compact short-phrase page remains valid.
- Prompt/skill tests: the canonical form and the visible editorial-delivery
  sequence are present.
- Regression: run the targeted script-quality and communication-strategy tests,
  then the full test suite with `PYTHONPATH=. pytest -q`.

## Non-goals

- No new approval files, manifests, receipts, hashes, or parallel directories.
- No mechanical conversion of existing scripts into labels or modules.
- No Stage 02/image-generation changes.
