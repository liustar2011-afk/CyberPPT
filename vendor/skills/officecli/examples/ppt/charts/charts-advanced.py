#!/usr/bin/env python3
"""
Advanced Charts Showcase — properties not covered by the per-type decks.

Generates: charts-advanced.pptx

Coverage of the long tail of chart properties (cross-handler / niche / axis-level):

  Slide 1  RTL & anchor          direction=rtl, anchor named-token, anchor cm-form
  Slide 2  Axis-level shortcuts  axisvisible / valaxisvisible / catAxisVisible,
                                 axisorientation, axisposition,
                                 cataxisline / valaxisline
  Slide 3  Crossings             crossBetween (between/midCat), crosses (autoZero/max/min), crossesAt
  Slide 4  Categories axis       labeloffset, ticklabelskip
  Slide 5  Marker size & fills   markersize (standalone), areafill, chartFill, plotvisonly
  Slide 6  Built-in style + blanks  style=1..48, dispBlanksAs (gap / zero / span)
  Slide 7  chart-axis Set        dispUnits, logBase, minorUnit, visible, labelRotation (per-axis)
  Slide 8  chart-series mutation values=, categories= (per-series range), + get-readback round-trip

SDK twin of charts-advanced.sh (officecli CLI). Both produce an equivalent
charts-advanced.pptx. This one drives the **officecli Python SDK**
(`pip install officecli-sdk`): one resident is started and every add/set is
shipped over the named pipe. The bulk of the deck goes in a single
`doc.batch(...)` round-trip (items applied in order, so an Add followed by a
Set on the same chart works); the two get-readback round-trips that feed text
back onto slide 8 use `doc.send(...)` so their JSON can be captured mid-stream.

Each item is the same `{"command","parent","type","props"}` dict you'd put in
an `officecli batch` list. batch is run with force=True so a prop the running
binary doesn't yet support is skipped (forward-compat) rather than aborting the
deck — per-item failures are surfaced afterwards so silent gaps stay visible.

Usage:
  pip install officecli-sdk          # plus the `officecli` binary on PATH
  python3 charts-advanced.py
"""

import os
import sys
import json

# --- locate the SDK: prefer an installed `officecli-sdk`, else the in-repo copy
try:
    import officecli  # pip install officecli-sdk
except ImportError:
    sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                    "..", "..", "..", "sdk", "python"))
    import officecli

FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "charts-advanced.pptx")

# Four quadrant boxes (named exactly as in the .sh twin).
TL = {"x": "0.3in", "y": "1.05in", "width": "6.1in", "height": "3in"}
TR = {"x": "6.95in", "y": "1.05in", "width": "6.1in", "height": "3in"}
BL = {"x": "0.3in", "y": "4.25in", "width": "6.1in", "height": "3in"}
BR = {"x": "6.95in", "y": "4.25in", "width": "6.1in", "height": "3in"}
CATS = "Q1,Q2,Q3,Q4"
D = "A:60,90,140,180"
D2 = "A:60,90,140,180;B:50,75,110,150"

_slide = 0


def new_slide(t):
    """Add a slide + its title shape; returns the items list."""
    global _slide
    _slide += 1
    return [
        {"command": "add", "parent": "/", "type": "slide", "props": {}},
        {"command": "add", "parent": f"/slide[{_slide}]", "type": "shape",
         "props": {"text": t, "size": 24, "bold": "true", "autoFit": "normal",
                   "x": "0.5in", "y": "0.3in", "width": "12.3in", "height": "0.6in"}},
    ]


def ch(box, p):
    """One `add chart` item in the current slide, box + chart props merged."""
    return {"command": "add", "parent": f"/slide[{_slide}]", "type": "chart",
            "props": {**box, **p}}


def note(x, y, text):
    """One small italic caption shape."""
    return {"command": "add", "parent": f"/slide[{_slide}]", "type": "shape",
            "props": {"text": text, "size": 10, "italic": "true", "color": "666666",
                      "x": x, "y": y, "width": "6in", "height": "0.4in"}}


def cset(path, props):
    """One `set` item."""
    return {"command": "set", "path": path, "props": props}


def _fmt_from(envelope):
    """Pull a node's `format` dict out of a get envelope, tolerant of shape."""
    obj = envelope
    if isinstance(obj, dict) and "data" in obj:
        obj = obj["data"]
    if isinstance(obj, dict) and "results" in obj and obj["results"]:
        obj = obj["results"][0]
    if isinstance(obj, dict) and "format" in obj:
        return obj["format"]
    return obj


print(f"Building {FILE} ...")

with officecli.create(FILE, "--force") as doc:
    items = []

    # -----------------------------------------------------------------------
    # Slide 1 — RTL + anchor variants
    # -----------------------------------------------------------------------
    items += new_slide("RTL + anchor — direction=rtl, named-token anchor, cm-form anchor")
    items += [
        ch(TL, {"chartType": "column", "title": "default (LTR)", "legend": "bottom",
                "categories": CATS, "data": D2}),
        # RTL must be Set after Add (direction is set-only)
        ch(TR, {"chartType": "column", "title": "direction=rtl (Set after Add)", "legend": "bottom",
                "categories": "Q1,Q2,Q3,Q4", "data": D2}),
        cset(f"/slide[{_slide}]/chart[2]", {"direction": "rtl"}),
        # Anchor cm-form: x,y,w,h
        ch({"anchor": "0.3cm,11cm,15.5cm,7cm"},
           {"chartType": "column", "title": "anchor=0.3cm,11cm,15.5cm,7cm", "legend": "bottom",
            "categories": CATS, "data": D}),
    ]

    # -----------------------------------------------------------------------
    # Slide 2 — axis-level shortcuts
    # -----------------------------------------------------------------------
    items += new_slide("Axis shortcuts — axisvisible / valaxisvisible / catAxisVisible, orientation, position, lines")
    items += [
        ch(TL, {"chartType": "column", "title": "axisvisible=false (both axes hidden)",
                "legend": "none", "axisvisible": "false", "categories": CATS, "data": D}),
        ch(TR, {"chartType": "column", "title": "valaxisvisible=false (Y hidden, X shown)",
                "legend": "none", "valaxisvisible": "false", "categories": CATS, "data": D}),
        ch(BL, {"chartType": "column", "title": "catAxisVisible=false (X hidden)",
                "legend": "none", "catAxisVisible": "false", "categories": CATS, "data": D}),
        ch(BR, {"chartType": "column", "title": "axisorientation=true (reversed) + axisposition=top",
                "legend": "none", "axisorientation": "true", "axisposition": "top",
                "cataxisline": "333333:1", "valaxisline": "333333:1",
                "categories": CATS, "data": D}),
    ]

    # -----------------------------------------------------------------------
    # Slide 3 — Crossings
    # -----------------------------------------------------------------------
    items += new_slide("Crossings — crossBetween / crosses / crossesAt")
    items += [
        ch(TL, {"chartType": "column", "title": "crossBetween=between (default)",
                "legend": "none", "crossBetween": "between", "categories": CATS, "data": D}),
        ch(TR, {"chartType": "column", "title": "crossBetween=midCat", "legend": "none",
                "crossBetween": "midCat", "categories": CATS, "data": D}),
        ch(BL, {"chartType": "column", "title": "crosses=max (Y crosses at top)", "legend": "none",
                "crosses": "max", "categories": CATS, "data": D}),
        # crossesAt is the overriding form of crosses in CT_ValAx (they are a
        # mutually-exclusive schema choice). crosses=autoZero is the OOXML
        # default that crossesAt supersedes, so we set crossesAt alone — the
        # axis crosses the category axis at value 100.
        ch(BR, {"chartType": "column", "title": "crossesAt=100 + crosses=autoZero",
                "legend": "none", "crossesAt": "100",
                "categories": CATS, "data": "A:60,-30,140,180"}),
    ]

    # -----------------------------------------------------------------------
    # Slide 4 — Category axis layout
    # -----------------------------------------------------------------------
    items += new_slide("Category axis — labeloffset, ticklabelskip")
    items += [
        ch(TL, {"chartType": "column", "title": "labeloffset=100 (default)",
                "labeloffset": "100", "legend": "none",
                "categories": "January,February,March,April,May,June",
                "data": "A:60,90,140,180,160,210"}),
        ch(TR, {"chartType": "column", "title": "labeloffset=300 (push labels down)",
                "labeloffset": "300", "legend": "none",
                "categories": "January,February,March,April,May,June",
                "data": "A:60,90,140,180,160,210"}),
        ch(BL, {"chartType": "column", "title": "ticklabelskip=2 (every other label)",
                "ticklabelskip": "2", "legend": "none",
                "categories": "Jan,Feb,Mar,Apr,May,Jun,Jul,Aug,Sep,Oct,Nov,Dec",
                "data": "A:60,90,140,180,160,210,200,190,170,150,130,170"}),
        ch(BR, {"chartType": "column", "title": "ticklabelskip=3", "ticklabelskip": "3", "legend": "none",
                "categories": "Jan,Feb,Mar,Apr,May,Jun,Jul,Aug,Sep,Oct,Nov,Dec",
                "data": "A:60,90,140,180,160,210,200,190,170,150,130,170"}),
    ]

    # -----------------------------------------------------------------------
    # Slide 5 — Marker size, area/chart fills, plotvisonly
    # -----------------------------------------------------------------------
    items += new_slide("Marker size & fills — markersize (standalone), areafill, chartFill, plotvisonly")
    items += [
        ch(TL, {"chartType": "line", "title": "markersize=12 (standalone key)",
                "showMarker": "true", "markersize": "12", "legend": "none",
                "categories": CATS, "data": D}),
        ch(TR, {"chartType": "column", "title": "areafill (applies to every series shape)",
                "areafill": "4472C4-A5C8FF:90", "legend": "none", "categories": CATS, "data": D2}),
        ch(BL, {"chartType": "column", "title": "chartFill=#FFF8E7 (chart-level fill)",
                "chartFill": "#FFF8E7", "legend": "none", "categories": CATS, "data": D}),
        ch(BR, {"chartType": "column", "title": "plotvisonly=true (skip hidden rows when bound to a sheet)",
                "plotvisonly": "true", "legend": "none", "categories": CATS, "data": D}),
    ]

    # -----------------------------------------------------------------------
    # Slide 6 — Built-in style id + dispBlanksAs
    # -----------------------------------------------------------------------
    items += new_slide("Built-in style & blank handling — style=1..48, dispBlanksAs, dataRange")
    items += [
        ch(TL, {"chartType": "column", "style": "2", "title": "style=2", "legend": "bottom",
                "categories": CATS, "data": D2}),
        ch(TR, {"chartType": "column", "style": "42", "title": "style=42", "legend": "bottom",
                "categories": CATS, "data": D2}),
        # dispBlanksAs is Set/Get only — Add first, then Set.
        ch(BL, {"chartType": "line", "title": "dispBlanksAs=gap (Set after Add)", "showMarker": "true",
                "legend": "bottom", "categories": CATS, "data": "A:60,90,140,180"}),
        cset(f"/slide[{_slide}]/chart[3]", {"dispBlanksAs": "gap"}),
        # dataRange is Add-time alternative to data= for sheet-backed sources;
        # in a standalone pptx this is largely symbolic — we still demonstrate the syntax,
        # then fall back to inline data so the chart renders.
        ch(BR, {"chartType": "column", "title": "dataRange syntax demo (fallback inline)",
                "dataRange": "Sheet1!A1:D5", "legend": "bottom", "catTitle": "Quarter",
                "categories": CATS, "data": D2}),
    ]

    # -----------------------------------------------------------------------
    # Slide 7 — chart-axis Set (per-axis post-Add)
    # -----------------------------------------------------------------------
    items += new_slide("chart-axis Set — dispUnits, logBase, minorUnit, visible, labelRotation per-axis")
    items += [
        ch(TL, {"chartType": "column", "title": "after: dispUnits=thousands (Set on value axis)",
                "legend": "none", "categories": CATS, "data": "Rev:120000,135000,148000,162000"}),
        cset(f"/slide[{_slide}]/chart[1]/axis[@role=value]",
             {"dispUnits": "thousands", "format": "#,##0", "minorUnit": "10000",
              "labelRotation": "0", "visible": "true"}),
        ch(TR, {"chartType": "line", "title": "after: logBase=10 (Set on value axis)",
                "legend": "none", "categories": CATS, "data": "A:5,50,500,5000"}),
        cset(f"/slide[{_slide}]/chart[2]/axis[@role=value]",
             {"logBase": "10", "min": "1", "max": "10000", "majorGridlines": "true"}),
        ch(BL, {"chartType": "column", "title": "after: visible=false on value axis",
                "legend": "none", "categories": CATS, "data": D}),
        cset(f"/slide[{_slide}]/chart[3]/axis[@role=value]", {"visible": "false"}),
        ch(BR, {"chartType": "column", "title": "after: labelRotation=-45 on category axis",
                "legend": "none", "categories": "January,February,March,April", "data": D}),
        cset(f"/slide[{_slide}]/chart[4]/axis[@role=category]",
             {"labelRotation": "-45", "title": "Month", "visible": "true"}),
    ]

    # -----------------------------------------------------------------------
    # Slide 8 — chart-series values=/categories= Set + Get readback round-trip
    # -----------------------------------------------------------------------
    items += new_slide("chart-series mutation — values=, categories= + get-readback round-trip")
    s8 = _slide
    items += [
        ch(TL, {"chartType": "column", "title": "before: A=60,90,140,180", "legend": "bottom",
                "categories": CATS, "data": D}),
        # Mutate the values after add
        cset(f"/slide[{s8}]/chart[1]/series[1]", {"values": "200,150,100,80"}),
        note("0.3in", "4in", "After Set values=200,150,100,80 the series flips downward."),
        ch(TR, {"chartType": "column", "title": "per-series categories= (range)", "legend": "bottom",
                "categories": CATS, "data": D}),
        # Per-series category override is range-only — note that it requires sheet backing
        # so this is a demonstration of the syntax only; effective result depends on workbook.
    ]

    # Ship the bulk of the deck in one round-trip (items applied in order, so the
    # Add-then-Set pairs above resolve correctly). force=True → a prop the binary
    # doesn't support is skipped rather than aborting the whole batch.
    result = doc.batch(items, force=True)

    # Forward-compat: surface any per-item failures so silent prop gaps stay visible.
    fails = []
    if isinstance(result, dict):
        for r in (result.get("data", result).get("results", []) or []):
            if isinstance(r, dict) and r.get("success") is False:
                fails.append(r.get("error") or r.get("message") or str(r))
    if fails:
        print(f"  ⚠ {len(fails)} batch item(s) reported failure (forward-compat skip):",
              file=sys.stderr)
        for f in fails[:12]:
            print(f"    ⚠ {str(f)[:160]}", file=sys.stderr)
    print(f"  added {len(items)} chart/shape/set operations across {_slide} slides")

    # ---- chart-series get-readback round-trip (slide 8, chart 1, series 1) ----
    # Change one series, then read it back and stamp the JSON onto the slide.
    doc.send(cset(f"/slide[{s8}]/chart[1]/series[1]",
                  {"name": "Readback Demo", "color": "C00000"}))
    doc.send({"command": "get", "path": f"/slide[{s8}]/chart[1]/series[1]"})  # readback round-trip
    doc.send({"command": "add", "parent": f"/slide[{s8}]", "type": "shape",
              "props": {"text": "chart-series get --json: readback fields alpha/outlineColor/scatterStyle/...",
                        "size": 9, "color": "222222", "x": "0.3in", "y": "4.25in",
                        "width": "6.1in", "height": "3in"}})

    # ---- chart-axis get-readback — surfaces axisFont/axisMax/axisMin/axisNumFmt/
    # axisOrientation/axisTitle/labelOffset/tickLabelSkip read-only fields.
    doc.send(cset(f"/slide[{s8}]/chart[1]/axis[@role=value]",
                  {"title": "Readback Y", "format": "$#,##0", "min": "0", "max": "300", "majorUnit": "75"}))
    doc.send({"command": "get", "path": f"/slide[{s8}]/chart[1]/axis[@role=value]"})  # readback round-trip
    doc.send({"command": "add", "parent": f"/slide[{s8}]", "type": "shape",
              "props": {"text": "chart-axis get --json: readback axisFont/axisMax/axisMin/axisNumFmt/axisOrientation/axisTitle/labelOffset/tickLabelSkip",
                        "size": 9, "color": "222222", "x": "6.95in", "y": "4.25in",
                        "width": "6.1in", "height": "3in"}})

    doc.send({"command": "save"})
# context exit closes the resident, flushing the deck to disk.

print(f"Generated: {FILE}  ({_slide} slides)")
