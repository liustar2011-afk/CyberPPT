#!/usr/bin/env python3
"""
Basic PowerPoint textboxes — alignment, multi-paragraph, bulleted/numbered
lists, styled runs, per-script fonts (Latin/EastAsian), vertical alignment and
padding. Demonstrates: type "textbox" (an alias for "shape"), type "paragraph"
with align/level, type "run" with bold/italic/underline/strike/color/baseline,
shape-level list=bullet|numbered, font.latin/font.ea, valign and margin.

SDK twin of textboxes-basic.sh (officecli CLI). Both produce an equivalent
textboxes-basic.pptx. This one drives the **officecli Python SDK**
(`pip install officecli-sdk`): one resident is started and every slide, shape,
paragraph and run is shipped over the named pipe in a single `doc.batch(...)`
round-trip — items apply in order, so a paragraph/run can target a shape an
earlier item in the same list just created. Each item is the same
`{"command","parent","type","props"}` dict you'd put in an `officecli batch` list.

Usage:
  pip install officecli-sdk          # plus the `officecli` binary on PATH
  python3 textboxes-basic.py
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

FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "textboxes-basic.pptx")


def slide(**props):
    """One `add slide` item in batch-shape."""
    return {"command": "add", "parent": "/", "type": "slide", "props": props}


def textbox(parent, **props):
    """One `add textbox` item in batch-shape."""
    return {"command": "add", "parent": parent, "type": "textbox", "props": props}


def paragraph(parent, **props):
    """One `add paragraph` item in batch-shape."""
    return {"command": "add", "parent": parent, "type": "paragraph", "props": props}


def run(parent, **props):
    """One `add run` item in batch-shape."""
    return {"command": "add", "parent": parent, "type": "run", "props": props}


def setp(path, **props):
    """One `set` item in batch-shape."""
    return {"command": "set", "path": path, "props": props}


LOREM = ("Lorem ipsum dolor sit amet, consectetur adipiscing elit. "
         "Vivamus lacinia odio vitae vestibulum vestibulum.")

print(f"Building {FILE} ...")

with officecli.create(FILE, "--force") as doc:
    items = []

    # ===================================================================
    # Slide 1 — Horizontal alignment (4 textboxes, one per align value)
    # ===================================================================
    items.append(slide())
    items.append(textbox("/slide[1]",
                         text="Horizontal Alignment", size="28", bold="true",
                         x="0.5in", y="0.3in", width="12in", height="0.6in"))

    y = 1.3
    for a in ("left", "center", "right", "justify"):
        items.append(textbox("/slide[1]",
                             x="0.5in", y=f"{y}in", width="12in", height="1.3in",
                             fill="F1FAEE", text=f"[align={a}] {LOREM}", size="14",
                             align=a))
        y += 1.5

    # ===================================================================
    # Slide 2 — Multi-paragraph + bulleted / numbered lists
    # ===================================================================
    items.append(slide())
    items.append(textbox("/slide[2]",
                         text="Lists and Multi-Paragraph", size="28", bold="true",
                         x="0.5in", y="0.3in", width="12in", height="0.6in"))

    # Bulleted list — start with one initial paragraph (the title), append the
    # rest, then turn on bullets.
    items.append(textbox("/slide[2]",
                         x="0.5in", y="1.2in", width="6in", height="4in",
                         text="Coffee preparation steps",
                         bold="true", size="18", color="1D3557"))
    for t in ("Grind beans to medium-fine",
              "Heat water to 93°C",
              "Bloom 30s with 2× coffee weight",
              "Pour remaining water in spirals",
              "Total brew time: 3-4 minutes"):
        items.append(paragraph("/slide[2]/shape[1]", text=t))
    # Turn paragraphs 2-6 into bullets (level 0). Paragraph 1 is the title.
    items.append(setp("/slide[2]/shape[1]", list="bullet"))

    # Numbered list (ordered)
    items.append(textbox("/slide[2]",
                         x="7in", y="1.2in", width="6in", height="4in",
                         text="Release checklist",
                         bold="true", size="18", color="1D3557"))
    for t in ("Run tests", "Tag the release", "Push to registry",
              "Announce in #releases"):
        items.append(paragraph("/slide[2]/shape[2]", text=t))
    items.append(setp("/slide[2]/shape[2]", list="numbered"))

    # Indented sub-bullet — level=1 on a paragraph nests it one step in.
    items.append(paragraph("/slide[2]/shape[2]",
                           text="(verify checksum)", level="1"))
    items.append(setp("/slide[2]/shape[2]", list="numbered"))

    # ===================================================================
    # Slide 3 — Styled runs (rich text within one paragraph)
    # ===================================================================
    items.append(slide())
    items.append(textbox("/slide[3]",
                         text="Rich Text — Runs", size="28", bold="true",
                         x="0.5in", y="0.3in", width="12in", height="0.6in"))

    # Empty paragraph that we'll fill with multiple runs of different styles.
    items.append(textbox("/slide[3]",
                         x="0.5in", y="1.5in", width="12in", height="1in",
                         text="", size="20"))
    items.append(run("/slide[3]/shape[1]/p[1]", text="The "))
    items.append(run("/slide[3]/shape[1]/p[1]", text="quick ", bold="true", color="E63946"))
    items.append(run("/slide[3]/shape[1]/p[1]", text="brown ", italic="true", color="A0522D"))
    items.append(run("/slide[3]/shape[1]/p[1]", text="fox jumps over the "))
    items.append(run("/slide[3]/shape[1]/p[1]", text="lazy ", underline="single", color="2A9D8F"))
    items.append(run("/slide[3]/shape[1]/p[1]", text="dog."))

    # Superscript / subscript via baseline
    items.append(textbox("/slide[3]",
                         x="0.5in", y="3in", width="12in", height="0.8in",
                         text="", size="24"))
    items.append(run("/slide[3]/shape[2]/p[1]", text="E = mc"))
    items.append(run("/slide[3]/shape[2]/p[1]", text="2", baseline="super"))
    items.append(run("/slide[3]/shape[2]/p[1]", text="    and H"))
    items.append(run("/slide[3]/shape[2]/p[1]", text="2", baseline="sub"))
    items.append(run("/slide[3]/shape[2]/p[1]", text="O"))

    # Strikethrough + colored
    items.append(textbox("/slide[3]",
                         x="0.5in", y="4.2in", width="12in", height="0.8in",
                         text="", size="20"))
    items.append(run("/slide[3]/shape[3]/p[1]",
                     text="OLD PRICE: $99   ", strike="single", color="999999"))
    items.append(run("/slide[3]/shape[3]/p[1]",
                     text="NOW $49!", bold="true", color="E63946", size="24"))

    # ===================================================================
    # Slide 4 — Per-script fonts (Latin + EastAsian) + vertical alignment
    # ===================================================================
    items.append(slide())
    items.append(textbox("/slide[4]",
                         text="Multilingual Fonts + Layout", size="28", bold="true",
                         x="0.5in", y="0.3in", width="12in", height="0.6in"))

    # Mixed-script box: separate fonts for Latin and EastAsian text.
    items.append(textbox("/slide[4]",
                         x="0.5in", y="1.5in", width="6in", height="2in",
                         fill="F1FAEE", margin="0.2in",
                         text="Hello, 世界! こんにちは、世界。",
                         size="24", bold="true",
                         **{"font.latin": "Georgia", "font.ea": "Yu Mincho"}))

    items.append(textbox("/slide[4]",
                         x="0.5in", y="3.7in", width="6in", height="0.5in",
                         text='font.latin=Georgia, font.ea="Yu Mincho"',
                         size="12", italic="true", color="666666"))

    # Vertical alignment within a tall box
    x = 7.0
    for va in ("top", "middle", "bottom"):
        items.append(textbox("/slide[4]",
                             x=f"{x}in", y="1.5in", width="2in", height="3in",
                             fill="A8DADC", margin="0.15in",
                             text=f"valign={va}", size="16", bold="true",
                             valign=va, align="center"))
        x += 2.2

    items.append(textbox("/slide[4]",
                         x="7in", y="4.8in", width="6in", height="0.5in",
                         text="valign + per-box margin + align=center",
                         size="12", italic="true", color="666666"))

    doc.batch(items)
    print(f"  added {len(items)} slides/shapes/paragraphs/runs")

print(f"Generated: {FILE}")
