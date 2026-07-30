#!/usr/bin/env python3
"""
Shape effects and meta — generates shapes-effects.pptx exercising the pptx shape
props NOT touched by shapes-basic / shapes-connectors / textboxes-basic:
autoFit, flipH/flipV (mirror), image= (picture as shape fill / blipFill), 3D
(bevel / bevelBottom / depth / lighting / material), softEdge, link + tooltip,
name override, and zorder stacking.

SDK twin of shapes-effects.sh (officecli CLI). Both produce an equivalent
shapes-effects.pptx. This one drives the **officecli Python SDK**
(`pip install officecli-sdk`): one resident is started and every slide / shape /
textbox is shipped over the named pipe in a single `doc.batch(...)` round-trip.
Each item is the same `{"command","parent","type","props"}` dict you'd put in an
`officecli batch` list.

A tiny 64x64 magenta+yellow checker PNG is synthesized on the fly (pure stdlib,
no document command) for the image-fill demo, exactly as the .sh does.

Usage:
  pip install officecli-sdk          # plus the `officecli` binary on PATH
  python3 shapes-effects.py
"""

import os
import struct
import sys
import zlib

# --- locate the SDK: prefer an installed `officecli-sdk`, else the in-repo copy
try:
    import officecli  # pip install officecli-sdk
except ImportError:
    sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                    "..", "..", "..", "sdk", "python"))
    import officecli

FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "shapes-effects.pptx")

LONGTEXT = ("Lorem ipsum dolor sit amet, consectetur adipiscing elit. Sed do "
            "eiusmod tempor incididunt ut labore et dolore magna aliqua. Ut "
            "enim ad minim veniam, quis nostrud exercitation ullamco laboris.")


def make_sample_png(path):
    """Write a 64x64 magenta+yellow 16px checker PNG (pure stdlib, no deps)."""
    W = H = 64
    rows = []
    for y in range(H):
        row = b"\x00"
        for x in range(W):
            cell = (x // 16 + y // 16) & 1
            row += (b"\xE6\x39\x46" if cell else b"\xFF\xE6\x6D")
        rows.append(row)
    raw = b"".join(rows)

    def chunk(t, d):
        return struct.pack(">I", len(d)) + t + d + struct.pack(
            ">I", zlib.crc32(t + d) & 0xffffffff)

    png = b"\x89PNG\r\n\x1a\n"
    png += chunk(b"IHDR", struct.pack(">IIBBBBB", W, H, 8, 2, 0, 0, 0))
    png += chunk(b"IDAT", zlib.compress(raw))
    png += chunk(b"IEND", b"")
    with open(path, "wb") as f:
        f.write(png)


def slide():
    """One `add slide` item in batch-shape."""
    return {"command": "add", "parent": "/", "type": "slide", "props": {}}


def textbox(sl, **props):
    """One `add textbox` item on slide `sl` in batch-shape."""
    return {"command": "add", "parent": f"/slide[{sl}]", "type": "textbox", "props": props}


def shape(sl, **props):
    """One `add shape` item on slide `sl` in batch-shape."""
    return {"command": "add", "parent": f"/slide[{sl}]", "type": "shape", "props": props}


SAMPLE_PNG = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".shapes-effects-fill.png")
make_sample_png(SAMPLE_PNG)

print(f"Building {FILE} ...")

try:
    with officecli.create(FILE, "--force") as doc:
        items = [
            # ============================================================
            # Slide 1 — autoFit (text overflow behavior)
            # ============================================================
            slide(),
            textbox(1, text="autoFit — text overflow behavior", size="28", bold="true",
                    x="0.5in", y="0.3in", width="12in", height="0.6in"),
            # 'none' — text just overflows the box
            textbox(1, x="0.5in", y="1.5in", width="4in", height="1.5in",
                    fill="F1FAEE", size="18", text=LONGTEXT, autoFit="none"),
            textbox(1, text="autoFit=none  (overflows)", size="12", italic="true",
                    x="0.5in", y="3.2in", width="4in", height="0.4in"),
            # 'normal' — shrinks text to fit
            textbox(1, x="5in", y="1.5in", width="4in", height="1.5in",
                    fill="A8DADC", size="18", text=LONGTEXT, autoFit="normal"),
            textbox(1, text="autoFit=normal  (text shrinks)", size="12", italic="true",
                    x="5in", y="3.2in", width="4in", height="0.4in"),
            # 'shape' — box resizes to fit text
            textbox(1, x="9.5in", y="1.5in", width="4in", height="1.5in",
                    fill="F4A261", size="18", text=LONGTEXT, autoFit="shape"),
            textbox(1, text="autoFit=shape  (box grows)", size="12", italic="true",
                    x="9.5in", y="4.5in", width="4in", height="0.4in"),

            # ============================================================
            # Slide 2 — flipH / flipV (mirror)
            # ============================================================
            slide(),
            textbox(2, text="flipH / flipV — mirror", size="28", bold="true",
                    x="0.5in", y="0.3in", width="12in", height="0.6in"),
            # Original
            shape(2, geometry="rightArrow", x="0.5in", y="2in", width="2.8in", height="1.5in",
                  fill="4472C4", color="FFFFFF", bold="true", text="original"),
            # flipH
            shape(2, geometry="rightArrow", x="4in", y="2in", width="2.8in", height="1.5in",
                  fill="E63946", color="FFFFFF", bold="true", text="flipH=true", flipH="true"),
            # flipV
            shape(2, geometry="rightArrow", x="7.5in", y="2in", width="2.8in", height="1.5in",
                  fill="2A9D8F", color="FFFFFF", bold="true", text="flipV=true", flipV="true"),
            # flipH + flipV
            shape(2, geometry="rightArrow", x="11in", y="2in", width="2.8in", height="1.5in",
                  fill="F4A261", color="000000", bold="true", text="flipH + flipV",
                  flipH="true", flipV="true"),
            textbox(2, text=("Aliases: flipHorizontal, flipVertical. Flip flags are stored "
                             "independently of rotation, so flipH + rotate=90 chains predictably."),
                    size="14", italic="true", color="666666",
                    x="0.5in", y="4in", width="13in", height="0.6in"),

            # ============================================================
            # Slide 3 — image fill on a shape (blipFill, NOT --type picture)
            # ============================================================
            slide(),
            textbox(3, text="image= — picture as shape fill (blipFill)", size="28", bold="true",
                    x="0.5in", y="0.3in", width="12in", height="0.6in"),
            # The image fills the shape interior; the geometry preset clips the image.
            shape(3, geometry="ellipse", x="0.5in", y="1.5in", width="3.5in", height="3.5in",
                  image=SAMPLE_PNG, lineColor="1D3557", lineWidth="3pt"),
            shape(3, geometry="star5", x="4.5in", y="1.5in", width="3.5in", height="3.5in",
                  image=SAMPLE_PNG),
            shape(3, geometry="diamond", x="8.5in", y="1.5in", width="3.5in", height="3.5in",
                  image=SAMPLE_PNG, lineColor="1D3557", lineWidth="3pt"),
            textbox(3, text=('image="/path/to/photo.png" turns the shape into a clipped picture '
                             "— different element from --type picture, which embeds the bitmap "
                             "with its native bounding box."),
                    size="14", italic="true", color="666666",
                    x="0.5in", y="5.5in", width="13in", height="1in"),

            # ============================================================
            # Slide 4 — 3D effects (bevel, bevelBottom, depth, lighting, material)
            # ============================================================
            slide(),
            textbox(4, text="3D — bevel / depth / lighting / material", size="28", bold="true",
                    x="0.5in", y="0.3in", width="12in", height="0.6in"),
            # Bevel top, default size
            shape(4, geometry="roundRect", x="0.5in", y="1.4in", width="3in", height="1.8in",
                  fill="4472C4", color="FFFFFF", bold="true", size="14",
                  text="bevel=circle", bevel="circle"),
            # Bevel top + bottom with explicit widths
            shape(4, geometry="roundRect", x="4in", y="1.4in", width="3in", height="1.8in",
                  fill="E63946", color="FFFFFF", bold="true", size="14",
                  text="bevel=angle-8-4 + bevelBottom=circle-4-4",
                  bevel="angle-8-4", bevelBottom="circle-4-4"),
            # Extrusion depth
            shape(4, geometry="roundRect", x="7.5in", y="1.4in", width="3in", height="1.8in",
                  fill="2A9D8F", color="FFFFFF", bold="true", size="14",
                  text="depth=14pt + bevel=softRound", depth="14pt", bevel="softRound"),
            # Lighting + material combos
            shape(4, geometry="ellipse", x="0.5in", y="3.7in", width="3in", height="1.8in",
                  fill="F4A261", color="000000", bold="true", size="12",
                  text="bevel=circle-8 depth=10 lighting=threePt material=metal",
                  bevel="circle-8", depth="10", lighting="threePt", material="metal"),
            shape(4, geometry="ellipse", x="4in", y="3.7in", width="3in", height="1.8in",
                  fill="A8DADC", color="000000", bold="true", size="12",
                  text="lighting=balanced material=plastic",
                  bevel="circle-6", depth="8", lighting="balanced", material="plastic"),
            shape(4, geometry="ellipse", x="7.5in", y="3.7in", width="3in", height="1.8in",
                  fill="FFD700", color="000000", bold="true", size="12",
                  text="lighting=harsh material=warmMatte",
                  bevel="circle-6", depth="8", lighting="harsh", material="warmMatte"),

            # ============================================================
            # Slide 5 — softEdge + link + tooltip + name + zorder
            # ============================================================
            slide(),
            textbox(5, text="softEdge / link / name / zorder", size="28", bold="true",
                    x="0.5in", y="0.3in", width="12in", height="0.6in"),
            # softEdge — feathered/blurred edge in points
            shape(5, geometry="ellipse", x="0.5in", y="1.5in", width="3in", height="2in",
                  fill="E63946", color="FFFFFF", bold="true",
                  text="softEdge=0  (sharp)", softEdge="0"),
            shape(5, geometry="ellipse", x="4in", y="1.5in", width="3in", height="2in",
                  fill="E63946", color="FFFFFF", bold="true",
                  text="softEdge=8pt", softEdge="8pt"),
            shape(5, geometry="ellipse", x="7.5in", y="1.5in", width="3in", height="2in",
                  fill="E63946", color="FFFFFF", bold="true",
                  text="softEdge=20pt  (heavy feather)", softEdge="20pt"),
            # link + tooltip on a shape — entire shape becomes clickable
            shape(5, geometry="roundRect", x="0.5in", y="4in", width="4in", height="1in",
                  fill="2A9D8F", color="FFFFFF", bold="true", size="16",
                  text="Click me → example.com",
                  link="https://example.com", tooltip="Open example.com", name="cta-button"),
            textbox(5, text=('link=https://example.com  tooltip="Open example.com"  name="cta-button"'),
                    size="12", italic="true", color="666666",
                    x="0.5in", y="5.1in", width="6in", height="0.4in"),
            # zorder — three overlapping shapes with explicit stack order
            shape(5, geometry="rect", x="8in", y="4in", width="2.5in", height="2.5in",
                  fill="4472C4", name="back", zorder="1",
                  color="FFFFFF", bold="true", text="back (zorder=1)"),
            shape(5, geometry="rect", x="9in", y="4.5in", width="2.5in", height="2.5in",
                  fill="E63946", name="middle", zorder="2",
                  color="FFFFFF", bold="true", text="middle (zorder=2)"),
            shape(5, geometry="rect", x="10in", y="5in", width="2.5in", height="2.5in",
                  fill="F4A261", name="front", zorder="3",
                  color="000000", bold="true", text="front (zorder=3)"),
        ]

        doc.batch(items)
        print(f"  added {len(items)} slides/shapes/textboxes")
        doc.send({"command": "save"})
    # context exit closes the resident, flushing the deck to disk.
finally:
    if os.path.exists(SAMPLE_PNG):
        os.remove(SAMPLE_PNG)

print(f"Generated: {FILE}")
