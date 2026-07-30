#!/usr/bin/env python3
r"""
Run / Character Formatting Showcase — generates run-formatting.docx exercising
the docx run (character) property surface: weight/style, underline variants +
color, strike/dstrike, case (caps/smallCaps), vertical align (super/subscript),
color/size/highlight, per-script fonts (latin/eastAsia/cs), text effects
(emboss/imprint/outline/shadow/vanish), character spacing/kerning/position,
language tagging, w14 (2010) text effects, character border, EastAsian layout,
run style, emphasis marks, and legacy/visibility effects.

Most lines set run formatting on the paragraph's implicit run via
`add ... type=paragraph`; the super/subscript and a few border/grid lines use
explicit `type=run` children (targeting `/body/p[last()]`) for mixed runs.

SDK twin of run-formatting.sh (officecli CLI). Both produce an equivalent
run-formatting.docx. This one drives the **officecli Python SDK**
(`pip install officecli-sdk`): one resident is started and every paragraph and
run is shipped over the named pipe in a single `doc.batch(...)` round-trip.
Each item is the same `{"command","parent","type","props"}` dict you'd put in
an `officecli batch` list. Within the batch, `/body/p[last()]` re-resolves
after each append, so a `type=run` item lands on the paragraph just added.

Usage:
  pip install officecli-sdk          # plus the `officecli` binary on PATH
  python3 run-formatting.py
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

FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "run-formatting.docx")


def para(text, **props):
    """One `add paragraph` item in batch-shape."""
    return {"command": "add", "parent": "/body", "type": "paragraph",
            "props": {"text": text, **props}}


def heading(text):
    """A section heading paragraph (matches the `heading()` helper in the .sh)."""
    return para(text, bold="true", size="14", color="1F4E79", spaceBefore="8pt")


def run(text, **props):
    """One `add run` item appended to the most recently added paragraph."""
    return {"command": "add", "parent": "/body/p[last()]", "type": "run",
            "props": {"text": text, **props}}


print(f"Building {FILE} ...")

with officecli.create(FILE, "--force") as doc:
    items = [
        para("Run / Character Formatting Showcase", align="center", bold="true", size="20"),

        # --- weight & style ---
        heading("Weight & style"),
        para("Bold text", bold="true"),
        para("Italic text", italic="true"),
        para("Bold + italic", bold="true", italic="true"),

        # --- underline variants + color ---
        heading("Underline"),
        para("single", underline="single"),
        para("double", underline="double"),
        para("thick", underline="thick"),
        para("dotted", underline="dotted"),
        para("wave (red)", underline="wave", **{"underline.color": "FF0000"}),

        # --- strikethrough ---
        heading("Strikethrough"),
        para("single strike", strike="true"),
        para("double strike", dstrike="true"),

        # --- case ---
        heading("Case"),
        para("all caps rendering", caps="true"),
        para("small caps rendering", smallcaps="true"),

        # --- vertical align: super / subscript (mixed runs) ---
        heading("Super / subscript"),
        para("E = mc"),
        run("2", superscript="true"),
        para("H"),
        run("2", subscript="true"),
        run("O"),

        # --- color / size / highlight ---
        heading("Color, size, highlight"),
        para("Red 16pt", color="C00000", size="16"),
        para("Highlighted", highlight="yellow"),

        # --- per-script fonts ---
        heading("Per-script fonts"),
        para("Latin Georgia + CJK 宋体", size="14",
             **{"font.latin": "Georgia", "font.eastAsia": "SimSun"}),

        # --- text effects ---
        heading("Text effects"),
        para("emboss", emboss="true"),
        para("imprint", imprint="true"),
        para("outline", outline="true"),
        para("shadow", shadow="true"),

        # --- character spacing / position ---
        heading("Character spacing & position"),
        para("expanded spacing", charSpacing="2pt"),
        para("raised 3pt", position="3pt"),

        # --- language ---
        heading("Language tag"),
        para("Tagged en-US for spellcheck", lang="en-US"),

        # --- complex-script (cs) variants ---
        heading("Complex-script variants"),
        para("cs bold + italic + 14pt",
             **{"bold.cs": "true", "italic.cs": "true", "size.cs": "14pt"}),
        para("Right-to-left run", rtl="true", direction="rtl"),

        # --- theme fonts (resolve against the document theme) ---
        heading("Theme fonts"),
        para("Latin/CS/EA theme fonts",
             **{"font.asciiTheme": "minorHAnsi", "font.hAnsiTheme": "minorHAnsi",
                "font.csTheme": "minorBidi", "font.eaTheme": "minorEastAsia"}),

        # --- explicit per-script fonts + the `font` shorthand ---
        heading("Per-script font keys"),
        para("font shorthand (all scripts)", font="Calibri"),
        para("cs + ea explicit fonts", **{"font.cs": "Arial", "font.ea": "SimSun"}),

        # --- per-script language tags ---
        heading("Per-script language"),
        para("lang per script (latin/ea/cs)",
             **{"lang.latin": "en-US", "lang.ea": "zh-CN", "lang.cs": "ar-SA"}),

        # --- run shading & hidden text ---
        heading("Run shading & hidden text"),
        para("Yellow run shading", shading="FFFF00"),
        para("Hidden (vanish) text", vanish="true"),
        para("No-proof (spellcheck off)", noproof="true"),

        # --- vertical alignment (vertAlign enum alias) ---
        heading("vertAlign enum"),
        para("vertAlign=superscript", vertAlign="superscript"),

        # --- WordprocessingML 2010 (w14) text effects ---
        heading("w14 text effects"),
        para("Text fill color", textFill="FF0000", size="16"),
        para("Text outline", textOutline="1pt-FF0000", size="16"),
        para("w14 glow", w14glow="FF0000", size="16"),
        para("w14 reflection", w14reflection="true", size="16"),
        para("w14 shadow", w14shadow="FF0000", size="16"),

        # --- character border, kerning, EastAsian layout, run style ---
        # kern / eastAsianLayout route to the paragraph's implicit run; bdr and a
        # run-level rStyle must be set on explicit type=run children (on a
        # paragraph, bdr/rStyle bind the paragraph border / paragraph-mark style).
        heading("Border, kerning, EastAsian layout, run style"),
        para("Kerning on (28 = 14pt threshold)", kern="28"),
        para("EastAsian layout 縦中横 (vert + combine)",
             **{"eastAsianLayout.vert": "true", "eastAsianLayout.combine": "true"}),
        para("Boxed run: "),
        run("single border", bdr="single"),
        run("  red 0.5pt", bdr="single;4;FF0000;0"),
        para("Run character style: "),
        run("Emphasis", rStyle="Emphasis"),

        # --- emphasis mark + legacy / visibility effects ---
        # These run keys are handled by the generic typed-attribute fallback (no
        # curated case in the handler) but still round-trip through add/set/get.
        # em = 着重号 (East-Asian emphasis dots): dot=above, underDot=below, circle.
        heading("Emphasis mark & visibility effects"),
        para("着重号 dots above (em=dot)", em="dot"),
        para("着重号 dots below (em=underDot)", em="underDot"),
        para("Circle emphasis (em=circle)", em="circle"),
        para("Legacy text animation (effect=blinkBackground)", effect="blinkBackground"),
        para("Hidden in web layout (webHidden)", webHidden="true"),
        para("Fit run to 1 inch (fitText=1440 twips)", fitText="1440"),
        # snapToGrid is also a paragraph property, so set it on an explicit run child to
        # demonstrate the run-level flag unambiguously; specVanish is run-only.
        para("Layout grid + special vanish: "),
        run("snapToGrid=false", snapToGrid="false"),
        run("  specVanish", specVanish="true"),
    ]

    doc.batch(items)
    print(f"  added {len(items)} paragraphs/runs")

print(f"Generated: {FILE}")
