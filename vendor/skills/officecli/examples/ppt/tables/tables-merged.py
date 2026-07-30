#!/usr/bin/env python3
"""
PowerPoint table cell merging — horizontal merge via gridSpan.

Demonstrates: multi-column header spans, section headers spanning the table,
nested header hierarchy. officecli supports both horizontal (gridSpan) and
vertical (merge.down) write-side merging; this walks through gridSpan.

SDK twin of tables-merged.sh (officecli CLI). Both produce an equivalent
tables-merged.pptx. This one drives the **officecli Python SDK**
(`pip install officecli-sdk`): one resident is started and every slide, shape,
table and cell-set is shipped over the named pipe in a single `doc.batch(...)`
round-trip. Each item is the same `{"command","parent","type","props"}` /
`{"command","path","props"}` dict you'd put in an `officecli batch` list.

Usage:
  pip install officecli-sdk          # plus the `officecli` binary on PATH
  python3 tables-merged.py
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

FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "tables-merged.pptx")


def add(parent, type, **props):
    """One `add` item in batch-shape."""
    return {"command": "add", "parent": parent, "type": type, "props": props}


def cell(path, **props):
    """One `set` item targeting a table cell in batch-shape."""
    return {"command": "set", "path": path, "props": props}


print(f"Building {FILE} ...")

with officecli.create(FILE, "--force") as doc:
    items = [
        # ===================================================================
        # Slide 1: 2-level header (gridSpan on row 1)
        # ===================================================================
        add("/", "slide"),
        add("/slide[1]", "shape",
            text="Two-Level Header (gridSpan)", size="28", bold="true",
            x="0.5in", y="0.3in", width="12in", height="0.6in"),
        add("/slide[1]", "table",
            x="0.5in", y="1.2in", width="12in", height="3.5in",
            rows="6", cols="5", headerFill="2E75B6", bodyFill="DEEAF6"),

        # Row 1: super-headers
        cell("/slide[1]/table[1]/tr[1]/tc[1]",
             text="Department", bold="true", color="FFFFFF", align="center"),
        cell("/slide[1]/table[1]/tr[1]/tc[2]",
             text="2024 Performance", bold="true", color="FFFFFF", align="center",
             gridSpan="2"),
        # tc[3] is now a continuation cell from gridSpan=2 — skip to tc[4].
        cell("/slide[1]/table[1]/tr[1]/tc[4]",
             text="2025 Forecast", bold="true", color="FFFFFF", align="center",
             gridSpan="2"),

        # Row 2: sub-headers (lighter shade)
        cell("/slide[1]/table[1]/tr[2]/tc[1]", text="", fill="5B9BD5"),
        cell("/slide[1]/table[1]/tr[2]/tc[2]",
             text="Revenue", bold="true", color="FFFFFF", align="center", fill="5B9BD5"),
        cell("/slide[1]/table[1]/tr[2]/tc[3]",
             text="Margin", bold="true", color="FFFFFF", align="center", fill="5B9BD5"),
        cell("/slide[1]/table[1]/tr[2]/tc[4]",
             text="Revenue", bold="true", color="FFFFFF", align="center", fill="5B9BD5"),
        cell("/slide[1]/table[1]/tr[2]/tc[5]",
             text="Margin", bold="true", color="FFFFFF", align="center", fill="5B9BD5"),
    ]

    # Body rows: r, dept, 2024-rev, 2024-margin, 2025-rev, 2025-margin
    for r, d, a, b, c, e in [
        (3, "Engineering", "1.20M", "18%", "1.45M", "22%"),
        (4, "Sales",       "2.30M", "12%", "2.80M", "15%"),
        (5, "Marketing",   "0.95M", "25%", "1.10M", "28%"),
        (6, "Operations",  "0.78M", "30%", "0.85M", "32%"),
    ]:
        items += [
            cell(f"/slide[1]/table[1]/tr[{r}]/tc[1]", text=d, bold="true"),
            cell(f"/slide[1]/table[1]/tr[{r}]/tc[2]", text=a, align="right"),
            cell(f"/slide[1]/table[1]/tr[{r}]/tc[3]", text=b, align="right"),
            cell(f"/slide[1]/table[1]/tr[{r}]/tc[4]", text=c, align="right"),
            cell(f"/slide[1]/table[1]/tr[{r}]/tc[5]", text=e, align="right"),
        ]

    # ===================================================================
    # Slide 2: Section header rows spanning the full table
    # ===================================================================
    items += [
        add("/", "slide"),
        add("/slide[2]", "shape",
            text="Full-Width Section Headers", size="28", bold="true",
            x="0.5in", y="0.3in", width="12in", height="0.6in"),
        add("/slide[2]", "table",
            x="0.5in", y="1.2in", width="12in", height="4.5in",
            rows="9", cols="4", headerFill="1F3864"),
    ]

    # Header
    for c, t in [(1, "Item"), (2, "Owner"), (3, "Due"), (4, "Status")]:
        items.append(cell(f"/slide[2]/table[1]/tr[1]/tc[{c}]",
                          text=t, bold="true", color="FFFFFF"))

    items += [
        # Section: "Phase 1" — spans all 4 columns
        cell("/slide[2]/table[1]/tr[2]/tc[1]",
             text="◆ Phase 1 — Discovery", bold="true", fill="FFE699", gridSpan="4"),
        cell("/slide[2]/table[1]/tr[3]/tc[1]", text="Stakeholder interviews"),
        cell("/slide[2]/table[1]/tr[3]/tc[2]", text="Alice"),
        cell("/slide[2]/table[1]/tr[3]/tc[3]", text="Mar 15"),
        cell("/slide[2]/table[1]/tr[3]/tc[4]", text="✓ Done", color="00B050"),
        cell("/slide[2]/table[1]/tr[4]/tc[1]", text="Market research"),
        cell("/slide[2]/table[1]/tr[4]/tc[2]", text="Bob"),
        cell("/slide[2]/table[1]/tr[4]/tc[3]", text="Mar 30"),
        cell("/slide[2]/table[1]/tr[4]/tc[4]", text="✓ Done", color="00B050"),

        # Section: "Phase 2"
        cell("/slide[2]/table[1]/tr[5]/tc[1]",
             text="◆ Phase 2 — Design", bold="true", fill="C6E0B4", gridSpan="4"),
        cell("/slide[2]/table[1]/tr[6]/tc[1]", text="Architecture spec"),
        cell("/slide[2]/table[1]/tr[6]/tc[2]", text="Carol"),
        cell("/slide[2]/table[1]/tr[6]/tc[3]", text="Apr 20"),
        cell("/slide[2]/table[1]/tr[6]/tc[4]", text="◐ WIP", color="FFC000"),

        # Section: "Phase 3"
        cell("/slide[2]/table[1]/tr[7]/tc[1]",
             text="◆ Phase 3 — Build", bold="true", fill="F4B084", gridSpan="4"),
        cell("/slide[2]/table[1]/tr[8]/tc[1]", text="Backend services"),
        cell("/slide[2]/table[1]/tr[8]/tc[2]", text="Dave"),
        cell("/slide[2]/table[1]/tr[8]/tc[3]", text="Jun 15"),
        cell("/slide[2]/table[1]/tr[8]/tc[4]", text="◯ Not started"),
        cell("/slide[2]/table[1]/tr[9]/tc[1]", text="Frontend UI"),
        cell("/slide[2]/table[1]/tr[9]/tc[2]", text="Eve"),
        cell("/slide[2]/table[1]/tr[9]/tc[3]", text="Jul 01"),
        cell("/slide[2]/table[1]/tr[9]/tc[4]", text="◯ Not started"),
    ]

    doc.batch(items)
    print(f"  shipped {len(items)} add/set commands")

print(f"Generated: {FILE}")
