#!/usr/bin/env python3
"""
Box-Whisker Chart Showcase — generates charts-boxwhisker.xlsx exercising the
full xlsx `boxWhisker` chart property surface across 8 charts on 2 sheets:
quartile methods, multi-series, title/series/axis styling, axis scaling and
titles, axis/gridline control, plot/chart-area fills and borders, data labels,
legend, and a full presentation-grade combination.

SDK twin of charts-boxwhisker.sh (officecli CLI). Both produce an equivalent
charts-boxwhisker.xlsx. This one drives the **officecli Python SDK**
(`pip install officecli-sdk`): one resident is started and every sheet and
chart is shipped over the named pipe in a single `doc.batch(...)` round-trip.
Each item is the same `{"command","parent","type","props"}` dict you'd put in
an `officecli batch` list.

Usage:
  pip install officecli-sdk          # plus the `officecli` binary on PATH
  python3 charts-boxwhisker.py
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

FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "charts-boxwhisker.xlsx")


def sheet(name):
    """One `add sheet` item in batch-shape."""
    return {"command": "add", "parent": "/", "type": "sheet", "props": {"name": name}}


def chart(parent, **props):
    """One `add chart` item in batch-shape (parent = sheet path)."""
    return {"command": "add", "parent": parent, "type": "chart", "props": props}


print(f"Building {FILE} ...")

with officecli.create(FILE, "--force") as doc:

    # ======================================================================
    # Sheet 1: Basics & Quartile Methods
    # ======================================================================
    s1 = "/1-Basics & Quartile"
    sheet1_items = [
        sheet("1-Basics & Quartile"),

        # ------------------------------------------------------------------
        # Chart 1: Basic single-series with exclusive quartile and data labels
        # Features: single series, quartileMethod=exclusive, dataLabels
        # ------------------------------------------------------------------
        chart(s1,
              chartType="boxWhisker",
              title="Test Score Distribution",
              series1="Scores:45,52,58,61,63,65,67,68,70,72,75,78,82,85,90,95,99",
              quartileMethod="exclusive",
              dataLabels="true",
              x="0", y="0", width="13", height="18"),

        # ------------------------------------------------------------------
        # Chart 2: Multi-series with inclusive quartile, legend at bottom
        # Features: 3 series, quartileMethod=inclusive, legend=bottom
        # ------------------------------------------------------------------
        chart(s1,
              chartType="boxWhisker",
              title="Salary by Department ($k)",
              series1="Engineering:85,92,95,98,102,105,108,112,118,125,135,150,180",
              series2="Marketing:60,65,68,72,75,78,80,83,88,92,98,110",
              series3="Sales:55,62,68,75,82,90,98,105,115,125,140,160,190",
              quartileMethod="inclusive",
              legend="bottom",
              x="14", y="0", width="13", height="18"),

        # ------------------------------------------------------------------
        # Chart 3: Title styling — color, size, bold, font, shadow
        # Features: title.color, title.size, title.bold, title.font, title.shadow
        # ------------------------------------------------------------------
        chart(s1,
              chartType="boxWhisker",
              title="Styled Title Demo",
              **{"title.color": "1B2838",
                 "title.size": "20",
                 "title.bold": "true",
                 "title.font": "Georgia",
                 "title.shadow": "000000-6-45-3-50"},
              series1="Data:18,22,25,28,30,32,35,38,40,42,45,55,62,78",
              x="0", y="19", width="13", height="18"),

        # ------------------------------------------------------------------
        # Chart 4: Series colors — fill, colors (per-series), series.shadow
        # Features: colors (per-series hex), series.shadow
        # ------------------------------------------------------------------
        chart(s1,
              chartType="boxWhisker",
              title="Custom Series Colors",
              series1="GroupA:30,38,45,52,58,62,65,68,71,74,78,85,92",
              series2="GroupB:20,28,35,40,48,55,60,66,70,80,88,95,110",
              colors="5B9BD5,ED7D31",
              **{"series.shadow": "000000-6-45-3-35"},
              x="14", y="19", width="13", height="18"),
    ]
    doc.batch(sheet1_items)
    print(f"  Sheet 1: Basics & Quartile — {len(sheet1_items) - 1} charts")

    # ======================================================================
    # Sheet 2: Axes & Styling
    # ======================================================================
    s2 = "/2-Axes & Styling"
    sheet2_items = [
        sheet("2-Axes & Styling"),

        # ------------------------------------------------------------------
        # Chart 5: Axis scaling + axis titles + axis title styling + axis font
        # Features: axismin, axismax, majorunit, minorunit, xAxisTitle,
        #   yAxisTitle, axisTitle.color/.size/.bold/.font, axisfont
        # ------------------------------------------------------------------
        chart(s2,
              chartType="boxWhisker",
              title="Response Time (ms)",
              series1="API:12,18,22,25,28,30,32,35,38,40,42,45,55,62,78,95,120",
              series2="DB:5,8,10,12,14,16,18,20,22,25,28,32,38,45,60",
              axismin="0", axismax="130", majorunit="10", minorunit="5",
              xAxisTitle="Service",
              yAxisTitle="Latency (ms)",
              **{"axisTitle.color": "4A5568",
                 "axisTitle.size": "12",
                 "axisTitle.bold": "true",
                 "axisTitle.font": "Helvetica Neue"},
              axisfont="10:6B7280:Consolas",
              x="0", y="0", width="13", height="18"),

        # ------------------------------------------------------------------
        # Chart 6: Axis visibility + axis lines + gridlines + xGridlines
        # Features: cataxis.visible=false, valaxis.line, gridlines,
        #   gridlineColor, xGridlines, xGridlineColor
        # ------------------------------------------------------------------
        chart(s2,
              chartType="boxWhisker",
              title="Axis & Gridline Control",
              series1="Temp:15,18,20,22,24,26,28,30,32,35,38,40,42",
              **{"cataxis.visible": "false",
                 "valaxis.line": "334155:1.5"},
              gridlines="true",
              gridlineColor="E2E8F0",
              xGridlines="true",
              xGridlineColor="F1F5F9",
              x="14", y="0", width="13", height="18"),

        # ------------------------------------------------------------------
        # Chart 7: Plot/chart area fills, borders, gapWidth, tickLabels=false
        # Features: fill (single color), gapWidth, tickLabels=false,
        #   gridlines=false, plotareafill, plotarea.border, chartareafill,
        #   chartarea.border
        # ------------------------------------------------------------------
        chart(s2,
              chartType="boxWhisker",
              title="Card Style",
              series1="Weight:50,55,58,60,62,64,66,68,70,72,75,78,82,88,95",
              fill="6366F1",
              gapWidth="200",
              tickLabels="false",
              gridlines="false",
              plotareafill="F8FAFC",
              chartareafill="FFFFFF",
              **{"plotarea.border": "E2E8F0:1",
                 "chartarea.border": "CBD5E1:0.75"},
              x="0", y="19", width="13", height="18"),

        # ------------------------------------------------------------------
        # Chart 8: Full presentation-grade — everything combined
        # Features: ALL properties combined — title styling, multi-series
        #   colors, series.shadow, axis scaling, axis titles + styling,
        #   axisfont, axisline, gridlineColor, dataLabels + numfmt, legend +
        #   overlay + legendfont, plot/chart area fill + border
        # ------------------------------------------------------------------
        chart(s2,
              chartType="boxWhisker",
              title="Server Latency Dashboard",
              **{"title.color": "0F172A",
                 "title.size": "18",
                 "title.bold": "true",
                 "title.font": "Helvetica Neue",
                 "title.shadow": "000000-4-45-2-40"},
              series1="US-East:8,12,15,18,20,22,24,26,28,30,35,42,55,70,95",
              series2="EU-West:10,14,18,22,25,28,30,33,36,40,45,50,60,80",
              series3="AP-South:15,20,25,30,35,38,42,45,48,52,58,65,75,90,120",
              quartileMethod="exclusive",
              colors="3B82F6,10B981,F59E0B",
              axismin="0", axismax="130", majorunit="10",
              xAxisTitle="Region",
              yAxisTitle="Latency (ms)",
              axisfont="9:64748B:Helvetica Neue",
              axisline="CBD5E1:1",
              gridlineColor="E2E8F0",
              dataLabels="true",
              legend="top",
              legendfont="10:475569:Helvetica Neue",
              plotareafill="F8FAFC",
              chartareafill="FFFFFF",
              **{"series.shadow": "000000-4-45-2-30",
                 "axisTitle.color": "475569",
                 "axisTitle.size": "11",
                 "axisTitle.bold": "true",
                 "axisTitle.font": "Helvetica Neue",
                 "datalabels.numfmt": "0",
                 "legend.overlay": "false",
                 "plotarea.border": "E2E8F0:0.75",
                 "chartarea.border": "CBD5E1:0.75"},
              x="14", y="19", width="16", height="22"),
    ]
    doc.batch(sheet2_items)
    print(f"  Sheet 2: Axes & Styling — {len(sheet2_items) - 1} charts")

    # Remove blank default Sheet1
    doc.send({"command": "remove", "path": "/Sheet1"})

# context exit closes the resident, flushing the workbook to disk.

print(f"\nGenerated: {FILE}")
print("  2 sheets (8 charts total)")
print("  Sheet 1: Basics & Quartile Methods (4 charts)")
print("  Sheet 2: Axes & Styling (4 charts)")
