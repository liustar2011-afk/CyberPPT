#!/usr/bin/env python3
"""
Slicer Showcase — generates slicers.xlsx with a PivotTable and 3 slicers.

Slicers are the interactive button panels that filter a PivotTable. In OOXML a
slicer is NOT free-standing: it is anchored to a *pivot cache field*, so it
always binds to an existing PivotTable via `pivotTable=` + `field=`. This
script builds the prerequisites first (source data → PivotTable), then adds
several slicers on different fields of that pivot.

SDK twin of slicers.sh (officecli CLI). Both produce an equivalent slicers.xlsx.
This one drives the **officecli Python SDK** (`pip install officecli-sdk`): one
resident is started, the source-data cell writes ship in a single `doc.batch(...)`
round-trip, and each pivot/slicer is one `add` item shipped over the named pipe.
Each item is the same `{"command","parent","type","props"}` dict you'd put in an
`officecli batch` list.

See slicers.md for a per-slicer guide.

Usage:
  pip install officecli-sdk          # plus the `officecli` binary on PATH
  python3 slicers.py
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

FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "slicers.xlsx")


def slicer(sheet, **props):
    """One `add slicer` item in batch-shape, anchored on the given sheet."""
    return {"command": "add", "parent": f"/{sheet}", "type": "slicer", "props": props}


print(f"Building {FILE} ...")

with officecli.create(FILE, "--force") as doc:

    # ==========================================================================
    # Source data — a realistic sales table: Region / Product / Quarter / Sales.
    # batch is used here only for speed (many cell writes in one round-trip).
    # ==========================================================================
    print("\n--- Populating source data ---")

    data_items = []
    for j, h in enumerate(["Region", "Product", "Quarter", "Sales"]):
        data_items.append({"command": "set", "path": f"/Sheet1/{'ABCD'[j]}1",
                           "props": {"text": h}})

    rows = [
        ("North", "Laptop", "Q1", 12500),
        ("North", "Phone",  "Q2", 8900),
        ("North", "Tablet", "Q3", 6200),
        ("South", "Laptop", "Q1", 22000),
        ("South", "Phone",  "Q2", 18500),
        ("South", "Tablet", "Q4", 7800),
        ("East",  "Laptop", "Q2", 19500),
        ("East",  "Phone",  "Q3", 13800),
        ("East",  "Tablet", "Q1", 5400),
        ("West",  "Laptop", "Q4", 25000),
        ("West",  "Phone",  "Q2", 16800),
        ("West",  "Tablet", "Q3", 8900),
    ]
    for i, row in enumerate(rows):
        for j, val in enumerate(row):
            data_items.append({"command": "set", "path": f"/Sheet1/{'ABCD'[j]}{i+2}",
                               "props": {"text": str(val)}})

    doc.batch(data_items)

    # ==========================================================================
    # The slicer SOURCE — a PivotTable. Slicers anchor to this pivot's cache
    # fields.
    #
    # officecli add slicers.xlsx /Dashboard --type pivottable \
    #   --prop source=Sheet1!A1:D13 \
    #   --prop rows=Region \
    #   --prop cols=Quarter \
    #   --prop values=Sales:sum \
    #   --prop layout=outline \
    #   --prop grandtotals=both \
    #   --prop name=SalesPivot \
    #   --prop style=PivotStyleMedium9
    # ==========================================================================
    print("\n--- Dashboard PivotTable (slicer source) ---")
    doc.send({"command": "add", "parent": "/", "type": "sheet",
              "props": {"name": "Dashboard"}})
    doc.send({"command": "add", "parent": "/Dashboard", "type": "pivottable",
              "props": {"source": "Sheet1!A1:D13", "rows": "Region",
                        "cols": "Quarter", "values": "Sales:sum",
                        "layout": "outline", "grandtotals": "both",
                        "name": "SalesPivot", "style": "PivotStyleMedium9"}})

    # ==========================================================================
    # Slicers — each binds to SalesPivot via a different cache field.
    # ==========================================================================

    # --------------------------------------------------------------------------
    # Slicer 1: Region
    #
    # officecli add slicers.xlsx /Dashboard --type slicer \
    #   --prop pivotTable=/Dashboard/pivottable[1] \
    #   --prop field=Region \
    #   --prop caption='Filter by Region' \
    #   --prop columnCount=2 \
    #   --prop rowHeight=250000 \
    #   --prop name=RegionSlicer
    #
    # Features: pivotTable= (full path reference), field=Region, custom caption,
    #   columnCount=2 (two-column button grid), rowHeight in EMU, explicit name
    # --------------------------------------------------------------------------
    print("\n--- Slicer: Region ---")
    doc.send(slicer("Dashboard",
                    pivotTable="/Dashboard/pivottable[1]",
                    field="Region",
                    caption="Filter by Region",
                    columnCount="2",
                    rowHeight="250000",
                    name="RegionSlicer"))

    # --------------------------------------------------------------------------
    # Slicer 2: Product
    #
    # officecli add slicers.xlsx /Dashboard --type slicer \
    #   --prop pivotTable=SalesPivot \
    #   --prop field=Product \
    #   --prop caption='Filter by Product' \
    #   --prop columnCount=3 \
    #   --prop name=ProductSlicer
    #
    # Features: pivotTable= by BARE NAME (resolves against the host sheet's
    #   pivots), columnCount=3 (wide grid)
    # --------------------------------------------------------------------------
    print("\n--- Slicer: Product ---")
    doc.send(slicer("Dashboard",
                    pivotTable="SalesPivot",
                    field="Product",
                    caption="Filter by Product",
                    columnCount="3",
                    name="ProductSlicer"))

    # --------------------------------------------------------------------------
    # Slicer 3: Quarter
    #
    # officecli add slicers.xlsx /Dashboard --type slicer \
    #   --prop pivotTable=SalesPivot \
    #   --prop field=Quarter \
    #   --prop columnCount=1 \
    #   --prop name=QuarterSlicer
    #
    # Features: caption OMITTED — defaults to the field name ("Quarter");
    #   rowHeight OMITTED — defaults to 225425 EMU (~17.5pt). Minimal slicer.
    # --------------------------------------------------------------------------
    print("\n--- Slicer: Quarter ---")
    doc.send(slicer("Dashboard",
                    pivotTable="SalesPivot",
                    field="Quarter",
                    columnCount="1",
                    name="QuarterSlicer"))

    # ==========================================================================
    # Modify an existing slicer with `set` (caption + columnCount are settable;
    # `field` is add-time only and Set intentionally ignores it).
    #
    # officecli set slicers.xlsx /Dashboard/slicer[1] \
    #   --prop caption=Region --prop columnCount=1
    # ==========================================================================
    print("\n--- Set: slicer[1] caption + columnCount ---")
    doc.send({"command": "set", "path": "/Dashboard/slicer[1]",
              "props": {"caption": "Region", "columnCount": "1"}})

    doc.send({"command": "save"})

print(f"\nDone! Generated: {FILE}")
print("  Sheet1 (source data) + Dashboard (1 PivotTable + 3 slicers)")
