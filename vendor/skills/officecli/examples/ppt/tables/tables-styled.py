#!/usr/bin/env python3
"""
PowerPoint built-in table styles showcase — generates tables-styled.pptx.

Demonstrates: style= (medium1..4, light1..3, dark1..2, none),
firstRow/lastRow/firstCol/lastCol/bandedRows/bandedCols banding flags,
rowHeight (uniform) and name= (stable @name addressing).

SDK twin of tables-styled.sh (officecli CLI). Both produce an equivalent
tables-styled.pptx. This one drives the **officecli Python SDK**
(`pip install officecli-sdk`): one resident is started and every slide, shape
and table is shipped over the named pipe in a single `doc.batch(...)`
round-trip. Each item is the same `{"command","parent","type","props"}` (or
`{"command","path","props"}` for set) dict you'd put in an `officecli batch`
list.

Usage:
  pip install officecli-sdk          # plus the `officecli` binary on PATH
  python3 tables-styled.py
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

FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "tables-styled.pptx")

DATA = ("Region,Q1,Q2,Q3,Q4;North,120,135,142,168;South,98,110,121,140;"
        "East,165,178,190,205;West,140,155,168,182")


def slide():
    """One `add slide` item in batch-shape (slides hang off the presentation root)."""
    return {"command": "add", "parent": "/", "type": "slide", "props": {}}


def shape(idx, **props):
    """One `add shape` item on /slide[idx] in batch-shape."""
    return {"command": "add", "parent": f"/slide[{idx}]", "type": "shape", "props": props}


def table(idx, **props):
    """One `add table` item on /slide[idx] in batch-shape."""
    return {"command": "add", "parent": f"/slide[{idx}]", "type": "table", "props": props}


def add_slide(idx, style, title):
    """Slide with a title shape + a styled table (firstRow + bandedRows)."""
    return [
        slide(),
        shape(idx, text=title, size="28", bold="true",
              x="0.5in", y="0.3in", width="12in", height="0.6in"),
        table(idx, x="0.5in", y="1.2in", width="12in", height="3in",
              style=style, firstRow="true", bandedRows="true", data=DATA),
    ]


print(f"Building {FILE} ...")

with officecli.create(FILE, "--force") as doc:
    items = []

    # 9 built-in styles, one per slide.
    items += add_slide(1, "medium1", "style=medium1")
    items += add_slide(2, "medium2", "style=medium2")
    items += add_slide(3, "medium3", "style=medium3")
    items += add_slide(4, "medium4", "style=medium4")
    items += add_slide(5, "light1",  "style=light1")
    items += add_slide(6, "light2",  "style=light2")
    items += add_slide(7, "light3",  "style=light3")
    items += add_slide(8, "dark1",   "style=dark1")
    items += add_slide(9, "dark2",   "style=dark2")

    # Slide 10: banding flag combinations on a single style.
    items += [
        slide(),
        shape(10, text="Banding Flags (style=medium2)", size="28", bold="true",
              x="0.5in", y="0.3in", width="12in", height="0.6in"),

        shape(10, text="firstRow + bandedRows", size="14",
              x="0.5in", y="1in", width="6in", height="0.4in"),
        table(10, x="0.5in", y="1.4in", width="6in", height="2.5in",
              style="medium2", firstRow="true", bandedRows="true", data=DATA),

        shape(10, text="firstCol + bandedCols", size="14",
              x="7in", y="1in", width="6in", height="0.4in"),
        table(10, x="7in", y="1.4in", width="6in", height="2.5in",
              style="medium2", firstCol="true", bandedCols="true", data=DATA),

        shape(10, text="firstRow + lastRow (total row)", size="14",
              x="0.5in", y="4.3in", width="6in", height="0.4in"),
        table(10, x="0.5in", y="4.7in", width="6in", height="2.5in",
              style="medium2", firstRow="true", lastRow="true",
              data=DATA + ";Total,523,578,621,695"),

        shape(10, text="style=none (no theme)", size="14",
              x="7in", y="4.3in", width="6in", height="0.4in"),
        table(10, x="7in", y="4.7in", width="6in", height="2.5in",
              style="none", **{"border.all": "1pt solid 808080"}, data=DATA),
    ]

    # Slide 11: rowHeight (uniform) + name (stable @name addressing).
    items += [
        slide(),
        shape(11, text="rowHeight + name= addressing", size="28", bold="true",
              x="0.5in", y="0.3in", width="12in", height="0.6in"),
        shape(11, text=("The table below was created with name=SalesData and "
                        "rowHeight=1cm. After creation, it can be addressed as "
                        "/slide[11]/table[@name=SalesData] instead of by positional "
                        "index — handy when slides are reordered or tables added/removed."),
              size="12", x="0.5in", y="0.95in", width="12in", height="0.8in"),
        table(11, x="0.5in", y="2in", width="12in",
              rows="5", cols="4", rowHeight="1cm",
              name="SalesData", style="medium2", firstRow="true",
              data="Region,Q1,Q2,Q3;North,120,135,142;South,98,110,121;"
                   "East,165,178,190;West,140,155,168"),

        # Demonstrate @name addressing — set a cell via the stable name path.
        {"command": "set", "path": "/slide[11]/table[@name=SalesData]/tr[2]/tc[2]",
         "props": {"text": "120 ▲", "bold": "true", "fill": "C6E0B4"}},
    ]

    doc.batch(items)
    print(f"  shipped {len(items)} commands")

    doc.send({"command": "save"})

print(f"Generated: {FILE}")
