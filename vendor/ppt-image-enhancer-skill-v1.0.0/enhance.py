#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parent
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from ppt_image_enhancer.auto import build_auto_config
from ppt_image_enhancer.pipeline import enhance


def main() -> int:
    p = argparse.ArgumentParser(description="PPT/Image Enhancer Skill — one-command enhancement")
    p.add_argument("input", help="Input image path")
    p.add_argument("-o", "--output", help="Output image path; default: <name>_enhanced.png")
    p.add_argument("--mode", choices=["ppt_page", "chart_heavy", "scene_plus_text", "screenshot"], help="Optional; auto-detected by default")
    p.add_argument("--backend", choices=["auto", "builtin", "realesrgan_ncnn", "realesrgan", "swinir"], default="auto")
    p.add_argument("--scale", type=float, default=2.0, choices=[1.0, 1.5, 2.0, 4.0])
    p.add_argument("--target-size", help="Exact WIDTHxHEIGHT output contract; overrides --scale")
    p.add_argument("--report", help="Optional JSON report path")
    args = p.parse_args()

    src = Path(args.input).expanduser().resolve()
    if not src.exists():
        print(f"Input not found: {src}", file=sys.stderr)
        return 2
    out = Path(args.output).expanduser().resolve() if args.output else src.with_name(src.stem + "_enhanced.png")
    report_path = Path(args.report).expanduser().resolve() if args.report else out.with_suffix(out.suffix + ".report.json")

    cfg, decision = build_auto_config(src, args.mode, args.backend, args.scale)
    if args.target_size:
        try:
            target_width, target_height = (int(value) for value in args.target_size.lower().split("x", 1))
        except (TypeError, ValueError) as exc:
            p.error("--target-size must use WIDTHxHEIGHT")
        cfg.setdefault("output", {})["target_width"] = target_width
        cfg["output"]["target_height"] = target_height
    print(f"[ppt-image-enhancer] mode={decision['selected_mode']} backend={decision['selected_backend']} scale={args.scale}x")
    try:
        result = enhance(src, out, cfg, report_path)
        if result.get("ai_super_resolution_used") and not result.get("quality_gate_valid", True):
            rejected = dict(result)
            print("[ppt-image-enhancer] AI result failed structural fidelity; falling back to builtin.")
            cfg, decision = build_auto_config(src, args.mode, "builtin", args.scale)
            if args.target_size:
                cfg.setdefault("output", {})["target_width"] = target_width
                cfg["output"]["target_height"] = target_height
            result = enhance(src, out, cfg, report_path)
            result["fallback_reason"] = "model_structural_fidelity_failed"
            result["rejected_model_result"] = {
                "backend": rejected.get("super_resolution_backend"),
                "structural_fidelity": rejected.get("structural_fidelity"),
                "warnings": rejected.get("warnings", []),
            }
    except Exception as exc:
        # Auto mode is required to be fail-safe: AI errors fall back to builtin.
        if args.backend == "auto" and decision["selected_backend"] != "builtin":
            print(f"[ppt-image-enhancer] AI backend failed: {exc}")
            print("[ppt-image-enhancer] Falling back to builtin conservative enhancement.")
            cfg, decision = build_auto_config(src, args.mode, "builtin", args.scale)
            if args.target_size:
                cfg.setdefault("output", {})["target_width"] = target_width
                cfg["output"]["target_height"] = target_height
            result = enhance(src, out, cfg, report_path)
        else:
            raise

    result["auto_decision"] = decision
    report_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[ppt-image-enhancer] output: {out}")
    print(f"[ppt-image-enhancer] report: {report_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
