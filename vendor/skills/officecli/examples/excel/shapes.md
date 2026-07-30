# Excel Shapes Gallery

Exercises the xlsx `shape` property surface (`officecli help xlsx shape`) — the
drawing layer that floats above the grid. Three files work together:

- **shapes.sh** — Bash script that drives `officecli` (CLI) to build the workbook.
- **shapes.py** — Python script that drives the officecli **SDK** to build an equivalent workbook.
- **shapes.xlsx** — The generated single-sheet shape gallery (20 shapes).

## Regenerate

```bash
cd examples/excel
bash shapes.sh          # CLI twin
# or
python3 shapes.py       # SDK twin
# → shapes.xlsx
```

Both scripts use resident mode (`open` … `close` / SDK context manager) for
speed and end with a `validate`.

## Anchoring model (read this first)

Excel shapes are **cell-anchored**, not point/inch-positioned. The `x` / `y` /
`width` / `height` props are **TwoCellAnchor column/row indices** (integers),
*not* lengths:

```bash
officecli add file.xlsx /Sheet1 --type shape --prop geometry=rect \
  --prop x=0 --prop y=4 --prop width=2 --prop height=3
```

means "top-left at column 0, row 4; span 2 columns × 3 rows". `Get` reads the
position back as those same integer indices.

The `anchor` prop is an **add-only** convenience that takes a cell range and is
normalized to `x/y/width/height` on readback (there is no `anchor` key in `Get`):

```bash
officecli add file.xlsx /Sheet1 --type shape --prop anchor=K25:L28 ...
# Get → x=10 y=24 width=1 height=3
```

Parent path for `add` is the sheet (`/Sheet1`); the address for
`set`/`get`/`remove` is `/Sheet1/shape[N]`.

## Shape property table

| Feature | Spec | Round-trips in `Get`? |
|---|---|---|
| Geometry preset | `geometry=rect\|roundRect\|ellipse\|triangle\|diamond\|parallelogram\|rightArrow\|star5\|…` (aliases `preset`, `shape`) | yes |
| Position / size | `x` `y` `width` `height` (cell indices; aliases `left`/`top`/`w`/`h`) | yes (integers) |
| Cell-range anchor | `anchor=K25:L28` (add-only; alias `ref`) | as `x/y/width/height` |
| Solid fill | `fill=4472C4` / `fill=accent1` (theme) / `fill=none` (aliases `background`) | yes (`#`-hex or scheme name) |
| Gradient fill | `gradientFill=C1-C2[:angle]` (2/3-stop linear; wins over `fill`; **add-only**) | no readback |
| Outline | `line=C00000:2:dash` — `color[:width[:style]]` (width in pt; style: `solid`/`dash`/`dot`/`dashdot`/`longdash`); plain `line=264653` still works; `line=none`; alias `border`/`lineColor` | no readback |
| Flip | `flipH=true` / `flipV=true` / `flipBoth=true` / `flip=h\|v\|both` | yes (as `flip`) |
| Rotation | `rotation=30` (degrees clockwise; aliases `rot`/`rotate`) | yes |
| Glow | `glow=FFD700` (color or `true`) | yes (`#RRGGBB-<radius>`) |
| Shadow | `shadow=000000` (color or `true`) | yes (`#`-hex) |
| Soft edge | `softEdge=4` (radius; alias `softedge`) | yes (`4pt`) |
| Reflection | `reflection=true` (**add-only**) | no readback |
| Text | `text="…"` | yes |
| Font | `font=Georgia`, `size=12`, `bold`, `italic`, `underline`, `color` | yes |
| Text align | `align=center` (paragraph), `valign=top\|center\|bottom` | yes |
| Text inset | `margin=6` (uniform padding) | yes (`6pt`) |
| Name | `name=MyStar` (overrides auto `Shape {id}`) | yes |

## Gallery layout

One `Gallery` sheet (`Sheet1`), 20 shapes in five bands of four, each shape
under a bold label cell:

| Band | Shapes |
|---|---|
| 1 | `rect`, `roundRect`, `ellipse`, `triangle` — solid fills, white/dark text |
| 2 | `diamond`, `parallelogram`, `rightArrow`, `star5` (with `name=MyStar`) |
| 3 | `flipH`, `flipV`, `flipBoth`, `rotation=30` |
| 4 | `glow`, `gradientFill`, `reflection`, `shadow`+`softEdge` |
| 5 | `line=C00000:2:dash` (compound `color:width:style`, `fill=none` outline-only), styled text (`font`/`size`/`italic`/`align`/`margin`), `fill=accent1` (theme), `anchor=K25:L28` |

```bash
# A geometry preset with solid fill + centered white text
officecli add shapes.xlsx /Sheet1 --type shape --prop geometry=roundRect \
  --prop x=3 --prop y=4 --prop width=2 --prop height=3 \
  --prop fill=2A9D8F --prop text="roundRect" --prop color=FFFFFF --prop bold=true

# Flip + rotation
officecli add shapes.xlsx /Sheet1 --type shape --prop geometry=rightArrow \
  --prop x=0 --prop y=14 --prop width=2 --prop height=3 --prop fill=4472C4 --prop flipH=true
officecli add shapes.xlsx /Sheet1 --type shape --prop geometry=rightArrow \
  --prop x=9 --prop y=14 --prop width=2 --prop height=3 --prop fill=E9C46A --prop rotation=30

# Effects
officecli add shapes.xlsx /Sheet1 --type shape --prop geometry=ellipse \
  --prop x=0 --prop y=19 --prop width=2 --prop height=3 --prop fill=2A9D8F --prop glow=FFD700
officecli add shapes.xlsx /Sheet1 --type shape --prop geometry=roundRect \
  --prop x=3 --prop y=19 --prop width=2 --prop height=3 --prop gradientFill=FF6B6B-4ECDC4:45
officecli add shapes.xlsx /Sheet1 --type shape --prop geometry=rect \
  --prop x=9 --prop y=19 --prop width=2 --prop height=3 --prop fill=8E44AD --prop shadow=000000 --prop softEdge=4

# Styled text inside a shape
officecli add shapes.xlsx /Sheet1 --type shape --prop geometry=roundRect \
  --prop x=3 --prop y=24 --prop width=2 --prop height=3 --prop fill=E9C46A \
  --prop text="Georgia italic center-top" \
  --prop font=Georgia --prop size=12 --prop italic=true --prop align=center --prop valign=top --prop margin=6
```

## Known limitations (xlsx shape)

- **`line` compound form works** (matches pptx shape line). Both `add` and `set`
  accept `line=color[:width[:style]]` — e.g. `line=C00000:2:dash` sets a
  2 pt dashed dark-red outline, emitting `<a:ln w="25400"><a:solidFill…/><a:prstDash val="dash"/></a:ln>`.
  Width is in points; `style` is a `prstDash` token (`solid`/`dash`/`dot`/`dashdot`/`longdash`).
  Plain `line=264653` and `line=none` still work. `Get` does not currently emit
  a `line` key, so the outline is add/set-only on readback.
- **`gradientFill` and `reflection` are add-only.** They apply and survive to a
  valid file, but `Get` does not emit a `gradientFill`/`reflection` key
  (and a `gradientFill` shape reports no `fill` on readback either).

## Set → Get round-trip

Both scripts end by reading shapes back and printing the canonical keys. Sample:

```
/Sheet1/shape[8]:  {'name': 'MyStar', 'geometry': 'star5'}
/Sheet1/shape[9]:  {'flip': 'h', 'geometry': 'rightArrow'}          # flipH → flip=h
/Sheet1/shape[12]: {'rotation': 30, 'geometry': 'rightArrow'}
/Sheet1/shape[13]: {'glow': '#FFD700-8', 'fill': '#2A9D8F'}
/Sheet1/shape[16]: {'shadow': '#000000', 'softEdge': '4pt'}
/Sheet1/shape[18]: {'font': 'Georgia', 'size': '12pt', 'align': 'center', 'margin': '6pt'}
/Sheet1/shape[20]: {'x': '10', 'y': '24', 'width': '1', 'height': '3'}  # anchor=K25:L28
```

Note the normalization on `get`: colors gain a `#` prefix, sizes/margins/soft
edges become unit-qualified (`12pt`, `6pt`, `4pt`), and `flipH`/`flipV`/`flipBoth`
all read back under the single `flip` key.

## Inspect the Generated File

```bash
officecli query shapes.xlsx shape                 # list all 20 shapes
officecli get   shapes.xlsx "/Sheet1/shape[8]"    # the named star5
officecli get   shapes.xlsx "/Sheet1/shape[18]"   # styled-text shape
```
