#!/usr/bin/env python3
"""
Pie & Doughnut Charts Showcase — pie, pie3d, and doughnut with all variations.

Generates: charts-pie.xlsx

SDK twin of charts-pie.sh (officecli CLI). Both produce an equivalent
charts-pie.xlsx. This one drives the **officecli Python SDK**
(`pip install officecli-sdk`): one resident is started and every sheet and
chart is shipped over the named pipe in a single `doc.batch(...)` round-trip.
Each item is the same `{"command","parent","type","props"}` dict you'd put in
an `officecli batch` list.

3 chart sheets, 12 charts total: 4 pie/pie3d, 4 doughnut, 4 advanced.

Usage:
  pip install officecli-sdk          # plus the `officecli` binary on PATH
  python3 charts-pie.py
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

FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "charts-pie.xlsx")


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
        # Sheet: 1-Pie Charts
        # ==================================================================
        sheet("1-Pie Charts"),

        # ------------------------------------------------------------------
        # Chart 1: Basic pie chart with inline data and custom colors
        # Features: chartType=pie, inline series, categories, colors, dataLabels
        # ------------------------------------------------------------------
        chart("/1-Pie Charts",
              chartType="pie",
              title="Market Share",
              series1="Share:40,25,20,15",
              categories="Product A,Product B,Product C,Product D",
              colors="4472C4,ED7D31,70AD47,FFC000",
              x="0", y="0", width="12", height="18",
              dataLabels="true", labelPos="outsideEnd"),

        # ------------------------------------------------------------------
        # Chart 2: Pie with exploded slice and per-point colors
        # Features: explosion (slice separation %), point{N}.color,
        #   labelPos=bestFit, dataLabels=percent
        # ------------------------------------------------------------------
        chart("/1-Pie Charts",
              chartType="pie",
              title="Revenue by Region",
              series1="Revenue:35,28,22,15",
              categories="North,South,East,West",
              x="13", y="0", width="12", height="18",
              explosion="15",
              **{"point1.color": "1F4E79", "point2.color": "2E75B6",
                 "point3.color": "9DC3E6", "point4.color": "BDD7EE"},
              dataLabels="percent", labelPos="bestFit"),

        # ------------------------------------------------------------------
        # Chart 3: 3D pie with perspective and title styling
        # Features: pie3d, view3d on pie (tilt angle), title.font/size/color/bold,
        #   labelFont (size:color:bold)
        # ------------------------------------------------------------------
        chart("/1-Pie Charts",
              chartType="pie3d",
              title="3D Category Split",
              series1="Sales:45,30,25",
              categories="Electronics,Clothing,Food",
              colors="2E75B6,70AD47,FFC000",
              x="0", y="19", width="12", height="18",
              view3d="30,0,0",
              **{"title.font": "Georgia", "title.size": "16",
                 "title.color": "1F4E79", "title.bold": "true"},
              dataLabels="true", labelPos="center",
              labelFont="12:FFFFFF:true"),

        # ------------------------------------------------------------------
        # Chart 4: Pie with gradient fills, leader lines, and legend positioning
        # Features: gradients (per-slice), legend=right, legendfont,
        #   dataLabels.showLeaderLines, chartFill, roundedCorners
        # ------------------------------------------------------------------
        chart("/1-Pie Charts",
              chartType="pie",
              title="Q4 Distribution",
              series1="Q4:198,158,142,180",
              categories="East,South,North,West",
              x="13", y="19", width="12", height="18",
              gradients="4472C4-BDD7EE:90;ED7D31-FBE5D6:90;70AD47-C5E0B4:90;FFC000-FFF2CC:90",
              legend="right", legendfont="10:333333:Helvetica",
              dataLabels="true",
              **{"dataLabels.showLeaderLines": "true"},
              chartFill="FAFAFA", roundedCorners="true"),

        # ==================================================================
        # Sheet: 2-Doughnut Charts
        # ==================================================================
        sheet("2-Doughnut Charts"),

        # ------------------------------------------------------------------
        # Chart 1: Basic doughnut chart
        # Features: chartType=doughnut, center labels
        # ------------------------------------------------------------------
        chart("/2-Doughnut Charts",
              chartType="doughnut",
              title="Channel Mix",
              series1="Channel:55,45",
              categories="Online,Retail",
              colors="4472C4,ED7D31",
              x="0", y="0", width="12", height="18",
              dataLabels="true", labelPos="center",
              labelFont="14:FFFFFF:true"),

        # ------------------------------------------------------------------
        # Chart 2: Multi-ring doughnut (multiple series)
        # Features: multi-ring doughnut (multiple series = concentric rings),
        #   series.outline (white separator between slices)
        # ------------------------------------------------------------------
        chart("/2-Doughnut Charts",
              chartType="doughnut",
              title="Year-over-Year Comparison",
              series1="2024:40,35,25",
              series2="2025:45,30,25",
              categories="Electronics,Clothing,Food",
              colors="4472C4,70AD47,FFC000",
              x="13", y="0", width="12", height="18",
              **{"series.outline": "FFFFFF-1"},
              legend="bottom"),

        # ------------------------------------------------------------------
        # Chart 3: Styled doughnut with shadow and custom data labels
        # Features: series.shadow on doughnut, title.shadow, plotFill
        # ------------------------------------------------------------------
        chart("/2-Doughnut Charts",
              chartType="doughnut",
              title="Priority Breakdown",
              series1="Priority:50,30,20",
              categories="High,Medium,Low",
              colors="C00000,FFC000,70AD47",
              x="0", y="19", width="12", height="18",
              **{"series.shadow": "000000-4-315-2-30"},
              dataLabels="true", labelPos="outsideEnd",
              **{"dataLabels.numFmt": '0"%"', "title.shadow": "000000-3-315-2-30"},
              plotFill="F5F5F5"),

        # ------------------------------------------------------------------
        # Chart 4: Doughnut with per-slice gradient and explosion
        # Features: explosion on doughnut, 5-slice gradients
        # ------------------------------------------------------------------
        chart("/2-Doughnut Charts",
              chartType="doughnut",
              title="Product Revenue",
              series1="Revenue:35,25,20,12,8",
              categories="Laptop,Phone,Tablet,Jacket,Coffee",
              x="13", y="19", width="12", height="18",
              explosion="8",
              gradients="1F4E79-5B9BD5:90;C55A11-F4B183:90;548235-A9D18E:90;7F6000-FFD966:90;843C0B-DDA15E:90",
              legend="right",
              dataLabels="true", labelPos="bestFit"),

        # ==================================================================
        # Sheet: 3-Pie Advanced
        # ==================================================================
        sheet("3-Pie Advanced"),

        # ------------------------------------------------------------------
        # Chart 1: varyColors=true + firstSliceAngle on pie
        # Features: varyColors=true (each slice gets a distinct color
        #   automatically), firstSliceAngle=45 (rotates the first slice start
        #   angle, 0-360 degrees)
        # ------------------------------------------------------------------
        chart("/3-Pie Advanced",
              chartType="pie",
              title="Pie — varyColors + firstSliceAngle",
              series1="Share:40,30,20,10",
              categories="Q1,Q2,Q3,Q4",
              x="0", y="0", width="12", height="18",
              varyColors="true",
              firstSliceAngle="45",
              dataLabels="true", labelPos="bestFit"),

        # ------------------------------------------------------------------
        # Chart 2: holeSize + leaderlines on doughnut
        # Features: holeSize=65 (% of total radius — larger value = thinner
        #   ring), leaderlines=true (connecting lines from labels to slices,
        #   pie/doughnut)
        # ------------------------------------------------------------------
        chart("/3-Pie Advanced",
              chartType="doughnut",
              title="Doughnut — holeSize + leaderlines",
              series1="Revenue:35,28,22,15",
              categories="North,South,East,West",
              colors="2E75B6,ED7D31,70AD47,FFC000",
              x="13", y="0", width="12", height="18",
              holeSize="65",
              leaderlines="true",
              dataLabels="true", labelPos="outsideEnd"),

        # ------------------------------------------------------------------
        # Chart 3: title.overlay on pie (title floats over plot area)
        # Features: title.overlay=true (title overlays the plot area,
        #   maximizing chart area — contrast with default where title reserves
        #   space above)
        # ------------------------------------------------------------------
        chart("/3-Pie Advanced",
              chartType="pie",
              title="Overlaid Title",
              **{"title.overlay": "true"},
              series1="Mix:50,30,20",
              categories="Online,Retail,Partner",
              colors="4472C4,70AD47,FFC000",
              x="0", y="19", width="12", height="18",
              varyColors="false",
              dataLabels="percent", labelPos="center"),

        # ------------------------------------------------------------------
        # Chart 4: Doughnut — holeSize + firstSliceAngle + title.overlay combined
        # Features: three doughnut-specific props together —
        #   holeSize, varyColors, title.overlay
        # ------------------------------------------------------------------
        chart("/3-Pie Advanced",
              chartType="doughnut",
              title="Doughnut — Combined",
              **{"title.overlay": "true"},
              series1="Split:45,35,20",
              categories="A,B,C",
              colors="C00000,FFC000,548235",
              x="13", y="19", width="12", height="18",
              holeSize="50",
              varyColors="false",
              dataLabels="true", labelPos="center",
              labelFont="12:FFFFFF:true"),

        # Remove blank default Sheet1 (all data is inline)
        {"command": "remove", "path": "/Sheet1"},
    ]

    doc.batch(items)
    print(f"  applied {len(items)} items (3 sheets, 12 charts)")
    doc.send({"command": "save"})

print(f"Generated: {FILE}")
print("  3 sheets (3 chart sheets, 12 charts total)")
