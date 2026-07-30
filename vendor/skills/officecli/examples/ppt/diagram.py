#!/usr/bin/env python3
"""
Mermaid diagrams — every property + both render modes, enumerating the mermaid
type gallery. SDK twin of diagram.sh; both produce an equivalent diagram.pptx.

  render=native  → editable PowerPoint shapes + connectors (no browser).
                   Supported types: flowchart / graph, sequenceDiagram.
  render=image   → full-fidelity PNG via real mermaid.js (headless browser).
                   Covers EVERY mermaid type; source stamped into alt-text.
  render=auto    → (default) image when a browser is present, else native.

A diagram is an ADD-ONLY synthesizer (like 'equation'): no persistent 'diagram'
node — the whole picture is ONE object and Add returns its path. Native → a group
(/slide[N]/group[K]); image → a single PNG picture (/slide[N]/picture[K]).

Source props are interchangeable — mermaid= (canonical), text=, dsl=, or src= (a
.mmd file). x/y/width/height define a box the diagram is fitted into (aspect
preserved, centred). poster= is deck-wide (pptx has one slide size) so it is
documented at the end, not baked into this multi-slide file.

This one drives the officecli Python SDK (`pip install officecli-sdk`): one
resident is started and every command is shipped over the named pipe. render=image
launches a browser per slide — the SDK client retries a busy connect, so it is safe.

Usage:
  pip install officecli-sdk          # plus the `officecli` binary on PATH
  python3 diagram.py
"""

import os
import sys

try:
    import officecli  # pip install officecli-sdk
except ImportError:
    sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                    "..", "..", "sdk", "python"))
    import officecli

HERE = os.path.dirname(os.path.abspath(__file__))
FILE = os.path.join(HERE, "diagram.pptx")
MMD = os.path.join(HERE, "pie.mmd")   # loaded via src= on the pie gallery slide

BOX = dict(x="1in", y="1.2in", width="11.3in", height="5.8in")

# The one flowchart the native + image comparison both render. Exercises the
# node-shape vocabulary the native synthesizer maps: ([stadium]) {diamond} [rect]
# [(database)] [[subroutine]] {{hexagon}} [/parallelogram/] ((circle)); and edge
# forms -->|label|  -.->  ==>  --x .
FLOW = ("flowchart TD\n"
        "  A([Start]) --> B{Decision}\n"
        "  B -->|yes| C[Process]\n"
        "  B -->|no| D[(Database)]\n"
        "  C --> E[[Subroutine]]\n"
        "  D -.-> F{{Prepare}}\n"
        "  E ==> G((Done))\n"
        "  F --> G\n"
        "  A --> H[/Input/]\n"
        "  H --x B")

SEQUENCE = ("sequenceDiagram\n"
            "  participant U as User\n"
            "  participant S as Server\n"
            "  participant D as Database\n"
            "  U->>S: Login request\n"
            "  S->>D: Validate credentials\n"
            "  D-->>S: OK\n"
            "  S-->>U: Session token")

# Image gallery — every other mermaid type (no native synthesizer). Ordered.
GALLERY = [
    ("pie",          "pie — proportions",                 None),   # pie loads via src= below
    ("class",        "classDiagram — UML classes",
     "classDiagram\n  class Animal { +int age +run() }\n  class Dog { +bark() }\n  Animal <|-- Dog"),
    ("state",        "stateDiagram-v2 — states",
     "stateDiagram-v2\n  [*] --> Idle\n  Idle --> Running: start\n  Running --> Idle: pause\n  Running --> [*]: stop"),
    ("er",           "erDiagram — entities & relations",
     "erDiagram\n  CUSTOMER ||--o{ ORDER : places\n  ORDER ||--|{ LINE_ITEM : contains"),
    ("gantt",        "gantt — project schedule",
     "gantt\n  title Project Plan\n  dateFormat YYYY-MM-DD\n  axisFormat %b %d\n"
     "  tickInterval 1week\n  weekday monday\n  todayMarker off\n  section Design\n"
     "  Research :a1, 2024-01-01, 5d\n  Draft :after a1, 4d\n  section Build\n  Code :2024-01-12, 6d"),
    ("journey",      "journey — user journey",
     "journey\n  title My working day\n  section Morning\n  Standup: 3: Me, Team\n"
     "  Code: 5: Me\n  section Afternoon\n  Review: 2: Me"),
    ("git",          "gitGraph — branch/merge",
     "gitGraph\n  commit\n  branch develop\n  commit\n  checkout main\n  merge develop\n  commit"),
    ("mindmap",      "mindmap — hierarchy",
     "mindmap\n  root((mermaid))\n    Origins\n      History\n    Uses\n      Docs\n      Diagrams"),
    ("timeline",     "timeline — events",
     "timeline\n  title Release History\n  2019 : v1\n  2021 : v2 : v2.1\n  2023 : v3"),
    ("quadrant",     "quadrantChart — 2x2 matrix",
     "quadrantChart\n  title Reach vs Engagement\n  x-axis Low Reach --> High Reach\n"
     "  y-axis Low Engagement --> High Engagement\n  quadrant-1 Expand\n  quadrant-2 Promote\n"
     "  quadrant-3 Re-evaluate\n  quadrant-4 Improve\n  Campaign A: [0.3, 0.6]\n  Campaign B: [0.45, 0.23]"),
    ("requirement",  "requirementDiagram — requirements",
     "requirementDiagram\n  requirement test_req {\n    id: 1\n    text: the test text\n"
     "    risk: high\n    verifymethod: test\n  }\n  element test_entity {\n    type: simulation\n  }\n"
     "  test_entity - satisfies -> test_req"),
    ("c4",           "C4Context — system context",
     'C4Context\n  title System Context\n  Person(customer, "Customer")\n'
     '  System(banking, "Internet Banking")\n  Rel(customer, banking, "Uses")'),
    ("sankey",       "sankey-beta — flow volumes",
     "sankey-beta\nAgricultural,Bio-conversion,124\nBio-conversion,Losses,26\n"
     "Bio-conversion,Solid,280\nBio-conversion,Gas,81"),
    ("xychart",      "xychart-beta — bar/line",
     'xychart-beta\n  title "Monthly Revenue"\n  x-axis [jan, feb, mar, apr]\n'
     '  y-axis "Revenue (k$)" 0 --> 100\n  bar [30, 50, 65, 80]\n  line [30, 50, 65, 80]'),
    ("block",        "block-beta — block layout",
     'block-beta\n  columns 3\n  a["Ingest"] b["Process"] c["Store"]\n  d["Log"]'),
    ("packet",       "packet-beta — byte layout",
     'packet-beta\n  0-15: "Source Port"\n  16-31: "Destination Port"\n  32-63: "Sequence Number"'),
    ("kanban",       "kanban — board",
     "kanban\n  Todo\n    t1[Design]\n  In Progress\n    t2[Build]\n  Done\n    t3[Ship]"),
    ("architecture", "architecture-beta — cloud services",
     "architecture-beta\n  group api(cloud)[API]\n  service db(database)[Database] in api\n"
     "  service server(server)[Server] in api\n  db:L -- R:server"),
    ("radar",        "radar-beta — multi-axis scores",
     'radar-beta\n  title Skill Assessment\n  axis a["Coding"], b["Design"], c["Testing"], d["Docs"]\n'
     "  curve x{80, 60, 70, 50}"),
]

# The pie source loaded via src= on its gallery slide.
with open(MMD, "w") as f:
    f.write('pie showData title Traffic Sources\n'
            '    "Organic Search" : 45\n'
            '    "Direct" : 30\n'
            '    "Referral" : 15\n'
            '    "Social" : 10\n')

print(f"Building {FILE} ...")

with officecli.create(FILE, "--force") as doc:

    def add(parent, type_, **props):
        return doc.send({"command": "add", "parent": parent, "type": type_,
                         "props": {k: str(v) for k, v in props.items()}})

    def title(slide, text):
        add(f"/slide[{slide}]", "textbox", text=text, size=24, bold="true",
            x="0.5in", y="0.3in", width="12.3in", height="0.6in")

    # Slide 1 — Title
    add("/", "slide")
    add("/slide[1]", "textbox", text="Mermaid Diagrams", size=44, bold="true",
        x="1in", y="2.5in", width="11.3in", height="1in", align="center")
    add("/slide[1]", "textbox",
        text="native editable shapes  ·  full-fidelity PNG for every mermaid type",
        size=20, color="595959",
        x="1in", y="3.6in", width="11.3in", height="0.6in", align="center")

    # Slide 2 — NATIVE flowchart (mermaid=), fitted + centred in the box.
    add("/", "slide")
    title(2, "render=native — flowchart (editable shapes + connectors)")
    add("/slide[2]", "diagram", render="native", mermaid=FLOW, **BOX)
    # The whole native diagram is ONE group — read its box back. set width=/height=
    # resizes it as a unit (fonts re-bake); remove deletes group + children.
    print(doc.send({"command": "get", "path": "/slide[2]/group[1]"}))

    # Slide 3 — IMAGE of the SAME flowchart (dsl= alias). Apples-to-apples.
    add("/", "slide")
    title(3, "render=image — the same flowchart as a full-fidelity PNG")
    add("/slide[3]", "diagram", render="image", dsl=FLOW, **BOX)

    # Slide 4 — NATIVE sequenceDiagram (text= alias). 2nd native-supported type.
    add("/", "slide")
    title(4, "render=native — sequenceDiagram")
    add("/slide[4]", "diagram", render="native", text=SEQUENCE, **BOX)

    # Slides 5+ — IMAGE gallery: every other mermaid type.
    n = 4
    for key, desc, src in GALLERY:
        n += 1
        add("/", "slide")
        title(n, f"render=image — {desc}")
        if key == "pie":
            add(f"/slide[{n}]", "diagram", render="image", src=MMD, **BOX)   # src= (alias path=)
        else:
            add(f"/slide[{n}]", "diagram", render="image", text=src, **BOX)

    doc.send({"command": "save"})

# poster= is deck-wide: pptx has a single slide size, so poster=true grows the
# WHOLE deck to the diagram's natural size (export-a-diagram-as-a-slide). Use it
# in a single-diagram file, e.g.:
#   add("/slide[1]", "diagram", poster="true", mermaid="flowchart LR; A --> B --> C")

print(f"Generated: {FILE}")
