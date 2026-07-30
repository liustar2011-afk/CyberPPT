# Slicer Showcase

This demo consists of three files that work together:

- **slicers.sh** — Shell script that calls `officecli` commands to generate the workbook. Read this to learn the exact `officecli add --type slicer --prop ...` syntax.
- **slicers.py** — Python twin that drives the officecli SDK to produce an equivalent `slicers.xlsx`. Each `add`/`set` is shown as a copyable shell command in the comments, then shipped over the named pipe.
- **slicers.xlsx** — The generated workbook: a `Sheet1` source table and a `Dashboard` sheet holding one PivotTable with three slicers. Open in Excel to interact with the slicer buttons. Use `officecli get` or `officecli query` to inspect programmatically.
- **slicers.md** — This file. Explains how slicers bind to their source and maps each slicer to the feature it demonstrates.

## Regenerate

```bash
cd examples/excel
bash slicers.sh          # CLI twin
# or
python3 slicers.py       # SDK twin
# → slicers.xlsx
```

## How slicers bind to a source

A slicer is the interactive button panel that filters a PivotTable. In OOXML a
slicer is **not free-standing** — it is anchored to a *pivot cache field* and
therefore always requires an existing PivotTable as its source. The binding is
expressed with two add-time props:

- `pivotTable=` — the source pivot. Accepts a full path (`/Dashboard/pivottable[1]`)
  or a **bare name** (`SalesPivot`) that resolves against the host sheet's pivots.
- `field=` — the pivot cache field to slice on (e.g. `Region`). Must match an
  existing cacheField name (case-insensitive). This is add-time only: `set`
  intentionally ignores `field=` because a slicer is anchored to its cache field
  at creation.

So the build order is always: **source data → PivotTable → slicers**. This demo
builds a `Sheet1` sales table, a `SalesPivot` PivotTable on the `Dashboard`
sheet, then three slicers on that pivot's `Region`, `Product`, and `Quarter`
fields.

## Source Data

| Sheet | Rows | Columns | Purpose |
|-------|------|---------|---------|
| Sheet1 | 12 | Region, Product, Quarter, Sales | Sales data feeding the pivot cache |
| Dashboard | — | — | Hosts the SalesPivot PivotTable + 3 slicers |

## The PivotTable (slicer source)

```bash
officecli add slicers.xlsx /Dashboard --type pivottable \
  --prop source=Sheet1!A1:D13 \
  --prop rows=Region \
  --prop cols=Quarter \
  --prop values=Sales:sum \
  --prop layout=outline \
  --prop grandtotals=both \
  --prop name=SalesPivot \
  --prop style=PivotStyleMedium9
```

Named `SalesPivot` so the slicers can reference it by bare name.

## Slicers

### Slicer 1: Region

```bash
officecli add slicers.xlsx /Dashboard --type slicer \
  --prop pivotTable=/Dashboard/pivottable[1] \
  --prop field=Region \
  --prop caption='Filter by Region' \
  --prop columnCount=2 \
  --prop rowHeight=250000 \
  --prop name=RegionSlicer
```

**Features:** `pivotTable=` (full path reference), `field=Region`, custom `caption`, `columnCount=2` (two-column button grid), `rowHeight=250000` (EMU, ~19.7pt), explicit `name`.

### Slicer 2: Product

```bash
officecli add slicers.xlsx /Dashboard --type slicer \
  --prop pivotTable=SalesPivot \
  --prop field=Product \
  --prop caption='Filter by Product' \
  --prop columnCount=3 \
  --prop name=ProductSlicer
```

**Features:** `pivotTable=SalesPivot` — resolves the source by **bare name** against the host sheet's pivots; `columnCount=3` (wide grid).

### Slicer 3: Quarter

```bash
officecli add slicers.xlsx /Dashboard --type slicer \
  --prop pivotTable=SalesPivot \
  --prop field=Quarter \
  --prop columnCount=1 \
  --prop name=QuarterSlicer
```

**Features:** `caption` omitted — defaults to the field name (`Quarter`); `rowHeight` omitted — defaults to `225425` EMU (~17.5pt). A minimal single-column slicer.

### Modifying a slicer

`caption` and `columnCount` are settable after creation; `field` is add-time only.

```bash
officecli set slicers.xlsx /Dashboard/slicer[1] \
  --prop caption=Region --prop columnCount=1
```

## Property reference

| Property | Ops | Notes |
|----------|-----|-------|
| `pivotTable` | add/set/get | Source pivot. Full path or bare name. Aliases: `pivot`, `source`, `tableName`. |
| `field` | add/get | Pivot cache field to slice on. Add-time only (Set ignores). Alias: `column`. |
| `caption` | add/set/get | Header caption. Defaults to the field name. |
| `name` | add/set/get | Slicer name. Sanitized; defaults to `Slicer_<field>`. |
| `columnCount` | add/set/get | Button-grid columns. Range 1..20000. |
| `rowHeight` | add/set/get | Item row height in EMU. Default 225425 (~17.5pt). |
| `cache` | get | Slicer cache name (read-only). |
| `pivotCacheId` | get | Extension pivot cache id (read-only, auto-assigned). |
| `itemCount` | get | Number of items/buttons, derived from the pivot's shared items (read-only). |

> **Note on `position`:** unlike some Excel elements, the slicer element does not
> accept a `position=` anchor prop — the drawing anchor is auto-placed. Passing
> `position=` reports an `unsupported_property` warning and is ignored.

## Inspect

```bash
# List every slicer in the workbook
officecli query slicers.xlsx slicer

# Inspect one slicer (field / caption / columnCount / rowHeight round-trip)
officecli get slicers.xlsx '/Dashboard/slicer[1]'

# Validate the workbook (slicer + pivot XML is strictly checked)
officecli validate slicers.xlsx
```
