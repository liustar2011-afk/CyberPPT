#!/usr/bin/env python3
"""
Stock Charts Showcase — High-Low-Close and OHLC variants.

Generates: charts-stock.pptx

  Slide 1  Basic stock         3-series HLC + 4-series OHLC
  Slide 2  Hi-low / up-down    hilowlines, updownbars
  Slide 3  Title & legend
  Slide 4  Data labels
  Slide 5  Axes                min/max, gridlines, axisnumfmt (currency)
  Slide 6  Series styling      colors, transparency, outline, shadow
  Slide 7  Backgrounds         chartareafill, plotFill, chartborder
  Slide 8  Presets & per-ser   preset bundles + chart-series Set

SDK twin of charts-stock.sh (officecli CLI). Both produce an equivalent
charts-stock.pptx. This one drives the **officecli Python SDK**
(`pip install officecli-sdk`): one resident is started and every slide's shapes
and charts are shipped over the named pipe in `doc.batch(...)` round-trips.
Each item is the same `{"command","parent","type","props"}` dict you'd put in
an `officecli batch` list. Unsupported props are forwarded as-is: the resident
warns (forward-compat) without failing the batch.

Usage:
  pip install officecli-sdk          # plus the `officecli` binary on PATH
  python3 charts-stock.py
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

FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "charts-stock.pptx")

# Quadrant boxes (top-left / top-right / bottom-left / bottom-right).
TL = {"x": "0.3in", "y": "1.05in", "width": "6.1in", "height": "3in"}
TR = {"x": "6.95in", "y": "1.05in", "width": "6.1in", "height": "3in"}
BL = {"x": "0.3in", "y": "4.25in", "width": "6.1in", "height": "3in"}
BR = {"x": "6.95in", "y": "4.25in", "width": "6.1in", "height": "3in"}
CATS = "Mon,Tue,Wed,Thu,Fri"
HLC = "High:130,135,140,138,145;Low:118,122,128,125,132;Close:125,130,135,132,140"
OHLC = "Open:120,128,130,135,138;High:130,135,140,138,145;Low:118,122,128,125,132;Close:125,130,135,132,140"


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

    # ---- Slide 1: Basic stock — HLC vs OHLC ------------------------------
    doc.batch(slide_items(1, "Basic stock — High-Low-Close vs Open-High-Low-Close", [
        (TL, {"chartType": "stock", "title": "HLC", "legend": "bottom", "categories": CATS, "data": HLC}),
        (TR, {"chartType": "stock", "title": "OHLC", "legend": "bottom", "categories": CATS, "data": OHLC}),
        (BL, {"chartType": "stock", "title": "HLC + dataTable=true", "dataTable": "true",
              "legend": "bottom", "categories": CATS, "data": HLC}),
        (BR, {"chartType": "stock", "title": "OHLC + dataTable=true", "dataTable": "true",
              "legend": "bottom", "categories": CATS, "data": OHLC}),
    ]))

    # ---- Slide 2: hilowlines & updownbars --------------------------------
    doc.batch(slide_items(2, "hilowlines & updownbars", [
        (TL, {"chartType": "stock", "title": "hilowlines=true", "hilowlines": "true",
              "legend": "bottom", "categories": CATS, "data": HLC}),
        (TR, {"chartType": "stock", "title": "hilowlines=808080:0.5", "hilowlines": "808080:0.5",
              "legend": "bottom", "categories": CATS, "data": HLC}),
        (BL, {"chartType": "stock", "title": "updownbars=true (OHLC)", "updownbars": "true",
              "legend": "bottom", "categories": CATS, "data": OHLC}),
        (BR, {"chartType": "stock", "title": "updownbars=150:00AA00:FF0000",
              "updownbars": "150:00AA00:FF0000", "legend": "bottom", "categories": CATS, "data": OHLC}),
    ]))

    # ---- Slide 3: Title & legend -----------------------------------------
    doc.batch(slide_items(3, "Title & legend", [
        (TL, {"chartType": "stock", "title": "Styled title", "title.font": "Georgia", "title.size": "20",
              "title.color": "4472C4", "title.bold": "true", "legend": "bottom", "categories": CATS, "data": HLC}),
        (TR, {"chartType": "stock", "title": "legend=top + legendFont", "legend": "top",
              "legendFont": "10:333333:Calibri", "categories": CATS, "data": HLC}),
        (BL, {"chartType": "stock", "title": "legend.overlay=true", "legend": "topRight",
              "legend.overlay": "true", "categories": CATS, "data": HLC}),
        (BR, {"chartType": "stock", "autotitledeleted": "true", "legend": "none", "categories": CATS, "data": HLC}),
    ]))

    # ---- Slide 4: Data labels — flags + labelfont ------------------------
    doc.batch(slide_items(4, "Data labels — flags + labelfont", [
        (TL, {"chartType": "stock", "title": "dataLabels=value", "dataLabels": "value",
              "labelfont": "9:333333:Calibri", "legend": "bottom", "categories": CATS, "data": HLC}),
        (TR, {"chartType": "stock", "title": "value,series", "dataLabels": "value,series",
              "legend": "bottom", "categories": CATS, "data": HLC}),
        (BL, {"chartType": "stock", "title": "value,category", "dataLabels": "value,category",
              "legend": "bottom", "categories": CATS, "data": HLC}),
        (BR, {"chartType": "stock", "title": "dataLabels=none", "dataLabels": "none",
              "legend": "bottom", "categories": CATS, "data": HLC}),
    ]))

    # ---- Slide 5: Axes — min/max, gridlines, currency format -------------
    doc.batch(slide_items(5, "Axes — min/max, gridlines, currency format", [
        (TL, {"chartType": "stock", "title": "min/max + titles", "axismin": "100", "axismax": "160",
              "majorunit": "10", "axistitle": "Price (USD)", "cattitle": "Day",
              "axisfont": "10:333333:Calibri", "axisnumfmt": "$#,##0.00",
              "legend": "bottom", "categories": CATS, "data": HLC}),
        (TR, {"chartType": "stock", "title": "gridlines + minorGridlines",
              "gridlines": "E0E0E0:0.3", "minorGridlines": "F0F0F0:0.25",
              "legend": "bottom", "categories": CATS, "data": HLC}),
        (BL, {"chartType": "stock", "title": "labelrotation=-30", "labelrotation": "-30",
              "legend": "bottom", "categories": CATS, "data": HLC}),
        (BR, {"chartType": "stock", "title": "dispunits=hundreds", "dispunits": "hundreds",
              "legend": "bottom", "categories": CATS,
              "data": "High:13000,13500,14000,13800,14500;Low:11800,12200,12800,12500,13200;Close:12500,13000,13500,13200,14000"}),
    ]))

    # ---- Slide 6: Series styling — colors, transparency, outline, shadow -
    doc.batch(slide_items(6, "Series styling — colors, transparency, outline, shadow", [
        (TL, {"chartType": "stock", "title": "colors", "colors": "4472C4,ED7D31,70AD47",
              "legend": "bottom", "categories": CATS, "data": HLC}),
        (TR, {"chartType": "stock", "title": "seriesoutline", "seriesoutline": "000000:1",
              "legend": "bottom", "categories": CATS, "data": HLC}),
        (BL, {"chartType": "stock", "title": "transparency=30", "transparency": "30",
              "legend": "bottom", "categories": CATS, "data": HLC}),
        (BR, {"chartType": "stock", "title": "seriesshadow", "seriesshadow": "000000-5-45-3-50",
              "legend": "bottom", "categories": CATS, "data": HLC}),
    ]))

    # ---- Slide 7: Backgrounds — chartareafill, plotFill, borders ---------
    doc.batch(slide_items(7, "Backgrounds — chartareafill, plotFill, chartborder, roundedcorners", [
        (TL, {"chartType": "stock", "title": "chartareafill + plotFill + borders",
              "chartareafill": "FFF8E7", "plotFill": "FAFAFA", "chartborder": "000000:1",
              "plotborder": "CCCCCC:0.5", "legend": "bottom", "categories": CATS, "data": HLC}),
        (TR, {"chartType": "stock", "title": "roundedcorners=true", "roundedcorners": "true",
              "chartborder": "4472C4:2", "legend": "bottom", "categories": CATS, "data": HLC}),
        (BL, {"chartType": "stock", "title": "plotFill=none", "plotFill": "none", "gridlines": "none",
              "legend": "bottom", "categories": CATS, "data": HLC}),
        (BR, {"chartType": "stock", "title": "chartareafill=none", "chartareafill": "none",
              "legend": "bottom", "categories": CATS, "data": HLC}),
    ]))

    # ---- Slide 8: Presets & per-series Set -------------------------------
    presets = ["minimal", "dark", "corporate"]
    charts8 = [(box, {"chartType": "stock", "preset": p, "title": f"preset={p}", "legend": "bottom",
                      "categories": CATS, "data": HLC})
               for box, p in zip([TL, TR, BL], presets)]
    charts8.append((BR, {"chartType": "stock", "title": "chart-series Set name+color", "legend": "bottom",
                         "categories": CATS, "data": HLC}))
    doc.batch(slide_items(8, "Presets & per-series Set", charts8))
    # chart-series Set on the 4th chart's three series (after the chart exists).
    doc.batch([
        {"command": "set", "path": "/slide[8]/chart[4]/series[1]", "props": {"name": "H", "color": "00AA00"}},
        {"command": "set", "path": "/slide[8]/chart[4]/series[2]", "props": {"name": "L", "color": "C00000"}},
        {"command": "set", "path": "/slide[8]/chart[4]/series[3]", "props": {"name": "C", "color": "4472C4"}},
    ])

    print("  built 8 slides")

print(f"Generated: {FILE}")
