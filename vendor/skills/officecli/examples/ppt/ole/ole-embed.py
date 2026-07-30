#!/usr/bin/env python3
"""
PowerPoint OLE embedded objects — embed .xlsx / .docx binary payloads in a deck.

SDK twin of ole-embed.sh (officecli CLI). Both produce an equivalent
ole-embed.pptx. This one drives the **officecli Python SDK**
(`pip install officecli-sdk`): a resident is started per file and every element
is shipped over the named pipe. Each item is the same
`{"command","parent","type","props"}` dict you'd put in an `officecli batch`
list; `doc.send(...)` ships one and returns its envelope.

This script:
  1. Builds two source payloads with officecli: a tiny .xlsx and a .docx
  2. Synthesizes two distinct preview thumbnail PNGs (Pillow)
  3. Builds a 2-slide PPTX demoing OLE embedding:
     - slide 1: embed the .xlsx (Excel.Sheet.12) and the .docx (Word.Document.12),
       each with an explicit preview= thumbnail so they render visibly
     - slide 2: WITH preview= vs WITHOUT — a deliberate teaching contrast
  4. Reads back contentType / fileSize / progId / relId via `get`

IMPORTANT: officecli does NOT auto-generate the Office live-preview image for an
embedded OLE object. Without preview=, the object embeds and validates fine, but
real PowerPoint renders it as a BLANK rectangle in static/print view — it only
becomes visible after the user double-clicks to activate it. Supply preview= for
any OLE object you want visible in a static view.

The embedded source files (data.xlsx, data.docx) and the preview PNGs live in
this example dir alongside the deck — they are the meaningful inputs the embed
step consumes.

Requirements:
  pip install Pillow officecli-sdk          # plus the `officecli` binary on PATH

Usage:
  python3 ole-embed.py
"""

import os
import sys

try:
    from PIL import Image, ImageDraw
except ImportError:
    print("ERROR: Pillow not installed. Run: pip install Pillow")
    sys.exit(1)

# --- locate the SDK: prefer an installed `officecli-sdk`, else the in-repo copy
try:
    import officecli  # pip install officecli-sdk
except ImportError:
    sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                    "..", "..", "..", "sdk", "python"))
    import officecli


HERE = os.path.dirname(os.path.abspath(__file__))
FILE = os.path.join(HERE, "ole-embed.pptx")
XLSX = os.path.join(HERE, "data.xlsx")
DOCX = os.path.join(HERE, "data.docx")
THUMB_XLSX = os.path.join(HERE, "thumb-xlsx.png")
THUMB_DOCX = os.path.join(HERE, "thumb-docx.png")


def add(doc, parent, typ, **props):
    """Ship one `add` item over the pipe; return the parsed envelope."""
    return doc.send({"command": "add", "parent": parent, "type": typ, "props": props})


def make_thumbs(xlsx_path, docx_path):
    # Excel-styled thumbnail (green) for the .xlsx embed
    img = Image.new("RGB", (240, 160), (33, 115, 70))
    d = ImageDraw.Draw(img)
    d.rectangle((8, 8, 231, 151), outline=(255, 255, 255), width=4)
    d.text((30, 40), "Q1 Revenue", fill=(255, 255, 255))
    d.text((30, 90), "(embedded .xlsx)", fill=(200, 230, 210))
    img.save(xlsx_path)

    # Word-styled thumbnail (blue) for the .docx embed
    img = Image.new("RGB", (240, 160), (43, 87, 154))
    d = ImageDraw.Draw(img)
    d.rectangle((8, 8, 231, 151), outline=(255, 255, 255), width=4)
    d.text((30, 40), "Quarterly Memo", fill=(255, 255, 255))
    d.text((30, 90), "(embedded .docx)", fill=(205, 218, 240))
    img.save(docx_path)


def build_xlsx(path):
    """A tiny spreadsheet payload."""
    if os.path.exists(path):
        os.remove(path)
    with officecli.create(path, "--force") as x:
        x.send({"command": "set", "path": "/sheet[1]/A1", "props": {"value": "Q1 Revenue"}})
        x.send({"command": "set", "path": "/sheet[1]/A2", "props": {"value": "North"}})
        x.send({"command": "set", "path": "/sheet[1]/B2", "props": {"value": "1200"}})
        x.send({"command": "set", "path": "/sheet[1]/A3", "props": {"value": "South"}})
        x.send({"command": "set", "path": "/sheet[1]/B3", "props": {"value": "980"}})
        x.send({"command": "save"})


def build_docx(path):
    """A tiny Word memo payload."""
    if os.path.exists(path):
        os.remove(path)
    with officecli.create(path, "--force") as w:
        add(w, "/body", "paragraph", text="Quarterly Memo", bold="true", size="16")
        add(w, "/body", "paragraph", text="Revenue is up 12% quarter over quarter.")
        w.send({"command": "save"})


def main():
    if os.path.exists(FILE):
        os.remove(FILE)

    build_xlsx(XLSX)
    build_docx(DOCX)
    make_thumbs(THUMB_XLSX, THUMB_DOCX)

    print(f"Building {FILE} ...")

    with officecli.create(FILE, "--force") as doc:

        # ── Slide 1: embed an .xlsx and a .docx, each with a preview= ─────────
        add(doc, "/", "slide")
        add(doc, "/slide[1]", "textbox",
            text="Embedded OLE objects — Excel + Word packages",
            size="24", bold="true",
            x="0.5in", y="0.3in", width="12in", height="0.6in")

        # Embed the spreadsheet. Double-clicking the object opens it in-place.
        # progId=Excel.Sheet.12 marks it as a modern .xlsx package.
        # preview= gives it a visible face in static view (officecli won't bake one).
        add(doc, "/slide[1]", "ole",
            src=XLSX,
            progId="Excel.Sheet.12",
            preview=THUMB_XLSX,
            x="1.5in", y="1.8in", width="3.5in", height="2.5in")
        add(doc, "/slide[1]", "textbox",
            text="src=data.xlsx  progId=Excel.Sheet.12  preview=thumb-xlsx.png",
            size="12", italic="true",
            x="1.5in", y="4.4in", width="5in", height="0.4in")

        # Embed the Word memo. progId=Word.Document.12 marks it as a modern .docx.
        # preview= gives it a visible face in static view (officecli won't bake one).
        add(doc, "/slide[1]", "ole",
            src=DOCX,
            progId="Word.Document.12",
            preview=THUMB_DOCX,
            x="6.5in", y="1.8in", width="3.5in", height="2.5in")
        add(doc, "/slide[1]", "textbox",
            text="src=data.docx  progId=Word.Document.12  preview=thumb-docx.png",
            size="12", italic="true",
            x="6.5in", y="4.4in", width="5in", height="0.4in")

        # ── Slide 2: WITH preview= vs WITHOUT — a deliberate teaching contrast ─
        add(doc, "/", "slide")
        add(doc, "/slide[2]", "textbox",
            text="preview= is the reliable path to a visible OLE object",
            size="24", bold="true",
            x="0.5in", y="0.3in", width="12in", height="0.6in")

        # WITH preview= — the thumbnail is drawn in the object frame in static
        # view. add-time only (Set ignores this key).
        add(doc, "/slide[2]", "ole",
            src=XLSX,
            progId="Excel.Sheet.12",
            preview=THUMB_XLSX,
            x="1.5in", y="1.8in", width="3.5in", height="2.5in")
        add(doc, "/slide[2]", "textbox",
            text="src=data.xlsx  preview=thumb-xlsx.png  (renders visibly)",
            size="12", italic="true",
            x="1.5in", y="4.4in", width="4.5in", height="0.4in")

        # WITHOUT preview= — embeds and validates fine, but real PowerPoint
        # renders a BLANK rectangle in static view; it only appears once
        # double-clicked/activated. officecli does NOT bake the live preview.
        add(doc, "/slide[2]", "ole",
            src=XLSX,
            progId="Excel.Sheet.12",
            x="6.5in", y="1.8in", width="3.5in", height="2.5in")
        add(doc, "/slide[2]", "textbox",
            text="src=data.xlsx  (no preview — blank until opened in PowerPoint)",
            size="12", italic="true",
            x="6.5in", y="4.4in", width="5in", height="0.4in")

        doc.send({"command": "save"})

        # ── Inspect: Get surfaces read-only readbacks (src is NOT echoed) ─────
        for path in ("/slide[1]/ole[1]", "/slide[1]/ole[2]"):
            env = doc.send({"command": "get", "path": path})
            print(f"{path}: {env.get('data') if isinstance(env, dict) else env}")

    # context exit closes the resident, flushing the deck to disk.
    print(f"Created: {FILE}")


if __name__ == "__main__":
    main()
