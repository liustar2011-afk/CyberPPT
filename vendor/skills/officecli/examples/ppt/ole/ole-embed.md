# PPT OLE Embedded Objects

Embed whole Office files (a .xlsx workbook, a .docx document) *inside* a slide
as OLE objects. Double-clicking the object in PowerPoint opens the embedded
payload in-place. This demo consists of four files that work together:

- **ole-embed.sh** — CLI script. Builds two source payloads (`data.xlsx`, `data.docx`) with `officecli`, synthesizes two preview thumbnails, then embeds them into the deck via `add --type ole`.
- **ole-embed.py** — Python SDK twin. Same output via the officecli Python SDK.
- **ole-embed.pptx** — The generated 2-slide deck.
- **ole-embed.md** — This file.

The two payloads (`data.xlsx`, `data.docx`) and the thumbnails (`thumb-xlsx.png`,
`thumb-docx.png`) are the demo inputs the embed step consumes; they are kept
in-dir next to the deck.

> **You must supply `preview=` to see anything.** officecli does **not**
> auto-generate the Office live-preview image for an embedded OLE object.
> Without `preview=`, the object embeds and validates correctly, but real
> PowerPoint renders it as a **blank rectangle** in static / print view — it
> only becomes visible once the user double-clicks to activate it. Supply a
> `preview=` thumbnail for any OLE object you want visible in a static view.

## Regenerate

```bash
cd examples/ppt/ole
pip install Pillow      # required for the preview thumbnails
bash ole-embed.sh
# → ole-embed.pptx (+ data.xlsx, data.docx, thumb-xlsx.png, thumb-docx.png)
```

## Build the payloads first

An OLE embed needs a real source file. Build a tiny spreadsheet and a tiny
Word memo with officecli, then embed them.

```bash
# A tiny .xlsx payload
officecli create data.xlsx
officecli open data.xlsx
officecli set data.xlsx '/sheet[1]/A1' --prop value="Q1 Revenue"
officecli set data.xlsx '/sheet[1]/A2' --prop value="North"
officecli set data.xlsx '/sheet[1]/B2' --prop value="1200"
officecli close data.xlsx

# A tiny .docx payload
officecli create data.docx
officecli open data.docx
officecli add data.docx /body --type paragraph --prop text="Quarterly Memo" --prop bold=true --prop size=16
officecli add data.docx /body --type paragraph --prop text="Revenue is up 12% quarter over quarter."
officecli close data.docx
```

## Slides

### Slide 1 — Embed .xlsx and .docx (each with a preview=)

Two OLE objects side by side, each carrying a full Office package. `progId`
tells PowerPoint which application owns the object (usually inferred from the
`src` extension, shown here explicitly). Each embed also gets its own
`preview=` thumbnail so it renders as a visible, intentional object rather than
a blank box.

```bash
officecli create ole-embed.pptx
officecli open ole-embed.pptx
officecli add ole-embed.pptx / --type slide

# Embed the spreadsheet — progId=Excel.Sheet.12 (modern .xlsx package)
officecli add ole-embed.pptx '/slide[1]' --type ole \
  --prop src=data.xlsx \
  --prop progId=Excel.Sheet.12 \
  --prop preview=thumb-xlsx.png \
  --prop x=1.5in --prop y=1.8in --prop width=3.5in --prop height=2.5in

# Embed the Word memo — progId=Word.Document.12 (modern .docx)
officecli add ole-embed.pptx '/slide[1]' --type ole \
  --prop src=data.docx \
  --prop progId=Word.Document.12 \
  --prop preview=thumb-docx.png \
  --prop x=6.5in --prop y=1.8in --prop width=3.5in --prop height=2.5in
```

**Features:** `--type ole`, `src` (embedded payload — file path / URL / data-URI; alias `path`), `progId` (`Excel.Sheet.12`, `Word.Document.12`, … — usually inferred from the `src` extension), `preview` (thumbnail image so the object is visible in static view), `x`/`y`/`width`/`height` (position and size, EMU-parseable; readback in cm)

---

### Slide 2 — `preview=` vs no `preview=` (teaching contrast)

The same payload embedded twice: once WITH a `preview=` thumbnail, once
WITHOUT. `preview=` supplies the image drawn in the object frame; it is
**add-time only** — `set` ignores this key. The no-preview object embeds and
validates fine but renders **blank** in static view until it is activated in
PowerPoint.

```bash
officecli add ole-embed.pptx / --type slide

# WITH an explicit preview thumbnail — renders visibly
officecli add ole-embed.pptx '/slide[2]' --type ole \
  --prop src=data.xlsx \
  --prop progId=Excel.Sheet.12 \
  --prop preview=thumb-xlsx.png \
  --prop x=1.5in --prop y=1.8in --prop width=3.5in --prop height=2.5in

# WITHOUT preview — embeds + validates, but blank until opened in PowerPoint
officecli add ole-embed.pptx '/slide[2]' --type ole \
  --prop src=data.xlsx \
  --prop progId=Excel.Sheet.12 \
  --prop x=6.5in --prop y=1.8in --prop width=3.5in --prop height=2.5in

officecli close ole-embed.pptx
officecli validate ole-embed.pptx
```

**Features:** `preview` (thumbnail image source; add-time only — `set` ignores it). Without it, the object is present and valid but shows blank in static / print view until double-clicked to activate.

---

## Complete Feature Coverage

| Feature | Slide |
|---------|-------|
| **--type ole:** embed an Office package on a slide | 1, 2 |
| **src=:** embedded payload (file path / URL / data-URI; alias `path`) | 1, 2 |
| **progId=:** `Excel.Sheet.12` (embedded .xlsx) | 1, 2 |
| **progId=:** `Word.Document.12` (embedded .docx) | 1 |
| **preview=:** custom thumbnail image (add-time only; required for a visible static-view face) | 1, 2 |
| **no preview=:** embeds + validates, but blank until activated in PowerPoint | 2 |
| **x / y / width / height:** position and size | 1, 2 |

## Inspect the Generated File

`Get` surfaces read-only readbacks about the embedded part. Note `src` is **not**
echoed by `Get` — the embedded relationship is exposed under `relId` instead.

```bash
# List every OLE object across all slides
officecli query ole-embed.pptx ole

# Full readback — progId / contentType / fileSize / relId / position
officecli get ole-embed.pptx '/slide[1]/ole[1]'   # the .xlsx
officecli get ole-embed.pptx '/slide[1]/ole[2]'   # the .docx
```

Example readback for the embedded .xlsx:

```
/slide[1]/ole[1] (ole) "Excel.Sheet.12" objectType=ole progId=Excel.Sheet.12 \
  display=icon x=3.81cm y=129.6pt width=8.89cm height=6.35cm \
  relId=R079cd9d005e64b19 \
  contentType=application/vnd.openxmlformats-officedocument.spreadsheetml.sheet \
  fileSize=3936
```

**Get-only readbacks:** `contentType` (MIME type of the embedded part),
`fileSize` (embedded payload bytes), `objectType` (literal `ole`),
`relId` (the embedded relationship id — inspect the part behind the object),
`progId` (also settable).

> `src` is accepted on `add`/`set` only and is **not** echoed by `Get`. Use
> `relId` to identify the embedded part.
