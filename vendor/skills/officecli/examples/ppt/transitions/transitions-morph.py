#!/usr/bin/env python3
"""
Morph transition — PowerPoint 2016+ smooth tweening between two slides that
share named objects. Same shape on adjacent slides with different
x/y/width/height/rotation is interpolated as continuous motion.

Morph option (transition=morph / morph-byword / morph-bychar):
  morph (byobject, default) — shapes with matching IDs are paired and tweened
  morph-byword              — text body is morphed word-by-word
  morph-bychar              — text body is morphed character-by-character

This trio is a starter demo. For a fuller scene-level showcase see
examples/product_launch_morph.pptx in the repo root.

SDK twin of transitions-morph.sh (officecli CLI). Both produce an equivalent
transitions-morph.pptx. This one drives the **officecli Python SDK**
(`pip install officecli-sdk`): one resident is started and every slide, shape
and transition is shipped over the named pipe in a single `doc.batch(...)`
round-trip. Each item is the same `{"command","parent"/"path","type","props"}`
dict you'd put in an `officecli batch` list.

Usage:
  pip install officecli-sdk          # plus the `officecli` binary on PATH
  python3 transitions-morph.py
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

FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "transitions-morph.pptx")


def slide():
    """One `add slide` item in batch-shape."""
    return {"command": "add", "parent": "/", "type": "slide"}


def shape(parent, **props):
    """One `add shape` item in batch-shape."""
    return {"command": "add", "parent": parent, "type": "shape", "props": props}


def transition(path, kind):
    """One `set` item applying a slide transition in batch-shape."""
    return {"command": "set", "path": path, "props": {"transition": kind}}


print(f"Building {FILE} ...")

with officecli.create(FILE, "--force") as doc:
    items = [
        # Slide 1: starting state (no transition — this is the entry point).
        slide(),
        shape("/slide[1]", x="0", y="0", width="33.87cm", height="19.05cm", fill="1F3864"),
        shape("/slide[1]", text="Morph", size="72", bold="true", color="FFFFFF", align="center",
              x="2cm", y="7cm", width="29.87cm", height="4cm"),
        # A named circle that will tween across slides 2/3/4.
        shape("/slide[1]", shape="ellipse", fill="FFC000", name="morphBall",
              x="2cm", y="14cm", width="3cm", height="3cm"),

        # Slide 2: morph-byobject — same-named ball moves right and grows.
        slide(),
        transition("/slide[2]", "morph"),
        shape("/slide[2]", x="0", y="0", width="33.87cm", height="19.05cm", fill="2E5C8A"),
        shape("/slide[2]", text="morph (byobject — default)", size="44", bold="true",
              color="FFFFFF", align="center",
              x="2cm", y="2cm", width="29.87cm", height="3cm"),
        shape("/slide[2]", shape="ellipse", fill="FFC000", name="morphBall",
              x="15cm", y="10cm", width="6cm", height="6cm"),

        # Slide 3: morph-byword — title text recomposes word-by-word.
        slide(),
        transition("/slide[3]", "morph-byword"),
        shape("/slide[3]", x="0", y="0", width="33.87cm", height="19.05cm", fill="4F7C3A"),
        shape("/slide[3]", text="morph byword tweens words", size="44", bold="true",
              color="FFFFFF", align="center",
              x="2cm", y="2cm", width="29.87cm", height="3cm"),
        shape("/slide[3]", shape="ellipse", fill="FFC000", name="morphBall",
              x="27cm", y="14cm", width="3cm", height="3cm"),

        # Slide 4: morph-bychar — recomposes letter-by-letter.
        slide(),
        transition("/slide[4]", "morph-bychar"),
        shape("/slide[4]", x="0", y="0", width="33.87cm", height="19.05cm", fill="8A5A2B"),
        shape("/slide[4]", text="bychar tweens letters", size="44", bold="true",
              color="FFFFFF", align="center",
              x="2cm", y="2cm", width="29.87cm", height="3cm"),
        shape("/slide[4]", shape="ellipse", fill="FFC000", name="morphBall",
              x="14cm", y="14cm", width="4cm", height="4cm"),
    ]

    doc.batch(items)
    print(f"  added {len(items)} slides/shapes/transitions")

print(f"Generated: {FILE}")
