#!/usr/bin/env python3
"""
Basic slide transitions — cut, fade, dissolve, flash, and the 'none' clear.
These five tokens form the everyday transition vocabulary: cut = instant,
fade = pixel cross-fade, dissolve = pixel-noise dissolve, flash = white
flash-through, none = remove an existing transition.

Each demo slide carries the transition that triggers AS THE SLIDE ENTERS
(replacing the previous one). To experience them, open the .pptx and step
through Slide Show mode — most differences only show in playback.

SDK twin of transitions-basic.sh (officecli CLI). Both produce an equivalent
transitions-basic.pptx. This one drives the **officecli Python SDK**
(`pip install officecli-sdk`): one resident is started and every slide, shape,
and transition is shipped over the named pipe in a single `doc.batch(...)`
round-trip. Each item is the same `{"command","parent"/"path","type","props"}`
dict you'd put in an `officecli batch` list.

Usage:
  pip install officecli-sdk          # plus the `officecli` binary on PATH
  python3 transitions-basic.py
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

FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "transitions-basic.pptx")


def demo_slide(n, trans, title, bg):
    """Batch items for one demo slide: a full-bleed background shape, a centred
    title shape, and (when non-empty) the slide-level transition. Mirrors the
    add_demo_slide() shell function command-for-command."""
    items = [
        {"command": "add", "parent": "/", "type": "slide", "props": {}},
        {"command": "add", "parent": f"/slide[{n}]", "type": "shape",
         "props": {"x": "0", "y": "0", "width": "33.87cm", "height": "19.05cm",
                   "fill": bg}},
        {"command": "add", "parent": f"/slide[{n}]", "type": "shape",
         "props": {"text": title, "size": "54", "bold": "true", "color": "FFFFFF",
                   "align": "center",
                   "x": "2cm", "y": "7cm", "width": "29.87cm", "height": "4cm"}},
    ]
    if trans:
        items.append({"command": "set", "path": f"/slide[{n}]",
                      "props": {"transition": trans}})
    return items


print(f"Building {FILE} ...")

with officecli.create(FILE, "--force") as doc:
    items = []
    items += demo_slide(1, "",         "Basic Transitions",         "1F3864")
    items += demo_slide(2, "cut",      "cut — instant swap",        "C00000")
    items += demo_slide(3, "fade",     "fade — pixel cross-fade",   "2E75B6")
    items += demo_slide(4, "dissolve", "dissolve — speckle blend",  "7030A0")
    items += demo_slide(5, "flash",    "flash — white flash-thru",  "BF8F00")

    # Demonstrate the 'none' clear: slide 6 first gets fade, then we wipe it.
    # Final readback on slide 6 should NOT have a transition key at all.
    items += demo_slide(6, "fade",     "none — fade cleared",       "404040")
    items.append({"command": "set", "path": "/slide[6]",
                  "props": {"transition": "none"}})

    doc.batch(items)
    print(f"  shipped {len(items)} commands")

    doc.send({"command": "save"})
# context exit closes the resident, flushing the presentation to disk.

print(f"Created: {FILE}")
