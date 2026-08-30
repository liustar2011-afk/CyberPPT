---
name: graft-first-search
description: Use when locating, exploring, debugging, reviewing, or changing repository code or files. Query the repository Graft graph before raw search or source reading.
---

# Graft-first Search

Use the repository context graph as the first search surface.

1. For a new repository or broad task, run `graft map`.
2. Run `graft ask "<task, symbol, error, or file name>" --source` before raw
   file search or source reading. Reuse literal identifiers from the request.
3. For exhaustive occurrences or callers, use `graft grep "<literal>"` or
   `graft callers <symbol>` as appropriate.
4. Open only the exact source span returned by Graft. If the graph lacks the
   required detail, search or read only the named unindexed file or that span.

Treat a known path as a query hint, not a reason to bypass Graft. After a large
code change, run `graft build` before completing the task.
