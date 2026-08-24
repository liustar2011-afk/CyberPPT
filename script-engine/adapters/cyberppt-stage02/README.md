# CyberPPT Stage 02 Adapter

This directory is the compatibility boundary between the standalone Script Engine and the existing CyberPPT Stage 02 implementation.

## Rule

Stage 02 compatibility logic belongs here. It must not leak back into UNDERSTAND, PLAN, or AUTHOR.

## Inputs

Preferred:

- `dist/final-script.md`
- optionally `dist/final-script.json`

## Output

A Stage 02-compatible script or handoff artifact required by the host CyberPPT repository.

## Migration strategy

1. Keep the existing Stage 02 unchanged initially.
2. Translate the new final-script contract at this boundary.
3. Once Stage 02 can consume `cyberppt.final-script@1.0` directly, remove most of the adapter.

The adapter is intentionally replaceable. The Script Engine remains usable without CyberPPT Stage 02.
