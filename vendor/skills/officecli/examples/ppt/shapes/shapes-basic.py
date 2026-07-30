#!/usr/bin/env python3
"""
Basic PowerPoint shapes — generates shapes-basic.pptx exercising the pptx
`shape` element: geometry presets, solid/gradient/pattern/image fills, line
styling (color/width/dash/caps/joins/align/arrowheads), rotation, opacity, and
shadow/glow/reflection effects.

SDK twin of shapes-basic.sh (officecli CLI). Both produce an equivalent
shapes-basic.pptx. This one drives the **officecli Python SDK**
(`pip install officecli-sdk`): one resident is started and every slide and
shape is shipped over the named pipe in a single `doc.batch(...)` round-trip.
Each item is the same `{"command","parent","type","props"}` dict you'd put in
an `officecli batch` list.

Usage:
  pip install officecli-sdk          # plus the `officecli` binary on PATH
  python3 shapes-basic.py
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

FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "shapes-basic.pptx")


def slide(**props):
    """One `add slide` item in batch-shape."""
    return {"command": "add", "parent": "/", "type": "slide", "props": props}


def shape(slide_idx, **props):
    """One `add shape` item onto /slide[slide_idx] in batch-shape."""
    return {"command": "add", "parent": f"/slide[{slide_idx}]", "type": "shape",
            "props": props}


print(f"Building {FILE} ...")

with officecli.create(FILE, "--force") as doc:
    items = []

    # ─────────────────────────────────────────────────────────────────────────
    # Slide 1 — Geometry preset gallery
    # ─────────────────────────────────────────────────────────────────────────
    items.append(slide())
    items.append(shape(1, text="Geometry Presets", size="28", bold="true",
                       x="0.5in", y="0.3in", width="12in", height="0.6in"))

    # Row of 8 shapes, one per supported preset.
    # Schema-declared presets: rect, roundRect, ellipse, triangle, diamond,
    # parallelogram, rightArrow, star5
    presets = ["rect", "roundRect", "ellipse", "triangle", "diamond",
               "parallelogram", "rightArrow", "star5"]
    for col, preset in enumerate(presets):
        x = 0.5 + col * 1.55
        items.append(shape(1, geometry=preset,
                           x=f"{x}in", y="1.5in", width="1.3in", height="1.3in",
                           fill="4472C4", color="FFFFFF",
                           text=preset, size="11", bold="true"))

    # ─────────────────────────────────────────────────────────────────────────
    # Slide 2 — Fill variations on the same geometry
    # ─────────────────────────────────────────────────────────────────────────
    items.append(slide())
    items.append(shape(2, text="Fill Variations", size="28", bold="true",
                       x="0.5in", y="0.3in", width="12in", height="0.6in"))

    # Solid hex
    items.append(shape(2, geometry="roundRect",
                       x="0.5in", y="1.3in", width="2.5in", height="1.5in",
                       fill="E63946", color="FFFFFF", bold="true",
                       text="fill=E63946"))
    # Theme color (follows deck theme)
    items.append(shape(2, geometry="roundRect",
                       x="3.3in", y="1.3in", width="2.5in", height="1.5in",
                       fill="accent2", color="FFFFFF", bold="true",
                       text="fill=accent2"))
    # Linear gradient (color1-color2-angle)
    items.append(shape(2, geometry="roundRect",
                       x="6.1in", y="1.3in", width="2.5in", height="1.5in",
                       gradient="FF6B6B-4ECDC4-45", color="FFFFFF", bold="true",
                       text="gradient linear 45°"))
    # Radial gradient
    items.append(shape(2, geometry="roundRect",
                       x="8.9in", y="1.3in", width="2.5in", height="1.5in",
                       gradient="radial:FFE66D-FF6B35-center", color="000000",
                       bold="true", text="gradient radial"))
    # Pattern (preset:fg:bg)
    items.append(shape(2, geometry="roundRect",
                       x="0.5in", y="3.1in", width="2.5in", height="1.5in",
                       pattern="diagBrick:1D3557:F1FAEE", color="FFFFFF",
                       bold="true", text="pattern diagBrick"))
    # Opacity (requires a fill to attach to)
    items.append(shape(2, geometry="roundRect",
                       x="3.3in", y="3.1in", width="2.5in", height="1.5in",
                       fill="2A9D8F", opacity="0.4", color="000000", bold="true",
                       text="fill + opacity=0.4"))
    # No fill (outline only)
    items.append(shape(2, geometry="roundRect",
                       x="6.1in", y="3.1in", width="2.5in", height="1.5in",
                       fill="none", line="264653:2.5:solid", color="264653",
                       bold="true", text="fill=none + outline"))
    # Per-stop gradient positions
    items.append(shape(2, geometry="roundRect",
                       x="8.9in", y="3.1in", width="2.5in", height="1.5in",
                       gradient="FF0000@0-FFD700@40-0000FF@100", color="FFFFFF",
                       bold="true", text="gradient per-stop"))

    # ─────────────────────────────────────────────────────────────────────────
    # Slide 3 — Outline styling (line color / width / dash / caps / arrowheads)
    # ─────────────────────────────────────────────────────────────────────────
    items.append(slide())
    items.append(shape(3, text="Outline Styling", size="28", bold="true",
                       x="0.5in", y="0.3in", width="12in", height="0.6in"))

    # Compound line form: color:width:dash
    items.append(shape(3, geometry="rect",
                       x="0.5in", y="1.3in", width="3in", height="1.2in",
                       fill="none", line="E63946:3:solid",
                       text='line="E63946:3:solid"', size="12"))
    items.append(shape(3, geometry="rect",
                       x="4in", y="1.3in", width="3in", height="1.2in",
                       fill="none", line="1D3557:2:dash",
                       text='line="1D3557:2:dash"', size="12"))
    items.append(shape(3, geometry="rect",
                       x="7.5in", y="1.3in", width="3in", height="1.2in",
                       fill="none", line="2A9D8F:2.5:dashDot",
                       text='line="2A9D8F:2.5:dashDot"', size="12"))

    # Per-attribute form: lineColor + lineWidth + lineDash
    items.append(shape(3, geometry="ellipse",
                       x="0.5in", y="2.9in", width="3in", height="1.4in",
                       fill="FFE66D", lineColor="E63946", lineWidth="4pt",
                       lineDash="solid",
                       text="separate lineColor/lineWidth/lineDash", size="11"))
    # Compound stroke (cmpd=dbl → double line)
    items.append(shape(3, geometry="ellipse",
                       x="4in", y="2.9in", width="3in", height="1.4in",
                       fill="A8DADC", lineColor="1D3557", lineWidth="6pt",
                       cmpd="dbl", text="cmpd=dbl (double stroke)", size="11"))
    # Triple stroke
    items.append(shape(3, geometry="ellipse",
                       x="7.5in", y="2.9in", width="3in", height="1.4in",
                       fill="A8DADC", lineColor="1D3557", lineWidth="8pt",
                       cmpd="tri", text="cmpd=tri (triple stroke)", size="11"))

    # Arrowheads on shape outlines (demo headEnd/tailEnd here)
    items.append(shape(3,
                       text="headEnd / tailEnd work on any outline (not just connectors):",
                       size="12",
                       x="0.5in", y="4.7in", width="12in", height="0.4in"))
    items.append(shape(3, geometry="rect",
                       x="0.5in", y="5.2in", width="4in", height="0.05in",
                       fill="none", lineColor="000000", lineWidth="2pt",
                       headEnd="triangle", tailEnd="arrow"))
    items.append(shape(3, geometry="rect",
                       x="5in", y="5.2in", width="4in", height="0.05in",
                       fill="none", lineColor="000000", lineWidth="2pt",
                       headEnd="diamond", tailEnd="oval"))

    # ─────────────────────────────────────────────────────────────────────────
    # Slide 4 — Rotation, shadow effect, z-order via add order
    # ─────────────────────────────────────────────────────────────────────────
    items.append(slide())
    items.append(shape(4, text="Rotation + Effects", size="28", bold="true",
                       x="0.5in", y="0.3in", width="12in", height="0.6in"))

    # Rotation in degrees (0..360)
    for col, r in enumerate([0, 30, 60, 90, 135, 180, 225, 270]):
        x = 0.5 + col * 1.55
        items.append(shape(4, geometry="rightArrow",
                           x=f"{x}in", y="1.3in", width="1.4in", height="0.8in",
                           fill="4472C4", color="FFFFFF", bold="true",
                           rotation=str(r), text=f"{r}°", size="11"))

    # Shadow effect: shadow=color:blur:offset:direction (compound effect)
    items.append(shape(4, geometry="roundRect",
                       x="1in", y="3in", width="3.5in", height="1.8in",
                       fill="E63946", color="FFFFFF", bold="true", size="14",
                       text="shadow=000000", shadow="000000"))
    items.append(shape(4, geometry="roundRect",
                       x="5.5in", y="3in", width="3.5in", height="1.8in",
                       fill="2A9D8F", color="FFFFFF", bold="true", size="14",
                       text="glow=FFD700", glow="FFD700"))
    items.append(shape(4, geometry="roundRect",
                       x="10in", y="3in", width="3in", height="1.8in",
                       fill="F4A261", color="000000", bold="true", size="14",
                       text="reflection=tight", reflection="tight"))

    # ─────────────────────────────────────────────────────────────────────────
    # Slide 5 — Stroke geometry details (lineCap / lineJoin / lineAlign)
    # ─────────────────────────────────────────────────────────────────────────
    items.append(slide())
    items.append(shape(5,
                       text="Stroke Geometry — lineCap / lineJoin / lineAlign",
                       size="28", bold="true",
                       x="0.5in", y="0.3in", width="12in", height="0.6in"))

    # lineCap — how the stroke terminates at endpoints / dash gaps.
    # Most visible with a thick dashed stroke.
    x = 0.5
    for cap in ["flat", "round", "square"]:
        items.append(shape(5, geometry="rect",
                           x=f"{x}in", y="1.5in", width="4in", height="0.05in",
                           fill="none", lineColor="1D3557", lineWidth="10pt",
                           lineDash="dash", lineCap=cap))
        items.append(shape(5, text=f"lineCap={cap}", size="12",
                           x=f"{x}in", y="1.8in", width="4in", height="0.4in",
                           fill="none", line="000000:0:solid"))
        x += 4.3

    # lineJoin — corner style on a stroked shape.
    # Most visible on a triangle outline with thick lines.
    x = 0.5
    for join in ["round", "bevel", "miter"]:
        items.append(shape(5, geometry="triangle",
                           x=f"{x}in", y="2.8in", width="2.5in", height="2in",
                           fill="A8DADC", lineColor="E63946", lineWidth="12pt",
                           lineJoin=join))
        items.append(shape(5, text=f"lineJoin={join}", size="12",
                           x=f"{x}in", y="4.9in", width="2.5in", height="0.4in",
                           fill="none", line="000000:0:solid"))
        x += 3

    # miterLimit — caps how far a miter join's spike extends before clipping.
    # Expressed in 1/1000ths of a percent; 800000 = 800%. Supplied as the
    # compound lineJoin=miter:<lim> form which sets both join + limit at once.
    items.append(shape(5, geometry="triangle",
                       x="0.5in", y="5.1in", width="2.5in", height="1.6in",
                       fill="A8DADC", lineColor="E63946", lineWidth="8pt",
                       lineJoin="miter:800000"))
    items.append(shape(5, text='lineJoin="miter:800000"  (limit 800%)', size="12",
                       x="0.5in", y="6.9in", width="4in", height="0.4in",
                       fill="none", line="000000:0:solid"))

    # lineAlign — stroke alignment relative to the path: ctr (centered) vs in.
    # Same shape, same border width, only the alignment of the stroke differs.
    x = 8.9
    for algn in ["ctr", "in"]:
        items.append(shape(5, geometry="rect",
                           x=f"{x}in", y="2.8in", width="1.9in", height="2in",
                           fill="F4A261", lineColor="1D3557", lineWidth="12pt",
                           lineAlign=algn))
        items.append(shape(5, text=f"lineAlign={algn}", size="12",
                           x=f"{x}in", y="4.9in", width="2in", height="0.4in",
                           fill="none", line="000000:0:solid"))
        x += 2.1

    doc.batch(items)
    print(f"  added {len(items)} slides/shapes")

    doc.send({"command": "save"})
# context exit closes the resident, flushing the deck to disk.

print(f"Generated: {FILE}")
