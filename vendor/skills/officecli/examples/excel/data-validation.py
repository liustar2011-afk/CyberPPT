#!/usr/bin/env python3
"""
Data Validation Showcase — generates data-validation.xlsx exercising the full
xlsx `validation` (dataValidation) feature surface
(schemas/help/xlsx/validation.json).

Unlike the other excel/*.py (which shell out per command), this one drives the
**officecli Python SDK** (`pip install officecli-sdk`): one resident is started,
every write goes over the named pipe, and all the validations for a sheet are
applied in a single `doc.batch(...)` round-trip. Same `{"command","parent",
"type","props"}` dict shape you'd put in an `officecli batch` list.

6 sheets, one validation family each:
  Sheet1     — list: inline CSV list AND range-based list (=$H$2:$H$5), inCellDropdown
  Number     — whole/decimal with between/notEqual/greaterThan/lessThanOrEqual/…
  DateTime   — date range, time window, exact-equal date, on/after date
  TextLength — bounded / exact / capped / notBetween length rules
  Custom     — arbitrary boolean formula1 expressions
  Messages   — prompt + promptTitle + showInput, error + errorTitle + showError,
               all three errorStyles (stop / warning / information), allowBlank

Closes with a Get round-trip proving the canonical keys read back.

Usage:
  pip install officecli-sdk          # plus the `officecli` binary on PATH
  python3 data-validation.py
"""

import os
import sys
import subprocess

# --- locate the SDK: prefer an installed `officecli-sdk`, else the in-repo copy
try:
    import officecli  # pip install officecli-sdk
except ImportError:
    sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                    "..", "..", "sdk", "python"))
    import officecli

FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data-validation.xlsx")


def hdr(sheet, ref, text):
    """Bold blue-on-white header cell."""
    return {"command": "set", "path": f"/{sheet}/{ref}",
            "props": {"value": text, "font.bold": "true", "fill": "1F4E79", "font.color": "FFFFFF"}}


def col(sheet, letter, start_row, values):
    """Write `values` down a column from {letter}{start_row}."""
    return [{"command": "set", "path": f"/{sheet}/{letter}{i}", "props": {"value": str(v)}}
            for i, v in enumerate(values, start=start_row)]


def dv(sheet, **props):
    """One `add validation` item in batch-shape."""
    return {"command": "add", "parent": f"/{sheet}", "type": "validation", "props": props}


def add_sheet(name):
    return {"command": "add", "parent": "/", "type": "sheet", "props": {"name": name}}


print("\n==========================================")
print(f"Generating data-validation showcase: {FILE}")
print("==========================================")

with officecli.create(FILE, "--force") as doc:

    # ======================================================================
    # Sheet1: List — inline CSV list AND range-based list (helper column)
    # ======================================================================
    print("\n--- Sheet1: List (inline + range) ---")
    items = [
        hdr("Sheet1", "A1", "Status (inline)"),
        hdr("Sheet1", "B1", "Priority (range)"),
        hdr("Sheet1", "H1", "Priorities"),
    ]
    items += col("Sheet1", "H", 2, ["Low", "Medium", "High", "Critical"])  # the range B points at
    items += [
        # inline CSV list; dropdown arrow shown (inCellDropdown default true)
        dv("Sheet1", type="list", ref="A2:A20", formula1="Draft,Review,Approved,Rejected"),
        # range-based list via sqref alias; hide the dropdown arrow
        dv("Sheet1", type="list", sqref="B2:B20", formula1="=$H$2:$H$5", inCellDropdown="false"),
    ]
    doc.batch(items)

    # ======================================================================
    # Sheet2: Number — whole & decimal, every comparison operator
    # ======================================================================
    print("--- Sheet2: Number (whole/decimal) ---")
    items = [add_sheet("Number"),
             hdr("Number", "A1", "Qty (whole)"), hdr("Number", "B1", "Discount (decimal)"),
             hdr("Number", "C1", "Rating (1-5)"), hdr("Number", "D1", "Price (>0)"),
             hdr("Number", "E1", "Not 13")]
    items += col("Number", "A", 2, [1, 5, 10, 20])
    items += col("Number", "B", 2, [0.05, 0.10, 0.25])
    items += col("Number", "C", 2, [1, 3, 5])
    items += col("Number", "D", 2, [9.99, 19.5])
    items += col("Number", "E", 2, [12, 14])
    items += [
        dv("Number", type="whole", ref="A2:A50", operator="between", formula1="1", formula2="100"),
        dv("Number", type="decimal", ref="B2:B50", operator="lessThanOrEqual", formula1="0.5"),
        dv("Number", type="whole", ref="C2:C50", operator="greaterThanOrEqual", formula1="1"),
        dv("Number", type="decimal", ref="D2:D50", operator="greaterThan", formula1="0"),
        dv("Number", type="whole", ref="E2:E50", operator="notEqual", formula1="13"),
    ]
    doc.batch(items)

    # ======================================================================
    # Sheet3: Date & Time
    # ======================================================================
    print("--- Sheet3: Date & Time ---")
    items = [add_sheet("DateTime"),
             hdr("DateTime", "A1", "Event date (2024)"), hdr("DateTime", "B1", "Shift start (9-17)"),
             hdr("DateTime", "C1", "Deadline (=EOY)"), hdr("DateTime", "D1", "Ship after")]
    items += col("DateTime", "A", 2, ["2024-03-15", "2024-07-01"])
    items += col("DateTime", "B", 2, ["10:30:00", "14:00:00"])
    items += col("DateTime", "D", 2, ["2024-06-01"])
    items += [
        dv("DateTime", type="date", ref="A2:A50", operator="between",
           formula1="2024-01-01", formula2="2024-12-31"),   # bounds stored as serials
        dv("DateTime", type="time", ref="B2:B50", operator="between",
           formula1="09:00:00", formula2="17:00:00"),        # bounds stored as day fractions
        dv("DateTime", type="date", ref="C2:C50", operator="equal", formula1="2024-12-31"),
        dv("DateTime", type="date", ref="D2:D50", operator="greaterThan", formula1="2024-01-01"),
    ]
    doc.batch(items)

    # ======================================================================
    # Sheet4: Text length
    # ======================================================================
    print("--- Sheet4: Text length ---")
    items = [add_sheet("TextLength"),
             hdr("TextLength", "A1", "Username (3-16)"), hdr("TextLength", "B1", "Country code (=2)"),
             hdr("TextLength", "C1", "Tweet (<=280)"), hdr("TextLength", "D1", "PIN (not 5-7)")]
    items += col("TextLength", "A", 2, ["alice", "bob_smith"])
    items += col("TextLength", "B", 2, ["US", "GB"])
    items += col("TextLength", "C", 2, ["hello world"])
    items += col("TextLength", "D", 2, ["1234", "12345678"])
    items += [
        dv("TextLength", type="textLength", ref="A2:A50", operator="between", formula1="3", formula2="16"),
        dv("TextLength", type="textLength", ref="B2:B50", operator="equal", formula1="2"),
        dv("TextLength", type="textLength", ref="C2:C50", operator="lessThanOrEqual", formula1="280"),
        dv("TextLength", type="textLength", ref="D2:D50", operator="notBetween", formula1="5", formula2="7"),
    ]
    doc.batch(items)

    # ======================================================================
    # Sheet5: Custom formula
    # ======================================================================
    print("--- Sheet5: Custom formula ---")
    items = [add_sheet("Custom"),
             hdr("Custom", "A1", "Must be number"), hdr("Custom", "B1", "Even only"),
             hdr("Custom", "C1", "No spaces")]
    items += col("Custom", "A", 2, [42, 3.14])
    items += col("Custom", "B", 2, [2, 4])
    items += col("Custom", "C", 2, ["nospace", "ok"])
    items += [
        dv("Custom", type="custom", ref="A2:A50", formula1="ISNUMBER(A2)"),
        dv("Custom", type="custom", ref="B2:B50", formula1="MOD(B2,2)=0"),
        dv("Custom", type="custom", ref="C2:C50", formula1='ISERROR(FIND(" ",C2))'),
    ]
    doc.batch(items)

    # ======================================================================
    # Sheet6: Messages — input prompt, error message, all three errorStyles
    # ======================================================================
    print("--- Sheet6: Messages (prompt / error / errorStyle) ---")
    items = [add_sheet("Messages"),
             hdr("Messages", "A1", "Age (stop)"), hdr("Messages", "B1", "Budget (warning)"),
             hdr("Messages", "C1", "Note (information)"), hdr("Messages", "D1", "Allow blank=false")]
    items += [
        # errorStyle=stop — hard block; full input prompt + error message
        dv("Messages", type="whole", ref="A2:A50", operator="between", formula1="18", formula2="120",
           promptTitle="Enter age", prompt="Age must be 18-120", showInput="true",
           errorTitle="Invalid age", error="Please enter a whole number 18-120", showError="true",
           errorStyle="stop"),
        # errorStyle=warning — soft block, user may override
        dv("Messages", type="decimal", ref="B2:B50", operator="lessThanOrEqual", formula1="10000",
           promptTitle="Budget cap", prompt="Suggested max is 10,000",
           errorTitle="Over budget", error="That exceeds the cap — continue anyway?",
           errorStyle="warning"),
        # errorStyle=information — advisory only, never blocks
        dv("Messages", type="textLength", ref="C2:C50", operator="lessThanOrEqual", formula1="200",
           promptTitle="Note", prompt="Keep notes under 200 chars",
           errorTitle="Long note", error="This note is quite long.",
           errorStyle="information"),
        # allowBlank=false (empty cells invalid) + showInput=false (no prompt bubble)
        dv("Messages", type="whole", ref="D2:D50", operator="greaterThan", formula1="0",
           allowBlank="false", showInput="false", showError="true",
           errorTitle="Required", error="This field is required and must be > 0"),
    ]
    doc.batch(items)

    # ======================================================================
    # Get round-trip: confirm canonical keys read back (in-session, over pipe)
    # ======================================================================
    print("\n--- Round-trip readback (Get the validations) ---")
    for path in ["/Sheet1/dataValidation[2]", "/DateTime/dataValidation[1]",
                 "/Custom/dataValidation[2]", "/Messages/dataValidation[2]"]:
        node = doc.send({"command": "get", "path": path})
        fmt = node.get("data", {}).get("results", [{}])[0].get("format", {})
        keys = ("type", "ref", "operator", "formula1", "formula2", "errorStyle",
                "prompt", "error", "inCellDropdown", "allowBlank")
        shown = {k: fmt.get(k) for k in keys if k in fmt}
        print(f"  {path}: {shown}")

    doc.send({"command": "save"})
# context exit closes the resident, flushing the workbook to disk.

# Validate the SAVED file with a fresh one-shot process (NOT in-session):
# validations live in each sheet's <dataValidations> block, so validate from
# disk to confirm they serialized cleanly.
print("\n--- Validate (fresh process, from disk) ---")
r = subprocess.run(["officecli", "validate", FILE], capture_output=True, text=True)
print(" ", (r.stdout or r.stderr).strip().split("\n")[0])

print(f"\nCreated: {FILE}")
