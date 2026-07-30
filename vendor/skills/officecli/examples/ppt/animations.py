#!/usr/bin/env python3
"""
Animation Showcase — the first-class pptx `animation` element.

SDK twin of animations.sh. Both produce an equivalent animations.pptx. This one
drives the **officecli Python SDK** (`pip install officecli-sdk`): one resident
is started and every slide, shape, and animation is shipped over the named pipe
in `doc.batch(...)` round-trips. Each item is the same
`{"command","parent"/"path","type","props"}` dict you'd put in an
`officecli batch` list.

The animation element exposes the full prop surface — effect, class
(entrance/exit/emphasis/motion), trigger (onClick/withPrevious/afterPrevious),
duration, delay, repeat, autoReverse, restart, direction, and motion paths
(path=/d=). Add it under a shape:

    {"command": "add", "parent": "/slide[N]/shape[M]", "type": "animation",
     "props": {"effect": "fade", "class": "entrance", "duration": "800"}}

Usage:
  pip install officecli-sdk          # plus the `officecli` binary on PATH
  python3 animations.py
"""

import os
import sys

# --- locate the SDK: prefer an installed `officecli-sdk`, else the in-repo copy
try:
    import officecli  # pip install officecli-sdk
except ImportError:
    sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                    "..", "..", "sdk", "python"))
    import officecli

FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "animations.pptx")


def add_slide(**props):
    """One `add slide` item in batch-shape."""
    return {"command": "add", "parent": "/", "type": "slide", "props": props}


def add_shape(slide, **props):
    """One `add shape` item in batch-shape, targeting /slide[N]."""
    return {"command": "add", "parent": f"/slide[{slide}]", "type": "shape", "props": props}


def add_anim(slide, shape, **props):
    """One `add animation` item — attaches an animation element to a shape.
    `class` is a Python keyword, so callers pass it via `cls=` and we remap."""
    if "cls" in props:
        props["class"] = props.pop("cls")
    return {"command": "add", "parent": f"/slide[{slide}]/shape[{shape}]",
            "type": "animation", "props": props}


def setp(path, **props):
    """One `set` item in batch-shape."""
    return {"command": "set", "path": path, "props": props}


def card(slide, text, fill, x, y):
    """A labeled rounded-rect card (twin of the shell `card` helper)."""
    return add_shape(slide, text=text, font="Consolas", size="13", color="FFFFFF",
                     fill=fill, preset="roundRect", x=x, y=y, width="6cm", height="2cm")


print(f"Building {FILE} ...")

with officecli.create(FILE, "--force") as doc:

    # =====================================================================
    # SLIDE 1 — Title
    # =====================================================================
    print("  -> Slide 1: Title")
    doc.batch([
        add_slide(layout="title"),
        setp("/slide[1]", background="radial:0D1B2A-1B4F72-bl"),
        setp("/slide[1]/placeholder[centertitle]",
             text="Animation Showcase", color="FFFFFF", size="48"),
        setp("/slide[1]/placeholder[subtitle]",
             text="The pptx animation element — every prop that round-trips",
             color="85C1E9", size="22"),
        setp("/slide[1]", transition="fade"),
    ])

    # =====================================================================
    # SLIDE 2 — Entrance Effects (effect + class=entrance + duration)
    # =====================================================================
    print("  -> Slide 2: Entrance Effects")
    entrances = [
        ("appear", "2E86C1", "400"), ("fade", "27AE60", "800"),
        ("fly", "E74C3C", "600"),    ("zoom", "8E44AD", "700"),
        ("wipe", "F39C12", "600"),   ("bounce", "1ABC9C", "800"),
        ("float", "E67E22", "700"),  ("swivel", "16A085", "700"),
        ("split", "2980B9", "600"),  ("wheel", "C0392B", "800"),
        ("box", "7D3C98", "600"),    ("circle", "D35400", "600"),
    ]
    items = [
        add_slide(title="Entrance Effects"),
        setp("/slide[2]", background="1B2838"),
        setp("/slide[2]/shape[1]", color="FFFFFF", size="28"),
    ]
    sh = 2
    for idx, (eff, fill, dur) in enumerate(entrances):
        col, row = idx % 4, idx // 4
        items.append(card(2, eff, fill, f"{1 + col * 6}cm", f"{4 + row * 3}cm"))
        # Features: effect=<name> class=entrance duration=<ms>
        items.append(add_anim(2, sh, effect=eff, cls="entrance", duration=dur))
        sh += 1
    items.append(setp("/slide[2]", transition="wipe"))
    doc.batch(items)

    # =====================================================================
    # SLIDE 3 — Exit Effects (class=exit; direction on directional effects)
    # =====================================================================
    print("  -> Slide 3: Exit Effects")
    # (label, fill, effect, duration, direction-or-None)
    exits = [
        ("fade out",  "E74C3C", "fade",     "800", None),
        ("fly down",  "2E86C1", "fly",      "600", "down"),
        ("fly up",    "2980B9", "fly",      "600", "up"),
        ("zoom out",  "27AE60", "zoom",     "700", None),
        ("wipe left", "F39C12", "wipe",     "600", "left"),
        ("wipe right","D35400", "wipe",     "600", "right"),
        ("dissolve",  "8E44AD", "dissolve", "600", None),
        ("split",     "1ABC9C", "split",    "600", None),
        ("wheel",     "C0392B", "wheel",    "800", None),
        ("flash",     "16A085", "flash",    "500", None),
    ]
    items = [
        add_slide(title="Exit Effects"),
        setp("/slide[3]", background="1B2838"),
        setp("/slide[3]/shape[1]", color="FFFFFF", size="28"),
    ]
    sh = 2
    for idx, (label, fill, eff, dur, direction) in enumerate(exits):
        col, row = idx % 4, idx // 4
        items.append(card(3, label, fill, f"{1 + col * 6}cm", f"{4 + row * 3}cm"))
        props = dict(effect=eff, cls="exit", duration=dur)
        if direction:
            # Features: effect=<name> class=exit direction=<dir> duration=<ms>
            props["direction"] = direction
        items.append(add_anim(3, sh, **props))
        sh += 1
    items.append(setp("/slide[3]", transition="push"))
    doc.batch(items)

    # =====================================================================
    # SLIDE 4 — Emphasis & Color Effects (class=emphasis)
    # =====================================================================
    print("  -> Slide 4: Emphasis & Color Effects")
    emphases = [
        ("spin", "E74C3C", "1000"),      ("grow", "2E86C1", "800"),
        ("wave", "27AE60", "700"),       ("growShrink", "8E44AD", "800"),
        ("teeter", "E67E22", "600"),     ("pulse", "1ABC9C", "500"),
    ]
    items = [
        add_slide(title="Emphasis & Color Effects"),
        setp("/slide[4]", background="1B2838"),
        setp("/slide[4]/shape[1]", color="FFFFFF", size="28"),
    ]
    sh = 2
    for idx, (eff, fill, dur) in enumerate(emphases):
        col, row = idx % 3, idx // 3
        items.append(add_shape(4, text=eff, font="Consolas", size="14", color="FFFFFF",
                               fill=fill, preset="ellipse",
                               x=f"{1.5 + col * 6}cm", y=f"{4 + row * 5}cm",
                               width="4.5cm", height="4.5cm"))
        # Features: effect=<name> class=emphasis duration=<ms>
        items.append(add_anim(4, sh, effect=eff, cls="emphasis", duration=dur))
        sh += 1
    items.append(setp("/slide[4]", transition="zoom"))
    doc.batch(items)

    # =====================================================================
    # SLIDE 5 — Motion Paths (class=motion + path=<preset|custom>)
    # =====================================================================
    print("  -> Slide 5: Motion Paths")
    # (label, fill, path, direction-or-None)
    paths = [
        ("line right", "2E86C1", "line",    "right"),
        ("line down",  "27AE60", "line",    "down"),
        ("arc",        "E74C3C", "arc",     "right"),
        ("circle",     "8E44AD", "circle",  None),
        ("diamond",    "F39C12", "diamond", None),
        ("square",     "16A085", "square",  None),
    ]
    items = [
        add_slide(title="Motion Paths"),
        setp("/slide[5]", background="1B2838"),
        setp("/slide[5]/shape[1]", color="FFFFFF", size="28"),
    ]
    sh = 2
    for idx, (label, fill, path, direction) in enumerate(paths):
        col, row = idx % 3, idx // 3
        items.append(card(5, label, fill, f"{1 + col * 6}cm", f"{4 + row * 4}cm"))
        props = {"cls": "motion", "path": path, "duration": "1000"}
        if direction:
            # Features: class=motion path=<preset> direction=<dir> duration=1000
            props["direction"] = direction
        items.append(add_anim(5, sh, **props))
        sh += 1
    # Custom motion path via d= (SVG-like; coords 0..1 of the slide; auto-appends 'E').
    items.append(card(5, "path=custom (d=)", "C0392B", "1cm", "12cm"))
    # Features: class=motion path=custom d=<SVG-path> duration=1500
    items.append(add_anim(5, sh, cls="motion", path="custom",
                          d="M 0 0 L 0.3 -0.1 L 0.6 0.1 E", duration="1500"))
    items.append(setp("/slide[5]", transition="split"))
    doc.batch(items)

    # =====================================================================
    # SLIDE 6 — Timing & Trigger Chaining
    # =====================================================================
    print("  -> Slide 6: Timing & Trigger Chaining")
    items = [
        add_slide(title="Timing & Trigger Chaining"),
        setp("/slide[6]", background="1B2838"),
        setp("/slide[6]/shape[1]", color="FFFFFF", size="28"),
        # 1) onClick — starts the chain on the first mouse click (default).
        card(6, "1. onClick\n(starts chain)", "2E86C1", "1cm", "4cm"),
        # Features: effect=fade class=entrance trigger=onClick duration=500
        add_anim(6, 2, effect="fade", cls="entrance", trigger="onClick", duration="500"),
        # 2) afterPrevious — auto-plays once #1 finishes.
        card(6, "2. afterPrevious\n(auto-follows #1)", "27AE60", "9cm", "4cm"),
        # Features: effect=fly class=entrance trigger=afterPrevious duration=600
        add_anim(6, 3, effect="fly", cls="entrance", trigger="afterPrevious", duration="600"),
        # 3) withPrevious — plays simultaneously with #2.
        card(6, "3. withPrevious\n(with #2)", "E74C3C", "17cm", "4cm"),
        # Features: effect=zoom class=entrance trigger=withPrevious duration=600
        add_anim(6, 4, effect="zoom", cls="entrance", trigger="withPrevious", duration="600"),
        # 4) afterPrevious + delay — waits 800ms after #3 before starting.
        card(6, "4. afterPrevious\n+ delay=800", "8E44AD", "5cm", "8cm"),
        # Features: effect=wipe class=entrance trigger=afterPrevious delay=800 duration=700
        add_anim(6, 5, effect="wipe", cls="entrance", trigger="afterPrevious",
                 delay="800", duration="700"),
        # 5) Slow (2000ms) vs the fast ones above.
        card(6, "5. slow duration=2000", "F39C12", "13cm", "8cm"),
        # Features: effect=wipe class=entrance trigger=afterPrevious duration=2000
        add_anim(6, 6, effect="wipe", cls="entrance", trigger="afterPrevious", duration="2000"),
        setp("/slide[6]", transition="reveal"),
    ]
    doc.batch(items)

    # =====================================================================
    # SLIDE 7 — Repeat, autoReverse & Restart
    # =====================================================================
    print("  -> Slide 7: Repeat, autoReverse & Restart")

    def ellipse(text, fill, x, size="13"):
        return add_shape(7, text=text, font="Consolas", size=size, color="FFFFFF",
                         fill=fill, preset="ellipse", x=x, y="5cm",
                         width="4cm", height="4cm")

    items = [
        add_slide(title="Repeat · autoReverse · Restart"),
        setp("/slide[7]", background="1B2838"),
        setp("/slide[7]/shape[1]", color="FFFFFF", size="28"),
        # repeat=3 — plays the emphasis three times.
        ellipse("repeat=3", "E74C3C", "2cm", size="14"),
        # Features: effect=spin class=emphasis repeat=3 duration=800
        add_anim(7, 2, effect="spin", cls="emphasis", repeat="3", duration="800"),
        # repeat=indefinite — loops forever.
        ellipse("repeat=indefinite", "2E86C1", "8cm"),
        # Features: effect=pulse class=emphasis repeat=indefinite trigger=withPrevious duration=600
        add_anim(7, 3, effect="pulse", cls="emphasis", repeat="indefinite",
                 trigger="withPrevious", duration="600"),
        # autoReverse=true — plays forward then reverses.
        ellipse("autoReverse=true", "27AE60", "14cm"),
        # Features: effect=grow class=emphasis autoReverse=true repeat=2 duration=700
        add_anim(7, 4, effect="grow", cls="emphasis", autoReverse="true",
                 repeat="2", duration="700"),
        # restart=whenNotActive — re-trigger only restarts if not already playing.
        ellipse("restart=whenNotActive", "8E44AD", "20cm", size="12"),
        # Features: effect=teeter class=emphasis restart=whenNotActive repeat=indefinite duration=500
        add_anim(7, 5, effect="teeter", cls="emphasis", restart="whenNotActive",
                 repeat="indefinite", duration="500"),
        setp("/slide[7]", transition="zoom"),
    ]
    doc.batch(items)

print(f"Generated: {FILE}")
