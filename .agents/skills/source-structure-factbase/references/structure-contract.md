# structure.json Contract

`structure.json` is a deterministic structural view of one Markdown source. It records provenance, Markdown SHA-256, document title/counts, hierarchical outline, ordered blocks and warnings. Evidence lines are 1-based positions in the complete Markdown file. Heading-level jumps are preserved rather than repaired. Blocks carry `block_id`, type, exact text, line range, section and heading path; tables/lists/code fences preserve their structural details.
