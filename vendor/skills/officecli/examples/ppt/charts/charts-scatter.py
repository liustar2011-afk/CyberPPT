#!/usr/bin/env python3
"""
Scatter Charts Showcase — scatterstyle line/lineMarker/marker/smooth/smoothMarker.

Generates: charts-scatter.pptx

  Slide 1  scatterstyle variants  line / lineMarker / marker / smooth / smoothMarker (5 charts)
  Slide 2  Markers                marker symbol/size/color
  Slide 3  Title & legend
  Slide 4  Data labels
  Slide 5  Axes                   min/max, gridlines, log on both axes
  Slide 6  Series styling         colors, gradient, transparency, outline, shadow
  Slide 7  Overlays               trendline (linear/poly/exp/log/power/movingAvg), errbars, referenceline
  Slide 8  Per-series Set         lineWidth/lineDash/marker/markerSize/color/smooth + presets

SDK twin of charts-scatter.sh (officecli CLI). Both produce an equivalent
charts-scatter.pptx. This one drives the **officecli Python SDK**
(`pip install officecli-sdk`): one resident is started and every slide, shape,
chart and per-series Set is shipped over the named pipe in `doc.batch(...)`
round-trips. Each item is the same `{"command","parent"/"path","type","props"}`
dict you'd put in an `officecli batch` list.

Forward-compat: a chart prop that this officecli build doesn't yet support is
reported by the resident as an `unsupported_property` warning inside the batch
envelope (not a hard failure); we surface those so silent gaps stay visible,
mirroring the .sh twin's UNSUPPORTED-skip behaviour.

Usage:
  pip install officecli-sdk          # plus the `officecli` binary on PATH
  python3 charts-scatter.py
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

FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "charts-scatter.pptx")

# --- slide layout boxes (4-up grid) and shared scatter data
TL = {"x": "0.3in",  "y": "1.05in", "width": "6.1in", "height": "3in"}
TR = {"x": "6.95in", "y": "1.05in", "width": "6.1in", "height": "3in"}
BL = {"x": "0.3in",  "y": "4.25in", "width": "6.1in", "height": "3in"}
BR = {"x": "6.95in", "y": "4.25in", "width": "6.1in", "height": "3in"}
D = "A:10,20,18,30,28,40,42,55,52,65"
D2 = "A:10,20,18,30,28,40,42,55;B:5,12,15,22,25,30,35,40"

# slide counter — tracks the current slide index used in parent/path strings
slide = 0


def new_slide(title):
    """Return [add slide, add title-shape] batch items and bump the counter."""
    global slide
    slide += 1
    return [
        {"command": "add", "parent": "/", "type": "slide", "props": {}},
        {"command": "add", "parent": f"/slide[{slide}]", "type": "shape",
         "props": {"text": title, "size": "24", "bold": "true", "autoFit": "normal",
                   "x": "0.5in", "y": "0.3in", "width": "12.3in", "height": "0.6in"}},
    ]


def ch(box, props):
    """One `add chart` item in batch-shape on the current slide."""
    return {"command": "add", "parent": f"/slide[{slide}]", "type": "chart",
            "props": {**box, **props}}


def warn_unsupported(env, label):
    """Surface any unsupported_property warnings in a batch envelope (forward-compat)."""
    if not isinstance(env, dict):
        return
    data = env.get("data", env)
    warnings = []
    if isinstance(data, dict):
        warnings = data.get("warnings") or data.get("Warnings") or []
    for w in warnings:
        msg = w if isinstance(w, str) else (w.get("message") or w.get("type") or str(w))
        print(f"  ⚠ {label} → {msg}", file=sys.stderr)


print(f"Building {FILE} ...")

with officecli.create(FILE, "--force") as doc:

    # --- Slide 1: scatterstyle variants ---
    items = new_slide("scatterstyle — line / lineMarker / marker / smooth / smoothMarker")
    items += [
        ch(TL, {"chartType": "scatter", "scatterstyle": "line", "title": "scatterstyle=line",
                "legend": "none", "data": D}),
        ch(TR, {"chartType": "scatter", "scatterstyle": "lineMarker", "title": "scatterstyle=lineMarker",
                "legend": "none", "data": D}),
        ch(BL, {"chartType": "scatter", "scatterstyle": "marker", "title": "scatterstyle=marker",
                "legend": "none", "data": D}),
        ch(BR, {"chartType": "scatter", "scatterstyle": "smoothMarker", "title": "scatterstyle=smoothMarker",
                "legend": "none", "data": D}),
    ]
    warn_unsupported(doc.batch(items), "slide1")

    # --- Slide 2: Markers ---
    items = new_slide("Markers — symbol / size / color / markercolor")
    items += [
        ch(TL, {"chartType": "scatter", "scatterstyle": "marker", "title": "circle:10:FF0000",
                "marker": "circle:10:FF0000", "legend": "none", "data": D}),
        ch(TR, {"chartType": "scatter", "scatterstyle": "marker", "title": "diamond:12:0070C0",
                "marker": "diamond:12:0070C0", "legend": "none", "data": D}),
        ch(BL, {"chartType": "scatter", "scatterstyle": "marker", "title": "square:8:70AD47",
                "marker": "square:8:70AD47", "legend": "none", "data": D}),
        # markercolor — per-series marker fill color (independent of marker= compound form)
        ch(BR, {"chartType": "scatter", "scatterstyle": "marker", "title": "markercolor=E63946",
                "marker": "circle:10", "markercolor": "E63946", "legend": "none", "data": D}),
    ]
    warn_unsupported(doc.batch(items), "slide2")

    # --- Slide 3: Title & legend ---
    items = new_slide("Title & legend — title.overlay / legend.overlay")
    items += [
        ch(TL, {"chartType": "scatter", "scatterstyle": "smoothMarker", "title": "Styled title",
                "title.font": "Georgia", "title.size": "20", "title.color": "4472C4", "title.bold": "true",
                "legend": "bottom", "data": D2}),
        ch(TR, {"chartType": "scatter", "scatterstyle": "lineMarker", "title": "legend=top + legendFont",
                "legend": "top", "legendFont": "10:333333:Calibri", "data": D2}),
        ch(BL, {"chartType": "scatter", "scatterstyle": "lineMarker", "title": "legend.overlay=true",
                "legend": "topRight", "legend.overlay": "true", "data": D2}),
        # title.overlay — title rendered over the plot area (saves vertical space)
        ch(BR, {"chartType": "scatter", "scatterstyle": "marker", "title": "title.overlay=true",
                "title.overlay": "true", "legend": "none", "data": D2}),
    ]
    warn_unsupported(doc.batch(items), "slide3")

    # --- Slide 4: Data labels ---
    items = new_slide("Data labels — flags + labelfont")
    items += [
        ch(TL, {"chartType": "scatter", "scatterstyle": "marker", "title": "value", "dataLabels": "value",
                "labelfont": "9:333333:Calibri", "legend": "none", "data": D}),
        ch(TR, {"chartType": "scatter", "scatterstyle": "marker", "title": "value,series",
                "dataLabels": "value,series", "legend": "none", "data": D2}),
        ch(BL, {"chartType": "scatter", "scatterstyle": "marker", "title": "labelPos=top",
                "dataLabels": "value", "labelPos": "top", "legend": "none", "data": D}),
        ch(BR, {"chartType": "scatter", "scatterstyle": "marker", "title": "dataLabels=none",
                "dataLabels": "none", "legend": "none", "data": D}),
    ]
    warn_unsupported(doc.batch(items), "slide4")

    # --- Slide 5: Axes ---
    items = new_slide("Axes — min/max, gridlines, ticks, log on both axes")
    items += [
        ch(TL, {"chartType": "scatter", "scatterstyle": "lineMarker", "title": "min/max + titles",
                "axismin": "0", "axismax": "80", "majorunit": "20", "axistitle": "Y", "cattitle": "X",
                "axisfont": "10:333333:Calibri", "axisline": "666666:1", "axisnumfmt": "#,##0",
                "legend": "none", "data": D}),
        ch(TR, {"chartType": "scatter", "scatterstyle": "marker", "title": "gridlines + minorGridlines",
                "gridlines": "E0E0E0:0.3", "minorGridlines": "F0F0F0:0.25", "legend": "none", "data": D}),
        ch(BL, {"chartType": "scatter", "scatterstyle": "marker", "title": "labelrotation=-30",
                "labelrotation": "-30", "legend": "none", "data": D}),
        ch(BR, {"chartType": "scatter", "scatterstyle": "marker", "title": "logbase=10 (Y)",
                "logbase": "10", "axismin": "1", "axismax": "100", "legend": "none",
                "data": "A:2,5,8,12,20,40,80"}),
    ]
    warn_unsupported(doc.batch(items), "slide5")

    # --- Slide 6: Series styling ---
    items = new_slide("Series styling — colors, gradient, transparency, outline, shadow")
    items += [
        ch(TL, {"chartType": "scatter", "scatterstyle": "marker", "title": "colors + seriesoutline",
                "colors": "4472C4,ED7D31", "seriesoutline": "000000:0.5", "legend": "bottom", "data": D2}),
        ch(TR, {"chartType": "scatter", "scatterstyle": "marker", "title": "gradient + seriesshadow",
                "gradient": "FF6600-FFCC00", "seriesshadow": "000000-5-45-3-50", "legend": "none", "data": D}),
        ch(BL, {"chartType": "scatter", "scatterstyle": "marker", "title": "transparency=30",
                "transparency": "30", "legend": "bottom", "data": D2}),
        ch(BR, {"chartType": "scatter", "scatterstyle": "marker", "title": "per-series gradients",
                "gradients": "FF0000-0000FF;00FF00-FFFF00", "legend": "bottom", "data": D2}),
    ]
    warn_unsupported(doc.batch(items), "slide6")

    # --- Slide 7: Overlays ---
    items = new_slide("Overlays — trendline (linear/poly/exp/movingAvg), errbars, referenceline")
    items += [
        ch(TL, {"chartType": "scatter", "scatterstyle": "marker", "title": "trendline=linear",
                "trendline": "linear", "legend": "none", "data": D}),
        ch(TR, {"chartType": "scatter", "scatterstyle": "marker", "title": "trendline=poly:3",
                "trendline": "poly:3", "legend": "none", "data": D}),
        ch(BL, {"chartType": "scatter", "scatterstyle": "marker", "title": "trendline=movingAvg:3",
                "trendline": "movingAvg:3", "legend": "none", "data": D}),
        ch(BR, {"chartType": "scatter", "scatterstyle": "marker", "title": "errbars=stdDev:1",
                "errbars": "stdDev:1", "legend": "none", "data": D}),
    ]
    warn_unsupported(doc.batch(items), "slide7")

    # --- Slide 8: Per-series Set + presets ---
    items = new_slide("Per-series Set + presets — lineWidth/lineDash/marker/markerSize/color/smooth")
    for box, p in zip([TL, TR, BL], ["minimal", "dark", "corporate"]):
        items.append(ch(box, {"chartType": "scatter", "scatterstyle": "smoothMarker", "preset": p,
                              "title": f"preset={p}", "legend": "bottom", "data": D2}))
    items.append(ch(BR, {"chartType": "scatter", "scatterstyle": "lineMarker",
                         "title": "chart-series Set per series", "legend": "bottom", "data": D2}))
    warn_unsupported(doc.batch(items), "slide8")

    # chart-series Set per series (path-based set, after the chart exists)
    set_items = [
        {"command": "set", "path": f"/slide[{slide}]/chart[4]/series[1]",
         "props": {"name": "Alpha", "color": "C00000", "lineWidth": "2.5", "lineDash": "solid",
                   "marker": "circle", "markerSize": "10", "smooth": "true"}},
        {"command": "set", "path": f"/slide[{slide}]/chart[4]/series[2]",
         "props": {"name": "Beta", "color": "2E75B6", "lineWidth": "1.5", "lineDash": "dash",
                   "marker": "diamond", "markerSize": "8"}},
    ]
    warn_unsupported(doc.batch(set_items), "slide8-set")

    # --- Slide 9: series{N}= named series shorthand ---
    # series{N}= is an alternative to data= that names each series at Add time.
    # series1=Name:v1,v2,…  series2=Name:v1,v2,…  (no shared categories needed for scatter)
    items = new_slide("series{N}= — named series shorthand (name:v1,v2,…)")
    items += [
        ch(TL, {"chartType": "scatter", "scatterstyle": "lineMarker",
                "title": "series1= + series2=",
                "series1": "Alpha:10,25,18,40", "series2": "Beta:5,15,12,30",
                "legend": "bottom"}),
        ch(TR, {"chartType": "scatter", "scatterstyle": "marker",
                "title": "three named series",
                "series1": "Group A:8,20,15", "series2": "Group B:4,12,10", "series3": "Group C:12,28,22",
                "legend": "bottom"}),
        ch(BL, {"chartType": "scatter", "scatterstyle": "smoothMarker",
                "title": "series1 with colors",
                "series1": "Rev:30,45,55,70", "series2": "Cost:20,30,35,42",
                "colors": "4472C4,E63946", "legend": "bottom"}),
        ch(BR, {"chartType": "scatter", "scatterstyle": "marker",
                "title": "series1.* per-series naming + colors=",
                "series1.name": "Alpha", "series1.values": "10,25,18,40",
                "series2.name": "Beta", "series2.values": "5,15,12,30",
                "colors": "4472C4,E63946", "legend": "bottom"}),
    ]
    warn_unsupported(doc.batch(items), "slide9")

    doc.send({"command": "save"})
# context exit closes the resident, flushing the presentation to disk.

print(f"Done: {FILE}  ({slide} slides)")
