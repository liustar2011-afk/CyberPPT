from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


DEFAULT_CANVAS_PX = {"w": 1280.0, "h": 720.0}
DEFAULT_SLIDE_IN = {"w": 13.333, "h": 7.5}


def px_rect_to_inches(
    rect: dict[str, Any],
    canvas_px: dict[str, float] | None = None,
    slide_in: dict[str, float] | None = None,
) -> dict[str, float]:
    canvas = canvas_px or DEFAULT_CANVAS_PX
    slide = slide_in or DEFAULT_SLIDE_IN
    return {
        "x": round(float(rect["x"]) * slide["w"] / canvas["w"], 3),
        "y": round(float(rect["y"]) * slide["h"] / canvas["h"], 3),
        "w": round(float(rect["w"]) * slide["w"] / canvas["w"], 3),
        "h": round(float(rect["h"]) * slide["h"] / canvas["h"], 3),
    }


def build_layout_context(learning: dict[str, Any]) -> dict[str, Any]:
    rules = learning.get("learned_rules", {})
    canvas_rule = rules.get("canvas", {})
    canvas_px = {
        "w": float(canvas_rule.get("width", DEFAULT_CANVAS_PX["w"])),
        "h": float(canvas_rule.get("height", DEFAULT_CANVAS_PX["h"])),
    }
    body_px = rules.get("safe_body_zone_median")
    so_what_px = rules.get("lower_so_what_band_bbox_median")
    badge_px = rules.get("top_badge_bbox_median")
    context: dict[str, Any] = {
        "schema": "cyberppt.blueprint_layout_context.v1",
        "source_learning": learning.get("blueprint_dir"),
        "canvas_px": canvas_px,
        "slide_in": DEFAULT_SLIDE_IN,
        "policy": {
            "blueprint_text_is_placeholder": True,
            "final_text_source": "content-lock",
        },
    }
    if body_px:
        context["safe_body_zone"] = px_rect_to_inches(body_px, canvas_px)
    if so_what_px:
        context["so_what_band"] = px_rect_to_inches(so_what_px, canvas_px)
        context["so_what_center_y"] = round(
            context["so_what_band"]["y"] + context["so_what_band"]["h"] / 2,
            3,
        )
    if badge_px:
        context["top_badge_zone"] = px_rect_to_inches(badge_px, canvas_px)
    return context


def load_layout_context(learning_path: Path) -> dict[str, Any]:
    return build_layout_context(json.loads(learning_path.read_text(encoding="utf-8")))


def write_js_context(context: dict[str, Any], out_path: Path) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "// Generated from blueprint-image-learning.json. Do not hand-tune slide constants here.",
        "module.exports = Object.freeze(" + json.dumps(context, ensure_ascii=False, indent=2) + ");",
        "",
    ]
    out_path.write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Convert blueprint image learning rules into PPT layout context.")
    parser.add_argument("learning_json", type=Path)
    parser.add_argument("--out-json", type=Path)
    parser.add_argument("--out-js", type=Path)
    args = parser.parse_args()
    context = load_layout_context(args.learning_json)
    output = json.dumps(context, ensure_ascii=False, indent=2) + "\n"
    if args.out_json:
        args.out_json.parent.mkdir(parents=True, exist_ok=True)
        args.out_json.write_text(output, encoding="utf-8")
    if args.out_js:
        write_js_context(context, args.out_js)
    if not args.out_json and not args.out_js:
        print(output, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
