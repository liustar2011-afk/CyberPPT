from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .project import build_projection
from .validate import validate_projection
from .runtime import run_outline_audit


OUTPUTS = {
    "source_registry": Path("workbench/stages/00-source-map/source-registry.json"),
    "source_units": Path("workbench/stages/00-source-map/source-units.jsonl"),
    "source_heading_tree": Path("workbench/stages/00-source-map/source-heading-tree.json"),
    "semantic_argument_model": Path("workbench/stages/00-semantic-understanding/semantic-argument-model.json"),
    "semantic_understanding_markdown": Path("workbench/stages/00-semantic-understanding/semantic-understanding.md"),
    "source_truth": Path("workbench/stages/01-analysis/source-truth.json"),
    "outline": Path("workbench/stages/01-analysis/outline.json"),
    "outline_review_markdown": Path("workbench/stages/01-analysis/outline-human-review.md"),
    "authority_map": Path("integration/authority-map.json"),
    "report": Path("integration/cyberppt-handoff-report.json"),
}


def _write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def export_projection(
    foundation_dir: Path | str,
    semantic_dir: Path | str,
    outline_dir: Path | str,
    output_dir: Path | str,
    *,
    force: bool = False,
    cyberppt_root: Path | str | None = None,
) -> dict[str, Any]:
    target = Path(output_dir)
    collisions = [target / rel for rel in OUTPUTS.values() if (target / rel).exists()]
    if collisions and not force:
        raise FileExistsError(f"CyberPPT projection already exists: {collisions[0]}")

    projection = build_projection(foundation_dir, semantic_dir, outline_dir)
    validation = validate_projection(projection)
    if validation["status"] != "ok":
        codes = ", ".join(item["code"] for item in validation["errors"])
        raise ValueError(f"CyberPPT projection failed adapter validation: {codes}")

    report = dict(projection["report"])
    report["status"] = "projection_validated"
    report["projection_validation"] = validation
    projection["report"] = report

    for key, rel in OUTPUTS.items():
        if key == "report":
            continue
        path = target / rel
        value = projection[key]
        path.parent.mkdir(parents=True, exist_ok=True)
        if key == "source_units":
            path.write_text("".join(json.dumps(item, ensure_ascii=False, separators=(",", ":")) + "\n" for item in value), encoding="utf-8")
        elif key.endswith("_markdown"):
            path.write_text(str(value), encoding="utf-8")
        else:
            _write_json(path, value)

    if cyberppt_root is not None:
        runtime = run_outline_audit(target, cyberppt_root)
        report["runtime_validation"] = runtime
        report["status"] = "cyberppt_runtime_validated" if runtime.get("status") == "passed" else "cyberppt_runtime_failed"

    report_path = target / OUTPUTS["report"]
    _write_json(report_path, report)
    return report
