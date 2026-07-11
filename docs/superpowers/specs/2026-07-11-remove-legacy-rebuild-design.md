# Remove Legacy Editable Rebuild

## Objective

Remove CyberPPT's legacy editable-rebuild capability. The only supported
production delivery route will be `full_image_ppt` through `produce prepare`,
`produce assemble`, and `produce verify`.

## Scope

Delete the executable legacy OCR, dual-image overlay, semantic-plan, and
template-rebuild runtime; their command routing; dedicated tests and fixtures;
and current documentation or project-scaffold references. Remove the legacy
Stage 03/04 workspace directories from newly initialized projects.

Historical design and planning documents remain as records of prior decisions;
they must not be presented as current workflow documentation.

## Design

1. Remove the legacy rebuild runtime and its direct support modules from
   `scripts/dual_image_overlay/`, including the editable overlay engine,
   template rebuild wrapper, OCR-forensics-only components, and rebuild-mode
   helpers.
2. Remove CLI, package-script, Makefile, initialization, and validation paths
   that expose or require those modules. Keep full-image assembly and its
   quality gates unchanged.
3. Remove legacy-specific tests, synthetic fixtures, and test assertions;
   replace them with narrow contract tests that assert no current command or
   scaffold exposes an editable-rebuild route.
4. Rewrite active workflow documentation (`README.md`, `SKILL.md`, repository
   layout, references) to describe one production route. Historical plans and
   specs are explicitly out of the runtime/documentation contract.

## Acceptance Criteria

- No supported CLI, Makefile, npm script, or project scaffold advertises or
  invokes OCR/template-rebuild/editable-overlay behavior.
- A new project has no legacy Stage 03/04 rebuild directories.
- The full-image CLI help and focused production-contract tests pass.
- Repository search finds legacy terms only in intentionally retained history
  or git metadata, not in active source, tests, or user-facing documentation.

## Risks and Handling

`resolve_rebuild_mode` has a high upstream impact because two legacy runners
and their readiness builder share it. Delete those connected callers in the
same change, then verify the remaining full-image production flow directly.
Existing user project artifacts are not modified.
