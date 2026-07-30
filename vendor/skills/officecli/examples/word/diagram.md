# Mermaid Diagrams in Word

The same `--type diagram` element as PowerPoint, targeting a `.docx` body. Render
[Mermaid](https://mermaid.js.org/) source two ways:

- **`render=native`** — the built-in synthesizer draws **editable Word drawing
  shapes + connectors** (no browser). Supported types: `flowchart` / `graph` and
  `sequenceDiagram`. These are **floating** shapes anchored to the page margin, so
  give each native diagram its own page (a page break) to avoid overlapping text.
- **`render=image`** — real **mermaid.js** (headless Chrome / Chromium / Edge)
  renders a **full-fidelity PNG** covering **every** mermaid type. The picture is
  **inline**, so it flows with the text like any image — the natural choice inside
  a flowing document. The mermaid source is stamped into the picture's alt-text.
- **`render=auto`** (default) — image when a browser is present, else native.

This demo ships four files:

- **diagram.sh** — CLI build script (`officecli add report.docx /body --type diagram`).
- **diagram.py** — SDK twin, regenerates the same document.
- **diagram.docx** — the generated document.
- **diagram.md** — this file.

A diagram is an **ADD-ONLY synthesizer** (like `equation`): there is no persistent
`diagram` node. The whole picture is wrapped in **one object** and `add` returns its
path — a **group** in native mode (`/body/group[N]`), an **inline picture** in a
paragraph in image mode. Word has no slide, so there is **no `x`/`y` and no
`poster`** (those are pptx-only); `width`/`height` fit the diagram (aspect preserved).

## Regenerate

```bash
cd examples/word
bash diagram.sh          # or: python3 diagram.py
# → diagram.docx
```

> `render=image` diagrams need a headless browser. Without one, use `render=auto`
> (the default) and they fall back to native shapes.

## Document

| Page(s) | Mode | Type | Source prop |
|------|------|------|------|
| native | `native` | flowchart | `mermaid=` |
| native | `native` | sequenceDiagram | `text=` |
| image | `image` | flowchart (same source) | `dsl=` |
| image | `image` | pie | `src=` (`.mmd` file) |
| image | `image` | classDiagram, stateDiagram-v2, erDiagram, gantt, journey, gitGraph, mindmap, timeline, quadrantChart, requirementDiagram, C4Context, sankey-beta, xychart-beta, block-beta, packet-beta, kanban, architecture-beta, radar-beta | `text=` |

### Native — editable shapes (each on its own page)

```bash
# flowchart — full node-shape vocabulary; page break isolates the floating group
officecli add diagram.docx /body --type paragraph \
  --prop text="render=native — flowchart" --prop bold=true --prop size=16 --prop pageBreakBefore=true
officecli add diagram.docx /body --type diagram \
  --prop render=native \
  --prop mermaid="flowchart TD
  A([Start]) --> B{Decision}
  B -->|yes| C[Process]
  B -->|no| D[(Database)]
  C --> E[[Subroutine]]" \
  --prop width=12cm

# sequenceDiagram (text= is an alias of mermaid=)
officecli add diagram.docx /body --type diagram \
  --prop render=native \
  --prop text="sequenceDiagram
  participant U as User
  participant S as Server
  U->>S: Login request
  S-->>U: Session token" \
  --prop width=13cm
```

**Node shapes:** `([stadium])`, `{diamond}`, `[rect]`, `[(database)]`,
`[[subroutine]]`, `{{hexagon}}`, `[/parallelogram/]`, `((circle))`.
**Edges:** `-->|label|`, `-.->` (dashed), `==>` (thick), `--x` (cross end).

> Native diagrams are **floating** shapes. Add a `pageBreakBefore=true` heading
> before each so the anchored group does not overlap the surrounding text.

### Image — inline PNGs that flow with the text

```bash
# Same flowchart as a PNG (dsl= alias). Inline, so it flows after the paragraph.
officecli add diagram.docx /body --type diagram \
  --prop render=image --prop dsl="flowchart TD; A([Start]) --> B{Decision} --> C[Process]" \
  --prop width=14cm

# Load the source from a .mmd file with src= (any mermaid type — pie is not native)
cat > pie.mmd << 'EOF'
pie showData title Traffic Sources
    "Organic Search" : 45
    "Direct" : 30
EOF
officecli add diagram.docx /body --type diagram \
  --prop render=image --prop src=pie.mmd --prop width=10cm
```

The rest of the gallery passes the source inline with `text=`:
`classDiagram`, `stateDiagram-v2`, `erDiagram`, `gantt`, `journey`, `gitGraph`,
`mindmap`, `timeline`, `quadrantChart`, `requirementDiagram`, `C4Context`,
`sankey-beta`, `xychart-beta`, `block-beta`, `packet-beta`, `kanban`,
`architecture-beta`, `radar-beta`.

## Complete Property Coverage

| Property | Meaning | Where |
|----------|---------|-------|
| `mermaid` | Canonical source (header line picks the diagram kind) | native flowchart |
| `text` | Alias of `mermaid` | native sequence + gallery |
| `dsl` | Alias of `mermaid` | image flowchart |
| `src` (`path`) | Load source from a `.mmd` file | pie |
| `render=native` | Editable shapes + connectors (no browser) | flowchart, sequence |
| `render=image` | Full-fidelity inline PNG via mermaid.js (needs a browser) | the gallery |
| `render=auto` | Image when a browser is present, else native (default) | — |
| `width` / `height` | Fit the diagram (aspect preserved) | every diagram |

> Word has no `x` / `y` (no canvas coordinates — diagrams sit in the text flow) and
> no `poster` (no slide to grow). Those are pptx-only. See
> [`ppt/diagram.md`](../ppt/diagram.md) for the pptx version, which adds them.

## Manipulate a native diagram after Add (`get` / `set` / `remove`)

`add` returns the group path for a native diagram:

```bash
officecli get diagram.docx '/body/group[1]'                  # read the box back
officecli set diagram.docx '/body/group[1]' --prop width=8cm  # resize (fonts re-bake)
officecli remove diagram.docx '/body/group[1]'               # delete group + children
```

An image diagram is an inline picture in a paragraph — address it like any picture.

## Inspect the Generated File

```bash
officecli view diagram.docx outline
officecli get diagram.docx '/body/group[1]'      # native flowchart — editable shapes
```
