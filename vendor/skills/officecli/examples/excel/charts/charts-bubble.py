#!/usr/bin/env python3
"""
Bubble Charts Showcase — bubble scale, size representation, and styling.

Generates: charts-bubble.xlsx — 4 chart sheets, 14 charts total
exercising chartType=bubble (X;Y;Size data), bubbleScale, sizeRepresents,
dataLabels, ARGB transparency, gridlines/axis styling, plot/chart fills,
series shadow, secondaryAxis, referenceLine, log scale, trendline,
shownegbubbles, and series1.bubbleSize range references.

SDK twin of charts-bubble.sh (officecli CLI). Both produce an equivalent
charts-bubble.xlsx. This one drives the **officecli Python SDK**
(`pip install officecli-sdk`): one resident is started and every sheet,
cell and chart is shipped over the named pipe — grouped per sheet into
`doc.batch(...)` round-trips. Each item is the same
`{"command","parent","type","props"}` dict you'd put in an `officecli
batch` list.

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

FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "charts-bubble.xlsx")


def sheet(name):
    """One `add sheet` item in batch-shape."""
    return {"command": "add", "parent": "/", "type": "sheet", "props": {"name": name}}


def chart(parent, **props):
    """One `add chart` item in batch-shape."""
    return {"command": "add", "parent": parent, "type": "chart", "props": props}


def cell(parent, ref, value):
    """One `add cell` item in batch-shape (matches the CLI's
    `add ... --type cell --prop ref=.. --prop value=..`)."""
    return {"command": "add", "parent": parent, "type": "cell",
            "props": {"ref": ref, "value": value}}


print(f"Building {FILE} ...")

with officecli.create(FILE, "--force") as doc:

    # ======================================================================
    # Sheet: 1-Bubble Fundamentals
    # ======================================================================
    print("\n--- 1-Bubble Fundamentals ---")
    S1 = "/1-Bubble Fundamentals"
    items = [
        sheet("1-Bubble Fundamentals"),

        # ------------------------------------------------------------------
        # Chart 1: Basic bubble chart with 2 series
        # Features: chartType=bubble, X;Y;Size triplets, catTitle, axisTitle
        # ------------------------------------------------------------------
        chart(S1,
              chartType="bubble",
              title="Market Analysis",
              series1="Enterprise:80,45,60",
              series2="Consumer:50,35,70",
              colors="4472C4,ED7D31",
              x="0", y="0", width="12", height="18",
              catTitle="Market Size", axisTitle="Growth Rate",
              legend="bottom"),

        # ------------------------------------------------------------------
        # Chart 2: bubbleScale=100 with dataLabels
        # Features: bubbleScale=100, dataLabels with center positioning
        # ------------------------------------------------------------------
        chart(S1,
              chartType="bubble",
              title="Product Portfolio",
              series1="Products:90,50,70,40",
              colors="2E75B6",
              x="13", y="0", width="12", height="18",
              bubbleScale="100",
              dataLabels="true", labelPos="center",
              labelFont="9:FFFFFF:true",
              legend="bottom"),

        # ------------------------------------------------------------------
        # Chart 3: bubbleScale=50 (smaller bubbles)
        # Features: bubbleScale=50
        # ------------------------------------------------------------------
        chart(S1,
              chartType="bubble",
              title="Small Bubbles (Scale 50)",
              series1="Tech:60,80,45",
              series2="Finance:55,70,35",
              colors="70AD47,FFC000",
              x="0", y="19", width="12", height="18",
              bubbleScale="50",
              legend="bottom"),

        # ------------------------------------------------------------------
        # Chart 4: sizeRepresents=width
        # Features: sizeRepresents=width (bubble diameter proportional to value)
        # ------------------------------------------------------------------
        chart(S1,
              chartType="bubble",
              title="Size by Width",
              series1="Regions:70,40,55,85",
              colors="5B9BD5",
              x="13", y="19", width="12", height="18",
              sizeRepresents="width",
              bubbleScale="100",
              legend="bottom"),
    ]
    doc.batch(items)

    # ======================================================================
    # Sheet: 2-Bubble Styling
    # ======================================================================
    print("--- 2-Bubble Styling ---")
    S2 = "/2-Bubble Styling"
    items = [
        sheet("2-Bubble Styling"),

        # ------------------------------------------------------------------
        # Chart 1: Title styling, legend positioning
        # Features: title.font/size/color/bold, legend=right, legendfont
        # ------------------------------------------------------------------
        chart(S2,
              chartType="bubble",
              title="Styled Bubble Chart",
              series1="SegmentA:65,50,80",
              series2="SegmentB:45,60,40",
              colors="1F4E79,C55A11",
              x="0", y="0", width="12", height="18",
              **{"title.font": "Georgia", "title.size": "16",
                 "title.color": "1F4E79", "title.bold": "true"},
              legend="right", legendfont="10:333333:Calibri"),

        # ------------------------------------------------------------------
        # Chart 2: Series colors, transparency
        # Features: ARGB colors with alpha (80=50% transparency)
        # ------------------------------------------------------------------
        chart(S2,
              chartType="bubble",
              title="Transparent Overlapping Bubbles",
              series1="GroupX:75,60,90,50",
              series2="GroupY:65,55,80,45",
              colors="804472C4,80ED7D31",
              x="13", y="0", width="12", height="18",
              bubbleScale="120",
              legend="bottom"),

        # ------------------------------------------------------------------
        # Chart 3: gridlines, axisfont, axisLine
        # Features: gridlines, axisfont, axisLine
        # ------------------------------------------------------------------
        chart(S2,
              chartType="bubble",
              title="Grid & Axis Styling",
              series1="Div1:55,70,45",
              series2="Div2:60,40,75",
              colors="2E75B6,548235",
              x="0", y="19", width="12", height="18",
              gridlines="D9D9D9:0.5",
              axisfont="9:666666",
              axisLine="333333:1",
              legend="bottom"),

        # ------------------------------------------------------------------
        # Chart 4: plotFill, chartFill, series.shadow
        # Features: plotFill, chartFill, series.shadow
        # ------------------------------------------------------------------
        chart(S2,
              chartType="bubble",
              title="Shadow & Fill Effects",
              series1="Portfolio:80,55,65,45",
              colors="4472C4",
              x="13", y="19", width="12", height="18",
              plotFill="F0F4F8", chartFill="FAFAFA",
              **{"series.shadow": "000000-4-315-2-30"},
              legend="bottom"),
    ]
    doc.batch(items)

    # ======================================================================
    # Sheet: 3-Bubble Advanced
    # ======================================================================
    print("--- 3-Bubble Advanced ---")
    S3 = "/3-Bubble Advanced"
    items = [
        sheet("3-Bubble Advanced"),

        # ------------------------------------------------------------------
        # Chart 1: secondaryAxis
        # Features: secondaryAxis on bubble chart
        # ------------------------------------------------------------------
        chart(S3,
              chartType="bubble",
              title="Dual-Axis Bubble",
              series1="Domestic:70,85,60,90",
              series2="International:45,55,80,65",
              categories="1,2,3,4",
              colors="4472C4,ED7D31",
              x="0", y="0", width="12", height="18",
              secondaryAxis="2",
              legend="bottom"),

        # ------------------------------------------------------------------
        # Chart 2: referenceLine
        # Features: referenceLine on bubble chart
        # ------------------------------------------------------------------
        chart(S3,
              chartType="bubble",
              title="Growth Threshold",
              series1="Products:60,80,45,55",
              categories="1,2,3,4",
              colors="70AD47",
              x="13", y="0", width="12", height="18",
              referenceLine="50:C00000:Target",
              bubbleScale="80",
              legend="bottom"),

        # ------------------------------------------------------------------
        # Chart 3: axisMin/Max, logBase
        # Features: axisMin/Max, logBase=10 (logarithmic scale)
        # ------------------------------------------------------------------
        chart(S3,
              chartType="bubble",
              title="Log Scale Analysis",
              series1="Markets:5,15,50,120",
              categories="1,2,3,4",
              colors="2E75B6",
              x="0", y="19", width="12", height="18",
              axisMin="1", axisMax="200",
              logBase="10",
              bubbleScale="80",
              legend="bottom"),

        # ------------------------------------------------------------------
        # Chart 4: chartArea.border, plotArea.border, trendline
        # Features: chartArea.border, plotArea.border, trendline=linear
        # ------------------------------------------------------------------
        chart(S3,
              chartType="bubble",
              title="Trend & Borders",
              series1="Investments:20,55,95,140,180",
              categories="1,2,3,4,5",
              colors="4472C4",
              x="13", y="19", width="12", height="18",
              **{"chartArea.border": "333333:1.5",
                 "plotArea.border": "999999:0.75"},
              trendline="linear",
              legend="bottom"),
    ]
    doc.batch(items)

    # ======================================================================
    # Sheet: 4-Bubble Series Data
    # ======================================================================
    print("--- 4-Bubble Series Data ---")
    S4 = "/4-Bubble Series Data"
    items = [
        sheet("4-Bubble Series Data"),

        # ------------------------------------------------------------------
        # Chart 1: shownegbubbles — render bubbles for negative size values
        # Features: shownegbubbles=true (render bubbles whose size value is
        #   negative by reflecting them — Excel hides them by default)
        # ------------------------------------------------------------------
        chart(S4,
              chartType="bubble",
              title="shownegbubbles — negative sizes visible",
              series1="Data:60,30,90",
              series2="Neg:40,50,70",
              colors="4472C4,C00000",
              x="0", y="0", width="12", height="18",
              shownegbubbles="true",
              bubbleScale="80",
              legend="bottom"),

        # ------------------------------------------------------------------
        # Chart 2: series1.bubbleSize (range ref) — sizes from worksheet cells
        #
        # Populate some size data first, then reference it. Demonstrates the
        # bubbleSize + bubbleSizeRef round-trip: Excel re-computes when the
        # source cells change; bubbleSizeRef is emitted on Get alongside the
        # cached literal bubbleSize values.
        # ------------------------------------------------------------------
        cell(S4, "A1", "10"),
        cell(S4, "A2", "25"),
        cell(S4, "A3", "40"),
        chart(S4,
              chartType="bubble",
              title="series1.bubbleSize — range ref",
              series1="Sizes:80,45,60",
              **{"series1.bubbleSize": "4-Bubble Series Data!$A$1:$A$3"},
              colors="70AD47",
              x="13", y="0", width="12", height="18",
              bubbleScale="100", legend="bottom"),
    ]
    doc.batch(items)

    # Remove blank default Sheet1 (all data is inline)
    doc.send({"command": "remove", "path": "/Sheet1"})

    doc.send({"command": "save"})
# context exit closes the resident, flushing the workbook to disk.

print(f"\nDone! Generated: {FILE}")
print("  4 chart sheets, 14 charts total")
