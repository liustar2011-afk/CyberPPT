#!/usr/bin/env python3
"""
PowerPoint Table Borders — generates tables-borders.pptx exercising the pptx
table border model: border.all shorthand, per-edge borders (top/right/bottom/
left), inside dividers (horizontal/vertical), diagonal borders (tl2br/tr2bl),
and dash patterns (solid/dot/dash/lgDash/dashDot/sysDot/sysDash).

SDK twin of tables-borders.sh (officecli CLI). Both produce an equivalent
tables-borders.pptx. This one drives the **officecli Python SDK**
(`pip install officecli-sdk`): one resident is started and every shape, table,
and per-cell set is shipped over the named pipe in a single `doc.batch(...)`
round-trip. Each item is the same `{"command","parent","type","props"}` /
`{"command","path","props"}` dict you'd put in an `officecli batch` list.

Usage:
  pip install officecli-sdk          # plus the `officecli` binary on PATH
  python3 tables-borders.py
"""

import os
import sys

# --- locate the SDK: prefer an installed `officecli-sdk`, else the in-repo copy
try:
    import officecli  # pip install officecli-sdk
except ImportError:
    sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                    "..", "..", "..", "sdk", "python"))
    import officecli

FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "tables-borders.pptx")

DATA = "A,B,C;1,2,3;4,5,6;7,8,9"


def shape(slide, text, x, y, width, height, **props):
    """One `add shape` item in batch-shape."""
    return {"command": "add", "parent": f"/slide[{slide}]", "type": "shape",
            "props": {"text": text, "x": x, "y": y, "width": width,
                      "height": height, **props}}


def add_table(slide, x, y, label, **border):
    """Mirror of the .sh add_table helper: a bold caption shape at (x, y)
    followed by a 4x3 table at (x, y+0.35). Returns the two batch items."""
    ty = round(y + 0.35, 10)
    return [
        {"command": "add", "parent": f"/slide[{slide}]", "type": "shape",
         "props": {"text": label, "size": "12", "bold": "true",
                   "x": f"{x}in", "y": f"{y}in", "width": "4in", "height": "0.3in"}},
        {"command": "add", "parent": f"/slide[{slide}]", "type": "table",
         "props": {"x": f"{x}in", "y": f"{ty}in", "width": "3.5in",
                   "height": "1.8in", "style": "none", "data": DATA, **border}},
    ]


def cell(slide, table, tr, tc, **props):
    """One `set` item targeting a table cell in batch-shape."""
    return {"command": "set",
            "path": f"/slide[{slide}]/table[{table}]/tr[{tr}]/tc[{tc}]",
            "props": props}


print(f"Building {FILE} ...")

with officecli.create(FILE, "--force") as doc:

    # --- Slide 1: border shorthand & per-edge ---
    items = [
        {"command": "add", "parent": "/", "type": "slide", "props": {}},
        shape(1, "Borders: Shorthand & Per-Edge", "0.5in", "0.3in", "12in", "0.6in",
              size="28", bold="true"),
    ]
    items += add_table(1, 0.5, 1.0, "border.all=1pt solid 808080",
                       **{"border.all": "1pt solid 808080"})
    items += add_table(1, 5.0, 1.0, "border.all=2pt solid FF0000",
                       **{"border.all": "2pt solid FF0000"})
    items += add_table(1, 9.5, 1.0, "border.all=none",
                       **{"border.all": "none"})
    items += add_table(1, 0.5, 3.5, "border.top=3pt solid 000000",
                       **{"border.top": "3pt solid 000000"})
    items += add_table(1, 5.0, 3.5, "border.bottom=3pt solid 0070C0",
                       **{"border.bottom": "3pt solid 0070C0"})
    items += add_table(1, 9.5, 3.5, "border.left=3pt solid 00B050",
                       **{"border.left": "3pt solid 00B050"})
    # Per-edge right border (mirrors left; same compound spec)
    items += add_table(1, 0.5, 5.8, "border.right=3pt solid C00000",
                       **{"border.right": "3pt solid C00000"})
    doc.batch(items)

    # --- Slide 2: inside dividers & dash patterns ---
    items = [
        {"command": "add", "parent": "/", "type": "slide", "props": {}},
        shape(2, "Borders: Inside Dividers & Dashes", "0.5in", "0.3in", "12in", "0.6in",
              size="28", bold="true"),
    ]
    items += add_table(2, 0.5, 1.0, "border.horizontal=1pt solid CCC",
                       **{"border.horizontal": "1pt solid CCCCCC",
                          "border.all": "1pt solid 404040"})
    items += add_table(2, 5.0, 1.0, "border.vertical=1pt dash 0070C0",
                       **{"border.vertical": "1pt dash 0070C0",
                          "border.all": "1pt solid 404040"})
    items += add_table(2, 9.5, 1.0, "horizontal+vertical=dot",
                       **{"border.horizontal": "1pt dot 808080",
                          "border.vertical": "1pt dot 808080",
                          "border.all": "2pt solid 000000"})
    items += add_table(2, 0.5, 3.5, "dash=lgDash",
                       **{"border.all": "1.5pt lgDash FF0000"})
    items += add_table(2, 5.0, 3.5, "dash=dashDot",
                       **{"border.all": "1.5pt dashDot 0070C0"})
    items += add_table(2, 9.5, 3.5, "dash=sysDash",
                       **{"border.all": "1.5pt sysDash 00B050"})
    doc.batch(items)

    # --- Slide 3: diagonal borders (per-cell) ---
    items = [
        {"command": "add", "parent": "/", "type": "slide", "props": {}},
        shape(3, "Diagonal Borders (per-cell, tl2br / tr2bl)", "0.5in", "0.3in",
              "12in", "0.6in", size="28", bold="true"),
        shape(3, "Typical use: 'crossed out' header corner cell.", "0.5in", "0.95in",
              "12in", "0.4in", size="14"),
        {"command": "add", "parent": "/slide[3]", "type": "table",
         "props": {"x": "2in", "y": "1.6in", "width": "9in", "height": "3in",
                   "rows": "4", "cols": "4", "border.all": "1pt solid 808080"}},
        # Top-left corner: diagonal split with 'Month' / 'Region' labels
        cell(3, 1, 1, 1, text="", fill="F2F2F2",
             **{"border.tl2br": "1pt solid 808080"}),
        # Column headers
        cell(3, 1, 1, 2, text="Jan", bold="true", align="center", fill="DEEAF6"),
        cell(3, 1, 1, 3, text="Feb", bold="true", align="center", fill="DEEAF6"),
        cell(3, 1, 1, 4, text="Mar", bold="true", align="center", fill="DEEAF6"),
        # Row headers + data
        cell(3, 1, 2, 1, text="North", bold="true", fill="DEEAF6"),
        cell(3, 1, 2, 2, text="120"),
        cell(3, 1, 2, 3, text="135"),
        cell(3, 1, 2, 4, text="142"),
        cell(3, 1, 3, 1, text="South", bold="true", fill="DEEAF6"),
        cell(3, 1, 3, 2, text="98"),
        cell(3, 1, 3, 3, text="110"),
        cell(3, 1, 3, 4, text="121"),
        cell(3, 1, 4, 1, text="East", bold="true", fill="DEEAF6"),
        cell(3, 1, 4, 2, text="165"),
        cell(3, 1, 4, 3, text="178"),
        cell(3, 1, 4, 4, text="190"),
        # A standalone cell with both diagonals (X pattern)
        shape(3, "Both diagonals on a single cell:", "0.5in", "5.2in",
              "12in", "0.4in", size="14"),
        {"command": "add", "parent": "/slide[3]", "type": "table",
         "props": {"x": "5in", "y": "5.7in", "width": "3in", "height": "1.2in",
                   "rows": "1", "cols": "1", "border.all": "1pt solid 000000"}},
        cell(3, 2, 1, 1, text="N/A", align="center", fill="F2F2F2",
             **{"border.tl2br": "1pt solid C00000",
                "border.tr2bl": "1pt solid C00000"}),
    ]
    doc.batch(items)

print(f"Generated: {FILE}")
