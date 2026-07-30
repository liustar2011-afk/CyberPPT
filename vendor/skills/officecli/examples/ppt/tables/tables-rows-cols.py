#!/usr/bin/env python3
"""
PowerPoint table row & column operations — generates tables-rows-cols.pptx.
Demonstrates: add row / add column (grow an existing table), per-row height
(set row.height), per-column width (set col.width), column seed text, gridSpan
(horizontal merge), merge.down (vertical merge).

SDK twin of tables-rows-cols.sh (officecli CLI). Both produce an equivalent
tables-rows-cols.pptx. This one drives the **officecli Python SDK**
(`pip install officecli-sdk`): one resident is started and every command is
shipped over the named pipe in a single `doc.batch(...)` round-trip. Each item
is the same `{"command","parent"|"path","type","props"}` dict you'd put in an
`officecli batch` list.

Usage:
  pip install officecli-sdk          # plus the `officecli` binary on PATH
  python3 tables-rows-cols.py
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

FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "tables-rows-cols.pptx")


def add(parent, type_, **props):
    """One `add` item in batch-shape."""
    return {"command": "add", "parent": parent, "type": type_, "props": props}


def setp(path, **props):
    """One `set` item in batch-shape."""
    return {"command": "set", "path": path, "props": props}


print(f"Building {FILE} ...")

HDR = "4472C4"
BODY = "DEEAF6"
SUM = "B4C7E7"

with officecli.create(FILE, "--force") as doc:
    items = [
        # ============================================================
        # Slide 1: Grow a table by add row / add column
        # Two side-by-side tables compare the two coloring models:
        #   LEFT  A. style=medium2   → table-level theme, auto-follows new rows/cols.
        #   RIGHT B. headerFill/bodyFill → per-cell stamp, does NOT follow; manual top-up.
        # ============================================================
        add("/", "slide"),
        add("/slide[1]", "shape", text="Grow a Table — Theme vs Per-Cell Stamp",
            size="28", bold="true", x="0.5in", y="0.3in", width="12in", height="0.6in"),

        # === LEFT: Table A — style=medium2 (theme, auto-inherits) ===
        add("/slide[1]", "shape", text="A) style=medium2  (auto-follows)",
            size="14", bold="true", x="0.5in", y="1in", width="6in", height="0.4in"),

        add("/slide[1]", "table", x="0.5in", y="1.5in", width="2in", height="1.5in",
            style="medium2", firstRow="true", bandedRows="true", lastCol="true",
            data="Name,H1;Alice,220"),

        # Append 2 rows + 1 column — set NOTHING about fill. PowerPoint paints
        # every new cell via the medium2 theme.
        add("/slide[1]/table[1]", "row", c1="Bob", c2="205"),
        add("/slide[1]/table[1]", "row", c1="Carol", c2="275"),
        add("/slide[1]/table[1]", "column", width="1in", text="H2"),
        setp("/slide[1]/table[1]/tr[2]/tc[3]", text="245"),
        setp("/slide[1]/table[1]/tr[3]/tc[3]", text="225"),
        setp("/slide[1]/table[1]/tr[4]/tc[3]", text="335"),
        add("/slide[1]/table[1]", "column", width="1in", text="Total"),
        setp("/slide[1]/table[1]/tr[2]/tc[4]", text="465", bold="true"),
        setp("/slide[1]/table[1]/tr[3]/tc[4]", text="430", bold="true"),
        setp("/slide[1]/table[1]/tr[4]/tc[4]", text="610", bold="true"),

        # === RIGHT: Table B — headerFill/bodyFill (per-cell stamp, does NOT inherit) ===
        add("/slide[1]", "shape", text="B) headerFill/bodyFill  (manual top-up)",
            size="14", bold="true", x="7in", y="1in", width="6in", height="0.4in"),

        add("/slide[1]", "table", x="7in", y="1.5in", width="2in", height="1.5in",
            headerFill="4472C4", bodyFill="DEEAF6", data="Name,H1;Alice,220"),
        add("/slide[1]/table[2]", "row", c1="Bob", c2="205"),
        add("/slide[1]/table[2]", "row", c1="Carol", c2="275"),
        add("/slide[1]/table[2]", "column", width="1in", text="H2"),
        setp("/slide[1]/table[2]/tr[2]/tc[3]", text="245"),
        setp("/slide[1]/table[2]/tr[3]/tc[3]", text="225"),
        setp("/slide[1]/table[2]/tr[4]/tc[3]", text="335"),
        add("/slide[1]/table[2]", "column", width="1in", text="Total"),
        setp("/slide[1]/table[2]/tr[2]/tc[4]", text="465"),
        setp("/slide[1]/table[2]/tr[3]/tc[4]", text="430"),
        setp("/slide[1]/table[2]/tr[4]/tc[4]", text="610"),

        # Manual top-up — headerFill/bodyFill are a one-shot stamp at add-table
        # time. Every cell created later by add row / add column has no fill and
        # must be styled explicitly. The Total column gets a darker fill (SUM) +
        # bold so it reads as a totals band; table A gets the equivalent emphasis
        # from medium2's last-column theme styling for free.
        # Bob, Carol body fill across the original 2 columns.
        setp("/slide[1]/table[2]/tr[3]/tc[1]", fill=BODY),
        setp("/slide[1]/table[2]/tr[4]/tc[1]", fill=BODY),
        setp("/slide[1]/table[2]/tr[3]/tc[2]", fill=BODY),
        setp("/slide[1]/table[2]/tr[4]/tc[2]", fill=BODY),
        # H2 column — header HDR, body BODY for all 3 data rows.
        setp("/slide[1]/table[2]/tr[1]/tc[3]", fill=HDR, color="FFFFFF", bold="true"),
        setp("/slide[1]/table[2]/tr[2]/tc[3]", fill=BODY),
        setp("/slide[1]/table[2]/tr[3]/tc[3]", fill=BODY),
        setp("/slide[1]/table[2]/tr[4]/tc[3]", fill=BODY),
        # Total column — header HDR, body SUM (bold) for all 3 data rows.
        setp("/slide[1]/table[2]/tr[1]/tc[4]", fill=HDR, color="FFFFFF", bold="true"),
        setp("/slide[1]/table[2]/tr[2]/tc[4]", fill=SUM, bold="true"),
        setp("/slide[1]/table[2]/tr[3]/tc[4]", fill=SUM, bold="true"),
        setp("/slide[1]/table[2]/tr[4]/tc[4]", fill=SUM, bold="true"),

        # ============================================================
        # Slide 2: Per-row heights & per-column widths
        # ============================================================
        add("/", "slide"),
        add("/slide[2]", "shape", text="Per-Row Height + Per-Column Width",
            size="28", bold="true", x="0.5in", y="0.3in", width="12in", height="0.6in"),

        add("/slide[2]", "table", x="0.5in", y="1.2in", width="12in", height="4in",
            rows="4", cols="4", headerFill="2E75B6"),

        # Header
        setp("/slide[2]/table[1]/tr[1]/tc[1]", bold="true", color="FFFFFF", align="center"),
        setp("/slide[2]/table[1]/tr[1]/tc[2]", bold="true", color="FFFFFF", align="center"),
        setp("/slide[2]/table[1]/tr[1]/tc[3]", bold="true", color="FFFFFF", align="center"),
        setp("/slide[2]/table[1]/tr[1]/tc[4]", bold="true", color="FFFFFF", align="center"),
        setp("/slide[2]/table[1]/tr[1]/tc[1]", text="Field", bold="true", color="FFFFFF"),
        setp("/slide[2]/table[1]/tr[1]/tc[2]", text="Short", bold="true", color="FFFFFF"),
        setp("/slide[2]/table[1]/tr[1]/tc[3]", text="Wide", bold="true", color="FFFFFF"),
        setp("/slide[2]/table[1]/tr[1]/tc[4]", text="Narrow", bold="true", color="FFFFFF"),

        # Custom per-column widths (the four columns total ~12in).
        setp("/slide[2]/table[1]/col[1]", width="2in"),
        setp("/slide[2]/table[1]/col[2]", width="1.5in"),
        setp("/slide[2]/table[1]/col[3]", width="7in"),
        setp("/slide[2]/table[1]/col[4]", width="1.5in"),

        # Custom per-row heights — header thin, body increasing.
        setp("/slide[2]/table[1]/tr[1]", height="0.5in"),
        setp("/slide[2]/table[1]/tr[2]", height="0.6in"),
        setp("/slide[2]/table[1]/tr[3]", height="1in"),
        setp("/slide[2]/table[1]/tr[4]", height="1.5in"),

        setp("/slide[2]/table[1]/tr[2]/tc[1]", text="Title"),
        setp("/slide[2]/table[1]/tr[2]/tc[2]", text="A"),
        setp("/slide[2]/table[1]/tr[2]/tc[3]", text="Standard row height (0.6in)"),
        setp("/slide[2]/table[1]/tr[2]/tc[4]", text="x"),

        setp("/slide[2]/table[1]/tr[3]/tc[1]", text="Body"),
        setp("/slide[2]/table[1]/tr[3]/tc[2]", text="B"),
        setp("/slide[2]/table[1]/tr[3]/tc[3]", text="Taller row (1in) for emphasis"),
        setp("/slide[2]/table[1]/tr[3]/tc[4]", text="y"),

        setp("/slide[2]/table[1]/tr[4]/tc[1]", text="Notes"),
        setp("/slide[2]/table[1]/tr[4]/tc[2]", text="C"),
        setp("/slide[2]/table[1]/tr[4]/tc[3]", text="Tallest row (1.5in) — multi-line content"),
        setp("/slide[2]/table[1]/tr[4]/tc[4]", text="z"),

        # ============================================================
        # Slide 3: Uniform row height via table-level rowHeight
        # ============================================================
        add("/", "slide"),
        add("/slide[3]", "shape", text="Uniform rowHeight (table-level)",
            size="28", bold="true", x="0.5in", y="0.3in", width="12in", height="0.6in"),

        # Setting rowHeight at add-time stamps every row with the same height
        # (no need to set each row individually).
        add("/slide[3]", "table", x="0.5in", y="1.2in", width="12in",
            rows="5", cols="3", rowHeight="0.8in",
            headerFill="1F4E79", bodyFill="F2F2F2",
            data="Step,Action,Result;1,Init,OK;2,Process,OK;3,Verify,OK;4,Commit,OK"),

        # ============================================================
        # Slide 4: Cell merging — gridSpan (horizontal) + vMerge (vertical)
        # OOXML's table model fixes row width at <a:tblGrid> column count and row
        # count at <a:tr> count — no "narrower row" or "shorter column" exists.
        # Visual merging is done in-place via gridSpan (horizontal) or merge.down
        # (vertical, wraps rowSpan + vMerge).
        # ============================================================
        add("/", "slide"),
        add("/slide[4]", "shape",
            text="Cell Merging — gridSpan (horizontal) + merge.down (vertical)",
            size="28", bold="true", x="0.5in", y="0.3in", width="12in", height="1in"),

        # === Top table: gridSpan=N — full-width footnote ===
        add("/slide[4]", "shape",
            text="1) gridSpan=N on first cell of a row — one wide cell across all N columns",
            size="14", bold="true", x="0.5in", y="1in", width="12in", height="0.4in"),
        add("/slide[4]", "table", x="0.5in", y="1.5in", width="12in", height="1.5in",
            headerFill="2E75B6", data="Q1,Q2,Q3,Q4;100,120,135,150"),
        # Append a normal 4-cell row, then horizontally merge via gridSpan on tc[1].
        add("/slide[4]/table[1]", "row", c1="Footnote: figures in thousands USD, unaudited."),
        setp("/slide[4]/table[1]/tr[3]/tc[1]", **{"gridSpan": "4", "fill": "F2F2F2", "bold": "true"}),

        # === Bottom table: merge.down=N — grouped row labels ===
        add("/slide[4]", "shape",
            text="2) merge.down=N on a cell — one tall cell spanning N rows (vMerge + rowSpan)",
            size="14", bold="true", x="0.5in", y="3.3in", width="12in", height="0.4in"),
        add("/slide[4]", "table", x="0.5in", y="3.8in", width="12in", height="3in",
            headerFill="2E75B6", rowHeight="0.5in",
            data="Region,Month,Sales,Notes;North,Jan,120,;North,Feb,135,;North,Mar,142,;South,Jan,98,;South,Feb,110,"),
        # Merge "North" cell down 3 rows (rows 2..4); merge "South" cell down 2
        # rows (rows 5..6). merge.down=N spans the cell over N+1 rows total.
        setp("/slide[4]/table[2]/tr[2]/tc[1]",
             **{"merge.down": "2", "bold": "true", "fill": "DEEAF6", "valign": "middle"}),
        setp("/slide[4]/table[2]/tr[5]/tc[1]",
             **{"merge.down": "1", "bold": "true", "fill": "DEEAF6", "valign": "middle"}),
    ]

    doc.batch(items)
    print(f"  applied {len(items)} commands")

print(f"Generated: {FILE}")
