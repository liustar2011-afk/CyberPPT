#!/usr/bin/env python3
"""
Transition Timing — generates transitions-timing.pptx demonstrating the
slide-transition timing knobs: speed token vs millisecond duration, plus the
auto-advance / click-to-advance controls.

Speed token (legacy CT_SlideTransition @spd, PowerPoint 97+):
  fast / medium|med / slow      (e.g. fade-slow)

Duration in ms (CT_TransitionStartSoundAction @dur extLst, Office 2010+):
  integer ms                    (e.g. fade-1500 -> 1.5 seconds)

Auto-advance:
  advanceTime=<ms>     auto-advance after N milliseconds (or 'none' to clear)
  advanceClick=false   disable click-to-advance (default true, stripped from XML when true)

SDK twin of transitions-timing.sh (officecli CLI). Both produce an equivalent
transitions-timing.pptx. This one drives the **officecli Python SDK**
(`pip install officecli-sdk`): one resident is started and every slide, shape,
and transition is shipped over the named pipe in a single `doc.batch(...)`
round-trip. Each item is the same `{"command","parent","type","props"}` /
`{"command","path","props"}` dict you'd put in an `officecli batch` list.

Usage:
  pip install officecli-sdk          # plus the `officecli` binary on PATH
  python3 transitions-timing.py
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

FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "transitions-timing.pptx")


def demo_slide(n, items, trans, title, bg):
    """Append one demo slide: full-bleed background shape + centred title shape,
    then (optionally) set the slide's transition. Mirrors add_demo_slide() in
    the .sh — same shape geometry, fills, and transition token."""
    items.append({"command": "add", "parent": "/", "type": "slide", "props": {}})
    items.append({"command": "add", "parent": f"/slide[{n}]", "type": "shape",
                  "props": {"x": "0", "y": "0", "width": "33.87cm", "height": "19.05cm",
                            "fill": bg}})
    items.append({"command": "add", "parent": f"/slide[{n}]", "type": "shape",
                  "props": {"text": title, "size": "40", "bold": "true", "color": "FFFFFF",
                            "align": "center", "x": "2cm", "y": "7cm",
                            "width": "29.87cm", "height": "4cm"}})
    if trans:
        items.append({"command": "set", "path": f"/slide[{n}]", "props": {"transition": trans}})


print(f"Building {FILE} ...")

with officecli.create(FILE, "--force") as doc:
    items = []

    demo_slide(1, items, "",          "Transition Timing",           "1F3864")

    # Legacy speed tokens
    demo_slide(2, items, "fade-fast", "fade-fast (legacy @spd)",      "C00000")
    demo_slide(3, items, "fade-med",  "fade-med  (legacy @spd)",      "2E75B6")
    demo_slide(4, items, "fade-slow", "fade-slow (legacy @spd)",      "7030A0")

    # Office 2010+ duration in ms
    demo_slide(5, items, "fade-500",  "fade-500ms",                   "4F7C3A")
    demo_slide(6, items, "fade-1500", "fade-1500ms",                  "8A5A2B")
    demo_slide(7, items, "fade-3000", "fade-3000ms",                  "404040")

    # Auto-advance: slide stays for 2 seconds then advances on its own
    items.append({"command": "add", "parent": "/", "type": "slide", "props": {}})
    items.append({"command": "add", "parent": "/slide[8]", "type": "shape",
                  "props": {"x": "0", "y": "0", "width": "33.87cm", "height": "19.05cm",
                            "fill": "BF8F00"}})
    items.append({"command": "add", "parent": "/slide[8]", "type": "shape",
                  "props": {"text": "advanceTime=2000  (auto-advance after 2s)", "size": "36",
                            "bold": "true", "color": "FFFFFF", "align": "center",
                            "x": "2cm", "y": "7cm", "width": "29.87cm", "height": "4cm"}})
    items.append({"command": "set", "path": "/slide[8]",
                  "props": {"transition": "fade", "advanceTime": "2000"}})

    # Disable click-to-advance: this slide will only advance via auto-time or arrow keys
    items.append({"command": "add", "parent": "/", "type": "slide", "props": {}})
    items.append({"command": "add", "parent": "/slide[9]", "type": "shape",
                  "props": {"x": "0", "y": "0", "width": "33.87cm", "height": "19.05cm",
                            "fill": "2E5C8A"}})
    items.append({"command": "add", "parent": "/slide[9]", "type": "shape",
                  "props": {"text": "advanceClick=false  (no click advance)", "size": "36",
                            "bold": "true", "color": "FFFFFF", "align": "center",
                            "x": "2cm", "y": "7cm", "width": "29.87cm", "height": "4cm"}})
    items.append({"command": "set", "path": "/slide[9]",
                  "props": {"transition": "fade", "advanceClick": "false"}})

    doc.batch(items)
    print(f"  added 9 slides ({len(items)} commands)")

    doc.send({"command": "save"})
# context exit closes the resident, flushing the presentation to disk.

print(f"Generated: {FILE}")
