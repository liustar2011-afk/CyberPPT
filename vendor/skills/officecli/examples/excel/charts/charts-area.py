#!/usr/bin/env python3
"""
Area Charts Showcase — area, areaStacked, areaPercentStacked, and area3d with all variations.

Generates: charts-area.xlsx

Every area chart feature officecli supports is demonstrated at least once:
area fills, gradients, transparency, stacking, axis scaling, gridlines,
data labels, legend positioning, reference lines, secondary axis,
shadows, manual layout, and 3D rotation.

5 sheets, 20 charts total.

  1-Area Fundamentals     4 charts — data input variants, transparency, area fills, gradients
  2-Area Variants         4 charts — areaStacked, areaPercentStacked, area3d
  3-Area Styling          4 charts — title styling, shadows, gridlines, chart/plot fills
  4-Labels & Legend       4 charts — data labels, per-point colors, legend, manual layout
  5-Advanced              4 charts — secondary axis, reference line, axis scaling, effects

SDK twin of charts-area.sh (officecli CLI). Both produce an equivalent
charts-area.xlsx. This one drives the **officecli Python SDK**
(`pip install officecli-sdk`): one resident is started, the source data and
every chart is shipped over the named pipe in `doc.batch(...)` round-trips.
Each item is the same `{"command","parent","type","props"}` dict you'd put in
an `officecli batch` list.

Usage:
  pip install officecli-sdk          # plus the `officecli` binary on PATH
  python3 charts-area.py
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

FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "charts-area.xlsx")


def add_sheet(name):
    """One `add sheet` item in batch-shape."""
    return {"command": "add", "parent": "/", "type": "sheet", "props": {"name": name}}


def chart(parent, **props):
    """One `add chart` item in batch-shape."""
    return {"command": "add", "parent": parent, "type": "chart", "props": props}


print(f"Building {FILE} ...")

with officecli.create(FILE, "--force") as doc:

    # ==========================================================================
    # Source data — shared across all charts
    # ==========================================================================
    print("\n--- Populating source data ---")

    data_cmds = []
    for j, h in enumerate(["Month", "Organic", "Paid", "Social", "Referral"]):
        data_cmds.append({"command": "set", "path": f"/Sheet1/{'ABCDE'[j]}1",
                          "props": {"text": h, "bold": "true"}})

    months   = ["Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"]
    organic  = [4200, 4800, 5100, 5600, 6200, 6800, 7500, 8100, 7600, 7200, 6900, 7800]
    paid     = [3100, 3500, 3800, 4200, 4800, 5200, 5800, 6300, 5900, 5500, 5100, 5700]
    social   = [1800, 2100, 2400, 2800, 3200, 3600, 4000, 4300, 3900, 3500, 3200, 3800]
    referral = [1200, 1400, 1500, 1700, 1900, 2100, 2300, 2500, 2300, 2100, 1900, 2200]

    for i in range(12):
        r = i + 2
        for j, val in enumerate([months[i], organic[i], paid[i], social[i], referral[i]]):
            data_cmds.append({"command": "set", "path": f"/Sheet1/{'ABCDE'[j]}{r}",
                              "props": {"text": str(val)}})

    doc.batch(data_cmds)

    # ==========================================================================
    # Sheet: 1-Area Fundamentals
    # ==========================================================================
    print("\n--- 1-Area Fundamentals ---")

    items = [add_sheet("1-Area Fundamentals")]

    # ----------------------------------------------------------------------
    # Chart 1: Basic area chart with dataRange, axis titles, and custom colors
    # Features: chartType=area, dataRange, colors, catTitle, axisTitle, gridlines
    # ----------------------------------------------------------------------
    items.append(chart("/1-Area Fundamentals",
        chartType="area",
        title="Website Traffic Overview",
        dataRange="Sheet1!A1:E13",
        colors="4472C4,ED7D31,70AD47,FFC000",
        x="0", y="0", width="12", height="18",
        catTitle="Month", axisTitle="Visitors",
        gridlines="D9D9D9:0.5:dot"))

    # ----------------------------------------------------------------------
    # Chart 2: Inline series with transparency
    # Features: inline series, transparency (0-100), legend=bottom
    # ----------------------------------------------------------------------
    items.append(chart("/1-Area Fundamentals",
        chartType="area",
        title="Quarterly Revenue Streams",
        series1="Subscriptions:120,180,210,250",
        series2="One-time:90,140,160,200",
        series3="Services:60,85,110,145",
        categories="Q1,Q2,Q3,Q4",
        colors="2E75B6,70AD47,FFC000",
        x="13", y="0", width="12", height="18",
        transparency="40",
        legend="bottom"))

    # ----------------------------------------------------------------------
    # Chart 3: Area with areafill gradient
    # Features: areafill (gradient from-to:angle), legend=none, single series
    # ----------------------------------------------------------------------
    items.append(chart("/1-Area Fundamentals",
        chartType="area",
        title="Monthly Active Users",
        series1="Users:3200,3800,4500,5100,5800,6400",
        categories="Jul,Aug,Sep,Oct,Nov,Dec",
        x="0", y="19", width="12", height="18",
        areafill="4472C4-BDD7EE:90",
        legend="none"))

    # ----------------------------------------------------------------------
    # Chart 4: Per-series gradient fills
    # Features: gradients (per-series gradient fills from-to:angle;...),
    #   legendfont (size:color:font)
    # ----------------------------------------------------------------------
    items.append(chart("/1-Area Fundamentals",
        chartType="area",
        title="Revenue by Channel",
        series1="Direct:45,52,61,70",
        series2="Partner:30,38,42,55",
        categories="Q1,Q2,Q3,Q4",
        x="13", y="19", width="12", height="18",
        gradients="4472C4-BDD7EE:90;ED7D31-FBE5D6:90",
        legend="right", legendfont="10:333333:Calibri"))

    doc.batch(items)

    # ==========================================================================
    # Sheet: 2-Area Variants
    # ==========================================================================
    print("\n--- 2-Area Variants ---")

    items = [add_sheet("2-Area Variants")]

    # ----------------------------------------------------------------------
    # Chart 1: Stacked area with plotFill and rounded corners
    # Features: chartType=areaStacked, plotFill (solid), roundedCorners
    # ----------------------------------------------------------------------
    items.append(chart("/2-Area Variants",
        chartType="areaStacked",
        title="Cumulative Traffic Sources",
        dataRange="Sheet1!A1:E13",
        colors="4472C4,ED7D31,70AD47,FFC000",
        x="0", y="0", width="12", height="18",
        plotFill="F5F5F5",
        roundedCorners="true",
        legend="bottom"))

    # ----------------------------------------------------------------------
    # Chart 2: 100% stacked area with axis number format and axis line
    # Features: chartType=areaPercentStacked, axisNumFmt, axisLine
    # ----------------------------------------------------------------------
    items.append(chart("/2-Area Variants",
        chartType="areaPercentStacked",
        title="Traffic Share by Channel",
        dataRange="Sheet1!A1:E13",
        colors="2E75B6,C55A11,548235,BF8F00",
        x="13", y="0", width="12", height="18",
        axisNumFmt="0%",
        axisLine="333333:1:solid",
        legend="bottom"))

    # ----------------------------------------------------------------------
    # Chart 3: 3D area with perspective rotation
    # Features: chartType=area3d, view3d (rotX,rotY,perspective)
    # ----------------------------------------------------------------------
    items.append(chart("/2-Area Variants",
        chartType="area3d",
        title="3D Regional Sales",
        series1="East:120,135,148,162,155,178",
        series2="West:95,108,115,128,142,155",
        series3="Central:88,92,105,118,125,138",
        categories="Jan,Feb,Mar,Apr,May,Jun",
        colors="4472C4,ED7D31,70AD47",
        x="0", y="19", width="12", height="18",
        view3d="20,25,15",
        legend="right"))

    # ----------------------------------------------------------------------
    # Chart 4: 3D stacked area
    # Features: area3d stacked appearance, multiple series, gridlines
    # ----------------------------------------------------------------------
    items.append(chart("/2-Area Variants",
        chartType="area3d",
        title="3D Stacked Inventory",
        series1="Warehouse A:500,480,520,550,530,560",
        series2="Warehouse B:320,350,340,380,400,410",
        series3="Warehouse C:180,200,210,230,250,240",
        categories="Jan,Feb,Mar,Apr,May,Jun",
        colors="1F4E79,2E75B6,9DC3E6",
        x="13", y="19", width="12", height="18",
        view3d="15,20,20",
        gridlines="D9D9D9:0.5:dot"))

    doc.batch(items)

    # ==========================================================================
    # Sheet: 3-Area Styling
    # ==========================================================================
    print("\n--- 3-Area Styling ---")

    items = [add_sheet("3-Area Styling")]

    # ----------------------------------------------------------------------
    # Chart 1: Title styling (font, size, color, bold, shadow)
    # Features: title.font, title.size, title.color, title.bold, title.shadow
    # ----------------------------------------------------------------------
    items.append(chart("/3-Area Styling",
        chartType="area",
        title="Styled Title Demo",
        series1="Revenue:80,120,160,200,240,280",
        categories="Jan,Feb,Mar,Apr,May,Jun",
        colors="4472C4",
        x="0", y="0", width="12", height="18",
        **{"title.font": "Georgia", "title.size": "16",
           "title.color": "1F4E79", "title.bold": "true",
           "title.shadow": "000000-3-315-2-30"},
        transparency="30"))

    # ----------------------------------------------------------------------
    # Chart 2: Series shadow, outline, and smooth curve
    # Features: smooth, series.shadow (color-blur-angle-dist-opacity),
    #   series.outline (color-width)
    # ----------------------------------------------------------------------
    items.append(chart("/3-Area Styling",
        chartType="area",
        title="Smooth Area with Effects",
        series1="Signups:150,180,220,260,310,350",
        series2="Trials:90,110,140,170,200,230",
        categories="Jan,Feb,Mar,Apr,May,Jun",
        colors="4472C4,70AD47",
        x="13", y="0", width="12", height="18",
        smooth="true",
        **{"series.shadow": "000000-4-315-2-40",
           "series.outline": "333333-1"},
        transparency="25"))

    # ----------------------------------------------------------------------
    # Chart 3: Axis font styling, gridlines, and minor gridlines
    # Features: axisfont (size:color:font), gridlines (color:width:dash),
    #   minorGridlines
    # ----------------------------------------------------------------------
    items.append(chart("/3-Area Styling",
        chartType="area",
        title="Gridline Configuration",
        dataRange="Sheet1!A1:C13",
        colors="2E75B6,C55A11",
        x="0", y="19", width="12", height="18",
        axisfont="9:58626E:Arial",
        gridlines="D9D9D9:0.5:dot",
        minorGridlines="EEEEEE:0.3:dot",
        catTitle="Month", axisTitle="Visitors"))

    # ----------------------------------------------------------------------
    # Chart 4: Chart fill, plot fill gradient, chart/plot area borders
    # Features: chartFill, plotFill (gradient from-to:angle),
    #   chartArea.border, plotArea.border, roundedCorners
    # ----------------------------------------------------------------------
    items.append(chart("/3-Area Styling",
        chartType="area",
        title="Fills and Borders",
        series1="Sales:200,240,280,320,360,400",
        categories="Jan,Feb,Mar,Apr,May,Jun",
        colors="4472C4",
        x="13", y="19", width="12", height="18",
        chartFill="FAFAFA",
        plotFill="E8F0FE-D6E4F0:90",
        **{"chartArea.border": "D0D0D0:1:solid",
           "plotArea.border": "E0E0E0:0.5:dot"},
        roundedCorners="true"))

    doc.batch(items)

    # ==========================================================================
    # Sheet: 4-Labels & Legend
    # ==========================================================================
    print("\n--- 4-Labels & Legend ---")

    items = [add_sheet("4-Labels & Legend")]

    # ----------------------------------------------------------------------
    # Chart 1: Data labels with position, font, and number format
    # Features: dataLabels, labelPos (top), labelFont (size:color:bold),
    #   dataLabels.numFmt
    # ----------------------------------------------------------------------
    items.append(chart("/4-Labels & Legend",
        chartType="area",
        title="Labeled Area Chart",
        series1="Users:3200,3800,4500,5100,5800,6400",
        categories="Jul,Aug,Sep,Oct,Nov,Dec",
        colors="4472C4",
        x="0", y="0", width="12", height="18",
        dataLabels="true", labelPos="top",
        labelFont="9:333333:true",
        **{"dataLabels.numFmt": "#,##0"}))

    # ----------------------------------------------------------------------
    # Chart 2: Individual label deletion and per-point colors
    # Features: dataLabel{N}.delete, point{N}.color
    # ----------------------------------------------------------------------
    items.append(chart("/4-Labels & Legend",
        chartType="area",
        title="Highlighted Peak Month",
        series1="Revenue:180,210,250,310,280,260",
        categories="Jul,Aug,Sep,Oct,Nov,Dec",
        colors="2E75B6",
        x="13", y="0", width="12", height="18",
        dataLabels="true",
        **{"dataLabel1.delete": "true", "dataLabel2.delete": "true",
           "dataLabel5.delete": "true", "dataLabel6.delete": "true",
           "point4.color": "C00000"},
        transparency="30"))

    # ----------------------------------------------------------------------
    # Chart 3: Legend positioning with overlay and font styling
    # Features: legend=right, legendfont, legend.overlay
    # ----------------------------------------------------------------------
    items.append(chart("/4-Labels & Legend",
        chartType="area",
        title="Legend Overlay Demo",
        series1="Desktop:4200,4800,5100,5600",
        series2="Mobile:3100,3500,3800,4200",
        series3="Tablet:1200,1400,1500,1700",
        categories="Q1,Q2,Q3,Q4",
        colors="4472C4,ED7D31,70AD47",
        x="0", y="19", width="12", height="18",
        legend="right", legendfont="10:1F4E79:Calibri",
        **{"legend.overlay": "true"},
        transparency="35"))

    # ----------------------------------------------------------------------
    # Chart 4: Manual layout — plotArea positioning
    # Features: plotArea.x/y/w/h, title.x/y, legend.x/y/w/h (manual layout)
    # ----------------------------------------------------------------------
    items.append(chart("/4-Labels & Legend",
        chartType="area",
        title="Manual Layout",
        series1="Growth:100,130,170,220,280,350",
        categories="Jan,Feb,Mar,Apr,May,Jun",
        colors="70AD47",
        x="13", y="19", width="12", height="18",
        **{"plotArea.x": "0.12", "plotArea.y": "0.18",
           "plotArea.w": "0.82", "plotArea.h": "0.55",
           "title.x": "0.25", "title.y": "0.02",
           "legend.x": "0.15", "legend.y": "0.82",
           "legend.w": "0.7", "legend.h": "0.12"}))

    doc.batch(items)

    # ==========================================================================
    # Sheet: 5-Advanced
    # ==========================================================================
    print("\n--- 5-Advanced ---")

    items = [add_sheet("5-Advanced")]

    # ----------------------------------------------------------------------
    # Chart 1: Secondary axis (dual scale)
    # Features: secondaryAxis (1-based series index on secondary Y axis)
    # ----------------------------------------------------------------------
    items.append(chart("/5-Advanced",
        chartType="area",
        title="Revenue vs Conversion Rate",
        series1="Revenue:120,180,250,310,280,340",
        series2="Conv %:2.1,2.8,3.2,3.9,3.5,4.1",
        categories="Jan,Feb,Mar,Apr,May,Jun",
        colors="4472C4,C00000",
        x="0", y="0", width="12", height="18",
        secondaryAxis="2",
        transparency="30"))

    # ----------------------------------------------------------------------
    # Chart 2: Reference line
    # Features: referenceLine (value:color:width:dash)
    # ----------------------------------------------------------------------
    items.append(chart("/5-Advanced",
        chartType="area",
        title="Sales vs Target",
        series1="Sales:85,92,108,115,98,120",
        categories="Jan,Feb,Mar,Apr,May,Jun",
        colors="4472C4",
        x="13", y="0", width="12", height="18",
        referenceLine="100:FF0000:1.5:dash",
        transparency="25",
        areafill="4472C4-BDD7EE:90"))

    # ----------------------------------------------------------------------
    # Chart 3: Axis min/max, major unit, log scale, display units
    # Features: axisMin, axisMax, majorUnit, dispUnits (thousands/millions)
    # ----------------------------------------------------------------------
    items.append(chart("/5-Advanced",
        chartType="area",
        title="Axis Scaling Demo",
        series1="Visits:3200,3800,4500,5100,5800,6400",
        categories="Jul,Aug,Sep,Oct,Nov,Dec",
        colors="2E75B6",
        x="0", y="19", width="12", height="18",
        axisMin="3000", axisMax="7000",
        majorUnit="500",
        dispUnits="thousands",
        axisTitle="Visitors (K)",
        transparency="30"))

    # ----------------------------------------------------------------------
    # Chart 4: Color rule, title glow, series shadow
    # Features: colorRule (threshold:belowColor:aboveColor), title.glow
    #   (color-radius-opacity), series.shadow
    # ----------------------------------------------------------------------
    items.append(chart("/5-Advanced",
        chartType="area",
        title="Performance Threshold",
        series1="Score:45,62,38,71,55,80",
        categories="Jan,Feb,Mar,Apr,May,Jun",
        x="13", y="19", width="12", height="18",
        colorRule="50:C00000:70AD47",
        referenceLine="50:888888:1:solid",
        **{"title.glow": "4472C4-8-60",
           "series.shadow": "000000-3-315-1-30"},
        transparency="20"))

    doc.batch(items)

    doc.send({"command": "save"})
# context exit closes the resident, flushing the workbook to disk.

print(f"\nDone! Generated: {FILE}")
print("  6 sheets (Sheet1 data + 5 chart sheets, 20 charts total)")
