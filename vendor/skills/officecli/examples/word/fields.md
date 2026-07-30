# Field & Table-of-Contents Showcase

Exercises the docx `field` and `toc` element surface — Word's computed values
(page numbers, dates, cross-references, conditionals) and the automatic table of
contents that indexes the document's headings. Three files work together:

- **fields.py** — builds the doc via the **officecli Python SDK**.
- **fields.docx** — the generated document.
- **fields.md** — this file.

## What a field is

A Word FIELD is a *complex field*: a run sequence of field characters —
`begin` / `instrText` (the code) / `separate` / `result` (the cached value) /
`end`. officecli addresses the whole thing as one node at `/field[N]`:

```bash
officecli add file.docx /body --type field --prop fieldType=date --prop format="yyyy-MM-dd"
officecli get file.docx /field[1]      # → instruction=DATE \@ "yyyy-MM-dd" fieldType=date
officecli query file.docx field        # list every field
```

Addressing `/body/p[N]/r[M]` returns the inner fieldChar *run*, not the field —
use `/field[N]`.

> **Fields show their cached result until Word updates them (F9).** officecli
> writes the field **code** correctly; the live value is computed by Word on
> open, or when you select the field and press **F9** / *Update
> Field*. That is why a freshly built `PAGE` reads back `"1"`, a `TOC` reads back
> `"Update field to see table of contents"`, and a `TITLE` reads back empty. The
> codes are what matter — the values are Word's job.

Built on the [`officecli-sdk`](../../sdk/python) (one resident, writes shipped
over the pipe); falls back to the in-repo SDK copy when the package isn't
pip-installed.

## Regenerate

```bash
cd examples/word
pip install officecli-sdk
python3 fields.py
# → fields.docx
```

The CLI twin, `fields.sh`, builds the same document with `officecli` directly.

## Field codes demonstrated

Every field is added with `--type field`. The typed `fieldType` shortcut builds
the instruction for you; `instruction` lets you write any raw code.

| Field | How it's built | Instruction produced |
|---|---|---|
| **DATE** | `fieldType=date format="yyyy-MM-dd"` | `DATE \@ "yyyy-MM-dd"` |
| **TIME** | `fieldType=time format="HH:mm"` | `TIME \@ "HH:mm"` |
| **REF** | `fieldType=ref bookmarkName=IntroSection hyperlink=true` | `REF IntroSection \h` |
| **IF** | `fieldType=if expression='1 = 1' trueText=… falseText=…` | `IF 1 = 1 "…" "…"` |
| **HYPERLINK** | `instruction=' HYPERLINK "https://example.com" \o "…" '` | `HYPERLINK "…" \o "…"` |
| **TITLE** | `fieldType=title` | `TITLE` |
| **PAGE** (locked) | `fieldType=page fldLock=true` | `PAGE` (won't recalc on F9) |
| **NUMPAGES** | `fieldType=page` / `fieldType=numpages` (in footer) | `PAGE`, `NUMPAGES` |

### Picture switches (`format`)

`format` is a **bare** picture string — the handler wraps it into the OOXML
`\@ "..."` switch. Do **not** pass the `\@` yourself:

```bash
officecli add file.docx /body --type field --prop fieldType=date --prop format="yyyy-MM-dd"
officecli add file.docx /body --type field --prop fieldType=time --prop format="HH:mm"
# numeric fields take a numeric picture, e.g. format="0.00%"
```

### Cross-reference (REF) to a bookmark

A REF field points at a bookmark by name; `hyperlink=true` appends the `\h`
switch so the inserted reference is a clickable link to the target. Bookmark
first, then reference it:

```bash
officecli add file.docx /body --type bookmark --prop name=IntroSection --prop text="Introduction"
officecli add file.docx /body --type field --prop fieldType=ref \
  --prop bookmarkName=IntroSection --prop hyperlink=true
```

`bookmarkName` is an alias of `name`; the same `name` prop feeds `mergefield`
(field name), `styleref` (style name) and `docproperty` (property name).

### Conditional (IF) field

`expression`, `trueText`, and `falseText` fold into the instruction — they are
**Add/Set-only** and surface back inside `instruction`, not as their own Format
keys:

```bash
officecli add file.docx /body --type field --prop fieldType=if \
  --prop expression='1 = 1' \
  --prop trueText="Condition is TRUE" --prop falseText="Condition is FALSE"
# → IF 1 = 1 "Condition is TRUE" "Condition is FALSE"
```

### Raw instruction (arbitrary codes)

For codes without a typed shortcut (e.g. HYPERLINK's URL form), pass the whole
instruction:

```bash
officecli add file.docx /body --type field \
  --prop instruction=' HYPERLINK "https://example.com" \o "Visit example.com" '
```

### Locked fields (`fldLock`)

`fldLock=true` rides on the begin fldChar; Word then does **not** update the
field on F9 / recalc — the cached result stays put:

```bash
officecli add file.docx /body --type field --prop fieldType=page --prop fldLock=true
```

> **Round-trip note:** `fldLock=true` is consumed by Add, **persists in the
> OOXML** (`w:fldChar/@w:fldLock="true"`), and is **surfaced on `get`** —
> `get`/`query` of the locked field reports `fldLock=true`. The key is emitted
> only when the field is locked; an unlocked field has no `fldLock` key.

## Composite footer — "Page X of Y"

A single `add` supports at most one text + one field. For a composite footer
(two fields + literal text) create the footer first, then Add the fields and the
joining run to its paragraph one by one:

```bash
officecli add file.docx / --type footer --prop text="Page " --prop align=center
officecli add file.docx "/footer[1]/p[1]" --type field --prop fieldType=page
officecli add file.docx "/footer[1]/p[1]" --type run --prop text=" of "
officecli add file.docx "/footer[1]/p[1]" --type field --prop fieldType=numpages
```

## Table of contents (`toc`)

A TOC is itself a complex field (`TOC \o "1-3" \h \u`), but it has its own
element type with friendly props.

> **A TOC collects paragraphs by _outline level_, which comes from their
> paragraph style.** A blank document has no `Heading1`/`Heading2` styles, so
> tagging paragraphs `style=Heading1` alone leaves the TOC **empty** ("no
> entries found"). Define the built-in heading styles first, each with an
> explicit `outlineLvl` (`0` = Heading 1):
>
> ```bash
> officecli add file.docx /styles --type style \
>   --prop id=Heading1 --prop name="heading 1" --prop type=paragraph --prop outlineLvl=0
> officecli add file.docx /styles --type style \
>   --prop id=Heading2 --prop name="heading 2" --prop type=paragraph --prop outlineLvl=1
> ```

Then add `Heading1`/`Heading2` paragraphs and insert the TOC:

```bash
officecli add file.docx /body --type toc \
  --prop title="Contents" --prop levels=1-3 \
  --prop hyperlinks=true --prop pageNumbers=true
officecli get file.docx /toc[1]
# → levels=1-3 hyperlinks=true pageNumbers=true title=Contents
```

| Prop | Meaning | Switch |
|---|---|---|
| `levels` | heading range indexed, e.g. `1-3` | `\o "1-3"` |
| `hyperlinks` | entries are clickable links | `\h` |
| `pageNumbers` | include trailing page numbers | (drops `\n` when true) |
| `title` | optional caption above the TOC | — |

> Word **rebuilds the rendered entries on open**. This example sets document
> `updateFields=true` (`officecli set file.docx / --prop updateFields=true`), so
> Word recomputes the TOC — and every other field — the moment the document
> opens: the entries fill in with real page numbers and dot leaders, no manual
> F9 needed. officecli's own `get`/`query` still report the write-time cache
> (the TOC reads back its "Update field to see..." placeholder) — that is
> expected; the field *codes* are correct and Word renders the live values.

Note the TOC is also enumerated by `query field` (it *is* a field) — in this
document it is `/field[1]`, so the first typed field (DATE) is `/field[2]`.

## Complete feature coverage

| Element | Keys | Notes |
|---|---|---|
| `field` | `fieldType`, `format`, `instruction`, `name`/`bookmarkName`, `expression`, `trueText`, `falseText`, `hyperlink`, `fldLock`, `id`, `vertAlign` | `fieldType` values: page, numpages, date, time, ref, if, title, mergefield, seq, styleref, docproperty, … (`officecli help docx field`) |
| `toc` | `levels`, `title`, `hyperlinks`, `pageNumbers` | `officecli help docx toc` |

## Set → Get round-trip

The scripts end by retargeting the DATE field's picture switch, then reading
fields and the TOC back:

```
/field[2]: date  instruction=DATE \@ "dddd, MMMM d, yyyy"
/field[4]: ref   instruction=REF IntroSection \h
/field[5]: if    instruction=IF 1 = 1 "Condition is TRUE" "Condition is FALSE"
/toc[1]:   toc   levels=1-3 hyperlinks=true pageNumbers=true title=Contents
```

`fieldType`, `instruction` (with all its switches and IF true/false text), and
every TOC prop round-trip. `fldLock` persists in the OOXML and is surfaced on
`get` (`fldLock=true`, only when the field is locked — see above).
