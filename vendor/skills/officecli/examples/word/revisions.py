#!/usr/bin/env python3
r"""
Revision Showcase — generates revisions.docx exercising every tracked-revision
element the docx handler supports: run-scope (ins / del / rPrChange implicit +
explicit / moveFrom + moveTo), paragraph-scope (ins / del / pPrChange),
table-scope (tblPrChange / trPrChange / tcPrChange / row + cell ins/del),
section-scope (sectPrChange), defaults & explicit-id, and Word-style
Find&Replace-with-Track-Changes (find + replace / format / delete-only /
paragraph-prop).

SDK twin of revisions.sh (officecli CLI). Both produce an equivalent
revisions.docx. This one drives the **officecli Python SDK**
(`pip install officecli-sdk`): one resident is started and every command is
shipped over the named pipe. Each item is the same `{"command","parent"/"path",
"type","props"}` dict you'd put in an `officecli batch` list.

Ordering note (mirrors the .sh): tracked-delete KEEPS the paragraph/cell element
in place (wrapped in w:del), so positional /body/p[N] indices do NOT shift after
a tracked remove. The build order below is chosen so every positional path stays
correct as the document grows. Sections 1-6 use stable /body/p[N] indices and so
ship as one big batch; sections 7-8 use `set --find` against handler-assigned
`/body/p[@paraId=...]` paths, so each paragraph is added with `send` first and
its returned paraId path is fed to the following `set` (the SDK analogue of the
.sh `add_para_capture` helper).

Usage:
  pip install officecli-sdk          # plus the `officecli` binary on PATH
  python3 revisions.py
"""

import os
import re
import sys

# --- locate the SDK: prefer an installed `officecli-sdk`, else the in-repo copy
try:
    import officecli  # pip install officecli-sdk
except ImportError:
    sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                    "..", "..", "sdk", "python"))
    import officecli

FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "revisions.docx")


def para(text, **props):
    """One `add paragraph` item in batch-shape."""
    return {"command": "add", "parent": "/body", "type": "paragraph",
            "props": {"text": text, **props}}


def add_para_capture(doc, text):
    """Add a paragraph with `send` and return the handler-assigned paraId path
    (e.g. /body/p[@paraId=00100012]). The SDK analogue of the .sh helper: the
    paraId path is stable across content shifts, unlike /body/p[N]."""
    resp = doc.send(para(text))
    data = resp.get("data", "") if isinstance(resp, dict) else str(resp)
    m = re.search(r"/body/p\[@paraId=[A-F0-9]+\]", data)
    if not m:
        raise RuntimeError(f"could not extract paraId path from add response: {resp!r}")
    return m.group(0)


print("==========================================")
print(f"Generating tracked-revision showcase: {FILE}")
print("==========================================")

with officecli.create(FILE, "--force") as doc:

    # ======================================================================
    # Sections 1-6 — stable /body/p[N] indices, shipped in one batch.
    #
    # Paragraph index map (1-based; counts EVERY body paragraph). Tracked-delete
    # keeps the paragraph element in place (wrapped in w:del), so subsequent
    # indices do NOT shift after step 2b.
    # ======================================================================
    items = [
        # p[1] title, p[2] spacer
        para("Revision API — Full Coverage", style="Heading1", align="center"),
        para(""),

        # ----- Section 1: run-level edits (p[3]..p[7]) -----
        para("1. Run-level edits", style="Heading2"),                          # p[3]
        para("This run will be marked as an INSERTION."),                      # p[4]
        para("This run will be marked as a DELETION."),                        # p[5]
        para("This run keeps the text and gets an IMPLICIT format change (font.color)."),  # p[6]
        para("This run gets an EXPLICIT revision.type=format with italic toggle."),        # p[7]

        # 1a. w:ins around the run.
        {"command": "set", "path": "/body/p[4]/r[1]",
         "props": {"revision.type": "ins", "revision.author": "Alice",
                   "revision.date": "2026-05-25T10:00:00Z"}},
        # 1b. w:del around the run (text becomes w:delText).
        {"command": "set", "path": "/body/p[5]/r[1]",
         "props": {"revision.type": "del", "revision.author": "Bob",
                   "revision.date": "2026-05-25T10:05:00Z"}},
        # 1c. Implicit format change — any font.* prop + revision.author captures
        #     the previous rPr in w:rPrChange. Most natural form.
        {"command": "set", "path": "/body/p[6]/r[1]",
         "props": {"font.color": "C00000", "bold": "true", "revision.author": "Carol",
                   "revision.date": "2026-05-25T10:10:00Z"}},
        # 1d. Explicit revision.type=format. Still needs a real property change
        #     alongside (empty rPrChange records nothing, so the handler errors out).
        {"command": "set", "path": "/body/p[7]/r[1]",
         "props": {"revision.type": "format", "italic": "true", "revision.author": "Carol",
                   "revision.date": "2026-05-25T10:11:00Z"}},

        # ----- Section 2: paragraph-level edits (p[8]..p[11]) -----
        para("2. Paragraph-level edits", style="Heading2"),                    # p[8]
        # 2a. w:ins around the entire paragraph (plus paragraphMarkInsertion).
        para("This whole paragraph was inserted by Alice as a tracked change.",  # p[9]
             **{"revision.author": "Alice", "revision.date": "2026-05-25T10:15:00Z"}),
        # 2b. w:del around the entire paragraph. remove + revision.author KEEPS
        #     the element (wraps it); it does not drop it.
        para("This whole paragraph will be tracked-deleted by Bob."),          # p[10]
        {"command": "remove", "path": "/body/p[10]",
         "props": {"revision.author": "Bob", "revision.date": "2026-05-25T10:20:00Z"}},
        # 2c. pPrChange — set a paragraph-level property (alignment) + author.
        para("This paragraph had alignment changed (pPrChange) by Carol."),    # p[11]
        {"command": "set", "path": "/body/p[11]",
         "props": {"align": "center", "revision.author": "Carol",
                   "revision.date": "2026-05-25T10:21:00Z"}},

        # ----- Section 3: paired move (shared revision.id, p[12]..p[14]) -----
        para("3. Moved content", style="Heading2"),                            # p[12]
        para("Source: this sentence is being relocated."),                     # p[13]
        para("Destination: it will land here in its new home."),               # p[14]
        # revision.id MUST be supplied (and equal) for the two halves to pair.
        {"command": "set", "path": "/body/p[13]/r[1]",
         "props": {"revision.type": "moveFrom", "revision.author": "Alice",
                   "revision.date": "2026-05-25T10:25:00Z", "revision.id": "500"}},
        {"command": "set", "path": "/body/p[14]/r[1]",
         "props": {"revision.type": "moveTo", "revision.author": "Alice",
                   "revision.date": "2026-05-25T10:25:00Z", "revision.id": "500"}},

        # ----- Section 4: table scope (p[15] + tbl[1]) -----
        para("4. Table-scope revisions", style="Heading2"),                    # p[15]
        {"command": "add", "parent": "/body", "type": "table",
         "props": {"rows": "3", "cols": "3"}},

        # Seed content
        {"command": "set", "path": "/body/tbl[1]/tr[1]/tc[1]", "props": {"text": "Header A", "bold": "true"}},
        {"command": "set", "path": "/body/tbl[1]/tr[1]/tc[2]", "props": {"text": "Header B", "bold": "true"}},
        {"command": "set", "path": "/body/tbl[1]/tr[1]/tc[3]", "props": {"text": "Header C", "bold": "true"}},
        {"command": "set", "path": "/body/tbl[1]/tr[2]/tc[1]", "props": {"text": "row2 a"}},
        {"command": "set", "path": "/body/tbl[1]/tr[2]/tc[2]", "props": {"text": "row2 b (shading change)"}},
        {"command": "set", "path": "/body/tbl[1]/tr[2]/tc[3]", "props": {"text": "row2 c"}},
        {"command": "set", "path": "/body/tbl[1]/tr[3]/tc[1]", "props": {"text": "row3 a (cell delete)"}},
        {"command": "set", "path": "/body/tbl[1]/tr[3]/tc[2]", "props": {"text": "row3 b"}},
        {"command": "set", "path": "/body/tbl[1]/tr[3]/tc[3]", "props": {"text": "row3 c"}},

        # 4a. tblPrChange — table-level property change.
        {"command": "set", "path": "/body/tbl[1]",
         "props": {"style": "TableGrid", "revision.author": "Dan",
                   "revision.date": "2026-05-25T10:30:00Z"}},
        # 4b. trPrChange — row-level property change (row height).
        {"command": "set", "path": "/body/tbl[1]/tr[1]",
         "props": {"height": "600", "revision.author": "Dan",
                   "revision.date": "2026-05-25T10:31:00Z"}},
        # 4c. tcPrChange — cell-level property change (shading). Cascades
        #     tblPrExChange / tblGridChange automatically when needed.
        {"command": "set", "path": "/body/tbl[1]/tr[2]/tc[2]",
         "props": {"shd": "FFE699", "revision.author": "Dan",
                   "revision.date": "2026-05-25T10:32:00Z"}},
        # 4d. Cell insertion — add a 4th cell to row 2.
        {"command": "add", "parent": "/body/tbl[1]/tr[2]", "type": "cell",
         "props": {"text": "row2 d (inserted)", "revision.author": "Eve",
                   "revision.date": "2026-05-25T10:33:00Z"}},
        # 4e. Cell deletion — drop cell 1 of row 3 (tracked, not destructive).
        {"command": "remove", "path": "/body/tbl[1]/tr[3]/tc[1]",
         "props": {"revision.author": "Eve", "revision.date": "2026-05-25T10:34:00Z"}},
        # 4f. Row insertion — append a row at the table tail; whole row inserted.
        {"command": "add", "parent": "/body/tbl[1]", "type": "row",
         "props": {"revision.author": "Eve", "revision.date": "2026-05-25T10:35:00Z"}},

        # ----- Section 5: section properties (sectPrChange) -----
        para("5. Section properties", style="Heading2"),                       # p[16]
        para("The body sectPr below got a tracked pageWidth change."),         # p[17]
        # The body's section properties live at /body/sectPr[1] (NOT /body/sect[1]).
        {"command": "set", "path": "/body/sectPr[1]",
         "props": {"pageWidth": "11906", "revision.author": "Frank",
                   "revision.date": "2026-05-25T10:40:00Z"}},

        # ----- Section 6: defaults & explicit-id -----
        para("6. Defaults", style="Heading2"),                                 # p[18]
        # 6a. Empty revision.author -> falls back to "OfficeCLI". `add +
        #     revision.author=""` silently produces an untracked paragraph, so add
        #     the paragraph plain then `set` it with an empty author to fire the
        #     default-author fallback on the set path.
        para('This run was wrapped via set with revision.author="" (defaults to OfficeCLI).'),  # p[19]
        {"command": "set", "path": "/body/p[19]/r[1]",
         "props": {"revision.type": "ins", "revision.author": "",
                   "revision.date": "2026-05-25T10:44:00Z"}},
        # 6b. Explicit revision.id outside of a move pair — accepted, you control
        #     the w:id attribute.
        para("This paragraph carries an explicit revision.id=9001.",           # p[20]
             **{"revision.author": "Grace", "revision.date": "2026-05-25T10:45:00Z",
                "revision.id": "9001"}),
    ]
    doc.batch(items)
    print(f"  sections 1-6: shipped {len(items)} batch items")

    # ======================================================================
    # Section 7 — Find + Replace combined with revision tracking.
    #   Word's Find&Replace with Track Changes ON: every match is wrapped in the
    #   marker shape inferred from the props passed alongside. The handler
    #   auto-allocates a fresh revision.id per marker, so `revision.id` is
    #   rejected on find — it would collide.
    # ======================================================================
    print("  -> Section 7: find + revision (Find&Replace with Track Changes)")
    doc.send(para("7. Find + Replace + Revision", style="Heading2"))

    # 7a. find + replace + revision via REGEX — track only the FIRST "fox".
    #     Pattern (?<!fox.*)fox matches "fox" only when NOT preceded by another
    #     "fox" on the same line (.NET variable-width negative lookbehind).
    p7a = add_para_capture(doc,
        "7a. The fox jumped and another fox ran fast. (regex tracks only the 1st 'fox'→'cat')")
    doc.send({"command": "set", "path": p7a,
              "props": {"find": r"(?<!fox.*)fox", "replace": "cat", "regex": "true",
                        "revision.author": "Iris", "revision.date": "2026-05-25T10:50:00Z"}})

    # 7b. find + format + revision — one w:rPrChange per matched run.
    p7b = add_para_capture(doc,
        "7b. Color red apples and the red barn. (tracked bold on every 'red')")
    doc.send({"command": "set", "path": p7b,
              "props": {"find": "red", "bold": "true",
                        "revision.author": "Jack", "revision.date": "2026-05-25T10:51:00Z"}})

    # 7c. find + replace + format + revision — inserted run inherits the original
    #     rPr from the matched text AND has the new format layered on.
    p7c = add_para_capture(doc,
        "7c. Replace bar with FOO. (find target → bold-green replacement)")
    doc.send({"command": "set", "path": p7c,
              "props": {"find": "bar", "replace": "BAZ", "bold": "true", "font.color": "00B050",
                        "revision.author": "Kelly", "revision.date": "2026-05-25T10:52:00Z"}})

    # 7d. find + regex + revision — multiple matches each get their own marker.
    p7d = add_para_capture(doc,
        r"7d. Prices: $100, $250, $999 (regex \$\d+ → tracked bold)")
    doc.send({"command": "set", "path": p7d,
              "props": {"find": r"\$\d+", "regex": "true", "bold": "true",
                        "revision.author": "Liam", "revision.date": "2026-05-25T10:53:00Z"}})

    # ======================================================================
    # Section 8 — Less-common find + revision variants.
    #   8a: find + replace="" — pure tracked deletion (one w:del per match, no
    #   w:ins). 8b: find + paragraph property — paragraph-scope mutation captured
    #   as w:pPrChange instead of run-scope w:rPrChange.
    # ======================================================================
    print("  -> Section 8: find variants (delete-only + paragraph-prop pPrChange)")
    doc.send(para("8. Find variants", style="Heading2"))

    # 8a. find + replace="" + revision — tracked DELETION of every match.
    p8a = add_para_capture(doc,
        "8a. Remove the OBSOLETE token here. (delete-only via find — no insertion)")
    doc.send({"command": "set", "path": p8a,
              "props": {"find": "OBSOLETE", "replace": "",
                        "revision.author": "Mira", "revision.date": "2026-05-25T10:54:00Z"}})

    # 8b. find + paragraph prop + revision — one w:pPrChange per matched paragraph.
    p8b = add_para_capture(doc,
        "8b. This paragraph contains MARK so its alignment gets tracked-centered.")
    doc.send({"command": "set", "path": p8b,
              "props": {"find": "MARK", "align": "center",
                        "revision.author": "Nora", "revision.date": "2026-05-25T10:55:00Z"}})

    doc.send({"command": "save"})
# context exit closes the resident, flushing the document to disk.

# ======================================================================
# Inspection — list every revision marker in the shipped file (read-side).
# ======================================================================
print("\n==========================================")
print(f"All revisions in {FILE}:")
print("==========================================")
with officecli.open(FILE) as doc:
    env = doc.send({"command": "query", "selector": "revision"})
    if isinstance(env, dict):
        data = env.get("data", {})
        print(f"  matches={data.get('matches')}")
        for r in data.get("results", [])[:3]:
            f = r.get("format", {})
            print(f"    path={r.get('path')}  type={f.get('revision.type')}  "
                  f"author={f.get('revision.author')}  text={repr(r.get('text',''))[:40]}")

print(f"\nDone: {FILE}")
