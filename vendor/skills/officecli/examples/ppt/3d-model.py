#!/usr/bin/env python3
"""
3D Morph Showcase — generates 3d-model.pptx: "The Sun — Our Star", an 8-slide
deck with a GLB 3D model on every slide, dark cinematic backgrounds, and a
morph transition between slides. The Sun model is repositioned/rotated slide
to slide so the morph animates a smooth orbit/spin.

SDK twin of 3d-model.sh (officecli CLI). Both produce an equivalent
3d-model.pptx. This one drives the **officecli Python SDK**
(`pip install officecli-sdk`): one resident is started and every slide, 3D
model, and text shape is shipped over the named pipe in a single
`doc.batch(...)` round-trip. Each item is the same
`{"command","parent","type","props"}` dict you'd put in an `officecli batch`
list.

Usage:
  pip install officecli-sdk          # plus the `officecli` binary on PATH
  python3 3d-model.py
"""

import os
import sys

# --- locate the SDK: prefer an installed `officecli-sdk`, else the in-repo copy
try:
    import officecli  # pip install officecli-sdk
except ImportError:
    sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                    "..", "..", "sdk", "python"))
    import officecli

DIR = os.path.dirname(os.path.abspath(__file__))
FILE = os.path.join(DIR, "3d-model.pptx")
SUN = os.path.join(DIR, "models", "sun.glb")


def slide(**props):
    """One `add slide` item in batch-shape."""
    return {"command": "add", "parent": "/", "type": "slide", "props": props}


def model(slide_idx, **props):
    """One `add 3dmodel` item on /slide[idx] in batch-shape."""
    return {"command": "add", "parent": f"/slide[{slide_idx}]",
            "type": "3dmodel", "props": {"path": SUN, "name": "sun", **props}}


def shape(slide_idx, text, **props):
    """One `add shape` (text box) item on /slide[idx] in batch-shape."""
    return {"command": "add", "parent": f"/slide[{slide_idx}]",
            "type": "shape", "props": {"text": text, **props}}


print(f"Building {FILE} ...")

with officecli.create(FILE, "--force") as doc:
    items = []

    # ====================================================================
    # SLIDES — 8 slides, dark background + morph transition
    # ====================================================================
    for _ in range(8):
        items.append(slide(background="0A0A0A", transition="morph"))

    # ====================================================================
    # 3D MODELS — Sun GLB on each slide; position/rotation drives the morph
    # ====================================================================
    items += [
        model(1, x="15cm",  y="0.5cm", width="18cm", height="18cm", rotx="10"),
        model(2, x="0.5cm", y="0.5cm", width="16cm", height="16cm", roty="50"),
        model(3, x="18cm",  y="3cm",   width="16cm", height="16cm", roty="100", rotx="15"),
        model(4, x="0.5cm", y="1cm",   width="18cm", height="18cm", roty="150"),
        model(5, x="17cm",  y="0.5cm", width="18cm", height="18cm", roty="200", rotx="20"),
        model(6, x="0.5cm", y="2cm",   width="17cm", height="17cm", roty="250"),
        model(7, x="16cm",  y="1cm",   width="17cm", height="17cm", roty="310", rotx="10"),
        model(8, x="15cm",  y="0.5cm", width="18cm", height="18cm", roty="360", rotx="10"),
    ]

    # ====================================================================
    # SLIDE 1 — Title
    # ====================================================================
    items += [
        shape(1, "THE SUN",
              x="1cm", y="2cm", w="13cm", h="3.5cm",
              size="64", bold="true", color="FF6F00", fill="00000000",
              font="Arial Black"),
        shape(1, "Our Star",
              x="1cm", y="6cm", w="13cm", h="2cm",
              size="26", color="FFB74D", fill="00000000", font="Calibri"),
        shape(1, "149.6 million km from Earth · Light takes 8 min 20 sec",
              x="1cm", y="8.5cm", w="13cm", h="2cm",
              size="18", color="9E9E9E", fill="00000000", font="Calibri"),
    ]

    # ====================================================================
    # SLIDE 2 — Star Profile
    # ====================================================================
    items += [
        shape(2, "Star Profile",
              x="18cm", y="1cm", w="15cm", h="2.5cm",
              size="40", bold="true", color="FF6F00", fill="00000000",
              font="Calibri", align="right"),
        shape(2,
              "Spectral type  G2V yellow dwarf\n"
              "Diameter  1.392 million km\n"
              "Mass  330,000x Earth\n"
              "Surface temp  5,778 K\n"
              "Core temp  15 million K\n"
              "Age  4.6 billion years",
              x="18cm", y="4cm", w="15cm", h="14cm",
              size="22", color="E0E0E0", fill="00000000",
              font="Calibri", align="right", lineSpacing="2x"),
    ]

    # ====================================================================
    # SLIDE 3 — Internal Structure
    # ====================================================================
    items += [
        shape(3, "Internal Structure",
              x="1cm", y="1cm", w="15cm", h="2.5cm",
              size="40", bold="true", color="FF6F00", fill="00000000",
              font="Calibri"),
        shape(3,
              "Core  Hydrogen fuses into helium\n"
              "Radiative zone  Photons take 170,000 years\n"
              "Convective zone  Plasma churns upward\n"
              "Photosphere  The visible \"surface\"\n"
              "Corona  Temperature mystery: millions of degrees",
              x="1cm", y="4cm", w="16cm", h="14cm",
              size="22", color="E0E0E0", fill="00000000",
              font="Calibri", lineSpacing="2x"),
    ]

    # ====================================================================
    # SLIDE 4 — Solar Activity
    # ====================================================================
    items += [
        shape(4, "Solar Activity",
              x="20cm", y="1cm", w="13cm", h="2.5cm",
              size="40", bold="true", color="FF6F00", fill="00000000",
              font="Calibri", align="right"),
        shape(4,
              "Sunspots  Cool regions twisted by magnetic fields\n"
              "Flares  Energy of a billion H-bombs in seconds\n"
              "CMEs  A billion tons of plasma ejected\n"
              "Solar wind  Particles at 400 km/s",
              x="20cm", y="4cm", w="13cm", h="14cm",
              size="22", color="E0E0E0", fill="00000000",
              font="Calibri", align="right", lineSpacing="2x"),
    ]

    # ====================================================================
    # SLIDE 5 — Source of Life
    # ====================================================================
    items += [
        shape(5, "Source of Life",
              x="1cm", y="1cm", w="14cm", h="2.5cm",
              size="40", bold="true", color="FF6F00", fill="00000000",
              font="Calibri"),
        shape(5,
              "Drives climate and water cycles\n"
              "Energy source for photosynthesis\n"
              "Magnetosphere shields from cosmic rays\n"
              "Aurora — a romantic gift from solar wind",
              x="1cm", y="4cm", w="14cm", h="14cm",
              size="22", color="E0E0E0", fill="00000000",
              font="Calibri", lineSpacing="2x"),
    ]

    # ====================================================================
    # SLIDE 6 — Observation History
    # ====================================================================
    items += [
        shape(6, "Observation History",
              x="19cm", y="1cm", w="14cm", h="2.5cm",
              size="40", bold="true", color="FF6F00", fill="00000000",
              font="Calibri", align="right"),
        shape(6,
              "1613  Galileo records sunspots\n"
              "1868  Helium discovered\n"
              "1995  SOHO satellite launched\n"
              "2018  Parker Solar Probe touches the Sun",
              x="19cm", y="4cm", w="14cm", h="14cm",
              size="22", color="E0E0E0", fill="00000000",
              font="Calibri", align="right", lineSpacing="2x"),
    ]

    # ====================================================================
    # SLIDE 7 — Future of the Sun
    # ====================================================================
    items += [
        shape(7, "Future of the Sun",
              x="1cm", y="1cm", w="14cm", h="2.5cm",
              size="40", bold="true", color="FF6F00", fill="00000000",
              font="Calibri"),
        shape(7,
              "In 5 billion years, expands into a red giant\n"
              "Swallows Mercury and Venus, scorches Earth\n"
              "Outer layers form a planetary nebula\n"
              "Core collapses into a white dwarf",
              x="1cm", y="4cm", w="14cm", h="14cm",
              size="22", color="E0E0E0", fill="00000000",
              font="Calibri", lineSpacing="2x"),
    ]

    # ====================================================================
    # SLIDE 8 — Closing
    # ====================================================================
    items += [
        shape(8, "Per Aspera Ad Astra",
              x="1cm", y="7cm", w="13cm", h="3cm",
              size="48", bold="true", italic="true", color="FF6F00",
              fill="00000000", font="Georgia"),
        shape(8, "Through hardships to the stars",
              x="1cm", y="11cm", w="13cm", h="2cm",
              size="24", color="9E9E9E", fill="00000000", font="Calibri"),
    ]

    doc.batch(items)
    print(f"  added 8 slides, 8 3D models, and the title/body text shapes")

print(f"Generated: {FILE}")
