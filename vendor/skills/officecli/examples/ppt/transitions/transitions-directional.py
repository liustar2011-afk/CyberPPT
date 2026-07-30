#!/usr/bin/env python3
"""
Directional transitions — push, cover, uncover/pull, wipe.

Direction support is NOT uniform across the family:
  - push:           up/down/left/right                       (4 dirs)
  - wipe:           up/down/left/right                       (4 dirs)
  - cover/uncover:  up/down/left/right + leftup/rightup/
                    leftdown/rightdown                       (8 dirs)
  - pull:           alias for uncover                        (same 8 dirs)

Mismatching the family/direction triggers an OOXML schema-level error
from officecli (e.g. 'push-leftup' is rejected — push only supports the
four cardinal directions). See transitions-basic for the no-direction
transitions (cut/fade/dissolve/flash).

SDK twin of transitions-directional.sh (officecli CLI). Both produce an
equivalent transitions-directional.pptx. This one drives the **officecli
Python SDK** (`pip install officecli-sdk`): one resident is started and
every slide/shape/transition is shipped over the named pipe in a single
`doc.batch(...)` round-trip. Each item is the same
`{"command","parent","type","props"}` / `{"command","path","props"}` dict
you'd put in an `officecli batch` list.

Usage:
  pip install officecli-sdk          # plus the `officecli` binary on PATH
  python3 transitions-directional.py
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

FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "transitions-directional.pptx")


def demo_slide(items, n, trans, title, bg):
    """Append the batch items for one demo slide: slide + full-bleed background
    shape + centred white title, then optionally set its transition."""
    items.append({"command": "add", "parent": "/", "type": "slide", "props": {}})
    items.append({"command": "add", "parent": f"/slide[{n}]", "type": "shape",
                  "props": {"x": "0", "y": "0", "width": "33.87cm", "height": "19.05cm",
                            "fill": bg}})
    items.append({"command": "add", "parent": f"/slide[{n}]", "type": "shape",
                  "props": {"text": title, "size": "44", "bold": "true", "color": "FFFFFF",
                            "align": "center", "x": "2cm", "y": "7cm",
                            "width": "29.87cm", "height": "4cm"}})
    if trans:
        items.append({"command": "set", "path": f"/slide[{n}]", "props": {"transition": trans}})


print(f"Building {FILE} ...")

with officecli.create(FILE, "--force") as doc:
    items = []
    n = 0

    def add_demo_slide(trans, title, bg):
        global n
        n += 1
        demo_slide(items, n, trans, title, bg)

    add_demo_slide("", "Directional Transitions", "1F3864")

    # push: 4 cardinal directions
    for d in ["up", "down", "left", "right"]:
        add_demo_slide(f"push-{d}", f"push-{d}", "2E5C8A")

    # wipe: 4 cardinal directions
    for d in ["up", "down", "left", "right"]:
        add_demo_slide(f"wipe-{d}", f"wipe-{d}", "4F7C3A")

    # cover: 8 directions (4 cardinal + 4 diagonal corner)
    for d in ["up", "down", "left", "right", "leftup", "rightup", "leftdown", "rightdown"]:
        add_demo_slide(f"cover-{d}", f"cover-{d}", "8A5A2B")

    # uncover (a.k.a. pull): 8 directions
    for d in ["up", "down", "left", "right", "leftup", "rightup", "leftdown", "rightdown"]:
        add_demo_slide(f"uncover-{d}", f"uncover-{d}", "7030A0")

    doc.batch(items)
    print(f"  added {n} slides")

print(f"Created: {FILE}")
