#!/usr/bin/env python3
from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path


def run(*args: str) -> None:
    result = subprocess.run(args, text=True, capture_output=True)
    if result.returncode != 0:
        print(result.stdout)
        print(result.stderr, file=sys.stderr)
        raise SystemExit(result.returncode)
    if result.stdout:
        print(result.stdout.strip())


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    py = sys.executable
    run(py, str(root / "scripts" / "validate_skill.py"), str(root))
    run(py, str(root / "scripts" / "validate_visual_spec.py"), str(root / "assets" / "example-page-spec.json"), "--strict")
    run(py, str(root / "scripts" / "validate_visual_spec.py"), str(root / "assets" / "example-deck-spec.json"), "--strict")
    run(py, str(root / "scripts" / "validate_visual_spec.py"), str(root / "assets" / "example-page-script.md"), "--strict")
    run(py, str(root / "scripts" / "test_domain_neutral_fixtures.py"))
    with tempfile.TemporaryDirectory() as td:
        temp_root = Path(td)
        out = temp_root / "prompt.md"
        run(py, str(root / "scripts" / "build_generation_prompt.py"), str(root / "assets" / "example-deck-spec.json"), "--output", str(out))
        text = out.read_text(encoding="utf-8")
        required = ["[Structural guidance]", "Semantic focus", "Required on-screen body text", "[Style source]"]
        missing = [x for x in required if x not in text]
        if missing:
            raise SystemExit(f"Prompt generation test failed, missing: {missing}")
        forbidden = ["[Style]\n", "- Font:", "- Minimum size equivalent:", "Ivory white and deep blue"]
        leaked = [x for x in forbidden if x in text]
        if leaked:
            raise SystemExit(f"Structure-only prompt leaked style implementation: {leaked}")
        example = json.loads((root / "assets" / "example-page-spec.json").read_text(encoding="utf-8"))
        legacy = dict(example)
        legacy["schema_version"] = "1.0"
        legacy.pop("structural_decision", None)
        legacy["visual_decision"] = dict(legacy["visual_decision"])
        legacy["visual_decision"]["dominant_visual_carrier"] = "legacy compatibility carrier"
        legacy["text_integration"] = dict(legacy["text_integration"])
        legacy["text_integration"]["font_family"] = "legacy sans serif"
        legacy["text_integration"]["minimum_font_pt"] = 14
        legacy_handoff = legacy["generation_handoff"]
        legacy["generation_handoff"] = {
            "composition_guidance": "Legacy composition guidance remains available for compatibility tests.",
            "required_text": list(legacy_handoff["required_text"]),
            "style_guidance": "Legacy external style prose for compatibility only.",
            "negative_constraints": [
                "no equal card wall",
                "no one-icon-per-bullet layout",
                "no disconnected left-text/right-image split",
                "no front-facing portrait",
            ],
            "title_exclusion_instruction": legacy_handoff["title_exclusion_instruction"],
        }
        legacy_path = temp_root / "legacy-v1.json"
        legacy_path.write_text(json.dumps(legacy, ensure_ascii=False, indent=2), encoding="utf-8")
        run(py, str(root / "scripts" / "validate_visual_spec.py"), str(legacy_path), "--strict")

    print("SELF TEST PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
