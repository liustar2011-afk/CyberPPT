#!/usr/bin/env python3
"""
The Art of Design — generates presentation.pptx, a visually rich 6-slide deck
built entirely from raw OOXML shape trees: deep gradient backgrounds, decorative
circles, gradient accent lines, stat cards, a quote slide, a process timeline,
and a closing slide.

SDK twin of presentation.sh (officecli CLI). Both produce an equivalent
presentation.pptx. This one drives the **officecli Python SDK**
(`pip install officecli-sdk`): one resident is started and every slide + every
raw-set shape injection is shipped over the named pipe in a single
`doc.batch(...)` round-trip.

The deck is built with the `raw-set` escape hatch (the same one the .sh uses):
each item is a batch dict whose `part` names the target slide and whose
`xpath`/`action`/`xml` fields drive `IDocumentHandler.RawSet` — exactly the
fields you'd pass to `officecli raw-set`. Slides themselves are plain
`add slide` items under `/presentation`.

Usage:
  pip install officecli-sdk          # plus the `officecli` binary on PATH
  python3 presentation.py
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

FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "presentation.pptx")


def slide():
    """One `add slide` item in batch-shape. Slides hang off the presentation
    root, so the parent is "/" (the resident/batch model; the CLI's positional
    /presentation maps to the same root)."""
    return {"command": "add", "parent": "/", "type": "slide"}


def bg(n, xml):
    """raw-set: prepend a <p:bg> into slide n's <p:cSld>."""
    return {"command": "raw-set", "part": f"/slide[{n}]",
            "xpath": "//p:cSld", "action": "prepend", "xml": xml}


def shape(n, xml):
    """raw-set: append a shape <p:sp> into slide n's <p:cSld>/<p:spTree>."""
    return {"command": "raw-set", "part": f"/slide[{n}]",
            "xpath": "//p:cSld/p:spTree", "action": "append", "xml": xml}


print(f"Building {FILE} ...")

with officecli.create(FILE, "--force") as doc:
    items = []

    # =========================================================================
    # SLIDE 1 — Title Slide
    # =========================================================================
    items.append(slide())

    # Full-bleed dark gradient background
    items.append(bg(1, '''
<p:bg>
  <p:bgPr>
    <a:gradFill rotWithShape="0">
      <a:gsLst>
        <a:gs pos="0"><a:srgbClr val="0D1B2A"/></a:gs>
        <a:gs pos="50000"><a:srgbClr val="1B2838"/></a:gs>
        <a:gs pos="100000"><a:srgbClr val="0A1628"/></a:gs>
      </a:gsLst>
      <a:lin ang="5400000" scaled="1"/>
    </a:gradFill>
    <a:effectLst/>
  </p:bgPr>
</p:bg>'''))

    # Decorative circle — top right (large, semi-transparent teal)
    items.append(shape(1, '''
<p:sp>
  <p:nvSpPr><p:cNvPr id="100" name="Deco Circle 1"/><p:cNvSpPr/><p:nvPr/></p:nvSpPr>
  <p:spPr>
    <a:xfrm><a:off x="8500000" y="-1200000"/><a:ext cx="4800000" cy="4800000"/></a:xfrm>
    <a:prstGeom prst="ellipse"><a:avLst/></a:prstGeom>
    <a:solidFill><a:srgbClr val="00B4D8"><a:alpha val="8000"/></a:srgbClr></a:solidFill>
    <a:ln><a:noFill/></a:ln>
  </p:spPr>
  <p:txBody><a:bodyPr/><a:lstStyle/><a:p><a:endParaRPr/></a:p></p:txBody>
</p:sp>'''))

    # Decorative circle — bottom left (lavender)
    items.append(shape(1, '''
<p:sp>
  <p:nvSpPr><p:cNvPr id="101" name="Deco Circle 2"/><p:cNvSpPr/><p:nvPr/></p:nvSpPr>
  <p:spPr>
    <a:xfrm><a:off x="-800000" y="4500000"/><a:ext cx="3200000" cy="3200000"/></a:xfrm>
    <a:prstGeom prst="ellipse"><a:avLst/></a:prstGeom>
    <a:solidFill><a:srgbClr val="E0AAFF"><a:alpha val="6000"/></a:srgbClr></a:solidFill>
    <a:ln><a:noFill/></a:ln>
  </p:spPr>
  <p:txBody><a:bodyPr/><a:lstStyle/><a:p><a:endParaRPr/></a:p></p:txBody>
</p:sp>'''))

    # Gradient accent line
    items.append(shape(1, '''
<p:sp>
  <p:nvSpPr><p:cNvPr id="102" name="Accent Line"/><p:cNvSpPr/><p:nvPr/></p:nvSpPr>
  <p:spPr>
    <a:xfrm><a:off x="800000" y="4200000"/><a:ext cx="5000000" cy="0"/></a:xfrm>
    <a:prstGeom prst="line"><a:avLst/></a:prstGeom>
    <a:ln w="28575">
      <a:gradFill>
        <a:gsLst>
          <a:gs pos="0"><a:srgbClr val="00B4D8"/></a:gs>
          <a:gs pos="100000"><a:srgbClr val="E0AAFF"/></a:gs>
        </a:gsLst>
        <a:lin ang="0" scaled="1"/>
      </a:gradFill>
    </a:ln>
  </p:spPr>
  <p:txBody><a:bodyPr/><a:lstStyle/><a:p><a:endParaRPr/></a:p></p:txBody>
</p:sp>'''))

    # Main title
    items.append(shape(1, '''
<p:sp>
  <p:nvSpPr><p:cNvPr id="103" name="Title"/><p:cNvSpPr txBox="1"/><p:nvPr/></p:nvSpPr>
  <p:spPr>
    <a:xfrm><a:off x="800000" y="1600000"/><a:ext cx="8000000" cy="1200000"/></a:xfrm>
    <a:prstGeom prst="rect"><a:avLst/></a:prstGeom>
    <a:noFill/><a:ln><a:noFill/></a:ln>
  </p:spPr>
  <p:txBody>
    <a:bodyPr wrap="square" anchor="b"/>
    <a:lstStyle/>
    <a:p>
      <a:pPr algn="l"/>
      <a:r>
        <a:rPr lang="en-US" sz="5400" b="1" dirty="0">
          <a:solidFill><a:srgbClr val="FFFFFF"/></a:solidFill>
          <a:latin typeface="Segoe UI"/>
        </a:rPr>
        <a:t>The Art of Design</a:t>
      </a:r>
    </a:p>
  </p:txBody>
</p:sp>'''))

    # Subtitle
    items.append(shape(1, '''
<p:sp>
  <p:nvSpPr><p:cNvPr id="104" name="Subtitle"/><p:cNvSpPr txBox="1"/><p:nvPr/></p:nvSpPr>
  <p:spPr>
    <a:xfrm><a:off x="800000" y="2900000"/><a:ext cx="8000000" cy="1100000"/></a:xfrm>
    <a:prstGeom prst="rect"><a:avLst/></a:prstGeom>
    <a:noFill/><a:ln><a:noFill/></a:ln>
  </p:spPr>
  <p:txBody>
    <a:bodyPr wrap="square" anchor="t"/>
    <a:lstStyle/>
    <a:p>
      <a:pPr algn="l"/>
      <a:r>
        <a:rPr lang="en-US" sz="2000" dirty="0">
          <a:solidFill><a:srgbClr val="90E0EF"/></a:solidFill>
          <a:latin typeface="Segoe UI"/>
        </a:rPr>
        <a:t>Crafting Beautiful Experiences</a:t>
      </a:r>
    </a:p>
    <a:p>
      <a:pPr algn="l"/>
      <a:r>
        <a:rPr lang="en-US" sz="1400" dirty="0" spc="600">
          <a:solidFill><a:srgbClr val="8B95A2"/></a:solidFill>
          <a:latin typeface="Segoe UI"/>
        </a:rPr>
        <a:t>SIMPLICITY  &#xB7;  ELEGANCE  &#xB7;  FUNCTION</a:t>
      </a:r>
    </a:p>
  </p:txBody>
</p:sp>'''))

    # Diamond accent
    items.append(shape(1, '''
<p:sp>
  <p:nvSpPr><p:cNvPr id="105" name="Diamond"/><p:cNvSpPr/><p:nvPr/></p:nvSpPr>
  <p:spPr>
    <a:xfrm rot="2700000"><a:off x="600000" y="4050000"/><a:ext cx="200000" cy="200000"/></a:xfrm>
    <a:prstGeom prst="rect"><a:avLst/></a:prstGeom>
    <a:solidFill><a:srgbClr val="00B4D8"/></a:solidFill>
    <a:ln><a:noFill/></a:ln>
  </p:spPr>
  <p:txBody><a:bodyPr/><a:lstStyle/><a:p><a:endParaRPr/></a:p></p:txBody>
</p:sp>'''))

    # =========================================================================
    # SLIDE 2 — Three Pillars
    # =========================================================================
    items.append(slide())

    items.append(bg(2,
        '<p:bg><p:bgPr><a:solidFill><a:srgbClr val="0D1B2A"/></a:solidFill>'
        '<a:effectLst/></p:bgPr></p:bg>'))

    # Section title
    items.append(shape(2, '''
<p:sp>
  <p:nvSpPr><p:cNvPr id="200" name="Section Title"/><p:cNvSpPr txBox="1"/><p:nvPr/></p:nvSpPr>
  <p:spPr>
    <a:xfrm><a:off x="800000" y="400000"/><a:ext cx="10592000" cy="900000"/></a:xfrm>
    <a:prstGeom prst="rect"><a:avLst/></a:prstGeom>
    <a:noFill/><a:ln><a:noFill/></a:ln>
  </p:spPr>
  <p:txBody>
    <a:bodyPr wrap="square" anchor="ctr"/>
    <a:lstStyle/>
    <a:p>
      <a:pPr algn="ctr"/>
      <a:r>
        <a:rPr lang="en-US" sz="3200" b="1" dirty="0">
          <a:solidFill><a:srgbClr val="FFFFFF"/></a:solidFill>
          <a:latin typeface="Segoe UI"/>
        </a:rPr>
        <a:t>Three Pillars of Great Design</a:t>
      </a:r>
    </a:p>
  </p:txBody>
</p:sp>'''))

    # Subtitle
    items.append(shape(2, '''
<p:sp>
  <p:nvSpPr><p:cNvPr id="201" name="SubLine"/><p:cNvSpPr txBox="1"/><p:nvPr/></p:nvSpPr>
  <p:spPr>
    <a:xfrm><a:off x="800000" y="1200000"/><a:ext cx="10592000" cy="400000"/></a:xfrm>
    <a:prstGeom prst="rect"><a:avLst/></a:prstGeom>
    <a:noFill/><a:ln><a:noFill/></a:ln>
  </p:spPr>
  <p:txBody>
    <a:bodyPr wrap="square" anchor="t"/>
    <a:lstStyle/>
    <a:p>
      <a:pPr algn="ctr"/>
      <a:r>
        <a:rPr lang="en-US" sz="1400" dirty="0">
          <a:solidFill><a:srgbClr val="8B95A2"/></a:solidFill>
          <a:latin typeface="Segoe UI"/>
        </a:rPr>
        <a:t>Every exceptional design is built upon these core principles</a:t>
      </a:r>
    </a:p>
  </p:txBody>
</p:sp>'''))

    # Card 1 — Simplicity
    items.append(shape(2, '''
<p:sp>
  <p:nvSpPr><p:cNvPr id="210" name="Card1"/><p:cNvSpPr/><p:nvPr/></p:nvSpPr>
  <p:spPr>
    <a:xfrm><a:off x="900000" y="2000000"/><a:ext cx="3200000" cy="4200000"/></a:xfrm>
    <a:prstGeom prst="roundRect"><a:avLst><a:gd name="adj" fmla="val 8000"/></a:avLst></a:prstGeom>
    <a:solidFill><a:srgbClr val="152238"/></a:solidFill>
    <a:ln w="12700"><a:solidFill><a:srgbClr val="1E3A5F"/></a:solidFill></a:ln>
  </p:spPr>
  <p:txBody>
    <a:bodyPr wrap="square" lIns="228600" tIns="228600" rIns="228600" bIns="228600" anchor="t"/>
    <a:lstStyle/>
    <a:p><a:pPr algn="ctr"/><a:r><a:rPr lang="en-US" sz="4800" dirty="0"><a:solidFill><a:srgbClr val="00B4D8"/></a:solidFill></a:rPr><a:t>&#x25CB;</a:t></a:r></a:p>
    <a:p><a:pPr algn="ctr"/><a:endParaRPr lang="en-US" sz="800"/></a:p>
    <a:p><a:pPr algn="ctr"/><a:r><a:rPr lang="en-US" sz="2400" b="1" dirty="0"><a:solidFill><a:srgbClr val="FFFFFF"/></a:solidFill><a:latin typeface="Segoe UI"/></a:rPr><a:t>Simplicity</a:t></a:r></a:p>
    <a:p><a:pPr algn="ctr"/><a:endParaRPr lang="en-US" sz="600"/></a:p>
    <a:p><a:pPr algn="ctr"/><a:r><a:rPr lang="en-US" sz="1200" dirty="0"><a:solidFill><a:srgbClr val="8B95A2"/></a:solidFill><a:latin typeface="Segoe UI"/></a:rPr><a:t>Less is more. Strip away the unnecessary to let the essential shine through.</a:t></a:r></a:p>
  </p:txBody>
</p:sp>'''))

    # Card 2 — Hierarchy
    items.append(shape(2, '''
<p:sp>
  <p:nvSpPr><p:cNvPr id="211" name="Card2"/><p:cNvSpPr/><p:nvPr/></p:nvSpPr>
  <p:spPr>
    <a:xfrm><a:off x="4496000" y="2000000"/><a:ext cx="3200000" cy="4200000"/></a:xfrm>
    <a:prstGeom prst="roundRect"><a:avLst><a:gd name="adj" fmla="val 8000"/></a:avLst></a:prstGeom>
    <a:solidFill><a:srgbClr val="152238"/></a:solidFill>
    <a:ln w="12700"><a:solidFill><a:srgbClr val="1E3A5F"/></a:solidFill></a:ln>
  </p:spPr>
  <p:txBody>
    <a:bodyPr wrap="square" lIns="228600" tIns="228600" rIns="228600" bIns="228600" anchor="t"/>
    <a:lstStyle/>
    <a:p><a:pPr algn="ctr"/><a:r><a:rPr lang="en-US" sz="4800" dirty="0"><a:solidFill><a:srgbClr val="E0AAFF"/></a:solidFill></a:rPr><a:t>&#x25B3;</a:t></a:r></a:p>
    <a:p><a:pPr algn="ctr"/><a:endParaRPr lang="en-US" sz="800"/></a:p>
    <a:p><a:pPr algn="ctr"/><a:r><a:rPr lang="en-US" sz="2400" b="1" dirty="0"><a:solidFill><a:srgbClr val="FFFFFF"/></a:solidFill><a:latin typeface="Segoe UI"/></a:rPr><a:t>Hierarchy</a:t></a:r></a:p>
    <a:p><a:pPr algn="ctr"/><a:endParaRPr lang="en-US" sz="600"/></a:p>
    <a:p><a:pPr algn="ctr"/><a:r><a:rPr lang="en-US" sz="1200" dirty="0"><a:solidFill><a:srgbClr val="8B95A2"/></a:solidFill><a:latin typeface="Segoe UI"/></a:rPr><a:t>Guide the eye with size, color, and space. Create a clear visual flow.</a:t></a:r></a:p>
  </p:txBody>
</p:sp>'''))

    # Card 3 — Harmony
    items.append(shape(2, '''
<p:sp>
  <p:nvSpPr><p:cNvPr id="212" name="Card3"/><p:cNvSpPr/><p:nvPr/></p:nvSpPr>
  <p:spPr>
    <a:xfrm><a:off x="8092000" y="2000000"/><a:ext cx="3200000" cy="4200000"/></a:xfrm>
    <a:prstGeom prst="roundRect"><a:avLst><a:gd name="adj" fmla="val 8000"/></a:avLst></a:prstGeom>
    <a:solidFill><a:srgbClr val="152238"/></a:solidFill>
    <a:ln w="12700"><a:solidFill><a:srgbClr val="1E3A5F"/></a:solidFill></a:ln>
  </p:spPr>
  <p:txBody>
    <a:bodyPr wrap="square" lIns="228600" tIns="228600" rIns="228600" bIns="228600" anchor="t"/>
    <a:lstStyle/>
    <a:p><a:pPr algn="ctr"/><a:r><a:rPr lang="en-US" sz="4800" dirty="0"><a:solidFill><a:srgbClr val="FFD166"/></a:solidFill></a:rPr><a:t>&#x25C7;</a:t></a:r></a:p>
    <a:p><a:pPr algn="ctr"/><a:endParaRPr lang="en-US" sz="800"/></a:p>
    <a:p><a:pPr algn="ctr"/><a:r><a:rPr lang="en-US" sz="2400" b="1" dirty="0"><a:solidFill><a:srgbClr val="FFFFFF"/></a:solidFill><a:latin typeface="Segoe UI"/></a:rPr><a:t>Harmony</a:t></a:r></a:p>
    <a:p><a:pPr algn="ctr"/><a:endParaRPr lang="en-US" sz="600"/></a:p>
    <a:p><a:pPr algn="ctr"/><a:r><a:rPr lang="en-US" sz="1200" dirty="0"><a:solidFill><a:srgbClr val="8B95A2"/></a:solidFill><a:latin typeface="Segoe UI"/></a:rPr><a:t>Consistent color, type, and layout create a professional, cohesive experience.</a:t></a:r></a:p>
  </p:txBody>
</p:sp>'''))

    # =========================================================================
    # SLIDE 3 — Data Showcase
    # =========================================================================
    items.append(slide())

    items.append(bg(3,
        '<p:bg><p:bgPr><a:gradFill rotWithShape="0"><a:gsLst>'
        '<a:gs pos="0"><a:srgbClr val="0D1B2A"/></a:gs>'
        '<a:gs pos="100000"><a:srgbClr val="152238"/></a:gs></a:gsLst>'
        '<a:lin ang="2700000" scaled="1"/></a:gradFill><a:effectLst/></p:bgPr></p:bg>'))

    # Title
    items.append(shape(3, '''
<p:sp>
  <p:nvSpPr><p:cNvPr id="300" name="DataTitle"/><p:cNvSpPr txBox="1"/><p:nvPr/></p:nvSpPr>
  <p:spPr>
    <a:xfrm><a:off x="800000" y="300000"/><a:ext cx="10592000" cy="700000"/></a:xfrm>
    <a:prstGeom prst="rect"><a:avLst/></a:prstGeom><a:noFill/><a:ln><a:noFill/></a:ln>
  </p:spPr>
  <p:txBody>
    <a:bodyPr wrap="square" anchor="ctr"/><a:lstStyle/>
    <a:p><a:pPr algn="l"/><a:r><a:rPr lang="en-US" sz="2800" b="1" dirty="0"><a:solidFill><a:srgbClr val="FFFFFF"/></a:solidFill><a:latin typeface="Segoe UI"/></a:rPr><a:t>Data-Driven Design</a:t></a:r></a:p>
  </p:txBody>
</p:sp>'''))

    # Gradient accent bar
    items.append(shape(3, '''
<p:sp>
  <p:nvSpPr><p:cNvPr id="301" name="Bar"/><p:cNvSpPr/><p:nvPr/></p:nvSpPr>
  <p:spPr>
    <a:xfrm><a:off x="800000" y="1050000"/><a:ext cx="3000000" cy="50000"/></a:xfrm>
    <a:prstGeom prst="rect"><a:avLst/></a:prstGeom>
    <a:gradFill><a:gsLst><a:gs pos="0"><a:srgbClr val="00B4D8"/></a:gs><a:gs pos="100000"><a:srgbClr val="E0AAFF"/></a:gs></a:gsLst><a:lin ang="0" scaled="1"/></a:gradFill>
    <a:ln><a:noFill/></a:ln>
  </p:spPr>
  <p:txBody><a:bodyPr/><a:lstStyle/><a:p><a:endParaRPr/></a:p></p:txBody>
</p:sp>'''))

    # Stat card 1 — 98%
    items.append(shape(3, '''
<p:sp>
  <p:nvSpPr><p:cNvPr id="310" name="Stat1"/><p:cNvSpPr txBox="1"/><p:nvPr/></p:nvSpPr>
  <p:spPr>
    <a:xfrm><a:off x="800000" y="1500000"/><a:ext cx="3400000" cy="2200000"/></a:xfrm>
    <a:prstGeom prst="roundRect"><a:avLst><a:gd name="adj" fmla="val 6000"/></a:avLst></a:prstGeom>
    <a:solidFill><a:srgbClr val="0E2540"/></a:solidFill>
    <a:ln w="19050"><a:gradFill><a:gsLst><a:gs pos="0"><a:srgbClr val="00B4D8"/></a:gs><a:gs pos="100000"><a:srgbClr val="0077B6"/></a:gs></a:gsLst><a:lin ang="5400000" scaled="1"/></a:gradFill></a:ln>
  </p:spPr>
  <p:txBody>
    <a:bodyPr wrap="square" lIns="228600" tIns="182880" rIns="228600" bIns="182880" anchor="ctr"/><a:lstStyle/>
    <a:p><a:pPr algn="ctr"/><a:r><a:rPr lang="en-US" sz="5600" b="1" dirty="0"><a:solidFill><a:srgbClr val="00B4D8"/></a:solidFill><a:latin typeface="Segoe UI"/></a:rPr><a:t>98%</a:t></a:r></a:p>
    <a:p><a:pPr algn="ctr"/><a:r><a:rPr lang="en-US" sz="1400" dirty="0"><a:solidFill><a:srgbClr val="8B95A2"/></a:solidFill><a:latin typeface="Segoe UI"/></a:rPr><a:t>User Satisfaction</a:t></a:r></a:p>
  </p:txBody>
</p:sp>'''))

    # Stat card 2 — 2.5M
    items.append(shape(3, '''
<p:sp>
  <p:nvSpPr><p:cNvPr id="311" name="Stat2"/><p:cNvSpPr txBox="1"/><p:nvPr/></p:nvSpPr>
  <p:spPr>
    <a:xfrm><a:off x="4500000" y="1500000"/><a:ext cx="3400000" cy="2200000"/></a:xfrm>
    <a:prstGeom prst="roundRect"><a:avLst><a:gd name="adj" fmla="val 6000"/></a:avLst></a:prstGeom>
    <a:solidFill><a:srgbClr val="0E2540"/></a:solidFill>
    <a:ln w="19050"><a:gradFill><a:gsLst><a:gs pos="0"><a:srgbClr val="E0AAFF"/></a:gs><a:gs pos="100000"><a:srgbClr val="9B5DE5"/></a:gs></a:gsLst><a:lin ang="5400000" scaled="1"/></a:gradFill></a:ln>
  </p:spPr>
  <p:txBody>
    <a:bodyPr wrap="square" lIns="228600" tIns="182880" rIns="228600" bIns="182880" anchor="ctr"/><a:lstStyle/>
    <a:p><a:pPr algn="ctr"/><a:r><a:rPr lang="en-US" sz="5600" b="1" dirty="0"><a:solidFill><a:srgbClr val="E0AAFF"/></a:solidFill><a:latin typeface="Segoe UI"/></a:rPr><a:t>2.5M</a:t></a:r></a:p>
    <a:p><a:pPr algn="ctr"/><a:r><a:rPr lang="en-US" sz="1400" dirty="0"><a:solidFill><a:srgbClr val="8B95A2"/></a:solidFill><a:latin typeface="Segoe UI"/></a:rPr><a:t>Monthly Active Users</a:t></a:r></a:p>
  </p:txBody>
</p:sp>'''))

    # Stat card 3 — 47ms
    items.append(shape(3, '''
<p:sp>
  <p:nvSpPr><p:cNvPr id="312" name="Stat3"/><p:cNvSpPr txBox="1"/><p:nvPr/></p:nvSpPr>
  <p:spPr>
    <a:xfrm><a:off x="8200000" y="1500000"/><a:ext cx="3400000" cy="2200000"/></a:xfrm>
    <a:prstGeom prst="roundRect"><a:avLst><a:gd name="adj" fmla="val 6000"/></a:avLst></a:prstGeom>
    <a:solidFill><a:srgbClr val="0E2540"/></a:solidFill>
    <a:ln w="19050"><a:gradFill><a:gsLst><a:gs pos="0"><a:srgbClr val="FFD166"/></a:gs><a:gs pos="100000"><a:srgbClr val="F48C06"/></a:gs></a:gsLst><a:lin ang="5400000" scaled="1"/></a:gradFill></a:ln>
  </p:spPr>
  <p:txBody>
    <a:bodyPr wrap="square" lIns="228600" tIns="182880" rIns="228600" bIns="182880" anchor="ctr"/><a:lstStyle/>
    <a:p><a:pPr algn="ctr"/><a:r><a:rPr lang="en-US" sz="5600" b="1" dirty="0"><a:solidFill><a:srgbClr val="FFD166"/></a:solidFill><a:latin typeface="Segoe UI"/></a:rPr><a:t>47ms</a:t></a:r></a:p>
    <a:p><a:pPr algn="ctr"/><a:r><a:rPr lang="en-US" sz="1400" dirty="0"><a:solidFill><a:srgbClr val="8B95A2"/></a:solidFill><a:latin typeface="Segoe UI"/></a:rPr><a:t>Avg Response Time</a:t></a:r></a:p>
  </p:txBody>
</p:sp>'''))

    # Bottom description
    items.append(shape(3, '''
<p:sp>
  <p:nvSpPr><p:cNvPr id="320" name="Desc"/><p:cNvSpPr txBox="1"/><p:nvPr/></p:nvSpPr>
  <p:spPr>
    <a:xfrm><a:off x="800000" y="4200000"/><a:ext cx="10592000" cy="2200000"/></a:xfrm>
    <a:prstGeom prst="rect"><a:avLst/></a:prstGeom><a:noFill/><a:ln><a:noFill/></a:ln>
  </p:spPr>
  <p:txBody>
    <a:bodyPr wrap="square" anchor="t"/><a:lstStyle/>
    <a:p><a:pPr algn="l"/><a:r><a:rPr lang="en-US" sz="1400" dirty="0"><a:solidFill><a:srgbClr val="8B95A2"/></a:solidFill><a:latin typeface="Segoe UI"/></a:rPr><a:t>Numbers tell stories. Through thoughtful visual design, every data point</a:t></a:r></a:p>
    <a:p><a:pPr algn="l"/><a:r><a:rPr lang="en-US" sz="1400" dirty="0"><a:solidFill><a:srgbClr val="8B95A2"/></a:solidFill><a:latin typeface="Segoe UI"/></a:rPr><a:t>communicates its meaning at first glance.</a:t></a:r></a:p>
  </p:txBody>
</p:sp>'''))

    # =========================================================================
    # SLIDE 4 — Quote Slide
    # =========================================================================
    items.append(slide())

    items.append(bg(4,
        '<p:bg><p:bgPr><a:gradFill rotWithShape="0"><a:gsLst>'
        '<a:gs pos="0"><a:srgbClr val="1B2838"/></a:gs>'
        '<a:gs pos="50000"><a:srgbClr val="0D1B2A"/></a:gs>'
        '<a:gs pos="100000"><a:srgbClr val="1B2838"/></a:gs></a:gsLst>'
        '<a:lin ang="2700000" scaled="1"/></a:gradFill><a:effectLst/></p:bgPr></p:bg>'))

    # Large quote mark
    items.append(shape(4, '''
<p:sp>
  <p:nvSpPr><p:cNvPr id="400" name="QuoteMark"/><p:cNvSpPr txBox="1"/><p:nvPr/></p:nvSpPr>
  <p:spPr>
    <a:xfrm><a:off x="1000000" y="800000"/><a:ext cx="3000000" cy="2000000"/></a:xfrm>
    <a:prstGeom prst="rect"><a:avLst/></a:prstGeom><a:noFill/><a:ln><a:noFill/></a:ln>
  </p:spPr>
  <p:txBody>
    <a:bodyPr wrap="square" anchor="t"/><a:lstStyle/>
    <a:p><a:pPr algn="l"/><a:r><a:rPr lang="en-US" sz="12000" dirty="0"><a:solidFill><a:srgbClr val="00B4D8"><a:alpha val="20000"/></a:srgbClr></a:solidFill><a:latin typeface="Georgia"/></a:rPr><a:t>&#x201C;</a:t></a:r></a:p>
  </p:txBody>
</p:sp>'''))

    # Quote text
    items.append(shape(4, '''
<p:sp>
  <p:nvSpPr><p:cNvPr id="401" name="Quote"/><p:cNvSpPr txBox="1"/><p:nvPr/></p:nvSpPr>
  <p:spPr>
    <a:xfrm><a:off x="1500000" y="2000000"/><a:ext cx="9192000" cy="2000000"/></a:xfrm>
    <a:prstGeom prst="rect"><a:avLst/></a:prstGeom><a:noFill/><a:ln><a:noFill/></a:ln>
  </p:spPr>
  <p:txBody>
    <a:bodyPr wrap="square" anchor="ctr"/><a:lstStyle/>
    <a:p><a:pPr algn="ctr"/><a:r><a:rPr lang="en-US" sz="2800" i="1" dirty="0"><a:solidFill><a:srgbClr val="FFFFFF"/></a:solidFill><a:latin typeface="Georgia"/></a:rPr><a:t>Good design is obvious.</a:t></a:r></a:p>
    <a:p><a:pPr algn="ctr"/><a:r><a:rPr lang="en-US" sz="2800" i="1" dirty="0"><a:solidFill><a:srgbClr val="FFFFFF"/></a:solidFill><a:latin typeface="Georgia"/></a:rPr><a:t>Great design is transparent.</a:t></a:r></a:p>
  </p:txBody>
</p:sp>'''))

    # Attribution
    items.append(shape(4, '''
<p:sp>
  <p:nvSpPr><p:cNvPr id="402" name="Author"/><p:cNvSpPr txBox="1"/><p:nvPr/></p:nvSpPr>
  <p:spPr>
    <a:xfrm><a:off x="1500000" y="4200000"/><a:ext cx="9192000" cy="600000"/></a:xfrm>
    <a:prstGeom prst="rect"><a:avLst/></a:prstGeom><a:noFill/><a:ln><a:noFill/></a:ln>
  </p:spPr>
  <p:txBody>
    <a:bodyPr wrap="square" anchor="t"/><a:lstStyle/>
    <a:p><a:pPr algn="ctr"/><a:r><a:rPr lang="en-US" sz="1600" dirty="0"><a:solidFill><a:srgbClr val="00B4D8"/></a:solidFill><a:latin typeface="Segoe UI"/></a:rPr><a:t>&#x2014; Joe Sparano</a:t></a:r></a:p>
  </p:txBody>
</p:sp>'''))

    # Decorative line under quote
    items.append(shape(4, '''
<p:sp>
  <p:nvSpPr><p:cNvPr id="403" name="QuoteLine"/><p:cNvSpPr/><p:nvPr/></p:nvSpPr>
  <p:spPr>
    <a:xfrm><a:off x="5096000" y="5000000"/><a:ext cx="2000000" cy="0"/></a:xfrm>
    <a:prstGeom prst="line"><a:avLst/></a:prstGeom>
    <a:ln w="19050"><a:gradFill><a:gsLst><a:gs pos="0"><a:srgbClr val="00B4D8"><a:alpha val="0"/></a:srgbClr></a:gs><a:gs pos="50000"><a:srgbClr val="00B4D8"/></a:gs><a:gs pos="100000"><a:srgbClr val="00B4D8"><a:alpha val="0"/></a:srgbClr></a:gs></a:gsLst><a:lin ang="0" scaled="1"/></a:gradFill></a:ln>
  </p:spPr>
  <p:txBody><a:bodyPr/><a:lstStyle/><a:p><a:endParaRPr/></a:p></p:txBody>
</p:sp>'''))

    # =========================================================================
    # SLIDE 5 — Process / Timeline
    # =========================================================================
    items.append(slide())

    items.append(bg(5,
        '<p:bg><p:bgPr><a:solidFill><a:srgbClr val="0D1B2A"/></a:solidFill>'
        '<a:effectLst/></p:bgPr></p:bg>'))

    # Title
    items.append(shape(5, '''
<p:sp>
  <p:nvSpPr><p:cNvPr id="500" name="ProcessTitle"/><p:cNvSpPr txBox="1"/><p:nvPr/></p:nvSpPr>
  <p:spPr>
    <a:xfrm><a:off x="800000" y="300000"/><a:ext cx="10592000" cy="900000"/></a:xfrm>
    <a:prstGeom prst="rect"><a:avLst/></a:prstGeom><a:noFill/><a:ln><a:noFill/></a:ln>
  </p:spPr>
  <p:txBody>
    <a:bodyPr wrap="square" anchor="ctr"/><a:lstStyle/>
    <a:p><a:pPr algn="ctr"/><a:r><a:rPr lang="en-US" sz="3200" b="1" dirty="0"><a:solidFill><a:srgbClr val="FFFFFF"/></a:solidFill><a:latin typeface="Segoe UI"/></a:rPr><a:t>Design Process</a:t></a:r></a:p>
  </p:txBody>
</p:sp>'''))

    # Horizontal rainbow connector
    items.append(shape(5, '''
<p:sp>
  <p:nvSpPr><p:cNvPr id="501" name="ConnLine"/><p:cNvSpPr/><p:nvPr/></p:nvSpPr>
  <p:spPr>
    <a:xfrm><a:off x="1800000" y="2800000"/><a:ext cx="8600000" cy="0"/></a:xfrm>
    <a:prstGeom prst="line"><a:avLst/></a:prstGeom>
    <a:ln w="25400"><a:gradFill><a:gsLst><a:gs pos="0"><a:srgbClr val="00B4D8"/></a:gs><a:gs pos="33000"><a:srgbClr val="E0AAFF"/></a:gs><a:gs pos="66000"><a:srgbClr val="FFD166"/></a:gs><a:gs pos="100000"><a:srgbClr val="06D6A0"/></a:gs></a:gsLst><a:lin ang="0" scaled="1"/></a:gradFill></a:ln>
  </p:spPr>
  <p:txBody><a:bodyPr/><a:lstStyle/><a:p><a:endParaRPr/></a:p></p:txBody>
</p:sp>'''))

    # Step circles + labels (loop — mirrors the bash for-loop)
    labels = ["Research", "Ideate", "Design", "Validate"]
    colors = ["00B4D8", "E0AAFF", "FFD166", "06D6A0"]
    xpos = [1400000, 3600000, 5800000, 8000000]
    for i in range(4):
        x = xpos[i]
        c = colors[i]
        label = labels[i]
        n = i + 1
        cid = 510 + i * 2
        cid2 = 511 + i * 2

        items.append(shape(5, f'''
<p:sp>
  <p:nvSpPr><p:cNvPr id="{cid}" name="Step{n}"/><p:cNvSpPr/><p:nvPr/></p:nvSpPr>
  <p:spPr>
    <a:xfrm><a:off x="{x}" y="2200000"/><a:ext cx="1200000" cy="1200000"/></a:xfrm>
    <a:prstGeom prst="ellipse"><a:avLst/></a:prstGeom>
    <a:solidFill><a:srgbClr val="{c}"><a:alpha val="15000"/></a:srgbClr></a:solidFill>
    <a:ln w="38100"><a:solidFill><a:srgbClr val="{c}"/></a:solidFill></a:ln>
  </p:spPr>
  <p:txBody>
    <a:bodyPr wrap="square" anchor="ctr"/><a:lstStyle/>
    <a:p><a:pPr algn="ctr"/><a:r><a:rPr lang="en-US" sz="2400" b="1" dirty="0"><a:solidFill><a:srgbClr val="{c}"/></a:solidFill></a:rPr><a:t>0{n}</a:t></a:r></a:p>
  </p:txBody>
</p:sp>'''))

        items.append(shape(5, f'''
<p:sp>
  <p:nvSpPr><p:cNvPr id="{cid2}" name="Label{n}"/><p:cNvSpPr txBox="1"/><p:nvPr/></p:nvSpPr>
  <p:spPr>
    <a:xfrm><a:off x="{x}" y="3600000"/><a:ext cx="1200000" cy="800000"/></a:xfrm>
    <a:prstGeom prst="rect"><a:avLst/></a:prstGeom><a:noFill/><a:ln><a:noFill/></a:ln>
  </p:spPr>
  <p:txBody>
    <a:bodyPr wrap="square" anchor="t"/><a:lstStyle/>
    <a:p><a:pPr algn="ctr"/><a:r><a:rPr lang="en-US" sz="1800" b="1" dirty="0"><a:solidFill><a:srgbClr val="FFFFFF"/></a:solidFill><a:latin typeface="Segoe UI"/></a:rPr><a:t>{label}</a:t></a:r></a:p>
  </p:txBody>
</p:sp>'''))

    # Bottom text
    items.append(shape(5, '''
<p:sp>
  <p:nvSpPr><p:cNvPr id="530" name="Bottom"/><p:cNvSpPr txBox="1"/><p:nvPr/></p:nvSpPr>
  <p:spPr>
    <a:xfrm><a:off x="800000" y="5000000"/><a:ext cx="10592000" cy="600000"/></a:xfrm>
    <a:prstGeom prst="rect"><a:avLst/></a:prstGeom><a:noFill/><a:ln><a:noFill/></a:ln>
  </p:spPr>
  <p:txBody>
    <a:bodyPr wrap="square" anchor="ctr"/><a:lstStyle/>
    <a:p><a:pPr algn="ctr"/><a:r><a:rPr lang="en-US" sz="1200" dirty="0"><a:solidFill><a:srgbClr val="8B95A2"/></a:solidFill><a:latin typeface="Segoe UI"/></a:rPr><a:t>Every step is iterative. From research to validation, we refine until perfection.</a:t></a:r></a:p>
  </p:txBody>
</p:sp>'''))

    # =========================================================================
    # SLIDE 6 — Closing
    # =========================================================================
    items.append(slide())

    items.append(bg(6,
        '<p:bg><p:bgPr><a:gradFill rotWithShape="0"><a:gsLst>'
        '<a:gs pos="0"><a:srgbClr val="0A1628"/></a:gs>'
        '<a:gs pos="50000"><a:srgbClr val="0D1B2A"/></a:gs>'
        '<a:gs pos="100000"><a:srgbClr val="1B2838"/></a:gs></a:gsLst>'
        '<a:lin ang="5400000" scaled="1"/></a:gradFill><a:effectLst/></p:bgPr></p:bg>'))

    # Gradient ring
    items.append(shape(6, '''
<p:sp>
  <p:nvSpPr><p:cNvPr id="600" name="Ring"/><p:cNvSpPr/><p:nvPr/></p:nvSpPr>
  <p:spPr>
    <a:xfrm><a:off x="3596000" y="800000"/><a:ext cx="5000000" cy="5000000"/></a:xfrm>
    <a:prstGeom prst="ellipse"><a:avLst/></a:prstGeom>
    <a:noFill/>
    <a:ln w="12700"><a:gradFill><a:gsLst><a:gs pos="0"><a:srgbClr val="00B4D8"><a:alpha val="30000"/></a:srgbClr></a:gs><a:gs pos="50000"><a:srgbClr val="E0AAFF"><a:alpha val="30000"/></a:srgbClr></a:gs><a:gs pos="100000"><a:srgbClr val="FFD166"><a:alpha val="30000"/></a:srgbClr></a:gs></a:gsLst><a:lin ang="2700000" scaled="1"/></a:gradFill></a:ln>
  </p:spPr>
  <p:txBody><a:bodyPr/><a:lstStyle/><a:p><a:endParaRPr/></a:p></p:txBody>
</p:sp>'''))

    # Thank You
    items.append(shape(6, '''
<p:sp>
  <p:nvSpPr><p:cNvPr id="601" name="Thanks"/><p:cNvSpPr txBox="1"/><p:nvPr/></p:nvSpPr>
  <p:spPr>
    <a:xfrm><a:off x="1500000" y="2200000"/><a:ext cx="9192000" cy="1400000"/></a:xfrm>
    <a:prstGeom prst="rect"><a:avLst/></a:prstGeom><a:noFill/><a:ln><a:noFill/></a:ln>
  </p:spPr>
  <p:txBody>
    <a:bodyPr wrap="square" anchor="ctr"/><a:lstStyle/>
    <a:p><a:pPr algn="ctr"/><a:r><a:rPr lang="en-US" sz="4800" b="1" dirty="0"><a:solidFill><a:srgbClr val="FFFFFF"/></a:solidFill><a:latin typeface="Segoe UI"/></a:rPr><a:t>Thank You</a:t></a:r></a:p>
  </p:txBody>
</p:sp>'''))

    # Closing subtitle
    items.append(shape(6, '''
<p:sp>
  <p:nvSpPr><p:cNvPr id="602" name="ClosingSub"/><p:cNvSpPr txBox="1"/><p:nvPr/></p:nvSpPr>
  <p:spPr>
    <a:xfrm><a:off x="1500000" y="3600000"/><a:ext cx="9192000" cy="800000"/></a:xfrm>
    <a:prstGeom prst="rect"><a:avLst/></a:prstGeom><a:noFill/><a:ln><a:noFill/></a:ln>
  </p:spPr>
  <p:txBody>
    <a:bodyPr wrap="square" anchor="t"/><a:lstStyle/>
    <a:p><a:pPr algn="ctr"/><a:r><a:rPr lang="en-US" sz="1600" dirty="0"><a:solidFill><a:srgbClr val="90E0EF"/></a:solidFill><a:latin typeface="Segoe UI"/></a:rPr><a:t>Design is not just what it looks like &#x2014; it&#x2019;s how it works.</a:t></a:r></a:p>
  </p:txBody>
</p:sp>'''))

    # Three accent diamonds
    items.append(shape(6, '''
<p:sp>
  <p:nvSpPr><p:cNvPr id="603" name="D1"/><p:cNvSpPr/><p:nvPr/></p:nvSpPr>
  <p:spPr>
    <a:xfrm rot="2700000"><a:off x="5850000" y="4700000"/><a:ext cx="120000" cy="120000"/></a:xfrm>
    <a:prstGeom prst="rect"><a:avLst/></a:prstGeom>
    <a:solidFill><a:srgbClr val="00B4D8"/></a:solidFill><a:ln><a:noFill/></a:ln>
  </p:spPr>
  <p:txBody><a:bodyPr/><a:lstStyle/><a:p><a:endParaRPr/></a:p></p:txBody>
</p:sp>'''))

    items.append(shape(6, '''
<p:sp>
  <p:nvSpPr><p:cNvPr id="604" name="D2"/><p:cNvSpPr/><p:nvPr/></p:nvSpPr>
  <p:spPr>
    <a:xfrm rot="2700000"><a:off x="6100000" y="4700000"/><a:ext cx="120000" cy="120000"/></a:xfrm>
    <a:prstGeom prst="rect"><a:avLst/></a:prstGeom>
    <a:solidFill><a:srgbClr val="E0AAFF"/></a:solidFill><a:ln><a:noFill/></a:ln>
  </p:spPr>
  <p:txBody><a:bodyPr/><a:lstStyle/><a:p><a:endParaRPr/></a:p></p:txBody>
</p:sp>'''))

    items.append(shape(6, '''
<p:sp>
  <p:nvSpPr><p:cNvPr id="605" name="D3"/><p:cNvSpPr/><p:nvPr/></p:nvSpPr>
  <p:spPr>
    <a:xfrm rot="2700000"><a:off x="6350000" y="4700000"/><a:ext cx="120000" cy="120000"/></a:xfrm>
    <a:prstGeom prst="rect"><a:avLst/></a:prstGeom>
    <a:solidFill><a:srgbClr val="FFD166"/></a:solidFill><a:ln><a:noFill/></a:ln>
  </p:spPr>
  <p:txBody><a:bodyPr/><a:lstStyle/><a:p><a:endParaRPr/></a:p></p:txBody>
</p:sp>'''))

    # One round-trip: 6 slides + every background and shape injection.
    # stop_on_error so an out-of-order raw-set surfaces immediately (a slide
    # must exist before its shapes can be appended to it).
    resp = doc.batch(items, stop_on_error=True)
    summary = resp.get("data", {}).get("summary", {}) if isinstance(resp, dict) else {}
    print(f"  shipped {len(items)} slide/raw-set items "
          f"({summary.get('succeeded', '?')} ok, {summary.get('failed', '?')} failed)")
    if summary.get("failed"):
        for row in resp["data"]["results"]:
            if not row.get("success"):
                print(f"  FAILED #{row['index']}: {row.get('error')}", file=sys.stderr)
        raise SystemExit(1)

# context exit closes the resident, flushing the deck to disk.
print(f"Generated: {FILE}")
