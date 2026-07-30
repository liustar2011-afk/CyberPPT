# Data Validation Showcase

Exercises the full xlsx `validation` (dataValidation) feature surface — the
input-restriction rules Excel enforces on cell entry. Three files work together:

- **data-validation.py** — builds the workbook via the **officecli Python SDK**.
- **data-validation.sh** — the CLI twin (`officecli add … --type validation`).
- **data-validation.xlsx** — the generated 6-sheet workbook.
- **data-validation.md** — this file.

## Built on the SDK (not subprocess)

Unlike the sibling `*.py` examples (which `subprocess.run("officecli …")` once
per command), the Python twin drives the [`officecli-sdk`](../../sdk/python)
client. One resident process is started; every validation is shipped over the
named pipe; all the validations for a sheet go in a single `doc.batch(...)`
round-trip:

```python
import officecli                      # pip install officecli-sdk

with officecli.create(FILE, "--force") as doc:
    doc.batch([
        {"command": "set", "path": "/Sheet1/A2", "props": {"value": "Draft"}},
        {"command": "add", "parent": "/Sheet1", "type": "validation",
         "props": {"type": "list", "ref": "A2:A20",
                   "formula1": "Draft,Review,Approved,Rejected"}},
    ])
```

The dict shape is identical to an `officecli batch` list item — `command`,
`path`/`parent`/`type`, and `props`. The script falls back to the in-repo SDK
copy if `officecli-sdk` isn't pip-installed, so it runs straight from a checkout.

## Regenerate

```bash
cd examples/excel
bash data-validation.sh            # CLI twin → data-validation.xlsx
# or:
pip install officecli-sdk          # plus the `officecli` binary on PATH
python3 data-validation.py         # SDK twin → equivalent data-validation.xlsx
```

## A data-validation rule

Every rule is one `add --type validation` against the sheet, with `type=`
selecting the rule kind and `ref=` (alias `sqref`) the target range:

```bash
officecli add file.xlsx /Sheet1 --type validation \
  --prop type=whole --prop ref=A2:A50 --prop operator=between \
  --prop formula1=1 --prop formula2=100
```

The rule lands at `/SheetName/dataValidation[N]`; `get`/`set`/`remove` address
it there (the alias `/SheetName/validation[N]` is also accepted). `type`
determines which of `formula1`/`formula2` are used — comparison rules use
`operator` plus one bound (`formula1`) or two (`between`/`notBetween` use both).

## Sheets

### Sheet1 — List (inline + range)

`type=list`. The allowed values are `formula1`: either an **inline CSV**
(`Draft,Review,Approved,Rejected`) or a **range reference** (`=$H$2:$H$5`)
pointing at a helper column. `inCellDropdown=true` (default) shows the dropdown
arrow; `inCellDropdown=false` hides it (the list still validates on typed input).

```bash
officecli add file.xlsx /Sheet1 --type validation --prop type=list --prop ref=A2:A20 --prop formula1="Draft,Review,Approved,Rejected"
officecli add file.xlsx /Sheet1 --type validation --prop type=list --prop sqref=B2:B20 --prop formula1==$H$2:$H$5 --prop inCellDropdown=false
```

### Sheet2 — Number (whole / decimal)

`type=whole` (integers) or `type=decimal` (any number), with `operator` ∈
`between`, `notBetween`, `equal`, `notEqual`, `greaterThan`,
`greaterThanOrEqual`, `lessThan`, `lessThanOrEqual`. `between`/`notBetween` use
both `formula1` (low) and `formula2` (high); the others use `formula1` only.

```bash
officecli add file.xlsx /Number --type validation --prop type=whole --prop ref=A2:A50 --prop operator=between --prop formula1=1 --prop formula2=100
officecli add file.xlsx /Number --type validation --prop type=decimal --prop ref=B2:B50 --prop operator=lessThanOrEqual --prop formula1=0.5
officecli add file.xlsx /Number --type validation --prop type=whole --prop ref=E2:E50 --prop operator=notEqual --prop formula1=13
```

### Sheet3 — Date & Time

`type=date` / `type=time`, same operator set. Dates accept ISO input
(`2024-01-01`) and are stored as Excel **serial numbers** on readback
(`2024-01-01` → `45292`); times are stored as **day fractions**
(`09:00:00` → `0.375`).

```bash
officecli add file.xlsx /DateTime --type validation --prop type=date --prop ref=A2:A50 --prop operator=between --prop formula1=2024-01-01 --prop formula2=2024-12-31
officecli add file.xlsx /DateTime --type validation --prop type=time --prop ref=B2:B50 --prop operator=between --prop formula1=09:00:00 --prop formula2=17:00:00
officecli add file.xlsx /DateTime --type validation --prop type=date --prop ref=C2:C50 --prop operator=equal --prop formula1=2024-12-31
```

### Sheet4 — Text length

`type=textLength`, same operator set — `formula1`/`formula2` are character
counts. Handy for bounded (`between 3–16`), exact (`equal 2`), capped
(`lessThanOrEqual 280`), or excluded-band (`notBetween 5–7`) lengths.

```bash
officecli add file.xlsx /TextLength --type validation --prop type=textLength --prop ref=A2:A50 --prop operator=between --prop formula1=3 --prop formula2=16
officecli add file.xlsx /TextLength --type validation --prop type=textLength --prop ref=C2:C50 --prop operator=lessThanOrEqual --prop formula1=280
```

### Sheet5 — Custom formula

`type=custom`. `formula1` is any boolean expression (relative to the top-left
cell of `ref`); the entry is valid when it evaluates `TRUE`. No `operator`.

```bash
officecli add file.xlsx /Custom --type validation --prop type=custom --prop ref=A2:A50 --prop formula1="ISNUMBER(A2)"
officecli add file.xlsx /Custom --type validation --prop type=custom --prop ref=B2:B50 --prop formula1="MOD(B2,2)=0"
```

### Sheet6 — Messages (prompt / error / errorStyle)

Any validation can carry an **input prompt** (`promptTitle` + `prompt`, gated by
`showInput`) shown when the cell is selected, and an **error alert**
(`errorTitle` + `error`, gated by `showError`) shown on invalid input. The alert
severity is `errorStyle`:

- `stop` (default) — hard block; the entry is rejected.
- `warning` — soft block; the user may override.
- `information` — advisory only; never blocks.

`allowBlank=false` makes empty cells themselves invalid (default `true`).

```bash
officecli add file.xlsx /Messages --type validation --prop type=whole --prop ref=A2:A50 --prop operator=between --prop formula1=18 --prop formula2=120 \
  --prop promptTitle="Enter age" --prop prompt="Age must be 18-120" \
  --prop errorTitle="Invalid age" --prop error="Please enter a whole number 18-120" --prop errorStyle=stop
officecli add file.xlsx /Messages --type validation --prop type=decimal --prop ref=B2:B50 --prop operator=lessThanOrEqual --prop formula1=10000 --prop errorStyle=warning ...
officecli add file.xlsx /Messages --type validation --prop type=whole --prop ref=D2:D50 --prop operator=greaterThan --prop formula1=0 --prop allowBlank=false --prop showInput=false
```

## Complete feature coverage

| Family | `type=` | Key props | Sheet |
|---|---|---|---|
| List (inline) | `list` | `formula1` (CSV), `inCellDropdown` | Sheet1 |
| List (range) | `list` | `formula1` (`=$H$2:$H$5`), `sqref`, `inCellDropdown=false` | Sheet1 |
| Whole number | `whole` | `operator`, `formula1`, `formula2` | Number |
| Decimal | `decimal` | `operator`, `formula1`, `formula2` | Number |
| Date | `date` | `operator`, `formula1`, `formula2` (ISO → serial) | DateTime |
| Time | `time` | `operator`, `formula1`, `formula2` (→ day fraction) | DateTime |
| Text length | `textLength` | `operator`, `formula1`, `formula2` | TextLength |
| Custom | `custom` | `formula1` (boolean expr) | Custom |
| Input prompt | any | `promptTitle`, `prompt`, `showInput` | Messages |
| Error alert | any | `errorTitle`, `error`, `showError`, `errorStyle` | Messages |
| Blank policy | any | `allowBlank` | Messages |

Operators covered: `between`, `notBetween`, `equal`, `notEqual`,
`greaterThan`, `greaterThanOrEqual`, `lessThan`, `lessThanOrEqual`.
`errorStyle` covered: `stop`, `warning`, `information`.

Full property list: `officecli help xlsx validation` (or
`schemas/help/xlsx/validation.json`).

## Read a validation back

```bash
officecli query data-validation.xlsx validation
officecli get data-validation.xlsx "/Sheet1/dataValidation[1]" --json
```

`get` normalizes on read: `type`/`operator` come back as canonical tokens,
dates/times as serials/fractions, and default flags (`showInput=true`,
`showError=true`, `allowBlank=true`) are implied — only non-default flags
(e.g. `inCellDropdown=false`, `allowBlank=false`, `errorStyle=warning`) surface
explicitly.

## Validating

Validations live in each sheet's `<dataValidations>` block, so validate the
saved file:

```bash
officecli validate data-validation.xlsx
```
