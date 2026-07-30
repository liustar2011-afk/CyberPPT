#!/usr/bin/env python3
"""
Real-world PowerPoint table showcase — generates tables-financial.pptx, a
quarterly financial-report deck. Combines: built-in table style, header
banding, per-cell fills for traffic-light status, gridSpan section headers,
right-aligned numbers, and a totals row.

SDK twin of tables-financial.sh (officecli CLI). Both produce an equivalent
tables-financial.pptx. This one drives the **officecli Python SDK**
(`pip install officecli-sdk`): one resident is started and every slide, shape,
table and cell edit is shipped over the named pipe in a single `doc.batch(...)`
round-trip. Each item is the same `{"command","parent"/"path","type","props"}`
dict you'd put in an `officecli batch` list.

Usage:
  pip install officecli-sdk          # plus the `officecli` binary on PATH
  python3 tables-financial.py
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

FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "tables-financial.pptx")

# Theme colors
NAVY = "1F3864"; STEEL = "2E75B6"; PALE = "DEEAF6"
GREEN = "00B050"; AMBER = "FFC000"; RED = "C00000"


def add_slide():
    # In batch shape a slide hangs off the presentation root "/".
    # (The CLI's `add <file> /presentation/slides --type slide` form maps to this.)
    return {"command": "add", "parent": "/", "type": "slide", "props": {}}


def add_shape(slide, **props):
    return {"command": "add", "parent": f"/slide[{slide}]", "type": "shape", "props": props}


def add_table(slide, **props):
    return {"command": "add", "parent": f"/slide[{slide}]", "type": "table", "props": props}


def cell(slide, r, c, **props):
    return {"command": "set", "path": f"/slide[{slide}]/table[1]/tr[{r}]/tc[{c}]", "props": props}


def set_row(slide, r, label, q1, q2, q3, q4, tot, emphasize=False):
    """A P&L data row: label + four quarter columns (right-aligned) + bold total.
    `emphasize` paints the whole row PALE (subtotal rows)."""
    fill = {"fill": PALE} if emphasize else {}
    return [
        cell(slide, r, 1, text=label, **fill),
        cell(slide, r, 2, text=q1, align="right", **fill),
        cell(slide, r, 3, text=q2, align="right", **fill),
        cell(slide, r, 4, text=q3, align="right", **fill),
        cell(slide, r, 5, text=q4, align="right", **fill),
        cell(slide, r, 6, text=tot, align="right", bold="true", **fill),
    ]


print(f"Building {FILE} ...")

with officecli.create(FILE, "--force") as doc:
    items = []

    # ==================== Slide 1: Title ====================
    items += [
        add_slide(),
        add_shape(1, text="Q4 2025 Financial Review", size="44", bold="true", color=NAVY,
                  x="1in", y="2.5in", width="11in", height="1.2in", align="center"),
        add_shape(1, text="Revenue · Expenses · Margin · Forecast", size="22", color="595959",
                  x="1in", y="4in", width="11in", height="0.8in", align="center"),
    ]

    # ==================== Slide 2: Quarterly P&L (sections via gridSpan) ====================
    items += [
        add_slide(),
        add_shape(2, text="Quarterly P&L (USD, thousands)", size="28", bold="true", color=NAVY,
                  x="0.5in", y="0.3in", width="12in", height="0.6in"),
        add_table(2, x="0.5in", y="1.2in", width="12in", height="5.5in", rows="11", cols="6"),
    ]

    # Header
    for c, t in [(1, "Line Item"), (2, "Q1"), (3, "Q2"), (4, "Q3"), (5, "Q4"), (6, "FY Total")]:
        items.append(cell(2, 1, c, text=t, bold="true", color="FFFFFF", fill=NAVY, align="center"))

    # Section: Revenue
    items.append(cell(2, 2, 1, text="REVENUE", bold="true", fill=STEEL, color="FFFFFF", gridSpan="6"))
    items += set_row(2, 3, "  Product Sales", "1,200", "1,350", "1,480", "1,720", "5,750")
    items += set_row(2, 4, "  Services",        "480",   "520",   "590",   "640", "2,230")
    items += set_row(2, 5, "  Licensing",       "120",   "140",   "165",   "195",   "620")
    items += set_row(2, 6, "  Subtotal",      "1,800", "2,010", "2,235", "2,555", "8,600", emphasize=True)

    # Section: Expenses
    items.append(cell(2, 7, 1, text="EXPENSES", bold="true", fill=STEEL, color="FFFFFF", gridSpan="6"))
    items += set_row(2, 8,  "  COGS",         "720",   "810",   "895", "1,025", "3,450")
    items += set_row(2, 9,  "  Operating",    "380",   "410",   "445",   "490", "1,725")
    items += set_row(2, 10, "  Subtotal",   "1,100", "1,220", "1,340", "1,515", "5,175", emphasize=True)

    # Net row
    items.append(cell(2, 11, 1, text="NET INCOME", bold="true", fill=GREEN, color="FFFFFF"))
    for c, v in [(2, "700"), (3, "790"), (4, "895"), (5, "1,040"), (6, "3,425")]:
        items.append(cell(2, 11, c, text=v, align="right", bold="true", fill=GREEN, color="FFFFFF"))

    # ==================== Slide 3: Risk register (traffic-light fills) ====================
    items += [
        add_slide(),
        add_shape(3, text="Risk Register", size="28", bold="true", color=NAVY,
                  x="0.5in", y="0.3in", width="12in", height="0.6in"),
        add_table(3, x="0.5in", y="1.2in", width="12in", height="4in",
                  style="medium2", firstRow="true", bandedRows="true",
                  data="Risk,Impact,Likelihood,Owner,Status;"
                       "FX volatility,High,Medium,CFO,At risk;"
                       "Supply chain,Medium,Low,COO,On track;"
                       "Talent attrition,High,High,CPO,Critical;"
                       "Reg compliance,Medium,Medium,GC,On track;"
                       "Cybersecurity,High,Low,CTO,On track"),
        # Color the Status column (col 5, rows 2..6)
        cell(3, 2, 5, text="At risk", fill=AMBER, bold="true", align="center"),
        cell(3, 3, 5, text="On track", fill=GREEN, color="FFFFFF", bold="true", align="center"),
        cell(3, 4, 5, text="Critical", fill=RED, color="FFFFFF", bold="true", align="center"),
        cell(3, 5, 5, text="On track", fill=GREEN, color="FFFFFF", bold="true", align="center"),
        cell(3, 6, 5, text="On track", fill=GREEN, color="FFFFFF", bold="true", align="center"),
    ]

    # ==================== Slide 4: KPI summary (small table) ====================
    items += [
        add_slide(),
        add_shape(4, text="KPI Summary", size="28", bold="true", color=NAVY,
                  x="0.5in", y="0.3in", width="12in", height="0.6in"),
        add_table(4, x="2in", y="1.5in", width="9in", height="3.5in",
                  style="medium4", firstRow="true", firstCol="true", lastRow="true",
                  data="Metric,Target,Actual,Variance;"
                       "Revenue ($M),8.0,8.6,+7.5%;"
                       "Gross Margin,38%,40.1%,+2.1pp;"
                       "Op Margin,18%,19.8%,+1.8pp;"
                       "CAC Payback,14 mo,12 mo,-2 mo;"
                       "Total,—,—,Beat"),
    ]

    doc.batch(items)
    print(f"  applied {len(items)} batch items")

    doc.send({"command": "save"})
# context exit closes the resident, flushing the deck to disk.

print(f"Generated: {FILE}")
