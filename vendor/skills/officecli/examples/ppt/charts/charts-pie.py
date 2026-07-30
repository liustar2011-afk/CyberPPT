#!/usr/bin/env python3
"""
Pie Charts Showcase — pie, pie3d, pieOfPie, barOfPie (where supported).

Generates: charts-pie.pptx

  Slide 1  Variants           pie / pie3d (view3d) — varyColors, firstSliceAngle
  Slide 2  Explosion          explosion=0/10/20/30
  Slide 3  Title & legend     title.* + legend positions + legendFont
  Slide 4  Data labels        flags (percent/category/value), labelfont, leaderlines
  Slide 5  Series styling     colors, gradient, transparency, seriesoutline, seriesshadow
  Slide 6  First-slice angle  0 / 90 / 180 / 270
  Slide 7  Backgrounds        chartareafill, plotFill, chartborder, roundedcorners
  Slide 8  Presets & per-pt   preset bundles + per-point recolor via chart-series Set

SDK twin of charts-pie.sh (officecli CLI). Both produce an equivalent
charts-pie.pptx. This one drives the **officecli Python SDK**
(`pip install officecli-sdk`): one resident is started and every slide, shape
and chart is shipped over the named pipe with `doc.batch(...)` round-trips.
Each item is the same `{"command","parent","type","props"}` dict you'd put in
an `officecli batch` list.

Usage:
  pip install officecli-sdk          # plus the `officecli` binary on PATH
  python3 charts-pie.py
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

FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "charts-pie.pptx")

# --- four-quadrant layout for the charts on each slide
TL = {"x": "0.3in", "y": "1.05in", "width": "6.1in", "height": "3in"}
TR = {"x": "6.95in", "y": "1.05in", "width": "6.1in", "height": "3in"}
BL = {"x": "0.3in", "y": "4.25in", "width": "6.1in", "height": "3in"}
BR = {"x": "6.95in", "y": "4.25in", "width": "6.1in", "height": "3in"}
CATS = "North,South,East,West"
D = "Share:30,25,28,17"


def slide_items(n, title):
    """Items that add slide #n plus its title shape."""
    return [
        {"command": "add", "parent": "/", "type": "slide", "props": {}},
        {"command": "add", "parent": f"/slide[{n}]", "type": "shape",
         "props": {"text": title, "size": "24", "bold": "true", "autoFit": "normal",
                   "x": "0.5in", "y": "0.3in", "width": "12.3in", "height": "0.6in"}},
    ]


def ch(n, box, props):
    """One `add chart` item on slide #n in quadrant `box`."""
    return {"command": "add", "parent": f"/slide[{n}]", "type": "chart",
            "props": {**box, **props}}


print(f"Building {FILE} ...")

with officecli.create(FILE, "--force") as doc:

    # ---- Slide 1: pie variants -------------------------------------------
    s = 1
    items = slide_items(s, "Pie variants — pie / pie3d (varyColors, firstSliceAngle)")
    items += [
        ch(s, TL, {"chartType": "pie", "title": "pie", "legend": "right", "varyColors": "true",
                   "categories": CATS, "data": D}),
        ch(s, TR, {"chartType": "pie3d", "title": "pie3d (view3d=20,20,30)", "view3d": "20,20,30",
                   "legend": "right", "varyColors": "true", "categories": CATS, "data": D}),
        ch(s, BL, {"chartType": "pie", "title": "firstSliceAngle=90", "firstSliceAngle": "90",
                   "legend": "right", "categories": CATS, "data": D}),
        ch(s, BR, {"chartType": "pie", "title": "varyColors=false", "varyColors": "false",
                   "legend": "right", "categories": CATS, "data": D}),
    ]
    doc.batch(items)

    # ---- Slide 2: explosion ----------------------------------------------
    s = 2
    items = slide_items(s, "Explosion — 0 / 10 / 20 / 30 (% of radius)")
    items += [
        ch(s, TL, {"chartType": "pie", "title": "explosion=0", "explosion": "0", "legend": "right",
                   "categories": CATS, "data": D}),
        ch(s, TR, {"chartType": "pie", "title": "explosion=10", "explosion": "10", "legend": "right",
                   "categories": CATS, "data": D}),
        ch(s, BL, {"chartType": "pie", "title": "explosion=20", "explosion": "20", "legend": "right",
                   "categories": CATS, "data": D}),
        ch(s, BR, {"chartType": "pie", "title": "explosion=30", "explosion": "30", "legend": "right",
                   "categories": CATS, "data": D}),
    ]
    doc.batch(items)

    # ---- Slide 3: title & legend -----------------------------------------
    s = 3
    items = slide_items(s, "Title & legend")
    items += [
        ch(s, TL, {"chartType": "pie", "title": "Styled title", "title.font": "Georgia",
                   "title.size": "20", "title.color": "4472C4", "title.bold": "true",
                   "legend": "right", "categories": CATS, "data": D}),
        ch(s, TR, {"chartType": "pie", "title": "legend=bottom + legendFont", "legend": "bottom",
                   "legendFont": "10:333333:Calibri", "categories": CATS, "data": D}),
        ch(s, BL, {"chartType": "pie", "title": "legend.overlay=true", "legend": "topRight",
                   "legend.overlay": "true", "categories": CATS, "data": D}),
        ch(s, BR, {"chartType": "pie", "autotitledeleted": "true", "legend": "none",
                   "categories": CATS, "data": D}),
    ]
    doc.batch(items)

    # ---- Slide 4: data labels --------------------------------------------
    s = 4
    items = slide_items(s, "Data labels — percent / category / value, labelfont, leaderlines")
    items += [
        ch(s, TL, {"chartType": "pie", "title": "dataLabels=percent", "dataLabels": "percent",
                   "legend": "right", "labelfont": "10:333333:Calibri", "categories": CATS, "data": D}),
        ch(s, TR, {"chartType": "pie", "title": "percent,category", "dataLabels": "percent,category",
                   "leaderlines": "true", "legend": "none", "labelfont": "10:333333:Calibri",
                   "categories": CATS, "data": D}),
        ch(s, BL, {"chartType": "pie", "title": "all flags", "dataLabels": "value,percent,category",
                   "leaderlines": "true", "legend": "none", "categories": CATS, "data": D}),
        ch(s, BR, {"chartType": "pie", "title": "dataLabels=none", "dataLabels": "none",
                   "legend": "right", "categories": CATS, "data": D}),
    ]
    doc.batch(items)

    # ---- Slide 5: series styling -----------------------------------------
    s = 5
    items = slide_items(s, "Series styling — colors, gradient, transparency, outline, shadow")
    items += [
        ch(s, TL, {"chartType": "pie", "title": "colors= explicit palette", "legend": "right",
                   "colors": "4472C4,ED7D31,A5A5A5,70AD47", "categories": CATS, "data": D}),
        ch(s, TR, {"chartType": "pie", "title": "gradient + seriesshadow", "legend": "right",
                   "gradient": "FF6600-FFCC00", "seriesshadow": "000000-5-45-3-50",
                   "categories": CATS, "data": D}),
        ch(s, BL, {"chartType": "pie", "title": "seriesoutline white", "legend": "right",
                   "seriesoutline": "FFFFFF:2", "categories": CATS, "data": D}),
        ch(s, BR, {"chartType": "pie", "title": "transparency=30", "legend": "right",
                   "transparency": "30", "categories": CATS, "data": D}),
    ]
    doc.batch(items)

    # ---- Slide 6: first-slice angle --------------------------------------
    s = 6
    items = slide_items(s, "First slice angle — 0 / 90 / 180 / 270")
    for box, ang in zip([TL, TR, BL, BR], [0, 90, 180, 270]):
        items.append(ch(s, box, {"chartType": "pie", "title": f"firstSliceAngle={ang}",
                                  "firstSliceAngle": str(ang), "legend": "right",
                                  "varyColors": "true", "categories": CATS, "data": D}))
    doc.batch(items)

    # ---- Slide 7: backgrounds --------------------------------------------
    s = 7
    items = slide_items(s, "Backgrounds — chartareafill, plotFill, chartborder, roundedcorners")
    items += [
        ch(s, TL, {"chartType": "pie", "title": "chartareafill + chartborder", "legend": "right",
                   "chartareafill": "FFF8E7", "chartborder": "000000:1", "categories": CATS, "data": D}),
        ch(s, TR, {"chartType": "pie", "title": "roundedcorners=true", "legend": "right",
                   "roundedcorners": "true", "chartborder": "4472C4:2", "categories": CATS, "data": D}),
        ch(s, BL, {"chartType": "pie", "title": "plotFill=none", "legend": "right",
                   "plotFill": "none", "categories": CATS, "data": D}),
        ch(s, BR, {"chartType": "pie", "title": "chartareafill=none", "legend": "right",
                   "chartareafill": "none", "categories": CATS, "data": D}),
    ]
    doc.batch(items)

    # ---- Slide 8: presets & per-series Set -------------------------------
    s = 8
    items = slide_items(s, "Presets & per-series Set")
    for box, p in zip([TL, TR, BL], ["minimal", "dark", "corporate"]):
        items.append(ch(s, box, {"chartType": "pie", "preset": p, "title": f"preset={p}",
                                  "legend": "right", "categories": CATS, "data": D}))
    items.append(ch(s, BR, {"chartType": "pie", "title": "chart-series Set name+color",
                            "legend": "right", "categories": CATS, "data": D}))
    doc.batch(items)
    # per-point recolor via chart-series Set (must follow the chart[4] add above)
    doc.send({"command": "set", "path": f"/slide[{s}]/chart[4]/series[1]",
              "props": {"name": "Renamed Share", "color": "C00000"}})

    print(f"  built {s} slides")

print(f"Generated: {FILE}  ({s} slides)")
