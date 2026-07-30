#!/usr/bin/env python3
"""
Band / strip transitions — the slide reveals through parallel bands,
checkerboard squares, or diagonal strips.

Orientation modifier (-horizontal / -vertical):
  blinds, venetian (alias for blinds), checker, checkerboard (alias),
  comb, bars, randombar (alias for bars)

Corner direction (-leftup / -rightup / -leftdown / -rightdown):
  strips, diagonal (alias for strips)

Orient + in/out (BOTH must be specified for explicit form):
  split-vertical-in, split-horizontal-out, ...
  Bare 'split' rounds back as 'split'; 'split-vertical' alone now
  defaults dir=in (canonical readback: split-vertical-in).

Aliases land on the canonical token at readback time:
  checkerboard → checker, randombar → bars, diagonal → strips,
  venetian → blinds.

SDK twin of transitions-bands.sh (officecli CLI). Both produce an equivalent
transitions-bands.pptx. This one drives the **officecli Python SDK**
(`pip install officecli-sdk`): one resident is started and every slide, shape
and transition is shipped over the named pipe in a single `doc.batch(...)`
round-trip. Each item is the same `{"command","parent"/"path","type","props"}`
dict you'd put in an `officecli batch` list.

Usage:
  pip install officecli-sdk          # plus the `officecli` binary on PATH
  python3 transitions-bands.py
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

FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "transitions-bands.pptx")


print(f"Building {FILE} ...")

items = []
n = 0


def add_demo_slide(trans, title, bg):
    """Mirror the .sh add_demo_slide helper: a slide with a full-bleed
    background shape, a centred white title, and an optional transition."""
    global n
    n += 1
    # 1. the slide itself
    items.append({"command": "add", "parent": "/", "type": "slide"})
    # 2. full-bleed background rectangle
    items.append({"command": "add", "parent": f"/slide[{n}]", "type": "shape",
                  "props": {"x": "0", "y": "0", "width": "33.87cm",
                            "height": "19.05cm", "fill": bg}})
    # 3. centred white title
    items.append({"command": "add", "parent": f"/slide[{n}]", "type": "shape",
                  "props": {"text": title, "size": "40", "bold": "true",
                            "color": "FFFFFF", "align": "center",
                            "x": "2cm", "y": "7cm", "width": "29.87cm",
                            "height": "4cm"}})
    # 4. transition (set on the slide)
    if trans:
        items.append({"command": "set", "path": f"/slide[{n}]",
                      "props": {"transition": trans}})


add_demo_slide("", "Band Transitions", "1F3864")

# Orientation: vertical vs horizontal
for combo in ("blinds-horizontal", "blinds-vertical",
              "checker-horizontal", "checker-vertical",
              "comb-horizontal", "comb-vertical",
              "bars-horizontal", "bars-vertical"):
    add_demo_slide(combo, combo, "2E5C8A")

# Strips: 4 corner directions
for d in ("leftup", "rightup", "leftdown", "rightdown"):
    add_demo_slide(f"strips-{d}", f"strips-{d}", "4F7C3A")

# Split: orient × in/out matrix
for orient in ("horizontal", "vertical"):
    for io in ("in", "out"):
        add_demo_slide(f"split-{orient}-{io}", f"split-{orient}-{io}", "8A5A2B")

# Alias demo — same XML, different input spelling
add_demo_slide("venetian-vertical", "venetian-vertical (alias → blinds)", "7030A0")
add_demo_slide("checkerboard-vertical", "checkerboard-vertical (alias → checker)", "7030A0")
add_demo_slide("randombar-vertical", "randombar-vertical (alias → bars)", "7030A0")
add_demo_slide("diagonal-leftdown", "diagonal-leftdown (alias → strips)", "7030A0")


with officecli.create(FILE, "--force") as doc:
    doc.batch(items)
    print(f"  added {n} slides ({len(items)} commands)")

print(f"Generated: {FILE}")
