#!/usr/bin/env python3
"""
Radar Charts Showcase — radar with standard, filled, and marker styles.

Generates: charts-radar.xlsx  (16 charts across 4 sheets)

SDK twin of charts-radar.sh (officecli CLI). Both produce an equivalent
charts-radar.xlsx. This one drives the **officecli Python SDK**
(`pip install officecli-sdk`): one resident is started and every sheet and
chart is shipped over the named pipe in a single `doc.batch(...)` round-trip.
Each item is the same `{"command","parent","type","props"}` dict you'd put in
an `officecli batch` list.

Usage:
  pip install officecli-sdk          # plus the `officecli` binary on PATH
  python3 charts-radar.py
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

FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "charts-radar.xlsx")


def sheet(name):
    """One `add sheet` item in batch-shape."""
    return {"command": "add", "parent": "/", "type": "sheet", "props": {"name": name}}


def chart(parent, **props):
    """One `add chart` item in batch-shape (parent = the sheet path)."""
    return {"command": "add", "parent": parent, "type": "chart", "props": props}


print(f"Building {FILE} ...")

with officecli.create(FILE, "--force") as doc:
    items = [
        # ==================================================================
        # Sheet: 1-Radar Fundamentals
        # ==================================================================
        sheet("1-Radar Fundamentals"),

        # Chart 1: Basic radar (standard style) with 3 series
        # Features: chartType=radar, radarStyle=standard, 3 series,
        #   categories as spokes
        chart("/1-Radar Fundamentals",
              chartType="radar",
              radarStyle="standard",
              title="Athlete Comparison",
              series1="Alice:85,70,90,60,75",
              series2="Bob:65,90,70,80,85",
              series3="Carol:75,80,80,70,65",
              categories="Speed,Strength,Stamina,Agility,Accuracy",
              colors="4472C4,ED7D31,70AD47",
              x="0", y="0", width="12", height="18",
              legend="bottom"),

        # Chart 2: Radar with markers (marker style)
        # Features: radarStyle=marker, marker=circle:6:color, dataLabels
        chart("/1-Radar Fundamentals",
              chartType="radar",
              radarStyle="marker",
              title="Product Ratings",
              series1="Product A:9,7,8,6,8",
              series2="Product B:6,9,7,8,5",
              categories="Quality,Price,Design,Support,Delivery",
              colors="2E75B6,C00000",
              marker="circle:6:2E75B6",
              x="13", y="0", width="12", height="18",
              legend="bottom",
              dataLabels="true"),

        # Chart 3: Filled radar with transparency
        # Features: radarStyle=filled, transparency=40 (semi-transparent fill)
        chart("/1-Radar Fundamentals",
              chartType="radar",
              radarStyle="filled",
              title="Skills Assessment",
              series1="Junior:50,40,60,70,55",
              series2="Senior:85,80,75,90,80",
              categories="Coding,Design,Testing,Communication,Leadership",
              colors="4472C4,70AD47",
              transparency="40",
              x="0", y="19", width="12", height="18",
              legend="bottom"),

        # Chart 4: Filled radar with per-series colors and white outline
        # Features: filled radar, series.outline (white border between areas),
        #   3 overlapping series with transparency
        chart("/1-Radar Fundamentals",
              chartType="radar",
              radarStyle="filled",
              title="Department Scores",
              series1="Engineering:90,75,60,85,70",
              series2="Marketing:60,85,80,70,90",
              series3="Sales:70,80,75,65,85",
              categories="Innovation,Teamwork,Efficiency,Quality,Growth",
              colors="4472C4,ED7D31,70AD47",
              **{"series.outline": "FFFFFF-0.5"},
              transparency="35",
              x="13", y="19", width="12", height="18",
              legend="bottom"),

        # ==================================================================
        # Sheet: 2-Radar Styling
        # ==================================================================
        sheet("2-Radar Styling"),

        # Chart 1: Title styling (font, size, color, bold, shadow)
        # Features: title.font, title.size, title.color, title.bold,
        #   title.shadow
        chart("/2-Radar Styling",
              chartType="radar",
              radarStyle="marker",
              title="Styled Title Demo",
              series1="Team A:80,65,90,70,85",
              categories="Attack,Defense,Speed,Skill,Stamina",
              colors="2E75B6",
              x="0", y="0", width="12", height="18",
              **{"title.font": "Georgia", "title.size": "18",
                 "title.color": "1F4E79", "title.bold": "true",
                 "title.shadow": "000000-3-315-2-30"}),

        # Chart 2: Series shadow effects
        # Features: series.shadow on filled radar, transparency with shadow
        chart("/2-Radar Styling",
              chartType="radar",
              radarStyle="filled",
              title="Shadow Effects",
              series1="Region A:75,80,65,90,70",
              series2="Region B:60,70,85,75,80",
              categories="Revenue,Profit,Growth,Retention,Satisfaction",
              colors="4472C4,ED7D31",
              **{"series.shadow": "000000-4-315-2-30"},
              transparency="30",
              x="13", y="0", width="12", height="18",
              legend="bottom"),

        # Chart 3: Axis font and gridlines styling
        # Features: axisfont (size:color:fontFamily), gridlines (color-width)
        chart("/2-Radar Styling",
              chartType="radar",
              radarStyle="marker",
              title="Axis & Gridlines",
              series1="Actual:70,85,60,75,80",
              series2="Target:80,80,80,80,80",
              categories="KPI 1,KPI 2,KPI 3,KPI 4,KPI 5",
              colors="4472C4,C00000",
              axisfont="10:333333:Calibri",
              gridlines="D9D9D9:0.5",
              x="0", y="19", width="12", height="18",
              legend="bottom"),

        # Chart 4: Plot fill, chart fill, rounded corners, borders
        # Features: plotFill, chartFill, roundedCorners, chartArea.border,
        #   plotArea.border
        chart("/2-Radar Styling",
              chartType="radar",
              radarStyle="filled",
              title="Chart Area Styling",
              series1="Score:85,70,90,60,75",
              categories="Speed,Power,Technique,Endurance,Flexibility",
              colors="4472C4",
              transparency="25",
              x="13", y="19", width="12", height="18",
              plotFill="F5F5F5", chartFill="FAFAFA",
              roundedCorners="true",
              **{"chartArea.border": "BFBFBF:0.5",
                 "plotArea.border": "D9D9D9:0.25"}),

        # ==================================================================
        # Sheet: 3-Labels & Legend
        # ==================================================================
        sheet("3-Labels & Legend"),

        # Chart 1: Data labels with font styling and position
        # Features: dataLabels=true, labelPos=outsideEnd,
        #   labelFont (size:color:bold)
        chart("/3-Labels & Legend",
              chartType="radar",
              radarStyle="marker",
              title="Data Labels",
              series1="Performance:88,72,95,67,81",
              categories="Speed,Strength,Stamina,Agility,Accuracy",
              colors="2E75B6",
              marker="circle:6:2E75B6",
              x="0", y="0", width="12", height="18",
              dataLabels="true", labelPos="outsideEnd",
              labelFont="9:333333:true"),

        # Chart 2: Legend positioning and styling with overlay
        # Features: legend=right, legendfont (size:color:fontFamily),
        #   legend.overlay
        chart("/3-Labels & Legend",
              chartType="radar",
              radarStyle="standard",
              title="Legend Styles",
              series1="Alpha:80,60,75,90,70",
              series2="Beta:70,80,85,65,75",
              series3="Gamma:65,75,70,80,85",
              categories="Metric A,Metric B,Metric C,Metric D,Metric E",
              colors="4472C4,ED7D31,70AD47",
              x="13", y="0", width="12", height="18",
              legend="right",
              legendfont="10:1F4E79:Calibri",
              **{"legend.overlay": "true"}),

        # Chart 3: Manual plot area layout
        # Features: plotArea.x/y/w/h (fractional manual layout positioning)
        chart("/3-Labels & Legend",
              chartType="radar",
              radarStyle="filled",
              title="Custom Layout",
              series1="Team:85,70,90,65,80",
              categories="Vision,Execution,Culture,Agility,Impact",
              colors="4472C4",
              transparency="30",
              x="0", y="19", width="12", height="18",
              **{"plotArea.x": "0.1", "plotArea.y": "0.15",
                 "plotArea.w": "0.8", "plotArea.h": "0.75"}),

        # Chart 4: Multiple series (5+) comparison
        # Features: 5 series on one radar, distinguishing many overlapping lines
        chart("/3-Labels & Legend",
              chartType="radar",
              radarStyle="standard",
              title="Multi-Team Comparison",
              series1="Dev:90,70,80,65,75",
              series2="QA:60,85,70,80,90",
              series3="Design:75,80,85,70,60",
              series4="PM:80,65,75,90,70",
              series5="DevOps:70,75,60,85,80",
              categories="Speed,Quality,Innovation,Teamwork,Delivery",
              colors="4472C4,ED7D31,70AD47,FFC000,7030A0",
              x="13", y="19", width="12", height="18",
              legend="bottom",
              legendfont="9:333333:Calibri"),

        # ==================================================================
        # Sheet: 4-Advanced
        # ==================================================================
        sheet("4-Advanced"),

        # Chart 1: Title glow and shadow effects
        # Features: title.glow (color-radius), title.shadow combined
        chart("/4-Advanced",
              chartType="radar",
              radarStyle="marker",
              title="Glow & Shadow Title",
              series1="Score:75,85,65,90,80",
              categories="Creativity,Logic,Memory,Focus,Speed",
              colors="2E75B6",
              marker="diamond:7:2E75B6",
              x="0", y="0", width="12", height="18",
              **{"title.font": "Georgia", "title.size": "16",
                 "title.bold": "true", "title.color": "1F4E79",
                 "title.glow": "4472C4-8",
                 "title.shadow": "000000-3-315-2-30"}),

        # Chart 2: Radar with many spokes (8 categories)
        # Features: 8 categories (many spokes), benchmark overlay, gridlines
        chart("/4-Advanced",
              chartType="radar",
              radarStyle="filled",
              title="8-Spoke Assessment",
              series1="Candidate:85,70,90,60,75,80,65,88",
              series2="Benchmark:70,70,70,70,70,70,70,70",
              categories="Technical,Communication,Leadership,Creativity,Analytical,Teamwork,Adaptability,Initiative",
              colors="4472C4,BFBFBF",
              transparency="35",
              x="13", y="0", width="12", height="18",
              legend="bottom",
              gridlines="D9D9D9:0.25"),

        # Chart 3: Single-series radar with full styling
        # Features: single series with marker, full title/chart/plot styling,
        #   themed color scheme (purple)
        chart("/4-Advanced",
              chartType="radar",
              radarStyle="marker",
              title="Personal Profile",
              series1="Self:92,78,85,65,88,70",
              categories="Python,JavaScript,SQL,DevOps,Testing,Design",
              colors="7030A0",
              marker="square:7:7030A0",
              x="0", y="19", width="12", height="18",
              dataLabels="true", labelFont="9:7030A0:true",
              plotFill="F8F0FF", chartFill="FFFFFF",
              roundedCorners="true",
              **{"title.font": "Calibri", "title.size": "14",
                 "title.color": "7030A0", "title.bold": "true",
                 "chartArea.border": "7030A0:0.5"}),

        # Chart 4: Two-series filled radar with low transparency for overlap
        # Features: low transparency (20%) for visible overlap, before/after
        #   comparison pattern, series.outline for separation
        chart("/4-Advanced",
              chartType="radar",
              radarStyle="filled",
              title="Before vs After",
              series1="Before:55,40,65,50,45",
              series2="After:85,75,80,70,80",
              categories="Revenue,Efficiency,Satisfaction,Innovation,Retention",
              colors="C00000,70AD47",
              transparency="20",
              **{"series.outline": "FFFFFF-0.75"},
              x="13", y="19", width="12", height="18",
              legend="bottom",
              dataLabels="true", labelFont="9:333333:false",
              chartFill="FAFAFA", plotFill="F5F5F5"),

        # Remove blank default Sheet1 (all data is inline)
        {"command": "remove", "path": "/Sheet1"},
    ]

    doc.batch(items)
    print(f"  added {len(items)} sheets/charts")

print(f"Generated: {FILE}")
print("  4 chart sheets, 16 charts total")
