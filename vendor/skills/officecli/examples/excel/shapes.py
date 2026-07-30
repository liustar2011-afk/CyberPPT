#!/usr/bin/env python3
"""
Excel Shapes Gallery — generates shapes.xlsx exercising the xlsx `shape`
property surface (officecli help xlsx shape).

SDK twin of shapes.sh (officecli CLI). Both produce an equivalent shapes.xlsx:
a single "Gallery" sheet laid out as a shape gallery — each demo shape sits in
a readable grid with a label cell above it. This one drives the **officecli
Python SDK** (`pip install officecli-sdk`): one resident is started and every
add/set ships over the named pipe in `doc.batch(...)` round-trips — the same
`{"command","parent","type","props"}` / `{"command","path","props"}` dicts you'd
put in an `officecli batch` list.

Shapes are anchored with cell-unit x/y/width/height (TwoCellAnchor column/row
indices — NOT points/inches). Get reads position back as those integer indices.

Usage:
  pip install officecli-sdk          # plus the `officecli` binary on PATH
  python3 shapes.py
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

FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "shapes.xlsx")


def cell(path, **props):
    """One `set <path> --prop k=v ...` item in batch-shape (labels/title)."""
    return {"command": "set", "path": f"/{path}" if not path.startswith("/") else path,
            "props": props}


def shape(**props):
    """One `add /Sheet1 --type shape --prop k=v ...` item in batch-shape."""
    return {"command": "add", "parent": "/Sheet1", "type": "shape", "props": props}


print("\n==========================================")
print(f"Generating Excel shapes gallery: {FILE}")
print("==========================================")

with officecli.create(FILE, "--force") as doc:

    items = [
        cell("Sheet1/A1", value="Excel Shapes Gallery",
             **{"font.bold": "true", "font.size": "16", "fill": "1F4E79", "font.color": "FFFFFF"}),
        cell("Sheet1/A2",
             value="Each shape sits below its label. Shapes are cell-anchored (x/y/width/height in column/row units).",
             **{"font.italic": "true", "font.color": "595959"}),
    ]

    # -----------------------------------------------------------------------
    # Band 1 — Geometry preset gallery (solid fill, white/dark text)
    # -----------------------------------------------------------------------
    print("--- Band 1: geometry presets ---")
    items += [
        cell("Sheet1/A4", value="geometry=rect",      **{"font.bold": "true"}),
        cell("Sheet1/D4", value="geometry=roundRect", **{"font.bold": "true"}),
        cell("Sheet1/G4", value="geometry=ellipse",   **{"font.bold": "true"}),
        cell("Sheet1/J4", value="geometry=triangle",  **{"font.bold": "true"}),
    ]
    # Features: geometry preset, solid fill, text, color, bold
    items.append(shape(geometry="rect",      x="0", y="4", width="2", height="3", fill="4472C4", text="rect",      color="FFFFFF", bold="true"))
    items.append(shape(geometry="roundRect", x="3", y="4", width="2", height="3", fill="2A9D8F", text="roundRect", color="FFFFFF", bold="true"))
    items.append(shape(geometry="ellipse",   x="6", y="4", width="2", height="3", fill="E76F51", text="ellipse",   color="FFFFFF", bold="true"))
    items.append(shape(geometry="triangle",  x="9", y="4", width="2", height="3", fill="E9C46A", text="triangle",  color="264653", bold="true"))

    # -----------------------------------------------------------------------
    # Band 2 — More presets + name override
    # -----------------------------------------------------------------------
    print("--- Band 2: more presets + name ---")
    items += [
        cell("Sheet1/A9", value="geometry=diamond",         **{"font.bold": "true"}),
        cell("Sheet1/D9", value="geometry=parallelogram",   **{"font.bold": "true"}),
        cell("Sheet1/G9", value="geometry=rightArrow",      **{"font.bold": "true"}),
        cell("Sheet1/J9", value="geometry=star5 (name=MyStar)", **{"font.bold": "true"}),
    ]
    items.append(shape(geometry="diamond",       x="0", y="9", width="2", height="3", fill="8E44AD", text="diamond",       color="FFFFFF", bold="true"))
    items.append(shape(geometry="parallelogram", x="3", y="9", width="2", height="3", fill="457B9D", text="parallelogram", color="FFFFFF", bold="true"))
    items.append(shape(geometry="rightArrow",    x="6", y="9", width="2", height="3", fill="F4A261", text="rightArrow",    color="264653", bold="true"))
    # Features: name (override auto cNvPr @name)
    items.append(shape(geometry="star5",         x="9", y="9", width="2", height="3", fill="E63946", name="MyStar"))

    # -----------------------------------------------------------------------
    # Band 3 — Flips & rotation
    # -----------------------------------------------------------------------
    print("--- Band 3: flips & rotation ---")
    items += [
        cell("Sheet1/A14", value="flipH=true (mirrored arrow)", **{"font.bold": "true"}),
        cell("Sheet1/D14", value="flipV=true",                  **{"font.bold": "true"}),
        cell("Sheet1/G14", value="flipBoth=true",               **{"font.bold": "true"}),
        cell("Sheet1/J14", value="rotation=30",                 **{"font.bold": "true"}),
    ]
    # Features: flipH / flipV / flipBoth (Office-API flip aliases → readback `flip`)
    items.append(shape(geometry="rightArrow",    x="0", y="14", width="2", height="3", fill="4472C4", flipH="true"))
    items.append(shape(geometry="triangle",      x="3", y="14", width="2", height="3", fill="2A9D8F", flipV="true"))
    items.append(shape(geometry="parallelogram", x="6", y="14", width="2", height="3", fill="E76F51", flipBoth="true"))
    # Features: rotation (degrees clockwise)
    items.append(shape(geometry="rightArrow",    x="9", y="14", width="2", height="3", fill="E9C46A", rotation="30", text="30°", color="264653", bold="true"))

    # -----------------------------------------------------------------------
    # Band 4 — Effects: glow, gradient fill, reflection, shadow, soft edge
    # -----------------------------------------------------------------------
    print("--- Band 4: effects ---")
    items += [
        cell("Sheet1/A19", value="glow=FFD700",              **{"font.bold": "true"}),
        cell("Sheet1/D19", value="gradientFill (2-stop)",    **{"font.bold": "true"}),
        cell("Sheet1/G19", value="reflection=true",          **{"font.bold": "true"}),
        cell("Sheet1/J19", value="shadow=000000 + softEdge=4", **{"font.bold": "true"}),
    ]
    # Features: glow (color halo)
    items.append(shape(geometry="ellipse",   x="0", y="19", width="2", height="3", fill="2A9D8F", glow="FFD700"))
    # Features: gradientFill (2-stop linear C1-C2:angle; mutually exclusive with fill, add-only)
    items.append(shape(geometry="roundRect", x="3", y="19", width="2", height="3", gradientFill="FF6B6B-4ECDC4:45", text="gradient", color="FFFFFF", bold="true"))
    # Features: reflection (mirror-below; 'true' = default reflection; add-only)
    items.append(shape(geometry="roundRect", x="6", y="19", width="2", height="3", fill="457B9D", reflection="true", text="reflection", color="FFFFFF", bold="true"))
    # Features: shadow (outer shadow) + softEdge (feathered radius)
    items.append(shape(geometry="rect",      x="9", y="19", width="2", height="3", fill="8E44AD", shadow="000000", softEdge="4", text="shadow", color="FFFFFF"))

    # -----------------------------------------------------------------------
    # Band 5 — Outline, text styling, theme fill, cell-range anchor
    # -----------------------------------------------------------------------
    print("--- Band 5: outline, text styling, theme fill, anchor ---")
    items += [
        cell("Sheet1/A24", value="line=C00000:2:dash (color:width:style)",  **{"font.bold": "true"}),
        cell("Sheet1/D24", value="styled text (font/size/align)", **{"font.bold": "true"}),
        cell("Sheet1/G24", value="fill=accent1 (theme color)",  **{"font.bold": "true"}),
        cell("Sheet1/J24", value="anchor=K25:L28 (cell range)", **{"font.bold": "true"}),
    ]
    # Features: line compound form 'color[:width[:style]]' (width in pt; style is
    #           a prstDash token: solid/dash/dot/dashdot/longdash — same grammar as
    #           pptx shape line), fill=none
    items.append(shape(geometry="rect", x="0", y="24", width="2", height="3", fill="none", line="C00000:2:dash", text="outline", color="C00000"))
    # Features: font / size / italic / align / valign / margin (text inset)
    items.append(shape(geometry="roundRect", x="3", y="24", width="2", height="3", fill="E9C46A",
                       text="Georgia italic center-top, inset 6pt",
                       font="Georgia", size="12", italic="true", align="center", valign="top", margin="6", color="264653"))
    # Features: fill with a theme (scheme) color name
    items.append(shape(geometry="ellipse", x="6", y="24", width="2", height="3", fill="accent1", text="accent1", color="FFFFFF", bold="true"))
    # Features: anchor (cell-range form; readback normalizes to x/y/width/height)
    items.append(shape(geometry="roundRect", anchor="K25:L28", fill="1D3557", text="anchored K25:L28", color="FFFFFF", bold="true"))

    # Widen columns so the label cells are readable.
    for c in range(1, 13):
        items.append(cell(f"Sheet1/col[{c}]", width="13"))

    doc.batch(items)

    # -----------------------------------------------------------------------
    # Round-trip readback (in-session, pipe) — confirm props survive the write.
    # -----------------------------------------------------------------------
    print("\n--- Round-trip readback (Add then Get) ---")
    for path, keys in [
        ("/Sheet1/shape[8]",  ("name", "geometry")),                 # star5 + name=MyStar
        ("/Sheet1/shape[9]",  ("flip", "geometry")),                 # flipH → flip=h
        ("/Sheet1/shape[12]", ("rotation", "geometry")),             # rotation=30
        ("/Sheet1/shape[13]", ("glow", "fill")),                     # glow
        ("/Sheet1/shape[16]", ("shadow", "softEdge")),               # shadow + softEdge
        ("/Sheet1/shape[18]", ("font", "size", "align", "margin")),  # styled text
        ("/Sheet1/shape[20]", ("x", "y", "width", "height")),        # anchor → x/y/width/height
    ]:
        node = doc.send({"command": "get", "path": path})
        try:
            fmt = node["data"]["results"][0]["format"]
        except Exception:
            fmt = {}
        shown = {k: fmt.get(k) for k in keys if k in fmt}
        print(f"  {path}: {shown}")

    doc.send({"command": "save"})
# context exit closes the resident, flushing the workbook to disk.

print(f"\nCreated: {FILE}")
