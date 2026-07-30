#!/usr/bin/env python3
"""
Extended Chart Types Showcase — full feature coverage for waterfall, funnel,
treemap, sunburst, histogram, boxWhisker (cx:chart family) plus pareto and
chart-meta knobs (anchor, preset, autotitledeleted, plotvisonly).

Covers every extended-chart-specific property plus representative generic
cx styling knobs (title.glow, chartFill, legendfont, dataLabels...).

SDK twin of charts-extended.sh (officecli CLI). Both produce an equivalent
charts-extended.xlsx. This one drives the **officecli Python SDK**
(`pip install officecli-sdk`): one resident is started and every sheet and
chart is shipped over the named pipe in `doc.batch(...)` round-trips. Each
item is the same `{"command","parent","type","props"}` dict you'd put in an
`officecli batch` list.

Generates: charts-extended.xlsx

Usage:
  pip install officecli-sdk          # plus the `officecli` binary on PATH
  python3 charts-extended.py
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

FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "charts-extended.xlsx")


def sheet(name):
    """One `add sheet` item in batch-shape."""
    return {"command": "add", "parent": "/", "type": "sheet", "props": {"name": name}}


def chart(parent, **props):
    """One `add chart` item in batch-shape (parent is the sheet path)."""
    return {"command": "add", "parent": parent, "type": "chart", "props": props}


print(f"Building {FILE} ...")

with officecli.create(FILE, "--force") as doc:

    # ======================================================================
    # Sheet 1: Waterfall & Funnel
    # ======================================================================
    print("--- 1-Waterfall & Funnel ---")
    S1 = "/1-Waterfall & Funnel"
    items = [sheet("1-Waterfall & Funnel")]

    # ------------------------------------------------------------------
    # Chart 1: Waterfall — increase/decrease/total colors + data labels + title glow
    # Features: chartType=waterfall, increaseColor, decreaseColor, totalColor,
    #   dataLabels, title.glow
    # ------------------------------------------------------------------
    items.append(chart(S1,
        chartType="waterfall",
        title="Cash Flow Bridge",
        data="Start:1000,Revenue:500,Costs:-300,Tax:-100,Net:1100",
        increaseColor="70AD47",
        decreaseColor="FF0000",
        totalColor="4472C4",
        dataLabels="true",
        **{"title.glow": "00D2FF-6-60"},
        x="0", y="0", width="13", height="18"))

    # ------------------------------------------------------------------
    # Chart 2: Waterfall — chart-area fill + legend + custom label font
    # Features: waterfall with legend=bottom, chartFill (solid hex — cx charts
    #   don't support gradient fills, use plain RGB), labelFont "size:color:bold"
    # ------------------------------------------------------------------
    items.append(chart(S1,
        chartType="waterfall",
        title="Budget vs Actual",
        data="Budget:5000,Sales:2000,Marketing:-800,Ops:-600,Net:5600",
        increaseColor="2E75B6",
        decreaseColor="C00000",
        totalColor="FFC000",
        legend="bottom",
        chartFill="F0F4FA",
        dataLabels="true",
        labelFont="9:333333:true",
        x="14", y="0", width="13", height="18"))

    # ------------------------------------------------------------------
    # Chart 3: Funnel — sales pipeline with title shadow
    # Features: chartType=funnel, descending pipeline values, dataLabels,
    #   title.shadow "COLOR-BLUR-ANGLE-DIST-OPACITY"
    # ------------------------------------------------------------------
    items.append(chart(S1,
        chartType="funnel",
        title="Sales Pipeline",
        series1="Pipeline:1200,850,600,300,120",
        categories="Leads,Qualified,Proposal,Negotiation,Won",
        dataLabels="true",
        **{"title.shadow": "000000-4-45-2-40"},
        x="0", y="19", width="13", height="18"))

    # ------------------------------------------------------------------
    # Chart 4: Funnel — marketing conversion + legend/axis fonts
    # Features: funnel, legendfont "size:color:fontname", axisfont,
    #   6-stage pipeline, dataLabels
    #
    # NOTE: `colors=` palette is intentionally omitted here. On cx:chart single-
    #   series types (funnel/treemap/sunburst) the CLI only applies the first
    #   palette color to the whole series, so all bars would render the same
    #   color. Let Excel's theme pick the default accent color.
    # ------------------------------------------------------------------
    items.append(chart(S1,
        chartType="funnel",
        title="Marketing Funnel",
        series1="Users:10000,6500,3200,1800,900,450",
        categories="Impressions,Clicks,Signups,Active,Paying,Retained",
        dataLabels="true",
        legendfont="9:8B949E:Helvetica Neue",
        axisfont="10:58626E:Helvetica Neue",
        x="14", y="19", width="13", height="18"))

    doc.batch(items)

    # ======================================================================
    # Sheet 2: Treemap & Sunburst
    # ======================================================================
    print("--- 2-Treemap & Sunburst ---")
    S2 = "/2-Treemap & Sunburst"
    items = [sheet("2-Treemap & Sunburst")]

    # ------------------------------------------------------------------
    # Chart 1: Treemap — parentLabelLayout=overlapping + dataLabels
    # Features: chartType=treemap, parentLabelLayout=overlapping, dataLabels.
    #   NOTE: `colors=` is omitted — see Funnel Chart 4 note: cx single-series
    #   charts only pick up the first palette color. Excel's theme will auto-
    #   rainbow the tiles instead.
    # ------------------------------------------------------------------
    items.append(chart(S2,
        chartType="treemap",
        title="Revenue by Product",
        series1="Revenue:450,380,310,280,210,180,150,120",
        categories="Laptops,Phones,Tablets,TVs,Cameras,Audio,Gaming,Wearables",
        parentLabelLayout="overlapping",
        dataLabels="true",
        x="0", y="0", width="13", height="18"))

    # ------------------------------------------------------------------
    # Chart 2: Treemap — parentLabelLayout=banner + bold title
    # Features: treemap parentLabelLayout=banner, title.bold/size/color
    # ------------------------------------------------------------------
    items.append(chart(S2,
        chartType="treemap",
        title="Department Budget",
        series1="Budget:900,750,600,500,420,350,280",
        categories="Engineering,Sales,Marketing,Support,Finance,HR,Legal",
        parentLabelLayout="banner",
        **{"title.bold": "true", "title.size": "14", "title.color": "2E5090"},
        x="14", y="0", width="13", height="18"))

    # ------------------------------------------------------------------
    # Chart 3: Treemap — parentLabelLayout=none (no parent label strip)
    # Features: treemap parentLabelLayout=none (all labels inline, no header
    #   strip), dataLabels on leaf tiles
    # ------------------------------------------------------------------
    items.append(chart(S2,
        chartType="treemap",
        title="Flat Treemap (no parent labels)",
        series1="Units:250,200,180,160,140,120,100,80,60,40",
        categories="A,B,C,D,E,F,G,H,I,J",
        parentLabelLayout="none",
        dataLabels="true",
        x="0", y="19", width="13", height="18"))

    # ------------------------------------------------------------------
    # Chart 4: Sunburst — radial hierarchy + chartFill (solid) + plotFill
    # Features: chartType=sunburst, radial hierarchical layout, chartFill (solid
    #   hex), plotFill (solid hex), dataLabels.
    #   NOTE 1: cx:chart's chart/plot fill only accepts solid color — not gradient
    #     (unlike regular cChart). Use a single hex like "F8FAFC" or "none".
    #   NOTE 2: `colors=` palette is omitted for the same reason as the funnel/
    #     treemap examples — cx single-series charts paint only the first palette
    #     entry. Let Excel's theme drive per-segment coloring.
    # ------------------------------------------------------------------
    items.append(chart(S2,
        chartType="sunburst",
        title="Market Share by Region",
        series1="Share:35,25,20,15,30,25,20,10,15",
        categories="North,South,East,West,Urban,Suburban,Rural,Online,Retail",
        chartFill="F8FAFC",
        plotFill="FFFFFF",
        dataLabels="true",
        x="14", y="19", width="13", height="18"))

    doc.batch(items)

    # ======================================================================
    # Sheet 3: Histogram & Box Whisker
    # ======================================================================
    print("--- 3-Histogram & BoxWhisker ---")
    S3 = "/3-Histogram & BoxWhisker"
    items = [sheet("3-Histogram & BoxWhisker")]

    # ------------------------------------------------------------------
    # Chart 1: Histogram — auto-binning (Excel picks bin count)
    # Features: chartType=histogram, no binning knobs → Excel auto-selects bins
    # ------------------------------------------------------------------
    items.append(chart(S3,
        chartType="histogram",
        title="Test Scores (auto bins)",
        series1="Scores:45,52,58,61,63,65,67,68,70,71,72,73,74,75,76,77,78,79,80,81,82,83,84,85,86,87,88,89,90,91,92,93,94,95,97,99",
        x="0", y="0", width="13", height="18"))

    # ------------------------------------------------------------------
    # Chart 2: Histogram — explicit binCount=5 with title glow
    # Features: histogram binCount (explicit bin count), title.glow
    # ------------------------------------------------------------------
    items.append(chart(S3,
        chartType="histogram",
        title="Sales (binCount=5)",
        series1="Sales:120,135,148,155,162,170,175,183,191,200,210,220,235,250,265,280,295,310,340,380,420,480,550,620,700",
        binCount="5",
        **{"title.glow": "FFC000-6-50"},
        x="14", y="0", width="13", height="18"))

    # ------------------------------------------------------------------
    # Chart 3: Histogram — explicit binSize=50 (fixed bin width) + label font
    # Features: histogram binSize (explicit bin width — mutually exclusive with
    #   binCount), dataLabels, labelFont
    # ------------------------------------------------------------------
    items.append(chart(S3,
        chartType="histogram",
        title="Sales (binSize=50)",
        series1="Sales:120,135,148,155,162,170,175,183,191,200,210,220,235,250,265,280,295,310,340,380,420,480,550,620,700",
        binSize="50",
        dataLabels="true",
        labelFont="9:FFFFFF:true",
        x="28", y="0", width="13", height="18"))

    # ------------------------------------------------------------------
    # Chart 4: Histogram — overflow/underflow bins + intervalClosed=l
    # Features: histogram underflowBin (cutoff for <N), overflowBin (cutoff for
    #   >N), intervalClosed=l (bins are [a,b) — left-closed; default "r" is
    #   (a,b]), legend=none
    # ------------------------------------------------------------------
    items.append(chart(S3,
        chartType="histogram",
        title="Response Time (outlier bins)",
        series1="ms:40,55,68,75,82,88,95,102,110,118,125,135,150,175,220,280,350",
        underflowBin="60",
        overflowBin="200",
        intervalClosed="l",
        dataLabels="true",
        legend="none",
        x="0", y="19", width="13", height="18"))

    # ------------------------------------------------------------------
    # Chart 5: Box & Whisker — two teams, quartileMethod=exclusive
    # Features: chartType=boxWhisker, two-series comparison,
    #   quartileMethod=exclusive, legend=bottom, outlier detection (built-in)
    # ------------------------------------------------------------------
    items.append(chart(S3,
        chartType="boxWhisker",
        title="Response Time by Team (ms)",
        series1="TeamA:42,55,61,68,72,75,78,81,85,88,92,97,105,120",
        series2="TeamB:30,38,45,52,58,62,65,68,71,74,78,85,92,110",
        quartileMethod="exclusive",
        legend="bottom",
        x="14", y="19", width="13", height="18"))

    # ------------------------------------------------------------------
    # Chart 6: Box & Whisker — three departments, quartileMethod=inclusive + glow
    # Features: boxWhisker three-series, quartileMethod=inclusive (different
    #   quartile formula from exclusive), title.glow, mean markers (default on)
    # ------------------------------------------------------------------
    items.append(chart(S3,
        chartType="boxWhisker",
        title="Salary Distribution ($k)",
        series1="Engineering:85,92,95,98,102,105,108,112,118,125,135,150,180",
        series2="Marketing:60,65,68,72,75,78,80,83,88,92,98,110",
        series3="Sales:55,62,68,75,82,90,98,105,115,125,140,160,190",
        quartileMethod="inclusive",
        **{"title.glow": "00D2FF-6-60"},
        legend="bottom",
        x="28", y="19", width="13", height="18"))

    doc.batch(items)

    # ======================================================================
    # Sheet 4: Pareto
    # ======================================================================
    print("--- 4-Pareto ---")
    S4 = "/4-Pareto"
    items = [sheet("4-Pareto")]

    # ------------------------------------------------------------------
    # Chart 1: Pareto — defect analysis, raw counts auto-sorted + cumul% overlay
    # Features: chartType=pareto (2-series under the hood — clusteredColumn bars
    #   + paretoLine cumulative %), automatic descending sort, cumulative %
    #   computed server-side, dataLabels on both series.
    #   Input is a SINGLE user series; officecli pre-sorts by value desc and
    #   emits the two cx:series MSO expects (layoutId=clusteredColumn +
    #   layoutId=paretoLine with cx:binning intervalClosed="r").
    # ------------------------------------------------------------------
    items.append(chart(S4,
        chartType="pareto",
        title="Defect Pareto",
        series1="Count:45,30,10,8,5,2",
        categories="Scratches,Dents,Cracks,Chips,Stains,Other",
        dataLabels="true",
        x="0", y="0", width="13", height="18"))

    # ------------------------------------------------------------------
    # Chart 2: Pareto — root cause analysis, 10 categories, out-of-order input
    # Features: pareto with unsorted input values (12, 87, 5, ...) — officecli
    #   re-sorts by value desc (120, 87, 67, ...) and re-aligns categories so
    #   the biggest contributor renders first. title.glow + legend=bottom
    #   demonstrate generic cx styling on pareto.
    # ------------------------------------------------------------------
    items.append(chart(S4,
        chartType="pareto",
        title="Root Cause Pareto",
        series1="Tickets:12,87,5,45,3,120,22,67,8,31",
        categories="Network,Auth,DB,Cache,UI,Config,Deploy,Monitor,Queue,Storage",
        **{"title.glow": "FFC000-6-50"},
        legend="bottom",
        x="14", y="0", width="13", height="18"))

    doc.batch(items)

    # ======================================================================
    # Sheet 5: Chart Meta
    # ======================================================================
    print("--- 5-Chart Meta ---")
    S5 = "/5-Chart Meta"
    items = [sheet("5-Chart Meta")]

    # ------------------------------------------------------------------
    # Chart 1: anchor (cell-range placement), preset (named style bundle)
    # Features: anchor="A1:M20" (position chart at exact cell-range instead of
    #   x/y/width/height — accepts A1-notation two-cell anchor string),
    #   preset=corporate (named style bundle that sets colors, fonts, fill, border
    #   in one shot; values: minimal, dark, corporate, magazine, dashboard,
    #   colorful, monochrome)
    # ------------------------------------------------------------------
    items.append(chart(S5,
        chartType="column",
        title="anchor + preset=corporate",
        series1="Revenue:120,145,132,160",
        categories="Q1,Q2,Q3,Q4",
        anchor="A1:M20",
        preset="corporate"))

    # ------------------------------------------------------------------
    # Chart 2: autotitledeleted, plotvisonly
    # Features: autotitledeleted=true (suppress the auto "Chart Title" placeholder
    #   that Excel inserts — use when you want no title at all without explicitly
    #   passing title=none),
    #   plotvisonly=true (skip plotting hidden rows/columns — mirrors Excel's
    #   "Show data in hidden rows and columns" unchecked)
    # ------------------------------------------------------------------
    items.append(chart(S5,
        chartType="bar",
        series1="Sales:80,95,88,110",
        categories="Q1,Q2,Q3,Q4",
        x="0", y="22", width="12", height="18",
        autotitledeleted="true",
        plotvisonly="true"))

    # ------------------------------------------------------------------
    # Chart 3: preset variants — minimal
    # Features: preset=minimal (strip: removes gridlines, legend, border, most
    #   styling; exposes the data with minimal chrome)
    # ------------------------------------------------------------------
    items.append(chart(S5,
        chartType="line",
        title="preset=minimal",
        series1="A:10,20,15,25",
        series2="B:8,14,12,20",
        categories="W1,W2,W3,W4",
        x="13", y="0", width="12", height="18",
        preset="minimal"))

    # ------------------------------------------------------------------
    # Chart 4: preset=dark
    # Features: preset=dark (dark background, light-colored series and text)
    # ------------------------------------------------------------------
    items.append(chart(S5,
        chartType="column",
        title="preset=dark",
        series1="Sales:45,60,55,80",
        categories="Q1,Q2,Q3,Q4",
        x="13", y="22", width="12", height="18",
        preset="dark"))

    doc.batch(items)

    # Remove blank default Sheet1 (all data is inline)
    doc.send({"command": "remove", "path": "/Sheet1"})

    doc.send({"command": "save"})
# context exit closes the resident, flushing the workbook to disk.

print(f"\nDone! Generated: {FILE}")
print("  4 sheets, 16 charts total (full cx:chart feature coverage)")
print("  Sheet 1: Waterfall (2) + Funnel (2)")
print("  Sheet 2: Treemap (3: overlapping/banner/none) + Sunburst (1)")
print("  Sheet 3: Histogram (4: auto/binCount/binSize/overflow+underflow+intervalClosed=l) + BoxWhisker (2: exclusive/inclusive)")
print("  Sheet 4: Pareto (2: sorted input / out-of-order input)")
print("  Sheet 5: Chart Meta (4: anchor+preset / autotitledeleted+plotvisonly / minimal / dark)")
