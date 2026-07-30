#!/usr/bin/env python3
"""
Word Charts Showcase — every docx chart family, embedded inline in a document.

Generates: charts.docx

SDK twin of charts.sh (officecli CLI). Both produce an equivalent charts.docx.
This one drives the officecli Python SDK (`pip install officecli-sdk`): one
resident is started and every paragraph + chart is shipped over the named pipe
in a single `doc.batch(...)` round-trip. Each item is the same
`{"command","parent","type","props"}` dict you'd put in an `officecli batch` list.

In Word a chart is an INLINE DrawingML object anchored on a paragraph. It is
added with `add /body/p[N] --type chart ...` and given its data inline
(data=/series{N}=/categories=) — Word has no worksheet grid to reference, so
inline data is idiomatic. Once created the chart is addressed document-globally
as `/chart[M]` (NOT `/body/p[N]/chart[M]`) for get/set/query.

Layout: a Heading1 title + intro, then 14 demos. Each demo is one Heading2
paragraph followed by one empty body paragraph that hosts the inline chart.
Because paragraphs are appended in order, each host paragraph's 1-based index
is tracked in `p` so the chart's anchor path is explicit.

Every meaningful docx chart family is demonstrated at least once:
column/bar/line/pie/area/scatter/radar/doughnut/stock/combo plus extended cx
types funnel/treemap/waterfall; titles & title styling, legend, data labels,
colors & gradients (areafill), axis scaling/styling, display units, radar
style, rounded corners, markers, and transparency.

Usage:
  pip install officecli-sdk          # plus the `officecli` binary on PATH
  python3 charts.py
"""

import os
import sys

# --- locate the SDK: prefer an installed `officecli-sdk`, else the in-repo copy
try:
    import officecli  # pip install officecli-sdk
except ImportError:
    sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                    "..", "..", "sdk", "python"))
    import officecli

FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "charts.docx")


# Running 1-based paragraph index; every para()/heading()/host() appends one.
_p = 0


def para(text, **props):
    global _p
    _p += 1
    return {"command": "add", "parent": "/body", "type": "paragraph",
            "props": {"text": text, **props}}


def heading(text):
    return para(text, style="Heading2")


def host():
    """Empty body paragraph that will host the next inline chart."""
    return para("")


def chart(**props):
    """One `add chart` item anchored on the most recently added paragraph."""
    return {"command": "add", "parent": f"/body/p[{_p}]", "type": "chart",
            "props": props}


print(f"Building {FILE} ...")

with officecli.create(FILE, "--force") as doc:
    items = []

    # Title + intro
    items.append(para("Word Charts Showcase", style="Heading1", align="center"))
    items.append(para("Each chart below is an inline DrawingML object anchored "
                      "on its own paragraph. Charts are addressed "
                      "document-globally as /chart[N]."))

    # ----------------------------------------------------------------------
    # 1. Column — axis titles, axis scaling, gridlines, colors.
    # Features: chartType=column, data (inline Name:v;Name2:v), categories,
    #   colors, catTitle/axisTitle, axisMin/axisMax/axisNumFmt, gridlines, legend
    # ----------------------------------------------------------------------
    items.append(heading("1. Column — axis titles, scaling & gridlines"))
    items.append(host())
    items.append(chart(
        chartType="column",
        title="Quarterly Revenue by Region",
        data="East:120,135,148,162;West:110,118,130,145;South:95,108,115,128",
        categories="Q1,Q2,Q3,Q4",
        colors="4472C4,ED7D31,70AD47",
        catTitle="Quarter", axisTitle="Revenue (K)",
        axisMin="0", axisMax="200", axisNumFmt="#,##0",
        gridlines="D9D9D9:0.5:dot",
        legend="bottom",
        width="16cm", height="9cm"))

    # ----------------------------------------------------------------------
    # 2. Bar — gap width & data labels.
    # Features: chartType=bar, gapwidth, dataLabels=value, labelPos, labelfont
    # ----------------------------------------------------------------------
    items.append(heading("2. Bar — gap width & data labels"))
    items.append(host())
    items.append(chart(
        chartType="bar",
        title="Product Units Sold",
        data="Units:320,280,410,190,360",
        categories="Laptop,Phone,Tablet,Watch,Buds",
        colors="2E75B6",
        gapwidth="80",
        dataLabels="value", labelPos="outsideEnd",
        labelfont="9:333333:Calibri",
        legend="none",
        width="16cm", height="9cm"))

    # ----------------------------------------------------------------------
    # 3. Line — markers, smoothing, drop lines.
    # Features: chartType=line, marker (symbol:size), smooth, droplines, linewidth
    # ----------------------------------------------------------------------
    items.append(heading("3. Line — markers, smoothing & drop lines"))
    items.append(host())
    items.append(chart(
        chartType="line",
        title="Monthly Active Users",
        data="2023:120,180,210,250,280,310;2024:150,220,260,300,340,380",
        categories="Jan,Feb,Mar,Apr,May,Jun",
        colors="4472C4,ED7D31",
        marker="circle:6",
        smooth="true",
        droplines="808080:0.5",
        linewidth="2",
        legend="bottom",
        width="16cm", height="9cm"))

    # ----------------------------------------------------------------------
    # 4. Pie — percent labels, slice explosion, first-slice angle.
    # Features: chartType=pie, dataLabels=percent, explosion, firstSliceAngle
    # ----------------------------------------------------------------------
    items.append(heading("4. Pie — percent labels & slice explosion"))
    items.append(host())
    items.append(chart(
        chartType="pie",
        title="Market Share",
        data="Share:42,28,18,12",
        categories="Alpha,Beta,Gamma,Other",
        colors="4472C4,ED7D31,70AD47,FFC000",
        dataLabels="percent",
        explosion="8",
        firstSliceAngle="90",
        legend="right",
        width="14cm", height="9cm"))

    # ----------------------------------------------------------------------
    # 5. Area — gradient fill via areafill (docx-specific shortcut).
    # Features: chartType=area, areafill=c1-c2:angle (gradient on every series)
    # ----------------------------------------------------------------------
    items.append(heading("5. Area — gradient fill (areafill)"))
    items.append(host())
    items.append(chart(
        chartType="area",
        title="Cumulative Traffic",
        data="Visits:20,35,30,55,48,70,65",
        categories="Mon,Tue,Wed,Thu,Fri,Sat,Sun",
        areafill="4472C4-A5C8FF:90",
        gridlines="E0E0E0:0.5:solid",
        legend="none",
        width="16cm", height="9cm"))

    # ----------------------------------------------------------------------
    # 6. Scatter — smoothMarker style.
    # Features: chartType=scatter, scatterstyle=smoothMarker, marker, axis titles
    # ----------------------------------------------------------------------
    items.append(heading("6. Scatter — smoothMarker style"))
    items.append(host())
    items.append(chart(
        chartType="scatter",
        title="Load vs Response Time",
        series1="Latency:12,18,27,41,60,88",
        categories="10,20,40,80,160,320",
        scatterstyle="smoothMarker",
        marker="diamond:7:C00000",
        catTitle="Concurrent Users", axisTitle="ms",
        legend="none",
        width="16cm", height="9cm"))

    # ----------------------------------------------------------------------
    # 7. Radar — filled radar style (radarstyle docx shortcut).
    # Features: chartType=radar, radarstyle=filled, multi-series, transparency
    # ----------------------------------------------------------------------
    items.append(heading("7. Radar — filled style (radarstyle)"))
    items.append(host())
    items.append(chart(
        chartType="radar",
        title="Product Comparison",
        data="Model A:4,5,3,4,5;Model B:5,3,4,5,3",
        categories="Speed,Battery,Camera,Price,Display",
        radarstyle="filled",
        colors="4472C4,ED7D31",
        transparency="40",
        legend="bottom",
        width="14cm", height="10cm"))

    # ----------------------------------------------------------------------
    # 8. Doughnut — hole size & percent labels.
    # Features: chartType=doughnut, holeSize, dataLabels=percent, colors
    # ----------------------------------------------------------------------
    items.append(heading("8. Doughnut — hole size & percent labels"))
    items.append(host())
    items.append(chart(
        chartType="doughnut",
        title="Budget Allocation",
        data="Budget:35,25,20,20",
        categories="R&D,Sales,Ops,Admin",
        holeSize="55",
        dataLabels="percent",
        colors="4472C4,ED7D31,70AD47,FFC000",
        legend="right",
        width="14cm", height="9cm"))

    # ----------------------------------------------------------------------
    # 9. Stock — high/low/close (OHLC-style) series.
    # Features: chartType=stock, three ordered series (High, Low, Close), hilowlines
    # ----------------------------------------------------------------------
    items.append(heading("9. Stock — high / low / close series"))
    items.append(host())
    items.append(chart(
        chartType="stock",
        title="Share Price (5 Days)",
        series1="High:32,35,34,38,37",
        series2="Low:28,29,30,32,33",
        series3="Close:30,34,31,37,35",
        categories="Mon,Tue,Wed,Thu,Fri",
        hilowlines="true",
        legend="bottom",
        width="16cm", height="9cm"))

    # ----------------------------------------------------------------------
    # 10. Combo — column + line on a secondary axis.
    # Features: chartType=combo, combotypes=column,line, secondaryaxis=2
    # ----------------------------------------------------------------------
    items.append(heading("10. Combo — column + line on secondary axis"))
    items.append(host())
    items.append(chart(
        chartType="combo",
        title="Revenue vs Growth Rate",
        series1="Revenue:120,180,250,310,380",
        series2="Growth %:50,33,39,24,23",
        categories="2021,2022,2023,2024,2025",
        combotypes="column,line",
        secondaryaxis="2",
        colors="2E75B6,C00000",
        legend="bottom",
        width="16cm", height="9cm"))

    # ----------------------------------------------------------------------
    # 11. Column — display units & rounded corners + title styling.
    # Features: dispUnits=thousands, roundedcorners, chartFill,
    #   title.font/size/color/bold
    # ----------------------------------------------------------------------
    items.append(heading("11. Column — display units & rounded corners"))
    items.append(host())
    items.append(chart(
        chartType="column",
        title="Revenue (in Thousands)",
        data="Revenue:12000,18500,22000,31000,45000",
        categories="2021,2022,2023,2024,2025",
        colors="1F4E79",
        dispUnits="thousands",
        axisNumFmt="#,##0",
        roundedcorners="true",
        chartFill="F8F8F8",
        **{"title.font": "Georgia", "title.size": "15",
           "title.color": "1F4E79", "title.bold": "true"},
        legend="none",
        width="16cm", height="9cm"))

    # ----------------------------------------------------------------------
    # 12. Funnel — extended (cx) chart type.
    # Features: chartType=funnel (extended cx:chart), single-series stages
    # ----------------------------------------------------------------------
    items.append(heading("12. Funnel — extended (cx) chart"))
    items.append(host())
    items.append(chart(
        chartType="funnel",
        title="Sales Funnel",
        data="Stage:1000,720,430,210,95",
        categories="Visitors,Leads,MQL,SQL,Won",
        width="16cm", height="9cm"))

    # ----------------------------------------------------------------------
    # 13. Treemap — extended (cx) chart type.
    # Features: chartType=treemap (extended cx:chart), proportional area tiles
    # ----------------------------------------------------------------------
    items.append(heading("13. Treemap — extended (cx) chart"))
    items.append(host())
    items.append(chart(
        chartType="treemap",
        title="Storage by File Type",
        data="Size:420,310,180,90,45",
        categories="Video,Images,Docs,Audio,Other",
        width="16cm", height="9cm"))

    # ----------------------------------------------------------------------
    # 14. Waterfall — extended (cx) chart with increase/decrease/total colors.
    # Features: chartType=waterfall, increaseColor, decreaseColor, totalColor
    # ----------------------------------------------------------------------
    items.append(heading("14. Waterfall — increase / decrease / total colors"))
    items.append(host())
    items.append(chart(
        chartType="waterfall",
        title="Cash Flow",
        data="Cash:100,-30,50,-20,80",
        categories="Start,Q1,Q2,Q3,End",
        increaseColor="00AA00",
        decreaseColor="C00000",
        totalColor="4472C4",
        width="16cm", height="9cm"))

    doc.batch(items)
    doc.send({"command": "save"})
# context exit closes the resident, flushing the document to disk.

print(f"Generated: {FILE}")
print("  1 document, 14 inline charts (/chart[1]../chart[14])")
