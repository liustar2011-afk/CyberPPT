#!/usr/bin/env python3
"""
Combo Charts Showcase — column+line, column+area, secondary axes, and styling.

Generates: charts-combo.xlsx

SDK twin of charts-combo.sh (officecli CLI). Both produce an equivalent
charts-combo.xlsx. This one drives the **officecli Python SDK**
(`pip install officecli-sdk`): one resident is started and every sheet and
chart is shipped over the named pipe in a single `doc.batch(...)` round-trip.
Each item is the same `{"command","parent"/"path","type","props"}` dict you'd
put in an `officecli batch` list.

16 combo charts across 4 sheets:
  1-Combo Fundamentals — comboSplit, secondaryAxis, combotypes per-series
  2-Combo Styling      — title.font, legendfont, axisfont, gradients, shadow,
                         dataLabels, plotFill/chartFill, roundedCorners
  3-Combo Advanced     — referenceLine, gridlines, axisMin/Max, dispUnits,
                         plotLayout, multi-line markers
  4-Combo Effects      — title.glow/shadow, chartArea/plotArea border,
                         colorRule, 5-series dashboard

Usage:
  pip install officecli-sdk          # plus the `officecli` binary on PATH
  python3 charts-combo.py
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

FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "charts-combo.xlsx")


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
        # Sheet: 1-Combo Fundamentals
        # ==================================================================
        sheet("1-Combo Fundamentals"),

        # Chart 1: Basic combo with comboSplit (2 bar series + 1 line)
        # Features: chartType=combo, comboSplit=2 (first 2 as bars, rest as lines)
        chart("/1-Combo Fundamentals",
              chartType="combo",
              title="Revenue vs Expenses vs Margin",
              series1="Revenue:120,145,160,180,195",
              series2="Expenses:90,100,110,115,125",
              series3="Margin %:25,31,31,36,36",
              categories="Q1,Q2,Q3,Q4,Q5",
              comboSplit="2",
              colors="4472C4,ED7D31,70AD47",
              x="0", y="0", width="12", height="18",
              legend="bottom"),

        # Chart 2: Combo with secondaryAxis (line on right Y-axis)
        # Features: secondaryAxis=2 (series 2 on right Y-axis), catTitle, axisTitle
        chart("/1-Combo Fundamentals",
              chartType="combo",
              title="Sales & Growth Rate",
              series1="Sales ($K):320,380,420,510,560",
              series2="Growth %:8,19,11,21,10",
              categories="2021,2022,2023,2024,2025",
              comboSplit="1",
              secondaryAxis="2",
              colors="2E75B6,C00000",
              x="13", y="0", width="12", height="18",
              legend="bottom",
              catTitle="Year", axisTitle="Sales ($K)"),

        # Chart 3: combotypes per-series type control
        # Features: combotypes=column,column,line,area (per-series type)
        chart("/1-Combo Fundamentals",
              chartType="combo",
              title="Mixed Series Types",
              series1="Product A:50,65,70,80,90",
              series2="Product B:40,55,60,72,85",
              series3="Trend:48,62,68,78,88",
              series4="Forecast:30,40,50,55,65",
              categories="Jan,Feb,Mar,Apr,May",
              combotypes="column,column,line,area",
              colors="4472C4,ED7D31,70AD47,BDD7EE",
              x="0", y="19", width="12", height="18",
              legend="bottom"),

        # Chart 4: combotypes with secondaryAxis
        # Features: combotypes + secondaryAxis together
        chart("/1-Combo Fundamentals",
              chartType="combo",
              title="Revenue Mix & Margin",
              series1="Domestic:200,220,250,270,300",
              series2="Export:80,95,110,130,150",
              series3="Net Margin %:18,20,22,24,26",
              categories="2021,2022,2023,2024,2025",
              combotypes="column,column,line",
              secondaryAxis="3",
              colors="4472C4,9DC3E6,C00000",
              x="13", y="19", width="12", height="18",
              legend="bottom",
              catTitle="Year"),

        # ==================================================================
        # Sheet: 2-Combo Styling
        # ==================================================================
        sheet("2-Combo Styling"),

        # Chart 1: Title, legend, axisfont styling
        # Features: title.font/size/color/bold, legendfont, axisfont
        chart("/2-Combo Styling",
              chartType="combo",
              title="Styled Combo Chart",
              series1="Revenue:150,175,200,220",
              series2="COGS:100,110,130,140",
              series3="Profit %:33,37,35,36",
              categories="Q1,Q2,Q3,Q4",
              comboSplit="2",
              colors="1F4E79,5B9BD5,70AD47",
              x="0", y="0", width="12", height="18",
              **{"title.font": "Georgia", "title.size": "16",
                 "title.color": "1F4E79", "title.bold": "true"},
              legend="bottom", legendfont="10:333333:Calibri",
              axisfont="9:666666"),

        # Chart 2: Series shadow, gradients
        # Features: gradients (per-bar-series), series.shadow
        chart("/2-Combo Styling",
              chartType="combo",
              title="Gradient & Shadow Effects",
              series1="Actual:85,92,105,120,135",
              series2="Budget:80,90,100,110,120",
              series3="Variance:5,2,5,10,15",
              categories="Jan,Feb,Mar,Apr,May",
              comboSplit="2",
              x="13", y="0", width="12", height="18",
              gradients="1F4E79-5B9BD5:90;C55A11-F4B183:90",
              **{"series.shadow": "000000-4-315-2-30"},
              legend="bottom"),

        # Chart 3: dataLabels on line series
        # Features: dataLabels=true, labelPos=top, labelFont
        chart("/2-Combo Styling",
              chartType="combo",
              title="Data Labels on Lines",
              series1="Units:500,620,710,800",
              series2="Avg Price:45,48,52,55",
              categories="Q1,Q2,Q3,Q4",
              comboSplit="1",
              secondaryAxis="2",
              colors="4472C4,ED7D31",
              x="0", y="19", width="12", height="18",
              dataLabels="true", labelPos="top",
              labelFont="9:333333:true",
              legend="bottom"),

        # Chart 4: plotFill, chartFill, roundedCorners
        # Features: plotFill, chartFill, roundedCorners
        chart("/2-Combo Styling",
              chartType="combo",
              title="Chart Area Styling",
              series1="Online:180,210,240,260,290",
              series2="Retail:150,140,135,130,120",
              series3="Growth %:5,12,15,10,12",
              categories="2021,2022,2023,2024,2025",
              comboSplit="2",
              colors="2E75B6,ED7D31,70AD47",
              x="13", y="19", width="12", height="18",
              plotFill="F0F4F8", chartFill="FAFAFA",
              roundedCorners="true",
              legend="bottom"),

        # ==================================================================
        # Sheet: 3-Combo Advanced
        # ==================================================================
        sheet("3-Combo Advanced"),

        # Chart 1: referenceLine, gridlines
        # Features: referenceLine=value:label:color, gridlines
        chart("/3-Combo Advanced",
              chartType="combo",
              title="Target Reference Line",
              series1="Actual:95,105,115,125,130",
              series2="Forecast:90,100,110,120,130",
              categories="Jan,Feb,Mar,Apr,May",
              comboSplit="1",
              colors="4472C4,BDD7EE",
              x="0", y="0", width="12", height="18",
              referenceLine="110:C00000:Target",
              gridlines="D9D9D9:0.5",
              legend="bottom"),

        # Chart 2: axisMin/Max, dispUnits
        # Features: axisMin/Max, dispUnits=thousands
        chart("/3-Combo Advanced",
              chartType="combo",
              title="Axis Scaling & Units",
              series1="Revenue:1200000,1450000,1600000,1800000",
              series2="Profit %:18,22,25,28",
              categories="2022,2023,2024,2025",
              comboSplit="1",
              secondaryAxis="2",
              colors="2E75B6,70AD47",
              x="13", y="0", width="12", height="18",
              axisMin="1000000", axisMax="2000000",
              dispUnits="thousands",
              legend="bottom"),

        # Chart 3: Manual layout
        # Features: plotLayout=left,top,width,height (manual plot area)
        chart("/3-Combo Advanced",
              chartType="combo",
              title="Manual Layout",
              series1="Plan:100,120,140,160",
              series2="Actual:95,125,135,170",
              series3="Delta %:-5,4,-4,6",
              categories="Q1,Q2,Q3,Q4",
              comboSplit="2",
              secondaryAxis="3",
              colors="4472C4,ED7D31,70AD47",
              x="0", y="19", width="12", height="18",
              plotLayout="0.1,0.15,0.85,0.75",
              legend="bottom"),

        # Chart 4: Multiple line series with markers + bar series
        # Features: multiple line series on secondary axis, markers
        chart("/3-Combo Advanced",
              chartType="combo",
              title="Multi-Line with Markers",
              series1="Units Sold:800,920,1050,1200,1350",
              series2="North:30,35,38,42,45",
              series3="South:25,28,32,36,40",
              series4="West:20,24,28,32,35",
              categories="Q1,Q2,Q3,Q4,Q5",
              comboSplit="1",
              secondaryAxis="2,3,4",
              colors="4472C4,C00000,70AD47,FFC000",
              x="13", y="19", width="12", height="18",
              markers="circle-6",
              legend="bottom"),

        # ==================================================================
        # Sheet: 4-Combo Effects
        # ==================================================================
        sheet("4-Combo Effects"),

        # Chart 1: title.glow, title.shadow
        # Features: title.glow=color-radius, title.shadow
        chart("/4-Combo Effects",
              chartType="combo",
              title="Glowing Title",
              series1="Metric A:60,72,85,90,100",
              series2="Metric B:40,50,55,62,70",
              series3="Ratio:67,69,65,69,70",
              categories="W1,W2,W3,W4,W5",
              comboSplit="2",
              colors="4472C4,ED7D31,70AD47",
              x="0", y="0", width="12", height="18",
              **{"title.glow": "4472C4-6",
                 "title.shadow": "000000-3-315-2-30"},
              legend="bottom"),

        # Chart 2: chartArea.border, plotArea.border
        # Features: chartArea.border=color-width, plotArea.border
        chart("/4-Combo Effects",
              chartType="combo",
              title="Bordered Areas",
              series1="Income:250,280,310,340",
              series2="Costs:180,195,210,225",
              series3="Margin %:28,30,32,34",
              categories="Q1,Q2,Q3,Q4",
              comboSplit="2",
              colors="2E75B6,ED7D31,548235",
              x="13", y="0", width="12", height="18",
              **{"chartArea.border": "333333:1.5",
                 "plotArea.border": "999999:0.75"},
              legend="bottom"),

        # Chart 3: colorRule
        # Features: colorRule=threshold:belowColor:aboveColor
        chart("/4-Combo Effects",
              chartType="combo",
              title="Color Rule Combo",
              series1="Performance:72,85,65,90,78",
              series2="Target:80,80,80,80,80",
              categories="Team A,Team B,Team C,Team D,Team E",
              comboSplit="1",
              colors="4472C4,C00000",
              x="0", y="19", width="12", height="18",
              colorRule="80:C00000:70AD47",
              legend="bottom"),

        # Chart 4: Complex combo with 5+ series
        # Features: 5 series, mixed combotypes, secondary axis
        chart("/4-Combo Effects",
              chartType="combo",
              title="Full Business Dashboard",
              series1="Revenue:500,550,600,650,700",
              series2="COGS:300,320,340,360,380",
              series3="OpEx:100,105,110,115,120",
              series4="Net Income:100,125,150,175,200",
              series5="Margin %:20,23,25,27,29",
              categories="2021,2022,2023,2024,2025",
              combotypes="column,column,column,area,line",
              secondaryAxis="5",
              colors="4472C4,ED7D31,A5A5A5,BDD7EE,C00000",
              x="13", y="19", width="12", height="18",
              legend="bottom",
              gridlines="E0E0E0:0.5"),

        # Remove blank default Sheet1 (all data is inline)
        {"command": "remove", "path": "/Sheet1"},
    ]

    doc.batch(items)
    print(f"  added {len(items)} sheets/charts/ops")
    doc.send({"command": "save"})

print(f"Generated: {FILE}")
print("  4 chart sheets, 16 charts total")
