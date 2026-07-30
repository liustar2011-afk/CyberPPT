# Textbox Showcase

Demonstrates 10 complex textbox scenarios built on the `wps:wsp` WordprocessingShape model (OOXML Drawing ML). The example is **hybrid**:

- **Scenarios 1, 4, 5, 6, 7, 8, 9, 10** use the high-level `officecli add --type textbox` command — fill, border, gradient, rotation, vertical text, geometry, corner radius, shadow, no-fill/no-line, wrap, positioning and z-order are `--prop`s on one `add`, and the inner text is formatted with `set` on the `<textbox>/p[N]` paths plus extra `add … --type paragraph` calls.
- **Scenarios 2 and 3** stay on `officecli raw-set` with pre-authored XML, because they exercise surface the high-level command does not expose (per-run mixed formatting inside one paragraph, and a nested table — see the per-scenario notes below).

Three files:

- **textbox.sh** — builds the document (high-level `add` for all but 2/3, `raw-set` for 2/3).
- **textbox.py** — SDK twin; ships the same items over one `doc.batch(...)` round-trip.
- **textbox.docx** — generated output; open in Word to see each floating shape.
- **textbox.md** — this file.

## Regenerate

```bash
cd examples/word
bash textbox.sh          # or: python3 textbox.py
# → textbox.docx
```

## The two insertion paths

**High-level (1/4/5/7/9).** One `add` creates the box and its first paragraph; the returned path (`/body/textbox[N]`) is then addressable for run formatting and more paragraphs:

```bash
TB=$(officecli add textbox.docx /body --type textbox \
  --prop text="Basic Textbox" --prop width=15cm --prop height=3.33cm \
  --prop fill=E6F3FF --prop line.color=0070C0 --prop line.width=2pt \
  --prop wrap=topAndBottom --prop textAnchor=top | grep -oE '/body/textbox\[[0-9]+\]')
officecli set textbox.docx "$TB/p[1]" --prop align=center --prop bold=true --prop color=0070C0 --prop size=14
officecli add textbox.docx "$TB" --type paragraph --prop text="… body text …"
```

Paragraph-level format keys are the **bare** forms (`bold`/`italic`/`color`/`size`/`align`) — each applies to every run in that paragraph. (For different formatting on different runs *within one paragraph*, use `raw-set` — see Scenario 2.)

**Raw (2/3/6/8/10).** The whole textbox paragraph is injected before the body `sectPr`:

```bash
officecli raw-set textbox.docx /document \
  --xpath "//w:body/w:sectPr" \
  --action insertbefore \
  --xml '<w:p> ... <mc:AlternateContent> ... </mc:AlternateContent> ... </w:p>'
```

The `mc:AlternateContent` wrapper follows the OOXML spec:
- `mc:Choice Requires="wps"` — the modern `wps:wsp` WordprocessingShape (Word 2010+).
- `mc:Fallback` — optional VML fallback for older renderers.

Each `wps:wsp` element has these children:
- `wps:cNvSpPr` — marks it as a text box (`txBox="1"`).
- `wps:spPr` — geometry, fill, border, effects.
- `wps:txbx` → `w:txbxContent` — the actual paragraph/table content inside the box.
- `wps:bodyPr` — text body layout: rotation, vertical flow, wrap, insets, anchor.

## Scenario 1: Basic Textbox (Solid Fill + Border) — HIGH-LEVEL

A rectangle with a solid light-blue fill, a 2pt blue border, and top-and-bottom text wrapping.

Built with `add --type textbox`:
- `fill=E6F3FF` (light blue fill)
- `line.color=0070C0` + `line.width=2pt` (blue border)
- `wrap=topAndBottom` (body text flows above and below)
- `textAnchor=top`; the centred bold-blue title is `set` on `p[1]`, the body is a second `add … --type paragraph`.

**Features:** `fill`, `line.color`, `line.width`, `wrap=topAndBottom`, `textAnchor`, per-paragraph run formatting via `set` on the inner `p[N]`.

> The raw-XML original also carried a VML `mc:Fallback` for pre-2010 renderers; the high-level command does not emit one. If you need the legacy fallback, use `raw-set` (see the raw scenarios).

## Scenario 2: Multi-Paragraph Rich Text Textbox

A taller box with a dashed orange border and rich mixed-format content: bold, italic, underline, strikethrough, color, highlight, and right-aligned text — all inside `w:txbxContent`.

Key `wps:spPr` attributes:
- `a:prstDash val="dash"` on `a:ln` (dashed border)
- Multiple paragraphs with varied `w:rPr` combinations inside `w:txbxContent`

**Features:** dashed border (`a:prstDash val="dash|solid|dot|…"`), multi-paragraph textbox content, mixed run formatting inside `w:txbxContent` (bold/italic/underline/strike/color/highlight)

## Scenario 3: Textbox with Nested Table

A gray-bordered box containing a paragraph header followed by a `w:tbl` — demonstrating that `w:txbxContent` can hold any valid body content including tables.

Key structure inside `w:txbxContent`:
```xml
<w:p> ... heading ... </w:p>
<w:tbl>
  <w:tblPr><w:tblStyle w:val="TableGrid"/></w:tblPr>
  <w:tr> ... header cells with blue fill ... </w:tr>
  <w:tr> ... data cells ... </w:tr>
</w:tbl>
```

**Features:** `w:tbl` nested inside `w:txbxContent` (full table-in-textbox), `w:tblStyle` reference, per-cell `w:shd` fill

## Scenario 4: Rotated Textbox (45 degrees + Gradient Fill) — HIGH-LEVEL

A box rotated 45° with a red-to-yellow gradient fill and centred white text.

Built with `add --type textbox`:
- `rotation=45` (degrees — the command converts to the `a:xfrm rot` 60000-per-degree units)
- `fill.gradient=FF6B6B,FFE66D` — a **comma-separated** stop list. (Note: this is *not* the `C1-C2:angle` syntax used by chart fills; the dash form is rejected here.)
- `line.color=C0392B` + `line.width=1.5pt`
- `textAnchor=center` (text centred despite rotation), `anchor.x=4.17cm` + `hRelative=column`

**Features:** `rotation`, `fill.gradient` (comma stop list), `line.color`/`line.width`, `textAnchor=center`, `anchor.x`/`hRelative`

## Scenario 5: Vertical Text Textbox — HIGH-LEVEL

A narrow tall box with East-Asian vertical text flow, where characters read top-to-bottom.

Built with `add --type textbox`:
- `textDirection=eaVert` (alias: `vert`; emits `wps:bodyPr vert="eaVert"`; other values `horz`, `vert`, `vert270`, `wordArtVert`)
- `fill=FFF0F5`, `line.color=8B0000` + `line.width=1pt`; the bold dark-red text is `set` on `p[1]`.

**Features:** `textDirection=eaVert` (vertical text orientation), `fill`, `line.*`

## Scenario 6: Rounded Rectangle Textbox + Drop Shadow — HIGH-LEVEL

A rounded rectangle with a soft outer drop shadow.

Built with `add --type textbox`:
- `geometry=roundRect` + `cornerRadius=16667` (the adjust-handle guide value; `0-100` is read as a percent ×1000, a value `>100` as a raw guide value)
- `shadow=true` — emits the standard outer drop shadow (blur 50800 / dist 38100 / dir 5400000 / black / 40% alpha). A compact `shadow=blur;dist;dir;color;alpha` form is also accepted for a custom shadow.
- `fill=E8F5E9`, `line.color=2E7D32` + `line.width=2.25pt`, `textAnchor=center`; the three paragraphs (bold-green title / body / italic-grey note) are `set` on `p[1..3]`.

**Features:** `geometry=roundRect`, `cornerRadius` (adjust handle), `shadow`, `line.width`, `textAnchor`

## Scenario 7: Side-by-Side Textboxes (Dashboard Cards) — HIGH-LEVEL

Three rounded metric cards floating side-by-side, each with `wrap=none` so they don't push body text.

Built with three `add --type textbox` calls (one per card):
- `geometry=roundRect` (card shape)
- `wrap=none` (boxes float freely)
- `hRelative=column` + `anchor.x=0cm / 5.28cm / 10.56cm` (horizontal offsets across the column)
- each card's accent title / big number / grey label are `set` on `p[1]`/`p[2]`/`p[3]`.

**Features:** `geometry=roundRect`, `wrap=none`, `anchor.x`/`hRelative` (horizontal positioning)

> **Known limitation:** the high-level `add` places each textbox in its own host paragraph, so the three cards sit at a slight *vertical stagger* rather than a single shared baseline. The raw-XML original packed all three `wp:anchor` into one paragraph for a perfectly aligned row — if you need pixel-exact co-baseline cards, use `raw-set`.

## Scenario 8: Borderless Transparent Textbox — HIGH-LEVEL

A completely invisible container — no fill, no border — so only the text shows (a watermark-style overlay).

Built with `add --type textbox`:
- `fill=none` and `line.color=none` — both sentinels emit `a:noFill` (fill and outline respectively). (`none`/`transparent` were previously rejected by the color parser, so this box needed raw-set.)
- `hRelative=column` + `anchor.x=1.39cm`, `textAnchor=center`; the single italic light-grey line is `set` on `p[1]`.

**Features:** `fill=none`, `line.color=none` (fully borderless/transparent), inner italic run formatting

## Scenario 9: Text Overflow Textbox — HIGH-LEVEL

A short fixed-height box holding six paragraphs — more text than fits — to show overflow clipping.

Built with `add --type textbox`:
- `height=1.67cm` with `autoFit` **omitted** → the box stays a fixed height and clips overflow. (Passing `autoFit=true` would emit `a:spAutoFit` and grow the box to fit instead.)
- `textAnchor=top` anchors content to the top so the overflow clips at the bottom; Line 1 is `set` bold-red, the rest are plain `add … --type paragraph` calls.

**Features:** fixed-height textbox (`autoFit` omitted), overflow clipping, `textAnchor=top`

## Scenario 10: Textbox Z-Order Stacking (behindDoc) — HIGH-LEVEL

Two overlapping boxes demonstrating Z-order, built with two `add --type textbox` calls:
- **Bottom layer:** `behindDoc=true` — sits behind the body text; `relativeHeight=251670528`.
- **Top layer:** `relativeHeight=251671552` (higher = front) + `fill.opacity=80` — a translucent (80%) fill so the bottom box shows through the overlap.

Both use `wrap=none` with `hRelative=column`/`anchor.x` (and the top box `vRelative=paragraph`/`anchor.y`) to overlap.

**Features:** `behindDoc` (push behind body text), `relativeHeight`/`zorder` (stacking order; higher = front), `fill.opacity` (translucent fill), `wrap=none` + `anchor.x`/`anchor.y` overlap

## Complete Feature Coverage

| Feature | Scenario |
|---------|---------|
| Solid fill (`a:solidFill`) | 1, 3, 7, 8, 10 |
| Gradient fill (`a:gradFill`/`a:gsLst`) | 4 |
| No fill (`a:noFill`) | 8 |
| Border width (`a:ln w`) + solid color | 1, 2, 3, 6, 7 |
| Dashed border (`a:prstDash`) | 2 |
| No border (`a:ln/a:noFill`) | 8 |
| Preset geometry: `rect` | 1, 8, 9, 10 |
| Preset geometry: `roundRect` + corner radius | 6, 7 |
| Shape rotation (`a:xfrm rot`) | 4 |
| Drop shadow (`a:outerShdw`) | 6 |
| Color transparency (`a:alpha`) | 10 |
| Vertical text (`wps:bodyPr vert="eaVert"`) | 5 |
| Body text anchor (`anchor="t"/"ctr"`) | 1, 4, 6, 9 |
| Text wrap: `wp:wrapTopAndBottom` | 1, 2, 3, 4, 5, 6 |
| Text wrap: `wp:wrapNone` (float freely) | 7, 10 (bottom) |
| Z-order: `relativeHeight`, `behindDoc` | 10 |
| Horizontal positioning: `wp:positionH/posOffset` | 7 |
| Nested table in textbox | 3 |
| Rich mixed-format content (`w:rPr` variants) | 2, 3 |
| VML fallback (`mc:Fallback` / `v:shape`) | — (raw-set only; high-level `add` does not emit one) |
| `mc:AlternateContent`/`mc:Choice Requires="wps"` | 2, 3 (raw scenarios) |
| **Build path** | high-level `add`: 1, 4, 5, 6, 7, 8, 9, 10 · `raw-set`: 2, 3 |

## Inspect the Generated File

```bash
# View the document outline (headings and textbox scenario labels)
officecli view textbox.docx outline

# Query all drawing anchors (each textbox is a wp:anchor drawing)
officecli query textbox.docx drawing

# Validate the generated file
officecli validate textbox.docx
```
