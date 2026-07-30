#!/usr/bin/env python3
"""
Stock Charts Showcase — generates charts-stock.xlsx exercising the xlsx
`chart` element with chartType=stock: OHLC series (Open/High/Low/Close),
hi-low lines, up-down bars, axis/title/legend styling, data labels,
reference lines, borders, and number formats.

SDK twin of charts-stock.sh (officecli CLI). Both produce an equivalent
charts-stock.xlsx. This one drives the **officecli Python SDK**
(`pip install officecli-sdk`): one resident is started and every sheet and
chart is shipped over the named pipe in `doc.batch(...)` round-trips. Each
item is the same `{"command","parent","type","props"}` dict you'd put in an
`officecli batch` list.

3 chart sheets, 12 stock charts total:
  1-Stock Fundamentals — basic OHLC, gridlines+axisfont, hiLowLines, updownbars
  2-Stock Styling      — title styling, axis lines, axis range, plot/chart fill
  3-Stock Advanced     — data labels, reference line, borders, number format

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

FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "charts-stock.xlsx")


def add_sheet(name):
    """One `add sheet` item in batch-shape."""
    return {"command": "add", "parent": "/", "type": "sheet", "props": {"name": name}}


def chart(sheet, **props):
    """One `add chart` item in batch-shape, parented to a sheet."""
    return {"command": "add", "parent": f"/{sheet}", "type": "chart", "props": props}


print(f"Building {FILE} ...")

with officecli.create(FILE, "--force") as doc:

    # ======================================================================
    # Sheet: 1-Stock Fundamentals
    # ======================================================================
    print("\n--- 1-Stock Fundamentals ---")
    items = [add_sheet("1-Stock Fundamentals")]

    # ------------------------------------------------------------------
    # Chart 1: Basic OHLC stock chart
    # Features: chartType=stock, 4 series (Open/High/Low/Close), catTitle, axisTitle
    # ------------------------------------------------------------------
    items.append(chart("1-Stock Fundamentals",
        chartType="stock",
        title="ACME Corp Weekly OHLC",
        series1="Open:142,145,148,150,147,152",
        series2="High:148,151,155,156,153,158",
        series3="Low:139,142,145,147,144,149",
        series4="Close:145,148,150,147,152,155",
        categories="Week 1,Week 2,Week 3,Week 4,Week 5,Week 6",
        x="0", y="0", width="12", height="18",
        catTitle="Week", axisTitle="Price ($)",
        legend="bottom"))

    # ------------------------------------------------------------------
    # Chart 2: Stock with gridlines and axisfont
    # Features: gridlines, axisfont on stock chart
    # ------------------------------------------------------------------
    items.append(chart("1-Stock Fundamentals",
        chartType="stock",
        title="Tech Sector Daily",
        series1="Open:210,215,212,218,220",
        series2="High:218,222,219,225,228",
        series3="Low:207,211,208,214,216",
        series4="Close:215,212,218,220,225",
        categories="Mon,Tue,Wed,Thu,Fri",
        x="13", y="0", width="12", height="18",
        gridlines="D9D9D9:0.5",
        axisfont="9:666666",
        legend="bottom"))

    # ------------------------------------------------------------------
    # Chart 3: Stock with hiLowLines
    # Features: hiLowLines=true (vertical lines connecting high to low)
    # ------------------------------------------------------------------
    items.append(chart("1-Stock Fundamentals",
        chartType="stock",
        title="Energy Sector with Hi-Low Lines",
        series1="Open:78,80,82,79,83,85",
        series2="High:84,86,88,85,89,91",
        series3="Low:75,77,79,76,80,82",
        series4="Close:80,82,79,83,85,88",
        categories="Jan,Feb,Mar,Apr,May,Jun",
        x="0", y="19", width="12", height="18",
        hiLowLines="true",
        legend="bottom"))

    # ------------------------------------------------------------------
    # Chart 4: Stock with updownbars
    # Features: updownbars=gapWidth:upColor:downColor
    # ------------------------------------------------------------------
    items.append(chart("1-Stock Fundamentals",
        chartType="stock",
        title="Pharma Index with Up-Down Bars",
        series1="Open:55,58,56,60,62,59",
        series2="High:61,63,62,66,68,65",
        series3="Low:52,55,53,57,59,56",
        series4="Close:58,56,60,62,59,63",
        categories="Jan,Feb,Mar,Apr,May,Jun",
        x="13", y="19", width="12", height="18",
        updownbars="100:70AD47:C00000",
        legend="bottom"))

    doc.batch(items)

    # ======================================================================
    # Sheet: 2-Stock Styling
    # ======================================================================
    print("--- 2-Stock Styling ---")
    items = [add_sheet("2-Stock Styling")]

    # ------------------------------------------------------------------
    # Chart 1: Title styling, legend positioning
    # Features: title.font/size/color/bold, legend=right, legendfont
    # ------------------------------------------------------------------
    items.append(chart("2-Stock Styling",
        chartType="stock",
        title="Styled Stock Chart",
        series1="Open:165,170,168,172,175",
        series2="High:175,178,176,180,183",
        series3="Low:160,165,163,168,170",
        series4="Close:170,168,172,175,180",
        categories="Mon,Tue,Wed,Thu,Fri",
        x="0", y="0", width="12", height="18",
        **{"title.font": "Georgia", "title.size": "16",
           "title.color": "1F4E79", "title.bold": "true"},
        legend="right", legendfont="10:333333:Calibri"))

    # ------------------------------------------------------------------
    # Chart 2: Series effects, axisLine, catAxisLine
    # Features: axisLine, catAxisLine on stock chart
    # ------------------------------------------------------------------
    items.append(chart("2-Stock Styling",
        chartType="stock",
        title="Axis Line Styling",
        series1="Open:92,95,93,97,99",
        series2="High:99,102,100,104,106",
        series3="Low:88,91,89,93,95",
        series4="Close:95,93,97,99,103",
        categories="W1,W2,W3,W4,W5",
        x="13", y="0", width="12", height="18",
        hiLowLines="true",
        axisLine="333333:1.5", catAxisLine="333333:1.5",
        legend="bottom"))

    # ------------------------------------------------------------------
    # Chart 3: axisMin/Max, majorUnit
    # Features: axisMin/Max, majorUnit
    # ------------------------------------------------------------------
    items.append(chart("2-Stock Styling",
        chartType="stock",
        title="Custom Axis Range",
        series1="Open:120,125,122,128,130",
        series2="High:132,138,135,140,142",
        series3="Low:115,120,118,124,126",
        series4="Close:125,122,128,130,135",
        categories="Day 1,Day 2,Day 3,Day 4,Day 5",
        x="0", y="19", width="12", height="18",
        axisMin="110", axisMax="150",
        majorUnit="10",
        updownbars="100:70AD47:C00000",
        legend="bottom"))

    # ------------------------------------------------------------------
    # Chart 4: plotFill, chartFill, roundedCorners
    # Features: plotFill, chartFill, roundedCorners
    # ------------------------------------------------------------------
    items.append(chart("2-Stock Styling",
        chartType="stock",
        title="Styled Chart Area",
        series1="Open:48,50,52,49,53",
        series2="High:55,57,59,56,60",
        series3="Low:44,46,48,45,49",
        series4="Close:50,52,49,53,56",
        categories="Mon,Tue,Wed,Thu,Fri",
        x="13", y="19", width="12", height="18",
        plotFill="F0F4F8", chartFill="FAFAFA",
        roundedCorners="true",
        hiLowLines="true",
        legend="bottom"))

    doc.batch(items)

    # ======================================================================
    # Sheet: 3-Stock Advanced
    # ======================================================================
    print("--- 3-Stock Advanced ---")
    items = [add_sheet("3-Stock Advanced")]

    # ------------------------------------------------------------------
    # Chart 1: dataLabels, labelFont
    # Features: dataLabels, labelPos, labelFont on stock
    # ------------------------------------------------------------------
    items.append(chart("3-Stock Advanced",
        chartType="stock",
        title="Stock with Data Labels",
        series1="Open:185,190,188,192,195",
        series2="High:195,198,196,200,203",
        series3="Low:180,185,183,188,190",
        series4="Close:190,188,192,195,200",
        categories="W1,W2,W3,W4,W5",
        x="0", y="0", width="12", height="18",
        dataLabels="true", labelPos="top",
        labelFont="8:666666:false",
        legend="bottom"))

    # ------------------------------------------------------------------
    # Chart 2: referenceLine (support/resistance)
    # Features: referenceLine as support/resistance level
    # ------------------------------------------------------------------
    items.append(chart("3-Stock Advanced",
        chartType="stock",
        title="Support & Resistance",
        series1="Open:105,108,106,110,112,109",
        series2="High:112,115,113,117,119,116",
        series3="Low:101,104,102,106,108,105",
        series4="Close:108,106,110,112,109,113",
        categories="Jan,Feb,Mar,Apr,May,Jun",
        x="13", y="0", width="12", height="18",
        referenceLine="115:C00000:Resistance",
        hiLowLines="true",
        legend="bottom"))

    # ------------------------------------------------------------------
    # Chart 3: chartArea.border, plotArea.border
    # Features: chartArea.border, plotArea.border
    # ------------------------------------------------------------------
    items.append(chart("3-Stock Advanced",
        chartType="stock",
        title="Bordered Stock Chart",
        series1="Open:72,75,73,77,79",
        series2="High:79,82,80,84,86",
        series3="Low:68,71,69,73,75",
        series4="Close:75,73,77,79,83",
        categories="Mon,Tue,Wed,Thu,Fri",
        x="0", y="19", width="12", height="18",
        **{"chartArea.border": "333333:1.5",
           "plotArea.border": "999999:0.75"},
        updownbars="100:70AD47:C00000",
        legend="bottom"))

    # ------------------------------------------------------------------
    # Chart 4: dispUnits, axisNumFmt
    # Features: axisNumFmt (dollar format)
    # ------------------------------------------------------------------
    items.append(chart("3-Stock Advanced",
        chartType="stock",
        title="Large Cap Stock",
        series1="Open:2850,2900,2880,2920,2950",
        series2="High:2950,2980,2960,3000,3020",
        series3="Low:2800,2850,2830,2870,2900",
        series4="Close:2900,2880,2920,2950,2990",
        categories="Q1,Q2,Q3,Q4,Q5",
        x="13", y="19", width="12", height="18",
        axisNumFmt="$#,##0",
        hiLowLines="true",
        legend="bottom"))

    doc.batch(items)

    # Remove blank default Sheet1 (all data is inline)
    doc.send({"command": "remove", "path": "/Sheet1"})

    doc.send({"command": "save"})
# context exit closes the resident, flushing the workbook to disk.

print(f"\nDone! Generated: {FILE}")
print("  3 chart sheets, 12 stock charts total")
