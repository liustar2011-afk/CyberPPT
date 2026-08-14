# Outline Candidate Audit Gate Design

## Goal

Prevent deterministic Stage 01 candidate outlines from being reported as dozens of content-quality failures before professional authoring has begun.

## Decision

When an outline declares `editorial_authoring_mode: author_driven` and `editorial_authoring_status: mechanical_draft`, `audit_outline()` returns only `OUTLINE_AUTHOR_EDIT_REQUIRED`. The candidate remains a complete source inventory for the author, but it is not treated as a submitted formal outline.

After `editorial_authoring_status` becomes `author_edited`, the existing complete audit remains unchanged: source coverage, P2 use, evidence roles, page density, semantic derivation, and argument-flow checks all run.

## Validation

Add a regression test with a multi-node candidate that would otherwise trigger disposition and P2 errors. Assert that the candidate produces only the author-edit requirement, then assert that a formally edited outline still runs the ordinary validations.
