# Word Charts Showcase

This demo consists of four files that work together:

- **charts.sh** — CLI script that calls `officecli` to build the document. Each
  chart is preceded by a `# Features:` comment listing the properties it exercises.
- **charts.py** — Python SDK twin (`officecli-sdk`). One resident, all paragraphs
  and charts shipped over the named pipe in a single `doc.batch(...)`.
- **charts.docx** — the generated document: 14 inline charts, each under its own
  heading.
- **charts.md** — this file. Maps each chart to the features it demonstrates.

## How charts work in Word

Unlike Excel (where a chart pulls a `dataRange` out of a worksheet grid), a Word
chart is an **inline DrawingML object anchored on a paragraph**, and it carries
its data **inline**:

```bash
officecli add file.docx /body/p[N] --type chart \
  --prop chartType=column \
  --prop 'data=East:120,135,148;West:110,118,130' \
  --prop categories="Q1,Q2,Q3"
```

Data can be given three ways (same as pptx/xlsx charts):

- `data="Name1:1,2,3;Name2:4,5,6"` — inline shorthand, one series per `;`
- `series1="Name:1,2,3"` / `series2=...` — one prop per series
- `series1.name=` / `series1.values=` — dotted per-series keys

Word has no worksheet to reference, so **inline data is idiomatic** — there is no
`dataRange`.

### Addressing charts

You **add** a chart at its host paragraph (`/body/p[N]`), but once created the
chart is addressed **document-globally** as `/chart[M]` for `get` / `set` /
`query` — *not* `/body/p[N]/chart[M]`:

```bash
officecli add   file.docx /body/p[4] --type chart --prop chartType=pie ...
officecli query file.docx chart              # lists /chart[1], /chart[2], ...
officecli get   file.docx '/chart[1]'        # read one chart back
officecli set   file.docx '/chart[1]' --prop title="New Title"
```

## Regenerate

```bash
cd examples/word
bash charts.sh            # CLI
# or:
python3 charts.py         # Python SDK twin
# → charts.docx
```

## Charts

Each chart sits under a Heading2 paragraph naming its demo. Extended `cx:chart`
types (funnel, treemap, waterfall) are supported alongside the classic
DrawingML `c:chart` types.

### 1. Column — axis titles, scaling & gridlines

```bash
officecli add charts.docx /body/p[N] --type chart \
  --prop chartType=column \
  --prop 'data=East:120,135,148,162;West:110,118,130,145;South:95,108,115,128' \
  --prop categories="Q1,Q2,Q3,Q4" \
  --prop colors=4472C4,ED7D31,70AD47 \
  --prop catTitle=Quarter --prop axisTitle="Revenue (K)" \
  --prop axisMin=0 --prop axisMax=200 --prop axisNumFmt="#,##0" \
  --prop gridlines=D9D9D9:0.5:dot --prop legend=bottom \
  --prop width=16cm --prop height=9cm
```

**Features:** `chartType=column`, `data`, `categories`, `colors`, `catTitle`,
`axisTitle`, `axisMin`, `axisMax`, `axisNumFmt`, `gridlines`, `legend`,
`width`/`height`

### 2. Bar — gap width & data labels

```bash
officecli add charts.docx /body/p[N] --type chart \
  --prop chartType=bar \
  --prop 'data=Units:320,280,410,190,360' \
  --prop categories="Laptop,Phone,Tablet,Watch,Buds" \
  --prop gapwidth=80 \
  --prop dataLabels=value --prop labelPos=outsideEnd \
  --prop labelfont=9:333333:Calibri --prop legend=none
```

**Features:** `chartType=bar`, `gapwidth`, `dataLabels=value`, `labelPos`,
`labelfont` (size:color:name)

### 3. Line — markers, smoothing & drop lines

```bash
officecli add charts.docx /body/p[N] --type chart \
  --prop chartType=line \
  --prop 'data=2023:120,180,210,250,280,310;2024:150,220,260,300,340,380' \
  --prop categories="Jan,Feb,Mar,Apr,May,Jun" \
  --prop marker=circle:6 --prop smooth=true \
  --prop droplines=808080:0.5 --prop linewidth=2 --prop legend=bottom
```

**Features:** `chartType=line`, `marker` (symbol:size:color), `smooth`,
`droplines`, `linewidth`

### 4. Pie — percent labels & slice explosion

```bash
officecli add charts.docx /body/p[N] --type chart \
  --prop chartType=pie \
  --prop 'data=Share:42,28,18,12' \
  --prop categories="Alpha,Beta,Gamma,Other" \
  --prop dataLabels=percent --prop explosion=8 \
  --prop firstSliceAngle=90 --prop legend=right
```

**Features:** `chartType=pie`, `dataLabels=percent`, `explosion`,
`firstSliceAngle`, `colors`

### 5. Area — gradient fill (areafill)

`areafill` is a docx-specific shortcut: a solid color or gradient
(`c1-c2[:angle]`) applied to every series shape. Readback surfaces as `gradient`.

```bash
officecli add charts.docx /body/p[N] --type chart \
  --prop chartType=area \
  --prop 'data=Visits:20,35,30,55,48,70,65' \
  --prop categories="Mon,Tue,Wed,Thu,Fri,Sat,Sun" \
  --prop areafill=4472C4-A5C8FF:90 \
  --prop gridlines=E0E0E0:0.5:solid --prop legend=none
```

**Features:** `chartType=area`, `areafill` (gradient), `gridlines`

### 6. Scatter — smoothMarker style

```bash
officecli add charts.docx /body/p[N] --type chart \
  --prop chartType=scatter \
  --prop series1="Latency:12,18,27,41,60,88" \
  --prop categories="10,20,40,80,160,320" \
  --prop scatterstyle=smoothMarker --prop marker=diamond:7:C00000 \
  --prop catTitle="Concurrent Users" --prop axisTitle="ms"
```

**Features:** `chartType=scatter`, `scatterstyle`, `marker`, `catTitle`,
`axisTitle`

### 7. Radar — filled style (radarstyle)

`radarstyle` is a docx-specific shortcut for the radar subtype
(`standard`/`marker`/`filled`).

```bash
officecli add charts.docx /body/p[N] --type chart \
  --prop chartType=radar \
  --prop 'data=Model A:4,5,3,4,5;Model B:5,3,4,5,3' \
  --prop categories="Speed,Battery,Camera,Price,Display" \
  --prop radarstyle=filled --prop colors=4472C4,ED7D31 \
  --prop transparency=40 --prop legend=bottom
```

**Features:** `chartType=radar`, `radarstyle=filled`, `transparency`, `colors`

### 8. Doughnut — hole size & percent labels

```bash
officecli add charts.docx /body/p[N] --type chart \
  --prop chartType=doughnut \
  --prop 'data=Budget:35,25,20,20' \
  --prop categories="R&D,Sales,Ops,Admin" \
  --prop holeSize=55 --prop dataLabels=percent --prop legend=right
```

**Features:** `chartType=doughnut`, `holeSize`, `dataLabels=percent`, `colors`

### 9. Stock — high / low / close series

The three ordered series map to High, Low, Close. `hilowlines` connects the
high/low extremes.

```bash
officecli add charts.docx /body/p[N] --type chart \
  --prop chartType=stock \
  --prop series1="High:32,35,34,38,37" \
  --prop series2="Low:28,29,30,32,33" \
  --prop series3="Close:30,34,31,37,35" \
  --prop categories="Mon,Tue,Wed,Thu,Fri" --prop hilowlines=true
```

**Features:** `chartType=stock`, ordered series, `hilowlines`

### 10. Combo — column + line on secondary axis

```bash
officecli add charts.docx /body/p[N] --type chart \
  --prop chartType=combo \
  --prop series1="Revenue:120,180,250,310,380" \
  --prop series2="Growth %:50,33,39,24,23" \
  --prop categories="2021,2022,2023,2024,2025" \
  --prop combotypes="column,line" --prop secondaryaxis=2 \
  --prop colors=2E75B6,C00000
```

**Features:** `chartType=combo`, `combotypes` (one type per series),
`secondaryaxis`

### 11. Column — display units & rounded corners

```bash
officecli add charts.docx /body/p[N] --type chart \
  --prop chartType=column \
  --prop 'data=Revenue:12000,18500,22000,31000,45000' \
  --prop categories="2021,2022,2023,2024,2025" \
  --prop dispUnits=thousands --prop axisNumFmt="#,##0" \
  --prop roundedcorners=true --prop chartFill=F8F8F8 \
  --prop title.font=Georgia --prop title.size=15 \
  --prop title.color=1F4E79 --prop title.bold=true
```

**Features:** `dispUnits`, `roundedcorners`, `chartFill`, `title.font`/`.size`/
`.color`/`.bold`

### 12. Funnel — extended (cx) chart

```bash
officecli add charts.docx /body/p[N] --type chart \
  --prop chartType=funnel \
  --prop 'data=Stage:1000,720,430,210,95' \
  --prop categories="Visitors,Leads,MQL,SQL,Won"
```

**Features:** `chartType=funnel` (extended `cx:chart`)

### 13. Treemap — extended (cx) chart

```bash
officecli add charts.docx /body/p[N] --type chart \
  --prop chartType=treemap \
  --prop 'data=Size:420,310,180,90,45' \
  --prop categories="Video,Images,Docs,Audio,Other"
```

**Features:** `chartType=treemap` (extended `cx:chart`)

### 14. Waterfall — increase / decrease / total colors

```bash
officecli add charts.docx /body/p[N] --type chart \
  --prop chartType=waterfall \
  --prop 'data=Cash:100,-30,50,-20,80' \
  --prop categories="Start,Q1,Q2,Q3,End" \
  --prop increaseColor=00AA00 --prop decreaseColor=C00000 --prop totalColor=4472C4
```

**Features:** `chartType=waterfall` (extended `cx:chart`), `increaseColor`,
`decreaseColor`, `totalColor` (all add-time only)

## Complete Feature Coverage

| Feature | Chart |
|---------|-------|
| **Classic types:** column, bar, line, pie, area, scatter, radar, doughnut, stock, combo | 1–10 |
| **Extended (cx) types:** funnel, treemap, waterfall | 12–14 |
| **Data input:** `data` (shorthand), `series{N}`, `categories` | all |
| **Colors:** `colors`, `areafill` (gradient) | 1–8, 5 |
| **Axis scaling:** `axisMin`, `axisMax`, `axisNumFmt`, `dispUnits` | 1, 11 |
| **Axis titles:** `catTitle`, `axisTitle` | 1, 6 |
| **Gridlines:** `gridlines` (styled) | 1, 5 |
| **Data labels:** `dataLabels` (value/percent), `labelPos`, `labelfont` | 2, 4, 8 |
| **Legend:** position (`bottom`/`right`/`none`) | all |
| **Line/scatter:** `marker`, `smooth`, `droplines`, `linewidth`, `scatterstyle` | 3, 6 |
| **Pie/doughnut:** `explosion`, `firstSliceAngle`, `holeSize` | 4, 8 |
| **Radar:** `radarstyle=filled` | 7 |
| **Stock:** ordered High/Low/Close series, `hilowlines` | 9 |
| **Combo:** `combotypes`, `secondaryaxis` | 10 |
| **Fills & effects:** `chartFill`, `transparency`, `roundedcorners` | 7, 11 |
| **Title styling:** `title.font`/`.size`/`.color`/`.bold` | 11 |
| **Bar geometry:** `gapwidth` | 2 |
| **Waterfall colors:** `increaseColor`, `decreaseColor`, `totalColor` | 14 |
| **Sizing:** `width`, `height` (cm/in/pt/EMU) | all |

## Inspect the Generated File

```bash
officecli query charts.docx chart              # list all 14 charts
officecli get   charts.docx '/chart[1]'        # full column chart props
officecli get   charts.docx '/chart[5]'        # area chart — areafill → gradient
officecli get   charts.docx '/chart[14]'       # waterfall — increase/decrease/total colors
```
