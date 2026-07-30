#!/usr/bin/env python3
"""
Bubble Charts Showcase — generates charts-bubble.pptx exercising the pptx
`chart` element with chartType=bubble across the full styling surface.

SDK twin of charts-bubble.sh (officecli CLI). Both produce an equivalent
charts-bubble.pptx. This one drives the **officecli Python SDK**
(`pip install officecli-sdk`): one resident is started and every slide, title
shape, and chart is shipped over the named pipe in `doc.batch(...)`
round-trips. Each item is the same `{"command","parent","type","props"}` dict
you'd put in an `officecli batch` list.

  Slide 1  bubbleScale            50 / 100 / 150 / 200 (% of default)
  Slide 2  sizerepresents         area vs width
  Slide 3  shownegbubbles         true vs false (with negative values)
  Slide 4  Title & legend         title.* + legend positions + legendFont
  Slide 5  Data labels            value/category/bubbleSize, labelfont
  Slide 6  Axes                   min/max, gridlines, ticks
  Slide 7  Series styling         colors, gradient, transparency, outline, shadow
  Slide 8  Presets & per-series   preset bundles + chart-series Set

Usage:
  pip install officecli-sdk          # plus the `officecli` binary on PATH
  python3 charts-bubble.py
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

FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "charts-bubble.pptx")

# Quadrant boxes (same layout the CLI twin uses for every slide).
TL = {"x": "0.3in", "y": "1.05in", "width": "6.1in", "height": "3in"}
TR = {"x": "6.95in", "y": "1.05in", "width": "6.1in", "height": "3in"}
BL = {"x": "0.3in", "y": "4.25in", "width": "6.1in", "height": "3in"}
BR = {"x": "6.95in", "y": "4.25in", "width": "6.1in", "height": "3in"}
D = "A:5,12,8,18,22,9,15,11"
D2 = "A:5,12,8,18,22,9;B:7,11,15,9,20,14"

_slide = 0


def new_slide(title):
    """Batch items: one `add slide` + its bold title shape. Bumps the slide index."""
    global _slide
    _slide += 1
    return [
        {"command": "add", "parent": "/", "type": "slide", "props": {}},
        {"command": "add", "parent": f"/slide[{_slide}]", "type": "shape",
         "props": {"text": title, "size": "24", "bold": "true", "autoFit": "normal",
                   "x": "0.5in", "y": "0.3in", "width": "12.3in", "height": "0.6in"}},
    ]


def ch(box, props):
    """One `add chart` item in the current slide, merging the quadrant box."""
    return {"command": "add", "parent": f"/slide[{_slide}]", "type": "chart",
            "props": {**box, **props}}


print(f"Building {FILE} ...")

with officecli.create(FILE, "--force") as doc:
    items = []

    # --- Slide 1: bubbleScale 50 / 100 / 150 / 200 -----------------------------
    items += new_slide("bubbleScale — 50 / 100 / 150 / 200 (% of default)")
    for box, s in zip([TL, TR, BL, BR], [50, 100, 150, 200]):
        items.append(ch(box, {"chartType": "bubble", "title": f"bubbleScale={s}",
                              "bubbleScale": str(s), "legend": "none", "data": D}))

    # --- Slide 2: sizerepresents area vs width ---------------------------------
    items += new_slide("sizerepresents — area vs width")
    items.append(ch(TL, {"chartType": "bubble", "title": "sizerepresents=area",
                         "sizerepresents": "area", "legend": "none", "data": D}))
    items.append(ch(TR, {"chartType": "bubble", "title": "sizerepresents=width",
                         "sizerepresents": "width", "legend": "none", "data": D}))
    items.append(ch(BL, {"chartType": "bubble", "title": "area + 2 series",
                         "sizerepresents": "area", "legend": "bottom", "data": D2}))
    items.append(ch(BR, {"chartType": "bubble", "title": "width + 2 series",
                         "sizerepresents": "width", "legend": "bottom", "data": D2}))

    # --- Slide 3: shownegbubbles false vs true ---------------------------------
    items += new_slide("shownegbubbles — false vs true")
    items.append(ch(TL, {"chartType": "bubble", "title": "shownegbubbles=false",
                         "shownegbubbles": "false", "legend": "none",
                         "data": "A:5,-8,12,-15,18,22"}))
    items.append(ch(TR, {"chartType": "bubble", "title": "shownegbubbles=true",
                         "shownegbubbles": "true", "legend": "none",
                         "data": "A:5,-8,12,-15,18,22"}))
    items.append(ch(BL, {"chartType": "bubble", "title": "false + 2 series",
                         "shownegbubbles": "false", "legend": "bottom",
                         "data": "A:5,-8,12,-15,18,22;B:8,11,-9,14,-16,20"}))
    items.append(ch(BR, {"chartType": "bubble", "title": "true + 2 series",
                         "shownegbubbles": "true", "legend": "bottom",
                         "data": "A:5,-8,12,-15,18,22;B:8,11,-9,14,-16,20"}))

    # --- Slide 4: Title & legend -----------------------------------------------
    items += new_slide("Title & legend")
    items.append(ch(TL, {"chartType": "bubble", "title": "Styled title",
                         "title.font": "Georgia", "title.size": "20",
                         "title.color": "4472C4", "title.bold": "true",
                         "legend": "bottom", "data": D2}))
    items.append(ch(TR, {"chartType": "bubble", "title": "legend=top + legendFont",
                         "legend": "top", "legendFont": "10:333333:Calibri", "data": D2}))
    items.append(ch(BL, {"chartType": "bubble", "title": "legend.overlay=true",
                         "legend": "topRight", "legend.overlay": "true", "data": D2}))
    items.append(ch(BR, {"chartType": "bubble", "autotitledeleted": "true",
                         "legend": "none", "data": D2}))

    # --- Slide 5: Data labels --------------------------------------------------
    items += new_slide("Data labels — flags + labelfont")
    items.append(ch(TL, {"chartType": "bubble", "title": "value", "dataLabels": "value",
                         "labelfont": "9:333333:Calibri", "legend": "none", "data": D}))
    items.append(ch(TR, {"chartType": "bubble", "title": "value,series",
                         "dataLabels": "value,series", "legend": "none", "data": D2}))
    items.append(ch(BL, {"chartType": "bubble", "title": "labelPos=top",
                         "dataLabels": "value", "labelPos": "top",
                         "legend": "none", "data": D}))
    items.append(ch(BR, {"chartType": "bubble", "title": "dataLabels=none",
                         "dataLabels": "none", "legend": "none", "data": D}))

    # --- Slide 6: Axes ---------------------------------------------------------
    items += new_slide("Axes — min/max, gridlines, ticks")
    items.append(ch(TL, {"chartType": "bubble", "title": "min/max + titles",
                         "axismin": "0", "axismax": "30", "majorunit": "10",
                         "axistitle": "Y", "cattitle": "X",
                         "axisfont": "10:333333:Calibri", "axisline": "666666:1",
                         "legend": "none", "data": D}))
    items.append(ch(TR, {"chartType": "bubble", "title": "gridlines + minorGridlines",
                         "gridlines": "E0E0E0:0.3", "minorGridlines": "F0F0F0:0.25",
                         "legend": "none", "data": D}))
    items.append(ch(BL, {"chartType": "bubble", "title": "labelrotation=-30",
                         "labelrotation": "-30", "legend": "none", "data": D}))
    items.append(ch(BR, {"chartType": "bubble", "title": "dispunits=hundreds",
                         "dispunits": "hundreds", "legend": "none",
                         "data": "A:500,1200,800,1800,2200,900"}))

    # --- Slide 7: Series styling -----------------------------------------------
    items += new_slide("Series styling — colors, gradient, transparency, outline, shadow")
    items.append(ch(TL, {"chartType": "bubble", "title": "colors + seriesoutline",
                         "colors": "4472C4,ED7D31", "seriesoutline": "000000:0.5",
                         "legend": "bottom", "data": D2}))
    items.append(ch(TR, {"chartType": "bubble", "title": "gradient + seriesshadow",
                         "gradient": "FF6600-FFCC00", "seriesshadow": "000000-5-45-3-50",
                         "legend": "none", "data": D}))
    items.append(ch(BL, {"chartType": "bubble", "title": "transparency=30",
                         "transparency": "30", "legend": "bottom", "data": D2}))
    items.append(ch(BR, {"chartType": "bubble", "title": "per-series gradients",
                         "gradients": "FF0000-0000FF;00FF00-FFFF00",
                         "legend": "bottom", "data": D2}))

    # --- Slide 8: Presets & per-series Set -------------------------------------
    items += new_slide("Presets & per-series Set")
    for box, p in zip([TL, TR, BL], ["minimal", "dark", "corporate"]):
        items.append(ch(box, {"chartType": "bubble", "preset": p, "title": f"preset={p}",
                              "legend": "bottom", "data": D2}))
    items.append(ch(BR, {"chartType": "bubble", "title": "chart-series Set name+color",
                         "legend": "bottom", "data": D2}))

    doc.batch(items)
    print(f"  added {_slide} slides ({len(items)} items)")

    # chart-series Set (slide 8, chart[4]) — must run after the chart exists.
    doc.batch([
        {"command": "set", "path": f"/slide[{_slide}]/chart[4]/series[1]",
         "props": {"name": "Renamed A", "color": "C00000"}},
        {"command": "set", "path": f"/slide[{_slide}]/chart[4]/series[2]",
         "props": {"name": "Renamed B", "color": "2E75B6"}},
    ])
    print("  applied per-series name+color Set on slide 8 chart[4]")

    doc.send({"command": "save"})

print(f"Generated: {FILE}  ({_slide} slides)")
