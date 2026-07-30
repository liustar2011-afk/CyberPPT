#!/usr/bin/env python3
"""
Area Charts Showcase — area, stackedArea, percentStackedArea, area3d.

Generates: charts-area.pptx

  Slide 1  Variants           area / stackedArea / percentStackedArea / area3d
  Slide 2  Title & legend     title.* + legend positions + legendFont
  Slide 3  Data labels        flags + labelPos + labelfont
  Slide 4  Axes               min/max, titles, fonts, gridlines, ticks, labelrotation
  Slide 5  Series styling     colors, gradient, gradients, transparency, seriesoutline, seriesshadow
  Slide 6  Overlays           referenceline, errbars, trendline
  Slide 7  Backgrounds        chartareafill, plotFill, chartborder, plotborder, roundedcorners
  Slide 8  Presets & per-ser  preset bundles + seriesN.* + chart-series Set

SDK twin of charts-area.sh (officecli CLI). Both produce an equivalent
charts-area.pptx. This one drives the **officecli Python SDK**
(`pip install officecli-sdk`): one resident is started and every slide, title
shape and chart is shipped over the named pipe in a single `doc.batch(...)`
round-trip. Each item is the same `{"command","parent","type","props"}` dict
you'd put in an `officecli batch` list — slides are added before the charts
that reference them, so in-order batch application keeps `/slide[N]` valid.

Forward-compat: any prop the running officecli build doesn't yet support is
reported as an `unsupported_property` warning in the batch envelope rather than
aborting the run (batch defaults to stop_on_error=False) — the showcase still
builds, and the gaps stay visible in the returned envelope.

Usage:
  pip install officecli-sdk          # plus the `officecli` binary on PATH
  python3 charts-area.py
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

FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "charts-area.pptx")

# Four quadrant boxes — same layout the CLI twin uses for every slide.
TL = {"x": "0.3in", "y": "1.05in", "width": "6.1in", "height": "3in"}
TR = {"x": "6.95in", "y": "1.05in", "width": "6.1in", "height": "3in"}
BL = {"x": "0.3in", "y": "4.25in", "width": "6.1in", "height": "3in"}
BR = {"x": "6.95in", "y": "4.25in", "width": "6.1in", "height": "3in"}
CATS = "Mon,Tue,Wed,Thu,Fri"
D = "A:50,60,70,65,80"
D2 = "Web:50,60,70,65,80;Mobile:30,35,42,48,55"

# slide counter shared by the two builders below
_slide = 0


def new_slide(title, items):
    """Append one `add slide` + its title `add shape` to `items`; return slide #."""
    global _slide
    _slide += 1
    items.append({"command": "add", "parent": "/", "type": "slide", "props": {}})
    items.append({"command": "add", "parent": f"/slide[{_slide}]", "type": "shape",
                  "props": {"text": title, "size": 24, "bold": "true", "autoFit": "normal",
                            "x": "0.5in", "y": "0.3in", "width": "12.3in", "height": "0.6in"}})
    return _slide


def ch(items, box, props):
    """Append one `add chart` (box + chart props) to the current slide."""
    items.append({"command": "add", "parent": f"/slide[{_slide}]", "type": "chart",
                  "props": {**box, **props}})


print(f"Building {FILE} ...")

with officecli.create(FILE, "--force") as doc:
    items = []

    # ============ Slide 1: variants ============
    new_slide("Area variants — area / stackedArea / percentStackedArea / area3d", items)
    ch(items, TL, {"chartType": "area", "title": "area", "legend": "bottom", "categories": CATS, "data": D2})
    ch(items, TR, {"chartType": "stackedArea", "title": "stackedArea", "legend": "bottom", "categories": CATS, "data": D2})
    ch(items, BL, {"chartType": "percentStackedArea", "title": "percentStackedArea", "legend": "bottom", "categories": CATS, "data": D2})
    ch(items, BR, {"chartType": "area3d", "title": "area3d", "view3d": "15,20,30", "legend": "bottom", "categories": CATS, "data": D2})

    # ============ Slide 2: title & legend ============
    new_slide("Title & legend", items)
    ch(items, TL, {"chartType": "area", "title": "Styled title", "title.font": "Georgia", "title.size": "20",
                   "title.color": "4472C4", "title.bold": "true", "legend": "bottom", "categories": CATS, "data": D2})
    ch(items, TR, {"chartType": "area", "title": "legend=top + legendFont", "legend": "top",
                   "legendFont": "10:333333:Calibri", "categories": CATS, "data": D2})
    ch(items, BL, {"chartType": "area", "title": "legend.overlay=true", "legend": "topRight",
                   "legend.overlay": "true", "categories": CATS, "data": D2})
    ch(items, BR, {"chartType": "area", "autotitledeleted": "true", "legend": "none", "categories": CATS, "data": D2})

    # ============ Slide 3: data labels ============
    new_slide("Data labels — flags, labelPos, labelfont", items)
    ch(items, TL, {"chartType": "area", "title": "dataLabels=value", "dataLabels": "value",
                   "labelfont": "10:333333:Calibri", "legend": "none", "categories": CATS, "data": D})
    ch(items, TR, {"chartType": "stackedArea", "title": "stacked + center labels", "dataLabels": "value",
                   "labelPos": "center", "legend": "bottom", "categories": CATS, "data": D2})
    ch(items, BL, {"chartType": "area", "title": "value,category", "dataLabels": "value,category",
                   "labelfont": "9:333333:Calibri", "legend": "none", "categories": CATS, "data": D})
    ch(items, BR, {"chartType": "area", "title": "dataLabels=none", "dataLabels": "none", "legend": "none",
                   "categories": CATS, "data": D})

    # ============ Slide 4: axes ============
    new_slide("Axes — min/max, gridlines, ticks, labelrotation", items)
    ch(items, TL, {"chartType": "area", "title": "min/max + titles", "legend": "none",
                   "axismin": "0", "axismax": "100", "majorunit": "25", "axistitle": "Value", "cattitle": "Day",
                   "axisfont": "10:333333:Calibri", "axisline": "666666:1", "axisnumfmt": "#,##0",
                   "categories": CATS, "data": D})
    ch(items, TR, {"chartType": "area", "title": "gridlines + ticks", "legend": "none",
                   "gridlines": "E0E0E0:0.3", "minorGridlines": "F0F0F0:0.25",
                   "majorTickMark": "out", "minorTickMark": "in", "tickLabelPos": "nextTo",
                   "categories": CATS, "data": D})
    ch(items, BL, {"chartType": "area", "title": "labelrotation=-30", "legend": "none", "labelrotation": "-30",
                   "categories": "January,February,March,April,May,June", "data": "A:60,90,140,180,160,210"})
    ch(items, BR, {"chartType": "area", "title": "dispunits=thousands", "legend": "none", "dispunits": "thousands",
                   "categories": CATS, "data": "Rev:120000,135000,148000,162000,180000"})

    # ============ Slide 5: series styling ============
    new_slide("Series styling — colors, gradient(s), transparency, outline, shadow", items)
    ch(items, TL, {"chartType": "area", "title": "colors + seriesoutline", "legend": "bottom",
                   "colors": "4472C4,ED7D31", "seriesoutline": "000000:0.5", "categories": CATS, "data": D2})
    ch(items, TR, {"chartType": "area", "title": "gradient + seriesshadow", "legend": "none",
                   "gradient": "FF6600-FFCC00:90", "seriesshadow": "000000-5-45-3-50",
                   "categories": CATS, "data": D})
    ch(items, BL, {"chartType": "area", "title": "per-series gradients + transparency=30",
                   "gradients": "FF0000-0000FF;00FF00-FFFF00", "transparency": "30",
                   "legend": "bottom", "categories": CATS, "data": D2})
    ch(items, BR, {"chartType": "area", "title": "single + transparency=50", "transparency": "50",
                   "colors": "4472C4", "legend": "none", "categories": CATS, "data": D})

    # ============ Slide 6: overlays ============
    new_slide("Overlays — referenceline, errbars, trendline", items)
    ch(items, TL, {"chartType": "area", "title": "referenceline=60", "referenceline": "60:FF0000:Target",
                   "legend": "none", "categories": CATS, "data": D})
    ch(items, TR, {"chartType": "area", "title": "errbars=percentage:10", "errbars": "percentage:10",
                   "legend": "none", "categories": CATS, "data": D})
    ch(items, BL, {"chartType": "area", "title": "trendline=linear", "trendline": "linear",
                   "legend": "none", "categories": CATS, "data": D})
    ch(items, BR, {"chartType": "area", "title": "trendline=movingAvg:3", "trendline": "movingAvg:3",
                   "legend": "none", "categories": CATS, "data": D})

    # ============ Slide 7: backgrounds ============
    new_slide("Backgrounds — chartareafill, plotFill, chartborder, plotborder, roundedcorners", items)
    ch(items, TL, {"chartType": "area", "title": "chartareafill + plotFill + borders", "legend": "bottom",
                   "chartareafill": "FFF8E7", "plotFill": "FAFAFA", "chartborder": "000000:1",
                   "plotborder": "CCCCCC:0.5", "categories": CATS, "data": D2})
    ch(items, TR, {"chartType": "area", "title": "roundedcorners=true", "roundedcorners": "true",
                   "chartborder": "4472C4:2", "legend": "bottom", "categories": CATS, "data": D2})
    ch(items, BL, {"chartType": "area", "title": "plotFill=none", "plotFill": "none", "gridlines": "none",
                   "legend": "none", "categories": CATS, "data": D})
    ch(items, BR, {"chartType": "area", "title": "dataTable=true", "dataTable": "true", "legend": "bottom",
                   "categories": CATS, "data": D2})

    # ============ Slide 8: presets & per-series control ============
    new_slide("Presets & per-series control", items)
    for box, p in zip([TL, TR, BL], ["minimal", "dark", "corporate"]):
        ch(items, box, {"chartType": "area", "preset": p, "title": f"preset={p}", "legend": "bottom",
                        "categories": CATS, "data": D2})
    ch(items, BR, {"chartType": "area", "title": "seriesN.* + chart-series Set", "legend": "bottom",
                   "categories": CATS,
                   "series1.name": "Web", "series1.values": "50,60,70,65,80", "series1.color": "4472C4",
                   "series2.name": "Mobile", "series2.values": "30,35,42,48,55", "series2.color": "ED7D31"})
    # chart-series Set — recolour/rename series[1] of the BR chart after Add.
    # In-batch, sequential: the chart already exists by the time this runs.
    items.append({"command": "set", "path": f"/slide[{_slide}]/chart[4]/series[1]",
                  "props": {"name": "Renamed Web", "color": "C00000"}})

    doc.batch(items)
    print(f"  added {_slide} slides ({len(items)} batch items)")

# context exit closes the resident, flushing the presentation to disk.
print(f"Generated: {FILE}  ({_slide} slides)")
