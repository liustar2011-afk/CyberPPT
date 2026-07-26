# Stage 01 Prompt Chain Integrity Implementation Plan

**Goal:** Make the approved Stage 01 manuscript the traceable, approved source of every ImageGen prompt used by the Stage 02 manifest.

**Scope:** Reuse existing Python commands and project artifacts. Do not add services, databases, or a second workflow.

1. Make one `ScriptPage`-based prompt compiler the shared implementation for review handoff and manifest generation; add equality tests.
2. Record final-script, outline, and Source Truth hashes in Stage 01 script approval; require a matching approval before the manifest path runs.
3. Require an approved per-slide ImageGen prompt record whose hash matches the prompt placed in the manifest.
4. Record source-file paths, hashes, and basic extraction counts in Source Truth; validate the receipt during Source Truth audit.
5. Run focused unit/command tests and a small project-chain regression.
