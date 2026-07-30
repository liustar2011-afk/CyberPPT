# Sparklines Showcase

Exercises the full xlsx `sparkline` element — the in-cell mini charts (line,
column, win/loss) that render a trend inside a single cell. Three files work
together:

- **sparklines.py** — builds the workbook via the **officecli Python SDK**.
- **sparklines.xlsx** — the generated dashboard workbook.
- **sparklines.md** — this file.

## Built on the SDK (not subprocess)

Like `conditional-formatting.py`, this script drives the
[`officecli-sdk`](../../sdk/python) Python client rather than shelling out per
command. One resident process is started; the whole dashboard — data cells and
sparklines — ships over the named pipe in a single `doc.batch(...)` round-trip:

```python
import officecli                      # pip install officecli-sdk

with officecli.create(FILE, "--force") as doc:
    doc.batch([
        {"command": "set", "path": "/Sheet1/B2", "props": {"value": "45"}},
        {"command": "add", "parent": "/Sheet1", "type": "sparkline",
         "props": {"type": "line", "dataRange": "B2:M2", "location": "N2",
                   "color": "#4472C4", "lineWeight": "1.5"}},
    ])
```

The dict shape is identical to an `officecli batch` list item — `command`,
`path`/`parent`/`type`, and `props`. The script falls back to the in-repo SDK
copy if `officecli-sdk` isn't pip-installed, so it runs straight from a checkout.

## Regenerate

```bash
cd examples/excel
pip install officecli-sdk          # plus the `officecli` binary on PATH
python3 sparklines.py              # → sparklines.xlsx
# or the CLI twin:
bash sparklines.sh
```

## A sparkline

Each sparkline is one `add` against the sheet. `type=` picks the kind,
`dataRange=` is the source values, and `location=` is the cell the mini chart
draws in (place it next to the data row for a dashboard look):

```bash
officecli add file.xlsx /Sheet1 --type sparkline \
  --prop type=line --prop dataRange=B2:M2 --prop location=N2 \
  --prop color=#4472C4 --prop lineWeight=1.5
```

The group lands at `/Sheet1/sparkline[N]`; `get`/`set`/`remove` address it
there. Sparkline groups are stored under the worksheet's **x14 extension list**
(the Excel 2010+ feature area).

## Dashboard layout

One sheet: label in column A, twelve months of trend data across B–M, and the
sparkline in column N of the same row.

| Row | Label | Type | Highlights demonstrated |
|---|---|---|---|
| 2 | North | `line` | plain series colour, `lineWeight=1.5` |
| 3 | South | `line` | `markers` + all four point highlights + every marker colour |
| 4 | East | `column` | `highPoint`/`lowPoint` with marker colours |
| 5 | West | `column` | `firstPoint`/`lastPoint` with marker colours |
| 6 | Central | `column` | plain single-colour bars |
| 7 | Online | `winLoss` | `negative` points in `negativeColor` |
| 8 | Kiosk | `winLoss` (via `win-loss` alias) | high/low + negative |

## Sparkline kinds (`type=`)

`line`, `column`, `winLoss`. `stacked` and `win-loss` are accepted aliases that
both map to OOXML stacked and **read back as `winLoss`**.

```bash
officecli add file.xlsx /Sheet1 --type sparkline --prop type=line    --prop dataRange=B2:M2 --prop location=N2
officecli add file.xlsx /Sheet1 --type sparkline --prop type=column  --prop dataRange=B4:M4 --prop location=N4
officecli add file.xlsx /Sheet1 --type sparkline --prop type=winLoss --prop dataRange=B7:M7 --prop location=N7
```

## Point highlights & markers

Toggle any of the "special point" highlights; each has an **add-only** marker
colour. `markers=true` shows a marker at every point (line sparklines only).

```bash
officecli add file.xlsx /Sheet1 --type sparkline --prop type=line --prop dataRange=B3:M3 --prop location=N3 \
  --prop markers=true \
  --prop highPoint=true  --prop highMarkerColor=#00B050 \
  --prop lowPoint=true   --prop lowMarkerColor=#FF0000 \
  --prop firstPoint=true --prop firstMarkerColor=#7030A0 \
  --prop lastPoint=true  --prop lastMarkerColor=#0070C0 \
  --prop markersColor=#808080 \
  --prop lineWeight=2.25
```

## Negative points (win/loss & highlight)

`negative=true` highlights negative points in `negativeColor` — the defining
behaviour of a win/loss sparkline, but usable on line/column too.

```bash
officecli add file.xlsx /Sheet1 --type sparkline --prop type=winLoss --prop dataRange=B7:M7 --prop location=N7 \
  --prop negative=true --prop negativeColor=#C00000
```

## Complete property coverage

| Group | Props | Ops |
|---|---|---|
| Kind | `type` (`line`/`column`/`winLoss`/`stacked`/`win-loss`) | add/set/get |
| Source & target | `dataRange`, `location` | add/set/get |
| Series style | `color`, `lineWeight` | add/set/get |
| Point highlights | `firstPoint`, `lastPoint`, `highPoint`, `lowPoint`, `negative` | add/set/get |
| Markers toggle | `markers` | add/set/get |
| Negative colour | `negativeColor` | add/set/get |
| Marker colours | `firstMarkerColor`, `lastMarkerColor`, `highMarkerColor`, `lowMarkerColor`, `markersColor` | **add-only** |

> Marker colours are **add-only** — set at creation, not modifiable via `set`,
> and not echoed by `get` (they live inline on the group's point definitions).
> The five point-highlight flags and `negativeColor` do round-trip.

Full property list: `officecli help xlsx sparkline` (or
`schemas/help/xlsx/sparkline.json`).

## Read a sparkline back

```bash
officecli query sparklines.xlsx sparkline
officecli get sparklines.xlsx "/Sheet1/sparkline[1]" --json
```

`get` normalizes on read: colours gain a `#` prefix (`#4472C4`), `type` comes
back as the canonical token (`stacked`/`win-loss` → `winLoss`), and
`lineWeight` reads back as a number.

## Validating

A sparkline group lives in the worksheet's x14 extension list, so validate the
**saved** file from a fresh process:

```bash
officecli validate sparklines.xlsx
```
