#!/usr/bin/env python3
"""
Line Charts Showcase — line, stackedLine, percentStackedLine, line3d.

Generates: charts-line.pptx

  Slide 1  Variants           line / stackedLine / percentStackedLine / line3d
  Slide 2  Markers            marker symbol/size/color, markersize, showMarker
  Slide 3  Smoothing & dash   smooth, linedash, linewidth
  Slide 4  Title & legend     title.* + legend positions + legendFont
  Slide 5  Data labels        flags, labelPos, labelfont
  Slide 6  Axes               min/max, titles, fonts, gridlines, ticks, labelrotation, log
  Slide 7  Overlays           droplines, hilowlines, updownbars, trendline, errbars, referenceline
  Slide 8  Per-series Set     lineWidth/lineDash/marker/markerSize/color/smooth + presets

SDK twin of charts-line.sh (officecli CLI). Both produce an equivalent
charts-line.pptx. This one drives the **officecli Python SDK**
(`pip install officecli-sdk`): one resident is started and every slide's shapes
and charts are shipped over the named pipe in `doc.batch(...)` round-trips.
Each item is the same `{"command","parent","type","props"}` dict you'd put in
an `officecli batch` list. Unsupported props are forwarded as-is: the resident
warns (forward-compat) without failing the batch.

Usage:
  pip install officecli-sdk          # plus the `officecli` binary on PATH
  python3 charts-line.py
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

FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "charts-line.pptx")

# Quadrant boxes (top-left / top-right / bottom-left / bottom-right).
TL = {"x": "0.3in", "y": "1.05in", "width": "6.1in", "height": "3in"}
TR = {"x": "6.95in", "y": "1.05in", "width": "6.1in", "height": "3in"}
BL = {"x": "0.3in", "y": "4.25in", "width": "6.1in", "height": "3in"}
BR = {"x": "6.95in", "y": "4.25in", "width": "6.1in", "height": "3in"}
CATS = "Mon,Tue,Wed,Thu,Fri"
D2 = "A:50,60,70,65,80;B:40,45,55,60,75"


def slide_items(slide_idx, title, charts):
    """Build the batch items for one slide: an `add slide`, a title `shape`,
    then one `add chart` per (box, props) pair. `slide_idx` is the 1-based index
    of the slide AFTER it is added (used to anchor the title + charts)."""
    items = [{"command": "add", "parent": "/", "type": "slide", "props": {}}]
    items.append({"command": "add", "parent": f"/slide[{slide_idx}]", "type": "shape",
                  "props": {"text": title, "size": "24", "bold": "true",
                            "autoFit": "normal", "x": "0.5in", "y": "0.3in",
                            "width": "12.3in", "height": "0.6in"}})
    for box, props in charts:
        items.append({"command": "add", "parent": f"/slide[{slide_idx}]", "type": "chart",
                      "props": {**box, **props}})
    return items


print(f"Building {FILE} ...")

with officecli.create(FILE, "--force") as doc:

    # ---- Slide 1: Line variants ------------------------------------------
    doc.batch(slide_items(1, "Line variants — line / stackedLine / percentStackedLine / line3d", [
        (TL, {"chartType": "line", "title": "line", "legend": "bottom", "categories": CATS, "data": D2}),
        (TR, {"chartType": "stackedLine", "title": "stackedLine", "legend": "bottom", "categories": CATS, "data": D2}),
        (BL, {"chartType": "percentStackedLine", "title": "percentStackedLine", "legend": "bottom", "categories": CATS, "data": D2}),
        (BR, {"chartType": "line3d", "title": "line3d", "legend": "bottom", "categories": CATS, "data": D2}),
    ]))

    # ---- Slide 2: Markers ------------------------------------------------
    doc.batch(slide_items(2, "Markers — symbol, size, color, showMarker", [
        (TL, {"chartType": "line", "title": "marker=circle:8:FF0000", "marker": "circle:8:FF0000",
              "linewidth": "2", "legend": "none", "categories": CATS, "data": "A:50,60,70,65,80"}),
        (TR, {"chartType": "line", "title": "marker=square:6", "marker": "square:6", "linewidth": "2",
              "legend": "none", "categories": CATS, "data": "A:50,60,70,65,80"}),
        (BL, {"chartType": "line", "title": "marker=diamond:10:0070C0", "marker": "diamond:10:0070C0",
              "linewidth": "2", "legend": "none", "categories": CATS, "data": "A:50,60,70,65,80"}),
        (BR, {"chartType": "line", "title": "showMarker=true (default markers)", "showMarker": "true",
              "legend": "bottom", "categories": CATS, "data": D2}),
    ]))

    # ---- Slide 3: Smoothing & dash ---------------------------------------
    doc.batch(slide_items(3, "Smoothing & dash — smooth, linedash, linewidth", [
        (TL, {"chartType": "line", "title": "smooth=true", "smooth": "true", "linewidth": "2.5",
              "legend": "none", "categories": CATS, "data": "A:50,60,70,65,80"}),
        (TR, {"chartType": "line", "title": "linedash=dash", "linedash": "dash", "linewidth": "2",
              "legend": "none", "categories": CATS, "data": "A:50,60,70,65,80"}),
        (BL, {"chartType": "line", "title": "linedash=dot", "linedash": "dot", "linewidth": "2",
              "legend": "none", "categories": CATS, "data": "A:50,60,70,65,80"}),
        (BR, {"chartType": "line", "title": "linedash=dashDot", "linedash": "dashDot", "linewidth": "2",
              "legend": "none", "categories": CATS, "data": "A:50,60,70,65,80"}),
    ]))

    # ---- Slide 4: Title & legend -----------------------------------------
    doc.batch(slide_items(4, "Title & legend", [
        (TL, {"chartType": "line", "title": "Styled title", "title.font": "Georgia", "title.size": "20",
              "title.color": "4472C4", "title.bold": "true", "legend": "bottom", "categories": CATS, "data": D2}),
        (TR, {"chartType": "line", "title": "legend=top + legendFont", "legend": "top",
              "legendFont": "10:333333:Calibri", "categories": CATS, "data": D2}),
        (BL, {"chartType": "line", "title": "legend.overlay=true", "legend": "topRight",
              "legend.overlay": "true", "categories": CATS, "data": D2}),
        (BR, {"chartType": "line", "autotitledeleted": "true", "legend": "none", "categories": CATS, "data": D2}),
    ]))

    # ---- Slide 5: Data labels --------------------------------------------
    doc.batch(slide_items(5, "Data labels — flags, labelPos, labelfont", [
        (TL, {"chartType": "line", "title": "dataLabels=value @ top", "dataLabels": "value", "labelPos": "top",
              "labelfont": "10:333333:Calibri", "legend": "none", "categories": CATS, "data": "A:50,60,70,65,80"}),
        (TR, {"chartType": "line", "title": "value,category", "dataLabels": "value,category", "labelPos": "top",
              "legend": "none", "categories": CATS, "data": "A:50,60,70,65,80"}),
        (BL, {"chartType": "line", "title": "dataLabels=none", "dataLabels": "none", "legend": "none",
              "categories": CATS, "data": "A:50,60,70,65,80"}),
        (BR, {"chartType": "line", "title": "labelfont styled", "dataLabels": "value", "labelPos": "top",
              "labelfont": "12:C00000:Georgia", "legend": "none", "categories": CATS, "data": "A:50,60,70,65,80"}),
    ]))

    # ---- Slide 6: Axes ---------------------------------------------------
    doc.batch(slide_items(6, "Axes — min/max, gridlines, ticks, labelrotation, log", [
        (TL, {"chartType": "line", "title": "min/max + titles", "legend": "none",
              "axismin": "0", "axismax": "100", "majorunit": "25", "axistitle": "Visits", "cattitle": "Day",
              "axisfont": "10:333333:Calibri", "axisline": "666666:1", "axisnumfmt": "#,##0",
              "categories": CATS, "data": "A:50,60,70,65,80"}),
        (TR, {"chartType": "line", "title": "gridlines + ticks", "legend": "none",
              "gridlines": "E0E0E0:0.3", "minorGridlines": "F0F0F0:0.25",
              "majorTickMark": "out", "minorTickMark": "in", "tickLabelPos": "nextTo",
              "categories": CATS, "data": "A:50,60,70,65,80"}),
        (BL, {"chartType": "line", "title": "labelrotation=-30", "legend": "none",
              "labelrotation": "-30", "categories": "January,February,March,April,May,June",
              "data": "A:60,90,140,180,160,210"}),
        (BR, {"chartType": "line", "title": "logbase=10", "legend": "none", "logbase": "10",
              "axismin": "1", "axismax": "10000", "categories": CATS, "data": "Growth:5,50,500,5000,3000"}),
    ]))

    # ---- Slide 7: Overlays -----------------------------------------------
    doc.batch(slide_items(7, "Overlays — droplines, hilowlines, updownbars, trendline, errbars, referenceline", [
        (TL, {"chartType": "line", "title": "droplines + hilowlines", "droplines": "808080:0.5", "hilowlines": "true",
              "legend": "bottom", "categories": CATS, "data": "High:130,135,140,138,145;Low:118,122,128,125,132"}),
        (TR, {"chartType": "line", "title": "updownbars=150:00AA00:FF0000",
              "updownbars": "150:00AA00:FF0000", "legend": "bottom", "categories": CATS,
              "data": "Open:120,128,130,135,138;Close:128,125,135,138,142"}),
        (BL, {"chartType": "line", "title": "trendline=linear + errbars=stdDev:1",
              "trendline": "linear", "errbars": "stdDev:1", "legend": "none",
              "categories": CATS, "data": "A:50,60,70,65,80"}),
        (BR, {"chartType": "line", "title": "referenceline=70:FF0000:Target",
              "referenceline": "70:FF0000:Target", "legend": "none",
              "categories": CATS, "data": "A:50,60,70,65,80"}),
    ]))

    # ---- Slide 8: Per-series Set + presets -------------------------------
    doc.batch(slide_items(8, "Per-series Set + presets — chart-series lineWidth/lineDash/marker/markerSize/color/smooth", [
        (TL, {"chartType": "line", "preset": "minimal", "title": "preset=minimal",
              "legend": "bottom", "categories": CATS, "data": D2}),
        (TR, {"chartType": "line", "preset": "dark", "title": "preset=dark",
              "legend": "bottom", "categories": CATS, "data": D2}),
        (BL, {"chartType": "line", "preset": "corporate", "title": "preset=corporate",
              "legend": "bottom", "categories": CATS, "data": D2}),
        (BR, {"chartType": "line", "title": "chart-series Set per line", "showMarker": "true",
              "legend": "bottom", "categories": CATS, "data": D2}),
    ]))
    # chart-series Set on the 4th chart's two lines (after the chart exists).
    doc.batch([
        {"command": "set", "path": "/slide[8]/chart[4]/series[1]",
         "props": {"name": "Alpha", "color": "C00000", "lineWidth": "2.5", "lineDash": "solid",
                   "marker": "circle", "markerSize": "9", "smooth": "true"}},
        {"command": "set", "path": "/slide[8]/chart[4]/series[2]",
         "props": {"name": "Beta", "color": "2E75B6", "lineWidth": "1.5", "lineDash": "dash",
                   "marker": "diamond", "markerSize": "8"}},
    ])

    print("  built 8 slides")

print(f"Generated: {FILE}")
