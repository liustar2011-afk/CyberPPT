#!/usr/bin/env python3
"""
Doughnut Charts Showcase — generates charts-doughnut.pptx exercising the pptx
`chart` element with chartType=doughnut across 8 slides.

  Slide 1  holeSize variants      holeSize=10/30/55/75
  Slide 2  Multi-ring             two-series + three-series concentric rings
  Slide 3  firstSliceAngle        0 / 90 / 180 / 270
  Slide 4  Data labels            percent / category / value, leaderlines, labelfont
  Slide 5  Series styling         colors, gradient, seriesoutline, seriesshadow, transparency
  Slide 6  Title & legend         title.* + legend positions + legendFont
  Slide 7  Backgrounds            chartareafill, plotFill, chartborder, roundedcorners
  Slide 8  Presets & per-series   preset bundles + chart-series Set

SDK twin of charts-doughnut.sh (officecli CLI). Both produce an equivalent
charts-doughnut.pptx. This one drives the **officecli Python SDK**
(`pip install officecli-sdk`): one resident is started and every slide, title
shape and chart is shipped over the named pipe in `doc.batch(...)` round-trips.
Each item is the same `{"command","parent","type","props"}` dict you'd put in an
`officecli batch` list. batch runs with force=True so a prop a future build
doesn't yet support is skipped (forward-compat) rather than aborting the run.

Usage:
  pip install officecli-sdk          # plus the `officecli` binary on PATH
  python3 charts-doughnut.py
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

FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "charts-doughnut.pptx")

# --- shared geometry & data -------------------------------------------------
TL = {"x": "0.3in", "y": "1.05in", "width": "6.1in", "height": "3in"}
TR = {"x": "6.95in", "y": "1.05in", "width": "6.1in", "height": "3in"}
BL = {"x": "0.3in", "y": "4.25in", "width": "6.1in", "height": "3in"}
BR = {"x": "6.95in", "y": "4.25in", "width": "6.1in", "height": "3in"}
CATS = "North,South,East,West"
D = "Share:30,25,28,17"
D2 = "Last:25,30,25,20;This:30,25,28,17"
D3 = "Region1:30,25,28,17;Region2:25,30,20,25;Region3:20,25,30,25"


def slide():
    """One `add slide` item in batch-shape."""
    return {"command": "add", "parent": "/", "type": "slide", "props": {}}


def title(n, text):
    """One `add shape` item (slide heading) in batch-shape."""
    return {"command": "add", "parent": f"/slide[{n}]", "type": "shape",
            "props": {"text": text, "size": "24", "bold": "true", "autoFit": "normal",
                      "x": "0.5in", "y": "0.3in", "width": "12.3in", "height": "0.6in"}}


def ch(n, box, props):
    """One `add chart` item in batch-shape (box geometry merged with props)."""
    return {"command": "add", "parent": f"/slide[{n}]", "type": "chart",
            "props": {**box, **props}}


print(f"Building {FILE} ...")

with officecli.create(FILE, "--force") as doc:

    # ---- Slide 1: holeSize — 10 / 30 / 55 / 75 ----
    items = [slide(), title(1, "holeSize — 10 / 30 / 55 / 75")]
    for box, h in zip([TL, TR, BL, BR], [10, 30, 55, 75]):
        items.append(ch(1, box, {"chartType": "doughnut", "title": f"holeSize={h}",
                                  "holeSize": str(h), "legend": "right", "varyColors": "true",
                                  "categories": CATS, "data": D}))
    doc.batch(items)

    # ---- Slide 2: Multi-ring — concentric series ----
    items = [slide(), title(2, "Multi-ring — concentric series")]
    items.append(ch(2, TL, {"chartType": "doughnut", "title": "single ring", "holeSize": "50",
                            "legend": "right", "categories": CATS, "data": D}))
    items.append(ch(2, TR, {"chartType": "doughnut", "title": "two rings", "holeSize": "40",
                            "legend": "right", "categories": CATS, "data": D2}))
    items.append(ch(2, BL, {"chartType": "doughnut", "title": "three rings", "holeSize": "30",
                            "legend": "right", "categories": CATS, "data": D3}))
    items.append(ch(2, BR, {"chartType": "doughnut", "title": "two rings + dataLabels=percent",
                            "holeSize": "40", "dataLabels": "percent", "legend": "right",
                            "categories": CATS, "data": D2}))
    doc.batch(items)

    # ---- Slide 3: First slice angle — 0 / 90 / 180 / 270 ----
    items = [slide(), title(3, "First slice angle — 0 / 90 / 180 / 270")]
    for box, ang in zip([TL, TR, BL, BR], [0, 90, 180, 270]):
        items.append(ch(3, box, {"chartType": "doughnut", "title": f"firstSliceAngle={ang}",
                                  "firstSliceAngle": str(ang), "holeSize": "50", "legend": "right",
                                  "varyColors": "true", "categories": CATS, "data": D}))
    doc.batch(items)

    # ---- Slide 4: Data labels — percent / category / value, leaderlines, labelfont ----
    items = [slide(), title(4, "Data labels — percent / category / value, leaderlines, labelfont")]
    items.append(ch(4, TL, {"chartType": "doughnut", "title": "dataLabels=percent",
                            "dataLabels": "percent", "holeSize": "50", "legend": "right",
                            "labelfont": "10:333333:Calibri", "categories": CATS, "data": D}))
    items.append(ch(4, TR, {"chartType": "doughnut", "title": "percent,category",
                            "dataLabels": "percent,category", "holeSize": "50", "leaderlines": "true",
                            "legend": "none", "labelfont": "10:333333:Calibri",
                            "categories": CATS, "data": D}))
    items.append(ch(4, BL, {"chartType": "doughnut", "title": "all flags",
                            "dataLabels": "value,percent,category", "holeSize": "50",
                            "leaderlines": "true", "legend": "none", "categories": CATS, "data": D}))
    items.append(ch(4, BR, {"chartType": "doughnut", "title": "dataLabels=none",
                            "dataLabels": "none", "holeSize": "50", "legend": "right",
                            "categories": CATS, "data": D}))
    doc.batch(items)

    # ---- Slide 5: Series styling — colors, gradient, outline, shadow, transparency ----
    items = [slide(), title(5, "Series styling — colors, gradient, outline, shadow, transparency")]
    items.append(ch(5, TL, {"chartType": "doughnut", "title": "colors=", "holeSize": "50",
                            "legend": "right", "colors": "4472C4,ED7D31,A5A5A5,70AD47",
                            "categories": CATS, "data": D}))
    items.append(ch(5, TR, {"chartType": "doughnut", "title": "gradient + seriesshadow",
                            "holeSize": "50", "gradient": "FF6600-FFCC00",
                            "seriesshadow": "000000-5-45-3-50", "legend": "right",
                            "categories": CATS, "data": D}))
    items.append(ch(5, BL, {"chartType": "doughnut", "title": "seriesoutline white", "holeSize": "50",
                            "seriesoutline": "FFFFFF:2", "legend": "right",
                            "categories": CATS, "data": D}))
    items.append(ch(5, BR, {"chartType": "doughnut", "title": "transparency=30", "holeSize": "50",
                            "transparency": "30", "legend": "right", "categories": CATS, "data": D}))
    doc.batch(items)

    # ---- Slide 6: Title & legend ----
    items = [slide(), title(6, "Title & legend")]
    items.append(ch(6, TL, {"chartType": "doughnut", "title": "Styled title", "title.font": "Georgia",
                            "title.size": "20", "title.color": "4472C4", "title.bold": "true",
                            "holeSize": "50", "legend": "right", "categories": CATS, "data": D}))
    items.append(ch(6, TR, {"chartType": "doughnut", "title": "legend=bottom + legendFont",
                            "holeSize": "50", "legend": "bottom", "legendFont": "10:333333:Calibri",
                            "categories": CATS, "data": D}))
    items.append(ch(6, BL, {"chartType": "doughnut", "title": "legend.overlay=true", "holeSize": "50",
                            "legend": "topRight", "legend.overlay": "true",
                            "categories": CATS, "data": D}))
    items.append(ch(6, BR, {"chartType": "doughnut", "autotitledeleted": "true", "holeSize": "50",
                            "legend": "none", "categories": CATS, "data": D}))
    doc.batch(items)

    # ---- Slide 7: Backgrounds — chartareafill, plotFill, chartborder, roundedcorners ----
    items = [slide(), title(7, "Backgrounds — chartareafill, plotFill, chartborder, roundedcorners")]
    items.append(ch(7, TL, {"chartType": "doughnut", "title": "chartareafill + chartborder",
                            "holeSize": "50", "chartareafill": "FFF8E7", "chartborder": "000000:1",
                            "legend": "right", "categories": CATS, "data": D}))
    items.append(ch(7, TR, {"chartType": "doughnut", "title": "roundedcorners=true", "holeSize": "50",
                            "roundedcorners": "true", "chartborder": "4472C4:2", "legend": "right",
                            "categories": CATS, "data": D}))
    items.append(ch(7, BL, {"chartType": "doughnut", "title": "plotFill=none", "holeSize": "50",
                            "plotFill": "none", "legend": "right", "categories": CATS, "data": D}))
    items.append(ch(7, BR, {"chartType": "doughnut", "title": "chartareafill=none", "holeSize": "50",
                            "chartareafill": "none", "legend": "right", "categories": CATS, "data": D}))
    doc.batch(items)

    # ---- Slide 8: Presets & per-series Set ----
    items = [slide(), title(8, "Presets & per-series Set")]
    for box, p in zip([TL, TR, BL], ["minimal", "dark", "corporate"]):
        items.append(ch(8, box, {"chartType": "doughnut", "preset": p, "title": f"preset={p}",
                                 "holeSize": "50", "legend": "right", "categories": CATS, "data": D}))
    items.append(ch(8, BR, {"chartType": "doughnut", "title": "chart-series Set name+color",
                            "holeSize": "50", "legend": "right", "categories": CATS, "data": D}))
    doc.batch(items)
    # per-series Set: rename + recolor the single series of the 4th chart
    doc.send({"command": "set", "path": "/slide[8]/chart[4]/series[1]",
              "props": {"name": "Renamed Share", "color": "C00000"}})

    print("  built 8 slides")
    doc.send({"command": "save"})
# context exit closes the resident, flushing the presentation to disk.

# Validate the SAVED file with a fresh one-shot process (from disk).
import subprocess
print("--- Validate (fresh process, from disk) ---")
r = subprocess.run(["officecli", "validate", FILE], capture_output=True, text=True)
print(" ", (r.stdout or r.stderr).strip().split("\n")[0])

print(f"Generated: {FILE}")
