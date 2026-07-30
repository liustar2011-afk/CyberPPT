#!/usr/bin/env python3
"""
Cell Formatting Showcase — generates cell-formatting.xlsx exercising the full
xlsx `cell` property surface (schemas/help/xlsx/cell.json).

SDK twin of cell-formatting.sh (officecli CLI). Both produce an equivalent
cell-formatting.xlsx. This one drives the **officecli Python SDK**
(`pip install officecli-sdk`): one resident is started and every cell write
ships over the named pipe in `doc.batch(...)` round-trips — the same
`{"command","parent","type","props"}` / `{"command","path","props"}` dicts
you'd put in an `officecli batch` list.

6 sheets, one property group each:
  Fonts    — font.name/size/bold/italic/color, underline, strike, super/subscript
  Fills    — fill (hex/named/rgb), alignment.horizontal/vertical/wrapText/readingOrder
             + textRotation/indent/shrinkToFit
  Borders  — border shorthand, border.all, per-side styles, border.color, diagonals
  Numbers  — numberformat codes (thousands, %, currency, date, scientific, accounting)
  Data     — value/type, formula, link + tooltip, locked, merge, arrayformula
  RichText — runs (multi-format text within one cell; add-time only)

`set` auto-creates the target cell, so no explicit `add` is needed per cell.
Closes with a Set -> Get round-trip readback proving the canonical keys come back.

Usage:
  pip install officecli-sdk          # plus the `officecli` binary on PATH
  python3 cell-formatting.py
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

FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "cell-formatting.xlsx")


def cell(path, **props):
    """One `set <path> --prop k=v ...` item in batch-shape. `set` auto-creates
    the target cell, so no explicit `add` is needed. Props pass through verbatim
    (canonical keys like `font.bold`, `alignment.horizontal`, `numberformat`)."""
    return {"command": "set", "path": f"/{path}" if not path.startswith("/") else path,
            "props": props}


def add_sheet(name):
    """One `add sheet --prop name=...` item in batch-shape."""
    return {"command": "add", "parent": "/", "type": "sheet", "props": {"name": name}}


def add_cell(parent, **props):
    """One `add cell` item in batch-shape — used for rich-text `runs`, which is an
    add-time property (requires --type cell + type=richtext); `set` can't do it."""
    return {"command": "add", "parent": parent, "type": "cell", "props": props}


print("\n==========================================")
print(f"Generating cell formatting showcase: {FILE}")
print("==========================================")

with officecli.create(FILE, "--force") as doc:

    # ==========================================================================
    # Sheet1: Fonts — font.* family + underline/strike
    # ==========================================================================
    print("\n--- Sheet1: Fonts ---")
    items = [
        cell("Sheet1/A1", value="Cell font properties", **{"font.bold": "true", "font.size": "14", "fill": "1F4E79", "font.color": "FFFFFF"}),
        cell("Sheet1/A2", value="Property", **{"font.bold": "true", "fill": "D9E1F2"}),
        cell("Sheet1/B2", value="Rendered sample", **{"font.bold": "true", "fill": "D9E1F2"}),
    ]

    # (label, sample-text, {props applied to the sample cell})
    FONT_ROWS = [
        ("font.name=Georgia", "Georgia serif",              {"font.name": "Georgia"}),
        ("font.size=18",      "18pt text",                  {"font.size": "18"}),
        ("font.bold=true",    "Bold text",                  {"font.bold": "true"}),
        ("font.italic=true",  "Italic text",                {"font.italic": "true"}),
        ("font.color=C00000", "Red text",                   {"font.color": "C00000"}),
        ("underline=single",  "Underlined",                 {"underline": "single"}),
        ("underline=double",  "Double underline",           {"underline": "double"}),
        ("strike=true",       "Struck out",                 {"strike": "true"}),
        ("superscript=true",  "Superscript cell",           {"superscript": "true"}),
        ("subscript=true",    "Subscript cell",             {"subscript": "true"}),
        ("combined",          "Bold + italic + blue + 14pt", {"font.bold": "true", "font.italic": "true", "font.color": "2E75B6", "font.size": "14"}),
    ]
    for i, (label, sample, props) in enumerate(FONT_ROWS, start=3):
        items.append(cell(f"Sheet1/A{i}", value=label))
        items.append(cell(f"Sheet1/B{i}", value=sample, **props))

    items.append(cell("Sheet1/col[1]", width="22"))
    items.append(cell("Sheet1/col[2]", width="32"))
    doc.batch(items)

    # ==========================================================================
    # Sheet2: Fills & alignment
    # ==========================================================================
    print("--- Sheet2: Fills & alignment ---")
    items = [add_sheet("Fills")]
    items.append(cell("Fills/A1", value="Fills & alignment", **{"font.bold": "true", "font.size": "14", "fill": "548235", "font.color": "FFFFFF"}))

    items.append(cell("Fills/A2", value="fill=E63946 (hex)",    fill="E63946", **{"font.color": "FFFFFF"}))
    items.append(cell("Fills/A3", value="fill=gold (named)",    fill="gold"))
    items.append(cell("Fills/A4", value="fill=rgb(46,157,182)", fill="rgb(46,157,182)", **{"font.color": "FFFFFF"}))

    for i, h in zip((6, 7, 8), ("left", "center", "right")):
        items.append(cell(f"Fills/A{i}", value=h, fill="F2F2F2", **{"alignment.horizontal": h}))
    for i, v in zip((6, 7, 8), ("top", "center", "bottom")):
        items.append(cell(f"Fills/C{i}", value={"center": "middle"}.get(v, v), fill="FCE4D6", **{"alignment.vertical": v}))
        items.append(cell(f"Fills/row[{i}]", height="34"))

    items.append(cell("Fills/A10", value="This is a long sentence that wraps inside one cell via alignment.wrapText.", fill="E2EFDA", **{"alignment.wrapText": "true"}))
    items.append(cell("Fills/A12", value="RTL reading order", fill="DDEBF7", **{"alignment.readingOrder": "rtl"}))

    # textRotation / indent / shrinkToFit — set directly on alignment (canonical keys).
    items.append(cell("Fills/A14", value="rotated 45deg", fill="FFF2CC", **{"alignment.textRotation": "45"}))
    items.append(cell("Fills/row[14]", height="40"))
    items.append(cell("Fills/A16", value="indented 3", fill="F2F2F2", **{"alignment.indent": "3"}))
    items.append(cell("Fills/A18", value="ThisLongLabelShrinksToFit", fill="E2EFDA", **{"alignment.shrinkToFit": "true"}))

    items.append(cell("Fills/col[1]", width="30"))
    items.append(cell("Fills/col[3]", width="14"))
    doc.batch(items)

    # ==========================================================================
    # Sheet3: Borders
    # ==========================================================================
    print("--- Sheet3: Borders ---")
    items = [add_sheet("Borders")]
    items.append(cell("Borders/A1", value="Border styles", **{"font.bold": "true", "font.size": "14", "fill": "7030A0", "font.color": "FFFFFF"}))

    items.append(cell("Borders/B3",  value="border=thin (all)",   border="thin"))
    items.append(cell("Borders/B5",  value="border.all=medium",   **{"border.all": "medium"}))
    items.append(cell("Borders/B7",  value="border + color",      border="thick", **{"border.color": "C00000"}))
    items.append(cell("Borders/B9",  value="double bottom",       **{"border.bottom": "double"}))
    items.append(cell("Borders/B11", value="dashed box",          **{"border.top": "dashed", "border.bottom": "dashed", "border.left": "dashed", "border.right": "dashed"}))
    items.append(cell("Borders/B13", value="mixed sides",         **{"border.left": "thick", "border.top": "thin", "border.right": "medium", "border.bottom": "double"}))
    # Diagonal borders — direction via diagonalUp/Down, color requires a diagonal line.
    items.append(cell("Borders/B15", value="diagonal up",         **{"border.diagonal": "thin", "border.diagonalUp": "true"}))
    items.append(cell("Borders/B17", value="diagonal down + color", **{"border.diagonal": "medium", "border.diagonalDown": "true", "border.diagonal.color": "C00000"}))

    items.append(cell("Borders/col[1]", width="18"))
    items.append(cell("Borders/col[2]", width="24"))
    doc.batch(items)

    # ==========================================================================
    # Sheet4: Number formats
    # ==========================================================================
    print("--- Sheet4: Number formats ---")
    items = [add_sheet("Numbers")]
    items.append(cell("Numbers/A1", value="numberformat codes", **{"font.bold": "true", "font.size": "14", "fill": "C55A11", "font.color": "FFFFFF"}))
    items.append(cell("Numbers/A2", value="Format code", **{"font.bold": "true", "fill": "FCE4D6"}))
    items.append(cell("Numbers/B2", value="Result",      **{"font.bold": "true", "fill": "FCE4D6"}))

    # (format code, raw value); A-label is the code itself, B-cell carries the format
    NUM_ROWS = [
        ("#,##0",       "1234567"),
        ("#,##0.00",    "1234.5"),
        ("0.00%",       "0.1834"),
        ("$#,##0.00",   "29999.9"),
        ("yyyy-mm-dd",  "45413"),
        ("0.00E+00",    "602214"),
        ('_(* #,##0.00_);_(* (#,##0.00);_(* "-"??_)', "-4250"),
    ]
    for i, (code, val) in enumerate(NUM_ROWS, start=3):
        # label cell: show the (short) code as literal text — type=string keeps
        # codes like "0.00E+00" from being parsed as a scientific-notation number.
        items.append(cell(f"Numbers/A{i}", value=code.split(";")[0], type="string"))
        items.append(cell(f"Numbers/B{i}", value=val, numberformat=code))

    items.append(cell("Numbers/col[1]", width="28"))
    items.append(cell("Numbers/col[2]", width="18"))
    doc.batch(items)

    # ==========================================================================
    # Sheet5: Data — value/type, formula, link, locked, merge
    # ==========================================================================
    print("--- Sheet5: Data, formulas & links ---")
    items = [add_sheet("Data")]
    items.append(cell("Data/A1", value="Values, formulas, links", **{"font.bold": "true", "font.size": "14", "fill": "2E75B6", "font.color": "FFFFFF"}))

    items.append(cell("Data/A3", value="Qty"));                 items.append(cell("Data/B3", value="12"))
    items.append(cell("Data/A4", value="Price"));               items.append(cell("Data/B4", value="4.5", numberformat="$#,##0.00"))
    items.append(cell("Data/A5", value="Total", **{"font.bold": "true"}))
    items.append(cell("Data/B5", formula="B3*B4", numberformat="$#,##0.00", **{"font.bold": "true"}))

    items.append(cell("Data/A7", value="type=string on a numeric value", type="string"))
    items.append(cell("Data/B7", value="007", type="string"))

    items.append(cell("Data/A9", value="OfficeCLI on GitHub", link="https://github.com/iOfficeAI/OfficeCLI",
                      tooltip="Open the repo", underline="single", **{"font.color": "0563C1"}))

    items.append(cell("Data/A11", value="locked cell (effective when sheet is protected)", locked="true"))

    items.append(cell("Data/A13", value="Merged title across A13:C13", merge="A13:C13", fill="DDEBF7",
                      **{"alignment.horizontal": "center", "font.bold": "true"}))

    # Dynamic-array formula — spills the result across the ref range.
    items.append(cell("Data/A15", value="arrayformula = B3*2", **{"font.italic": "true"}))
    items.append(cell("Data/B15", arrayformula="B3*2"))

    items.append(cell("Data/col[1]", width="40"))
    items.append(cell("Data/col[2]", width="16"))
    doc.batch(items)

    # ==========================================================================
    # Sheet6: Rich-text — runs (multi-format text within one cell)
    # ==========================================================================
    # `runs` is an add-time property (requires type=cell + type=richtext). Each
    # run is a JSON object with "text" plus any font props (bold, italic, color,
    # size, underline). `set` does not support rich-text; use `add`.
    print("--- Sheet6: Rich-text runs ---")
    items = [add_sheet("RichText")]

    # Label
    items.append(cell("RichText/A1", value="runs — rich-text within one cell", **{"font.bold": "true", "font.size": "14", "fill": "5B2C8B", "font.color": "FFFFFF"}))

    # Each add creates the cell with multi-format text in a single SST entry.
    items.append(add_cell("/RichText", ref="A3", type="richtext",
        runs='[{"text":"Bold + Red  ","bold":true,"color":"C00000"},{"text":"Italic + Blue","italic":true,"color":"2E75B6"},{"text":"  Normal"}]'))
    items.append(add_cell("/RichText", ref="A5", type="richtext",
        runs='[{"text":"H","bold":true,"color":"1F4E79","size":18},{"text":"2","superscript":true,"size":10},{"text":"O water formula","color":"1F4E79"}]'))
    items.append(add_cell("/RichText", ref="A7", type="richtext",
        runs='[{"text":"Strike","strike":true},{"text":" | "},{"text":"underline","underline":"single"},{"text":" | "},{"text":"size 14pt","size":14}]'))

    items.append(cell("RichText/col[1]", width="50"))
    doc.batch(items)

    # ==========================================================================
    # Set -> Get round-trip: confirm canonical keys read back (in-session, pipe)
    # ==========================================================================
    print("\n--- Round-trip readback (Set then Get) ---")
    for path, keys in [
        ("/Sheet1/B11", ("font.bold", "font.italic", "font.color", "font.size")),
        ("/Numbers/B6", ("value", "numberformat")),
        ("/Borders/B9", ("border.bottom",)),
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
