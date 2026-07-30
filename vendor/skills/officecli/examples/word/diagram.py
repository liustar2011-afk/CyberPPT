#!/usr/bin/env python3
"""
Mermaid diagrams in Word — native (editable shapes) + image (full-fidelity PNG),
enumerating the mermaid type gallery. SDK twin of diagram.sh.

  render=native  → editable Word drawing shapes + connectors (no browser).
                   Supported types: flowchart / graph, sequenceDiagram. FLOATING
                   shapes anchored to the page margin, so each native diagram gets
                   its own page (page break) to avoid overlapping text.
  render=image   → full-fidelity PNG via real mermaid.js. Covers EVERY mermaid type
                   and is INLINE, so it flows with the text like any picture.
  render=auto    → (default) image when a browser is present, else native.

Source props are interchangeable: mermaid= (canonical), text=, dsl=, or src= (a
.mmd file). width/height fit the diagram (aspect preserved). Word has no slide, so
there is no x/y and no poster (pptx-only). `add` returns the object path — a group
(/body/group[N]) for native, an inline picture paragraph for image.

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
FILE = os.path.join(HERE, "diagram.docx")
MMD = os.path.join(HERE, "pie.mmd")

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

GALLERY = [
    ("classDiagram — UML classes",
     "classDiagram\n  class Animal { +int age +run() }\n  class Dog { +bark() }\n  Animal <|-- Dog"),
    ("stateDiagram-v2 — states",
     "stateDiagram-v2\n  [*] --> Idle\n  Idle --> Running: start\n  Running --> Idle: pause\n  Running --> [*]: stop"),
    ("erDiagram — entities & relations",
     "erDiagram\n  CUSTOMER ||--o{ ORDER : places\n  ORDER ||--|{ LINE_ITEM : contains"),
    ("gantt — project schedule",
     "gantt\n  title Project Plan\n  dateFormat YYYY-MM-DD\n  axisFormat %b %d\n  tickInterval 1week\n"
     "  weekday monday\n  todayMarker off\n  section Design\n  Research :a1, 2024-01-01, 5d\n"
     "  Draft :after a1, 4d\n  section Build\n  Code :2024-01-12, 6d"),
    ("journey — user journey",
     "journey\n  title My working day\n  section Morning\n  Standup: 3: Me, Team\n"
     "  Code: 5: Me\n  section Afternoon\n  Review: 2: Me"),
    ("gitGraph — branch/merge",
     "gitGraph\n  commit\n  branch develop\n  commit\n  checkout main\n  merge develop\n  commit"),
    ("mindmap — hierarchy",
     "mindmap\n  root((mermaid))\n    Origins\n      History\n    Uses\n      Docs\n      Diagrams"),
    ("timeline — events",
     "timeline\n  title Release History\n  2019 : v1\n  2021 : v2 : v2.1\n  2023 : v3"),
    ("quadrantChart — 2x2 matrix",
     "quadrantChart\n  title Reach vs Engagement\n  x-axis Low Reach --> High Reach\n"
     "  y-axis Low Engagement --> High Engagement\n  quadrant-1 Expand\n  quadrant-2 Promote\n"
     "  quadrant-3 Re-evaluate\n  quadrant-4 Improve\n  Campaign A: [0.3, 0.6]\n  Campaign B: [0.45, 0.23]"),
    ("requirementDiagram — requirements",
     "requirementDiagram\n  requirement test_req {\n    id: 1\n    text: the test text\n"
     "    risk: high\n    verifymethod: test\n  }\n  element test_entity {\n    type: simulation\n  }\n"
     "  test_entity - satisfies -> test_req"),
    ("C4Context — system context",
     'C4Context\n  title System Context\n  Person(customer, "Customer")\n'
     '  System(banking, "Internet Banking")\n  Rel(customer, banking, "Uses")'),
    ("sankey-beta — flow volumes",
     "sankey-beta\nAgricultural,Bio-conversion,124\nBio-conversion,Losses,26\n"
     "Bio-conversion,Solid,280\nBio-conversion,Gas,81"),
    ("xychart-beta — bar/line",
     'xychart-beta\n  title "Monthly Revenue"\n  x-axis [jan, feb, mar, apr]\n'
     '  y-axis "Revenue (k$)" 0 --> 100\n  bar [30, 50, 65, 80]\n  line [30, 50, 65, 80]'),
    ("block-beta — block layout",
     'block-beta\n  columns 3\n  a["Ingest"] b["Process"] c["Store"]\n  d["Log"]'),
    ("packet-beta — byte layout",
     'packet-beta\n  0-15: "Source Port"\n  16-31: "Destination Port"\n  32-63: "Sequence Number"'),
    ("kanban — board",
     "kanban\n  Todo\n    t1[Design]\n  In Progress\n    t2[Build]\n  Done\n    t3[Ship]"),
    ("architecture-beta — cloud services",
     "architecture-beta\n  group api(cloud)[API]\n  service db(database)[Database] in api\n"
     "  service server(server)[Server] in api\n  db:L -- R:server"),
    ("radar-beta — multi-axis scores",
     'radar-beta\n  title Skill Assessment\n  axis a["Coding"], b["Design"], c["Testing"], d["Docs"]\n'
     "  curve x{80, 60, 70, 50}"),
]

with open(MMD, "w") as f:
    f.write('pie showData title Traffic Sources\n'
            '    "Organic Search" : 45\n    "Direct" : 30\n'
            '    "Referral" : 15\n    "Social" : 10\n')

print(f"Building {FILE} ...")

with officecli.create(FILE, "--force") as doc:

    def add(type_, **props):
        return doc.send({"command": "add", "parent": "/body", "type": type_,
                         "props": {k: str(v) for k, v in props.items()}})

    def head(text, page_break=False):
        p = dict(text=text, bold="true", size=16)
        if page_break:
            p["pageBreakBefore"] = "true"
        add("paragraph", **p)

    def para(text):
        add("paragraph", text=text)

    # Title
    add("paragraph", text="Mermaid Diagrams in Word", bold="true", size=24)
    para("The same --type diagram element as pptx, in a .docx body. Native builds "
         "editable Word shapes; image embeds a full-fidelity PNG of any mermaid type.")

    # render=native — flowchart (its own page: native diagrams float)
    head("render=native — flowchart (editable shapes + connectors)", page_break=True)
    add("diagram", render="native", mermaid=FLOW, width="12cm")
    # ONE group at the returned path — read its box back; set width= resizes, remove deletes.
    print(doc.send({"command": "get", "path": "/body/group[1]"}))

    # render=native — sequenceDiagram, its own page
    head("render=native — sequenceDiagram", page_break=True)
    add("diagram", render="native", text=SEQUENCE, width="13cm")

    # render=image — inline PNGs that flow with the text
    head("render=image — full-fidelity PNG (real mermaid.js)", page_break=True)
    para("Image diagrams are inline pictures, so they flow with the text. The same "
         "flowchart as above, now a PNG (dsl= is an alias of mermaid=):")
    add("diagram", render="image", dsl=FLOW, width="14cm")

    # pie via src= (alias path=)
    head("render=image — pie — proportions")
    add("diagram", render="image", src=MMD, width="10cm")

    # the rest of the gallery, inline (text=)
    for heading, source in GALLERY:
        head(f"render=image — {heading}")
        add("diagram", render="image", text=source, width="14cm")

    doc.send({"command": "save"})

print(f"Generated: {FILE}")
