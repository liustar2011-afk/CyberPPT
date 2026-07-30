#!/usr/bin/env python3
"""
Sheet Settings Showcase — generates sheet-settings.xlsx exercising the xlsx
`sheet` element's sheet-level property surface (schemas/help/xlsx/sheet.json):
the per-*worksheet* settings on <sheetView>, <pageSetup>, <headerFooter>,
<sheetPr>, <sheetProtection>, and the sheet's defined-names. Distinct from the
workbook-level settings in workbook-settings.{sh,py}.

Four themed sheets: freeze panes, print setup, headers/footers, display +
protection (plus a sorted sheet and a hidden sheet).

SDK twin of sheet-settings.sh. Drives the officecli Python SDK
(`pip install officecli-sdk`) and maps onto the shell script one-for-one:

    officecli.create(...)          ≈  officecli create + open  (file + resident)
    doc.send({...})                ≈  one officecli set/add    (one call each, no batch)
    doc.close()                    ≈  officecli close          (flush to disk)

Usage:
  pip install officecli-sdk          # plus the `officecli` binary on PATH
  python3 sheet-settings.py
"""

import os
import officecli  # pip install officecli-sdk

FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "sheet-settings.xlsx")

print("\n==========================================")
print(f"Generating sheet-settings showcase: {FILE}")
print("==========================================")

doc = officecli.create(FILE, "--force")      # create the .xlsx + start its resident

COLS = "ABCDEFGH"


def cell(path, **props):                      # one cell write = one `officecli set`
    doc.send({"command": "set", "path": path, "props": props})


def sheet(path, **props):                     # one sheet-container `set`
    doc.send({"command": "set", "path": path, "props": props})


def add_sheet(**props):                       # one `officecli add --type sheet`
    doc.send({"command": "add", "parent": "/", "type": "sheet", "props": props})


def hdr(name, *titles):                        # bold header row (row 1)
    for i, title in enumerate(titles):
        cell(f"/{name}/{COLS[i]}1", value=title, **{"font.bold": "true"})


def rows(name, start, data):                   # data rows from `start` down
    for r, values in enumerate(data, start=start):
        for i, v in enumerate(values):
            cell(f"/{name}/{COLS[i]}{r}", value=str(v))


# --- Sheet 1 — Freeze Panes (rename Sheet1) ---
print("\n--- 1-Freeze-Panes ---")
sheet("/Sheet1", name="1-Freeze-Panes")
hdr("1-Freeze-Panes", "Date", "Region", "Product", "Units", "Revenue")
rows("1-Freeze-Panes", 2, [
    ("2026-01", "North", "Widget", 120, 1140),
    ("2026-01", "South", "Gadget", 95, 1045),
    ("2026-02", "East", "Widget", 140, 1225),
    ("2026-02", "West", "Gizmo", 88, 968),
    ("2026-03", "North", "Gadget", 132, 1452),
])
# freeze panes: B2 freezes header row 1 AND first column A
sheet("/1-Freeze-Panes", freeze="B2")

# --- Sheet 2 — Print Setup ---
print("--- 2-Print-Setup ---")
add_sheet(name="2-Print-Setup")
hdr("2-Print-Setup", "Item", "Qty", "Unit", "Total")
rows("2-Print-Setup", 2, [
    ("Screws", 500, 0.02, 10.00),
    ("Bolts", 300, 0.05, 15.00),
    ("Washers", 800, 0.01, 8.00),
    ("Nuts", 450, 0.03, 13.50),
    ("Anchors", 120, 0.12, 14.40),
])
# print-only settings — verify via get, not visual render
sheet("/2-Print-Setup", **{
    "orientation": "landscape",
    "paperSize": "9",                          # 9 = A4
    "fitToPage": "1x1",                        # fit to one page
    "printArea": "A1:D6",
    "printTitleRows": "1:1",                   # repeat row 1 at top of each page
    "printTitleCols": "A:A",                   # repeat column A at left
    "margin.top": "1.0in", "margin.bottom": "1.0in",
    "margin.left": "0.5in", "margin.right": "0.5in",
    "margin.header": "0.3in", "margin.footer": "0.3in",
})

# --- Sheet 3 — Headers & Footers ---
print("--- 3-Headers-Footers ---")
add_sheet(name="3-Headers-Footers")
hdr("3-Headers-Footers", "Quarter", "Sales", "Target")
rows("3-Headers-Footers", 2, [
    ("Q1", 45000, 40000),
    ("Q2", 52000, 48000),
    ("Q3", 61000, 55000),
    ("Q4", 58000, 60000),
])
# Excel format codes pass through verbatim:
#   &L left  &C center  &R right   &P page num  &N page count  &D date  &F file
sheet("/3-Headers-Footers",
      header="&LQuarterly Report&C2026 Sales&R&D",
      footer="&LConfidential&CPage &P of &N&R&F")

# --- Sheet 4 — Display & Protection ---
print("--- 4-Display-Protection ---")
add_sheet(name="4-Display-Protection")
hdr("4-Display-Protection", "Metric", "Value")
rows("4-Display-Protection", 2, [
    ("Users", 1250),
    ("Sessions", 8400),
    ("Bounce", 32),
    ("Retention", 68),
])
# display: tab color, hide gridlines + headings, zoom, AutoFilter, RTL layout
sheet("/4-Display-Protection", **{
    "tabColor": "C0392B",
    "gridlines": "false",
    "headings": "false",
    "zoom": "125",
    "autoFilter": "A1:B5",
    "direction": "rtl",
})
# protection: enable + legacy password hash (do last — a protected sheet
# can't be sorted, so sorting is on its own sheet below)
sheet("/4-Display-Protection", protect="true", password="secret123")

# --- Sheet 5 — Sorted (sort can't coexist with protect) ---
print("--- 5-Sorted ---")
add_sheet(name="5-Sorted", tabColor="27AE60")
hdr("5-Sorted", "Name", "Score")
rows("5-Sorted", 2, [
    ("Carol", 88),
    ("Alice", 95),
    ("Bob", 72),
    ("Dave", 60),
])
sheet("/5-Sorted", sort="B desc")              # highest score first

# --- Sheet 6 — Hidden at creation ---
print("--- 6-Hidden ---")
add_sheet(name="6-Hidden", hidden="true")
cell("/6-Hidden/A1", value="Hidden data sheet")

# --- Get round-trip: confirm sheet-level keys read back (over the pipe) ---
print("\n--- Round-trip readback ---")
for path, keys in [
    ("/1-Freeze-Panes", ["freeze"]),
    ("/2-Print-Setup", ["orientation", "paperSize", "fitToPage", "printArea"]),
    ("/3-Headers-Footers", ["header", "footer"]),
    ("/4-Display-Protection", ["tabColor", "gridlines", "headings", "zoom",
                               "autoFilter", "direction", "protect"]),
    ("/5-Sorted", ["sort", "tabColor"]),
    ("/6-Hidden", ["hidden", "visibility"]),
]:
    node = doc.send({"command": "get", "path": path})
    fmt = node.get("data", {}).get("results", [{}])[0].get("format", {})
    got = {k: fmt[k] for k in keys if k in fmt}
    print(f"  {path}: {got}")

# --- Validate over the pipe (in-session, no extra process) ---
# `save` first so element order is normalized on disk before we validate —
# otherwise the pre-save in-memory model can report a transient schema-order
# note (e.g. sheetPr) that the save-time reserialization fixes.
print("\n--- Validate ---")
doc.send({"command": "save"})
v = doc.send({"command": "validate"})
print("  Validation passed: no errors found." if v.get("success")
      else f"  {v.get('warnings')}")

doc.close()                                   # stop the resident (flushes to disk)
print(f"\nCreated: {FILE}")
