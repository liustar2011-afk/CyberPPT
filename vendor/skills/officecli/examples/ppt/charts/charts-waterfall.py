#!/usr/bin/env python3
"""
Waterfall Charts Showcase — increaseColor / decreaseColor / totalColor.

Generates: charts-waterfall.pptx

  Slide 1  Basic                  default colors, single dataset
  Slide 2  Color schemes          increaseColor / decreaseColor / totalColor combinations
  Slide 3  Title & legend
  Slide 4  Data labels
  Slide 5  Axes                   min/max, gridlines, axisnumfmt (currency)
  Slide 6  Backgrounds            chartareafill, plotFill, chartborder, roundedcorners
  Slide 7  Larger story           a real cashflow waterfall with labels
  Slide 8  Presets

SDK twin of charts-waterfall.sh (officecli CLI). Both produce an equivalent
charts-waterfall.pptx. This one drives the **officecli Python SDK**
(`pip install officecli-sdk`): one resident is started and every slide, title
shape and chart is shipped over the named pipe in a single `doc.batch(...)`
round-trip. Each item is the same `{"command","parent","type","props"}` dict
you'd put in an `officecli batch` list.

Usage:
  pip install officecli-sdk          # plus the `officecli` binary on PATH
  python3 charts-waterfall.py
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

FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "charts-waterfall.pptx")

# Quadrant + hero layout boxes (re-used across slides)
TL = {"x": "0.3in", "y": "1.05in", "width": "6.1in", "height": "3in"}
TR = {"x": "6.95in", "y": "1.05in", "width": "6.1in", "height": "3in"}
BL = {"x": "0.3in", "y": "4.25in", "width": "6.1in", "height": "3in"}
BR = {"x": "6.95in", "y": "4.25in", "width": "6.1in", "height": "3in"}
HERO = {"x": "1in", "y": "1.05in", "width": "11.3in", "height": "6.2in"}

CATS = "Start,Q1,Q2,Q3,Q4,End"
D = "Cashflow:100,30,-15,40,-10,145"
CATS_LONG = "Open,Revenue,COGS,Opex,R&D,Tax,Net"
D_LONG = "P&L:100,80,-30,-25,-15,-10,100"


# --- batch-item builders ----------------------------------------------------
_state = {"slide": 0}


def new_slide(title):
    """Add a slide + its bold title shape; returns the two batch items."""
    _state["slide"] += 1
    n = _state["slide"]
    return [
        {"command": "add", "parent": "/", "type": "slide", "props": {}},
        {"command": "add", "parent": f"/slide[{n}]", "type": "shape",
         "props": {"text": title, "size": "24", "bold": "true", "autoFit": "normal",
                   "x": "0.5in", "y": "0.3in", "width": "12.3in", "height": "0.6in"}},
    ]


def ch(box, props):
    """One `add chart` item on the current slide in batch-shape."""
    n = _state["slide"]
    return {"command": "add", "parent": f"/slide[{n}]", "type": "chart",
            "props": {**box, **props}}


print(f"Building {FILE} ...")

with officecli.create(FILE, "--force") as doc:
    items = []

    # ---- Slide 1: Basic waterfall — default colors ----
    items += new_slide("Basic waterfall — default colors")
    items += [
        ch(TL, {"chartType": "waterfall", "title": "Default colors", "legend": "none",
                "categories": CATS, "data": D}),
        ch(TR, {"chartType": "waterfall", "title": "Default + dataTable", "dataTable": "true",
                "legend": "none", "categories": CATS, "data": D}),
        ch(BL, {"chartType": "waterfall", "title": "With legend", "legend": "bottom",
                "categories": CATS, "data": D}),
        ch(BR, {"chartType": "waterfall", "title": "7-step P&L", "legend": "none",
                "categories": CATS_LONG, "data": D_LONG}),
    ]

    # ---- Slide 2: Color schemes — increaseColor / decreaseColor / totalColor ----
    items += new_slide("Color schemes — increaseColor / decreaseColor / totalColor")
    items += [
        ch(TL, {"chartType": "waterfall", "title": "green/red/blue (default-ish)",
                "increaseColor": "00AA00", "decreaseColor": "FF0000", "totalColor": "4472C4",
                "legend": "none", "categories": CATS, "data": D}),
        ch(TR, {"chartType": "waterfall", "title": "corporate (teal/orange/navy)",
                "increaseColor": "008080", "decreaseColor": "D86600", "totalColor": "1F3864",
                "legend": "none", "categories": CATS, "data": D}),
        ch(BL, {"chartType": "waterfall", "title": "monochrome",
                "increaseColor": "606060", "decreaseColor": "A0A0A0", "totalColor": "303030",
                "legend": "none", "categories": CATS, "data": D}),
        ch(BR, {"chartType": "waterfall", "title": "vivid",
                "increaseColor": "00C853", "decreaseColor": "D50000", "totalColor": "2962FF",
                "legend": "none", "categories": CATS, "data": D}),
    ]

    # ---- Slide 3: Title & legend ----
    items += new_slide("Title & legend")
    items += [
        ch(TL, {"chartType": "waterfall", "title": "Styled title", "title.font": "Georgia",
                "title.size": "20", "title.color": "4472C4", "title.bold": "true",
                "legend": "bottom", "categories": CATS, "data": D}),
        ch(TR, {"chartType": "waterfall", "title": "legend=top + legendFont", "legend": "top",
                "legendFont": "10:333333:Calibri", "categories": CATS, "data": D}),
        ch(BL, {"chartType": "waterfall", "title": "legend.overlay=true", "legend": "topRight",
                "legend.overlay": "true", "categories": CATS, "data": D}),
        ch(BR, {"chartType": "waterfall", "autotitledeleted": "true", "legend": "none",
                "categories": CATS, "data": D}),
    ]

    # ---- Slide 4: Data labels — flags + labelfont ----
    items += new_slide("Data labels — flags + labelfont")
    items += [
        ch(TL, {"chartType": "waterfall", "title": "value", "dataLabels": "value",
                "labelfont": "10:333333:Calibri", "legend": "none", "categories": CATS, "data": D}),
        ch(TR, {"chartType": "waterfall", "title": "value,category", "dataLabels": "value,category",
                "legend": "none", "categories": CATS, "data": D}),
        ch(BL, {"chartType": "waterfall", "title": "value @ outsideEnd", "dataLabels": "value",
                "labelPos": "outsideEnd", "legend": "none", "categories": CATS, "data": D}),
        ch(BR, {"chartType": "waterfall", "title": "dataLabels=none", "dataLabels": "none",
                "legend": "none", "categories": CATS, "data": D}),
    ]

    # ---- Slide 5: Axes — min/max, titles, gridlines, axisnumfmt ----
    items += new_slide("Axes — min/max, titles, gridlines, axisnumfmt")
    items += [
        ch(TL, {"chartType": "waterfall", "title": "min/max + titles", "axismin": "0", "axismax": "200",
                "majorunit": "50", "axistitle": "USD", "cattitle": "Phase",
                "axisfont": "10:333333:Calibri", "axisnumfmt": "$#,##0",
                "legend": "none", "categories": CATS, "data": D}),
        ch(TR, {"chartType": "waterfall", "title": "gridlines + minorGridlines",
                "gridlines": "E0E0E0:0.3", "minorGridlines": "F0F0F0:0.25",
                "legend": "none", "categories": CATS, "data": D}),
        ch(BL, {"chartType": "waterfall", "title": "labelrotation=-30", "labelrotation": "-30",
                "legend": "none", "categories": CATS, "data": D}),
        ch(BR, {"chartType": "waterfall", "title": "dispunits=thousands", "dispunits": "thousands",
                "legend": "none", "categories": CATS,
                "data": "USD:100000,30000,-15000,40000,-10000,145000"}),
    ]

    # ---- Slide 6: Backgrounds — chartareafill, plotFill, chartborder, roundedcorners ----
    items += new_slide("Backgrounds — chartareafill, plotFill, chartborder, roundedcorners")
    items += [
        ch(TL, {"chartType": "waterfall", "title": "chartareafill + chartborder",
                "chartareafill": "FFF8E7", "chartborder": "000000:1", "plotFill": "FAFAFA",
                "plotborder": "CCCCCC:0.5", "legend": "none", "categories": CATS, "data": D}),
        ch(TR, {"chartType": "waterfall", "title": "roundedcorners=true", "roundedcorners": "true",
                "chartborder": "4472C4:2", "legend": "none", "categories": CATS, "data": D}),
        ch(BL, {"chartType": "waterfall", "title": "plotFill=none", "plotFill": "none",
                "gridlines": "none", "legend": "none", "categories": CATS, "data": D}),
        ch(BR, {"chartType": "waterfall", "title": "chartareafill=none", "chartareafill": "none",
                "legend": "none", "categories": CATS, "data": D}),
    ]

    # ---- Slide 7: Hero cashflow waterfall — full slide with labels ----
    items += new_slide("Hero cashflow waterfall — full slide with labels")
    items += [
        ch(HERO, {"chartType": "waterfall", "title": "FY24 P&L Walk",
                  "title.font": "Helvetica", "title.size": "22", "title.bold": "true",
                  "title.color": "1F3864",
                  "increaseColor": "00C853", "decreaseColor": "D50000", "totalColor": "2962FF",
                  "dataLabels": "value,category", "labelPos": "outsideEnd",
                  "labelfont": "11:333333:Helvetica", "axistitle": "USD", "cattitle": "",
                  "axisnumfmt": "$#,##0", "gridlines": "E0E0E0:0.3",
                  "legend": "none", "categories": CATS_LONG, "data": D_LONG}),
    ]

    # ---- Slide 8: Presets ----
    items += new_slide("Presets")
    for box, p in zip([TL, TR, BL, BR], ["minimal", "dark", "corporate", "colorful"]):
        items += [ch(box, {"chartType": "waterfall", "preset": p, "title": f"preset={p}",
                           "legend": "none", "categories": CATS, "data": D})]

    doc.batch(items)
    print(f"  added {_state['slide']} slides, {len(items)} items")

    doc.send({"command": "save"})
# context exit closes the resident, flushing the presentation to disk.

print(f"Generated: {FILE}  ({_state['slide']} slides)")
