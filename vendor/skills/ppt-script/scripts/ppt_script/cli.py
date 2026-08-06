from __future__ import annotations

import hashlib
import json
from datetime import datetime
from pathlib import Path

from .audit import audit_script_text, compare_script_texts
from .config import AuditConfig
from .extractors import extract_project_sources, extract_text
from .pages_index import active_page_files
from .planning import audit_plan_text
from .render import render_audit, render_comparison, render_planning_audit, render_source_inventory, render_speaker_notes_audit
from .script_parser import parse_script
from .source_truth import build_source_inventory, parse_source_truth_map
from .speaker_notes import audit_speaker_notes
from .quality import audit_project_quality, render_quality_report
from .rules import load_rules


def _config(repo_root: Path, config_path: str | Path | None = None, project: Path | None = None) -> AuditConfig:
    path = Path(config_path) if config_path else repo_root / "config/cec-formal.yaml"
    base = AuditConfig.from_yaml(path) if path.exists() else AuditConfig()
    if project is None or not (project / "project.json").exists():
        return base
    meta = json.loads((project / "project.json").read_text(encoding="utf-8"))
    values = {field: getattr(base, field) for field in base.__dataclass_fields__}
    for field in ("speaker_notes_enabled", "speaker_notes_required_for_substantive", "speaker_notes_default_seconds", "target_duration_minutes"):
        values[field] = meta.get(field, values[field])
    return AuditConfig(**values)


def _truth_path(project: Path) -> Path:
    return project / "analysis/01-source-truth-map.md"


def _read_truth(project: Path) -> str:
    path = _truth_path(project)
    if not path.exists():
        raise FileNotFoundError(f"Source Truth Map not found: {path}")
    return path.read_text(encoding="utf-8")


def _read_script(project: Path) -> str:
    pages = active_page_files(project)
    if pages:
        return "\n\n---\n\n".join(path.read_text(encoding="utf-8") for path in pages)
    assembled = project / "output/script-final.md"
    if assembled.exists():
        return assembled.read_text(encoding="utf-8")
    raise FileNotFoundError("No page files or output/script-final.md found")


def source_inventory_command(project: Path) -> Path:
    bundle = extract_project_sources(project)
    inventory = build_source_inventory(bundle.text, file_names=bundle.file_names)
    output = project / "analysis/00-source-inventory.md"
    output.write_text(
        render_source_inventory(
            inventory, bundle.unsupported_files, bundle.low_quality_files, bundle.original_titles
        ),
        encoding="utf-8",
    )
    json_output = project / "analysis/00-source-inventory.json"
    json_output.write_text(
        json.dumps(
            {
                **inventory.to_dict(),
                "unsupported_files": bundle.unsupported_files,
                "low_quality_files": bundle.low_quality_files,
                "original_titles": bundle.original_titles,
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    return output


def plan_check_command(project: Path) -> Path:
    from .workflow import editorial_gate_required

    truth = parse_source_truth_map(_read_truth(project))
    plan_path = project / "outline/02-outline.md"
    if not plan_path.exists():
        raise FileNotFoundError(f"Outline not found: {plan_path}")
    formal = False
    meta_path = project / "project.json"
    if meta_path.is_file():
        try:
            meta = json.loads(meta_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            meta = {}
        if isinstance(meta, dict):
            formal = (
                meta.get("writing_profile") == "government-soe-formal"
                or editorial_gate_required(project)
            )
    plan_bytes = plan_path.read_bytes()
    audit = audit_plan_text(
        plan_bytes.decode("utf-8"),
        truth.required_ids,
        formal_internal_reporting=formal,
    )
    output = project / "outline/02-plan-audit.md"
    output.write_text(render_planning_audit(audit), encoding="utf-8")
    payload = audit.to_dict()
    payload["outline_sha256"] = hashlib.sha256(plan_bytes).hexdigest()
    (project / "outline/02-plan-audit.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return output


def audit_command(project: Path, repo_root: Path, config_path: str | Path | None = None) -> Path:
    bundle = extract_project_sources(project)
    truth_text = _read_truth(project)
    report = audit_script_text(bundle.text, truth_text, _read_script(project), _config(repo_root, config_path, project))
    output = project / "review/05-machine-audit.md"
    output.write_text(render_audit(report), encoding="utf-8")
    (project / "review/05-machine-audit.json").write_text(
        json.dumps(report.to_dict(), ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return output


def notes_check_command(project: Path, repo_root: Path, config_path: str | Path | None = None) -> Path:
    bundle = extract_project_sources(project)
    audit = audit_speaker_notes(bundle.text, parse_script(_read_script(project)), _config(repo_root, config_path, project))
    output = project / "review/06-speaker-notes-audit.md"
    output.write_text(render_speaker_notes_audit(audit), encoding="utf-8")
    output.with_suffix(".json").write_text(json.dumps(audit.to_dict(), ensure_ascii=False, indent=2), encoding="utf-8")
    return output


def quality_check_command(project: Path, repo_root: Path) -> Path:
    report = audit_project_quality(project, load_rules(repo_root / "config/rules.yaml"))
    review = project / "review"
    review.mkdir(parents=True, exist_ok=True)
    output = review / "07-quality-gate.md"
    output.write_text(render_quality_report(report), encoding="utf-8")
    output.with_suffix(".json").write_text(
        json.dumps(report.to_dict(), ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return output


def compare_command(
    project: Path,
    original_path: str | Path,
    revised_path: str | Path,
    repo_root: Path,
    config_path: str | Path | None = None,
) -> Path:
    bundle = extract_project_sources(project)
    truth_text = _read_truth(project)
    original = extract_text(original_path)
    revised = extract_text(revised_path)
    report = compare_script_texts(bundle.text, truth_text, original, revised, _config(repo_root, config_path))
    comparison_dir = project / "comparison"
    comparison_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S-%f")
    output = comparison_dir / f"comparison-{timestamp}.md"
    output.write_text(render_comparison(report), encoding="utf-8")
    output.with_suffix(".json").write_text(
        json.dumps(report.to_dict(), ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return output
