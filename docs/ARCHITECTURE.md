# Script Engine Architecture

## Goal

Provide a focused, high-quality PPT script-generation engine with a small authority surface and a stable downstream contract.

## Design principles

1. Authoring complexity belongs in AUTHOR.
2. `foundation.json` and `deck-plan.json` are private implementation details.
3. `dist/final-script.md` is the stable downstream artifact.
4. Compatibility is an adapter concern.
5. Whole-deck first, page editing second.
6. Each deck task is a project (`projects/<slug>/`), not a mutation of shared repo-root state — this keeps concurrent/past tasks inspectable and lets progress be derived from disk rather than remembered.

## Human gates

- Gate A — Deck Plan
- Gate B — Final Script
