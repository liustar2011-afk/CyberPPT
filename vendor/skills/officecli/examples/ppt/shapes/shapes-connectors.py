#!/usr/bin/env python3
"""
Connectors and groups — generates shapes-connectors.pptx exercising the pptx
`connector` element (straight / elbow / curve presets, head/tail arrowheads,
lineJoin / miterLimit) and the `group` element (comma-separated shape indices).

SDK twin of shapes-connectors.sh (officecli CLI). Both produce an equivalent
shapes-connectors.pptx. This one drives the **officecli Python SDK**
(`pip install officecli-sdk`): one resident is started and every command is
shipped over the named pipe. Each item is the same
`{"command","parent","type","props"}` dict you'd put in an `officecli batch`
list.

Connectors attach to shapes via from=/to= shape *paths*, and a group is built
from a comma-separated list of shape paths — so the shapes those refer to must
be added first and their returned `@id` path captured. `add_shape` does exactly
that: it `send`s one add and parses the path out of the response envelope
("Added shape at /slide[N]/shape[@id=M]" → the last whitespace-delimited token).

Usage:
  pip install officecli-sdk          # plus the `officecli` binary on PATH
  python3 shapes-connectors.py
"""

import os
import sys

# --- locate the SDK: prefer an installed `officecli-sdk`, else the in-repo copy
try:
    import officecli  # pip install officecli-sdk
except ImportError:
    sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                    "..", "..", "..", "sdk", "python"))
    import officecli

FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "shapes-connectors.pptx")


def _path_from_add(resp):
    """officecli prints "Added shape at /slide[N]/shape[@id=M]"; the path is the
    last whitespace-delimited token of the response's data/message string."""
    msg = ""
    if isinstance(resp, dict):
        msg = resp.get("data") or resp.get("message") or ""
    else:
        msg = str(resp)
    return msg.split()[-1] if msg else ""


print(f"Building {FILE} ...")

with officecli.create(FILE, "--force") as doc:

    def add(parent, type_, **props):
        """Send one `add` and return the parsed envelope."""
        return doc.send({"command": "add", "parent": parent, "type": type_,
                         "props": {k: str(v) for k, v in props.items()}})

    def add_shape(parent, **props):
        """Add a shape and return its captured @id path (for from=/to=/shapes=)."""
        return _path_from_add(add(parent, "shape", **props))

    # ─────────────────────────────────────────────────────────────────────────
    # Slide 1 — Connector geometry presets (straight / elbow / curve)
    # ─────────────────────────────────────────────────────────────────────────
    add("/", "slide")
    add("/slide[1]", "shape", text="Connector Presets", size=28, bold="true",
        x="0.5in", y="0.3in", width="12in", height="0.6in")

    A1 = add_shape("/slide[1]", geometry="ellipse",
                   x="0.5in", y="1.5in", width="2in", height="1.2in",
                   fill="4472C4", color="FFFFFF", bold="true", text="A")
    B1 = add_shape("/slide[1]", geometry="ellipse",
                   x="4.5in", y="1.5in", width="2in", height="1.2in",
                   fill="E63946", color="FFFFFF", bold="true", text="B")
    add("/slide[1]", "connector", shape="straight", **{"from": A1}, to=B1,
        color="1D3557", lineWidth="2pt", tailEnd="triangle")

    add("/slide[1]", "shape", text="straight (default)", size=12,
        x="0.5in", y="2.8in", width="6in", height="0.4in")

    A2 = add_shape("/slide[1]", geometry="ellipse",
                   x="0.5in", y="3.6in", width="2in", height="1.2in",
                   fill="4472C4", color="FFFFFF", bold="true", text="A")
    B2 = add_shape("/slide[1]", geometry="ellipse",
                   x="4.5in", y="5in", width="2in", height="1.2in",
                   fill="E63946", color="FFFFFF", bold="true", text="B")
    add("/slide[1]", "connector", shape="elbow", **{"from": A2}, to=B2,
        color="1D3557", lineWidth="2pt", tailEnd="triangle")

    add("/slide[1]", "shape", text="elbow (bent, 90° turns)", size=12,
        x="0.5in", y="6.3in", width="6in", height="0.4in")

    A3 = add_shape("/slide[1]", geometry="ellipse",
                   x="8in", y="1.5in", width="2in", height="1.2in",
                   fill="4472C4", color="FFFFFF", bold="true", text="A")
    B3 = add_shape("/slide[1]", geometry="ellipse",
                   x="11.5in", y="4.5in", width="2in", height="1.2in",
                   fill="E63946", color="FFFFFF", bold="true", text="B")
    add("/slide[1]", "connector", shape="curve", **{"from": A3}, to=B3,
        color="2A9D8F", lineWidth="3pt", tailEnd="arrow")

    add("/slide[1]", "shape", text="curve (smooth Bezier)", size=12,
        x="7.5in", y="6in", width="6in", height="0.4in")

    # ─────────────────────────────────────────────────────────────────────────
    # Slide 2 — Mini flowchart with attached connectors
    # ─────────────────────────────────────────────────────────────────────────
    add("/", "slide")
    add("/slide[2]", "shape", text="Flowchart with Attached Connectors",
        size=28, bold="true",
        x="0.5in", y="0.3in", width="12in", height="0.6in")

    P1 = add_shape("/slide[2]", geometry="roundRect",
                   x="0.8in", y="2.5in", width="2.2in", height="1.2in",
                   fill="2A9D8F", color="FFFFFF", bold="true", size=16, text="Start")
    P2 = add_shape("/slide[2]", geometry="diamond",
                   x="4.5in", y="2.3in", width="2.8in", height="1.6in",
                   fill="F4A261", color="000000", bold="true", size=14, text="Valid?")
    P3 = add_shape("/slide[2]", geometry="roundRect",
                   x="9in", y="2.5in", width="2.2in", height="1.2in",
                   fill="E63946", color="FFFFFF", bold="true", size=16, text="End")
    P4 = add_shape("/slide[2]", geometry="roundRect",
                   x="4.7in", y="5in", width="2.4in", height="1in",
                   fill="A8DADC", color="000000", bold="true", size=14, text="Retry")

    # Connect Start → Valid? → End, plus the loopback Valid? → Retry → Start
    add("/slide[2]", "connector", shape="straight", **{"from": P1}, to=P2,
        color="1D3557", lineWidth="2pt", tailEnd="triangle")
    add("/slide[2]", "connector", shape="straight", **{"from": P2}, to=P3,
        color="1D3557", lineWidth="2pt", tailEnd="triangle")
    add("/slide[2]", "connector", shape="elbow", **{"from": P2}, to=P4,
        color="E63946", lineWidth="2pt", lineDash="dash", tailEnd="triangle")
    add("/slide[2]", "connector", shape="elbow", **{"from": P4}, to=P1,
        color="E63946", lineWidth="2pt", lineDash="dash", tailEnd="triangle")

    # Branch labels (textbox-style; no fill, transparent outline)
    add("/slide[2]", "textbox", x="7.4in", y="2.7in", width="1.3in", height="0.5in",
        text="yes", size=12, bold="true", color="2A9D8F")
    add("/slide[2]", "textbox", x="6in", y="4in", width="1.3in", height="0.5in",
        text="no", size=12, bold="true", color="E63946")

    # ─────────────────────────────────────────────────────────────────────────
    # Slide 3 — Grouping shapes
    # ─────────────────────────────────────────────────────────────────────────
    add("/", "slide")
    add("/slide[3]", "shape", text="Grouping Shapes", size=28, bold="true",
        x="0.5in", y="0.3in", width="12in", height="0.6in")

    # Three logo-like shapes that we'll group together.
    G1 = add_shape("/slide[3]", geometry="ellipse",
                   x="1.5in", y="2in", width="1.4in", height="1.4in", fill="E63946")
    G2 = add_shape("/slide[3]", geometry="ellipse",
                   x="2.4in", y="2in", width="1.4in", height="1.4in",
                   fill="F4A261", opacity="0.75")
    G3 = add_shape("/slide[3]", geometry="ellipse",
                   x="3.3in", y="2in", width="1.4in", height="1.4in",
                   fill="2A9D8F", opacity="0.75")

    # Group them by passing the captured shape paths (comma-separated)
    add("/slide[3]", "group", shapes=f"{G1},{G2},{G3}", name="Logo")

    add("/slide[3]", "textbox",
        text=f"Three ellipses grouped (shapes={G1},{G2},{G3}).", size=12,
        x="0.5in", y="4in", width="12in", height="0.5in")

    # Three independent boxes for comparison
    add("/slide[3]", "shape", geometry="rect",
        x="8in", y="2in", width="1.4in", height="1.4in", fill="4472C4")
    add("/slide[3]", "shape", geometry="rect",
        x="9.5in", y="2in", width="1.4in", height="1.4in", fill="4472C4")
    add("/slide[3]", "shape", geometry="rect",
        x="11in", y="2in", width="1.4in", height="1.4in", fill="4472C4")

    add("/slide[3]", "textbox",
        text="Three independent boxes (no group — each addressed separately).",
        size=12, x="7in", y="4in", width="6in", height="0.5in")

    # ─────────────────────────────────────────────────────────────────────────
    # Slide 4 — headEnd / lineJoin / miterLimit on connectors
    # ─────────────────────────────────────────────────────────────────────────
    add("/", "slide")
    add("/slide[4]", "shape",
        text="headEnd / lineJoin / miterLimit on Connectors",
        size=24, bold="true",
        x="0.5in", y="0.3in", width="12in", height="0.6in")

    # headEnd — arrowhead at the START of the connector (the 'head' = from-side)
    # tailEnd — arrowhead at the END of the connector (the 'tail' = to-side)
    add("/slide[4]", "textbox", text="headEnd + tailEnd arrowhead combinations:",
        size=14, bold="true",
        x="0.5in", y="1.1in", width="12in", height="0.4in")

    y = 1.8
    for hv, tv in [("triangle", "oval"), ("diamond", "arrow"), ("arrow", "arrow")]:
        add("/slide[4]", "connector", shape="straight",
            x="0.5in", y=f"{y}in", width="5in", height="0in",
            color="1D3557", lineWidth="2pt", headEnd=hv, tailEnd=tv)
        add("/slide[4]", "textbox", text=f"headEnd={hv}  tailEnd={tv}", size=12,
            x="5.8in", y=f"{y}in", width="6in", height="0.4in")
        y += 0.8

    # lineJoin — connector joins: round / bevel / miter, visible at the elbow bend.
    add("/slide[4]", "textbox", text="lineJoin on elbow connectors:",
        size=14, bold="true",
        x="0.5in", y="4.6in", width="12in", height="0.4in")

    # Three elbow connectors, one per column. The third uses the compound
    # lineJoin=miter:<lim> form (limit in 1/1000ths of a percent) to also
    # exercise miterLimit.
    def add_elbow(x_in, color, line_join, label):
        add("/slide[4]", "connector", shape="elbow",
            x=f"{x_in}in", y="5.2in", width="3.4in", height="1.6in",
            color=color, lineWidth="5pt", lineJoin=line_join)
        add("/slide[4]", "textbox", text=label, size=12,
            x=f"{x_in}in", y="7.0in", width="4in", height="0.4in")

    add_elbow(0.5, "E63946", "round", "lineJoin=round")
    add_elbow(4.7, "E63946", "bevel", "lineJoin=bevel")
    add_elbow(8.9, "2A9D8F", "miter:800000", "lineJoin=miter:800000 (800% limit)")

    doc.send({"command": "save"})

print(f"Generated: {FILE}")
