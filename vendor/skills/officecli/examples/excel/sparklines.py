#!/usr/bin/env python3
"""
Sparklines Showcase — generates sparklines.xlsx exercising the full xlsx
`sparkline` element (in-cell mini charts, schemas/help/xlsx/sparkline.json).

Unlike the other excel/*.py (which shell out per command), this one drives the
**officecli Python SDK** (`pip install officecli-sdk`): one resident is started,
every write goes over the named pipe, and the whole dashboard is applied in a
single `doc.batch(...)` round-trip. Same `{"command","parent","type","props"}`
dict shape you'd put in an `officecli batch` list.

One dashboard sheet: a label column + 12 months of trend data per row, with a
sparkline in the cell adjacent to each data row. Demonstrates all three kinds:
  line    — plain, and with every point-highlight + per-point marker colours
  column  — high/low and first/last highlights, plain bars
  winLoss — negative points in their own colour (win-loss alias too)

Closes with a Get round-trip proving the canonical keys read back.

Usage:
  pip install officecli-sdk          # plus the `officecli` binary on PATH
  python3 sparklines.py
"""

import os
import sys
import subprocess

# --- locate the SDK: prefer an installed `officecli-sdk`, else the in-repo copy
try:
    import officecli  # pip install officecli-sdk
except ImportError:
    sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                    "..", "..", "sdk", "python"))
    import officecli

FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "sparklines.xlsx")

MONTH_COLS = ["B", "C", "D", "E", "F", "G", "H", "I", "J", "K", "L", "M"]
MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun",
          "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]

HDR = {"font.bold": "true", "fill": "1F4E79", "font.color": "FFFFFF"}


def cell(ref, value, **props):
    return {"command": "set", "path": f"/Sheet1/{ref}", "props": {"value": str(value), **props}}


def data_row(r, label, values):
    """Label in A, 12 monthly values across B..M."""
    items = [cell(f"A{r}", label, **{"font.bold": "true"})]
    items += [cell(f"{MONTH_COLS[i]}{r}", v) for i, v in enumerate(values)]
    return items


def sp(**props):
    """One `add sparkline` item in batch-shape."""
    return {"command": "add", "parent": "/Sheet1", "type": "sparkline", "props": props}


print("\n==========================================")
print(f"Generating sparklines showcase: {FILE}")
print("==========================================")

with officecli.create(FILE, "--force") as doc:

    items = []

    # ---- Header row: label · Jan..Dec · Trend ----
    items.append(cell("A1", "Region / Product", **HDR))
    items += [cell(f"{MONTH_COLS[i]}1", MONTHS[i], **HDR) for i in range(12)]
    items.append(cell("N1", "Trend", **HDR))

    # ---- Data rows ----
    items += data_row(2, "North",   [45, 52, 48, 61, 58, 67, 72, 69, 74, 81, 78, 90])
    items += data_row(3, "South",   [88, 84, 79, 72, 68, 61, 55, 49, 44, 40, 38, 35])
    items += data_row(4, "East",    [30, 55, 20, 70, 35, 82, 40, 90, 25, 60, 45, 100])
    items += data_row(5, "West",    [12, 15, 14, 18, 22, 25, 24, 28, 30, 33, 31, 40])
    items += data_row(6, "Central", [50, 48, 55, 52, 60, 58, 63, 61, 68, 66, 72, 70])
    items += data_row(7, "Online",  [-20, 15, -35, 40, -10, 55, -50, 30, -25, 60, -15, 80])
    items += data_row(8, "Kiosk",   [5, -8, 12, -3, 20, -15, 25, -6, 30, -18, 35, -10])

    # ---- Line sparklines (rows 2-3) ----
    # plain series colour + custom line weight
    items.append(sp(type="line", dataRange="B2:M2", location="N2", color="#4472C4", lineWeight="1.5"))
    # line + all point highlights + per-point marker colours + markers toggle
    items.append(sp(type="line", dataRange="B3:M3", location="N3", color="#ED7D31",
                    markers="true", highPoint="true", lowPoint="true",
                    firstPoint="true", lastPoint="true",
                    highMarkerColor="#00B050", lowMarkerColor="#FF0000",
                    firstMarkerColor="#7030A0", lastMarkerColor="#0070C0",
                    markersColor="#808080", lineWeight="2.25"))

    # ---- Column sparklines (rows 4-6) ----
    # high/low point highlight with marker colours
    items.append(sp(type="column", dataRange="B4:M4", location="N4", color="#70AD47",
                    highPoint="true", lowPoint="true",
                    highMarkerColor="#00B050", lowMarkerColor="#C00000"))
    # first/last point highlight
    items.append(sp(type="column", dataRange="B5:M5", location="N5", color="#5B9BD5",
                    firstPoint="true", lastPoint="true",
                    firstMarkerColor="#264478", lastMarkerColor="#0070C0"))
    # plain single-colour bars
    items.append(sp(type="column", dataRange="B6:M6", location="N6", color="#A5A5A5"))

    # ---- WinLoss sparklines (rows 7-8) ----
    # negative points highlighted in their own colour
    items.append(sp(type="winLoss", dataRange="B7:M7", location="N7", color="#4472C4",
                    negative="true", negativeColor="#C00000"))
    # win-loss alias (maps to winLoss) + high/low + negative
    items.append(sp(type="win-loss", dataRange="B8:M8", location="N8", color="#7030A0",
                    highPoint="true", lowPoint="true",
                    negative="true", negativeColor="#FF0000"))

    print(f"\n--- Applying {len(items)} batch items (data + sparklines) ---")
    doc.batch(items)

    # ---- Get round-trip: confirm canonical keys read back (in-session, over pipe) ----
    print("\n--- Round-trip readback (Get the sparklines) ---")
    for n in (1, 2, 4, 7):
        node = doc.send({"command": "get", "path": f"/Sheet1/sparkline[{n}]"})
        fmt = node.get("data", {}).get("results", [{}])[0].get("format", {})
        keys = ("type", "dataRange", "location", "color", "negativeColor",
                "markers", "highPoint", "lowPoint", "firstPoint", "lastPoint",
                "negative", "lineWeight")
        shown = {k: fmt.get(k) for k in keys if k in fmt}
        print(f"  /Sheet1/sparkline[{n}]: {shown}")

    doc.send({"command": "save"})
# context exit closes the resident, flushing the workbook to disk.

# Validate the SAVED file with a fresh one-shot process (NOT in-session): a
# sparkline group lives in the worksheet's x14 extension list, so validate from
# disk to confirm the extension serialized cleanly.
print("\n--- Validate (fresh process, from disk) ---")
r = subprocess.run(["officecli", "validate", FILE], capture_output=True, text=True)
print(" ", (r.stdout or r.stderr).strip().split("\n")[0])

print(f"\nCreated: {FILE}")
