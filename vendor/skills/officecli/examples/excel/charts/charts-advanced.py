#!/usr/bin/env python3
"""
Advanced Charts Showcase — generates charts-advanced.xlsx exercising the
xlsx `chart` element's advanced chart types: scatter, bubble, combo, radar,
and stock (OHLC). 12 charts across 3 sheets.

SDK twin of charts-advanced.sh (officecli CLI). Both produce an equivalent
charts-advanced.xlsx. This one drives the **officecli Python SDK**
(`pip install officecli-sdk`): one resident is started and every sheet and
chart is shipped over the named pipe in `doc.batch(...)` round-trips. Each
item is the same `{"command","parent","type","props"}` dict you'd put in an
`officecli batch` list.

3 sheets, by chart family:
  1-Scatter & Bubble — scatter(markers/line, smooth+trendline, per-series
                       markers) + bubble(market size)
  2-Combo & Radar    — combo(comboSplit, secondaryAxis, combotypes) +
                       radar(marker style)
  3-Stock & Radar    — stock(daily OHLC, weekly OHLC) + radar(filled) +
                       bubble(single series)

Usage:
  pip install officecli-sdk          # plus the `officecli` binary on PATH
  python3 charts-advanced.py
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

FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "charts-advanced.xlsx")


def add_sheet(name):
    """One `add sheet` item in batch-shape."""
    return {"command": "add", "parent": "/", "type": "sheet", "props": {"name": name}}


def chart(sheet, **props):
    """One `add chart` item in batch-shape (parent = the sheet)."""
    return {"command": "add", "parent": f"/{sheet}", "type": "chart", "props": props}


print(f"Building {FILE} ...")

with officecli.create(FILE, "--force") as doc:

    # ======================================================================
    # Sheet: 1-Scatter & Bubble
    # ======================================================================
    print("--- 1-Scatter & Bubble ---")
    items = [add_sheet("1-Scatter & Bubble")]

    # ------------------------------------------------------------------
    # Chart 1: Scatter with markers — circle markers, line connecting points
    # Features: chartType=scatter, categories as X values, marker=circle,
    #   markerSize, lineWidth, legend=bottom
    # ------------------------------------------------------------------
    items.append(chart(
        "1-Scatter & Bubble",
        chartType="scatter",
        title="Scatter: Markers & Line",
        categories="1,2,3,4,5,6",
        series1="SeriesA:10,25,15,40,30,50",
        series2="SeriesB:5,18,22,35,28,42",
        colors="4472C4,ED7D31",
        x="0", y="0", width="12", height="18",
        marker="circle", markerSize="8",
        lineWidth="1.5",
        legend="bottom",
    ))

    # ------------------------------------------------------------------
    # Chart 2: Scatter with smooth curve and trendline (reference line)
    # Features: smooth=true (smooth curve), marker=diamond,
    #   referenceLine (trendline overlay), axisTitle, catTitle
    # ------------------------------------------------------------------
    items.append(chart(
        "1-Scatter & Bubble",
        chartType="scatter",
        title="Scatter: Smooth + Trendline",
        categories="1,2,3,4,5,6,7,8",
        series1="Growth:3,7,12,20,28,35,40,45",
        colors="70AD47",
        x="13", y="0", width="12", height="18",
        smooth="true",
        marker="diamond", markerSize="7",
        referenceLine="25:FF0000:Target:dash",
        axisTitle="Value", catTitle="Period",
    ))

    # ------------------------------------------------------------------
    # Chart 3: Scatter with varied marker styles per series
    # Features: per-series marker style (series{N}.marker), gridlines styling
    # ------------------------------------------------------------------
    items.append(chart(
        "1-Scatter & Bubble",
        chartType="scatter",
        title="Scatter: Marker Styles",
        categories="10,20,30,40,50",
        series1="Squares:8,22,18,35,30",
        series2="Triangles:15,10,28,20,42",
        series3="Stars:5,30,12,45,25",
        colors="4472C4,ED7D31,70AD47",
        x="0", y="19", width="12", height="18",
        **{"series1.marker": "square",
           "series2.marker": "triangle",
           "series3.marker": "star"},
        markerSize="9",
        lineWidth="1",
        gridlines="D9D9D9:0.5:dot",
    ))

    # ------------------------------------------------------------------
    # Chart 4: Bubble chart with size data
    # Features: chartType=bubble, categories as X, series as Y values,
    #   bubble sizes default to Y values, bubbleScale to control sizing
    # ------------------------------------------------------------------
    items.append(chart(
        "1-Scatter & Bubble",
        chartType="bubble",
        title="Bubble: Market Size",
        categories="10,25,40,60,80",
        series1="ProductA:30,50,20,70,45",
        series2="ProductB:15,35,55,40,60",
        colors="4472C4,ED7D31",
        x="13", y="19", width="12", height="18",
        bubbleScale="80",
        legend="right",
    ))

    doc.batch(items)

    # ======================================================================
    # Sheet: 2-Combo & Radar
    # ======================================================================
    print("--- 2-Combo & Radar ---")
    items = [add_sheet("2-Combo & Radar")]

    # ------------------------------------------------------------------
    # Chart 1: Combo chart — bar+line with comboSplit
    # Features: chartType=combo, comboSplit=2 (first 2 series as bars,
    #   remaining as lines), categories as X labels
    # ------------------------------------------------------------------
    items.append(chart(
        "2-Combo & Radar",
        chartType="combo",
        title="Combo: Sales (Bar) + Growth % (Line)",
        categories="Jan,Feb,Mar,Apr,May,Jun",
        series1="Revenue:120,145,132,168,155,180",
        series2="Expenses:80,92,85,98,90,105",
        series3="Growth:8,12,6,15,10,16",
        colors="4472C4,ED7D31,70AD47",
        x="0", y="0", width="12", height="18",
        comboSplit="2",
        legend="bottom",
        axisTitle="Amount", catTitle="Month",
    ))

    # ------------------------------------------------------------------
    # Chart 2: Combo with secondary axis
    # Features: comboSplit=1, secondaryAxis=2 (series 2 on right Y-axis)
    # ------------------------------------------------------------------
    items.append(chart(
        "2-Combo & Radar",
        chartType="combo",
        title="Combo: Volume (Bar) + Price (Line, 2nd Axis)",
        categories="Q1,Q2,Q3,Q4",
        series1="Volume:1200,1450,1320,1680",
        series2="AvgPrice:45,52,48,58",
        colors="5B9BD5,FF0000",
        x="13", y="0", width="12", height="18",
        comboSplit="1",
        secondaryAxis="2",
        legend="bottom",
    ))

    # ------------------------------------------------------------------
    # Chart 3: Combo with combotypes — per-series type control
    # Features: combotypes (per-series type: column, column, line, area)
    # ------------------------------------------------------------------
    items.append(chart(
        "2-Combo & Radar",
        chartType="combo",
        title="Combo: Mixed Types (combotypes)",
        categories="A,B,C,D,E",
        series1="Bars:30,45,28,52,40",
        series2="MoreBars:20,30,22,38,28",
        series3="Lines:12,18,15,22,16",
        series4="Area:8,12,10,15,11",
        colors="4472C4,5B9BD5,ED7D31,70AD47",
        x="0", y="19", width="12", height="18",
        combotypes="column,column,line,area",
        legend="bottom",
    ))

    # ------------------------------------------------------------------
    # Chart 4: Radar (spider) chart with multiple series
    # Features: chartType=radar, categories as spoke labels,
    #   multiple series, radarStyle=marker
    # ------------------------------------------------------------------
    items.append(chart(
        "2-Combo & Radar",
        chartType="radar",
        title="Radar: Skills Comparison",
        categories="Speed,Strength,Stamina,Agility,Accuracy",
        series1="AthleteA:80,65,90,75,85",
        series2="AthleteB:70,85,60,90,70",
        series3="AthleteC:90,70,75,65,80",
        colors="4472C4,ED7D31,70AD47",
        x="13", y="19", width="12", height="18",
        radarStyle="marker",
        legend="bottom",
    ))

    doc.batch(items)

    # ======================================================================
    # Sheet: 3-Stock & Radar
    # ======================================================================
    print("--- 3-Stock & Radar ---")
    items = [add_sheet("3-Stock & Radar")]

    # ------------------------------------------------------------------
    # Chart 1: Stock (OHLC) chart — Open-High-Low-Close
    # Features: chartType=stock, 4 series (Open/High/Low/Close),
    #   categories as date labels, catTitle, axisTitle
    # ------------------------------------------------------------------
    items.append(chart(
        "3-Stock & Radar",
        chartType="stock",
        title="Stock: OHLC Daily Prices",
        categories="Mon,Tue,Wed,Thu,Fri",
        series1="Open:145,148,150,147,152",
        series2="High:152,155,157,153,160",
        series3="Low:143,146,148,144,150",
        series4="Close:148,150,147,152,158",
        x="0", y="0", width="14", height="18",
        legend="bottom",
        catTitle="Day", axisTitle="Price",
    ))

    # ------------------------------------------------------------------
    # Chart 2: Stock chart — weekly OHLC with date categories
    # Features: stock chart with 6 weeks of OHLC, gridlines styling
    # ------------------------------------------------------------------
    items.append(chart(
        "3-Stock & Radar",
        chartType="stock",
        title="Stock: Weekly OHLC (6 Weeks)",
        categories="W1,W2,W3,W4,W5,W6",
        series1="Open:100,104,102,108,105,110",
        series2="High:106,110,108,115,112,118",
        series3="Low:98,101,100,105,103,107",
        series4="Close:104,102,108,105,110,115",
        x="15", y="0", width="14", height="18",
        gridlines="E0E0E0:0.75",
        legend="bottom",
    ))

    # ------------------------------------------------------------------
    # Chart 3: Radar — filled style (spider web)
    # Features: radarStyle=filled, transparency (fill alpha), multiple series
    # ------------------------------------------------------------------
    items.append(chart(
        "3-Stock & Radar",
        chartType="radar",
        title="Radar: Product Ratings (Filled)",
        categories="Quality,Price,Design,Support,Delivery",
        series1="BrandX:85,70,90,75,80",
        series2="BrandY:70,90,65,85,75",
        colors="4472C4,70AD47",
        x="0", y="19", width="14", height="18",
        radarStyle="filled",
        transparency="40",
        legend="bottom",
    ))

    # ------------------------------------------------------------------
    # Chart 4: Bubble — single series with explicit large differences in size
    # Features: bubble with single series, bubbleScale=100, legend=none,
    #   axisTitle and catTitle labels
    # ------------------------------------------------------------------
    items.append(chart(
        "3-Stock & Radar",
        chartType="bubble",
        title="Bubble: Regional Opportunity",
        categories="5,15,30,50,70,90",
        series1="Regions:20,45,30,80,55,65",
        colors="4472C4",
        x="15", y="19", width="14", height="18",
        bubbleScale="100",
        legend="none",
        axisTitle="Revenue", catTitle="Market Size",
    ))

    doc.batch(items)

    doc.send({"command": "save"})

print(f"Generated: {FILE}")
print("  3 sheets (1-Scatter & Bubble, 2-Combo & Radar, 3-Stock & Radar)")
print("  12 charts total: scatter(3), bubble(2), combo(3), radar(2), stock(2)")
