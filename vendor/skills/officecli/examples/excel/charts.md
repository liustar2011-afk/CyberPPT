# charts — Master chart showcase

Generates **charts.xlsx**: eight chart types across four data sheets, built with
the high-level `officecli add --type chart` command (one `add` per chart). Each
chart references its sheet data by cell range (`dataRange`) — or, where the source
cells aren't contiguous, inline `series`/`categories`.

Three files (the usual four-set, minus a hand-written `.xlsx` — it's generated):

- **charts.sh** — CLI script (`officecli add --type chart …`).
- **charts.py** — SDK twin (same commands over one resident).
- **charts.xlsx** — generated output.

```bash
cd examples/excel
bash charts.sh          # or: python3 charts.py
```

For per-type deep dives (every option of a single chart kind) see the
[`charts/`](charts/) subdirectory (`charts-column.sh`, `charts-combo.sh`,
`charts-stock.sh`, …).

## The eight charts

| # | Sheet | Type | Key props |
|---|-------|------|-----------|
| 1 | Sheet1 | Combo | `combotypes=column,column,column,column,line` + `secondaryaxis=5` (YoY-growth line on a right-hand axis) |
| 2 | Sheet1 | 3D column | `chartType=column3d` + `view3d=15,20,30` |
| 3 | Analysis | Scatter | `chartType=scatter` + `trendline=linear` (equation + R² shown) |
| 4 | Sheet1 | 3D pie (exploded) | `chartType=pie3d` + `explosion=10` + `view3d=30,70,30` + `dataLabels=percent` |
| 5 | Analysis | Bubble | **raw-set** — see note below |
| 6 | StockData | Stock OHLC | `chartType=stock` + `hilowlines=true` + `updownbars=100:FF0000:00B050` (red up / green down) |
| 7 | Assessment | Filled radar | `chartType=radar` + `radarStyle=filled` |
| 8 | Sheet1 | Multi-ring doughnut | `chartType=doughnut` + two inline series (two rings) |

Common props on every chart: `title`, `colors` (comma-separated palette),
`legend=b`, and `x`/`y`/`width`/`height` (position and size in cell units).

## Why Chart 5 (bubble) stays on raw-set

A bubble point needs three coordinates — x, y and size. The high-level
`add --type chart --prop chartType=bubble` reads a multi-column `dataRange` as
several y-series sharing column A as x; it cannot map three columns to a single
x / y / size series (a multi-point bubble). Until that mapping exists, the
faithful single-series bubble is authored with `raw-set`. Every other chart here
uses the high-level command.

## Inspect

```bash
officecli validate charts.xlsx
officecli view charts.xlsx outline
officecli query charts.xlsx chart          # list all chart parts
officecli get charts.xlsx '/Sheet1/chart[1]'
```
