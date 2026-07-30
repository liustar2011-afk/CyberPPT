#!/usr/bin/env python3
"""
Shape typography — paragraph spacing, character spacing, kerning, case, BCP-47
lang, RTL direction, complex-script (Arabic) font slot. Covers the typography
props NOT touched by textboxes-basic.

SDK twin of shapes-typography.sh (officecli CLI). Both produce an equivalent
shapes-typography.pptx. This one drives the **officecli Python SDK**
(`pip install officecli-sdk`): one resident is started and every slide / shape /
paragraph is shipped over the named pipe in a single `doc.batch(...)`
round-trip. Each item is the same `{"command","parent","type","props"}` dict
you'd put in an `officecli batch` list.

Usage:
  pip install officecli-sdk          # plus the `officecli` binary on PATH
  python3 shapes-typography.py
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

FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "shapes-typography.pptx")

LOREM = ("Lorem ipsum dolor sit amet, consectetur adipiscing elit. "
         "Sed do eiusmod tempor incididunt.")
SAMPLE = "Tight Loose Spacing TYPOGRAPHY"


def slide():
    """One `add slide` item."""
    return {"command": "add", "parent": "/", "type": "slide", "props": {}}


def shape(parent, stype, **props):
    """One `add` item of arbitrary shape `type` under `parent`."""
    return {"command": "add", "parent": parent, "type": stype, "props": props}


print(f"Building {FILE} ...")

with officecli.create(FILE, "--force") as doc:
    items = [
        # =====================================================================
        # Slide 1 — Paragraph spacing (lineSpacing / spaceBefore / spaceAfter)
        # =====================================================================
        slide(),
        shape("/slide[1]", "textbox",
              text="lineSpacing / spaceBefore / spaceAfter", size="28", bold="true",
              x="0.5in", y="0.3in", width="12in", height="0.6in"),

        # Reference (tight spacing) — default. shape[2]
        shape("/slide[1]", "textbox",
              x="0.5in", y="1.2in", width="4in", height="3.5in",
              fill="F1FAEE", size="14", text=LOREM),
        shape("/slide[1]/shape[2]", "paragraph", text=LOREM),
        shape("/slide[1]/shape[2]", "paragraph", text=LOREM),

        shape("/slide[1]", "textbox",
              text="default (no spacing props set)", size="12", italic="true",
              x="0.5in", y="4.8in", width="4in", height="0.4in"),

        # lineSpacing=1.5x. shape[4]
        shape("/slide[1]", "textbox",
              x="5in", y="1.2in", width="4in", height="3.5in",
              fill="A8DADC", size="14", text=LOREM, lineSpacing="1.5x"),
        shape("/slide[1]/shape[4]", "paragraph", text=LOREM, lineSpacing="1.5x"),
        shape("/slide[1]/shape[4]", "paragraph", text=LOREM, lineSpacing="1.5x"),

        shape("/slide[1]", "textbox",
              text="lineSpacing=1.5x  (multiplier; also accepts 150% / 18pt)",
              size="12", italic="true",
              x="5in", y="4.8in", width="4in", height="0.4in"),

        # spaceBefore + spaceAfter on each paragraph. shape[6]
        shape("/slide[1]", "textbox",
              x="9.5in", y="1.2in", width="4in", height="3.5in",
              fill="F4A261", size="14", text=LOREM,
              spaceBefore="12pt", spaceAfter="12pt"),
        shape("/slide[1]/shape[6]", "paragraph", text=LOREM,
              spaceBefore="12pt", spaceAfter="12pt"),
        shape("/slide[1]/shape[6]", "paragraph", text=LOREM,
              spaceBefore="12pt", spaceAfter="12pt"),

        shape("/slide[1]", "textbox",
              text="spaceBefore=12pt  spaceAfter=12pt", size="12", italic="true",
              x="9.5in", y="4.8in", width="4in", height="0.4in"),

        # =====================================================================
        # Slide 2 — Character spacing, kerning, all/small caps
        # =====================================================================
        slide(),
        shape("/slide[2]", "textbox",
              text="spacing / kern / cap", size="28", bold="true",
              x="0.5in", y="0.3in", width="12in", height="0.6in"),

        # Character spacing (1/100 pt; positive = looser, negative = tighter)
        shape("/slide[2]", "textbox",
              x="0.5in", y="1.5in", width="13in", height="0.8in",
              size="22", bold="true", text=f"{SAMPLE}  (default)"),
        shape("/slide[2]", "textbox",
              x="0.5in", y="2.3in", width="13in", height="0.8in",
              size="22", bold="true", text=f"{SAMPLE}  (spacing=-50)",
              spacing="-50"),
        shape("/slide[2]", "textbox",
              x="0.5in", y="3.1in", width="13in", height="0.8in",
              size="22", bold="true", text=f"{SAMPLE}  (spacing=200)",
              spacing="200"),
        shape("/slide[2]", "textbox",
              x="0.5in", y="3.9in", width="13in", height="0.8in",
              size="22", bold="true", text=f"{SAMPLE}  (spacing=500)",
              spacing="500"),

        # Kerning threshold — min font size (1/100 pt) at which kerning kicks in
        shape("/slide[2]", "textbox",
              x="0.5in", y="5in", width="6in", height="0.8in",
              size="18", text="AVATAR  Yawning  (kern=1)  — kern on from 0.01pt",
              kern="1"),
        shape("/slide[2]", "textbox",
              x="7in", y="5in", width="6in", height="0.8in",
              size="18", text="AVATAR  Yawning  (kern=0)  — kern OFF",
              kern="0"),

        # Case rendering
        shape("/slide[2]", "textbox",
              x="0.5in", y="6in", width="4in", height="0.8in",
              size="18", text="cap=none — Default case", cap="none"),
        shape("/slide[2]", "textbox",
              x="4.7in", y="6in", width="4in", height="0.8in",
              size="18", text="cap=small — Small caps", cap="small"),
        shape("/slide[2]", "textbox",
              x="8.9in", y="6in", width="4in", height="0.8in",
              size="18", text="cap=all — All caps", cap="all"),

        # =====================================================================
        # Slide 3 — direction=rtl + font.cs (Arabic / complex-script)
        # =====================================================================
        slide(),
        shape("/slide[3]", "textbox",
              text="direction=rtl + font.cs (complex script)", size="28", bold="true",
              x="0.5in", y="0.3in", width="12in", height="0.6in"),

        # LTR Arabic — punctuation/digits end up in left-to-right order
        shape("/slide[3]", "textbox",
              x="0.5in", y="1.5in", width="6in", height="1.2in",
              fill="F1FAEE", size="24", bold="true",
              text="مرحبا بالعالم — 2026",
              **{"font.cs": "Arabic Typesetting"}),
        shape("/slide[3]", "textbox",
              text='direction=ltr (default)  +  font.cs="Arabic Typesetting"',
              size="12", italic="true", color="666666",
              x="0.5in", y="2.8in", width="6in", height="0.4in"),

        # RTL Arabic — paragraph flows right-to-left
        shape("/slide[3]", "textbox",
              x="7in", y="1.5in", width="6in", height="1.2in",
              fill="A8DADC", size="24", bold="true",
              text="مرحبا بالعالم — 2026",
              direction="rtl", align="right",
              **{"font.cs": "Arabic Typesetting"}),
        shape("/slide[3]", "textbox",
              text="direction=rtl  +  align=right  (aliases: dir, rtl)",
              size="12", italic="true", color="666666",
              x="7in", y="2.8in", width="6in", height="0.4in"),

        # Hebrew
        shape("/slide[3]", "textbox",
              x="0.5in", y="3.7in", width="12.5in", height="1.5in",
              fill="F4A261", size="24", bold="true",
              text="שלום עולם — Hebrew demo",
              direction="rtl", align="right",
              **{"font.cs": "Arial Hebrew"}),
        shape("/slide[3]", "textbox",
              text=("Same RTL machinery covers Hebrew, Urdu, Persian etc. — "
                    "pick the appropriate font.cs face."),
              size="12", italic="true", color="666666",
              x="0.5in", y="5.3in", width="12.5in", height="0.4in"),

        # =====================================================================
        # Slide 4 — Bare 'font' + BCP-47 lang tag
        # =====================================================================
        slide(),
        shape("/slide[4]", "textbox",
              text="font (bare) + lang BCP-47", size="28", bold="true",
              x="0.5in", y="0.3in", width="12in", height="0.6in"),

        # Bare 'font' targets BOTH Latin and EastAsian slots in one shot
        shape("/slide[4]", "textbox",
              x="0.5in", y="1.5in", width="6in", height="1.5in",
              fill="F1FAEE", size="22",
              text="Bare font sets Latin + EastAsian",
              font="Times New Roman"),
        shape("/slide[4]", "textbox",
              text='font="Times New Roman"  (sets a:latin AND a:ea)',
              size="12", italic="true",
              x="0.5in", y="3.1in", width="6in", height="0.4in"),

        shape("/slide[4]", "textbox",
              x="7in", y="1.5in", width="6in", height="1.5in",
              fill="A8DADC", size="22",
              text="Per-script gives finer control",
              **{"font.latin": "Georgia", "font.ea": "Yu Mincho"}),
        shape("/slide[4]", "textbox",
              text='font.latin=Georgia + font.ea="Yu Mincho"  (a:latin / a:ea)',
              size="12", italic="true",
              x="7in", y="3.1in", width="6in", height="0.4in"),

        # BCP-47 language tags — affects spellcheck, hyphenation, font fallback
        shape("/slide[4]", "textbox",
              x="0.5in", y="3.8in", width="4in", height="1in",
              fill="F4A261", size="18", text="Color or colour?", lang="en-GB"),
        shape("/slide[4]", "textbox",
              text="lang=en-GB  (British English spellcheck)",
              size="12", italic="true",
              x="0.5in", y="4.9in", width="4in", height="0.4in"),

        shape("/slide[4]", "textbox",
              x="4.7in", y="3.8in", width="4in", height="1in",
              fill="F4A261", size="18", text="Couleur en français", lang="fr-FR"),
        shape("/slide[4]", "textbox",
              text="lang=fr-FR", size="12", italic="true",
              x="4.7in", y="4.9in", width="4in", height="0.4in"),

        shape("/slide[4]", "textbox",
              x="8.9in", y="3.8in", width="4in", height="1in",
              fill="F4A261", size="18", text="日本語のテスト", lang="ja-JP",
              **{"font.ea": "Yu Mincho"}),
        shape("/slide[4]", "textbox",
              text='lang=ja-JP + font.ea="Yu Mincho"', size="12", italic="true",
              x="8.9in", y="4.9in", width="4in", height="0.4in"),

        # =====================================================================
        # Slide 5 — strike / underline / valign / margin / list / lineOpacity /
        #           animation
        # =====================================================================
        slide(),
        shape("/slide[5]", "textbox",
              text="strike / underline / valign / margin / list / lineOpacity / animation",
              size="22", bold="true",
              x="0.5in", y="0.3in", width="13in", height="0.6in"),

        # strike + underline — set at shape level (applied to all runs as default)
        shape("/slide[5]", "shape", geometry="roundRect",
              x="0.5in", y="1.2in", width="3.5in", height="1.2in",
              fill="F4A261", color="000000", size="18",
              text="strike=single", strike="single"),
        shape("/slide[5]", "shape", geometry="roundRect",
              x="4.3in", y="1.2in", width="3.5in", height="1.2in",
              fill="A8DADC", color="000000", size="18",
              text="underline=single", underline="single"),

        # valign — vertical text position inside the shape (top / middle / bottom)
        shape("/slide[5]", "shape", geometry="rect",
              x="0.5in", y="2.6in", width="3.5in", height="2in",
              fill="DEEAF6", lineColor="4472C4", lineWidth="2pt",
              text="valign=top", size="16", bold="true", valign="top"),
        shape("/slide[5]", "shape", geometry="rect",
              x="4.3in", y="2.6in", width="3.5in", height="2in",
              fill="DEEAF6", lineColor="4472C4", lineWidth="2pt",
              text="valign=middle", size="16", bold="true", valign="middle"),
        shape("/slide[5]", "shape", geometry="rect",
              x="8.1in", y="2.6in", width="3.5in", height="2in",
              fill="DEEAF6", lineColor="4472C4", lineWidth="2pt",
              text="valign=bottom", size="16", bold="true", valign="bottom"),

        # margin — inner text padding (uniform; also per-edge via marginLeft etc.)
        shape("/slide[5]", "shape", geometry="roundRect",
              x="0.5in", y="4.8in", width="4in", height="1.3in",
              fill="F1FAEE", lineColor="2A9D8F", lineWidth="2pt",
              text="margin=0.4in  — large inner padding", size="16",
              margin="0.4in"),

        # list — shape-level bullet/numbered list. Pass every item as ONE
        # multiline text block so the list style applies to all paragraphs;
        # paragraphs added after creation do NOT inherit the shape's list style.
        shape("/slide[5]", "shape", geometry="rect",
              x="5in", y="4.8in", width="4.2in", height="1.5in",
              fill="F4A261", color="000000", size="14",
              list="bullet",
              text="First item\nSecond item\nThird item"),

        # lineOpacity — outline transparency (0=opaque … 1=invisible); needs a line
        shape("/slide[5]", "shape", geometry="rect",
              x="0.5in", y="6.4in", width="4in", height="0.95in",
              fill="4472C4", lineColor="E63946", lineWidth="6pt",
              lineOpacity="0.35",
              text="lineOpacity=0.35", color="FFFFFF", size="14"),

        # animation — shape entrance animation (see animations.sh for full cover)
        shape("/slide[5]", "shape", geometry="roundRect",
              x="5in", y="6.4in", width="4.2in", height="0.95in",
              fill="E63946", color="FFFFFF", size="14", bold="true",
              text="animation=fadeIn", animation="fadeIn"),
    ]

    doc.batch(items)
    print(f"  added {len(items)} slides/shapes/paragraphs")

print(f"Generated: {FILE}")
