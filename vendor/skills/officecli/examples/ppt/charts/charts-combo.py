#!/usr/bin/env python3
"""
Combo Charts Showcase — combotypes, combosplit, secondaryaxis.

Generates: charts-combo.pptx

  Slide 1  combotypes mixes       column+line, column+area, line+area, bar+line
  Slide 2  combosplit             split index 1, 2, 3 (first N series use primary)
  Slide 3  secondaryaxis          1 series, 2 series, multiple series on secondary
  Slide 4  Title & legend
  Slide 5  Data labels
  Slide 6  Axes                   min/max on both axes, titles, gridlines
  Slide 7  Series styling         colors, gradients, transparency, outline, shadow
  Slide 8  Presets & per-series   preset bundles + chart-series Set

SDK twin of charts-combo.sh (officecli CLI). Both produce an equivalent
charts-combo.pptx. This one drives the **officecli Python SDK**
(`pip install officecli-sdk`): one resident is started and every slide, shape,
chart and per-element Set is shipped over the named pipe in `doc.batch(...)`
round-trips. Each item is the same `{"command","parent"/"path","type","props"}`
dict you'd put in an `officecli batch` list.

Forward-compat note: any prop a future-built handler doesn't yet support is
carried through verbatim (faithful to charts-combo.sh). The resident
silently skips unsupported props during `add`/`set`; nothing here strips them.

Usage:
  pip install officecli-sdk          # plus the `officecli` binary on PATH
  python3 charts-combo.py
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

FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "charts-combo.pptx")

# Four quadrant boxes (top-left, top-right, bottom-left, bottom-right).
TL = {"x": "0.3in", "y": "1.05in", "width": "6.1in", "height": "3in"}
TR = {"x": "6.95in", "y": "1.05in", "width": "6.1in", "height": "3in"}
BL = {"x": "0.3in", "y": "4.25in", "width": "6.1in", "height": "3in"}
BR = {"x": "6.95in", "y": "4.25in", "width": "6.1in", "height": "3in"}

CATS = "Q1,Q2,Q3,Q4"
D2 = "Sales:120,135,148,162;Growth %:5,12,18,22"
D3 = "Sales:120,135,148,162;Cost:80,90,95,105;Growth %:5,12,18,22"


def slide():
    """One `add slide` item in batch-shape."""
    return {"command": "add", "parent": "/", "type": "slide", "props": {}}


def title(n, text):
    """Slide title shape — `add shape` item in batch-shape."""
    return {"command": "add", "parent": f"/slide[{n}]", "type": "shape",
            "props": {"text": text, "size": "24", "bold": "true", "autoFit": "normal",
                      "x": "0.5in", "y": "0.3in", "width": "12.3in", "height": "0.6in"}}


def ch(n, box, p):
    """One `add chart` item in batch-shape (box geometry merged with props)."""
    return {"command": "add", "parent": f"/slide[{n}]", "type": "chart",
            "props": {**box, **p}}


print(f"Building {FILE} ...")

with officecli.create(FILE, "--force") as doc:

    # ---- Slide 1: combotypes ---------------------------------------------
    doc.batch([
        slide(),
        title(1, "combotypes — column+line / column+area / line+area / bar+line"),
        ch(1, TL, {"chartType": "combo", "combotypes": "column,line", "title": "column + line",
                   "legend": "bottom", "categories": CATS, "data": D2}),
        ch(1, TR, {"chartType": "combo", "combotypes": "column,area", "title": "column + area",
                   "legend": "bottom", "categories": CATS, "data": D2}),
        ch(1, BL, {"chartType": "combo", "combotypes": "line,area", "title": "line + area",
                   "legend": "bottom", "categories": CATS, "data": D2}),
        ch(1, BR, {"chartType": "combo", "combotypes": "bar,line", "title": "bar + line",
                   "legend": "bottom", "categories": CATS, "data": D2}),
    ])

    # ---- Slide 2: combosplit — first N series use primary type -----------
    doc.batch([
        slide(),
        title(2, "combosplit — first N series use primary type"),
        ch(2, TL, {"chartType": "combo", "combotypes": "column,column,line", "combosplit": "2",
                   "title": "combosplit=2 (2 columns + 1 line)", "legend": "bottom",
                   "categories": CATS, "data": D3}),
        ch(2, TR, {"chartType": "combo", "combotypes": "column,line,line", "combosplit": "1",
                   "title": "combosplit=1 (1 column + 2 lines)", "legend": "bottom",
                   "categories": CATS, "data": D3}),
        ch(2, BL, {"chartType": "combo", "combotypes": "line,line,column", "combosplit": "2",
                   "title": "combosplit=2 (2 lines + 1 column)", "legend": "bottom",
                   "categories": CATS, "data": D3}),
        ch(2, BR, {"chartType": "combo", "combotypes": "area,column,line", "combosplit": "1",
                   "title": "area + column + line", "legend": "bottom",
                   "categories": CATS, "data": D3}),
    ])

    # ---- Slide 3: secondaryaxis — line on secondary value axis -----------
    doc.batch([
        slide(),
        title(3, "secondaryaxis — line on secondary value axis"),
        ch(3, TL, {"chartType": "combo", "combotypes": "column,line", "secondaryaxis": "2",
                   "title": "secondaryaxis=2", "legend": "bottom", "categories": CATS, "data": D2}),
        ch(3, TR, {"chartType": "combo", "combotypes": "column,column,line", "secondaryaxis": "3",
                   "combosplit": "2", "title": "secondaryaxis=3 (Growth on right)", "legend": "bottom",
                   "categories": CATS, "data": D3}),
        ch(3, BL, {"chartType": "combo", "combotypes": "column,line,line", "secondaryaxis": "2,3",
                   "combosplit": "1", "title": "secondaryaxis=2,3", "legend": "bottom",
                   "categories": CATS, "data": D3}),
        ch(3, BR, {"chartType": "combo", "combotypes": "column,line", "secondaryaxis": "2",
                   "title": "with grid + tick fonts",
                   "gridlines": "E0E0E0:0.3", "axisfont": "9:333333:Calibri",
                   "legend": "bottom", "categories": CATS, "data": D2}),
    ])

    # ---- Slide 4: Title & legend -----------------------------------------
    doc.batch([
        slide(),
        title(4, "Title & legend"),
        ch(4, TL, {"chartType": "combo", "combotypes": "column,line", "title": "Styled title",
                   "title.font": "Georgia", "title.size": "20", "title.color": "4472C4",
                   "title.bold": "true",
                   "legend": "bottom", "categories": CATS, "data": D2}),
        ch(4, TR, {"chartType": "combo", "combotypes": "column,line", "title": "legend=top + legendFont",
                   "legend": "top", "legendFont": "10:333333:Calibri", "categories": CATS, "data": D2}),
        ch(4, BL, {"chartType": "combo", "combotypes": "column,line", "title": "legend.overlay=true",
                   "legend": "topRight", "legend.overlay": "true", "categories": CATS, "data": D2}),
        ch(4, BR, {"chartType": "combo", "combotypes": "column,line", "autotitledeleted": "true",
                   "legend": "none", "categories": CATS, "data": D2}),
    ])

    # ---- Slide 5: Data labels (combo charts skip labelPos) ---------------
    doc.batch([
        slide(),
        title(5, "Data labels — combo charts skip labelPos (chart-type conditional)"),
        ch(5, TL, {"chartType": "combo", "combotypes": "column,line", "title": "dataLabels=value",
                   "dataLabels": "value", "legend": "bottom", "categories": CATS, "data": D2}),
        ch(5, TR, {"chartType": "combo", "combotypes": "column,line", "title": "value,series",
                   "dataLabels": "value,series", "legend": "bottom", "categories": CATS, "data": D2}),
        ch(5, BL, {"chartType": "combo", "combotypes": "column,line", "title": "dataLabels=none",
                   "dataLabels": "none", "legend": "bottom", "categories": CATS, "data": D2}),
        ch(5, BR, {"chartType": "combo", "combotypes": "column,line", "title": "labelfont styled",
                   "dataLabels": "value", "labelfont": "10:C00000:Georgia",
                   "legend": "bottom", "categories": CATS, "data": D2}),
    ])

    # ---- Slide 6: Axes — min/max, secondary, gridlines, axisnumfmt -------
    doc.batch([
        slide(),
        title(6, "Axes — min/max on primary, secondary, gridlines, axisnumfmt"),
        ch(6, TL, {"chartType": "combo", "combotypes": "column,line", "secondaryaxis": "2",
                   "title": "both axes min/max", "axismin": "0", "axismax": "200",
                   "axistitle": "Sales", "cattitle": "Quarter", "axisfont": "10:333333:Calibri",
                   "axisnumfmt": "#,##0", "legend": "bottom", "categories": CATS, "data": D2}),
        ch(6, TR, {"chartType": "combo", "combotypes": "column,line", "title": "gridlines + minorGridlines",
                   "gridlines": "E0E0E0:0.3", "minorGridlines": "F0F0F0:0.25",
                   "legend": "bottom", "categories": CATS, "data": D2}),
        ch(6, BL, {"chartType": "combo", "combotypes": "column,line", "title": "labelrotation=-30",
                   "labelrotation": "-30", "legend": "bottom", "categories": CATS, "data": D2}),
        ch(6, BR, {"chartType": "combo", "combotypes": "column,line", "title": "chart-axis Set after add",
                   "legend": "bottom", "categories": CATS, "data": D2}),
        # chart-axis Set after add (value axis of chart[4])
        {"command": "set", "path": "/slide[6]/chart[4]/axis[@role=value]",
         "props": {"title": "Sales (USD)", "format": "$#,##0", "majorGridlines": "true",
                   "min": "0", "max": "200"}},
    ])

    # ---- Slide 7: Series styling -----------------------------------------
    doc.batch([
        slide(),
        title(7, "Series styling — colors, gradient(s), transparency, outline, shadow"),
        ch(7, TL, {"chartType": "combo", "combotypes": "column,line", "title": "colors + seriesoutline",
                   "colors": "4472C4,ED7D31", "seriesoutline": "000000:0.5",
                   "legend": "bottom", "categories": CATS, "data": D2}),
        ch(7, TR, {"chartType": "combo", "combotypes": "column,line", "title": "gradient + seriesshadow",
                   "gradient": "FF6600-FFCC00", "seriesshadow": "000000-5-45-3-50",
                   "legend": "bottom", "categories": CATS, "data": D2}),
        ch(7, BL, {"chartType": "combo", "combotypes": "column,line", "title": "transparency=30",
                   "transparency": "30", "legend": "bottom", "categories": CATS, "data": D2}),
        ch(7, BR, {"chartType": "combo", "combotypes": "column,line", "title": "per-series gradients",
                   "gradients": "FF0000-0000FF;00FF00-FFFF00",
                   "legend": "bottom", "categories": CATS, "data": D2}),
    ])

    # ---- Slide 8: Presets & per-series Set -------------------------------
    items = [slide(), title(8, "Presets & per-series Set")]
    for box, p in zip([TL, TR, BL], ["minimal", "dark", "corporate"]):
        items.append(ch(8, box, {"chartType": "combo", "combotypes": "column,line", "preset": p,
                                 "title": f"preset={p}", "legend": "bottom",
                                 "categories": CATS, "data": D2}))
    items.append(ch(8, BR, {"chartType": "combo", "combotypes": "column,line", "title": "chart-series Set",
                            "legend": "bottom", "categories": CATS, "data": D2}))
    # chart-series Set after add (series[1], series[2] of chart[4])
    items.append({"command": "set", "path": "/slide[8]/chart[4]/series[1]",
                  "props": {"name": "Renamed Sales", "color": "C00000"}})
    items.append({"command": "set", "path": "/slide[8]/chart[4]/series[2]",
                  "props": {"name": "Renamed Growth", "color": "2E75B6", "lineWidth": "2.5",
                            "marker": "circle", "markerSize": "8"}})
    doc.batch(items)

    doc.send({"command": "save"})
# context exit closes the resident, flushing the presentation to disk.

print(f"Generated: {FILE}  (8 slides)")
