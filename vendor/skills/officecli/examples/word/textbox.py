#!/usr/bin/env python3
r"""
Complex Textbox Showcase — generates textbox.docx exercising 10 advanced
textbox (WPS drawing / w:txbxContent) scenarios for testing officecli
compatibility: basic border+fill, multi-paragraph rich text, a nested table,
45-degree rotation + gradient, vertical text, rounded rectangle + shadow,
side-by-side metric cards, a borderless transparent box, fixed-height overflow,
and z-order stacking (behindDoc + translucent overlay).

Scenarios 1, 4, 5, 6, 7, 8, 9, 10 use the HIGH-LEVEL `add --type textbox` command:
the box (fill, border, gradient, rotation, vertical text, geometry, corner radius,
shadow, no-fill/no-line, wrap, position, z-order) is one `add` item, and its inner
paragraphs are formatted with `set` on the `/body/textbox[N]/p[M]` paths (bare
bold/italic/color/size/align keys — they apply to every run in the paragraph) plus
more `add` paragraph items.

Only scenarios 2 and 3 stay on `raw-set` with pre-authored DrawingML — they exercise
surface the high-level command does not expose (per-run mixed formatting inside one
paragraph, and a nested table). See textbox.md for the breakdown.

SDK twin of textbox.sh (officecli CLI). Both produce an equivalent
textbox.docx. This twin drives the **officecli Python SDK** (`pip install
officecli-sdk`): one resident is started and every item is shipped over the named
pipe in a single `doc.batch(...)` round-trip. Each item is the same
`{"command", ...}` dict you'd put in an `officecli batch` list — `add` items
carry `parent`/`type`/`props`, `set` items carry `path`/`props`, and `raw-set`
items carry `part`/`xpath`/`action`/`xml`. Because a batch runs in order and each
textbox is appended to the body, the textbox indices are deterministic:
S1=1, S2=2, S3=3, S4=4, S5=5, S6=6, S7=7/8/9, S8=10, S9=11, S10=12/13.

Usage:
  pip install officecli-sdk          # plus the `officecli` binary on PATH
  python3 textbox.py
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

FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "textbox.docx")


def para(text, **props):
    """One `add paragraph` item in batch-shape."""
    return {"command": "add", "parent": "/body", "type": "paragraph",
            "props": {"text": text, **props}}


def textbox(xml):
    """One `raw-set` item that injects a textbox paragraph before the body
    sectPr — the exact `officecli raw-set /document --xpath //w:body/w:sectPr
    --action insertbefore --xml ...` the .sh runs."""
    return {"command": "raw-set", "part": "/document",
            "xpath": "//w:body/w:sectPr", "action": "insertbefore", "xml": xml}


# ------------------------------------------------- high-level textbox helpers
# All scenarios except 2 and 3 are built from these batch items instead of raw XML.

def tb_add(**props):
    """`add --type textbox` batch item — creates the box + its first paragraph."""
    return {"command": "add", "parent": "/body", "type": "textbox", "props": props}


def tb_fmt(idx, p, **props):
    """`set` a textbox inner paragraph (bold/italic/color/size/align apply to all
    runs in that paragraph). idx = the textbox's document order, p = 1-based paragraph."""
    return {"command": "set", "path": f"/body/textbox[{idx}]/p[{p}]", "props": props}


def tb_para(idx, text):
    """Append a paragraph inside textbox #idx."""
    return {"command": "add", "parent": f"/body/textbox[{idx}]", "type": "paragraph",
            "props": {"text": text}}


def card_items(idx, title, big, label, fill, accent, offset):
    """Batch items for one S7 metric card (textbox #idx): rounded box + three
    centred paragraphs (accent title / big number / grey label)."""
    return [
        tb_add(text=title, geometry="roundRect", width="4.72cm", height="3.89cm",
               fill=fill, wrap="none", textAnchor="center",
               **{"line.color": accent, "line.width": "1pt",
                  "hRelative": "column", "anchor.x": offset}),
        tb_fmt(idx, 1, align="center", bold="true", color=accent, size="14"),
        tb_para(idx, big),
        tb_fmt(idx, 2, align="center", size="24"),
        tb_para(idx, label),
        tb_fmt(idx, 3, align="center", color="888888", size="9"),
    ]


# ---------------------------------------------------------------- raw textbox XML
# Scenarios 2 and 3 — the verbatim <w:p>...</w:p> wrappers kept on raw-set.

SCENARIO_2 = r'''
<w:p>
  <w:r>
    <w:rPr><w:noProof/></w:rPr>
    <mc:AlternateContent>
      <mc:Choice Requires="wps">
        <w:drawing>
          <wp:anchor distT="0" distB="0" distL="114300" distR="114300" simplePos="0" relativeHeight="251660288" behindDoc="0" locked="0" layoutInCell="1" allowOverlap="1">
            <wp:simplePos x="0" y="0"/>
            <wp:positionH relativeFrom="column"><wp:posOffset>0</wp:posOffset></wp:positionH>
            <wp:positionV relativeFrom="paragraph"><wp:posOffset>0</wp:posOffset></wp:positionV>
            <wp:extent cx="5400000" cy="2400000"/>
            <wp:effectExtent l="0" t="0" r="0" b="0"/>
            <wp:wrapTopAndBottom/>
            <wp:docPr id="2" name="TextBox 2"/>
            <a:graphic>
              <a:graphicData uri="http://schemas.microsoft.com/office/word/2010/wordprocessingShape">
                <wps:wsp>
                  <wps:cNvSpPr txBox="1"/>
                  <wps:spPr>
                    <a:xfrm><a:off x="0" y="0"/><a:ext cx="5400000" cy="2400000"/></a:xfrm>
                    <a:prstGeom prst="rect"><a:avLst/></a:prstGeom>
                    <a:solidFill><a:srgbClr val="FFFDE7"/></a:solidFill>
                    <a:ln w="19050"><a:solidFill><a:srgbClr val="FF8C00"/></a:solidFill><a:prstDash val="dash"/></a:ln>
                  </wps:spPr>
                  <wps:txbx>
                    <w:txbxContent>
                      <w:p><w:pPr><w:jc w:val="center"/></w:pPr><w:r><w:rPr><w:b/><w:sz w:val="32"/><w:color w:val="FF8C00"/></w:rPr><w:t>Rich Text Content</w:t></w:r></w:p>
                      <w:p><w:r><w:rPr><w:b/></w:rPr><w:t>Bold</w:t></w:r><w:r><w:t xml:space="preserve"> | </w:t></w:r><w:r><w:rPr><w:i/></w:rPr><w:t>Italic</w:t></w:r><w:r><w:t xml:space="preserve"> | </w:t></w:r><w:r><w:rPr><w:u w:val="single"/></w:rPr><w:t>Underline</w:t></w:r><w:r><w:t xml:space="preserve"> | </w:t></w:r><w:r><w:rPr><w:strike/></w:rPr><w:t>Strikethrough</w:t></w:r></w:p>
                      <w:p><w:r><w:rPr><w:color w:val="FF0000"/><w:sz w:val="20"/></w:rPr><w:t>Red small</w:t></w:r><w:r><w:t xml:space="preserve"> </w:t></w:r><w:r><w:rPr><w:color w:val="00B050"/><w:sz w:val="36"/></w:rPr><w:t>Green large</w:t></w:r><w:r><w:t xml:space="preserve"> </w:t></w:r><w:r><w:rPr><w:color w:val="0000FF"/><w:sz w:val="28"/><w:b/><w:i/></w:rPr><w:t>Blue bold italic</w:t></w:r></w:p>
                      <w:p><w:r><w:rPr><w:highlight w:val="yellow"/></w:rPr><w:t>Yellow highlight</w:t></w:r><w:r><w:t xml:space="preserve"> </w:t></w:r><w:r><w:rPr><w:highlight w:val="green"/><w:color w:val="FFFFFF"/></w:rPr><w:t>Green highlight white</w:t></w:r></w:p>
                      <w:p><w:pPr><w:jc w:val="right"/></w:pPr><w:r><w:rPr><w:rFonts w:ascii="Times New Roman" w:hAnsi="Times New Roman"/><w:i/><w:sz w:val="22"/></w:rPr><w:t>-- Right-aligned quote</w:t></w:r></w:p>
                    </w:txbxContent>
                  </wps:txbx>
                  <wps:bodyPr rot="0" vert="horz" wrap="square" lIns="91440" tIns="45720" rIns="91440" bIns="45720" anchor="t"/>
                </wps:wsp>
              </a:graphicData>
            </a:graphic>
          </wp:anchor>
        </w:drawing>
      </mc:Choice>
    </mc:AlternateContent>
  </w:r>
</w:p>'''

SCENARIO_3 = r'''
<w:p>
  <w:r>
    <w:rPr><w:noProof/></w:rPr>
    <mc:AlternateContent>
      <mc:Choice Requires="wps">
        <w:drawing>
          <wp:anchor distT="0" distB="0" distL="114300" distR="114300" simplePos="0" relativeHeight="251661312" behindDoc="0" locked="0" layoutInCell="1" allowOverlap="1">
            <wp:simplePos x="0" y="0"/>
            <wp:positionH relativeFrom="column"><wp:posOffset>0</wp:posOffset></wp:positionH>
            <wp:positionV relativeFrom="paragraph"><wp:posOffset>0</wp:posOffset></wp:positionV>
            <wp:extent cx="5400000" cy="2000000"/>
            <wp:effectExtent l="0" t="0" r="0" b="0"/>
            <wp:wrapTopAndBottom/>
            <wp:docPr id="3" name="TextBox 3"/>
            <a:graphic>
              <a:graphicData uri="http://schemas.microsoft.com/office/word/2010/wordprocessingShape">
                <wps:wsp>
                  <wps:cNvSpPr txBox="1"/>
                  <wps:spPr>
                    <a:xfrm><a:off x="0" y="0"/><a:ext cx="5400000" cy="2000000"/></a:xfrm>
                    <a:prstGeom prst="rect"><a:avLst/></a:prstGeom>
                    <a:solidFill><a:srgbClr val="F5F5F5"/></a:solidFill>
                    <a:ln w="12700"><a:solidFill><a:srgbClr val="333333"/></a:solidFill></a:ln>
                  </wps:spPr>
                  <wps:txbx>
                    <w:txbxContent>
                      <w:p><w:r><w:rPr><w:b/><w:sz w:val="24"/></w:rPr><w:t>Table inside textbox:</w:t></w:r></w:p>
                      <w:tbl>
                        <w:tblPr>
                          <w:tblStyle w:val="TableGrid"/>
                          <w:tblW w:w="5000" w:type="pct"/>
                          <w:tblBorders>
                            <w:top w:val="single" w:sz="4" w:space="0" w:color="auto"/>
                            <w:left w:val="single" w:sz="4" w:space="0" w:color="auto"/>
                            <w:bottom w:val="single" w:sz="4" w:space="0" w:color="auto"/>
                            <w:right w:val="single" w:sz="4" w:space="0" w:color="auto"/>
                            <w:insideH w:val="single" w:sz="4" w:space="0" w:color="auto"/>
                            <w:insideV w:val="single" w:sz="4" w:space="0" w:color="auto"/>
                          </w:tblBorders>
                        </w:tblPr>
                        <w:tblGrid><w:gridCol w:w="1800"/><w:gridCol w:w="1800"/><w:gridCol w:w="1800"/></w:tblGrid>
                        <w:tr>
                          <w:tc><w:tcPr><w:shd w:val="clear" w:color="auto" w:fill="4472C4"/></w:tcPr><w:p><w:r><w:rPr><w:b/><w:color w:val="FFFFFF"/></w:rPr><w:t>Name</w:t></w:r></w:p></w:tc>
                          <w:tc><w:tcPr><w:shd w:val="clear" w:color="auto" w:fill="4472C4"/></w:tcPr><w:p><w:r><w:rPr><w:b/><w:color w:val="FFFFFF"/></w:rPr><w:t>Department</w:t></w:r></w:p></w:tc>
                          <w:tc><w:tcPr><w:shd w:val="clear" w:color="auto" w:fill="4472C4"/></w:tcPr><w:p><w:r><w:rPr><w:b/><w:color w:val="FFFFFF"/></w:rPr><w:t>Score</w:t></w:r></w:p></w:tc>
                        </w:tr>
                        <w:tr>
                          <w:tc><w:p><w:r><w:t>John</w:t></w:r></w:p></w:tc>
                          <w:tc><w:p><w:r><w:t>Engineering</w:t></w:r></w:p></w:tc>
                          <w:tc><w:p><w:r><w:rPr><w:color w:val="00B050"/><w:b/></w:rPr><w:t>95</w:t></w:r></w:p></w:tc>
                        </w:tr>
                        <w:tr>
                          <w:tc><w:p><w:r><w:t>Sarah</w:t></w:r></w:p></w:tc>
                          <w:tc><w:p><w:r><w:t>Marketing</w:t></w:r></w:p></w:tc>
                          <w:tc><w:p><w:r><w:rPr><w:color w:val="FF0000"/><w:b/></w:rPr><w:t>78</w:t></w:r></w:p></w:tc>
                        </w:tr>
                      </w:tbl>
                      <w:p><w:r><w:rPr><w:i/><w:sz w:val="18"/><w:color w:val="888888"/></w:rPr><w:t>* Table nested inside a textbox</w:t></w:r></w:p>
                    </w:txbxContent>
                  </wps:txbx>
                  <wps:bodyPr rot="0" vert="horz" wrap="square" lIns="91440" tIns="45720" rIns="91440" bIns="45720" anchor="t"/>
                </wps:wsp>
              </a:graphicData>
            </a:graphic>
          </wp:anchor>
        </w:drawing>
      </mc:Choice>
    </mc:AlternateContent>
  </w:r>
</w:p>'''


print(f"Building {FILE} ...")

with officecli.create(FILE, "--force") as doc:
    items = [
        # ==================== Intro ====================
        para("Complex Textbox Examples", style="Heading1", align="center"),
        para("The following contains multiple complex textbox scenarios for "
             "testing textbox behavior under various conditions."),

        # Scenario 1 (HIGH-LEVEL, textbox[1]): solid fill + border + 2 paragraphs
        para("Scenario 1: Basic Textbox (with border and background)", style="Heading2"),
        tb_add(text="Basic Textbox", width="15cm", height="3.33cm",
               fill="E6F3FF", **{"line.color": "0070C0", "line.width": "2pt"},
               wrap="topAndBottom", textAnchor="top"),
        tb_fmt(1, 1, align="center", bold="true", color="0070C0", size="14"),
        tb_para(1, "This is a textbox with a blue border and light blue background. "
                   "It contains a centered title and a normal paragraph."),

        # Scenario 2: Multi-paragraph Rich Text Textbox
        para("Scenario 2: Multi-paragraph Rich Text Textbox", style="Heading2"),
        textbox(SCENARIO_2),

        # Scenario 3: Textbox with Nested Table
        para("Scenario 3: Textbox with Nested Table", style="Heading2"),
        textbox(SCENARIO_3),

        # Scenario 4 (HIGH-LEVEL, textbox[4]): rotation + gradient (comma stop list)
        para("Scenario 4: Rotated Textbox (45 degrees)", style="Heading2"),
        tb_add(text="Rotated 45", width="6.67cm", height="3.33cm", rotation="45",
               **{"fill.gradient": "FF6B6B,FFE66D", "line.color": "C0392B",
                  "line.width": "1.5pt", "anchor.x": "4.17cm"},
               wrap="topAndBottom", textAnchor="center", hRelative="column"),
        tb_fmt(4, 1, align="center", bold="true", color="FFFFFF", size="14"),
        tb_para(4, "Gradient + Rotation"),
        tb_fmt(4, 2, align="center", color="FFFFFF"),

        # Scenario 5 (HIGH-LEVEL, textbox[5]): vertical text flow
        para("Scenario 5: Vertical Text Textbox", style="Heading2"),
        tb_add(text="Vertical text content", width="2.22cm", height="6.67cm",
               fill="FFF0F5", **{"line.color": "8B0000", "line.width": "1pt"},
               textDirection="eaVert", wrap="topAndBottom", textAnchor="top"),
        tb_fmt(5, 1, align="center", bold="true", color="8B0000", size="18"),

        # Scenario 6 (HIGH-LEVEL, textbox[6]): roundRect + corner radius + shadow.
        # shadow=true's default blur/dist/dir/color/alpha match Word's preset.
        para("Scenario 6: Rounded Rectangle Textbox", style="Heading2"),
        tb_add(text="Rounded Rectangle + Shadow", width="15cm", height="4.17cm",
               geometry="roundRect", cornerRadius="16667", fill="E8F5E9", shadow="true",
               wrap="topAndBottom", textAnchor="center",
               **{"line.color": "2E7D32", "line.width": "2.25pt"}),
        tb_fmt(6, 1, align="center", bold="true", color="2E7D32", size="15"),
        tb_para(6, "This is a rounded rectangle textbox with an outer shadow effect."),
        tb_fmt(6, 2, align="center"),
        tb_para(6, "Uses geometry=roundRect + cornerRadius for rounded corners"),
        tb_fmt(6, 3, align="center", italic="true", color="666666"),

        # Scenario 7 (HIGH-LEVEL, textbox[7..9]): three floating metric cards.
        # Each add is its own host paragraph, so the cards sit at a slight
        # vertical stagger (the raw-XML original packed all three into one).
        para("Scenario 7: Side-by-side Textboxes (Card Layout)", style="Heading2"),
        *card_items(7, "Card A", "128",   "Daily Visits", "E3F2FD", "1565C0", "0cm"),
        *card_items(8, "Card B", "56",    "New Orders",   "FFF3E0", "E65100", "5.28cm"),
        *card_items(9, "Card C", "99.8%", "Uptime",       "E8F5E9", "2E7D32", "10.56cm"),

        # Scenario 8 (HIGH-LEVEL, textbox[10]): fill=none + line.color=none →
        # a fully invisible container (both sentinels emit a:noFill).
        para("Scenario 8: Borderless Transparent Textbox", style="Heading2"),
        tb_add(text="Borderless transparent text", width="11.11cm", height="2.22cm",
               fill="none", wrap="topAndBottom", textAnchor="center",
               **{"line.color": "none", "hRelative": "column", "anchor.x": "1.39cm"}),
        tb_fmt(10, 1, align="center", italic="true", size="22", color="AAAAAA"),

        # Scenario 9 (HIGH-LEVEL, textbox[11]): fixed height, autoFit omitted
        para("Scenario 9: Text Overflow Textbox", style="Heading2"),
        tb_add(text="Line 1: This is a fixed-height textbox with too much text to "
                    "test overflow behavior.", width="15cm", height="1.67cm",
               fill="FCE4EC", **{"line.color": "C62828", "line.width": "1pt"},
               wrap="topAndBottom", textAnchor="top"),
        tb_fmt(11, 1, bold="true", color="C62828"),
        tb_para(11, "Line 2: In real usage, the textbox height is limited but content can be long."),
        tb_para(11, "Line 3: Word usually auto-expands the textbox height, but fixed height may truncate."),
        tb_para(11, "Line 4: This line may be truncated or overflow, depending on bodyPr settings."),
        tb_para(11, "Line 5: Continuing to test more overflow content..."),
        tb_para(11, "Line 6: Final overflow line."),

        # Scenario 10 (HIGH-LEVEL, textbox[12..13]): behindDoc pushes the bottom
        # box behind body text; relativeHeight sets stacking order (higher=front);
        # the top box's fill.opacity=80 lets the bottom show through.
        para("Scenario 10: Textbox Stacking (Z-order)", style="Heading2"),
        tb_add(text="Bottom layer (behindDoc)", width="8.33cm", height="4.17cm",
               fill="BBDEFB", wrap="none", behindDoc="true", relativeHeight="251670528",
               textAnchor="top",
               **{"line.color": "1565C0", "line.width": "1.5pt",
                  "hRelative": "column", "anchor.x": "0.56cm"}),
        tb_fmt(12, 1, bold="true", color="1565C0", size="14"),
        tb_para(12, "This textbox is behind the document content."),
        tb_para(12, "It should be partially obscured by the top layer textbox."),
        tb_add(text="Top layer (translucent)", width="8.33cm", height="3.33cm",
               fill="FFCDD2", wrap="none", relativeHeight="251671552", textAnchor="top",
               **{"fill.opacity": "80", "line.color": "C62828", "line.width": "1.5pt",
                  "hRelative": "column", "anchor.x": "3.33cm",
                  "vRelative": "paragraph", "anchor.y": "1.11cm"}),
        tb_fmt(13, 1, bold="true", color="C62828", size="14"),
        tb_para(13, "This textbox is on top, 80% opacity."),
        tb_para(13, "It partially obscures the bottom blue textbox."),
    ]

    doc.batch(items)
    print(f"  added {len(items)} paragraphs/textboxes")

print(f"Generated: {FILE}")
