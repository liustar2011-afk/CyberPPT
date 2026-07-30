#!/usr/bin/env python3
"""
3D / dynamic transitions — PowerPoint 2010+ "Exciting" gallery. Each requires
Office 2010+ to render; older PowerPoint silently falls back to fade (officecli
emits an mc:AlternateContent wrapper with that fallback baked in).

Direction families:
  left/right (LeftRightDir):  switch, flip, ferris, gallery, conveyor, reveal
  in/out     (InOutDir):      shred, flythrough, warp
  up/down/left/right          (SlideDir):  vortex, glitter, pan, prism
  horizontal/vertical:        doors, window
  no direction:               ripple, honeycomb

SDK twin of transitions-dynamic.sh (officecli CLI). Both produce an equivalent
transitions-dynamic.pptx. This one drives the **officecli Python SDK**
(`pip install officecli-sdk`): one resident is started and every slide, shape,
and transition is shipped over the named pipe in a single `doc.batch(...)`
round-trip. Each item is the same `{"command","parent"/"path","type","props"}`
dict you'd put in an `officecli batch` list.

Usage:
  pip install officecli-sdk          # plus the `officecli` binary on PATH
  python3 transitions-dynamic.py
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

FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "transitions-dynamic.pptx")


print(f"Building {FILE} ...")

items = []


def add_demo_slide(trans, title, bg):
    """One demo slide: blank slide + full-bleed background shape + centred white
    title, then (optionally) a transition set on the slide. Mirrors
    add_demo_slide() in transitions-dynamic.sh — same parent paths and props."""
    n = sum(1 for it in items if it["command"] == "add" and it["parent"] == "/") + 1
    items.append({"command": "add", "parent": "/", "type": "slide", "props": {}})
    items.append({"command": "add", "parent": f"/slide[{n}]", "type": "shape",
                  "props": {"x": "0", "y": "0", "width": "33.87cm", "height": "19.05cm",
                            "fill": bg}})
    items.append({"command": "add", "parent": f"/slide[{n}]", "type": "shape",
                  "props": {"text": title, "size": "40", "bold": "true",
                            "color": "FFFFFF", "align": "center",
                            "x": "2cm", "y": "7cm", "width": "29.87cm", "height": "4cm"}})
    if trans:
        items.append({"command": "set", "path": f"/slide[{n}]",
                      "props": {"transition": trans}})


with officecli.create(FILE, "--force") as doc:
    add_demo_slide("", "Dynamic Transitions", "1F3864")

    # LeftRight family
    for t in ["switch", "flip", "ferris", "gallery", "conveyor", "reveal"]:
        add_demo_slide(f"{t}-right", f"{t}-right", "2E5C8A")

    # InOut family
    for t in ["shred", "flythrough", "warp"]:
        add_demo_slide(f"{t}-out", f"{t}-out", "4F7C3A")

    # SlideDir family — 4 cardinal (prism is direction-less; see PrismFamily below)
    for t in ["vortex", "glitter", "pan"]:
        for d in ["up", "right"]:
            add_demo_slide(f"{t}-{d}", f"{t}-{d}", "8A5A2B")

    # Prism family — same <p14:prism> element, 3 UI tiles via isContent/isInverted:
    #   prism / cube (alias)               -> "Cube"   (Exciting)
    #   rotate (isContent=1)               -> "Rotate" (Dynamic Content)
    #   orbit  (isContent=1 isInverted=1)  -> "Orbit"  (Dynamic Content)
    add_demo_slide("prism", "prism (== Cube in UI)", "6E3B23")
    add_demo_slide("rotate", "rotate", "6E3B23")
    add_demo_slide("orbit", "orbit", "6E3B23")

    # Horizontal/vertical orientation
    for t in ["doors", "window"]:
        for d in ["horizontal", "vertical"]:
            add_demo_slide(f"{t}-{d}", f"{t}-{d}", "7030A0")

    # Direction-less
    for t in ["ripple", "honeycomb"]:
        add_demo_slide(t, t, "C00000")

    doc.batch(items)
    slides = sum(1 for it in items if it["command"] == "add" and it["parent"] == "/")
    print(f"  added {slides} slides ({len(items)} commands)")

    doc.send({"command": "save"})
# context exit closes the resident, flushing the presentation to disk.

print(f"Generated: {FILE}")
