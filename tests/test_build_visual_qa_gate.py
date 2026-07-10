from __future__ import annotations

import json
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_build_visual_qa_gate_writes_top_level_valid_for_quality_registry(tmp_path: Path) -> None:
    diff = tmp_path / "pixel_diff_report.json"
    diff.write_text('{"passed": true, "failures": []}\n', encoding="utf-8")
    out = tmp_path / "visual_qa_gate.json"

    result = subprocess.run(
        [
            "python3",
            str(ROOT / "scripts/build_visual_qa_gate.py"),
            "--slide",
            "3",
            "--blueprint-render",
            "blueprint.png",
            "--ppt-render",
            "ppt.png",
            "--side-by-side",
            "side-by-side.png",
            "--component-signature-check",
            "component_signature.json",
            "--visual-element-registry",
            "visual_registry.json",
            "--bbox-delta-report",
            "bbox_delta.json",
            "--overlay-comparison",
            "overlay.png",
            "--pixel-diff-report",
            str(diff),
            "--delivery-mode",
            "dual_image_editable_overlay",
            "--out",
            str(out),
        ],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, result.stdout + result.stderr
    payload = json.loads(out.read_text(encoding="utf-8"))
    assert payload["schema"] == "cyberppt.visual_qa_gate.v1"
    assert payload["valid"] is True
    assert payload["deliverable_allowed"] is True
    assert payload["slides"][0]["deliverable_allowed"] is True
