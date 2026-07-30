# Word Pictures

This demo consists of several files that work together:

- **pictures.sh** — CLI script that synthesizes two sample PNGs (a square logo, a wide banner) and drives `officecli` to build the document.
- **pictures.py** — Python SDK twin of `pictures.sh`; produces an equivalent `pictures.docx`.
- **pictures.docx** — The generated document (inline, cropped, alt-text, watermark, wrapped, positioned, and clickable pictures).
- **pictures-logo.png / pictures-banner.png** — The generated sample images, embedded into the document.
- **pictures.md** — This file. Maps each section to the picture features it demonstrates.

## Regenerate

```bash
cd examples/word
pip install Pillow   # required for sample image generation
bash pictures.sh
# → pictures.docx  (+ pictures-logo.png, pictures-banner.png)
```

## How docx pictures are addressed

A picture in Word is a **run inside a paragraph**. So you `add --type picture`
to a *paragraph* path (`/body/p[N]` or `/body/p[@paraId=X]`), and the picture's
own path is that paragraph plus a run index (`/body/p[@paraId=X]/r[N]`).

- **Inline** (default) — the picture sits in the text flow like a large glyph.
- **Floating** — pass `--prop anchor=true` to unlock `wrap`, `behindText`,
  `hAlign` / `vAlign`, `hPosition` / `vPosition`, `hRelative` / `vRelative`.

## Sections

### 1 — Inline Picture

An inline picture flows with the paragraph text; only `width` / `height` (always
unit-qualified) apply.

```bash
officecli add pictures.docx /body --type paragraph --prop text="1. Inline Picture" --prop style=Heading1
officecli add pictures.docx /body --type paragraph --prop text="An inline picture flows with the paragraph text ..."
officecli add pictures.docx /body --type paragraph --prop text=""
officecli add pictures.docx '/body/p[3]' --type picture \
  --prop src=pictures-logo.png \
  --prop width=3cm --prop height=3cm
```

**Features:** `--type picture`, `src` (file path / URL / data-URI), `width` / `height` (unit-qualified — always pass cm/in/pt; a bare number is raw EMU)

---

### 2 — Cropped Picture

`crop=L,T,R,B` trims each edge by a percentage of the source image.

```bash
officecli add pictures.docx '/body/p[6]' --type picture \
  --prop src=pictures-banner.png \
  --prop crop=10,5,15,8 \
  --prop width=10cm --prop height=2.5cm
```

**Features:** `crop` (1 value = symmetric, or 4 values `L,T,R,B` = per-edge percent); per-edge `cropLeft` / `cropTop` / `cropRight` / `cropBottom` accepted on add/set. `Get` folds all sides into the canonical 4-value `crop` key.

---

### 3 — Alt Text (Accessibility)

`alt=` writes the DocProperties description that screen readers announce.

```bash
officecli add pictures.docx '/body/p[9]' --type picture \
  --prop src=pictures-logo.png \
  --prop width=3cm --prop height=3cm \
  --prop alt="Company logo: a blue circle enclosing a yellow triangle"
```

**Features:** `alt` (alternative text; aliases `altText`, `description`). When omitted, no description is written (an auto-filled filename is worse than none for screen readers).

---

### 4 — Behind-Text Watermark

A floating picture with `wrap=none` + `behindText=true` sits behind the text
like a watermark, centered on the page margins.

```bash
officecli add pictures.docx '/body/p[11]' --type picture \
  --prop src=pictures-banner.png \
  --prop anchor=true --prop wrap=none --prop behindText=true \
  --prop hAlign=center --prop vAlign=center \
  --prop hRelative=margin --prop vRelative=margin \
  --prop width=12cm --prop height=3cm \
  --prop alt="Decorative watermark banner"
```

**Features:** `anchor=true` (floating), `wrap=none` + `behindText=true` (behind-text z-order), `hAlign` / `vAlign` (relative alignment keyword), `hRelative` / `vRelative` (reference frame)

---

### 5 — Square Text Wrap

With `wrap=square`, surrounding text flows around the picture's bounding box.
Here the picture is right-aligned to the margin so the paragraph wraps down its
left side.

```bash
officecli add pictures.docx '/body/p[13]' --type picture \
  --prop src=pictures-logo.png \
  --prop anchor=true --prop wrap=square \
  --prop hAlign=right --prop hRelative=margin --prop vRelative=paragraph \
  --prop width=3.5cm --prop height=3.5cm \
  --prop alt="Logo floated right with square wrap"
```

**Features:** `wrap` (`none`, `square`, `tight`, `topandbottom`, `through`), `hAlign=right` relative to the `margin` frame

---

### 6 — Absolute Position (hPosition / vPosition)

Instead of relative alignment, pin a floating picture to an absolute offset from
its reference frame. `wrap=tight` makes text hug the boundary.

```bash
officecli add pictures.docx '/body/p[15]' --type picture \
  --prop src=pictures-logo.png \
  --prop anchor=true --prop wrap=tight \
  --prop hPosition=2cm --prop vPosition=1cm \
  --prop hRelative=margin --prop vRelative=paragraph \
  --prop width=3cm --prop height=3cm \
  --prop alt="Logo at absolute 2cm,1cm offset with tight wrap"
```

**Features:** `hPosition` / `vPosition` (absolute offset — always unit-qualified; a bare number is raw EMU), `wrap=tight`

---

### 7 — Clickable Picture (link)

`link=` wraps the picture in a click hyperlink.

```bash
officecli add pictures.docx '/body/p[18]' --type picture \
  --prop src=pictures-banner.png \
  --prop width=10cm --prop height=2.5cm \
  --prop link="https://example.com" \
  --prop alt="Banner linking to example.com"
```

**Features:** `link` (absolute URL → external relationship; `#anchor` or bookmark name → internal jump)

---

### 8 — Decorative Picture (accessibility)

`decorative=true` marks the image as decorative: screen readers skip it entirely
(no alt text is announced). Stored as an `adec:decorative` extension under the
picture's `<wp:docPr>`.

```bash
officecli add pictures.docx '/body/p[21]' --type picture \
  --prop src=pictures-banner.png \
  --prop width=10cm --prop height=2.5cm \
  --prop decorative=true
```

`get` reports `decorative=true` (only when the flag is set). `decorative` also
works via `set`. Use it for purely ornamental images that carry no information.

**Features:** `decorative` (accessibility — screen readers skip the image)

---

## Complete Feature Coverage

| Feature | Section |
|---------|---------|
| **inline picture:** default text-flow placement | 1 |
| **width / height:** unit-qualified sizing | 1–7 |
| **src=:** file path (also URL / data-URI) | 1–7 |
| **crop=L,T,R,B:** per-edge crop percent | 2 |
| **cropLeft / cropTop / cropRight / cropBottom:** named per-edge (add/set) | 2 |
| **alt=:** accessibility description | 3 |
| **anchor=true:** floating picture | 4–6 |
| **wrap=none + behindText:** behind-text watermark | 4 |
| **hAlign / vAlign:** relative alignment keyword | 4, 5 |
| **hRelative / vRelative:** reference frame | 4–6 |
| **wrap=square:** text flows around bounding box | 5 |
| **wrap=tight:** text hugs boundary | 6 |
| **hPosition / vPosition:** absolute offset | 6 |
| **link=:** clickable image hyperlink | 7 |
| **decorative=true:** mark decorative (screen readers skip) | 8 |

## Inspect the Generated File

```bash
# List every picture with its stable run path and key props
officecli query pictures.docx picture

# Inline picture (section 1) — width/height/wrap=inline
officecli get pictures.docx '/body/p[3]/r[2]'

# Cropped banner (section 2) — crop=10,5,15,8
officecli get pictures.docx '/body/p[6]/r[2]'

# Alt text (section 3)
officecli get pictures.docx '/body/p[9]/r[2]'

# Behind-text watermark (section 4) — anchor/behindText/hAlign/vAlign
officecli get pictures.docx '/body/p[11]/r[2]'

# Square wrap, right-aligned (section 5)
officecli get pictures.docx '/body/p[13]/r[2]'

# Absolute position + tight wrap (section 6) — hPosition/vPosition
officecli get pictures.docx '/body/p[15]/r[2]'

# Clickable banner (section 7) — link=
officecli get pictures.docx '/body/p[18]/r[2]'
```

> **Note on paths:** the `/body/p[N]/r[2]` positional paths above assume a
> freshly generated file. `officecli query pictures.docx picture` prints the
> authoritative `@paraId` paths, which are stable across edits.
