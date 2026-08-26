# structure.json Contract

`structure.json` is a deterministic structural view of one Markdown source. It records provenance, Markdown SHA-256, document title/counts, hierarchical outline, ordered blocks and warnings. Evidence lines are 1-based positions in the complete Markdown file. Heading-level jumps are preserved rather than repaired. Blocks carry `block_id`, type, exact text, line range, section and heading path; tables/lists/code fences preserve their structural details.

Table blocks declare `header_status=explicit|empty`. When the Markdown header cells are all empty, the first body row remains in `rows` and is also recorded as `candidate_header` with `status=unconfirmed`, exact row index, exact line range and cells. This is lossless structural evidence only: the parser does not promote or delete that row, and downstream consumers must not treat an unconfirmed candidate as a header.
