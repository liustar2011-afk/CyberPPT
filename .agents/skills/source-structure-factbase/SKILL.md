---
name: source-structure-factbase
description: Use when normalized Markdown source materials need source-preserving structure extraction, heading hierarchy recovery, evidence line mapping, or a traceable source-assertion fact base before semantic analysis, solution drafting, knowledge modeling, or PPT compilation.
---

# Source Structure Factbase

Turn one normalized Markdown source into deterministic `structure.json` and `fact-base.json`. Preserve provenance, heading levels, source wording and evidence line ranges; never summarize, paraphrase, verify or infer here. Fact-base entries remain `source_assertion / unverified / unclassified` until downstream semantic work. Run `python scripts/parse.py <source.md>`; use the two JSON artifacts as the only layer-two outputs.
