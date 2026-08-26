from __future__ import annotations

import json
from dataclasses import replace
from pathlib import Path

from ..pages_index import active_page_files
from ..config import AuditConfig
from ..formal_style import audit_government_soe_style
from ..render import render_formal_style_audit
from ..report_profiles import resolve_project_reporting_context


def _read_pages(project: Path) -> str:
    pages = active_page_files(project)
    if not pages:
        raise FileNotFoundError(f"No page files found: {project / 'pages'}")
    return "\n\n---\n\n".join(path.read_text(encoding="utf-8") for path in pages)


def style_check_command(
    project: Path,
    repo_root: Path,
    config_path: str | Path | None = None,
) -> Path:
    meta_path = project / "project.json"
    outline_path = project / "outline/02-outline.md"
    if not meta_path.is_file():
        raise FileNotFoundError(f"Project metadata not found: {meta_path}")
    if not outline_path.is_file():
        raise FileNotFoundError(f"Outline not found: {outline_path}")
    meta = json.loads(meta_path.read_text(encoding="utf-8"))
    context = resolve_project_reporting_context(meta, repo_root)
    source = Path(config_path) if config_path else repo_root / "config/government-soe-formal.yaml"
    config = AuditConfig.from_yaml(source)
    config = replace(
        config,
        writing_profile=str(meta.get("writing_profile", config.writing_profile)),
        report_subtype=context.report_subtype,
        decision_intent=context.decision_intent,
        audience_level=context.audience_level,
        project_phase=context.project_phase,
    )
    report = audit_government_soe_style(
        outline_path.read_text(encoding="utf-8"),
        _read_pages(project),
        config,
        repo_root=repo_root,
    )
    output = project / "review/07-government-soe-style-audit.md"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(render_formal_style_audit(report), encoding="utf-8")
    output.with_suffix(".json").write_text(
        json.dumps(report.to_dict(), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return output
