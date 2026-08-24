# Boundary Contract: Script Engine → CyberPPT Stage 02

## Required downstream input

Stage 02 receives one canonical final script artifact by path:

```text
final-script.md
```

A machine-readable mirror may also be supplied:

```text
final-script.json
```

## Stage 02 may depend on

- stable page IDs;
- page type;
- title;
- page mission / core message;
- final onscreen copy;
- speaker notes;
- visual thesis and semantic relationships when provided;
- source trace references when provided.

## Stage 02 must not depend on

- `foundation.json` internal structure;
- `deck-plan.json` internal structure;
- semantic caches;
- audit reports;
- critique drafts;
- authoring iteration state;
- human-gate bookkeeping;
- Source Truth projection files;
- Script Engine-specific Skill names.

## Compatibility rule

If the current CyberPPT Stage 02 expects a legacy final-script layout, `adapters/cyberppt-stage02/` performs the translation. The adapter is replaceable and versioned independently from the authoring engine.

## Versioning

Every machine-readable delivery should include:

```json
{
  "contract": "cyberppt.final-script",
  "version": "1.0"
}
```

Breaking changes require a major version bump. Stage 02 integration should bind to the contract version, not to Script Engine internals.
