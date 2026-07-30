# Content Controls Showcase

Exercises the docx `sdt` property surface — **structured document tags**, better
known as **content controls**: bounded regions Word treats as fillable form
fields. Three files work together:

- **content-controls.py** — builds the doc via the **officecli Python SDK**.
- **content-controls.sh** — the CLI twin (produces the shipped `.docx`).
- **content-controls.docx** — the generated document, a small employee-intake form.
- **content-controls.md** — this file.

## The `sdt` element

An `sdt` is added under `/body` (block-level, wrapping paragraphs) and reads
back at the stable path `/body/sdt[@sdtId=N]` (positional `/body/sdt[N]` also
works):

```bash
officecli add file.docx /body --type sdt --prop type=text --prop alias="Full Name"
officecli query file.docx sdt          # list every control with its props
officecli get   file.docx /body/sdt[1] # read one control's property bag
```

The control **type cannot be changed after creation**.
`text`/`richtext`/`dropdown`/`combobox`/`date`/`picture`/`group`/`checkbox` can
all be created at add-time. (`buildingBlockGallery`/`repeatingSection` still
require creating the control in Word first, then editing via the CLI.)

Built on the [`officecli-sdk`](../../sdk/python) (one resident, writes shipped
over the pipe); falls back to the in-repo SDK copy when the package isn't
pip-installed.

## Regenerate

```bash
cd examples/word
pip install officecli-sdk
python3 content-controls.py        # or: bash content-controls.sh
# → content-controls.docx
```

## Control types demonstrated

| # | Type | Purpose | Type-specific props |
|---|---|---|---|
| 1 | `text` (plainText) | Single-line text field | `text=` initial/placeholder content |
| 2 | `dropdown` | Pick-one, typing disabled | `items=`, `dropDown.lastValue=` |
| 3 | `combobox` | Pick-one **or** free type | `items=` (`display\|value`), `comboBox.lastValue=` |
| 4 | `date` | Calendar picker | `format=`, `date.fullDate/calendar/lid/storeMappedDataAs=` |
| 5 | `picture` | Image-insert placeholder | — |
| 6 | `richtext` | Formatted multi-run field | `text=` |
| 7 | `group` | Locked grouping wrapper | — |
| 8 | `checkbox` | Check-box toggle (☒/☐) | `checked=` (`true`/`false`) |

## Shared props (every control type)

```bash
officecli add file.docx /body --type sdt --prop type=text \
  --prop alias="Full Name" \          # human-readable label shown in Word
  --prop tag=fullName \               # machine-readable data-binding key
  --prop text="[Enter full legal name]" \  # initial / placeholder content
  --prop lock=unlocked \              # unlocked | contentLocked | sdtLocked | sdtContentLocked
  --prop placeholderText=DefaultPlaceholder  # docPart gallery reference
```

`lock` semantics: `contentLocked` freezes the content (readback `editable=false`),
`sdtLocked` blocks deletion of the control, `sdtContentLocked` does both.
`placeholder=true` marks the control as currently *showing* its placeholder text
(`<w:showingPlcHdr/>`).

## Per-type props

### 2 + 3. dropDown / comboBox — choice lists

```bash
# dropDown: choices only, no free typing
officecli add file.docx /body --type sdt --prop type=dropdown \
  --prop alias="Department" --prop tag=department \
  --prop items="Sales,Engineering,Human Resources,Finance,Operations" \
  --prop dropDown.lastValue=Engineering

# comboBox: same, but the user may also type a value not in the list.
# items= supports display|value form when the stored value differs from the label.
officecli add file.docx /body --type sdt --prop type=combobox \
  --prop alias="Office Location" --prop tag=office \
  --prop items="New York|NYC,London|LON,Singapore|SIN,Remote|REMOTE" \
  --prop comboBox.lastValue=LON
```

`items=` is a comma list; each entry is either `display` or `display|value`.
`{dropDown,comboBox}.lastValue=` is the currently-selected stored value.

### 4. date — calendar picker

```bash
officecli add file.docx /body --type sdt --prop type=date \
  --prop alias="Start Date" --prop tag=startDate \
  --prop format="yyyy-MM-dd" \
  --prop date.fullDate=2026-02-01T00:00:00Z \
  --prop date.calendar=gregorian --prop date.lid=en-US \
  --prop date.storeMappedDataAs=dateTime
```

`format=` is the display mask; `date.fullDate` is the actual selected value
(ISO-8601 UTC), distinct from the mask. `date.calendar` (e.g. `gregorian`,
`hijri`, `japan`), `date.lid` (locale id), and `date.storeMappedDataAs`
(`dateTime`/`date`/`text`) round out the picker.

### 5. picture — image placeholder

```bash
officecli add file.docx /body --type sdt --prop type=picture \
  --prop alias="Profile Photo" --prop tag=photo
```

### 6. richText — formatted field

```bash
officecli add file.docx /body --type sdt --prop type=richtext \
  --prop alias="Reviewer Notes" --prop tag=notes \
  --prop text="Manager may add formatted commentary here." \
  --prop lock=contentLocked
```

### 7. group — locked wrapper

```bash
officecli add file.docx /body --type sdt --prop type=group \
  --prop alias="Approval Block" --prop tag=approval \
  --prop text="Approved by HR — signature on file." \
  --prop lock=sdtContentLocked
```

### 8. checkbox — check-box toggle

A real Word check-box content control. `checked=true` renders ☒ (2612),
`checked=false` renders ☐ (2610); the state is stored as a `<w14:checkbox>`
marker in the control's `sdtPr`. `get` reads `type=checkbox` and `checked`.

```bash
officecli add file.docx /body --type sdt --prop type=checkbox \
  --prop alias="Approved" --prop tag=hrApproved \
  --prop checked=true
```

## Modifying after creation (`set`)

`alias`, `tag`, `lock`, and `text` are settable. The **per-type** props
(`dropDown.lastValue`, `comboBox.lastValue`, `items`, `format`, `date.*`,
`placeholderText`) are **add/get-only** — set at creation, read back on `get`,
but not modifiable via `set`.

```bash
officecli set file.docx /body/sdt[2] --prop alias="Home Department" --prop lock=sdtLocked
```

## Inspect

```bash
officecli query content-controls.docx sdt      # one line per control
officecli get   content-controls.docx /body/sdt[1]
```

```
/body/sdt[@sdtId=1] (sdt) "[Enter full legal name]" alias=Full Name tag=fullName lock=unlocked type=text editable=true placeholderText=DefaultPlaceholder
/body/sdt[@sdtId=2] (sdt) "" alias=Home Department tag=department lock=sdtLocked type=dropdown items=Sales,Engineering,Human Resources,Finance,Operations dropDown.lastValue=Engineering
/body/sdt[@sdtId=4] (sdt) "" alias=Start Date tag=startDate type=date format=yyyy-MM-dd date.fullDate=2026-02-01T00:00:00Z date.calendar=gregorian date.lid=en-US date.storeMappedDataAs=dateTime
/body/sdt[@sdtId=6] (sdt) "Manager may add formatted commentary here." alias=Reviewer Notes tag=notes lock=contentLocked type=richtext editable=false
```

Read-only readback keys: `id` (source of `@sdtId`) and `editable` (mirrors
`lock`). Full list: `officecli help docx sdt`.
