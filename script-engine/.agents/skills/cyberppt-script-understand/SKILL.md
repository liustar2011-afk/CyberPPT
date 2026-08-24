---
name: cyberppt-script-understand
description: Build the unified source foundation for PPT script generation from source materials and user constraints. Use at the beginning of Script Engine work. Preserve facts, concepts, relationships, argument chains, numbers, boundaries, responsibilities, terminology, and provenance. Do not plan slides or write PPT copy.
---

# UNDERSTAND

## Mission

Create a compact but complete semantic foundation for later planning and authoring.

The output is `foundation.json`. It is the only semantic authority exposed to downstream Script Engine stages.

## Input

- source materials;
- user instructions and required questions;
- source metadata or extracted Markdown when available.

## Required reasoning

1. Identify source units and provenance.
2. Extract facts and preserve statement strength.
3. Normalize entities and terminology without changing institutional meaning.
4. Identify actors, objects, actions, conditions, responsibilities, states, numbers, and boundaries.
5. Build material relationships and argument chains.
6. Record unresolved contradictions or missing evidence as `open_questions`.
7. Perform a completeness pass against the source.

## Output

Write `foundation.json` conforming to `contracts/foundation.schema.json`.

Internal extraction files may exist as cache, but they are not downstream authorities.

## Hard rules

- Do not create chapters or pages.
- Do not draft presentation copy.
- Do not upgrade source strength: suggestion cannot become requirement; plan cannot become completed fact; possibility cannot become commitment.
- Do not invent causal, chronological, priority, or dependency relationships.
- Preserve important exclusions, prerequisites, responsibilities, and numeric qualifiers.
- Source completeness has priority over early compression.

## Completion gate

The stage is complete when the foundation supports all source-critical topics and user-required questions, provenance is available for material claims, and unresolved conflicts are explicitly recorded.
