#!/usr/bin/env python3
"""
Modern (p15) Transitions — generates transitions-modern.pptx exercising the
PowerPoint 2013+ "Exciting" / "Dynamic Content" transition presets stored as
<p15:prstTrans prst="..."/> inside an mc:AlternateContent wrapper (PowerPoint
<2013 plays the inline fade fallback).

Token spelling matches the OOXML prst attribute (lowerCamelCase): fallOver,
peelOff, pageCurlDouble, pageCurlSingle, etc. Box (covered in
transitions-shapes) uses the same element.

Direction modifier (-in / -out):
  default is -in (no invX/invY attributes written)
  -out sets invX="1" invY="1" — visually flips the transition axis on presets
  with a directional component (wind, peelOff, pageCurl*, airplane, origami,
  fallOver, drape). Symmetric presets (curtains, fracture, crush, prestige)
  accept the suffix but render unchanged.

SDK twin of transitions-modern.sh (officecli CLI). Both produce an equivalent
transitions-modern.pptx. This one drives the **officecli Python SDK**
(`pip install officecli-sdk`): one resident is started and every slide, shape,
and transition is shipped over the named pipe in a single `doc.batch(...)`
round-trip. Each item is the same `{"command","parent"/"path","type","props"}`
dict you'd put in an `officecli batch` list.

Usage:
  pip install officecli-sdk          # plus the `officecli` binary on PATH
  python3 transitions-modern.py
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

FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "transitions-modern.pptx")


print(f"Building {FILE} ...")

with officecli.create(FILE, "--force") as doc:
    items = []
    n = 0

    def add_demo_slide(trans, title, bg):
        """Append the batch items for one demo slide: a full-bleed background
        rectangle, a centred white title, and (optionally) a transition set."""
        global n
        n += 1
        # slide
        items.append({"command": "add", "parent": "/", "type": "slide", "props": {}})
        # full-bleed background rectangle
        items.append({"command": "add", "parent": f"/slide[{n}]", "type": "shape",
                       "props": {"x": "0", "y": "0", "width": "33.87cm",
                                 "height": "19.05cm", "fill": bg}})
        # centred white title
        items.append({"command": "add", "parent": f"/slide[{n}]", "type": "shape",
                       "props": {"text": title, "size": "40", "bold": "true",
                                 "color": "FFFFFF", "align": "center",
                                 "x": "2cm", "y": "7cm", "width": "29.87cm",
                                 "height": "4cm"}})
        # transition (set on the slide)
        if trans:
            items.append({"command": "set", "path": f"/slide[{n}]",
                           "props": {"transition": trans}})

    # Title slide (no transition)
    add_demo_slide("", "Modern (p15) Transitions", "1F3864")

    # Each preset's bare form (= -in)
    for t in ["fallOver", "drape", "curtains", "wind", "prestige", "fracture",
              "crush", "peelOff", "pageCurlDouble", "pageCurlSingle",
              "airplane", "origami"]:
        add_demo_slide(t, t, "2E5C8A")

    # A handful of -out variants showing the invX/invY flip on direction-sensitive presets
    for t in ["wind", "peelOff", "pageCurlDouble", "airplane", "origami", "fallOver"]:
        add_demo_slide(f"{t}-out", f"{t}-out", "8A5A2B")

    doc.batch(items)
    print(f"  added {n} slides ({len(items)} commands)")

# context exit closes the resident, flushing the presentation to disk.
print(f"Created: {FILE}")
