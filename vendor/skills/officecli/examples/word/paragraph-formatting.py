#!/usr/bin/env python3
"""
Paragraph Formatting Showcase — generates paragraph-formatting.docx exercising
the docx paragraph property surface: alignment, indentation, spacing, pagination
flags, paragraph-level run formatting (applied to every run), shading, the
paragraph-mark run properties (markRPr.* — formatting of the ¶ glyph itself),
outline level, complex-script props, fonts, styles, tab stops, text frames
(framePr), paragraph borders (pBdr), vertical text alignment, EastAsian
typography toggles, line/hyphenation/indent flags, web/textbox hints, and list
numbering.

Note: paragraph-level `bold` etc. apply to all runs in the paragraph and read
back on the paragraph; `markRPr.bold` formats only the paragraph mark and is
distinct. Both are settable + gettable.

SDK twin of paragraph-formatting.sh (officecli CLI). Both produce an equivalent
paragraph-formatting.docx. This one drives the **officecli Python SDK**: one
resident is started and every paragraph is shipped over the named pipe in a
single `doc.batch(...)` round-trip. Each item is the same
`{"command","parent","type","props"}` dict you'd put in an `officecli batch` list.

Usage:
  pip install officecli-sdk          # plus the `officecli` binary on PATH
  python3 paragraph-formatting.py
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

FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                    "paragraph-formatting.docx")


def para(text, **props):
    """One `add paragraph` item in batch-shape."""
    return {"command": "add", "parent": "/body", "type": "paragraph",
            "props": {"text": text, **props}}


def heading(text):
    """Section heading paragraph — mirrors the `heading()` shell helper."""
    return para(text, bold="true", size="14", color="1F4E79", spaceBefore="10pt")


print(f"Building {FILE} ...")

with officecli.create(FILE, "--force") as doc:
    items = [
        para("Paragraph Formatting Showcase", align="center", bold="true", size="20"),

        # --- alignment ---
        heading("Alignment"),
        para("Left aligned (default)", align="left"),
        para("Center aligned", align="center"),
        para("Right aligned", align="right"),
        para("Justified text stretched edge to edge across the full measure of the line so both margins align.", align="both"),

        # --- indentation ---
        heading("Indentation"),
        para("Left indent 1cm", indent="1cm"),
        para("Right indent 2cm so the right edge pulls in.", rightIndent="2cm"),
        para("First-line indent — only the first line is pushed in from the left margin.", firstLineIndent="1cm"),
        para("Hanging indent — the first line hangs left while the rest of the paragraph is indented.", indent="1cm", hangingIndent="1cm"),

        # --- spacing ---
        heading("Spacing"),
        para("Space before 18pt, after 6pt", spaceBefore="18pt", spaceAfter="6pt"),
        para("Line spacing 1.5x across a longer paragraph that wraps so the extra leading between wrapped lines is visible.", lineSpacing="1.5x"),

        # --- pagination flags ---
        heading("Pagination flags"),
        para("keepNext — stays with the following paragraph", keepNext="true"),
        para("keepLines — lines stay together, never split across pages", keepLines="true"),
        para("widowControl on", widowControl="true"),

        # --- paragraph-level run formatting (applies to all runs) ---
        heading("Paragraph-level run formatting"),
        para("Whole paragraph bold + red + 13pt", bold="true", color="C00000", size="13"),
        para("Whole paragraph italic + highlighted", italic="true", highlight="yellow"),

        # --- shading ---
        heading("Shading"),
        para("Light gray paragraph shading", **{"shading.fill": "D9D9D9"}),
        para("Pale blue shading", **{"shading.fill": "DDEBF7"}),

        # --- paragraph-mark run props (the pilcrow itself) ---
        heading("Paragraph-mark formatting (markRPr)"),
        para("The mark glyph is bold+red (distinct from run text)",
             **{"markRPr.bold": "true", "markRPr.color": "C00000"}),

        # --- outline level ---
        heading("Outline level"),
        para("Outline level 1 (shows in document map)", outlineLvl="1"),

        # --- paragraph-level run formatting: strike / underline ---
        heading("Paragraph strike & underline"),
        para("Whole paragraph struck out", strike="true"),
        para("Underlined paragraph (red wave)", underline="wave", **{"underline.color": "#FF0000"}),

        # --- complex-script run props on the paragraph ---
        heading("Complex-script (cs)"),
        para("cs bold/italic/14pt + RTL",
             **{"bold.cs": "true", "italic.cs": "true", "size.cs": "14pt", "direction": "rtl"}),

        # --- spacing & pagination extras ---
        heading("Spacing & pagination extras"),
        para("contextualSpacing (collapse between same-style paras)", contextualSpacing="true"),
        para("lineSpacing 14pt, lineRule=atLeast", lineSpacing="14pt", lineRule="atLeast"),
        para("pageBreakBefore", pageBreakBefore="true"),
        para("wordWrap off (break long URLs anywhere)", wordWrap="false"),

        # --- chars-based indentation (CJK 1/100-char units) ---
        heading("Chars-based indent"),
        para("first-line 200 chars, hanging 100 chars", firstLineChars="200", hangingChars="100"),

        # --- fonts: explicit per-script + theme references ---
        heading("Fonts (explicit & theme)"),
        para("font shorthand Times New Roman", font="Times New Roman"),
        para("per-script latin/ea/cs",
             **{"font.latin": "Calibri", "font.ea": "SimSun", "font.cs": "Arial"}),
        para("theme fonts",
             **{"font.asciiTheme": "minorHAnsi", "font.hAnsiTheme": "minorHAnsi",
                "font.eaTheme": "minorEastAsia", "font.csTheme": "minorBidi"}),

        # --- styles ---
        heading("Styles"),
        para("Paragraph style Heading1", style="Heading1"),
        para("Character style on the run", rStyle="Emphasis"),

        # --- shading variants (shd shorthand + decomposed val/color) ---
        heading("Shading variants"),
        para("shd shorthand (yellow)", shd="FFFF00"),
        para("pct15 pattern, blue fill, red pattern color",
             **{"shading.val": "pct15", "shading.fill": "DDEBF7", "shading.color": "C00000"}),

        # --- tab stops ---
        heading("Tab stops"),
        para("Tabs at 720 and 1440 twips", tabs="720,1440"),

        # --- paragraph-mark run props (full markRPr set) ---
        heading("Paragraph-mark formatting (full markRPr)"),
        para("mark: italic/strike/underline/size/highlight/fonts",
             **{"markRPr.italic": "true", "markRPr.strike": "true", "markRPr.underline": "single",
                "markRPr.size": "14pt", "markRPr.highlight": "yellow",
                "markRPr.font.latin": "Georgia", "markRPr.font.ea": "SimSun", "markRPr.font.cs": "Arial"}),

        # --- text frame / drop-cap frame (framePr) ---
        # A framed paragraph floats in its own box (twips for w/h/hSpace/vSpace);
        # wrap=around lets body text flow around it, anchored to the margin.
        heading("Text frame (framePr)"),
        para("Framed paragraph — floats in a 3-inch box with text wrapping around it, anchored to the margin.",
             **{"framePr.w": "4320", "framePr.h": "720", "framePr.wrap": "around",
                "framePr.hAnchor": "margin", "framePr.vAnchor": "text",
                "framePr.hSpace": "180", "framePr.vSpace": "180"}),

        # --- paragraph borders (pBdr) ---
        # Whole-box shorthand (`border=...`) sets all four sides at once. Per-side
        # keys (border.top/border.bottom/border.left/border.right) are also
        # supported and take the same `style;size;color` value — mix for a partial box.
        heading("Paragraph borders (pBdr)"),
        para("Box border, all sides (single)", border="single"),
        para("Red 1pt box (style;size;color)", border="single;8;FF0000"),
        para("Per-side: top + bottom only (rule above and below)",
             **{"border.top": "single;8;0070C0", "border.bottom": "single;8;0070C0"}),

        # --- vertical text alignment within the line ---
        heading("Vertical text alignment"),
        para("textAlignment=center (glyphs centered on the line box)", textAlignment="center"),
        para("textAlignment=top", textAlignment="top"),

        # --- EastAsian typography toggles (handled via the generic fallback) ---
        heading("EastAsian typography"),
        para("kinsoku off — permit breaks at forbidden CJK chars", kinsoku="false"),
        para("autoSpace off — no auto gap between CJK and Latin/digits",
             autoSpaceDE="false", autoSpaceDN="false"),
        para("overflowPunct + topLinePunct on", overflowPunct="true", topLinePunct="true"),

        # --- line / hyphenation / indent flags ---
        heading("Line & indent flags"),
        para("suppressLineNumbers + suppressAutoHyphens",
             suppressLineNumbers="true", suppressAutoHyphens="true"),
        para("mirrorIndents on, adjustRightInd off, snapToGrid off",
             mirrorIndents="true", adjustRightInd="false", snapToGrid="false"),

        # --- web / textbox layout hints ---
        heading("Web / textbox hints"),
        para("divId (web division id) + textboxTightWrap=allLines",
             divId="123456", textboxTightWrap="allLines"),

        # --- list numbering (auto-created via listStyle; numId/numLevel reference it) ---
        heading("List numbering"),
        para("Bulleted item", listStyle="bullet"),
        para("Ordered item starting at 5", listStyle="ordered", start="5"),
        para("Explicit numId=1 level 0", numId="1", numLevel="0"),
    ]

    doc.batch(items)
    print(f"  added {len(items)} paragraphs")

print(f"Generated: {FILE}")
