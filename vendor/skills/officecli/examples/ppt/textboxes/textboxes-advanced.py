#!/usr/bin/env python3
"""
Advanced PPT textbox typography — per-paragraph and per-run overrides that the
basic example didn't reach. Each slide demonstrates a different scope:
  slide 1 — per-paragraph align / lineSpacing override (shape default vs paragraph)
  slide 2 — paragraph indents (indent / marginLeft / marginRight) for hanging-indent style
  slide 3 — per-paragraph styling (bold / italic / color / size / lang) without runs
  slide 4 — per-run typography (font / size / spacing / kern / lang) inside one paragraph
  slide 5 — subscript / superscript convenience aliases vs canonical baseline=
  slide 6 — name / zorder / autoFit / direction / font.cs (textbox-specific)

SDK twin of textboxes-advanced.sh (officecli CLI). Both produce an equivalent
textboxes-advanced.pptx. This one drives the **officecli Python SDK**
(`pip install officecli-sdk`): one resident is started and every slide, shape,
paragraph and run is shipped over the named pipe in a single `doc.batch(...)`
round-trip. Each item is the same `{"command","parent","type","props"}` dict
you'd put in an `officecli batch` list.

Usage:
  pip install officecli-sdk          # plus the `officecli` binary on PATH
  python3 textboxes-advanced.py
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

FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "textboxes-advanced.pptx")

LOREM = ("Lorem ipsum dolor sit amet, consectetur adipiscing elit. "
         "Vivamus lacinia odio vitae vestibulum vestibulum.")
LONGTEXT = ("Vivamus lacinia odio vitae vestibulum vestibulum. "
            "Sed molestie augue sit amet leo consequat posuere.")


def add(parent, type_, **props):
    """One `add` item in batch-shape."""
    return {"command": "add", "parent": parent, "type": type_, "props": props}


def slide():
    return {"command": "add", "parent": "/", "type": "slide", "props": {}}


print(f"Building {FILE} ...")

with officecli.create(FILE, "--force") as doc:
    items = [
        # =====================================================================
        # Slide 1 — Per-paragraph overrides (align / lineSpacing in one textbox)
        # =====================================================================
        slide(),
        add("/slide[1]", "textbox",
            text="Per-paragraph overrides inside one textbox",
            size="28", bold="true",
            x="0.5in", y="0.3in", width="12in", height="0.6in"),

        # One textbox; shape-level defaults are align=left, lineSpacing=1x.
        # Each paragraph overrides one of them.
        add("/slide[1]", "textbox",
            x="0.5in", y="1.2in", width="13in", height="5.5in",
            fill="F1FAEE", size="14",
            text=f"[shape default: align=left, single-spaced]  {LOREM}"),
        add("/slide[1]/shape[2]", "paragraph",
            text=f"[paragraph override: align=center]  {LOREM}", align="center"),
        add("/slide[1]/shape[2]", "paragraph",
            text=f"[paragraph override: align=right]  {LOREM}", align="right"),
        add("/slide[1]/shape[2]", "paragraph",
            text=f"[paragraph override: align=justify + lineSpacing=2x]  {LOREM} {LOREM}",
            align="justify", lineSpacing="2x"),
        add("/slide[1]/shape[2]", "paragraph",
            text=f"[paragraph override: lineSpacing=18pt fixed]  {LOREM}",
            lineSpacing="18pt"),

        # =====================================================================
        # Slide 2 — Paragraph indents (indent / marginLeft / marginRight)
        # =====================================================================
        slide(),
        add("/slide[2]", "textbox",
            text="Paragraph indents — indent / marginLeft / marginRight",
            size="28", bold="true",
            x="0.5in", y="0.3in", width="12in", height="0.6in"),

        # Reference (no indent)
        add("/slide[2]", "textbox",
            x="0.5in", y="1.3in", width="13in", height="1in",
            fill="F1FAEE", size="14",
            text=f"[default: no indent]  {LOREM} {LOREM}"),
        # Left indent (whole paragraph shifted right)
        add("/slide[2]", "textbox",
            x="0.5in", y="2.5in", width="13in", height="1in",
            fill="A8DADC", size="14",
            text=f"[marginLeft=1in]  {LOREM} {LOREM}",
            marginLeft="1in"),
        # First-line indent (only first line is shifted; rest flush left)
        add("/slide[2]", "textbox",
            x="0.5in", y="3.7in", width="13in", height="1in",
            fill="F4A261", size="14",
            text=f"[indent=0.5in first-line]  {LOREM} {LOREM}",
            indent="0.5in"),
        # Hanging indent (negative indent + positive marginLeft pulls first line back left)
        add("/slide[2]", "textbox",
            x="0.5in", y="4.9in", width="13in", height="1in",
            fill="A8DADC", size="14",
            text=f"[hanging: marginLeft=0.6in + indent=-0.5in]  {LOREM} {LOREM}",
            marginLeft="0.6in", indent="-0.5in"),
        # Right margin (text narrowed from the right)
        add("/slide[2]", "textbox",
            x="0.5in", y="6.1in", width="13in", height="1in",
            fill="F4A261", size="14",
            text=f"[marginRight=2in]  {LOREM} {LOREM}",
            marginRight="2in"),

        # =====================================================================
        # Slide 3 — Per-paragraph styling (bold / italic / color / size / lang)
        # =====================================================================
        slide(),
        add("/slide[3]", "textbox",
            text="Per-paragraph styling (no runs needed)",
            size="28", bold="true",
            x="0.5in", y="0.3in", width="12in", height="0.6in"),

        # One textbox; each paragraph carries its own bold/italic/color/size/lang.
        add("/slide[3]", "textbox",
            x="0.5in", y="1.2in", width="13in", height="5in",
            fill="F1FAEE", size="14",
            text="[shape default: 14pt black]  Default paragraph styling."),
        add("/slide[3]/shape[2]", "paragraph",
            text="[bold=true at paragraph level]  Whole paragraph is bold.",
            bold="true"),
        add("/slide[3]/shape[2]", "paragraph",
            text="[italic=true at paragraph level]  Whole paragraph is italic.",
            italic="true"),
        add("/slide[3]/shape[2]", "paragraph",
            text="[color=E63946 at paragraph level]  Whole paragraph is red.",
            color="E63946"),
        add("/slide[3]/shape[2]", "paragraph",
            text="[size=22 at paragraph level]  Whole paragraph is 22pt.",
            size="22"),
        add("/slide[3]/shape[2]", "paragraph",
            text="[lang=fr-FR at paragraph level]  Lorem ipsum dolor sit amet.",
            lang="fr-FR", color="2A9D8F"),

        # =====================================================================
        # Slide 4 — Per-run typography (font / size / spacing / kern / lang)
        # =====================================================================
        slide(),
        add("/slide[4]", "textbox",
            text="Per-run typography in one paragraph",
            size="28", bold="true",
            x="0.5in", y="0.3in", width="12in", height="0.6in"),

        # Empty textbox we'll build run-by-run
        add("/slide[4]", "textbox",
            x="0.5in", y="1.5in", width="13in", height="1in",
            text="", size="20"),
        add("/slide[4]/shape[1]/p[1]", "run", text="Mix "),
        add("/slide[4]/shape[1]/p[1]", "run",
            text="Times ", font="Times New Roman", size="24"),
        add("/slide[4]/shape[1]/p[1]", "run",
            text="Courier ", font="Courier New", size="18"),
        add("/slide[4]/shape[1]/p[1]", "run",
            text="Georgia", font="Georgia", size="28", bold="true"),

        # Per-run character spacing
        add("/slide[4]", "textbox",
            x="0.5in", y="3in", width="13in", height="1in",
            text="", size="20", bold="true"),
        add("/slide[4]/shape[2]/p[1]", "run", text="Normal "),
        add("/slide[4]/shape[2]/p[1]", "run",
            text="TIGHTENED ", spacing="-1", color="E63946"),
        add("/slide[4]/shape[2]/p[1]", "run",
            text="LOOSENED ", spacing="4", color="2A9D8F"),
        add("/slide[4]/shape[2]/p[1]", "run",
            text="EXPANDED", spacing="8", color="1D3557"),

        # Per-run kerning threshold
        add("/slide[4]", "textbox",
            x="0.5in", y="4.3in", width="13in", height="1in",
            text="", size="20", bold="true"),
        add("/slide[4]/shape[3]/p[1]", "run",
            text="AV AT WA — kern=0  ", kern="0"),
        add("/slide[4]/shape[3]/p[1]", "run",
            text="AV AT WA — kern=1", kern="1", color="E63946"),

        # Per-run lang tag (drives spellcheck per-run)
        add("/slide[4]", "textbox",
            x="0.5in", y="5.6in", width="13in", height="1in",
            text="", size="20"),
        add("/slide[4]/shape[4]/p[1]", "run",
            text="English: color  ", lang="en-US"),
        add("/slide[4]/shape[4]/p[1]", "run",
            text="British: colour  ", lang="en-GB", color="2A9D8F"),
        add("/slide[4]/shape[4]/p[1]", "run",
            text="Français: couleur", lang="fr-FR", color="E63946"),

        # =====================================================================
        # Slide 5 — subscript / superscript aliases vs canonical baseline=
        # =====================================================================
        slide(),
        add("/slide[5]", "textbox",
            text="subscript / superscript aliases",
            size="28", bold="true",
            x="0.5in", y="0.3in", width="12in", height="0.6in"),

        # Convenience form: subscript=true and superscript=true
        add("/slide[5]", "textbox",
            x="0.5in", y="1.5in", width="13in", height="1in",
            text="", size="24"),
        add("/slide[5]/shape[1]/p[1]", "run", text="H"),
        add("/slide[5]/shape[1]/p[1]", "run", text="2", subscript="true"),
        add("/slide[5]/shape[1]/p[1]", "run", text="SO"),
        add("/slide[5]/shape[1]/p[1]", "run", text="4", subscript="true"),
        add("/slide[5]/shape[1]/p[1]", "run", text="   x"),
        add("/slide[5]/shape[1]/p[1]", "run", text="2", superscript="true"),
        add("/slide[5]/shape[1]/p[1]", "run", text=" + y"),
        add("/slide[5]/shape[1]/p[1]", "run", text="2", superscript="true"),
        add("/slide[5]/shape[1]/p[1]", "run", text=" = r"),
        add("/slide[5]/shape[1]/p[1]", "run", text="2", superscript="true"),

        add("/slide[5]", "textbox",
            text="subscript=true   ≡   baseline=sub      superscript=true   ≡   baseline=super",
            size="14", italic="true", color="666666",
            x="0.5in", y="2.8in", width="13in", height="0.5in"),

        # Custom baseline percent — neither alias gives you this
        add("/slide[5]", "textbox",
            x="0.5in", y="3.7in", width="13in", height="1in",
            text="", size="24"),
        add("/slide[5]/shape[3]/p[1]", "run", text="Custom: "),
        add("/slide[5]/shape[3]/p[1]", "run",
            text="50%", baseline="50", color="E63946"),
        add("/slide[5]/shape[3]/p[1]", "run", text=" higher  /  "),
        add("/slide[5]/shape[3]/p[1]", "run",
            text="-40%", baseline="-40", color="2A9D8F"),
        add("/slide[5]/shape[3]/p[1]", "run", text=" lower"),

        add("/slide[5]", "textbox",
            text=("baseline= accepts signed integer percent (super≡+30, sub≡-25 by "
                  "convention). Custom values give arbitrary vertical offset."),
            size="14", italic="true", color="666666",
            x="0.5in", y="5in", width="13in", height="0.6in"),

        # Per-run case rendering — run Add accepts cap / allCaps / smallCaps
        add("/slide[5]", "textbox",
            x="0.5in", y="5.9in", width="13in", height="0.8in",
            text="", size="20", bold="true"),
        add("/slide[5]/shape[4]/p[1]", "run", text="default  "),
        add("/slide[5]/shape[4]/p[1]", "run",
            text="small caps  ", cap="small", color="2A9D8F"),
        add("/slide[5]/shape[4]/p[1]", "run",
            text="ALL CAPS", allCaps="true", color="E63946"),

        add("/slide[5]", "textbox",
            text="Per-run cap=small / cap=all / cap=none, plus allCaps / smallCaps boolean aliases.",
            size="12", italic="true", color="666666",
            x="0.5in", y="6.8in", width="13in", height="0.5in"),

        # =====================================================================
        # Slide 6 — name / zorder / autoFit / direction / font.cs
        # =====================================================================
        slide(),
        add("/slide[6]", "textbox",
            text="name / zorder / autoFit / direction / font.cs",
            size="28", bold="true",
            x="0.5in", y="0.3in", width="13in", height="0.6in"),

        # name= — label the textbox so it can be re-addressed by @name later
        add("/slide[6]", "textbox",
            x="0.5in", y="1.2in", width="5in", height="1.5in",
            fill="F1FAEE", size="16", bold="true",
            text="This is intro-box.",
            name="intro-box"),
        add("/slide[6]", "textbox",
            text='name="intro-box"  → addressable as /slide[6]/shape[@name=intro-box]',
            size="12", italic="true", color="666666",
            x="0.5in", y="2.8in", width="5in", height="0.5in"),

        # zorder= — three overlapping textboxes with explicit stack order
        add("/slide[6]", "textbox",
            x="6in", y="1.2in", width="3in", height="2in",
            fill="4472C4", color="FFFFFF", bold="true", size="16",
            text="back (zorder=1)",
            name="tb-back", zorder="1"),
        add("/slide[6]", "textbox",
            x="7in", y="1.6in", width="3in", height="2in",
            fill="E63946", color="FFFFFF", bold="true", size="16",
            text="mid (zorder=2)",
            name="tb-mid", zorder="2"),
        add("/slide[6]", "textbox",
            x="8in", y="2.0in", width="3in", height="2in",
            fill="2A9D8F", color="FFFFFF", bold="true", size="16",
            text="front (zorder=3)",
            name="tb-front", zorder="3"),
        add("/slide[6]", "textbox",
            text="zorder=  controls stack depth; aliases: z-order, order.",
            size="12", italic="true", color="666666",
            x="6in", y="4.2in", width="5in", height="0.5in"),

        # autoFit= — overflow behavior for textbox (same as shape)
        add("/slide[6]", "textbox",
            x="0.5in", y="3.6in", width="3in", height="1.2in",
            fill="FFE66D", size="16", text=LONGTEXT,
            autoFit="normal"),
        add("/slide[6]", "textbox",
            text="autoFit=normal  (shrinks text to fit)",
            size="12", italic="true", color="666666",
            x="0.5in", y="4.9in", width="3in", height="0.5in"),

        # direction=rtl — paragraph flows right-to-left inside a textbox
        add("/slide[6]", "textbox",
            x="0.5in", y="5.6in", width="5in", height="1.2in",
            fill="A8DADC", size="20", bold="true",
            text="مرحبا بالعالم — 2026",
            direction="rtl", align="right",
            **{"font.cs": "Arabic Typesetting"}),
        add("/slide[6]", "textbox",
            text='direction=rtl + font.cs="Arabic Typesetting"  (complex-script slot)',
            size="12", italic="true", color="666666",
            x="0.5in", y="6.9in", width="5in", height="0.5in"),
    ]

    doc.batch(items)
    print(f"  added {len(items)} slides/shapes/paragraphs/runs")
    doc.send({"command": "save"})

print(f"Generated: {FILE}")
