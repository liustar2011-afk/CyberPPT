# Animation Showcase

Demonstrates the first-class pptx **`animation` element** and its full property
surface. Three files work together:

- **animations.sh** — Shell script driving `officecli create/open/add/set/close`.
- **animations.py** — SDK twin (`officecli-sdk`), same deck via `doc.batch(...)`.
- **animations.pptx** — The generated 7-slide deck.

## The animation element

An animation is a child element of a **shape** (or **chart**):

```bash
officecli add animations.pptx /slide[N]/shape[M] --type animation \
  --prop effect=fade --prop class=entrance --prop duration=800
```

`add ... --type animation` gives you the full timing model. (The legacy
`set --prop animation=fade-entrance-800` compound-token shortcut still works for
quick one-liners, but the element form is what exposes trigger/delay/repeat/
autoReverse/restart/motion-paths.)

On `get`, each facet is its own key — there is **no** composite `animation` key
in readback:

```bash
officecli get animations.pptx /slide[2]/shape[3]/animation[1]
# → effect=fade class=entrance presetId=10 trigger=onClick duration=800
```

## Regenerate

```bash
cd examples/ppt
bash animations.sh          # → animations.pptx (7 slides, 44 animations)
# or the SDK twin:
python3 animations.py
```

## Property reference

| Prop | Values / format | Notes |
|---|---|---|
| `effect` | preset name (see catalog below) | The animation preset. Some effects require a specific `class`. |
| `class` | `entrance` \| `exit` \| `emphasis` \| `motion` | Category. `spin/grow/wave` need `emphasis`; `motion` needs `path=`. |
| `trigger` | `onClick` \| `withPrevious` \| `afterPrevious` | When it starts. Default `onClick`. |
| `duration` | ms integer (alias `dur`) | e.g. `500` = 0.5s. |
| `delay` | ms integer | Delay before starting. |
| `repeat` | positive int \| `indefinite` | Loop count, or loop forever. |
| `autoReverse` | `true` / `false` | Play forward then reverse (doubles the visible run). |
| `restart` | `always` \| `whenNotActive` \| `never` | Behavior when re-triggered. |
| `direction` | `in`/`out`/`left`/`right`/`up`/`down` (+ aliases `top`/`bottom`, `l/r/u/d`) | For directional effects. |
| `path` | `line` \| `arc` \| `circle` \| `diamond` \| `triangle` \| `square` \| `custom` | Motion preset (only with `class=motion`). |
| `d` | SVG-like path, coords 0..1 of slide | Custom motion path (only with `path=custom`; auto-appends `E`). |

Get-only facets: `presetId`, `easein`, `easeout`, `motionPath`.

## Timing model

Animations on a slide play as an ordered list. Each animation's `trigger`
decides how it relates to the one before it:

- **`onClick`** — waits for a mouse click to start (the default).
- **`afterPrevious`** — starts automatically when the previous animation ends
  (add `delay=` for a gap).
- **`withPrevious`** — starts at the same instant as the previous animation.

Chaining `onClick → afterPrevious → withPrevious …` builds a self-playing
sequence off a single click (see Slide 6).

## Effect catalog

**Entrance / Exit** (same names, pick via `class=`):
`appear`, `fade`, `fly`, `zoom`, `wipe`, `bounce`, `float`, `swivel`, `split`,
`wheel`, `checkerboard`, `blinds`, `dissolve`, `flash`, `box`, `circle`,
`diamond`, `plus`, `strips`, `wedge`, `random`.

**Emphasis** (`class=emphasis`):
motion — `spin`, `grow`, `wave`, `bold`, `growShrink`, `teeter`, `pulse`;
color — `fillColor`, `lineColor`, `transparency`, `complementaryColor`,
`complementaryColor2`, `contrastingColor`, `darken`, `desaturate`, `lighten`,
`objectColor`, `colorPulse`.

**Motion** (`class=motion` + `path=`): `line`, `arc`, `circle`, `diamond`,
`triangle`, `square`, `custom`.

**Template exit effects** (`class=exit`, verbatim PowerPoint OOXML):
`contract`, `centerRevolve`, `collapse`, `floatOut`, `shrinkTurn`, `sinkDown`,
`spinner`, `basicZoom`, `stretchy`, `boomerang`, `credits`, `curveDown`,
`pinwheel`, `spiralOut`, `basicSwivel`.

> **Known limitation — template exit effects are lossy on readback.** These 15
> effects are backed by byte-for-byte PowerPoint-authored OOXML, so they render
> correctly in PowerPoint but **ignore the `duration` prop** (they keep the
> authored timing) and **do not round-trip their effect name** — `get` reports
> them as a generic `effect=fade`/`split`/`unknown` plus a `presetId`. Because
> the effect name doesn't survive a round-trip, this demo builds its slides from
> the effects that round-trip cleanly. Use the template effects directly in a
> deck when you want their exact PowerPoint look; just don't rely on `get`
> echoing the name back.

## Slides

### Slide 1 — Title

Radial-gradient title slide (`layout=title`, `background=radial:`, title +
subtitle placeholders, `transition=fade`).

### Slide 2 — Entrance Effects

Twelve entrance effects on a 4-column grid, each with its own `duration`.

```bash
officecli add animations.pptx /slide[2]/shape[2] --type animation \
  --prop effect=appear --prop class=entrance --prop duration=400
officecli add animations.pptx /slide[2]/shape[3] --type animation \
  --prop effect=fade --prop class=entrance --prop duration=800
# … fly, zoom, wipe, bounce, float, swivel, split, wheel, box, circle
```

**Features:** `effect=` (entrance family), `class=entrance`, `duration=`.

### Slide 3 — Exit Effects

Ten exit effects; directional ones (`fly`, `wipe`) add `direction=`.

```bash
officecli add animations.pptx /slide[3]/shape[3] --type animation \
  --prop effect=fly --prop class=exit --prop direction=down --prop duration=600
officecli add animations.pptx /slide[3]/shape[6] --type animation \
  --prop effect=wipe --prop class=exit --prop direction=left --prop duration=600
```

**Features:** `class=exit`, `direction=` on directional effects.

### Slide 4 — Emphasis & Color Effects

Six emphasis effects on ellipses — motion (`spin`, `grow`, `wave`, `growShrink`,
`teeter`) and `pulse`.

```bash
officecli add animations.pptx /slide[4]/shape[2] --type animation \
  --prop effect=spin --prop class=emphasis --prop duration=1000
officecli add animations.pptx /slide[4]/shape[5] --type animation \
  --prop effect=growShrink --prop class=emphasis --prop duration=800
```

**Features:** `class=emphasis`; color-change and motion emphasis effects.

### Slide 5 — Motion Paths

Preset paths (`line`, `arc`, `circle`, `diamond`, `square`) plus a custom `d=`.

```bash
officecli add animations.pptx /slide[5]/shape[2] --type animation \
  --prop class=motion --prop path=line --prop direction=right --prop duration=1000
# Custom path — coords are 0..1 of the slide; a trailing 'E' is auto-appended
officecli add animations.pptx /slide[5]/shape[8] --type animation \
  --prop class=motion --prop path=custom \
  --prop d='M 0 0 L 0.3 -0.1 L 0.6 0.1 E' --prop duration=1500
```

**Features:** `class=motion`, `path=<preset|custom>`, `direction=`, `d=`.
`get` echoes the resolved path back as `motionPath=`.

### Slide 6 — Timing & Trigger Chaining

Five shapes chained into a self-playing sequence off one click, plus a `delay=`
and a slow (2000ms) run.

```bash
officecli add animations.pptx /slide[6]/shape[2] --type animation \
  --prop effect=fade --prop class=entrance --prop trigger=onClick --prop duration=500
officecli add animations.pptx /slide[6]/shape[3] --type animation \
  --prop effect=fly --prop class=entrance --prop trigger=afterPrevious --prop duration=600
officecli add animations.pptx /slide[6]/shape[4] --type animation \
  --prop effect=zoom --prop class=entrance --prop trigger=withPrevious --prop duration=600
officecli add animations.pptx /slide[6]/shape[5] --type animation \
  --prop effect=wipe --prop class=entrance --prop trigger=afterPrevious \
  --prop delay=800 --prop duration=700
```

**Features:** `trigger=onClick|afterPrevious|withPrevious`, `delay=`, duration
range (500–2000ms).

### Slide 7 — Repeat, autoReverse & Restart

```bash
officecli add animations.pptx /slide[7]/shape[2] --type animation \
  --prop effect=spin --prop class=emphasis --prop repeat=3 --prop duration=800
officecli add animations.pptx /slide[7]/shape[3] --type animation \
  --prop effect=pulse --prop class=emphasis --prop repeat=indefinite \
  --prop trigger=withPrevious --prop duration=600
officecli add animations.pptx /slide[7]/shape[4] --type animation \
  --prop effect=grow --prop class=emphasis --prop autoReverse=true \
  --prop repeat=2 --prop duration=700
officecli add animations.pptx /slide[7]/shape[5] --type animation \
  --prop effect=teeter --prop class=emphasis --prop restart=whenNotActive \
  --prop repeat=indefinite --prop duration=500
```

**Features:** `repeat=<int>`, `repeat=indefinite`, `autoReverse=true`,
`restart=whenNotActive`.

## Complete feature coverage

| Feature | Slide |
|---------|-------|
| `add --type animation` element | 2–7 |
| `effect=` entrance family | 2 |
| `effect=` exit family | 3 |
| `effect=` emphasis (motion + color) | 4 |
| `class=entrance` / `exit` / `emphasis` / `motion` | 2 / 3 / 4 / 5 |
| `duration=` (400–2000ms) | 2–7 |
| `delay=` | 6 |
| `direction=` on directional effects | 3, 5 |
| `trigger=onClick` / `afterPrevious` / `withPrevious` | 6 |
| `repeat=<int>` / `repeat=indefinite` | 7 |
| `autoReverse=true` | 7 |
| `restart=whenNotActive` | 7 |
| `path=` preset motion + `d=` custom | 5 |
| `transition=` (fade, wipe, push, zoom, split, reveal) | 1–7 |

## Inspect the generated file

```bash
officecli query animations.pptx animation
officecli get animations.pptx /slide[2]/shape[3]/animation[1]
officecli get animations.pptx /slide[6]/shape[5]/animation[1]
officecli get animations.pptx /slide[7]/shape[4]/animation[1]
```
