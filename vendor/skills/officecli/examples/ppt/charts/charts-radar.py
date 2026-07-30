#!/usr/bin/env python3
"""
Radar Charts Showcase — radarstyle standard / marker / filled.

Generates: charts-radar.pptx

  Slide 1  radarstyle             standard / marker / filled
  Slide 2  Title & legend         title.* + legend positions + legendFont
  Slide 3  Data labels            flags + labelfont
  Slide 4  Axes                   min/max, gridlines, axisfont, labelrotation
  Slide 5  Series styling         colors, gradient, transparency, outline, shadow
  Slide 6  Markers                marker symbol/size/color (radarstyle=marker only)
  Slide 7  Backgrounds            chartareafill, plotFill, chartborder, roundedcorners
  Slide 8  Presets & per-series   preset bundles + chart-series Set

SDK twin of charts-radar.sh (officecli CLI). Both produce an equivalent
charts-radar.pptx. This one drives the **officecli Python SDK**
(`pip install officecli-sdk`): one resident is started and each slide's
title shape plus its four charts are shipped over the named pipe in a single
`doc.batch(...)` round-trip. Each item is the same
`{"command","parent","type","props"}` dict you'd put in an `officecli batch`
list.

Usage:
  pip install officecli-sdk          # plus the `officecli` binary on PATH
  python3 charts-radar.py
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

FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "charts-radar.pptx")

# Four-up grid boxes (inches) shared by every slide.
TL = {"x": "0.3in", "y": "1.05in", "width": "6.1in", "height": "3in"}
TR = {"x": "6.95in", "y": "1.05in", "width": "6.1in", "height": "3in"}
BL = {"x": "0.3in", "y": "4.25in", "width": "6.1in", "height": "3in"}
BR = {"x": "6.95in", "y": "4.25in", "width": "6.1in", "height": "3in"}

CATS = "Speed,Power,Range,Style,Tech,Price"
D = "A:8,7,9,6,8,7"
D2 = "Model A:8,7,9,6,8,7;Model B:6,9,7,8,9,6"


def title_shape(slide, text):
    """One `add shape` item: the slide's bold title bar."""
    return {"command": "add", "parent": f"/slide[{slide}]", "type": "shape",
            "props": {"text": text, "size": "24", "bold": "true", "autoFit": "normal",
                      "x": "0.5in", "y": "0.3in", "width": "12.3in", "height": "0.6in"}}


def chart(slide, box, props):
    """One `add chart` item at grid box `box` on `slide`."""
    return {"command": "add", "parent": f"/slide[{slide}]", "type": "chart",
            "props": {**box, **props}}


print(f"Building {FILE} ...")

with officecli.create(FILE, "--force") as doc:

    # ---- Slide 1: radarstyle — standard / marker / filled ------------------
    doc.batch([
        {"command": "add", "parent": "/", "type": "slide"},
        title_shape(1, "radarstyle — standard / marker / filled"),
        chart(1, TL, {"chartType": "radar", "radarstyle": "standard", "title": "radarstyle=standard",
                      "legend": "bottom", "categories": CATS, "data": D2}),
        chart(1, TR, {"chartType": "radar", "radarstyle": "marker", "title": "radarstyle=marker",
                      "legend": "bottom", "categories": CATS, "data": D2}),
        chart(1, BL, {"chartType": "radar", "radarstyle": "filled", "title": "radarstyle=filled",
                      "legend": "bottom", "categories": CATS, "data": D2}),
        chart(1, BR, {"chartType": "radar", "radarstyle": "standard", "title": "single series",
                      "legend": "bottom", "categories": CATS, "data": D}),
    ])

    # ---- Slide 2: Title & legend -------------------------------------------
    doc.batch([
        {"command": "add", "parent": "/", "type": "slide"},
        title_shape(2, "Title & legend"),
        chart(2, TL, {"chartType": "radar", "radarstyle": "filled", "title": "Styled title",
                      "title.font": "Georgia", "title.size": "20", "title.color": "4472C4",
                      "title.bold": "true",
                      "legend": "bottom", "categories": CATS, "data": D2}),
        chart(2, TR, {"chartType": "radar", "radarstyle": "standard", "title": "legend=top + legendFont",
                      "legend": "top", "legendFont": "10:333333:Calibri",
                      "categories": CATS, "data": D2}),
        chart(2, BL, {"chartType": "radar", "radarstyle": "standard", "title": "legend.overlay=true",
                      "legend": "topRight", "legend.overlay": "true",
                      "categories": CATS, "data": D2}),
        chart(2, BR, {"chartType": "radar", "radarstyle": "filled", "autotitledeleted": "true",
                      "legend": "none", "categories": CATS, "data": D2}),
    ])

    # ---- Slide 3: Data labels — flags + labelfont --------------------------
    doc.batch([
        {"command": "add", "parent": "/", "type": "slide"},
        title_shape(3, "Data labels — flags + labelfont"),
        chart(3, TL, {"chartType": "radar", "radarstyle": "marker", "title": "value",
                      "dataLabels": "value", "labelfont": "9:333333:Calibri",
                      "legend": "none", "categories": CATS, "data": D}),
        chart(3, TR, {"chartType": "radar", "radarstyle": "marker", "title": "value,series",
                      "dataLabels": "value,series", "legend": "bottom",
                      "categories": CATS, "data": D2}),
        chart(3, BL, {"chartType": "radar", "radarstyle": "standard", "title": "value,category",
                      "dataLabels": "value,category", "legend": "none",
                      "categories": CATS, "data": D}),
        chart(3, BR, {"chartType": "radar", "radarstyle": "filled", "title": "dataLabels=none",
                      "dataLabels": "none", "legend": "bottom",
                      "categories": CATS, "data": D2}),
    ])

    # ---- Slide 4: Axes — min/max, gridlines, axisfont, labelrotation -------
    doc.batch([
        {"command": "add", "parent": "/", "type": "slide"},
        title_shape(4, "Axes — min/max, gridlines, axisfont, labelrotation"),
        chart(4, TL, {"chartType": "radar", "radarstyle": "standard", "title": "min/max + titles",
                      "axismin": "0", "axismax": "10", "majorunit": "2",
                      "axisfont": "10:333333:Calibri",
                      "legend": "none", "categories": CATS, "data": D}),
        chart(4, TR, {"chartType": "radar", "radarstyle": "standard", "title": "gridlines + minorGridlines",
                      "gridlines": "E0E0E0:0.3", "minorGridlines": "F0F0F0:0.25",
                      "legend": "none", "categories": CATS, "data": D}),
        chart(4, BL, {"chartType": "radar", "radarstyle": "standard", "title": "labelrotation=30",
                      "labelrotation": "30", "legend": "none", "categories": CATS, "data": D}),
        chart(4, BR, {"chartType": "radar", "radarstyle": "standard", "title": "axisnumfmt=0.0",
                      "axisnumfmt": "0.0", "legend": "none", "categories": CATS, "data": D}),
    ])

    # ---- Slide 5: Series styling — colors/gradient/transparency/outline/shadow
    doc.batch([
        {"command": "add", "parent": "/", "type": "slide"},
        title_shape(5, "Series styling — colors, gradient, transparency, outline, shadow"),
        chart(5, TL, {"chartType": "radar", "radarstyle": "filled", "title": "colors + seriesoutline",
                      "colors": "4472C4,ED7D31", "seriesoutline": "000000:0.5",
                      "legend": "bottom", "categories": CATS, "data": D2}),
        chart(5, TR, {"chartType": "radar", "radarstyle": "filled", "title": "gradient + seriesshadow",
                      "gradient": "FF6600-FFCC00", "seriesshadow": "000000-5-45-3-50",
                      "legend": "none", "categories": CATS, "data": D}),
        chart(5, BL, {"chartType": "radar", "radarstyle": "filled", "title": "transparency=40",
                      "transparency": "40", "legend": "bottom", "categories": CATS, "data": D2}),
        chart(5, BR, {"chartType": "radar", "radarstyle": "filled", "title": "per-series gradients",
                      "gradients": "FF0000-0000FF;00FF00-FFFF00", "legend": "bottom",
                      "categories": CATS, "data": D2}),
    ])

    # ---- Slide 6: Markers (radarstyle=marker) — symbol/size/color ----------
    doc.batch([
        {"command": "add", "parent": "/", "type": "slide"},
        title_shape(6, "Markers (radarstyle=marker) — symbol/size/color"),
        chart(6, TL, {"chartType": "radar", "radarstyle": "marker", "title": "circle:10:FF0000",
                      "marker": "circle:10:FF0000", "legend": "none", "categories": CATS, "data": D}),
        chart(6, TR, {"chartType": "radar", "radarstyle": "marker", "title": "square:8:0070C0",
                      "marker": "square:8:0070C0", "legend": "none", "categories": CATS, "data": D}),
        chart(6, BL, {"chartType": "radar", "radarstyle": "marker", "title": "diamond:12",
                      "marker": "diamond:12", "legend": "none", "categories": CATS, "data": D}),
        chart(6, BR, {"chartType": "radar", "radarstyle": "marker", "title": "triangle:10:70AD47",
                      "marker": "triangle:10:70AD47", "legend": "none", "categories": CATS, "data": D}),
    ])

    # ---- Slide 7: Backgrounds — chartareafill/plotFill/chartborder/rounded --
    doc.batch([
        {"command": "add", "parent": "/", "type": "slide"},
        title_shape(7, "Backgrounds — chartareafill, plotFill, chartborder, roundedcorners"),
        chart(7, TL, {"chartType": "radar", "radarstyle": "filled",
                      "title": "chartareafill + plotFill + borders",
                      "chartareafill": "FFF8E7", "plotFill": "FAFAFA", "chartborder": "000000:1",
                      "plotborder": "CCCCCC:0.5", "legend": "bottom", "categories": CATS, "data": D2}),
        chart(7, TR, {"chartType": "radar", "radarstyle": "filled", "title": "roundedcorners=true",
                      "roundedcorners": "true", "chartborder": "4472C4:2",
                      "legend": "bottom", "categories": CATS, "data": D2}),
        chart(7, BL, {"chartType": "radar", "radarstyle": "standard", "title": "plotFill=none",
                      "plotFill": "none", "legend": "none", "categories": CATS, "data": D}),
        chart(7, BR, {"chartType": "radar", "radarstyle": "filled", "title": "chartareafill=none",
                      "chartareafill": "none", "legend": "bottom", "categories": CATS, "data": D2}),
    ])

    # ---- Slide 8: Presets & per-series Set ---------------------------------
    items = [
        {"command": "add", "parent": "/", "type": "slide"},
        title_shape(8, "Presets & per-series Set"),
    ]
    for box, p in zip([TL, TR, BL], ["minimal", "dark", "corporate"]):
        items.append(chart(8, box, {"chartType": "radar", "radarstyle": "filled", "preset": p,
                                     "title": f"preset={p}",
                                     "legend": "bottom", "categories": CATS, "data": D2}))
    items.append(chart(8, BR, {"chartType": "radar", "radarstyle": "marker", "title": "chart-series Set",
                               "legend": "bottom", "categories": CATS, "data": D2}))
    # per-series Set applies AFTER chart[4] exists in the same batch (items apply
    # in order), recoloring + remarking the first series.
    items.append({"command": "set", "path": "/slide[8]/chart[4]/series[1]",
                  "props": {"name": "Renamed A", "color": "C00000",
                            "marker": "circle", "markerSize": "9"}})
    doc.batch(items)

    doc.send({"command": "save"})
# context exit closes the resident, flushing the deck to disk.

print(f"Generated: {FILE}  (8 slides)")
