#!/usr/bin/env python3
"""
Content Controls Showcase — generates content-controls.docx exercising the docx
`sdt` (structured document tag / content control) property surface
(schemas/help/docx/sdt.json).

An `sdt` is a content control: a bounded region Word treats as a single form
field. Block-level SDTs (added at /body) wrap paragraphs. Every control shares
alias / tag / lock / placeholder; each variant then adds its own props:

  text      — plain-text field            (text=)
  richText  — rich formatted field        (text=, lock=contentLocked)
  dropDown  — pick-one, typing disabled    (items=, dropDown.lastValue=)
  comboBox  — pick-one OR free type        (items= display|value, comboBox.lastValue=)
  date      — date picker                  (format=, date.fullDate/calendar/lid/storeMappedDataAs=)
  picture   — image placeholder            (type=picture)
  group     — locked grouping wrapper       (type=group, lock=sdtContentLocked)
  checkbox  — check-box toggle              (type=checkbox, checked=)

The document models a small employee-intake form.

Like examples/word/document-formatting.py, this drives the officecli Python SDK
(`pip install officecli-sdk`): one resident, writes shipped over the pipe.

Usage:
  python3 content-controls.py
"""

import os
import sys
import subprocess

try:
    import officecli  # pip install officecli-sdk
except ImportError:
    sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                    "..", "..", "sdk", "python"))
    import officecli

FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "content-controls.docx")


def para(text, **props):
    return {"command": "add", "parent": "/body", "type": "paragraph",
            "props": {"text": text, **props}}


def sdt(**props):
    return {"command": "add", "parent": "/body", "type": "sdt", "props": props}


print("\n==========================================")
print(f"Generating content-controls showcase: {FILE}")
print("==========================================")

with officecli.create(FILE, "--force") as doc:

    # ----------------------------------------------------------------------
    # Title + intro
    # ----------------------------------------------------------------------
    print("\n--- Title + intro ---")
    doc.batch([
        para("Employee Intake Form", style="Title"),
        para("Complete every field. Grey boxes are content controls — click one "
             "and Word treats it as a single fillable region.", style="Subtitle"),
    ])

    # ----------------------------------------------------------------------
    # 1. plainText — the employee's full name
    #    alias (Word label) / tag (data key) / text (initial content) / lock /
    #    placeholderText (docPart gallery reference).
    # ----------------------------------------------------------------------
    print("--- plainText: Full Name ---")
    doc.batch([
        para("Full name", style="Heading2"),
        sdt(type="text", alias="Full Name", tag="fullName",
            text="[Enter full legal name]",
            lock="unlocked", placeholderText="DefaultPlaceholder"),
    ])

    # ----------------------------------------------------------------------
    # 2. dropDown — department (pick-one, typing disabled)
    #    items= comma list, dropDown.lastValue= the current pick.
    # ----------------------------------------------------------------------
    print("--- dropDown: Department ---")
    doc.batch([
        para("Department", style="Heading2"),
        sdt(type="dropdown", alias="Department", tag="department",
            items="Sales,Engineering,Human Resources,Finance,Operations",
            **{"dropDown.lastValue": "Engineering"}),
    ])

    # ----------------------------------------------------------------------
    # 3. comboBox — office location (pick-one OR free-type)
    #    items= uses display|value form; comboBox.lastValue= the stored value.
    # ----------------------------------------------------------------------
    print("--- comboBox: Office Location ---")
    doc.batch([
        para("Primary office", style="Heading2"),
        sdt(type="combobox", alias="Office Location", tag="office",
            items="New York|NYC,London|LON,Singapore|SIN,Remote|REMOTE",
            **{"comboBox.lastValue": "LON"}),
    ])

    # ----------------------------------------------------------------------
    # 4. date — start date (calendar picker)
    #    format= display mask; date.fullDate ISO value; calendar / lid / mapping.
    # ----------------------------------------------------------------------
    print("--- date: Start Date ---")
    doc.batch([
        para("Start date", style="Heading2"),
        sdt(type="date", alias="Start Date", tag="startDate",
            format="yyyy-MM-dd",
            **{"date.fullDate": "2026-02-01T00:00:00Z",
               "date.calendar": "gregorian",
               "date.lid": "en-US",
               "date.storeMappedDataAs": "dateTime"}),
    ])

    # ----------------------------------------------------------------------
    # 5. picture — profile photo placeholder
    # ----------------------------------------------------------------------
    print("--- picture: Profile Photo ---")
    doc.batch([
        para("Profile photo", style="Heading2"),
        sdt(type="picture", alias="Profile Photo", tag="photo"),
    ])

    # ----------------------------------------------------------------------
    # 6. richText — reviewer notes (formatted, multi-run field)
    #    lock=contentLocked freezes the content (editable=false on readback).
    # ----------------------------------------------------------------------
    print("--- richText: Reviewer Notes ---")
    doc.batch([
        para("Reviewer notes", style="Heading2"),
        sdt(type="richtext", alias="Reviewer Notes", tag="notes",
            text="Manager may add formatted commentary here.",
            lock="contentLocked"),
    ])

    # ----------------------------------------------------------------------
    # 7. group — a locked wrapper around an approval line
    #    sdtContentLocked blocks both deletion and content edits.
    # ----------------------------------------------------------------------
    print("--- group: Approval Block ---")
    doc.batch([
        para("Approval", style="Heading2"),
        sdt(type="group", alias="Approval Block", tag="approval",
            text="Approved by HR — signature on file.",
            lock="sdtContentLocked"),
    ])

    # ----------------------------------------------------------------------
    # 8. checkbox — the HR approval toggle (real Word check-box control).
    #    checked=true → ☒ (2612) / false → ☐ (2610). Emits <w14:checkbox>.
    # ----------------------------------------------------------------------
    print("--- checkbox: HR approved ---")
    doc.batch([
        para("HR approved", style="Heading2"),
        sdt(type="checkbox", alias="Approved", tag="hrApproved",
            checked="true"),
    ])

    # ----------------------------------------------------------------------
    # Post-add tweak via `set` — alias / tag / lock / text are settable.
    # (Per-type props like dropDown.lastValue are add/get-only, not settable.)
    # ----------------------------------------------------------------------
    print("--- set: rename + lock the department control ---")
    doc.send({"command": "set", "path": "/body/sdt[2]",
              "props": {"alias": "Home Department", "lock": "sdtLocked"}})

    doc.send({"command": "save"})

    # ----------------------------------------------------------------------
    # Get round-trip: confirm each control's canonical props read back
    # ----------------------------------------------------------------------
    print("\n--- Round-trip readback (query sdt) ---")
    for i in range(1, 9):
        node = doc.send({"command": "get", "path": f"/body/sdt[{i}]"})
        fmt = node.get("data", {}).get("results", [{}])[0].get("format", {})
        checked = f" checked={fmt['checked']}" if "checked" in fmt else ""
        print(f"  sdt[{i}] type={fmt.get('type')} alias={fmt.get('alias')!r} "
              f"tag={fmt.get('tag')} lock={fmt.get('lock', 'unlocked')}{checked}")

print("\n--- Validate (fresh process, from disk) ---")
r = subprocess.run(["officecli", "validate", FILE], capture_output=True, text=True)
print(" ", (r.stdout or r.stderr).strip().split("\n")[0])

print(f"\nCreated: {FILE}")
