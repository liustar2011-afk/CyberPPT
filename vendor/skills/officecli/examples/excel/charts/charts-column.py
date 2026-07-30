#!/usr/bin/env python3
"""
Column & Bar Charts Showcase — column, columnStacked, columnPercentStacked, and column3d with all variations.

Generates: charts-column.xlsx

SDK twin of charts-column.sh (officecli CLI). Both produce an equivalent
charts-column.xlsx. This one drives the **officecli Python SDK**
(`pip install officecli-sdk`): one resident is started, the shared source data
and every chart are shipped over the named pipe, and each sheet's charts are
applied in `doc.batch(...)` round-trips. Each item is the same
`{"command","parent","type","props"}` dict you'd put in an `officecli batch` list.

Every column chart feature officecli supports is demonstrated at least once:
gap width, overlap, bar shapes, axis scaling, gridlines, data labels,
legend positioning, reference lines, secondary axis, gradients,
transparency, shadows, manual layout, and 3D rotation.

8 sheets (Sheet1 data + 7 chart sheets), 28 charts total.

  1-Column Fundamentals   4 charts — data input variants, axis titles, inline/cell-range/data
  2-Column Variants       4 charts — columnStacked, columnPercentStacked, column3d
  3-Column Styling        4 charts — title styling, series effects, gradients, transparency
  4-Axis & Gridlines      4 charts — axis scaling, log scale, reverse, display units
  5-Labels & Legend       4 charts — data labels, custom labels, legend layout
  6-Effects & Advanced    4 charts — secondary axis, reference line, glow/shadow, colorRule
  7-Bar Shape & Gap       4 charts — gapwidth, overlap, 3D shapes (cylinder, cone, pyramid)

Usage:
  pip install officecli-sdk          # plus the `officecli` binary on PATH
  python3 charts-column.py
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

FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "charts-column.xlsx")


def add_sheet(name):
    """One `add sheet` item in batch-shape."""
    return {"command": "add", "parent": "/", "type": "sheet", "props": {"name": name}}


def cell(path, **props):
    """One `set` item writing a cell in batch-shape."""
    return {"command": "set", "path": path, "props": props}


def chart(sheet, **props):
    """One `add chart` item in batch-shape, anchored on a sheet."""
    return {"command": "add", "parent": sheet, "type": "chart", "props": props}


print(f"Building {FILE} ...")

with officecli.create(FILE, "--force") as doc:

    # ======================================================================
    # Source data — shared across all charts (Sheet1)
    # ======================================================================
    print("--- Populating source data ---")
    data_items = []
    for j, h in enumerate(["Month", "East", "South", "North", "West"]):
        data_items.append(cell(f"/Sheet1/{'ABCDE'[j]}1", text=h, bold="true"))

    months = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
    east =  [120, 135, 148, 162, 155, 178, 195, 210, 188, 172, 165, 198]
    south = [95,  108, 115, 128, 142, 155, 168, 175, 160, 148, 135, 158]
    north = [88,  92,  105, 118, 125, 138, 145, 152, 140, 130, 122, 142]
    west =  [110, 118, 130, 145, 138, 162, 175, 190, 170, 155, 148, 180]

    for i in range(12):
        r = i + 2
        for j, val in enumerate([months[i], east[i], south[i], north[i], west[i]]):
            data_items.append(cell(f"/Sheet1/{'ABCDE'[j]}{r}", text=str(val)))
    doc.batch(data_items)

    # ======================================================================
    # Sheet: 1-Column Fundamentals
    # ======================================================================
    print("--- 1-Column Fundamentals ---")
    s = "/1-Column Fundamentals"
    items = [add_sheet("1-Column Fundamentals")]

    # ------------------------------------------------------------------
    # Chart 1: Basic column with dataRange and axis titles
    # Features: chartType=column, dataRange, catTitle, axisTitle, axisfont,
    #   gridlines, colors
    # ------------------------------------------------------------------
    items.append(chart(s,
        chartType="column",
        title="Monthly Sales by Region",
        dataRange="Sheet1!A1:E13",
        x="0", y="0", width="12", height="18",
        catTitle="Month", axisTitle="Revenue",
        axisfont="9:58626E:Arial",
        gridlines="D9D9D9:0.5:dot",
        colors="4472C4,ED7D31,70AD47,FFC000"))

    # ------------------------------------------------------------------
    # Chart 2: Inline series with custom colors and gap width
    # Features: inline series (series1=Name:v1,v2,...), colors, gapwidth,
    #   legend=bottom
    # ------------------------------------------------------------------
    items.append(chart(s,
        chartType="column",
        title="Q1 Product Sales",
        series1="Laptops:320,280,350,310",
        series2="Phones:450,420,480,460",
        series3="Tablets:180,160,200,190",
        categories="Jan,Feb,Mar,Apr",
        colors="2E75B6,C00000,70AD47",
        x="13", y="0", width="12", height="18",
        gapwidth="80",
        legend="bottom"))

    # ------------------------------------------------------------------
    # Chart 3: Dotted syntax with cell ranges
    # Features: series.name/values/categories (cell range via dotted syntax),
    #   minorGridlines
    # ------------------------------------------------------------------
    items.append(chart(s,
        chartType="column",
        title="East vs South (Cell Range)",
        **{"series1.name": "East",
           "series1.values": "Sheet1!B2:B13",
           "series1.categories": "Sheet1!A2:A13",
           "series2.name": "South",
           "series2.values": "Sheet1!C2:C13",
           "series2.categories": "Sheet1!A2:A13"},
        x="0", y="19", width="12", height="18",
        colors="4472C4,ED7D31",
        gridlines="D9D9D9:0.5:dot",
        minorGridlines="EEEEEE:0.3:dot"))

    # ------------------------------------------------------------------
    # Chart 4: data= shorthand format
    # Features: data (inline shorthand Name:v1;Name2:v2), legend=right
    # ------------------------------------------------------------------
    items.append(chart(s,
        chartType="column",
        title="Weekly Output",
        data="Team A:85,92,78,95,88;Team B:70,80,85,90,75",
        categories="Mon,Tue,Wed,Thu,Fri",
        colors="0070C0,FF6600",
        x="13", y="19", width="12", height="18",
        legend="right"))
    doc.batch(items)

    # ======================================================================
    # Sheet: 2-Column Variants
    # ======================================================================
    print("--- 2-Column Variants ---")
    s = "/2-Column Variants"
    items = [add_sheet("2-Column Variants")]

    # ------------------------------------------------------------------
    # Chart 1: Stacked column with center data labels and series outline
    # Features: columnStacked, dataLabels=center, series.outline
    # ------------------------------------------------------------------
    items.append(chart(s,
        chartType="columnStacked",
        title="Stacked Sales by Region",
        dataRange="Sheet1!A1:E7",
        x="0", y="0", width="12", height="18",
        colors="4472C4,ED7D31,70AD47,FFC000",
        dataLabels="center",
        **{"series.outline": "FFFFFF-0.5"},
        legend="bottom"))

    # ------------------------------------------------------------------
    # Chart 2: 100% stacked column with axis number format
    # Features: columnPercentStacked, axisNumFmt=0%, legend=bottom
    # ------------------------------------------------------------------
    items.append(chart(s,
        chartType="columnPercentStacked",
        title="Regional Contribution %",
        dataRange="Sheet1!A1:E7",
        x="13", y="0", width="12", height="18",
        colors="1F4E79,2E75B6,9DC3E6,BDD7EE",
        axisNumFmt="0%",
        legend="bottom",
        gridlines="E0E0E0:0.5:solid"))

    # ------------------------------------------------------------------
    # Chart 3: 3D column with perspective and style
    # Features: column3d, view3d (rotX,rotY,perspective), style (preset 1-48)
    # ------------------------------------------------------------------
    items.append(chart(s,
        chartType="column3d",
        title="3D Regional Trends",
        dataRange="Sheet1!A1:E7",
        x="0", y="19", width="12", height="18",
        view3d="15,20,30",
        colors="4472C4,ED7D31,70AD47,FFC000",
        chartFill="F8F8F8",
        style="3"))

    # ------------------------------------------------------------------
    # Chart 4: 3D stacked column with gap depth
    # Features: column3d stacked, gapDepth=200 (3D depth spacing)
    # ------------------------------------------------------------------
    items.append(chart(s,
        chartType="column3d",
        title="3D Stacked with Gap Depth",
        series1="East:120,135,148,162,155,178",
        series2="South:95,108,115,128,142,155",
        series3="North:88,92,105,118,125,138",
        categories="Jan,Feb,Mar,Apr,May,Jun",
        x="13", y="19", width="12", height="18",
        view3d="15,20,30",
        gapDepth="200",
        colors="2E75B6,ED7D31,70AD47",
        legend="right"))
    doc.batch(items)

    # ======================================================================
    # Sheet: 3-Column Styling
    # ======================================================================
    print("--- 3-Column Styling ---")
    s = "/3-Column Styling"
    items = [add_sheet("3-Column Styling")]

    # ------------------------------------------------------------------
    # Chart 1: Title styling — font, size, color, bold
    # Features: title.font=Georgia, title.size=16, title.color=1F4E79,
    #   title.bold=true
    # ------------------------------------------------------------------
    items.append(chart(s,
        chartType="column",
        title="Styled Title Demo",
        dataRange="Sheet1!A1:E7",
        x="0", y="0", width="12", height="18",
        **{"title.font": "Georgia", "title.size": "16",
           "title.color": "1F4E79", "title.bold": "true"},
        colors="4472C4,ED7D31,70AD47,FFC000",
        legend="bottom"))

    # ------------------------------------------------------------------
    # Chart 2: Series shadow and outline effects
    # Features: series.shadow (color-blur-angle-dist-opacity),
    #   series.outline (color-width)
    # ------------------------------------------------------------------
    items.append(chart(s,
        chartType="column",
        title="Shadow & Outline Effects",
        series1="Revenue:320,280,350,310,340",
        series2="Cost:210,195,230,220,215",
        categories="Q1,Q2,Q3,Q4,Q5",
        x="13", y="0", width="12", height="18",
        colors="4472C4,C00000",
        **{"series.shadow": "000000-4-315-2-40",
           "series.outline": "FFFFFF-0.5"},
        gapwidth="100",
        legend="bottom"))

    # ------------------------------------------------------------------
    # Chart 3: Per-series gradient fills
    # Features: gradients (per-series gradient fills, start-end:angle)
    # ------------------------------------------------------------------
    items.append(chart(s,
        chartType="column",
        title="Gradient Columns",
        series1="East:120,135,148,162",
        series2="South:95,108,115,128",
        series3="North:88,92,105,118",
        categories="Q1,Q2,Q3,Q4",
        x="0", y="19", width="12", height="18",
        gradients="4472C4-BDD7EE:90;ED7D31-FBE5D6:90;70AD47-C5E0B4:90",
        legend="bottom"))

    # ------------------------------------------------------------------
    # Chart 4: Transparency + plotFill gradient + chartFill + roundedCorners
    # Features: transparency=30, plotFill gradient, chartFill, roundedCorners
    # ------------------------------------------------------------------
    items.append(chart(s,
        chartType="column",
        title="Transparent Columns on Gradient",
        dataRange="Sheet1!A1:E7",
        x="13", y="19", width="12", height="18",
        transparency="30",
        plotFill="F0F4F8-D6E4F0:90",
        chartFill="FFFFFF",
        colors="1F4E79,2E75B6,5B9BD5,9DC3E6",
        roundedCorners="true",
        legend="bottom"))
    doc.batch(items)

    # ======================================================================
    # Sheet: 4-Axis & Gridlines
    # ======================================================================
    print("--- 4-Axis & Gridlines ---")
    s = "/4-Axis & Gridlines"
    items = [add_sheet("4-Axis & Gridlines")]

    # ------------------------------------------------------------------
    # Chart 1: Custom axis scaling — min, max, majorUnit, minorUnit
    # Features: axisMin, axisMax, majorUnit, minorUnit,
    #   axisLine (value axis line styling), catAxisLine (category axis line)
    # ------------------------------------------------------------------
    items.append(chart(s,
        chartType="column",
        title="Custom Axis Scale (50-250)",
        dataRange="Sheet1!A1:E13",
        x="0", y="0", width="12", height="18",
        axisMin="50", axisMax="250", majorUnit="50",
        minorUnit="25",
        gridlines="D0D0D0:0.5:solid",
        minorGridlines="EEEEEE:0.3:dot",
        axisLine="C00000:1.5:solid",
        catAxisLine="2E75B6:1.5:solid",
        colors="4472C4,ED7D31,70AD47,FFC000"))

    # ------------------------------------------------------------------
    # Chart 2: Logarithmic scale with reversed axis
    # Features: logBase=10 (logarithmic scale), axisReverse=true
    # ------------------------------------------------------------------
    items.append(chart(s,
        chartType="column",
        title="Log Scale (Base 10)",
        series1="Growth:1,10,100,1000,5000",
        categories="Year 1,Year 2,Year 3,Year 4,Year 5",
        x="13", y="0", width="12", height="18",
        logBase="10",
        axisReverse="true",
        colors="C00000",
        axisTitle="Value (log)",
        catTitle="Year",
        gridlines="E0E0E0:0.5:dash"))

    # ------------------------------------------------------------------
    # Chart 3: Display units and axis number format
    # Features: dispUnits=thousands, axisNumFmt=#,##0,
    #   majorTickMark=outside, minorTickMark=inside
    # ------------------------------------------------------------------
    items.append(chart(s,
        chartType="column",
        title="Revenue (in Thousands)",
        series1="Revenue:12000,18500,22000,31000,45000,52000",
        series2="Cost:8000,11000,14000,19500,28000,33000",
        categories="2020,2021,2022,2023,2024,2025",
        x="0", y="19", width="12", height="18",
        dispUnits="thousands",
        axisNumFmt="#,##0",
        colors="2E75B6,C00000",
        catTitle="Year", axisTitle="Amount (K)",
        majorTickMark="outside", minorTickMark="inside",
        legend="bottom"))

    # ------------------------------------------------------------------
    # Chart 4: Hidden axes with data table
    # Features: gridlines=none, axisVisible=false, dataTable=true, legend=none
    # ------------------------------------------------------------------
    items.append(chart(s,
        chartType="column",
        title="Minimal Chart with Data Table",
        dataRange="Sheet1!A1:E7",
        x="13", y="19", width="12", height="18",
        gridlines="none",
        axisVisible="false",
        dataTable="true",
        legend="none",
        colors="4472C4,ED7D31,70AD47,FFC000"))
    doc.batch(items)

    # ======================================================================
    # Sheet: 5-Labels & Legend
    # ======================================================================
    print("--- 5-Labels & Legend ---")
    s = "/5-Labels & Legend"
    items = [add_sheet("5-Labels & Legend")]

    # ------------------------------------------------------------------
    # Chart 1: Data labels with number format and styled label font
    # Features: dataLabels=true, labelPos=outsideEnd, labelFont (size:color:bold),
    #   dataLabels.numFmt
    # ------------------------------------------------------------------
    items.append(chart(s,
        chartType="column",
        title="Sales with Labels",
        series1="Revenue:120,180,210,250,280",
        categories="Jan,Feb,Mar,Apr,May",
        x="0", y="0", width="12", height="18",
        colors="4472C4",
        dataLabels="true", labelPos="outsideEnd",
        labelFont="9:333333:true",
        **{"dataLabels.numFmt": "#,##0"}))

    # ------------------------------------------------------------------
    # Chart 2: Custom individual labels — delete some, highlight peak
    # Features: dataLabel{N}.delete, dataLabel{N}.text, point{N}.color
    # ------------------------------------------------------------------
    items.append(chart(s,
        chartType="column",
        title="Peak Highlight",
        series1="Sales:88,120,165,210,195,178",
        categories="Jan,Feb,Mar,Apr,May,Jun",
        x="13", y="0", width="12", height="18",
        colors="2E75B6",
        dataLabels="true", labelPos="outsideEnd",
        **{"dataLabel1.delete": "true", "dataLabel2.delete": "true",
           "dataLabel3.delete": "true",
           "point4.color": "C00000",
           "dataLabel4.text": "Peak!",
           "dataLabel5.delete": "true", "dataLabel6.delete": "true"}))

    # ------------------------------------------------------------------
    # Chart 3: Legend positioning and overlay with styled legend font
    # Features: legend=right, legend.overlay=true, legendfont (size:color:fontname),
    #   plotFill
    # ------------------------------------------------------------------
    items.append(chart(s,
        chartType="column",
        title="Legend Overlay on Chart",
        dataRange="Sheet1!A1:E7",
        x="0", y="19", width="12", height="18",
        colors="4472C4,ED7D31,70AD47,FFC000",
        legend="right",
        **{"legend.overlay": "true"},
        legendfont="10:333333:Calibri",
        plotFill="F5F5F5"))

    # ------------------------------------------------------------------
    # Chart 4: Manual layout — plotArea, title, and legend positioning
    # Features: plotArea.x/y/w/h, title.x/y, legend.x/y/w/h (manual layout)
    # ------------------------------------------------------------------
    items.append(chart(s,
        chartType="column",
        title="Manual Layout Control",
        dataRange="Sheet1!A1:E7",
        x="13", y="19", width="12", height="18",
        colors="2E75B6,ED7D31,70AD47,FFC000",
        **{"plotArea.x": "0.12", "plotArea.y": "0.18",
           "plotArea.w": "0.82", "plotArea.h": "0.55",
           "title.x": "0.25", "title.y": "0.02",
           "legend.x": "0.15", "legend.y": "0.82",
           "legend.w": "0.7", "legend.h": "0.12",
           "title.font": "Arial", "title.size": "13",
           "title.bold": "true"}))
    doc.batch(items)

    # ======================================================================
    # Sheet: 6-Effects & Advanced
    # ======================================================================
    print("--- 6-Effects & Advanced ---")
    s = "/6-Effects & Advanced"
    items = [add_sheet("6-Effects & Advanced")]

    # ------------------------------------------------------------------
    # Chart 1: Secondary axis — dual Y-axis
    # Features: secondaryAxis=2 (series 2 on right-hand axis)
    # ------------------------------------------------------------------
    items.append(chart(s,
        chartType="column",
        title="Revenue vs Growth Rate",
        series1="Revenue:120,180,250,310,380,420",
        series2="Growth %:50,33,39,24,23,11",
        categories="2020,2021,2022,2023,2024,2025",
        x="0", y="0", width="12", height="18",
        secondaryAxis="2",
        colors="2E75B6,C00000",
        catTitle="Year", axisTitle="Revenue",
        dataLabels="true", labelPos="outsideEnd",
        legend="bottom"))

    # ------------------------------------------------------------------
    # Chart 2: Reference line (target/threshold)
    # referenceLine format: value:color:width:dash
    # Features: referenceLine (horizontal target line)
    # ------------------------------------------------------------------
    items.append(chart(s,
        chartType="column",
        title="vs Target (150)",
        dataRange="Sheet1!A1:C13",
        x="13", y="0", width="12", height="18",
        colors="4472C4,70AD47",
        referenceLine="150:FF0000:1.5:dash",
        legend="bottom"))

    # ------------------------------------------------------------------
    # Chart 3: Title glow and shadow effects
    # Features: title.glow (color-radius-opacity), title.shadow,
    #   series.shadow on column charts
    # ------------------------------------------------------------------
    items.append(chart(s,
        chartType="column",
        title="Glow & Shadow Effects",
        series1="East:120,135,148,162,155,178",
        series2="West:110,118,130,145,138,162",
        categories="Jan,Feb,Mar,Apr,May,Jun",
        x="0", y="19", width="12", height="18",
        colors="4472C4,ED7D31",
        **{"title.glow": "4472C4-8-60",
           "title.shadow": "000000-3-315-2-40",
           "title.font": "Calibri", "title.size": "16",
           "title.bold": "true", "title.color": "1F4E79",
           "series.shadow": "000000-3-315-1-30"},
        plotFill="F0F4F8", chartFill="FFFFFF"))

    # ------------------------------------------------------------------
    # Chart 4: Conditional coloring with chart/plot borders
    # colorRule format: threshold:belowColor:aboveColor
    # Features: colorRule (threshold-based conditional coloring),
    #   chartArea.border, plotArea.border
    # ------------------------------------------------------------------
    items.append(chart(s,
        chartType="column",
        title="Profit: Conditional Colors",
        series1="Profit:80,120,-30,160,-50,200,140,-20,180,90",
        categories="Jan,Feb,Mar,Apr,May,Jun,Jul,Aug,Sep,Oct",
        x="13", y="19", width="12", height="18",
        colors="2E75B6",
        colorRule="0:C00000:70AD47",
        referenceLine="0:888888:1:solid",
        **{"chartArea.border": "D0D0D0:1:solid",
           "plotArea.border": "E0E0E0:0.5:dot"},
        dataLabels="true", labelPos="outsideEnd",
        labelFont="8:666666:false"))
    doc.batch(items)

    # ======================================================================
    # Sheet: 7-Bar Shape & Gap
    # ======================================================================
    print("--- 7-Bar Shape & Gap ---")
    s = "/7-Bar Shape & Gap"
    items = [add_sheet("7-Bar Shape & Gap")]

    # ------------------------------------------------------------------
    # Chart 1: Narrow gap width (bars close together)
    # Features: gapwidth=30 (narrow gaps between column groups)
    # ------------------------------------------------------------------
    items.append(chart(s,
        chartType="column",
        title="Narrow Gap (30%)",
        dataRange="Sheet1!A1:E7",
        x="0", y="0", width="12", height="18",
        gapwidth="30",
        colors="4472C4,ED7D31,70AD47,FFC000",
        legend="bottom"))

    # ------------------------------------------------------------------
    # Chart 2: Wide gap with negative overlap (separated bars within group)
    # Features: gapwidth=200 (wide gap), overlap=-50 (negative = bars separated)
    # ------------------------------------------------------------------
    items.append(chart(s,
        chartType="column",
        title="Wide Gap + Negative Overlap",
        dataRange="Sheet1!A1:E7",
        x="13", y="0", width="12", height="18",
        gapwidth="200",
        overlap="-50",
        colors="2E75B6,ED7D31,70AD47,FFC000",
        legend="bottom"))

    # ------------------------------------------------------------------
    # Chart 3: 3D column with cylinder shape
    # Features: shape=cylinder (3D column bar shape)
    # ------------------------------------------------------------------
    items.append(chart(s,
        chartType="column3d",
        title="Cylinder Shape",
        series1="East:120,135,148,162,155,178",
        series2="South:95,108,115,128,142,155",
        categories="Jan,Feb,Mar,Apr,May,Jun",
        x="0", y="19", width="12", height="18",
        shape="cylinder",
        view3d="15,20,30",
        colors="4472C4,ED7D31",
        legend="bottom"))

    # ------------------------------------------------------------------
    # Chart 4: 3D column with cone/pyramid shapes
    # Features: shape=cone (3D column bar shape — also supports pyramid)
    # ------------------------------------------------------------------
    items.append(chart(s,
        chartType="column3d",
        title="Cone Shape",
        series1="North:88,92,105,118,125,138",
        series2="West:110,118,130,145,138,162",
        categories="Jan,Feb,Mar,Apr,May,Jun",
        x="13", y="19", width="12", height="18",
        shape="cone",
        view3d="15,20,30",
        colors="70AD47,FFC000",
        legend="bottom"))
    doc.batch(items)

    doc.send({"command": "save"})
# context exit closes the resident, flushing the workbook to disk.

print(f"Generated: {FILE}")
print("  8 sheets (Sheet1 data + 7 chart sheets, 28 charts total)")
