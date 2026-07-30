# Mermaid Diagrams — native + image (full type gallery)

Render [Mermaid](https://mermaid.js.org/) source into a slide two ways:

- **`render=native`** — the built-in synthesizer draws the diagram as **editable
  PowerPoint shapes + connectors** (no browser). Supported types: `flowchart` /
  `graph` and `sequenceDiagram`. Fully editable in PowerPoint.
- **`render=image`** — real **mermaid.js** (headless Chrome / Chromium / Edge)
  renders a **full-fidelity PNG**, covering **every** mermaid type. The mermaid
  source is stamped into the picture's alt-text, so the diagram is regenerable.
- **`render=auto`** (default) — image when a browser is present, else native.

This demo ships four files:

- **diagram.sh** — CLI build script (`officecli add … --type diagram`).
- **diagram.py** — SDK twin, regenerates the same deck.
- **diagram.pptx** — the generated deck (native flowchart + sequence, the same
  flowchart as PNG, then an image gallery of every other mermaid type).
- **diagram.md** — this file.

A diagram is an **ADD-ONLY synthesizer** (like `equation`): there is no persistent
`diagram` node. The whole picture is wrapped in **one object** and `add` returns
its path — a **group** in native mode (`/slide[N]/group[K]`), a single **picture**
in image mode (`/slide[N]/picture[K]`). Either is addressable and movable as one
unit; the native group re-bakes child font sizes when you resize it.

## Regenerate

```bash
cd examples/ppt
bash diagram.sh          # or: python3 diagram.py
# → diagram.pptx
```

> `render=image` slides need a headless browser. Without one, use `render=auto`
> (the default) and those slides fall back to native shapes.

## Deck

| Slide | Mode | Type | Source prop |
|------|------|------|------|
| 2 | `native` | flowchart | `mermaid=` |
| 3 | `image` | flowchart (same source as 2) | `dsl=` |
| 4 | `native` | sequenceDiagram | `text=` |
| 5 | `image` | pie | `src=` (`.mmd` file) |
| 6–23 | `image` | classDiagram, stateDiagram-v2, erDiagram, gantt, journey, gitGraph, mindmap, timeline, quadrantChart, requirementDiagram, C4Context, sankey-beta, xychart-beta, block-beta, packet-beta, kanban, architecture-beta, radar-beta | `text=` |

### Native (slides 2 & 4)

```bash
# flowchart — full node-shape vocabulary + edge forms
officecli add diagram.pptx '/slide[2]' --type diagram \
  --prop render=native \
  --prop mermaid="flowchart TD
  A([Start]) --> B{Decision}
  B -->|yes| C[Process]
  B -->|no| D[(Database)]
  C --> E[[Subroutine]]
  D -.-> F{{Prepare}}
  E ==> G((Done))
  F --> G
  A --> H[/Input/]
  H --x B" \
  --prop x=1in --prop y=1.2in --prop width=11.3in --prop height=5.8in

# sequenceDiagram (text= is an alias of mermaid=)
officecli add diagram.pptx '/slide[4]' --type diagram \
  --prop render=native \
  --prop text="sequenceDiagram
  participant U as User
  participant S as Server
  U->>S: Login request
  S-->>U: Session token" \
  --prop x=1in --prop y=1.2in --prop width=11.3in --prop height=5.8in
```

**Node shapes:** `([stadium])`, `{diamond}`, `[rect]`, `[(database)]`,
`[[subroutine]]`, `{{hexagon}}`, `[/parallelogram/]`, `((circle))`.
**Edges:** `-->|label|`, `-.->` (dashed), `==>` (thick), `--x` (cross end).
The diagram is fitted into the box (aspect preserved) and **centred**.

### Image — same flowchart as a PNG (slide 3)

```bash
officecli add diagram.pptx '/slide[3]' --type diagram \
  --prop render=image \
  --prop dsl="flowchart TD; A([Start]) --> B{Decision} --> C[Process]" \
  --prop x=1in --prop y=1.2in --prop width=11.3in --prop height=5.8in
```

`dsl=` is another alias of `mermaid=`. Compare with slide 2 — same topology, a
pixel-perfect raster instead of editable shapes.

### Image gallery — every other mermaid type (slides 5–23)

`render=image` goes through real mermaid.js, so anything outside the native
`flowchart` / `sequenceDiagram` subset still renders. The pie slide loads its
source from a file with `src=`:

```bash
cat > pie.mmd << 'EOF'
pie showData title Traffic Sources
    "Organic Search" : 45
    "Direct" : 30
    "Referral" : 15
    "Social" : 10
EOF

officecli add diagram.pptx '/slide[5]' --type diagram \
  --prop render=image --prop src=pie.mmd \
  --prop x=1in --prop y=1.2in --prop width=11.3in --prop height=5.8in
```

The rest of the gallery passes the source inline with `text=`:
`classDiagram`, `stateDiagram-v2`, `erDiagram`, `gantt`, `journey`, `gitGraph`,
`mindmap`, `timeline`, `quadrantChart`, `requirementDiagram`, `C4Context`,
`sankey-beta`, `xychart-beta`, `block-beta`, `packet-beta`, `kanban`,
`architecture-beta`, `radar-beta`.

## Complete Property Coverage

| Property | Meaning | Where |
|----------|---------|-------|
| `mermaid` | Canonical source (header line picks the diagram kind) | slide 2 |
| `text` | Alias of `mermaid` | slide 4 + gallery |
| `dsl` | Alias of `mermaid` | slide 3 |
| `src` (`path`) | Load source from a `.mmd` file | slide 5 (pie) |
| `render=native` | Editable shapes + connectors (no browser) | slides 2, 4 |
| `render=image` | Full-fidelity PNG via mermaid.js (needs a browser) | slides 3, 5–23 |
| `render=auto` | Image when a browser is present, else native (default) | — (combines the two above) |
| `x` / `y` | Top-left of the placement box | every diagram |
| `width` / `height` | Box the diagram is scaled to fit (aspect preserved, centred) | every diagram |
| `poster=true` | Grow the **whole deck** to the diagram's natural size (export-a-diagram-as-a-slide) | see below |

### `poster` — the one deck-wide property

pptx has a single presentation-wide slide size, so `poster=true` resizes **every
slide** to the diagram's natural size. It is mutually exclusive with a multi-slide
showcase, so it lives in a single-diagram file rather than this gallery:

```bash
officecli create poster.pptx
officecli add poster.pptx / --type slide
officecli add poster.pptx '/slide[1]' --type diagram --prop poster=true \
  --prop mermaid="flowchart LR; A --> B --> C"
# → the slide is grown to the diagram's exact size (x/y/width/height ignored)
```

## Manipulate the diagram after Add (`get` / `set` / `remove`)

`add` returns the object path. For a **native** diagram that is a group:

```bash
officecli get diagram.pptx '/slide[2]/group[1]'                 # read the box back
officecli set diagram.pptx '/slide[2]/group[1]' --prop width=6in # resize as a unit (fonts re-bake)
officecli remove diagram.pptx '/slide[2]/group[1]'              # delete group + every child
```

For an **image** diagram it is a picture (`/slide[N]/picture[K]`) — move / resize
/ remove it like any other picture.

## Native vs image at a glance

| | `render=native` | `render=image` |
|---|---|---|
| Output | group of shapes + connectors | one PNG picture |
| Returned path | `/slide[N]/group[K]` | `/slide[N]/picture[K]` |
| Editable in PowerPoint | ✅ every shape | ❌ raster (source in alt-text) |
| Browser required | no | yes (Chrome / Chromium / Edge) |
| Supported types | `flowchart` / `graph`, `sequenceDiagram` | every mermaid type |

## Inspect the Generated File

```bash
officecli view diagram.pptx outline                 # native groups on 2/4, pictures on 3 & 5–23
officecli get diagram.pptx '/slide[2]/group[1]'      # native flowchart — shapes + connectors
officecli get diagram.pptx '/slide[3]/picture[1]'    # image flowchart — PNG (mermaid source in alt-text)
officecli query diagram.pptx '/slide[2]' shape       # each editable node in the native group
```

## docx parity

The same `--type diagram` element works in Word (`officecli add report.docx /body
--type diagram …`), with the same `mermaid` / `text` / `dsl` / `src` / `width` /
`height` / `render` props. Word has no slide, so there is no `poster` and no
`x` / `y` — the diagram fits the section text-area width. The parse + layout
engine is shared; only the drawing output differs.
