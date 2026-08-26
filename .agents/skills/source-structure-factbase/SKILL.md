---
name: source-structure-factbase
description: Use when normalized Markdown source materials need source-preserving structure extraction, heading hierarchy recovery, evidence line mapping, or a traceable source-assertion fact base before semantic analysis, solution drafting, knowledge modeling, or PPT compilation.
---

# Source Structure Factbase

Turn one normalized Markdown source into deterministic `structure.json` and `fact-base.json`. Preserve provenance, heading levels, source wording and evidence line ranges; never summarize, paraphrase, verify or infer here. Table rows retain trace parents and expose stable cell-level atomic children for downstream citation. An empty Markdown header records the first body row only as an unconfirmed candidate with exact coordinates; do not promote or remove it without separate structural evidence. Fact-base entries remain `source_assertion / unverified / unclassified` until downstream semantic work. From this Skill directory, run `../../../.venv/bin/python3 scripts/parse.py <source.md>`; use the two JSON artifacts as the only layer-two outputs.
