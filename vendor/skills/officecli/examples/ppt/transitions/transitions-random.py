#!/usr/bin/env python3
"""
Random transitions — PowerPoint picks the actual animation at render time, so
the .pptx only captures the intent, not the specific motion.

  newsflash — newspaper-style spin-and-zoom (one fixed animation, but grouped
              with the random family because it's pre-2010 legacy and rarely
              used outside this slot).
  random    — PowerPoint chooses a random transition each time you enter Slide
              Show mode.

SDK twin of transitions-random.sh (officecli CLI). Both produce an equivalent
transitions-random.pptx. This one drives the **officecli Python SDK**
(`pip install officecli-sdk`): one resident is started and every slide/shape add
plus the per-slide transition set ships over the named pipe in a single
`doc.batch(...)` round-trip. Each item is the same `{"command","parent","type",
"props"}` (or `{"command":"set","path","props"}`) dict you'd put in an `officecli
batch` list.

Usage:
  pip install officecli-sdk          # plus the `officecli` binary on PATH
  python3 transitions-random.py
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

FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "transitions-random.pptx")


def demo_slide(n, trans, title, bg):
    """One demo slide as batch items: slide + full-bleed background shape +
    centred white title; optionally set the slide transition."""
    items = [
        {"command": "add", "parent": "/", "type": "slide", "props": {}},
        {"command": "add", "parent": f"/slide[{n}]", "type": "shape",
         "props": {"x": "0", "y": "0", "width": "33.87cm", "height": "19.05cm", "fill": bg}},
        {"command": "add", "parent": f"/slide[{n}]", "type": "shape",
         "props": {"text": title, "size": "44", "bold": "true", "color": "FFFFFF",
                   "align": "center", "x": "2cm", "y": "7cm",
                   "width": "29.87cm", "height": "4cm"}},
    ]
    if trans:
        items.append({"command": "set", "path": f"/slide[{n}]",
                      "props": {"transition": trans}})
    return items


print(f"Building {FILE} ...")

with officecli.create(FILE, "--force") as doc:
    items = []
    items += demo_slide(1, "",          "Random Transitions",            "1F3864")
    items += demo_slide(2, "newsflash", "newsflash",                     "C00000")
    # Run Slide Show twice on this deck — slide 3 should animate differently each time.
    items += demo_slide(3, "random",    "random (re-rolls each play)",   "2E75B6")
    items += demo_slide(4, "random",    "random (different again)",      "7030A0")

    doc.batch(items)
    print(f"  added 4 slides ({len(items)} commands)")

    doc.send({"command": "save"})
# context exit closes the resident, flushing the deck to disk.

print(f"Generated: {FILE}")
