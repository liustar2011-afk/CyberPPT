#!/usr/bin/env python3
"""
Histogram Charts — Grand Showcase
==================================

The most thorough, most visually polished histogram demo officecli can
produce. Every binning knob, every styling vocabulary, every canonical
distribution shape, six design themes on one dataset, four font type
specimens, and a cohesive production-grade ML dashboard — all driven by
the real officecli Python SDK.

SDK twin of charts-histogram.sh (officecli CLI). Both produce an equivalent
charts-histogram.xlsx. This one drives the **officecli Python SDK**
(`pip install officecli-sdk`): one resident is started and every sheet and
chart is shipped over the named pipe in `doc.batch(...)` round-trips. Each
item is the same `{"command","parent","type","props"}` dict you'd put in an
`officecli batch` list.

Generates: charts-histogram.xlsx (6 sheets, 29 histograms)

  0-Hero                 1 magazine-grade full-bleed hero poster chart
  1-Binning Lab          6 charts — every binning knob, identical styling
  2-Distribution Zoo     6 canonical real-world distribution shapes
  3-Theme Gallery        6 design themes on the SAME dataset
  4-Typography           4 font-family type specimens
  5-ML Dashboard         6-chart "Production ML Model Report" dashboard

Usage:
  pip install officecli-sdk          # plus the `officecli` binary on PATH
  python3 charts-histogram.py
"""

import os
import sys
import random
import math

# --- locate the SDK: prefer an installed `officecli-sdk`, else the in-repo copy
try:
    import officecli  # pip install officecli-sdk
except ImportError:
    sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                    "..", "..", "..", "sdk", "python"))
    import officecli

FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "charts-histogram.xlsx")


# --------------------------------------------------------------------------
# Batch-item helpers — each returns one dict you'd put in an `officecli batch`
# list. The SDK ships the whole list in a single named-pipe round-trip.
# --------------------------------------------------------------------------
def add_sheet(name):
    """One `add sheet` item in batch-shape."""
    return {"command": "add", "parent": "/", "type": "sheet", "props": {"name": name}}


def chart(parent, **props):
    """One `add chart` item in batch-shape."""
    props.setdefault("chartType", "histogram")
    return {"command": "add", "parent": parent, "type": "chart", "props": props}


# --------------------------------------------------------------------------
# Deterministic sample generators — same seed, same file every regeneration.
# All datasets are CSV-joined once here and reused across sheets.
# --------------------------------------------------------------------------
def csv(values):
    return ",".join(str(v) for v in values)

# The "reference" bell curve — 200 samples around 75±12. Used by the hero,
# the binning lab, the theme gallery, the typography specimens, and the zoo.
random.seed(42)
BELL_200 = sorted(round(random.gauss(75, 12), 1) for _ in range(200))
BELL_CSV = csv(BELL_200)

# Bimodal: two cohorts (beginners ~55, experts ~88) glued together.
random.seed(7)
BIMODAL = sorted(
    [round(random.gauss(55, 6), 1) for _ in range(80)]
    + [round(random.gauss(88, 5), 1) for _ in range(80)]
)
BIMODAL_CSV = csv(BIMODAL)

# Right-skewed / log-normal: classic income shape.
random.seed(11)
LOGNORM = sorted(round(math.exp(random.gauss(3.2, 0.55)), 1) for _ in range(180))
LOGNORM_CSV = csv(LOGNORM)

# Left-skewed: retirement ages — most cluster high, a few retire early.
random.seed(23)
LEFT_SKEW = sorted(round(75 - math.exp(random.gauss(1.6, 0.6)), 1) for _ in range(140))
LEFT_CSV = csv(LEFT_SKEW)

# Uniform: random draws evenly distributed across a range.
random.seed(31)
UNIFORM = sorted(round(random.uniform(0, 100), 1) for _ in range(160))
UNIFORM_CSV = csv(UNIFORM)

# Heavy-tailed (Pareto): most small, tiny fraction catastrophic.
random.seed(47)
PARETO = sorted(round(random.paretovariate(1.6) * 20, 1) for _ in range(200))
PARETO_CSV = csv(PARETO)

# --- ML Dashboard datasets (sheet 5) ---
random.seed(101)
LATENCY_MS = sorted(round(random.paretovariate(1.8) * 15 + 10, 1) for _ in range(250))
LATENCY_CSV = csv(LATENCY_MS)

random.seed(102)
CONFIDENCE = sorted(round(random.betavariate(6, 2) * 100, 2) for _ in range(240))
CONFIDENCE_CSV = csv(CONFIDENCE)

random.seed(103)
ERROR_MAG = sorted(round(abs(random.gauss(0, 1.5)), 3) for _ in range(180))
ERROR_MAG_CSV = csv(ERROR_MAG)

random.seed(104)
TOKEN_LEN = sorted(
    [max(1, round(random.gauss(180, 40))) for _ in range(100)]
    + [max(1, round(random.gauss(520, 90))) for _ in range(80)]
)
TOKEN_CSV = csv(TOKEN_LEN)

random.seed(105)
GPU_UTIL = sorted(round(min(99.0, max(30.0, random.gauss(82, 8))), 1) for _ in range(200))
GPU_CSV = csv(GPU_UTIL)

random.seed(106)
COST_REQ = sorted(round(math.exp(random.gauss(-3.2, 0.9)) * 1000, 3) for _ in range(220))
COST_CSV = csv(COST_REQ)


print(f"Building {FILE} ...")

with officecli.create(FILE, "--force") as doc:

    # ======================================================================
    # Sheet 0: "0-Hero" — the full-bleed magazine hero poster
    #
    # A single giant chart using EVERY histogram knob at once:
    #   - Dark "Midnight Academia" palette: navy plot area, gold bars, cream text
    #   - title.*  (color/size/bold/font/shadow)
    #   - series.shadow + fill
    #   - axisline + axisfont + axisTitle.*
    #   - plotareafill / plotarea.border / chartareafill / chartarea.border
    #   - axismin / axismax / majorunit (locked Y scale)
    #   - gridlineColor
    #   - dataLabels + datalabels.numfmt
    #   - legend=top + legend.overlay + legendfont
    #   - intervalClosed=l + explicit binCount
    #
    # This chart is the "representative sample" — if it renders correctly, the
    # entire histogram pipeline is healthy.
    # ======================================================================
    print("\n--- 0-Hero ---")
    doc.batch([
        # rename the default Sheet1 → "0-Hero"
        {"command": "set", "path": "/Sheet1", "props": {"name": "0-Hero"}},
        # EVERY knob — title/series/axis/plotarea/chartarea/shadow/scaling/legend/datalabel
        chart("/0-Hero",
              title="The Shape of Data · 200-sample bell curve",
              **{"title.color": "F5F1E0", "title.size": "22", "title.bold": "true",
                 "title.font": "Helvetica Neue",
                 "title.shadow": "000000-8-45-4-70"},
              series1=f"Samples:{BELL_CSV}",
              binCount="24", intervalClosed="l",
              fill="F0C96A", **{"series.shadow": "000000-8-45-4-60"},
              axismin="0", axismax="28", majorunit="4",
              xAxisTitle="Score", yAxisTitle="Frequency",
              **{"axisTitle.color": "C9B87A", "axisTitle.size": "13",
                 "axisTitle.bold": "true", "axisTitle.font": "Helvetica Neue",
                 "axisfont": "10:B8B090:Helvetica Neue",
                 "axisline": "6A6448:1.5"},
              gridlineColor="2F3544",
              plotareafill="1A1F2C", **{"plotarea.border": "3A3E4E:1.25"},
              chartareafill="0B0F18", **{"chartarea.border": "2A2E3E:1"},
              dataLabels="true", **{"datalabels.numfmt": "0"},
              legend="top", **{"legend.overlay": "false",
                               "legendfont": "11:D4C994:Helvetica Neue"},
              x="0", y="0", width="27", height="38"),
    ])

    # ======================================================================
    # Sheet 1: "1-Binning Lab"
    #
    # Six histograms, SAME dataset (BELL_200), IDENTICAL typography / colors /
    # frames — the ONLY thing that varies is the binning strategy. Put side by
    # side, this sheet is the "Rosetta stone": once you see how each binning
    # knob reshapes the bars, you'll never be confused about which to use.
    #
    #   ┌──────────┬──────────┐
    #   │ 1. auto  │ 2. count │
    #   ├──────────┼──────────┤
    #   │ 3. fine  │ 4. width │
    #   ├──────────┼──────────┤
    #   │ 5. fence │ 6. lclos │
    #   └──────────┴──────────┘
    # ======================================================================
    print("\n--- 1-Binning Lab ---")

    # Shared "clean lab" style — every chart on this sheet wears the exact same
    # outfit so the bin-shape difference is the only visible variable.
    LAB = {
        "fill": "4472C4",
        "title.color": "1F2937", "title.size": "13", "title.bold": "true",
        "title.font": "Helvetica Neue",
        "xAxisTitle": "Score", "yAxisTitle": "Count",
        "axisTitle.color": "6B7280", "axisTitle.size": "10",
        "axisTitle.font": "Helvetica Neue",
        "axisfont": "9:6B7280:Helvetica Neue",
        "gridlineColor": "F0F0F0",
        "plotareafill": "FFFFFF", "plotarea.border": "E5E7EB:0.75",
        "chartareafill": "F9FAFB", "chartarea.border": "E5E7EB:0.75",
        "axisline": "9CA3AF:0.75",
    }

    doc.batch([
        add_sheet("1-Binning Lab"),
        # no binCount, no binSize — Excel picks the bin count automatically.
        chart("/1-Binning Lab", title="1 · Auto-binning (Excel default)",
              series1=f"Samples:{BELL_CSV}", **LAB,
              x="0", y="0", width="13", height="18"),
        # binCount=8 — coarse. Fewer, wider bars. Good for "what's the mode?"
        chart("/1-Binning Lab", title="2 · binCount=8 (coarse)",
              series1=f"Samples:{BELL_CSV}", binCount="8", **LAB,
              x="14", y="0", width="13", height="18"),
        # binCount=32 — fine. Many narrow bars. Good for "is it really Gaussian?"
        chart("/1-Binning Lab", title="3 · binCount=32 (fine)",
              series1=f"Samples:{BELL_CSV}", binCount="32", **LAB,
              x="0", y="19", width="13", height="18"),
        # binSize=5 — fixed bin width. Use when you want human-friendly bin
        # boundaries (multiples of 5, 10, etc) regardless of data range.
        chart("/1-Binning Lab", title="4 · binSize=5 (fixed-width bins)",
              series1=f"Samples:{BELL_CSV}", binSize="5", **LAB,
              x="14", y="19", width="13", height="18"),
        # underflowBin=55 + overflowBin=95 — outlier fencing. Everything below
        # 55 or above 95 collapses into a single <55 / >95 bar.
        chart("/1-Binning Lab", title="5 · underflow=55 · overflow=95 (fencing)",
              series1=f"Samples:{BELL_CSV}", binSize="5", underflowBin="55",
              overflowBin="95", **LAB,
              x="0", y="38", width="13", height="18"),
        # intervalClosed=l (half-open [a,b)) + gapWidth=30 — shows the
        # "left-closed" variant AND pushes bars apart so you can see each one.
        # Useful when the dataset has values lying exactly on a bin boundary.
        chart("/1-Binning Lab", title="6 · [a,b) intervals + gapWidth=30",
              series1=f"Samples:{BELL_CSV}", binCount="16", intervalClosed="l",
              gapWidth="30", **LAB,
              x="14", y="38", width="13", height="18"),
    ])

    # ======================================================================
    # Sheet 2: "2-Distribution Zoo"
    #
    # A cohesive 2x3 gallery of the canonical distribution shapes you'll see
    # in production data. Pattern recognition: if you ever see one of these
    # shapes in a telemetry chart, you know immediately what's going on.
    #
    # Every chart shares the same typography + plot/chart area frames; only
    # the fill color and data change. Uses different binning strategies
    # appropriate to each distribution.
    # ======================================================================
    print("\n--- 2-Distribution Zoo ---")

    ZOO = {
        "title.color": "1F2937", "title.size": "13", "title.bold": "true",
        "title.font": "Helvetica Neue",
        "axisTitle.color": "6B7280", "axisTitle.size": "10",
        "axisTitle.font": "Helvetica Neue",
        "axisfont": "9:6B7280:Helvetica Neue",
        "gridlineColor": "EFEFEF",
        "plotareafill": "FFFFFF", "plotarea.border": "E5E7EB:0.75",
        "chartareafill": "F9FAFB", "chartarea.border": "E5E7EB:0.75",
        "axisline": "9CA3AF:0.75",
    }

    doc.batch([
        add_sheet("2-Distribution Zoo"),
        # classic bell curve reference, binCount=18, midnight blue fill.
        chart("/2-Distribution Zoo", title="Normal · bell curve (reference)",
              series1=f"Samples:{BELL_CSV}", binCount="18", fill="2F5597",
              xAxisTitle="Score", yAxisTitle="Count", **ZOO,
              x="0", y="0", width="13", height="18"),
        # bimodal — two hidden populations. Narrow bins reveal the split.
        chart("/2-Distribution Zoo", title="Bimodal · two hidden cohorts",
              series1=f"Score:{BIMODAL_CSV}", binCount="22", fill="ED7D31",
              xAxisTitle="Test score", yAxisTitle="Students", **ZOO,
              x="14", y="0", width="13", height="18"),
        # right-skewed log-normal. Mean >> median, long tail to the right.
        chart("/2-Distribution Zoo", title="Right-skewed · log-normal (income)",
              series1=f"Income:{LOGNORM_CSV}", binCount="20", fill="70AD47",
              xAxisTitle="Monthly income ($k)", yAxisTitle="People", **ZOO,
              x="0", y="19", width="13", height="18"),
        # left-skewed — retirement ages cluster high, tail stretches left.
        chart("/2-Distribution Zoo", title="Left-skewed · retirement ages",
              series1=f"Age:{LEFT_CSV}", binCount="18", fill="7030A0",
              xAxisTitle="Age at retirement", yAxisTitle="Retirees", **ZOO,
              x="14", y="19", width="13", height="18"),
        # uniform — every value equally likely. binSize emphasizes the
        # "flat floor" visual tell.
        chart("/2-Distribution Zoo", title="Uniform · flat floor",
              series1=f"Draws:{UNIFORM_CSV}", binSize="10", fill="00B0F0",
              xAxisTitle="Random draw (0-100)", yAxisTitle="Count", **ZOO,
              x="0", y="38", width="13", height="18"),
        # heavy-tailed Pareto + overflowBin. Fences the catastrophic tail so
        # the interesting bulk of the distribution stays readable.
        chart("/2-Distribution Zoo", title="Heavy-tailed · Pareto (overflow=250)",
              series1=f"Latency:{PARETO_CSV}", binSize="20", overflowBin="250",
              fill="C00000",
              xAxisTitle="Latency (ms)", yAxisTitle="Requests", **ZOO,
              x="14", y="38", width="13", height="18"),
    ])

    # ======================================================================
    # Sheet 3: "3-Theme Gallery"
    #
    # Six complete design themes applied to the SAME bell-curve dataset. Each
    # theme is a coordinated palette: plot-area fill, chart-area fill, series
    # fill, gridline color, axis line color, tick-label color, title color,
    # title font — all chosen to read as one coherent mood.
    #
    # Grid:
    #   ┌─────────────┬─────────────┐
    #   │ 1. Midnight │ 2. Sunset   │
    #   ├─────────────┼─────────────┤
    #   │ 3. Forest   │ 4. Mono     │
    #   ├─────────────┼─────────────┤
    #   │ 5. Neon     │ 6. Pastel   │
    #   └─────────────┴─────────────┘
    # ======================================================================
    print("\n--- 3-Theme Gallery ---")
    doc.batch([
        add_sheet("3-Theme Gallery"),
        # Theme 1 · Midnight Academia — dark plot area, gold bars, shadows
        chart("/3-Theme Gallery", title="Midnight Academia",
              **{"title.color": "F5F1E0", "title.size": "14", "title.bold": "true",
                 "title.font": "Georgia", "title.shadow": "000000-6-45-3-70"},
              series1=f"Samples:{BELL_CSV}", binCount="18", fill="F0C96A",
              **{"series.shadow": "000000-6-45-3-55"},
              plotareafill="1A1F2C", **{"plotarea.border": "3A3E4E:1"},
              chartareafill="0B0F18", **{"chartarea.border": "2A2E3E:0.75"},
              gridlineColor="2F3544",
              **{"axisfont": "9:B8B090:Georgia"},
              xAxisTitle="Score", yAxisTitle="Count",
              **{"axisTitle.color": "C9B87A", "axisTitle.size": "10",
                 "axisTitle.font": "Georgia", "axisline": "5A5848:1"},
              x="0", y="0", width="13", height="18"),
        # Theme 2 · Sunset Terracotta (warm cream + coral, serif)
        chart("/3-Theme Gallery", title="Sunset Terracotta",
              **{"title.color": "3F2818", "title.size": "14", "title.bold": "true",
                 "title.font": "Georgia"},
              series1=f"Samples:{BELL_CSV}", binCount="18", fill="E85D4A",
              plotareafill="FFF5E8", **{"plotarea.border": "F0D8B0:1"},
              chartareafill="FFE6C7", **{"chartarea.border": "E6BC88:1"},
              gridlineColor="F5C98A",
              **{"axisfont": "9:6B4A2A:Georgia"},
              xAxisTitle="Score", yAxisTitle="Count",
              **{"axisTitle.color": "A8522C", "axisTitle.size": "10",
                 "axisTitle.font": "Georgia", "axisline": "C08050:1"},
              x="14", y="0", width="13", height="18"),
        # Theme 3 · Forest Parchment (beige + forest green, serif)
        chart("/3-Theme Gallery", title="Forest Parchment",
              **{"title.color": "1F3A1F", "title.size": "14", "title.bold": "true",
                 "title.font": "Georgia"},
              series1=f"Samples:{BELL_CSV}", binCount="18", fill="2F5D3A",
              plotareafill="F3EDD8", **{"plotarea.border": "C8B890:1"},
              chartareafill="EADFBE", **{"chartarea.border": "A89858:1"},
              gridlineColor="C0B888",
              **{"axisfont": "9:4A5A3A:Georgia"},
              xAxisTitle="Score", yAxisTitle="Count",
              **{"axisTitle.color": "3F5A2F", "axisTitle.size": "10",
                 "axisTitle.font": "Georgia", "axisline": "6A7A4A:1"},
              x="0", y="19", width="13", height="18"),
        # Theme 4 · Editorial Mono (pure grayscale, sans)
        chart("/3-Theme Gallery", title="Editorial Mono",
              **{"title.color": "111111", "title.size": "14", "title.bold": "true",
                 "title.font": "Helvetica Neue"},
              series1=f"Samples:{BELL_CSV}", binCount="18", fill="2A2A2A",
              plotareafill="FFFFFF", **{"plotarea.border": "CCCCCC:0.75"},
              chartareafill="FAFAFA", **{"chartarea.border": "E0E0E0:0.75"},
              gridlineColor="EEEEEE",
              **{"axisfont": "9:555555:Helvetica Neue"},
              xAxisTitle="Score", yAxisTitle="Count",
              **{"axisTitle.color": "333333", "axisTitle.size": "10",
                 "axisTitle.font": "Helvetica Neue", "axisline": "888888:1"},
              x="14", y="19", width="13", height="18"),
        # Theme 5 · Neon Terminal (black + electric cyan, mono)
        chart("/3-Theme Gallery", title="Neon Terminal",
              **{"title.color": "00F0C8", "title.size": "14", "title.bold": "true",
                 "title.font": "Courier New", "title.shadow": "00F0C8-6-45-0-40"},
              series1=f"Samples:{BELL_CSV}", binCount="18", fill="00F0C8",
              **{"series.shadow": "00F0C8-8-45-0-45"},
              plotareafill="0A0A14", **{"plotarea.border": "1F2F3F:1"},
              chartareafill="000008", **{"chartarea.border": "1F1F2F:1"},
              gridlineColor="1A2A3A",
              **{"axisfont": "9:00D0E8:Courier New"},
              xAxisTitle="Score", yAxisTitle="Count",
              **{"axisTitle.color": "00D0E8", "axisTitle.size": "10",
                 "axisTitle.font": "Courier New", "axisline": "00707F:1"},
              x="0", y="38", width="13", height="18"),
        # Theme 6 · Pastel Bloom (lavender cream + rose, sans)
        chart("/3-Theme Gallery", title="Pastel Bloom",
              **{"title.color": "5A3C4A", "title.size": "14", "title.bold": "true",
                 "title.font": "Helvetica Neue"},
              series1=f"Samples:{BELL_CSV}", binCount="18", fill="F5A7C8",
              plotareafill="FDF4F8", **{"plotarea.border": "F0D0E0:1"},
              chartareafill="FAEDF2", **{"chartarea.border": "F0C0D8:1"},
              gridlineColor="F5D8E5",
              **{"axisfont": "9:8A6878:Helvetica Neue"},
              xAxisTitle="Score", yAxisTitle="Count",
              **{"axisTitle.color": "A04C6A", "axisTitle.size": "10",
                 "axisTitle.font": "Helvetica Neue", "axisline": "C888A0:1"},
              x="14", y="38", width="13", height="18"),
    ])

    # ======================================================================
    # Sheet 4: "4-Typography"
    #
    # Four font-family "type specimens". Same data, same geometry, same colors —
    # only the font varies. Side-by-side, this shows how typography alone reads
    # as tone: Helvetica is corporate, Georgia is editorial, Courier is data,
    # Verdana is approachable.
    # ======================================================================
    print("\n--- 4-Typography ---")
    doc.batch([
        add_sheet("4-Typography"),
        # Specimen 1 · Helvetica Neue (modern sans — dashboards, corporate reports)
        chart("/4-Typography", title="Helvetica Neue · modern sans",
              **{"title.color": "1F2937", "title.size": "16", "title.bold": "true",
                 "title.font": "Helvetica Neue"},
              series1=f"Samples:{BELL_CSV}", binCount="18", fill="4472C4",
              xAxisTitle="Score", yAxisTitle="Count",
              **{"axisTitle.color": "4472C4", "axisTitle.size": "11",
                 "axisTitle.font": "Helvetica Neue",
                 "axisfont": "10:6B7280:Helvetica Neue"},
              gridlineColor="EEEEEE",
              plotareafill="FFFFFF", **{"plotarea.border": "E5E7EB:0.75"},
              chartareafill="F9FAFB", **{"chartarea.border": "E5E7EB:0.75"},
              x="0", y="0", width="13", height="18"),
        # Specimen 2 · Georgia (editorial serif — magazines, long-form reports)
        chart("/4-Typography", title="Georgia · editorial serif",
              **{"title.color": "3F2818", "title.size": "16", "title.bold": "true",
                 "title.font": "Georgia"},
              series1=f"Samples:{BELL_CSV}", binCount="18", fill="A8522C",
              xAxisTitle="Score", yAxisTitle="Count",
              **{"axisTitle.color": "A8522C", "axisTitle.size": "11",
                 "axisTitle.font": "Georgia",
                 "axisfont": "10:6B4A2A:Georgia"},
              gridlineColor="F0E8D8",
              plotareafill="FFFBF3", **{"plotarea.border": "E8D8B8:0.75"},
              chartareafill="FDF6E8", **{"chartarea.border": "E8D8B8:0.75"},
              x="14", y="0", width="13", height="18"),
        # Specimen 3 · Courier New (monospace — data, telemetry, engineering)
        chart("/4-Typography", title="Courier New · data mono",
              **{"title.color": "1A3A1A", "title.size": "16", "title.bold": "true",
                 "title.font": "Courier New"},
              series1=f"Samples:{BELL_CSV}", binCount="18", fill="2F8F4F",
              xAxisTitle="Score", yAxisTitle="Count",
              **{"axisTitle.color": "2F8F4F", "axisTitle.size": "11",
                 "axisTitle.font": "Courier New",
                 "axisfont": "10:3A5A3A:Courier New"},
              gridlineColor="E0EDE0",
              plotareafill="F7FBF7", **{"plotarea.border": "C8DCC8:0.75"},
              chartareafill="F0F7F0", **{"chartarea.border": "C8DCC8:0.75"},
              x="0", y="19", width="13", height="18"),
        # Specimen 4 · Verdana (friendly sans — onboarding, public-facing UI)
        chart("/4-Typography", title="Verdana · friendly sans",
              **{"title.color": "4A2B6A", "title.size": "16", "title.bold": "true",
                 "title.font": "Verdana"},
              series1=f"Samples:{BELL_CSV}", binCount="18", fill="8E4DBB",
              xAxisTitle="Score", yAxisTitle="Count",
              **{"axisTitle.color": "8E4DBB", "axisTitle.size": "11",
                 "axisTitle.font": "Verdana",
                 "axisfont": "10:6B4A8A:Verdana"},
              gridlineColor="ECE0F4",
              plotareafill="FCF7FF", **{"plotarea.border": "D8C4E8:0.75"},
              chartareafill="F6EDFA", **{"chartarea.border": "D8C4E8:0.75"},
              x="14", y="19", width="13", height="18"),
    ])

    # ======================================================================
    # Sheet 5: "5-ML Dashboard"
    #
    # A cohesive six-chart "Production ML Model Report". Every chart wears the
    # same corporate dashboard uniform — same typography, same frames, same
    # gridlines — but each shows a different slice of the model's behavior,
    # deliberately using a different color + binning strategy so the six read
    # as a single dashboard at a glance.
    #
    #   Row 1:  Inference latency (ms)   |  Prediction confidence (%)
    #   Row 2:  |Residual| (logit)       |  Token length (chars)
    #   Row 3:  GPU utilization (%)      |  Cost per request ($ × 0.001)
    # ======================================================================
    print("\n--- 5-ML Dashboard ---")

    DASH = {
        "title.color": "1F2937", "title.size": "12", "title.bold": "true",
        "title.font": "Helvetica Neue",
        "axisTitle.color": "6B7280", "axisTitle.size": "9",
        "axisTitle.font": "Helvetica Neue",
        "axisfont": "8:6B7280:Helvetica Neue",
        "gridlineColor": "F0F0F0",
        "plotareafill": "FFFFFF", "plotarea.border": "E5E7EB:0.75",
        "chartareafill": "F9FAFB", "chartarea.border": "E5E7EB:0.75",
        "axisline": "9CA3AF:0.75",
        "dataLabels": "false",
    }

    doc.batch([
        add_sheet("5-ML Dashboard"),
        # 1 · Inference Latency — heavy-tail, overflow-fenced, red for "watch this"
        chart("/5-ML Dashboard", title="Inference Latency · p50-p99 (ms)",
              series1=f"Latency:{LATENCY_CSV}", binSize="25", overflowBin="300",
              fill="EF4444", **{"series.shadow": "EF4444-4-45-2-25"},
              xAxisTitle="Latency (ms)", yAxisTitle="Requests", **DASH,
              x="0", y="0", width="13", height="18"),
        # 2 · Prediction Confidence — beta-like, axismin/max locked to 0..100
        chart("/5-ML Dashboard", title="Prediction Confidence",
              series1=f"Confidence:{CONFIDENCE_CSV}", binSize="5", fill="10B981",
              axismin="0", majorunit="50",
              xAxisTitle="Softmax confidence (%)", yAxisTitle="Samples", **DASH,
              x="14", y="0", width="13", height="18"),
        # 3 · Residual Magnitude — half-normal, intervalClosed=l so bin=0 catches zeros
        chart("/5-ML Dashboard", title="|Residual| · model calibration",
              series1=f"Residual:{ERROR_MAG_CSV}", binSize="0.25",
              intervalClosed="l", fill="F59E0B",
              xAxisTitle="|y - ŷ| (logit)", yAxisTitle="Samples", **DASH,
              x="0", y="19", width="13", height="18"),
        # 4 · Token Length — bimodal (short prompts vs long prompts)
        chart("/5-ML Dashboard", title="Token Length · short vs long prompts",
              series1=f"Tokens:{TOKEN_CSV}", binCount="24", fill="6366F1",
              xAxisTitle="Tokens", yAxisTitle="Requests", **DASH,
              x="14", y="19", width="13", height="18"),
        # 5 · GPU Utilization — locked axis range so dashboard charts share scale
        chart("/5-ML Dashboard", title="GPU Utilization",
              series1=f"GPU:{GPU_CSV}", binSize="5", fill="8B5CF6",
              axismin="0", axismax="50", majorunit="10",
              xAxisTitle="Utilization (%)", yAxisTitle="Samples", **DASH,
              x="0", y="38", width="13", height="18"),
        # 6 · Cost per Request — log-normal, overflow-fenced, data labels with numfmt
        chart("/5-ML Dashboard", title="Cost per Request ($ × 0.001)",
              series1=f"Cost:{COST_CSV}", binSize="5", overflowBin="120",
              fill="EC4899", dataLabels="true", **{"datalabels.numfmt": "0"},
              xAxisTitle="Cost (m$)", yAxisTitle="Requests",
              # DASH carries dataLabels=false; override it on this one chart.
              **{k: v for k, v in DASH.items() if k != "dataLabels"},
              x="14", y="38", width="13", height="18"),
    ])

    doc.send({"command": "save"})
# context exit closes the resident, flushing the workbook to disk.

print(f"\nDone! Generated: {FILE}")
print("  6 sheets, 29 histograms total")
print("  Sheet 0 (0-Hero):              1 magazine-grade full-bleed hero poster")
print("  Sheet 1 (1-Binning Lab):       6 charts — every binning knob, identical styling")
print("  Sheet 2 (2-Distribution Zoo):  6 canonical real-world distribution shapes")
print("  Sheet 3 (3-Theme Gallery):     6 design themes on the SAME dataset")
print("  Sheet 4 (4-Typography):        4 font-family type specimens")
print("  Sheet 5 (5-ML Dashboard):      6-chart Production ML Model Report")
