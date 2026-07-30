#!/usr/bin/env python3
"""
Shape-mask transitions — generates transitions-shapes.pptx, where the new slide
reveals through a growing geometric mask cut into the old slide. OOXML calls
these CT_OptionalBlackTransition.

  Direction-less (NO -in/-out suffix; officecli rejects one):
    circle, diamond, plus, wedge
  Direction-ful (-in / -out):
    box, zoom
  Spoke-count (wheel-N where N = number of spokes, 1..8 typical):
    wheel-1, wheel-2, wheel-3, wheel-4 (default), wheel-8

Box is stored as PowerPoint 2013+ `<p15:prstTrans prst="box">` inside
mc:AlternateContent (older PowerPoint plays the fallback fade). `box-in` is the
default (no invX/invY); `box-out` flips both invX and invY.

SDK twin of transitions-shapes.sh (officecli CLI). Both produce an equivalent
transitions-shapes.pptx. This one drives the **officecli Python SDK**
(`pip install officecli-sdk`): one resident is started and every slide, shape
and transition is shipped over the named pipe in a single `doc.batch(...)`
round-trip. Each item is the same `{"command","parent"/"path","type","props"}`
dict you'd put in an `officecli batch` list.

Usage:
  pip install officecli-sdk          # plus the `officecli` binary on PATH
  python3 transitions-shapes.py
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

FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "transitions-shapes.pptx")

# 33.87cm x 19.05cm = a 16:9 slide canvas; the title sits centred in the middle.
items = []
n = 0


def add_demo_slide(trans, title, bg):
    """Replays the shell's add_demo_slide(): a full-bleed colour shape, a centred
    white title, and (optionally) a slide-level transition set."""
    global n
    n += 1
    # 1) new slide
    items.append({"command": "add", "parent": "/", "type": "slide"})
    # 2) full-bleed background rectangle
    items.append({"command": "add", "parent": f"/slide[{n}]", "type": "shape",
                  "props": {"x": "0", "y": "0", "width": "33.87cm",
                            "height": "19.05cm", "fill": bg}})
    # 3) centred white title
    items.append({"command": "add", "parent": f"/slide[{n}]", "type": "shape",
                  "props": {"text": title, "size": "44", "bold": "true",
                            "color": "FFFFFF", "align": "center",
                            "x": "2cm", "y": "7cm", "width": "29.87cm",
                            "height": "4cm"}})
    # 4) slide-level transition (skipped for the empty-trans cover slide)
    if trans:
        items.append({"command": "set", "path": f"/slide[{n}]",
                      "props": {"transition": trans}})


add_demo_slide("", "Shape Transitions", "1F3864")

# Direction-less geometric masks
for t in ["circle", "diamond", "plus", "wedge"]:
    add_demo_slide(t, t, "C00000")

# In/out direction masks
for combo in ["zoom-in", "zoom-out", "box-in", "box-out"]:
    add_demo_slide(combo, combo, "2E75B6")

# Wheel spokes: same shape, different spoke count
for n_spokes in [1, 2, 3, 4, 8]:
    add_demo_slide(f"wheel-{n_spokes}", f"wheel-{n_spokes} ({n_spokes} spokes)", "7030A0")


print(f"Building {FILE} ...")

with officecli.create(FILE, "--force") as doc:
    doc.batch(items)
    print(f"  added {n} slides ({len(items)} commands)")

print(f"Generated: {FILE}")
