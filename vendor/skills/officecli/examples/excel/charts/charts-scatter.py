#!/usr/bin/env python3
"""
Scatter Charts Showcase — scatter with all marker, trendline, error bar, and styling variations.

Generates: charts-scatter.xlsx

Every scatter chart feature officecli supports is demonstrated at least once:
scatter styles, marker types, smooth curves, trendlines (linear, polynomial,
exponential, logarithmic, power, movingAvg), error bars, axis scaling,
gridlines, data labels, legend, fills, shadows, borders, secondary axis,
reference lines, log scale, and color rules.

6 sheets, 24 charts total.

  1-Scatter Fundamentals   4 charts — basic scatter, marker-only, smooth curve, line-only
  2-Marker Styles          4 charts — per-series markers, shapes, sizes, toggle
  3-Trendlines             4 charts — linear, polynomial, exponential, per-series
  4-Error Bars             4 charts — fixed, percent, stddev, stderr
  5-Styling                4 charts — title/shadow, gradients, axis/grid, borders
  6-Advanced               4 charts — secondary axis, reference line, log scale, color rule

SDK twin of charts-scatter.sh (officecli CLI). Both produce an equivalent
charts-scatter.xlsx. This one drives the **officecli Python SDK**
(`pip install officecli-sdk`): one resident is started and every sheet and
chart is shipped over the named pipe in a single `doc.batch(...)` round-trip.
Each item is the same `{"command","parent","type","props"}` dict you'd put in
an `officecli batch` list.

Usage:
  pip install officecli-sdk          # plus the `officecli` binary on PATH
  python3 charts-scatter.py
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

FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "charts-scatter.xlsx")


def sheet(name):
    """One `add sheet` item in batch-shape."""
    return {"command": "add", "parent": "/", "type": "sheet", "props": {"name": name}}


def chart(parent, **props):
    """One `add chart` item in batch-shape."""
    return {"command": "add", "parent": parent, "type": "chart", "props": props}


print(f"Building {FILE} ...")

with officecli.create(FILE, "--force") as doc:
    items = [
        # ==================================================================
        # Sheet: 1-Scatter Fundamentals
        # ==================================================================
        sheet("1-Scatter Fundamentals"),

        # Chart 1: Basic scatter with circle markers and connecting lines
        # Features: chartType=scatter, marker=circle, markerSize=6, lineWidth=1.5,
        #   catTitle, axisTitle, legend
        chart("/1-Scatter Fundamentals",
              chartType="scatter",
              title="Height vs Weight",
              categories="160,165,170,175,180,185,190",
              series1="Male:62,68,72,78,82,88,95",
              series2="Female:50,55,58,62,65,70,74",
              colors="2E75B6,ED7D31",
              x="0", y="0", width="12", height="18",
              marker="circle", markerSize="6",
              lineWidth="1.5",
              catTitle="Height (cm)", axisTitle="Weight (kg)",
              legend="bottom"),

        # Chart 2: Scatter marker-only (scatterStyle=marker), various marker sizes
        # Features: scatterStyle=marker (no connecting lines), markerSize=8,
        #   gridlines styling
        chart("/1-Scatter Fundamentals",
              chartType="scatter",
              scatterStyle="marker",
              title="Study Hours vs Test Score",
              categories="1,2,3,4,5,6,7,8",
              series1="Class A:55,60,65,72,78,82,88,92",
              series2="Class B:50,58,62,68,74,80,85,90",
              colors="4472C4,70AD47",
              x="13", y="0", width="12", height="18",
              markerSize="8",
              catTitle="Study Hours", axisTitle="Score",
              gridlines="D9D9D9:0.5:dot"),

        # Chart 3: Scatter smooth curve (smooth=true, scatterStyle=smooth)
        # Features: scatterStyle=smooth, smooth=true (Bezier interpolation),
        #   marker=diamond, single series
        chart("/1-Scatter Fundamentals",
              chartType="scatter",
              scatterStyle="smooth",
              smooth="true",
              title="Temperature vs Ice Cream Sales",
              categories="15,18,22,25,28,30,33,35",
              series1="Sales ($):120,180,260,340,420,480,530,560",
              colors="C00000",
              x="0", y="19", width="12", height="18",
              marker="diamond", markerSize="7",
              lineWidth="2",
              catTitle="Temperature (C)", axisTitle="Daily Sales ($)"),

        # Chart 4: Scatter line-only (no markers, scatterStyle=line)
        # Features: scatterStyle=line (line without markers), showMarker=false,
        #   lineWidth=2.5, lineDash=dash
        chart("/1-Scatter Fundamentals",
              chartType="scatter",
              scatterStyle="line",
              title="Altitude vs Air Pressure",
              categories="0,500,1000,2000,3000,5000,8000",
              series1="Pressure (hPa):1013,955,899,795,701,540,356",
              colors="1F4E79",
              x="13", y="19", width="12", height="18",
              showMarker="false",
              lineWidth="2.5",
              lineDash="dash",
              catTitle="Altitude (m)", axisTitle="Pressure (hPa)"),

        # ==================================================================
        # Sheet: 2-Marker Styles
        # ==================================================================
        sheet("2-Marker Styles"),

        # Chart 1: Per-series markers — circle, diamond, square
        # Features: series1.marker=circle, series2.marker=diamond,
        #   series3.marker=square (per-series marker style)
        chart("/2-Marker Styles",
              chartType="scatter",
              title="Per-Series Markers: Circle, Diamond, Square",
              categories="10,20,30,40,50,60",
              series1="Sensor A:12,28,35,42,55,68",
              series2="Sensor B:8,22,30,38,48,58",
              series3="Sensor C:15,25,32,45,52,62",
              colors="4472C4,ED7D31,70AD47",
              x="0", y="0", width="12", height="18",
              **{"series1.marker": "circle",
                 "series2.marker": "diamond",
                 "series3.marker": "square"},
              markerSize="8", lineWidth="1",
              legend="bottom"),

        # Chart 2: Per-series markers — triangle, star, x
        # Features: series1.marker=triangle, series2.marker=star, series3.marker=x
        chart("/2-Marker Styles",
              chartType="scatter",
              title="Per-Series Markers: Triangle, Star, X",
              categories="5,10,15,20,25,30",
              series1="Lab 1:18,32,28,45,52,60",
              series2="Lab 2:22,25,38,40,48,55",
              series3="Lab 3:10,20,32,35,42,50",
              colors="FFC000,9DC3E6,843C0B",
              x="13", y="0", width="12", height="18",
              **{"series1.marker": "triangle",
                 "series2.marker": "star",
                 "series3.marker": "x"},
              markerSize="9", lineWidth="1",
              legend="bottom"),

        # Chart 3: Large markers with series colors, markerSize=10
        # Features: markerSize=10, marker=plus, marker=dash, scatterStyle=marker
        chart("/2-Marker Styles",
              chartType="scatter",
              scatterStyle="marker",
              title="Large Markers (size=10)",
              categories="100,200,300,400,500",
              series1="Revenue:150,280,350,420,510",
              series2="Profit:80,140,180,220,280",
              series3="Cost:70,140,170,200,230",
              colors="2E75B6,548235,BF8F00",
              x="0", y="19", width="12", height="18",
              **{"series1.marker": "circle",
                 "series2.marker": "plus",
                 "series3.marker": "dash"},
              markerSize="10",
              legend="right"),

        # Chart 4: showMarker=false (line only) vs showMarker=true
        # Features: scatterStyle=lineMarker, showMarker=false (markers hidden),
        #   lineDash=dashDot
        chart("/2-Marker Styles",
              chartType="scatter",
              scatterStyle="lineMarker",
              title="Marker Toggle (none shown)",
              categories="1,2,3,4,5,6,7,8,9,10",
              series1="Signal:3,7,5,11,9,14,12,18,15,20",
              series2="Noise:2,4,6,5,8,7,10,9,12,11",
              colors="4472C4,BFBFBF",
              x="13", y="19", width="12", height="18",
              showMarker="false",
              lineWidth="2",
              lineDash="dashDot",
              legend="bottom"),

        # ==================================================================
        # Sheet: 3-Trendlines
        # ==================================================================
        sheet("3-Trendlines"),

        # Chart 1: Linear trendline with equation display
        # Features: trendline=linear, series1.trendline.equation=true
        chart("/3-Trendlines",
              chartType="scatter",
              scatterStyle="marker",
              title="Linear Trendline + Equation",
              categories="1,2,3,4,5,6,7,8,9,10",
              series1="Observed:8,15,22,28,33,42,48,55,60,68",
              colors="4472C4",
              x="0", y="0", width="12", height="18",
              markerSize="7",
              trendline="linear",
              **{"series1.trendline.equation": "true"},
              catTitle="X", axisTitle="Y"),

        # Chart 2: Polynomial trendline (order 3) with R-squared display
        # Features: trendline=poly:3, series1.trendline.rsquared=true
        chart("/3-Trendlines",
              chartType="scatter",
              scatterStyle="marker",
              title="Polynomial (order 3) + R-squared",
              categories="1,2,3,4,5,6,7,8,9,10",
              series1="Measurement:5,12,25,30,28,35,50,62,58,72",
              colors="70AD47",
              x="13", y="0", width="12", height="18",
              markerSize="7", marker="square",
              trendline="poly:3",
              **{"series1.trendline.rsquared": "true"},
              catTitle="Sample", axisTitle="Value"),

        # Chart 3: Exponential trendline with forward/backward extrapolation
        # Features: trendline=exp:2:1 (forward=2, backward=1),
        #   series1.trendline.name (custom trendline label)
        chart("/3-Trendlines",
              chartType="scatter",
              scatterStyle="marker",
              title="Exponential + Extrapolation",
              categories="1,2,3,4,5,6,7,8",
              series1="Growth:2,4,7,12,20,35,58,95",
              colors="ED7D31",
              x="0", y="19", width="12", height="18",
              markerSize="7", marker="triangle",
              trendline="exp:2:1",
              **{"series1.trendline.name": "Exponential Fit"},
              catTitle="Period", axisTitle="Amount"),

        # Chart 4: Per-series trendlines — linear vs logarithmic
        # Features: series1.trendline=linear, series2.trendline=log,
        #   per-series trendline with sub-properties
        chart("/3-Trendlines",
              chartType="scatter",
              scatterStyle="marker",
              title="Per-Series: Linear vs Logarithmic",
              categories="1,2,4,8,16,32,64",
              series1="Dataset A:10,18,30,45,62,78,95",
              series2="Dataset B:5,25,38,45,50,54,56",
              colors="4472C4,C00000",
              x="13", y="19", width="12", height="18",
              markerSize="7",
              **{"series1.trendline": "linear",
                 "series2.trendline": "log",
                 "series1.trendline.equation": "true",
                 "series2.trendline.rsquared": "true"},
              legend="bottom"),

        # ==================================================================
        # Sheet: 4-Error Bars
        # ==================================================================
        sheet("4-Error Bars"),

        # Chart 1: Fixed error bars (errBars=fixed:5)
        # Features: errBars=fixed:5 (constant +/-5 error)
        chart("/4-Error Bars",
              chartType="scatter",
              title="Fixed Error Bars (+-5)",
              categories="10,20,30,40,50,60",
              series1="Measurement:25,42,58,72,88,105",
              colors="4472C4",
              x="0", y="0", width="12", height="18",
              marker="circle", markerSize="7",
              lineWidth="1",
              errBars="fixed:5",
              catTitle="Input", axisTitle="Output"),

        # Chart 2: Percentage error bars (errBars=percent:10)
        # Features: errBars=percent:10 (10% of each value)
        chart("/4-Error Bars",
              chartType="scatter",
              title="Percentage Error Bars (10%)",
              categories="5,10,15,20,25,30",
              series1="Yield:120,185,240,310,375,450",
              colors="70AD47",
              x="13", y="0", width="12", height="18",
              marker="diamond", markerSize="7",
              lineWidth="1",
              errBars="percent:10",
              catTitle="Dosage", axisTitle="Yield"),

        # Chart 3: Standard deviation error bars (errBars=stddev)
        # Features: errBars=stddev (standard deviation), multi-series with errBars
        chart("/4-Error Bars",
              chartType="scatter",
              title="Standard Deviation Error Bars",
              categories="0,1,2,3,4,5,6,7",
              series1="Trial 1:48,52,47,55,50,53,49,51",
              series2="Trial 2:30,35,28,40,32,38,34,36",
              colors="ED7D31,9DC3E6",
              x="0", y="19", width="12", height="18",
              marker="square", markerSize="6",
              lineWidth="1",
              errBars="stddev",
              legend="bottom"),

        # Chart 4: Standard error with series styling
        # Features: errBars=stderr, series.shadow, gridlines styling
        chart("/4-Error Bars",
              chartType="scatter",
              title="Standard Error + Styled Series",
              categories="2,4,6,8,10,12,14",
              series1="Experiment:18,32,28,45,40,55,52",
              colors="843C0B",
              x="13", y="19", width="12", height="18",
              marker="star", markerSize="8",
              lineWidth="1.5",
              errBars="stderr",
              **{"series.shadow": "000000-4-315-2-30"},
              gridlines="D9D9D9:0.5:dot",
              catTitle="Time (h)", axisTitle="Response"),

        # ==================================================================
        # Sheet: 5-Styling
        # ==================================================================
        sheet("5-Styling"),

        # Chart 1: Title styling, series shadow, series outline
        # Features: title.font, title.size, title.color, title.bold, title.shadow,
        #   series.shadow, series.outline
        chart("/5-Styling",
              chartType="scatter",
              title="Styled Title + Series Effects",
              categories="10,20,30,40,50",
              series1="Alpha:15,35,28,48,55",
              series2="Beta:8,22,32,40,50",
              colors="4472C4,ED7D31",
              x="0", y="0", width="12", height="18",
              marker="circle", markerSize="8", lineWidth="2",
              **{"title.font": "Georgia", "title.size": "16",
                 "title.color": "1F4E79", "title.bold": "true",
                 "title.shadow": "000000-3-315-2-30",
                 "series.shadow": "000000-4-315-2-30",
                 "series.outline": "333333:1.5"},
              legend="bottom"),

        # Chart 2: Gradients, transparency, plotFill, chartFill
        # Features: gradients (per-series gradient), transparency, plotFill, chartFill
        chart("/5-Styling",
              chartType="scatter",
              title="Gradients + Fills",
              categories="5,15,25,35,45",
              series1="Group 1:12,28,35,42,55",
              series2="Group 2:8,18,22,38,48",
              x="13", y="0", width="12", height="18",
              marker="diamond", markerSize="8", lineWidth="1.5",
              gradients="4472C4-BDD7EE:90;ED7D31-FBE5D6:90",
              transparency="20",
              plotFill="F5F5F5",
              chartFill="FAFAFA",
              legend="bottom"),

        # Chart 3: Axis font, gridlines, minor gridlines, axis line
        # Features: axisfont (size:color:font), gridlines, minorGridlines, axisLine
        chart("/5-Styling",
              chartType="scatter",
              title="Axis & Grid Styling",
              categories="0,10,20,30,40,50",
              series1="Readings:5,22,38,52,68,82",
              colors="2E75B6",
              x="0", y="19", width="12", height="18",
              marker="circle", markerSize="7", lineWidth="1.5",
              axisfont="9:C00000:Arial",
              gridlines="BFBFBF:0.75:solid",
              minorGridlines="E0E0E0:0.25:dot",
              axisLine="333333:1",
              catTitle="X Axis", axisTitle="Y Axis"),

        # Chart 4: Chart area border, plot area border, rounded corners
        # Features: chartArea.border, plotArea.border, roundedCorners
        chart("/5-Styling",
              chartType="scatter",
              title="Borders + Rounded Corners",
              categories="1,3,5,7,9",
              series1="Data:10,25,18,35,28",
              colors="548235",
              x="13", y="19", width="12", height="18",
              marker="square", markerSize="8", lineWidth="1.5",
              **{"chartArea.border": "333333:1.5",
                 "plotArea.border": "999999:0.75"},
              roundedCorners="true",
              chartFill="FFFFFF",
              plotFill="F0F0F0"),

        # ==================================================================
        # Sheet: 6-Advanced
        # ==================================================================
        sheet("6-Advanced"),

        # Chart 1: Secondary axis
        # Features: secondaryAxis=2 (series 2 on right Y-axis)
        chart("/6-Advanced",
              chartType="scatter",
              title="Secondary Y-Axis",
              categories="10,20,30,40,50,60",
              series1="Temperature (C):15,20,28,32,38,42",
              series2="Humidity (%):85,78,65,58,45,38",
              colors="C00000,4472C4",
              x="0", y="0", width="12", height="18",
              marker="circle", markerSize="7", lineWidth="1.5",
              secondaryAxis="2",
              legend="bottom",
              catTitle="Location"),

        # Chart 2: Reference line (horizontal target)
        # Features: referenceLine=value:color:label:dash (horizontal target line)
        chart("/6-Advanced",
              chartType="scatter",
              title="Reference Line (Target=75)",
              categories="1,2,3,4,5,6,7,8",
              series1="Score:60,68,72,78,80,74,82,88",
              colors="70AD47",
              x="13", y="0", width="12", height="18",
              marker="diamond", markerSize="7", lineWidth="1.5",
              referenceLine="75:FF0000:Target:dash",
              catTitle="Week", axisTitle="Performance"),

        # Chart 3: Axis min/max and log scale
        # Features: logBase=10 (logarithmic value axis), axisMin, axisMax
        chart("/6-Advanced",
              chartType="scatter",
              title="Log Scale (base 10)",
              categories="1,10,100,1000,10000",
              series1="Response:2,15,120,950,8500",
              colors="1F4E79",
              x="0", y="19", width="12", height="18",
              marker="triangle", markerSize="8", lineWidth="1.5",
              logBase="10",
              axisMin="1", axisMax="10000",
              catTitle="Concentration", axisTitle="Response"),

        # Chart 4: Data labels and color rule
        # Features: dataLabels=true, labelPos=top, colorRule=threshold:below:above
        #   (points below 60 = red, above = green)
        chart("/6-Advanced",
              chartType="scatter",
              scatterStyle="marker",
              title="Data Labels + Color Rule",
              categories="1,2,3,4,5,6,7,8",
              series1="KPI:45,62,38,78,55,82,48,90",
              colors="4472C4",
              x="13", y="19", width="12", height="18",
              markerSize="9",
              dataLabels="true", labelPos="top",
              colorRule="60:C00000:00AA00",
              catTitle="Quarter", axisTitle="KPI Score"),

        # Remove blank default Sheet1 (all data is inline)
        {"command": "remove", "path": "/Sheet1"},
    ]

    doc.batch(items)
    print(f"  added {len(items)} sheets/charts")

print(f"Generated: {FILE}")
print("  6 chart sheets, 24 charts total")
