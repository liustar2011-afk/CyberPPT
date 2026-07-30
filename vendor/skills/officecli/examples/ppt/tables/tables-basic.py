#!/usr/bin/env python3
"""
Basic PowerPoint table showcase — generates tables-basic.pptx exercising the
pptx `table` element: inline CSV seeding (`data=`), header/body fills, explicit
rows/cols + per-cell text via `set`, cell fill variations (solid hex, named,
theme, gradient, none), cell typography (italic / underline / strike / font /
wrap / spacing) and cell layout (padding / opacity / image fill / textdirection /
direction / merge.right / bevel / per-cell border).

SDK twin of tables-basic.sh (officecli CLI). Both produce an equivalent
tables-basic.pptx. This one drives the **officecli Python SDK**
(`pip install officecli-sdk`): one resident is started and every shape, table,
and per-cell set is shipped over the named pipe — one `doc.batch(...)`
round-trip per slide. Each item is the same `{"command","parent","type",
"props"}` (add) or `{"command","path","props"}` (set) dict you'd put in an
`officecli batch` list.

Usage:
  pip install officecli-sdk          # plus the `officecli` binary on PATH
  python3 tables-basic.py
"""

import os
import sys
import struct
import zlib
import tempfile

# --- locate the SDK: prefer an installed `officecli-sdk`, else the in-repo copy
try:
    import officecli  # pip install officecli-sdk
except ImportError:
    sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                    "..", "..", "..", "sdk", "python"))
    import officecli

FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "tables-basic.pptx")


def add_slide():
    return {"command": "add", "parent": "/", "type": "slide", "props": {}}


def shape(slide, text, **props):
    """One `add shape` item in batch-shape."""
    return {"command": "add", "parent": f"/slide[{slide}]", "type": "shape",
            "props": {"text": text, **props}}


def table(slide, **props):
    """One `add table` item in batch-shape."""
    return {"command": "add", "parent": f"/slide[{slide}]", "type": "table", "props": props}


def cell(slide, tbl, row, col, **props):
    """One `set` item targeting a table cell."""
    return {"command": "set", "path": f"/slide[{slide}]/table[{tbl}]/tr[{row}]/tc[{col}]",
            "props": props}


def _make_checkerboard_png():
    """Write a 32x32 blue/teal checkerboard PNG to a temp file; return its path.
    Mirrors the inline `python3` heredoc in tables-basic.sh (slide 5 image fill)."""
    W = H = 32
    rows = []
    for y in range(H):
        row = b'\x00'
        for x in range(W):
            cell_on = (x // 8 + y // 8) & 1
            row += (b'\x4a\x72\xc4' if cell_on else b'\xa8\xda\xdc')
        rows.append(row)
    raw = b''.join(rows)

    def chunk(t, d):
        return struct.pack('>I', len(d)) + t + d + struct.pack('>I', zlib.crc32(t + d) & 0xffffffff)

    png = b'\x89PNG\r\n\x1a\n'
    png += chunk(b'IHDR', struct.pack('>IIBBBBB', W, H, 8, 2, 0, 0, 0))
    png += chunk(b'IDAT', zlib.compress(raw))
    png += chunk(b'IEND', b'')
    p = tempfile.mktemp(suffix='.png')
    with open(p, 'wb') as f:
        f.write(png)
    return p


print(f"Building {FILE} ...")

imgfile = _make_checkerboard_png()
try:
    with officecli.create(FILE, "--force") as doc:

        # --- Slide 1: minimal 3x3 table seeded inline ---
        doc.batch([
            add_slide(),
            shape(1, "Basic Table — Inline Data", size="28", bold="true",
                  x="0.5in", y="0.3in", width="12in", height="0.6in"),
            # 'data=' uses CSV (comma = cell sep, semicolon = row sep).
            table(1, x="0.5in", y="1.2in", width="12in", height="2in",
                  headerFill="4472C4", bodyFill="DEEAF6",
                  data="Region,Q1,Q2,Q3,Q4;North,120,135,142,168;"
                       "South,98,110,121,140;East,165,178,190,205"),
        ])

        # --- Slide 2: explicit rows/cols then per-cell text ---
        items = [
            add_slide(),
            shape(2, "Basic Table — Per-Cell Set", size="28", bold="true",
                  x="0.5in", y="0.3in", width="12in", height="0.6in"),
            table(2, x="0.5in", y="1.2in", width="10in", height="2.5in",
                  rows="4", cols="3", headerFill="2E75B6"),
        ]
        # Header
        for col, txt in ((1, "Product"), (2, "Units"), (3, "Revenue")):
            items.append(cell(2, 1, 1, col, text=txt, bold="true", color="FFFFFF"))
        # Body
        body = [
            ("Widget", "1,200", "$48,000"),
            ("Gizmo", "850", "$72,250"),
            ("Sprocket", "430", "$25,800"),
        ]
        for r, (p, u, rev) in enumerate(body, start=2):
            items.append(cell(2, 1, r, 1, text=p))
            items.append(cell(2, 1, r, 2, text=u))
            items.append(cell(2, 1, r, 3, text=rev))
        doc.batch(items)

        # --- Slide 3: Cell fill variations (solid hex, theme color, gradient, none) ---
        doc.batch([
            add_slide(),
            shape(3, "Cell Fill Variations", size="28", bold="true",
                  x="0.5in", y="0.3in", width="12in", height="0.6in"),
            table(3, x="0.5in", y="1.2in", width="12in", height="4in",
                  rows="5", cols="2", style="none", **{"border.all": "1pt solid 808080"}),
            cell(3, 1, 1, 1, text="fill spec", bold="true", fill="404040", color="FFFFFF"),
            cell(3, 1, 1, 2, text="rendered", bold="true", fill="404040", color="FFFFFF"),
            # Solid hex
            cell(3, 1, 2, 1, text="fill=FF0000  (solid hex)"),
            cell(3, 1, 2, 2, fill="FF0000"),
            # Named color
            cell(3, 1, 3, 1, text="fill=red  /  fill=rgb(255,0,0)  (named / rgb forms)"),
            cell(3, 1, 3, 2, fill="red"),
            # Theme color — accent1 follows the deck theme
            cell(3, 1, 4, 1, text="fill=accent1  (theme color, follows deck theme)"),
            cell(3, 1, 4, 2, fill="accent1"),
            # Gradient — "COLOR1-COLOR2[-ANGLE]"
            cell(3, 1, 5, 1, text='fill="FF0000-0000FF-90"  (gradient, 90° angle)'),
            cell(3, 1, 5, 2, fill="FF0000-0000FF-90"),
            # fill=none demo (separate small table so 'none' is visible against page bg)
            shape(3, "fill=none  (explicit no-fill; cell becomes transparent):", size="14",
                  x="0.5in", y="5.4in", width="12in", height="0.4in"),
            table(3, x="0.5in", y="5.9in", width="4in", height="0.8in",
                  rows="1", cols="2", style="none", **{"border.all": "1pt solid 000000"}),
            cell(3, 2, 1, 1, text="solid", fill="FFE699"),
            cell(3, 2, 1, 2, text="none", fill="none"),
        ])

        # --- Slide 4: Cell typography — italic / underline / strike / font / wrap ---
        # --- and paragraph spacing — linespacing / spacebefore / spaceafter        ---
        doc.batch([
            add_slide(),
            shape(4, "Cell Typography — italic / underline / strike / font / wrap / spacing",
                  size="24", bold="true",
                  x="0.5in", y="0.3in", width="13in", height="0.6in"),
            table(4, x="0.5in", y="1.1in", width="13in", height="5in",
                  rows="7", cols="2", style="none", **{"border.all": "1pt solid 808080"}),
            # Header
            cell(4, 1, 1, 1, text="Property", bold="true", fill="2E75B6", color="FFFFFF"),
            cell(4, 1, 1, 2, text="Example", bold="true", fill="2E75B6", color="FFFFFF"),
            # italic
            cell(4, 1, 2, 1, text="italic=true"),
            cell(4, 1, 2, 2, text="This cell text is italic.", italic="true"),
            # underline
            cell(4, 1, 3, 1, text="underline=single"),
            cell(4, 1, 3, 2, text="This cell text is underlined.", underline="single"),
            # strike
            cell(4, 1, 4, 1, text="strike=single"),
            cell(4, 1, 4, 2, text="This cell text has strikethrough.", strike="single"),
            # font
            cell(4, 1, 5, 1, text="font=Georgia"),
            cell(4, 1, 5, 2, text="This cell uses Georgia.", font="Georgia", size="16"),
            # wrap=false (text doesn't wrap; overflow is clipped)
            cell(4, 1, 6, 1, text="wrap=false"),
            cell(4, 1, 6, 2,
                 text="This is a long sentence that will not wrap because wrap is "
                      "disabled — it just runs off the edge.",
                 wrap="false"),
            # linespacing / spacebefore / spaceafter
            cell(4, 1, 7, 1, text="linespacing=1.5x + spacebefore=4pt + spaceafter=4pt"),
            cell(4, 1, 7, 2, text="Paragraph A",
                 linespacing="1.5x", spacebefore="4pt", spaceafter="4pt"),
        ])

        # --- Slide 5: Cell layout — padding / padding.bottom / opacity / image / ---
        # ---           textdirection / direction / merge.right / bevel / border.right ---
        doc.batch([
            add_slide(),
            shape(5, "Cell Layout — padding / opacity / image / textdirection / "
                     "merge.right / bevel",
                  size="22", bold="true",
                  x="0.5in", y="0.3in", width="13in", height="0.6in"),
            table(5, x="0.5in", y="1.1in", width="13in", height="6.2in",
                  rows="8", cols="2", style="none", **{"border.all": "1pt solid 808080"}),
            # Header
            cell(5, 1, 1, 1, text="Property", bold="true", fill="1F4E79", color="FFFFFF"),
            cell(5, 1, 1, 2, text="Example", bold="true", fill="1F4E79", color="FFFFFF"),
            # padding — uniform inner margin
            cell(5, 1, 2, 1, text="padding=0.25in"),
            cell(5, 1, 2, 2, text="Large inner margin.", fill="F1FAEE", padding="0.25in"),
            # padding.bottom — single-edge padding override
            cell(5, 1, 3, 1, text="padding.bottom=0.3in"),
            cell(5, 1, 3, 2, text="Extra space below this text.", fill="F1FAEE",
                 **{"padding.bottom": "0.3in"}),
            # opacity — fill transparency (0=opaque, 1=invisible)
            cell(5, 1, 4, 1, text="opacity=0.4  (requires fill)"),
            cell(5, 1, 4, 2, text="40% transparent fill.", fill="4472C4", opacity="0.4"),
            # image — picture fill (blipFill on the cell)
            cell(5, 1, 5, 1, text="image=/path/to/img.png"),
            cell(5, 1, 5, 2, image=imgfile),
            # textdirection — vertical text rendering in a cell
            cell(5, 1, 6, 1, text="textdirection=vert"),
            cell(5, 1, 6, 2, text="Vertical text", textdirection="vert", fill="FFE699"),
            # direction — RTL paragraph direction within a cell
            cell(5, 1, 7, 1, text="direction=rtl"),
            cell(5, 1, 7, 2, text="مرحبا", direction="rtl", size="18", fill="A8DADC"),
            # merge.right + bevel + border.right (per-cell border)
            cell(5, 1, 8, 1, text="merge.right=1  bevel=circle  border.right=2pt solid E63946",
                 fill="F4A261", size="11"),
            cell(5, 1, 8, 2, text="Merged, beveled, custom right border.",
                 fill="F4A261", bevel="circle", **{"border.right": "2pt solid E63946"}),
        ])

        doc.send({"command": "save"})
    # context exit closes the resident, flushing the deck to disk.
finally:
    if os.path.exists(imgfile):
        os.remove(imgfile)

print(f"Generated: {FILE}")
