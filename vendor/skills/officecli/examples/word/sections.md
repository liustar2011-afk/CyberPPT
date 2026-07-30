# Sections Showcase

Exercises the docx `section` property surface — the per-section page layout that
has no per-paragraph or per-run equivalent: multi-column layout, footnote and
endnote behaviour, per-section page setup, line numbering and vertical
alignment. Three files work together:

- **sections.sh** — builds the doc via the **officecli CLI** directly.
- **sections.py** — the SDK twin (officecli Python SDK), same document.
- **sections.docx** — the generated document.
- **sections.md** — this file.

## Word's section model

A **section** is a run of content that shares one page layout: page size and
orientation, margins, columns, header/footer refs, line numbering,
footnote/endnote behaviour and vertical alignment. Those settings live in a
`sectPr` (section properties) element.

A `.docx` always has **one trailing "final" section** — the body-level `sectPr`,
addressed at path `/`. Every `add / --type section` inserts a section **break**:
it closes off the content added so far into a new `/section[N]` carrying its own
`sectPr`, and the still-open trailing section shifts down to hold whatever comes
next.

So the build pattern is:

```
add paragraphs  →  add section (break)  →  add paragraphs  →  add section  →  …
```

The section you just added **owns the paragraphs above it**. This is why in
`sections.sh` the layout `add` comes *after* the paragraphs it applies to.

Addressing:

| Path | What it is | Operations |
|---|---|---|
| `/section[N]` | a mid-document section (the break paragraph's `sectPr`) | `get` `set` `query` `remove` |
| `/` | the final trailing section (body-level `sectPr`) | `get` `set` (rejects break `type`) |

```bash
officecli add  file.docx / --type section --prop type=nextPage --prop columns=2
officecli query file.docx section        # list all sections + their layout
officecli get   file.docx /section[1]    # read one section's property bag
officecli set   file.docx /section[1] --prop vAlign=center
```

> The final section at `/` has no break `type` (nothing follows it), so
> `set / --prop type=…` is rejected with a pointer to `/section[N]`. Set the
> break type only on mid-document sections.

## Regenerate

```bash
cd examples/word
bash sections.sh                 # CLI
# or
pip install officecli-sdk
python3 sections.py              # SDK twin
# → sections.docx
```

`sections.sh` intentionally omits `set -e`: like the SDK twin's `doc.batch`, it
tolerates forward-compat `UNSUPPORTED props` warnings and keeps building.

## The three demonstrated sections

### 1. Two-column layout with footnotes

```bash
officecli add file.docx / --type section \
  --prop type=nextPage \
  --prop pageWidth=21cm --prop pageHeight=29.7cm --prop orientation=portrait \
  --prop marginTop=2.54cm --prop marginBottom=2.54cm \
  --prop marginLeft=2.54cm --prop marginRight=2.54cm \
  --prop marginHeader=1.25cm --prop marginFooter=1.25cm \
  --prop columns=2 --prop columnSpace=1cm \
  --prop titlePage=true \
  --prop footnotePr.numFmt=lowerRoman --prop footnotePr.numRestart=eachPage \
  --prop footnotePr.numStart=1 --prop footnotePr.pos=pageBottom
```

`columns=2` splits into two balanced columns; `columnSpace` is the gutter. Add
enough running text for the wrap to be visible. Footnotes attach to a body
paragraph and render per `footnotePr.pos`:

```bash
officecli add file.docx /body/p[3] --type footnote --prop text="See note."
```

`columns` also accepts a combined form on `add`: `--prop columns=2,1cm` (count
plus space). `titlePage=true` gives the section a distinct first-page
header/footer.

### 2. Landscape, single column, vertically centered, line numbering

```bash
officecli add file.docx / --type section \
  --prop type=nextPage \
  --prop orientation=landscape \
  --prop pageWidth=29.7cm --prop pageHeight=21cm \
  --prop marginTop=2cm --prop marginBottom=2cm \
  --prop marginLeft=3cm --prop marginRight=1.5cm \
  --prop columns=1 \
  --prop vAlign=center \
  --prop lineNumbers=continuous --prop lineNumberCountBy=5 \
  --prop lineNumberDistance=288 \
  --prop pageNumFmt=decimal --prop pageStart=1
```

`orientation=landscape` swaps the geometry — set `pageWidth`/`pageHeight`
accordingly. `vAlign=center` vertically centers a short block on the page
(`top`/`center`/`both`/`bottom`). `lineNumbers=continuous` with
`lineNumberCountBy=5` numbers every fifth line; `lineNumberDistance` (twips) is
the gutter to the body text. `pageNumFmt` sets the page-number format and
`pageStart` the starting number for the section.

### 3. Continuous two-column with endnotes

```bash
officecli add file.docx / --type section \
  --prop type=continuous \
  --prop orientation=portrait \
  --prop pageWidth=21cm --prop pageHeight=29.7cm \
  --prop columns=2 --prop columnSpace=0.8cm \
  --prop endnotePr.numFmt=upperRoman --prop endnotePr.numRestart=eachSect \
  --prop endnotePr.numStart=1 --prop endnotePr.pos=docEnd
```

`type=continuous` changes layout **without** ejecting a page (contrast
`nextPage`). Endnotes attach to a body paragraph like footnotes and gather where
`endnotePr.pos` points (`sectEnd` or `docEnd`):

```bash
officecli add file.docx /body/p[9] --type endnote --prop text="End reference."
```

## Complete feature coverage

| Group | Keys | Visible in render? |
|---|---|---|
| Break type | `type` (`nextPage`/`continuous`/`evenPage`/`oddPage`/`nextColumn`) | Yes (page/column flow) |
| Page setup | `pageWidth`, `pageHeight`, `orientation`, `marginTop/Bottom/Left/Right/Header/Footer/Gutter` | Yes (geometry) |
| Columns | `columns`, `columnSpace` | Yes (multi-column flow) |
| Vertical | `vAlign` (`top`/`center`/`both`/`bottom`) | Yes (block position) |
| Line numbers | `lineNumbers`, `lineNumberCountBy`, `lineNumberDistance` | Yes (margin numbers) |
| Page numbers | `pageNumFmt`, `pageStart` | Yes (in fields) |
| Title page | `titlePage` | Yes (first-page H/F) |
| Footnotes | `footnotePr.numFmt`, `.numRestart`, `.numStart`, `.pos` | Yes (note behaviour) |
| Endnotes | `endnotePr.numFmt`, `.numRestart`, `.numStart`, `.pos` | Yes (note behaviour) |
| RTL | `direction`, `rtlGutter`, `textDirection` | Yes (reading order) |
| Page borders | `pgBorders[.top/left/bottom/right/offsetFrom/zOrder/display]` | Yes (border) |
| Paper source | `paperSrc.first`, `paperSrc.other` | No (printer trays) |
| Read-only | `headerRef[.default/first/even]`, `footerRef[…]`, `colSpaces`, `columns.equalWidth`, `columns.separator` | — (`get` only) |

Full list: `officecli help docx section`.

> **`get`-only keys.** `columns.equalWidth` and `columns.separator` (the vertical
> rule between columns) surface on `get`/`dump` but are **not** settable through a
> `--prop` — the separator rule needs a raw-XML edit. `headerRef`/`footerRef` and
> `colSpaces` are likewise read-back conveniences, not inputs.

## Inspect the result

```bash
officecli query sections.docx section          # list every section + layout
officecli get   sections.docx /section[1]      # two-column + footnotePr.*
officecli get   sections.docx /section[2]      # landscape + vAlign + line nums
officecli get   sections.docx /section[3]      # continuous + endnotePr.*
officecli get   sections.docx /                # final trailing section
```

Note normalization on `get`: lengths read back unit-qualified in `cm` (e.g.
`21cm`), enums as their OOXML inner text (e.g. `lowerRoman`, `center`).
