#!/usr/bin/env python3
"""
Complex Tables Showcase — generates tables.docx exercising the docx `table`
element: merged cells (vmerge / gridspan / hmerge), multi-level headers, a color
heatmap, full table/row/cell property coverage (borders, layout, direction,
padding, cell run-formatting), an RTL table, and an inline `data=` shorthand
grid.

SDK twin of tables.sh (officecli CLI). The shell script generates three files
(tables.docx + tables.xlsx + tables.pptx); this twin produces the **Word**
document, tables.docx, command-for-command equivalent to the `$DOCX` section of
tables.sh.

It drives the **officecli Python SDK** (`pip install officecli-sdk`): one
resident is started and every paragraph/table/cell command is shipped over the
named pipe in a single `doc.batch(...)` round-trip. Each item is the same
`{"command","parent"/"path","type","props"}` dict you'd put in an
`officecli batch` list.

Usage:
  pip install officecli-sdk          # plus the `officecli` binary on PATH
  python3 tables.py
"""

import os
import sys

# --- locate the SDK: prefer an installed `officecli-sdk`, else the in-repo copy
try:
    import officecli  # pip install officecli-sdk
except ImportError:
    sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                    "..", "..", "sdk", "python"))
    import officecli

FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "tables.docx")


def para(text, **props):
    """One `add paragraph` item in batch-shape."""
    return {"command": "add", "parent": "/body", "type": "paragraph",
            "props": {"text": text, **props}}


def table(**props):
    """One `add table` item in batch-shape."""
    return {"command": "add", "parent": "/body", "type": "table", "props": props}


def cell(path, **props):
    """One `set` item targeting a tc/tr/tbl path in batch-shape."""
    return {"command": "set", "path": path, "props": props}


print(f"Building {FILE} ...")

with officecli.create(FILE, "--force") as doc:
    items = [
        para("Complex Table Examples", style="Heading1", align="center"),
        para(""),

        # ==================== Table 1: Project Progress Tracker ====================
        # vertical merge (vmerge=restart / continue) spanning 3 rows per project
        para("1. Project Progress Tracker", style="Heading2"),
        table(rows="7", cols="6"),

        # Header
        cell("/body/tbl[1]/tr[1]/tc[1]", text="Project Name", bold="true",
             shd="4472C4", color="FFFFFF", valign="center"),
        cell("/body/tbl[1]/tr[1]/tc[2]", text="Phase", bold="true",
             shd="4472C4", color="FFFFFF"),
        cell("/body/tbl[1]/tr[1]/tc[3]", text="Owner", bold="true",
             shd="4472C4", color="FFFFFF"),
        cell("/body/tbl[1]/tr[1]/tc[4]", text="Start Date", bold="true",
             shd="4472C4", color="FFFFFF"),
        cell("/body/tbl[1]/tr[1]/tc[5]", text="End Date", bold="true",
             shd="4472C4", color="FFFFFF"),
        cell("/body/tbl[1]/tr[1]/tc[6]", text="Progress", bold="true",
             shd="4472C4", color="FFFFFF"),

        # Project A - Smart Office System (merge 3 rows)
        cell("/body/tbl[1]/tr[2]/tc[1]", text="Smart Office System",
             vmerge="restart", valign="center", shd="D9E2F3"),
        cell("/body/tbl[1]/tr[2]/tc[2]", text="Requirements"),
        cell("/body/tbl[1]/tr[2]/tc[3]", text="John"),
        cell("/body/tbl[1]/tr[2]/tc[4]", text="2025-01-05"),
        cell("/body/tbl[1]/tr[2]/tc[5]", text="2025-02-15"),
        cell("/body/tbl[1]/tr[2]/tc[6]", text="100%", color="00B050"),

        cell("/body/tbl[1]/tr[3]/tc[1]", text="", vmerge="continue", shd="D9E2F3"),
        cell("/body/tbl[1]/tr[3]/tc[2]", text="Development"),
        cell("/body/tbl[1]/tr[3]/tc[3]", text="Sarah"),
        cell("/body/tbl[1]/tr[3]/tc[4]", text="2025-02-16"),
        cell("/body/tbl[1]/tr[3]/tc[5]", text="2025-06-30"),
        cell("/body/tbl[1]/tr[3]/tc[6]", text="75%", color="FFC000"),

        cell("/body/tbl[1]/tr[4]/tc[1]", text="", vmerge="continue", shd="D9E2F3"),
        cell("/body/tbl[1]/tr[4]/tc[2]", text="Testing"),
        cell("/body/tbl[1]/tr[4]/tc[3]", text="Mike"),
        cell("/body/tbl[1]/tr[4]/tc[4]", text="2025-07-01"),
        cell("/body/tbl[1]/tr[4]/tc[5]", text="2025-08-31"),
        cell("/body/tbl[1]/tr[4]/tc[6]", text="0%", color="FF0000"),

        # Project B - Data Platform Upgrade (merge 3 rows)
        cell("/body/tbl[1]/tr[5]/tc[1]", text="Data Platform Upgrade",
             vmerge="restart", valign="center", shd="E2EFDA"),
        cell("/body/tbl[1]/tr[5]/tc[2]", text="Architecture"),
        cell("/body/tbl[1]/tr[5]/tc[3]", text="Emily"),
        cell("/body/tbl[1]/tr[5]/tc[4]", text="2025-03-01"),
        cell("/body/tbl[1]/tr[5]/tc[5]", text="2025-04-15"),
        cell("/body/tbl[1]/tr[5]/tc[6]", text="100%", color="00B050"),

        cell("/body/tbl[1]/tr[6]/tc[1]", text="", vmerge="continue", shd="E2EFDA"),
        cell("/body/tbl[1]/tr[6]/tc[2]", text="Migration"),
        cell("/body/tbl[1]/tr[6]/tc[3]", text="David"),
        cell("/body/tbl[1]/tr[6]/tc[4]", text="2025-04-16"),
        cell("/body/tbl[1]/tr[6]/tc[5]", text="2025-07-31"),
        cell("/body/tbl[1]/tr[6]/tc[6]", text="40%", color="FFC000"),

        cell("/body/tbl[1]/tr[7]/tc[1]", text="", vmerge="continue", shd="E2EFDA"),
        cell("/body/tbl[1]/tr[7]/tc[2]", text="Acceptance"),
        cell("/body/tbl[1]/tr[7]/tc[3]", text="Lisa"),
        cell("/body/tbl[1]/tr[7]/tc[4]", text="2025-08-01"),
        cell("/body/tbl[1]/tr[7]/tc[5]", text="2025-09-30"),
        cell("/body/tbl[1]/tr[7]/tc[6]", text="0%", color="FF0000"),

        # ==================== Table 2: Financial Statement ====================
        # gridspan horizontal merge + vmerge vertical merge in a two-row header
        para(""),
        para("2. Financial Statement", style="Heading2"),
        table(rows="8", cols="5"),

        # Header row 1 - gridspan=2 automatically removes the merged tc
        cell("/body/tbl[2]/tr[1]/tc[1]", text="Category", bold="true",
             shd="2E75B6", color="FFFFFF", vmerge="restart", valign="center"),
        cell("/body/tbl[2]/tr[1]/tc[2]", text="Line Item", bold="true",
             shd="2E75B6", color="FFFFFF", vmerge="restart", valign="center"),
        cell("/body/tbl[2]/tr[1]/tc[3]", text="Amount (10K USD)", bold="true",
             shd="2E75B6", color="FFFFFF", gridspan="2", align="center"),
        # gridspan=2 removed original tc[4], original tc[5] becomes tc[4]
        cell("/body/tbl[2]/tr[1]/tc[4]", text="Notes", bold="true",
             shd="2E75B6", color="FFFFFF", vmerge="restart", valign="center"),

        # Header row 2
        cell("/body/tbl[2]/tr[2]/tc[1]", text="", vmerge="continue", shd="2E75B6"),
        cell("/body/tbl[2]/tr[2]/tc[2]", text="", vmerge="continue", shd="2E75B6"),
        cell("/body/tbl[2]/tr[2]/tc[3]", text="Budget", bold="true",
             shd="5B9BD5", color="FFFFFF", align="center"),
        cell("/body/tbl[2]/tr[2]/tc[4]", text="Actual", bold="true",
             shd="5B9BD5", color="FFFFFF", align="center"),
        cell("/body/tbl[2]/tr[2]/tc[5]", text="", vmerge="continue", shd="2E75B6"),

        # Revenue (merge 3 rows)
        cell("/body/tbl[2]/tr[3]/tc[1]", text="Revenue", vmerge="restart",
             valign="center", shd="DEEAF6", bold="true"),
        cell("/body/tbl[2]/tr[3]/tc[2]", text="Product Sales"),
        cell("/body/tbl[2]/tr[3]/tc[3]", text="500.00", align="right"),
        cell("/body/tbl[2]/tr[3]/tc[4]", text="523.50", align="right", color="00B050"),
        cell("/body/tbl[2]/tr[3]/tc[5]", text="Exceeded"),

        cell("/body/tbl[2]/tr[4]/tc[1]", text="", vmerge="continue", shd="DEEAF6"),
        cell("/body/tbl[2]/tr[4]/tc[2]", text="Consulting Services"),
        cell("/body/tbl[2]/tr[4]/tc[3]", text="200.00", align="right"),
        cell("/body/tbl[2]/tr[4]/tc[4]", text="185.30", align="right", color="FF0000"),
        cell("/body/tbl[2]/tr[4]/tc[5]", text="Below target"),

        cell("/body/tbl[2]/tr[5]/tc[1]", text="", vmerge="continue", shd="DEEAF6"),
        cell("/body/tbl[2]/tr[5]/tc[2]", text="Tech Licensing"),
        cell("/body/tbl[2]/tr[5]/tc[3]", text="80.00", align="right"),
        cell("/body/tbl[2]/tr[5]/tc[4]", text="92.00", align="right", color="00B050"),
        cell("/body/tbl[2]/tr[5]/tc[5]", text="New partners"),

        # Expenses (merge 3 rows)
        cell("/body/tbl[2]/tr[6]/tc[1]", text="Expenses", vmerge="restart",
             valign="center", shd="FFF2CC", bold="true"),
        cell("/body/tbl[2]/tr[6]/tc[2]", text="Labor Cost"),
        cell("/body/tbl[2]/tr[6]/tc[3]", text="320.00", align="right"),
        cell("/body/tbl[2]/tr[6]/tc[4]", text="335.00", align="right", color="FF0000"),
        cell("/body/tbl[2]/tr[6]/tc[5]", text="New hires"),

        cell("/body/tbl[2]/tr[7]/tc[1]", text="", vmerge="continue", shd="FFF2CC"),
        cell("/body/tbl[2]/tr[7]/tc[2]", text="Operating Expenses"),
        cell("/body/tbl[2]/tr[7]/tc[3]", text="150.00", align="right"),
        cell("/body/tbl[2]/tr[7]/tc[4]", text="142.80", align="right", color="00B050"),
        cell("/body/tbl[2]/tr[7]/tc[5]", text="Cost savings"),

        cell("/body/tbl[2]/tr[8]/tc[1]", text="", vmerge="continue", shd="FFF2CC"),
        cell("/body/tbl[2]/tr[8]/tc[2]", text="R&D Investment"),
        cell("/body/tbl[2]/tr[8]/tc[3]", text="180.00", align="right"),
        cell("/body/tbl[2]/tr[8]/tc[4]", text="195.50", align="right"),
        cell("/body/tbl[2]/tr[8]/tc[5]", text="Strategic investment"),

        # ==================== Table 3: Skill Assessment Matrix ====================
        # color heatmap: Expert=00B050 Proficient=92D050 Familiar=FFC000 Beginner=FF0000
        para(""),
        para("3. Skill Assessment Matrix", style="Heading2"),
        table(rows="6", cols="7"),

        # Header
        cell("/body/tbl[3]/tr[1]/tc[1]", text="Name/Skill", bold="true",
             shd="002060", color="FFFFFF", align="center"),
        cell("/body/tbl[3]/tr[1]/tc[2]", text="Python", bold="true",
             shd="002060", color="FFFFFF", align="center"),
        cell("/body/tbl[3]/tr[1]/tc[3]", text="Java", bold="true",
             shd="002060", color="FFFFFF", align="center"),
        cell("/body/tbl[3]/tr[1]/tc[4]", text="Frontend", bold="true",
             shd="002060", color="FFFFFF", align="center"),
        cell("/body/tbl[3]/tr[1]/tc[5]", text="Database", bold="true",
             shd="002060", color="FFFFFF", align="center"),
        cell("/body/tbl[3]/tr[1]/tc[6]", text="DevOps", bold="true",
             shd="002060", color="FFFFFF", align="center"),
        cell("/body/tbl[3]/tr[1]/tc[7]", text="AI/ML", bold="true",
             shd="002060", color="FFFFFF", align="center"),
    ]

    # Skill rows: person name in tc[1], then 6 graded skill cells (text:color).
    skill_rows = [
        (2, "John",  ["Expert:00B050", "Proficient:92D050", "Familiar:FFC000",
                      "Expert:00B050", "Familiar:FFC000", "Expert:00B050"]),
        (3, "Sarah", ["Proficient:92D050", "Expert:00B050", "Expert:00B050",
                      "Proficient:92D050", "Familiar:FFC000", "Beginner:FF0000"]),
        (4, "Mike",  ["Familiar:FFC000", "Familiar:FFC000", "Expert:00B050",
                      "Familiar:FFC000", "Expert:00B050", "Proficient:92D050"]),
        (5, "Emily", ["Expert:00B050", "Beginner:FF0000", "Familiar:FFC000",
                      "Expert:00B050", "Proficient:92D050", "Familiar:FFC000"]),
        (6, "David", ["Proficient:92D050", "Proficient:92D050", "Proficient:92D050",
                      "Expert:00B050", "Expert:00B050", "Expert:00B050"]),
    ]
    for row, person, cells in skill_rows:
        items.append(cell(f"/body/tbl[3]/tr[{row}]/tc[1]", text=person,
                          bold="true", shd="D6DCE4", align="center"))
        for i, spec in enumerate(cells):
            text, clr = spec.split(":", 1)
            items.append(cell(f"/body/tbl[3]/tr[{row}]/tc[{i + 2}]", text=text,
                              shd=clr, color="FFFFFF", align="center", bold="true"))

    items += [
        # ==================== Table 4: Property Coverage Table ====================
        # border.all + cellSpacing + colWidths + direction + indent + layout + padding
        para(""),
        para("4. Property Coverage (border / layout / direction / cell formatting)",
             style="Heading2"),
        table(rows="3", cols="4",
              **{"border.all": "single;8;2E74B5",
                 "colWidths": "2500,2500,2500,2500",
                 "cellSpacing": "20",
                 "indent": "200",
                 "layout": "fixed",
                 "padding": "80"}),

        # Override outer-edge borders after creation
        cell("/body/tbl[4]", **{"border.top": "double;8;1F3864"}),
        cell("/body/tbl[4]", **{"border.bottom": "double;8;1F3864"}),
        cell("/body/tbl[4]", **{"border.left": "double;8;1F3864"}),
        cell("/body/tbl[4]", **{"border.right": "double;8;1F3864"}),
        cell("/body/tbl[4]", **{"border.horizontal": "single;4;9DC3E6"}),
        cell("/body/tbl[4]", **{"border.vertical": "single;4;9DC3E6"}),

        # Header row: header=true + height.exact
        cell("/body/tbl[4]/tr[1]", header="true", **{"height.exact": "400"}),
        cell("/body/tbl[4]/tr[1]/tc[1]", text="Cell Borders", bold="true",
             fill="2E74B5", color="FFFFFF"),
        cell("/body/tbl[4]/tr[1]/tc[2]", text="Run Formatting", bold="true",
             fill="2E74B5", color="FFFFFF"),
        cell("/body/tbl[4]/tr[1]/tc[3]", text="Merge / Flow", bold="true",
             fill="2E74B5", color="FFFFFF"),
        cell("/body/tbl[4]/tr[1]/tc[4]", text="Padding / Grid", bold="true",
             fill="2E74B5", color="FFFFFF"),

        # Data row 2: cell borders (border.all, tl2br, tr2bl), direction, nowrap
        cell("/body/tbl[4]/tr[2]/tc[1]", text="border.all + tl2br + tr2bl",
             **{"border.all": "single;8;FF0000",
                "border.tl2br": "single;4;0000FF",
                "border.tr2bl": "single;4;0000FF"}),
        cell("/body/tbl[4]/tr[2]/tc[2]",
             text="font + italic + strike + underline + highlight",
             font="Times New Roman", italic="true", strike="true",
             underline="single", highlight="yellow"),
        cell("/body/tbl[4]/tr[2]/tc[3]",
             text="direction=rtl + nowrap + textDirection=btlr",
             direction="rtl", nowrap="true", textDirection="btlr"),
        cell("/body/tbl[4]/tr[2]/tc[4]", text="padding per side + skipGridSync",
             **{"padding.top": "50", "padding.bottom": "150",
                "padding.left": "80", "padding.right": "80"}),

        # Data row 3: border.top/bottom/left/right per cell, fitText, skipGridSync
        cell("/body/tbl[4]/tr[3]/tc[1]", text="border.top + border.bottom",
             **{"border.top": "single;8;FF0000", "border.bottom": "single;8;0000FF"}),
        cell("/body/tbl[4]/tr[3]/tc[2]", text="border.left + border.right",
             **{"border.left": "single;8;00FF00", "border.right": "single;8;FF00FF"}),
        cell("/body/tbl[4]/tr[3]/tc[3]", text="fitText squeezes text to cell width",
             fitText="true"),
        cell("/body/tbl[4]/tr[3]/tc[4]", text="width + skipGridSync",
             width="2500", skipGridSync="true"),

        # ==================== Table 5: hmerge (horizontal merge) ====================
        # hmerge=restart on tc[1] spans 2 cols and absorbs tc[2]; tc[3]->tc[2] after
        table(rows="2", cols="3", **{"border.all": "single;4;808080"}),
        # Set the non-merged cell before applying hmerge=restart (which removes tc[2])
        cell("/body/tbl[5]/tr[1]/tc[3]", text="normal tc"),
        cell("/body/tbl[5]/tr[1]/tc[1]", text="hmerge restart (spans 2 cols)",
             hmerge="restart"),
        # After hmerge=restart, original tc[3] is now tc[2]
        cell("/body/tbl[5]/tr[2]/tc[1]", text="row 2 col 1"),
        cell("/body/tbl[5]/tr[2]/tc[2]", text="row 2 col 2"),
        cell("/body/tbl[5]/tr[2]/tc[3]", text="row 2 col 3"),

        # ==================== Table 6: RTL table ====================
        table(rows="2", cols="2",
              **{"direction": "rtl", "border.all": "single;8;C00000"}),
        cell("/body/tbl[6]/tr[1]/tc[1]", text="RTL table", bold="true"),
        cell("/body/tbl[6]/tr[1]/tc[2]", text="column order mirrored"),
        cell("/body/tbl[6]/tr[2]/tc[1]", text="row 2 col 1"),
        cell("/body/tbl[6]/tr[2]/tc[2]", text="row 2 col 2"),

        # ==================== Table 7: inline data= shorthand ====================
        # rows separated by ';', cells by ',' — builds the whole grid in one prop
        table(**{"data": "Region,Q1,Q2;North,120,150;South,90,110",
                 "border.all": "single;4;808080"}),
    ]

    doc.batch(items)
    print(f"  added {len(items)} paragraphs/tables/cell-sets")

print(f"Generated: {FILE}")
