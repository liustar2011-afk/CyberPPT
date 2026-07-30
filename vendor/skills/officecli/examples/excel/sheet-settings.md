# Sheet Settings Showcase

Exercises the xlsx `sheet` element's **sheet-level** property surface — the
per-worksheet settings that live on `<sheetView>`, `<pageSetup>`,
`<headerFooter>`, `<sheetPr>`, `<sheetProtection>`, and the sheet's
defined-names. These are distinct from the workbook-level settings in
[workbook-settings](workbook-settings.md). Four files work together:

- **sheet-settings.sh** — builds the workbook via the `officecli` CLI (this file walks through it).
- **sheet-settings.py** — the same build via the **officecli Python SDK** (one `doc.send()` per command, mirroring the `.sh` line for line).
- **sheet-settings.xlsx** — the generated workbook (either script produces it).
- **sheet-settings.md** — this file.

The CLI commands shown below are exactly what `sheet-settings.sh` runs; the
`.py` issues the identical sequence over the SDK pipe.

## The `sheet` element

A `sheet` is addressed at path `/<sheetName>`. You `add`/`remove` sheets and
`set`/`get` their sheet-level properties. Each themed sheet in this example
carries a header row + a few data rows so freeze panes, print titles, and the
print area point at meaningful cells:

```bash
officecli set file.xlsx /Sheet1 --prop freeze=B2
officecli get file.xlsx /Sheet1
```

> **Print-only settings verify via `get`, not visual render.** Orientation,
> paper size, fit-to-page, margins, print area, and print titles change how the
> sheet *prints*, not how it looks on screen — a static screenshot won't show
> them. Confirm them with `officecli get`, which reads them straight back out of
> the OOXML.

## Regenerate

```bash
cd examples/excel
bash sheet-settings.sh               # via the CLI
# — or —
pip install officecli-sdk            # the SDK (officecli binary still required)
python3 sheet-settings.py            # via the SDK, same result
# → sheet-settings.xlsx
```

## The four themed sheets

### 1-Freeze-Panes — freeze panes

```bash
officecli set file.xlsx /1-Freeze-Panes --prop freeze=B2
```

`freeze` takes the top-left cell of the *unfrozen* region: `A2` freezes row 1,
`B1` freezes column A, `B2` freezes **both** row 1 and column A. `none` /
`false` removes the freeze. Set-only on existing sheets.

### 2-Print-Setup — page setup, margins, print area & titles

```bash
officecli set file.xlsx /2-Print-Setup \
  --prop orientation=landscape \
  --prop paperSize=9 \                # OOXML code: 1=Letter, 9=A4
  --prop fitToPage=1x1 \              # fit to WxH pages
  --prop printArea=A1:D6 \            # _xlnm.Print_Area for this sheet
  --prop printTitleRows=1:1 \         # repeat row 1 at top of every page (set-only)
  --prop printTitleCols=A:A \         # repeat column A at left of every page (set-only)
  --prop margin.top=1.0in --prop margin.bottom=1.0in \
  --prop margin.left=0.5in --prop margin.right=0.5in \
  --prop margin.header=0.3in --prop margin.footer=0.3in
```

`printTitleRows` / `printTitleCols` are **set-only** — they apply but do not
read back on `get` (they share the sheet's print-title defined-name). All the
others round-trip.

### 3-Headers-Footers — page header / footer

```bash
officecli set file.xlsx /3-Headers-Footers \
  --prop header="&LQuarterly Report&C2026 Sales&R&D" \
  --prop footer="&LConfidential&CPage &P of &N&R&F"
```

Excel header/footer **format codes** pass through verbatim:

| Code | Meaning | Code | Meaning |
|---|---|---|---|
| `&L` | left section | `&P` | page number |
| `&C` | center section | `&N` | page count |
| `&R` | right section | `&D` | date |
| `&F` | file name | `&T` | time |

### 4-Display-Protection — display toggles + sheet protection

```bash
officecli set file.xlsx /4-Display-Protection \
  --prop tabColor=C0392B \
  --prop gridlines=false \            # hide sheetView gridlines
  --prop headings=false \             # hide row/column headings
  --prop zoom=125 \                   # sheetView zoom % (10-400)
  --prop autoFilter=A1:B5 \           # AutoFilter over a range (or `true` for used range)
  --prop direction=rtl                # RTL layout — column A on the right

officecli set file.xlsx /4-Display-Protection \
  --prop protect=true \               # enable sheet protection
  --prop password=secret123           # legacy password hash (implicitly enables protect)
```

`gridlines` / `headings` are emitted only when hidden (default-on is omitted).
`zoom` is emitted only when ≠ 100.

### 5-Sorted / 6-Hidden — sort & hidden sheets

```bash
officecli add file.xlsx / --type sheet --prop name=5-Sorted --prop tabColor=27AE60
officecli set file.xlsx /5-Sorted --prop sort="B desc"     # reorder rows by column B, descending

officecli add file.xlsx / --type sheet --prop name=6-Hidden --prop hidden=true
```

`sort` readback is `Col:dir` (e.g. `B:desc`). **A protected sheet can't be
sorted** (`sort` errors on it), so sorting lives on its own unprotected sheet
rather than on `4-Display-Protection`.

## Complete feature coverage

| Group | Keys |
|---|---|
| Freeze | `freeze` |
| Page setup | `orientation`, `paperSize`, `fitToPage`, `printArea`, `printTitleRows`*, `printTitleCols`*, `margin.top/bottom/left/right/header/footer` |
| Headers/footers | `header`, `footer` |
| Display | `tabColor`, `gridlines`, `headings`, `zoom`, `autoFilter`, `direction` |
| Protection | `protect`, `password`* |
| Structure | `name`, `hidden`, `visibility`, `sort` |

\* set-only (no `get` readback): `printTitleRows`, `printTitleCols`, `password`.

Full list: `officecli help xlsx sheet`.

## Set → Get round-trip

```
/1-Freeze-Panes       freeze=B2
/2-Print-Setup        orientation=landscape paperSize=9 fitToPage=1x1 printArea=A1:D6
                      margin.top=1in margin.bottom=1in margin.left=0.5in margin.right=0.5in
/3-Headers-Footers    header=&LQuarterly Report&C2026 Sales&R&D  footer=&LConfidential&CPage &P of &N&R&F
/4-Display-Protection zoom=125 gridlines=false headings=false direction=rtl
                      tabColor=#C0392B autoFilter=A1:B5 protect=true
/5-Sorted             tabColor=#27AE60 sort=B:desc
/6-Hidden             hidden=true visibility=hidden
```
