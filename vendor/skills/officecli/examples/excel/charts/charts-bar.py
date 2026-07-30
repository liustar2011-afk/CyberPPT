#!/usr/bin/env python3
"""
Bar (Horizontal) Charts Showcase — bar, barStacked, barPercentStacked, and bar3d with all variations.

Generates: charts-bar.xlsx

Every horizontal bar chart feature officecli supports is demonstrated at least once:
gap width, overlap, data labels, axis scaling, gridlines, legend positioning,
reference lines, secondary axis, error bars, gradients, transparency, shadows,
manual layout, data table, 3D rotation, and conditional coloring.

8 sheets (Sheet1 data + 7 chart sheets), 28 charts total.

  1-Bar Fundamentals      4 charts — data input variants, colors, stacked, data shorthand
  2-Bar Variants          4 charts — barStacked, barPercentStacked, bar3d, cylinder
  3-Bar Styling           4 charts — title styling, shadow/outline, gradients, plot/chart fill
  4-Axis & Labels         4 charts — axis scale, log/reverse/dispUnits, label styling, per-point
  5-Legend & Layout       4 charts — legend positions, overlay, manual layout, secondary axis
  6-Advanced              4 charts — reference line, colorRule, glow/shadow, errBars/dataTable
  7-Axis Controls         4 charts — crosses/crossBetween, label rotation/skip, axisposition/serlines, markercolor

SDK twin of charts-bar.sh (officecli CLI). Both produce an equivalent
charts-bar.xlsx. This one drives the **officecli Python SDK**
(`pip install officecli-sdk`): one resident is started and every cell write and
chart is shipped over the named pipe via `doc.batch(...)` / `doc.send(...)`.
Each item is the same `{"command","parent"/"path","type","props"}` dict you'd
put in an `officecli batch` list.

Usage:
  pip install officecli-sdk          # plus the `officecli` binary on PATH
  python3 charts-bar.py
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

FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "charts-bar.xlsx")


def add_sheet(name):
    """One `add sheet` item in batch-shape."""
    return {"command": "add", "parent": "/", "type": "sheet", "props": {"name": name}}


def chart(sheet, **props):
    """One `add chart` item in batch-shape (props become --prop k=v)."""
    return {"command": "add", "parent": f"/{sheet}", "type": "chart", "props": props}


print(f"Building {FILE} ...")

with officecli.create(FILE, "--force") as doc:

    # ======================================================================
    # Source data — shared across all charts
    # ======================================================================
    print("--- Populating source data ---")
    data_items = []
    for j, h in enumerate(["Department", "Q1", "Q2", "Q3", "Q4"]):
        data_items.append({"command": "set", "path": f"/Sheet1/{'ABCDE'[j]}1",
                           "props": {"text": h, "bold": "true"}})

    depts = ["Engineering", "Marketing", "Sales", "Support", "Finance", "HR", "Legal", "Operations"]
    q1 =    [185, 120, 210, 95, 78, 62, 55, 140]
    q2 =    [195, 135, 225, 105, 82, 68, 58, 152]
    q3 =    [210, 142, 240, 112, 88, 72, 62, 165]
    q4 =    [228, 158, 260, 118, 92, 78, 68, 178]

    for i in range(8):
        r = i + 2
        for j, val in enumerate([depts[i], q1[i], q2[i], q3[i], q4[i]]):
            data_items.append({"command": "set", "path": f"/Sheet1/{'ABCDE'[j]}{r}",
                               "props": {"text": str(val)}})
    doc.batch(data_items)

    # ======================================================================
    # Sheet: 1-Bar Fundamentals
    # ======================================================================
    print("--- 1-Bar Fundamentals ---")
    items = [add_sheet("1-Bar Fundamentals")]

    # Chart 1: Basic bar chart with dataRange, axis titles, and gridlines
    # Features: chartType=bar, dataRange, catTitle, axisTitle, axisfont, gridlines
    items.append(chart("1-Bar Fundamentals",
        chartType="bar",
        title="Department Performance — Q1",
        dataRange="Sheet1!A1:B9",
        x="0", y="0", width="12", height="18",
        catTitle="Department", axisTitle="Score",
        axisfont="9:333333:Arial",
        gridlines="D9D9D9:0.5:dot"))

    # Chart 2: Inline series with custom colors, gap width, and data labels
    # Features: inline series, colors per category, gapwidth, dataLabels=outsideEnd
    items.append(chart("1-Bar Fundamentals",
        chartType="bar",
        title="Survey Results",
        series1="Satisfaction:85,72,91,68,78",
        categories="Product,Service,Delivery,Price,Overall",
        colors="4472C4,ED7D31,70AD47,FFC000,5B9BD5",
        x="13", y="0", width="12", height="18",
        gapwidth="80",
        dataLabels="outsideEnd"))

    # Chart 3: Stacked bar with overlap and series outline
    # Features: barStacked, overlap=0, series.outline (white separator)
    items.append(chart("1-Bar Fundamentals",
        chartType="barStacked",
        title="Quarterly Headcount by Dept",
        series1="Q1:30,18,25,12",
        series2="Q2:35,20,28,14",
        series3="Q3:38,22,30,16",
        categories="Engineering,Marketing,Sales,Support",
        colors="2E75B6,70AD47,FFC000",
        x="0", y="19", width="12", height="18",
        overlap="0",
        **{"series.outline": "FFFFFF-0.5"}))

    # Chart 4: data= shorthand with legend=bottom
    # Features: data= shorthand (inline multi-series), legend=bottom
    items.append(chart("1-Bar Fundamentals",
        chartType="bar",
        title="Training Hours by Team",
        data="Technical:45,38,52;Soft Skills:20,28,18;Compliance:12,15,10",
        categories="Engineering,Sales,Support",
        colors="4472C4,ED7D31,70AD47",
        x="13", y="19", width="12", height="18",
        legend="bottom"))
    doc.batch(items)

    # ======================================================================
    # Sheet: 2-Bar Variants
    # ======================================================================
    print("--- 2-Bar Variants ---")
    items = [add_sheet("2-Bar Variants")]

    # Chart 1: barStacked with tight gap width
    # Features: barStacked, gapwidth=50 (tight bars)
    items.append(chart("2-Bar Variants",
        chartType="barStacked",
        title="Budget Allocation",
        series1="Salaries:120,80,95,60",
        series2="Operations:45,35,40,25",
        series3="Marketing:30,50,20,15",
        categories="Engineering,Sales,Support,HR",
        colors="1F4E79,2E75B6,9DC3E6",
        x="0", y="0", width="12", height="18",
        gapwidth="50",
        legend="bottom"))

    # Chart 2: barPercentStacked with axis number format and reference line
    # Features: barPercentStacked, axisNumFmt=0%, referenceLine with label and dash
    items.append(chart("2-Bar Variants",
        chartType="barPercentStacked",
        title="Task Completion Ratio",
        series1="Done:75,60,90,45,80",
        series2="In Progress:15,25,5,30,12",
        series3="Blocked:10,15,5,25,8",
        categories="Backend,Frontend,QA,Design,DevOps",
        colors="70AD47,FFC000,C00000",
        x="13", y="0", width="12", height="18",
        axisNumFmt="0%",
        referenceLine="0.5:FF0000:Target:dash",
        legend="bottom"))

    # Chart 3: bar3d with perspective and style
    # Features: bar3d, view3d (rotX,rotY,perspective), style=3
    items.append(chart("2-Bar Variants",
        chartType="bar3d",
        title="3D Revenue by Region",
        series1="Revenue:340,280,310,195",
        categories="North,South,East,West",
        colors="4472C4,ED7D31,70AD47,FFC000",
        x="0", y="19", width="12", height="18",
        view3d="10,30,20",
        style="3",
        legend="right"))

    # Chart 4: bar3d with cylinder shape
    # Features: bar3d shape=cylinder, multi-series 3D bars
    items.append(chart("2-Bar Variants",
        chartType="bar3d",
        title="Cylinder — Project Milestones",
        series1="Completed:8,12,6,10,15",
        series2="Remaining:4,3,6,5,2",
        categories="Alpha,Beta,Gamma,Delta,Epsilon",
        colors="2E75B6,BDD7EE",
        x="13", y="19", width="12", height="18",
        shape="cylinder",
        gapwidth="60",
        legend="bottom"))
    doc.batch(items)

    # ======================================================================
    # Sheet: 3-Bar Styling
    # ======================================================================
    print("--- 3-Bar Styling ---")
    items = [add_sheet("3-Bar Styling")]

    # Chart 1: Title styling (font, size, color, bold)
    # Features: title.font, title.size, title.color, title.bold
    items.append(chart("3-Bar Styling",
        chartType="bar",
        title="Styled Title Demo",
        series1="Score:88,76,92,65,84",
        categories="Dept A,Dept B,Dept C,Dept D,Dept E",
        colors="4472C4",
        x="0", y="0", width="12", height="18",
        gapwidth="100",
        **{"title.font": "Georgia", "title.size": "16",
           "title.color": "1F4E79", "title.bold": "true"}))

    # Chart 2: Series shadow and outline effects
    # Features: series.shadow (color-blur-angle-dist-opacity), series.outline
    items.append(chart("3-Bar Styling",
        chartType="bar",
        title="Shadow & Outline",
        series1="2024:165,142,180,128",
        series2="2025:185,158,195,140",
        categories="Engineering,Marketing,Sales,Support",
        colors="2E75B6,ED7D31",
        x="13", y="0", width="12", height="18",
        legend="bottom",
        **{"series.shadow": "000000-4-315-2-30",
           "series.outline": "1F4E79-1"}))

    # Chart 3: Per-series gradients
    # Features: gradients (per-bar gradient fills, angle=0 for horizontal), labelFont (size:color:bold)
    items.append(chart("3-Bar Styling",
        chartType="bar",
        title="Gradient Bars",
        series1="Revenue:320,275,410,190,245",
        categories="North,South,East,West,Central",
        x="0", y="19", width="12", height="18",
        gradients="1F4E79-5B9BD5:0;C55A11-F4B183:0;548235-A9D18E:0;7F6000-FFD966:0;843C0B-DDA15E:0",
        dataLabels="outsideEnd",
        labelFont="9:333333:true"))

    # Chart 4: Plot fill gradient, chart fill, transparency, rounded corners
    # Features: plotFill gradient, chartFill, transparency, roundedCorners
    items.append(chart("3-Bar Styling",
        chartType="bar",
        title="Styled Background",
        dataRange="Sheet1!A1:C9",
        x="13", y="19", width="12", height="18",
        colors="5B9BD5,ED7D31",
        plotFill="F0F4F8-D6E4F0:90",
        chartFill="FFFFFF",
        transparency="20",
        roundedCorners="true",
        legend="right"))
    doc.batch(items)

    # ======================================================================
    # Sheet: 4-Axis & Labels
    # ======================================================================
    print("--- 4-Axis & Labels ---")
    items = [add_sheet("4-Axis & Labels")]

    # Chart 1: Custom axis min/max, majorUnit, and gridlines styling
    # Features: axisMin, axisMax, majorUnit, gridlines styling, minorGridlines, axisLine, catAxisLine
    items.append(chart("4-Axis & Labels",
        chartType="bar",
        title="Axis Scale (50–250)",
        dataRange="Sheet1!A1:B9",
        x="0", y="0", width="12", height="18",
        axisMin="50", axisMax="250", majorUnit="50",
        gridlines="D0D0D0:0.5:solid",
        minorGridlines="EEEEEE:0.3:dot",
        axisLine="C00000:1.5:solid",
        catAxisLine="2E75B6:1.5:solid"))

    # Chart 2: Log scale, axis reverse, and display units
    # Features: logBase=10, axisReverse=true, dispUnits=thousands
    items.append(chart("4-Axis & Labels",
        chartType="bar",
        title="Log Scale & Reverse",
        series1="Users:10,100,1000,5000,25000,100000",
        categories="Tier 1,Tier 2,Tier 3,Tier 4,Tier 5,Tier 6",
        colors="2E75B6",
        x="13", y="0", width="12", height="18",
        logBase="10",
        axisReverse="true",
        dispUnits="thousands",
        gridlines="E0E0E0:0.5:dash"))

    # Chart 3: Data labels with labelFont, numFmt, separator
    # Features: dataLabels, labelFont, dataLabels.numFmt, dataLabels.separator
    items.append(chart("4-Axis & Labels",
        chartType="bar",
        title="Labeled Metrics",
        series1="FY2025:148,92,215,178,125",
        categories="Revenue,Costs,Gross,EBITDA,Net Income",
        colors="4472C4",
        x="0", y="19", width="12", height="18",
        dataLabels="outsideEnd",
        labelFont="10:1F4E79:true",
        **{"dataLabels.numFmt": "#,##0",
           "dataLabels.separator": ": "}))

    # Chart 4: Per-point label delete/text and per-point color
    # Features: dataLabel{N}.delete, dataLabel{N}.text, point{N}.color
    items.append(chart("4-Axis & Labels",
        chartType="bar",
        title="Highlight Winner",
        series1="Score:72,85,68,95,78",
        categories="Team A,Team B,Team C,Team D,Team E",
        colors="9DC3E6",
        x="13", y="19", width="12", height="18",
        dataLabels="true", labelPos="outsideEnd",
        gapwidth="70",
        **{"dataLabel1.delete": "true", "dataLabel3.delete": "true",
           "dataLabel5.delete": "true",
           "dataLabel4.text": "Winner!",
           "point4.color": "C00000",
           "point2.color": "2E75B6"}))
    doc.batch(items)

    # ======================================================================
    # Sheet: 5-Legend & Layout
    # ======================================================================
    print("--- 5-Legend & Layout ---")
    items = [add_sheet("5-Legend & Layout")]

    # Chart 1: Legend positions (right)
    # Features: legend=right (4-series bar with legend on right)
    items.append(chart("5-Legend & Layout",
        chartType="bar",
        title="Legend: Right",
        dataRange="Sheet1!A1:E9",
        x="0", y="0", width="12", height="18",
        colors="4472C4,ED7D31,70AD47,FFC000",
        legend="right"))

    # Chart 2: Legend font styling and overlay
    # Features: legendfont (size:color:fontname), legend.overlay=true
    # legend.overlay precedes legendfont (as in the CLI twin) so c:overlay is
    # emitted before c:txPr — the schema order CT_Legend requires.
    items.append(chart("5-Legend & Layout", **{
        "chartType": "bar",
        "title": "Legend: Font & Overlay",
        "dataRange": "Sheet1!A1:E9",
        "x": "13", "y": "0", "width": "12", "height": "18",
        "colors": "1F4E79,2E75B6,5B9BD5,9DC3E6",
        "legend": "top",
        "legend.overlay": "true",
        "legendfont": "10:1F4E79:Calibri"}))

    # Chart 3: Manual layout — plotArea.x/y/w/h, title.x/y, legend.x/y/w/h
    # Features: plotArea.x/y/w/h, title.x/y, legend.x/y/w/h (manual layout)
    items.append(chart("5-Legend & Layout",
        chartType="bar",
        title="Manual Layout",
        dataRange="Sheet1!A1:C9",
        x="0", y="19", width="12", height="18",
        colors="2E75B6,70AD47",
        **{"plotArea.x": "0.25", "plotArea.y": "0.15",
           "plotArea.w": "0.70", "plotArea.h": "0.60",
           "title.x": "0.20", "title.y": "0.02",
           "legend.x": "0.25", "legend.y": "0.82",
           "legend.w": "0.50", "legend.h": "0.10",
           "title.font": "Arial", "title.size": "13",
           "title.bold": "true"}))

    # Chart 4: Secondary axis with chart/plot area borders
    # Features: secondaryAxis=2, chartArea.border, plotArea.border
    items.append(chart("5-Legend & Layout",
        chartType="bar",
        title="Dual Axis: Revenue vs Margin",
        series1="Revenue:340,280,410,195,310",
        series2="Margin %:22,18,28,15,25",
        categories="North,South,East,West,Central",
        colors="2E75B6,C00000",
        x="13", y="19", width="12", height="18",
        secondaryAxis="2",
        legend="bottom",
        **{"chartArea.border": "D0D0D0:1:solid",
           "plotArea.border": "E0E0E0:0.5:dot"}))
    doc.batch(items)

    # ======================================================================
    # Sheet: 6-Advanced
    # ======================================================================
    print("--- 6-Advanced ---")
    items = [add_sheet("6-Advanced")]

    # Chart 1: Reference line with label
    # Features: referenceLine (value:color:label:dash style)
    items.append(chart("6-Advanced",
        chartType="bar",
        title="vs Company Average",
        series1="Score:82,74,91,68,87,72",
        categories="Engineering,Marketing,Sales,Support,Finance,HR",
        colors="4472C4",
        x="0", y="0", width="12", height="18",
        referenceLine="79:FF0000:Average:dash",
        gapwidth="80",
        gridlines="E0E0E0:0.5:solid"))

    # Chart 2: Conditional coloring (colorRule)
    # Features: colorRule (threshold:belowColor:aboveColor), referenceLine=0 (zero baseline)
    items.append(chart("6-Advanced",
        chartType="bar",
        title="Profit/Loss by Division",
        series1="P&L:120,85,-45,160,-80,95,-20,140",
        categories="Div A,Div B,Div C,Div D,Div E,Div F,Div G,Div H",
        colors="2E75B6",
        x="13", y="0", width="12", height="18",
        colorRule="0:C00000:70AD47",
        referenceLine="0:888888:1:solid",
        dataLabels="outsideEnd",
        labelFont="9:333333:false"))

    # Chart 3: Title glow, title shadow, series shadow
    # Features: title.glow (color-radius-opacity), title.shadow, series.shadow on bar charts
    items.append(chart("6-Advanced",
        chartType="bar",
        title="Glow & Shadow Effects",
        series1="East:185,195,210,228",
        series2="West:140,152,165,178",
        categories="Q1,Q2,Q3,Q4",
        colors="4472C4,ED7D31",
        x="0", y="19", width="12", height="18",
        plotFill="F0F4F8", chartFill="FFFFFF",
        legend="bottom",
        **{"title.glow": "4472C4-8-60",
           "title.shadow": "000000-3-315-2-40",
           "title.font": "Calibri", "title.size": "16",
           "title.bold": "true", "title.color": "1F4E79",
           "series.shadow": "000000-3-315-1-30"}))

    # Chart 4: Error bars and data table
    # Features: errBars=percent:10, dataTable=true, legend=none
    items.append(chart("6-Advanced",
        chartType="bar",
        title="With Error Bars & Data Table",
        dataRange="Sheet1!A1:E9",
        x="13", y="19", width="12", height="18",
        colors="2E75B6,ED7D31,70AD47,FFC000",
        errBars="percent:10",
        dataTable="true",
        legend="none",
        plotFill="FAFAFA"))
    doc.batch(items)

    # ======================================================================
    # Sheet: 7-Axis Controls
    # ======================================================================
    print("--- 7-Axis Controls ---")
    items = [add_sheet("7-Axis Controls")]

    # Chart 1: crosses, crossBetween, valAxisVisible
    # Features: crosses=autoZero (value axis crosses cat axis at zero, the default),
    #   crossBetween=between (bars centred between tick marks vs midCat at the mark),
    #   valAxisVisible=true/false (show or hide the value axis entirely)
    items.append(chart("7-Axis Controls",
        chartType="bar",
        title="Axis Cross Controls",
        series1="Sales:120,80,-30,150",
        categories="Q1,Q2,Q3,Q4",
        x="0", y="0", width="12", height="18",
        crosses="autoZero",
        crossBetween="between",
        valAxisVisible="true"))

    # Chart 2: labelrotation, labeloffset, ticklabelskip
    # Features: labelrotation=45 (rotate category tick labels, -90..90 degrees),
    #   labeloffset=100 (category-axis label offset as % of default; 100=default),
    #   ticklabelskip=2 (draw tick labels every 2nd category — reduces crowding)
    items.append(chart("7-Axis Controls",
        chartType="column",
        title="Tick-label Rotation, Offset & Skip",
        series1="Units:45,30,20,55,40,25,60",
        categories="January,February,March,April,May,June,July",
        x="13", y="0", width="12", height="18",
        labelrotation="45",
        labeloffset="100",
        ticklabelskip="2"))

    # Chart 3: axisposition, serlines (stacked bar)
    # Features: axisposition=nextTo (tick labels next to the axis — alias for
    #   tickLabelPos; also accepts: high, low),
    #   serlines=true (series connector lines on stacked bar charts)
    items.append(chart("7-Axis Controls",
        chartType="barStacked",
        title="Stacked — axisposition + serlines",
        series1="Online:55,48,60,70",
        series2="Retail:30,40,35,25",
        categories="Q1,Q2,Q3,Q4",
        colors="4472C4,ED7D31",
        x="0", y="19", width="12", height="18",
        axisposition="nextTo",
        serlines="true"))

    # Chart 4: markercolor on line/scatter (chart-level fanout)
    # Features: markercolor=FF0000 (chart-level fan-out — applies the fill color
    #   to every series marker; per-series override via series[N] path)
    items.append(chart("7-Axis Controls",
        chartType="line",
        title="Line — markercolor",
        series1="Sales:120,145,132,160",
        series2="Costs:80,95,88,110",
        categories="Q1,Q2,Q3,Q4",
        colors="4472C4,ED7D31",
        x="13", y="19", width="12", height="18",
        marker="circle", markerSize="8",
        markercolor="FF0000",
        lineWidth="2"))
    doc.batch(items)

    doc.send({"command": "save"})
# context exit closes the resident, flushing the workbook to disk.

print(f"Generated: {FILE}")
print("  8 sheets (Sheet1 data + 7 chart sheets, 28 charts total)")
