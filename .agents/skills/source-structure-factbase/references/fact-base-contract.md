# fact-base.json Contract

Entries are source assertions, not independently verified facts. Every entry is emitted with `claim_status=source_assertion`, `verification_status=unverified`, and `semantic_role=unclassified`. Paragraph/list/blockquote material becomes statement entries without rewriting; table headers are schema and each data row becomes one table record. Every record preserves its originating block and Markdown line range. Headings, code fences and dividers do not become facts.
