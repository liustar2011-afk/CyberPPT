#!/usr/bin/env python3
"""
Waterfall Charts Showcase — waterfall chart type with all variations.

Generates: charts-waterfall.xlsx

4 sheets, 16 charts total:
  1-Waterfall Fundamentals  4 charts — basic P&L, budget bridge, quarterly cash flow, title styling
  2-Waterfall Styling       4 charts — title shadow, series shadow/fill, gridlines/axis font, borders
  3-Waterfall Labels & Axis 4 charts — label numFmt, axis range, legend styling, manual plot layout
  4-Waterfall Advanced      4 charts — reference line, axis line styling, glow/shadow, large dataset

SDK twin of charts-waterfall.sh (officecli CLI). Both produce an equivalent
charts-waterfall.xlsx. This one drives the **officecli Python SDK**
(`pip install officecli-sdk`): one resident is started and every chart is
shipped over the named pipe via `doc.batch(...)`. Each item is the same
`{"command","parent","type","props"}` dict you'd put in an `officecli batch`
list. The batch defaults to stop_on_error=False, so a not-yet-consumed
("unsupported_property") prop warns but still creates the element — matching
the CLI twin's forward-compat tolerance.

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

FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "charts-waterfall.xlsx")


def add_sheet(name):
    """One `add sheet` item in batch-shape."""
    return {"command": "add", "parent": "/", "type": "sheet", "props": {"name": name}}


def chart(sheet, **props):
    """One `add chart` item in batch-shape (props become --prop k=v)."""
    return {"command": "add", "parent": f"/{sheet}", "type": "chart", "props": props}


print(f"Building {FILE} ...")

with officecli.create(FILE, "--force") as doc:

    # ======================================================================
    # Sheet: 1-Waterfall Fundamentals
    # ======================================================================
    print("--- 1-Waterfall Fundamentals ---")
    items = [add_sheet("1-Waterfall Fundamentals")]

    # Chart 1: Basic P&L waterfall with increase/decrease/total colors
    # Features: chartType=waterfall, data= name:value pairs, increaseColor,
    #   decreaseColor, totalColor, dataLabels
    items.append(chart("1-Waterfall Fundamentals",
        chartType="waterfall",
        title="P&L Summary",
        data="Start:1000,Revenue:500,Costs:-300,Tax:-100,Net:1100",
        increaseColor="70AD47",
        decreaseColor="FF0000",
        totalColor="4472C4",
        x="0", y="0", width="12", height="18",
        dataLabels="true"))

    # Chart 2: Budget waterfall with blue/red/amber theme and legend
    # Features: waterfall legend=bottom, alternative color palette (blue/red/amber)
    items.append(chart("1-Waterfall Fundamentals",
        chartType="waterfall",
        title="Budget vs Actual",
        data="Budget:5000,Sales:2000,Marketing:-800,Ops:-600,Net:5600",
        increaseColor="2E75B6",
        decreaseColor="C00000",
        totalColor="FFC000",
        x="13", y="0", width="12", height="18",
        legend="bottom"))

    # Chart 3: Quarterly cash flow bridge with more data points
    # Features: waterfall with 10 categories (extended data points),
    #   quarterly granularity
    items.append(chart("1-Waterfall Fundamentals",
        chartType="waterfall",
        title="Quarterly Cash Flow",
        data="Opening:3000,Q1 Sales:1200,Q1 Costs:-500,Q2 Sales:1500,Q2 Costs:-700,Q3 Sales:800,Q3 Costs:-400,Q4 Sales:2000,Q4 Costs:-900,Closing:6000",
        increaseColor="70AD47",
        decreaseColor="ED7D31",
        totalColor="4472C4",
        x="0", y="19", width="12", height="18",
        dataLabels="true"))

    # Chart 4: Waterfall with custom title styling
    # Features: title.font, title.size, title.color, title.bold
    items.append(chart("1-Waterfall Fundamentals",
        chartType="waterfall",
        title="Revenue Bridge",
        data="Base:2500,New Clients:800,Upsell:400,Churn:-600,Total:3100",
        increaseColor="548235",
        decreaseColor="BF0000",
        totalColor="2F5496",
        x="13", y="19", width="12", height="18",
        **{"title.font": "Georgia", "title.size": "16",
           "title.color": "1F4E79", "title.bold": "true"}))
    doc.batch(items)

    # ======================================================================
    # Sheet: 2-Waterfall Styling
    # ======================================================================
    print("--- 2-Waterfall Styling ---")
    items = [add_sheet("2-Waterfall Styling")]

    # Chart 1: Title styling with font, size, color, bold, and shadow
    # Features: title.font, title.size, title.color, title.bold, title.shadow
    items.append(chart("2-Waterfall Styling",
        chartType="waterfall",
        title="Styled Title Demo",
        data="Start:800,Income:300,Expenses:-200,Net:900",
        increaseColor="70AD47",
        decreaseColor="FF0000",
        totalColor="4472C4",
        x="0", y="0", width="12", height="18",
        **{"title.font": "Trebuchet MS", "title.size": "18",
           "title.color": "833C0B", "title.bold": "true",
           "title.shadow": "000000-3-315-2-30"}))

    # Chart 2: Series shadow, plotFill, chartFill, roundedCorners
    # Features: series.shadow, plotFill, chartFill, roundedCorners
    items.append(chart("2-Waterfall Styling",
        chartType="waterfall",
        title="Shadow & Fill Effects",
        data="Baseline:1500,Growth:600,Decline:-400,Result:1700",
        increaseColor="2E75B6",
        decreaseColor="C00000",
        totalColor="FFC000",
        x="13", y="0", width="12", height="18",
        plotFill="F0F0F0",
        chartFill="FAFAFA",
        roundedCorners="true",
        **{"series.shadow": "000000-4-315-2-30"}))

    # Chart 3: Gridlines styling and axis font
    # Features: gridlineColor, axisfont (size:color:font)
    items.append(chart("2-Waterfall Styling",
        chartType="waterfall",
        title="Gridlines & Axis Font",
        data="Open:2000,Add:750,Remove:-350,Close:2400",
        increaseColor="70AD47",
        decreaseColor="FF0000",
        totalColor="4472C4",
        x="0", y="19", width="12", height="18",
        gridlineColor="CCCCCC",
        axisfont="10:333333:Calibri"))

    # Chart 4: Chart area border and plot area border
    # Features: chartArea.border (color-width), plotArea.border
    items.append(chart("2-Waterfall Styling",
        chartType="waterfall",
        title="Border Styling",
        data="Initial:1200,Gain:500,Loss:-300,Final:1400",
        increaseColor="548235",
        decreaseColor="BF0000",
        totalColor="2F5496",
        x="13", y="19", width="12", height="18",
        **{"chartArea.border": "4472C4:2",
           "plotArea.border": "A5A5A5:1"}))
    doc.batch(items)

    # ======================================================================
    # Sheet: 3-Waterfall Labels & Axis
    # ======================================================================
    print("--- 3-Waterfall Labels & Axis ---")
    items = [add_sheet("3-Waterfall Labels & Axis")]

    # Chart 1: Data labels with labelFont and numFmt
    # Features: dataLabels, labelFont (size:color:bold), dataLabels.numFmt
    items.append(chart("3-Waterfall Labels & Axis",
        chartType="waterfall",
        title="Labels with NumFmt",
        data="Start:4500,Revenue:1800,COGS:-1200,SGA:-600,Net:4500",
        increaseColor="70AD47",
        decreaseColor="FF0000",
        totalColor="4472C4",
        x="0", y="0", width="12", height="18",
        dataLabels="true",
        labelFont="10:333333:true",
        **{"dataLabels.numFmt": "#,##0"}))

    # Chart 2: Axis min/max and majorUnit
    # Features: axisMin, axisMax, majorUnit
    items.append(chart("3-Waterfall Labels & Axis",
        chartType="waterfall",
        title="Custom Axis Range",
        data="Base:2000,Up:800,Down:-500,Total:2300",
        increaseColor="2E75B6",
        decreaseColor="C00000",
        totalColor="FFC000",
        x="13", y="0", width="12", height="18",
        axisMin="0", axisMax="3500", majorUnit="500"))

    # Chart 3: Legend positioning and legendfont
    # Features: legend=right, legendfont (size:color:font)
    items.append(chart("3-Waterfall Labels & Axis",
        chartType="waterfall",
        title="Legend Styling",
        data="Begin:3000,Earned:1100,Spent:-700,End:3400",
        increaseColor="70AD47",
        decreaseColor="FF0000",
        totalColor="4472C4",
        x="0", y="19", width="12", height="18",
        legend="right",
        legendfont="10:1F4E79:Helvetica"))

    # Chart 4: Manual layout with plotArea.x/y/w/h
    # Features: plotArea.x/y/w/h (manual layout, fractional coordinates)
    items.append(chart("3-Waterfall Labels & Axis",
        chartType="waterfall",
        title="Manual Plot Layout",
        data="Start:1800,Add:600,Sub:-400,End:2000",
        increaseColor="548235",
        decreaseColor="BF0000",
        totalColor="2F5496",
        x="13", y="19", width="12", height="18",
        **{"plotArea.x": "0.15", "plotArea.y": "0.15",
           "plotArea.w": "0.75", "plotArea.h": "0.70"}))
    doc.batch(items)

    # ======================================================================
    # Sheet: 4-Waterfall Advanced
    # ======================================================================
    print("--- 4-Waterfall Advanced ---")
    items = [add_sheet("4-Waterfall Advanced")]

    # Chart 1: Waterfall with referenceLine
    # Features: referenceLine (value:label-color-dash-width)
    items.append(chart("4-Waterfall Advanced",
        chartType="waterfall",
        title="Reference Line",
        data="Start:2000,Revenue:900,Refunds:-300,Fees:-200,Net:2400",
        increaseColor="70AD47",
        decreaseColor="FF0000",
        totalColor="4472C4",
        x="0", y="0", width="12", height="18",
        referenceLine="2000:FF0000:Target:dash"))

    # Chart 2: Axis line and category axis line styling
    # Features: axisLine (color-width), catAxisLine
    items.append(chart("4-Waterfall Advanced",
        chartType="waterfall",
        title="Axis Line Styling",
        data="Open:1500,Deposit:700,Withdraw:-400,Close:1800",
        increaseColor="2E75B6",
        decreaseColor="C00000",
        totalColor="FFC000",
        x="13", y="0", width="12", height="18",
        axisLine="333333:2",
        catAxisLine="333333:2"))

    # Chart 3: Title glow and shadow effects
    # Features: title.glow (color-radius), title.shadow
    items.append(chart("4-Waterfall Advanced",
        chartType="waterfall",
        title="Glow & Shadow Effects",
        data="Base:3000,Inflow:1200,Outflow:-800,Balance:3400",
        increaseColor="70AD47",
        decreaseColor="FF0000",
        totalColor="4472C4",
        x="0", y="19", width="12", height="18",
        **{"title.glow": "4472C4-8",
           "title.shadow": "000000-3-315-2-30",
           "title.size": "16", "title.bold": "true"}))

    # Chart 4: Large dataset waterfall (8+ categories)
    # Features: large dataset (12 categories), axisfont with smaller size
    #   for readability
    items.append(chart("4-Waterfall Advanced",
        chartType="waterfall",
        title="Annual P&L Detail",
        data="Revenue:8500,COGS:-3400,Gross Profit:5100,R&D:-1200,Sales:-900,Marketing:-600,G&A:-500,EBITDA:1900,Depreciation:-300,Interest:-200,Tax:-350,Net Income:1050",
        increaseColor="548235",
        decreaseColor="C00000",
        totalColor="2F5496",
        x="13", y="19", width="12", height="18",
        dataLabels="true",
        axisfont="8:333333:Calibri"))
    doc.batch(items)

    # Remove blank default Sheet1 (all data is inline)
    doc.send({"command": "remove", "path": "/Sheet1"})

    doc.send({"command": "save"})
# context exit closes the resident, flushing the workbook to disk.

print(f"Generated: {FILE}")
print("  4 sheets (16 charts total)")
print("  Sheet 1: Waterfall Fundamentals (4 charts)")
print("  Sheet 2: Waterfall Styling (4 charts)")
print("  Sheet 3: Waterfall Labels & Axis (4 charts)")
print("  Sheet 4: Waterfall Advanced (4 charts)")
