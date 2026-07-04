#!/usr/bin/env python3
"""
PPT Master - Slide Image Rebuild Manifest Verifier

Validate the multi-page slide-image-rebuild manifest and, by stage, the
per-page artifacts it points to. This keeps page-folder rebuilds from silently
falling back to single-page root artifacts.

Usage:
    python3 scripts/verify_slide_image_rebuild_manifest.py <project_path> --stage intake
    python3 scripts/verify_slide_image_rebuild_manifest.py <project_path> --stage export

Dependencies:
    None (only uses standard library; delegated validators are repository scripts)
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

try:
    from rebuild_quality_mode import resolve_rebuild_modes
except ImportError:  # pragma: no cover
    from scripts.rebuild_quality_mode import resolve_rebuild_modes  # type: ignore

try:
    from slide_image_rebuild_manifest_lib import resolve_text_granularity, resolve_text_layout_policy
except ImportError:  # pragma: no cover
    from scripts.slide_image_rebuild_manifest_lib import (  # type: ignore
        resolve_text_granularity,
        resolve_text_layout_policy,
    )

REBUILD_MODES = {
    "vector-hifi",
    "text-editable-snapshot",
    "full-editable",
    "hifi",
    "editable",
    "wps-hifi",
}

PPTX_EXPORT_MODES = {
    "hifi",
    "editable",
    "wps-hifi",
}

STAGE_ORDER = {
    "intake": 1,
    "extracted": 2,
    "mapped": 3,
    "svg": 4,
    "export": 5,
}


@dataclass
class Finding:
    level: str
    code: str
    message: str
    path: str = ""

    def as_dict(self) -> dict[str, str]:
        payload = {
            "level": self.level,
            "code": self.code,
            "message": self.message,
        }
        if self.path:
            payload["path"] = self.path
        return payload


def _load_json(path: Path) -> dict[str, Any]:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}


def _run_json(cmd: list[str]) -> tuple[int, dict[str, Any]]:
    result = subprocess.run(cmd, text=True, capture_output=True, check=False)
    if result.stdout.strip():
        try:
            payload = json.loads(result.stdout)
        except json.JSONDecodeError:
            payload = {"valid": result.returncode == 0, "stdout": result.stdout.strip()}
    else:
        payload = {"valid": result.returncode == 0}
    if result.stderr.strip():
        payload["stderr"] = result.stderr.strip()
    payload["returncode"] = result.returncode
    return result.returncode, payload


def _append_tool_findings(
    findings: list[Finding],
    *,
    tool: str,
    path: Path,
    payload: dict[str, Any],
) -> None:
    for item in payload.get("errors", []) if isinstance(payload.get("errors"), list) else []:
        if isinstance(item, dict):
            findings.append(Finding(
                "error",
                str(item.get("code", f"{tool}_error")),
                str(item.get("message", item)),
                str(item.get("path", path)),
            ))
        else:
            findings.append(Finding("error", f"{tool}_error", str(item), str(path)))
    for item in payload.get("warnings", []) if isinstance(payload.get("warnings"), list) else []:
        if isinstance(item, dict):
            findings.append(Finding(
                "warning",
                str(item.get("code", f"{tool}_warning")),
                str(item.get("message", item)),
                str(item.get("path", path)),
            ))
        else:
            findings.append(Finding("warning", f"{tool}_warning", str(item), str(path)))


def _stage_at_least(stage: str, target: str) -> bool:
    return STAGE_ORDER[stage] >= STAGE_ORDER[target]


def _resolve_project_path(project: Path, raw: Any) -> Path | None:
    if not isinstance(raw, str) or not raw.strip():
        return None
    path = Path(raw)
    if not path.is_absolute():
        path = project / path
    return path.resolve()


def _page_dir(project: Path, page: dict[str, Any]) -> Path:
    for key in ["project_path", "page_project", "page_dir"]:
        resolved = _resolve_project_path(project, page.get(key))
        if resolved is not None:
            return resolved
    page_id = str(page.get("page_id", ""))
    candidate = project / "pages" / page_id
    return candidate if candidate.is_dir() else project


def _artifact(page_dir: Path, page: dict[str, Any], key: str, default_name: str) -> Path:
    raw = page.get(key)
    if isinstance(raw, str) and raw.strip():
        path = Path(raw)
        if not path.is_absolute():
            path = page_dir / path
        return path.resolve()
    return page_dir / default_name


def _latest_pptx(project: Path) -> Path | None:
    exports = project / "exports"
    if not exports.is_dir():
        return None
    pptxs = sorted(
        (path for path in exports.glob("*.pptx") if not path.name.startswith("~$")),
        key=lambda path: path.stat().st_mtime,
        reverse=True,
    )
    return pptxs[0] if pptxs else None


def _matching_svg_files(project: Path, page_dir: Path, page_id: str) -> list[Path]:
    candidates: list[Path] = []
    for root in [page_dir, project]:
        for folder in ["svg_output", "svg_final"]:
            svg_dir = root / folder
            if not svg_dir.is_dir():
                continue
            candidates.extend(sorted(svg_dir.glob(f"{page_id}*.svg")))
    return candidates


def _preferred_page_id(page_id: str) -> bool:
    return bool(re.fullmatch(r"P\d{2,3}", page_id))


def _exact_svg_exists(project: Path, page_dir: Path, page_id: str) -> bool:
    return any(
        (root / "svg_output" / f"{page_id}.svg").is_file()
        or (root / "svg_final" / f"{page_id}.svg").is_file()
        for root in [page_dir, project]
    )


def _notes_headings(path: Path) -> set[str]:
    if not path.is_file():
        return set()
    headings: set[str] = set()
    for line in path.read_text(encoding="utf-8", errors="ignore").splitlines():
        stripped = line.strip()
        if stripped.startswith("# "):
            headings.add(stripped[2:].strip())
    return headings


def _check_modes(project: Path, manifest: dict[str, Any], findings: list[Finding]) -> None:
    path = str(project / "slide_image_rebuild_manifest.json")
    resolved = resolve_rebuild_modes(manifest)
    for code, message in zip(resolved.error_codes, resolved.errors, strict=True):
        findings.append(Finding("error", code, message, path))
    for message in resolved.warnings:
        findings.append(Finding("warning", "rebuild_quality_mode_warning", message, path))

    text_resolved = resolve_text_granularity(manifest)
    for code, message in zip(text_resolved.error_codes, text_resolved.errors, strict=True):
        findings.append(Finding("error", code, message, path))
    for message in text_resolved.warnings:
        findings.append(Finding("warning", "text_granularity_warning", message, path))

    layout_policy_resolved = resolve_text_layout_policy(manifest)
    for code, message in zip(layout_policy_resolved.error_codes, layout_policy_resolved.errors, strict=True):
        findings.append(Finding("error", code, message, path))
    for message in layout_policy_resolved.warnings:
        findings.append(Finding("warning", "text_layout_policy_warning", message, path))

    rebuild_mode = resolved.rebuild_mode or manifest.get("rebuild_mode")
    export_mode = resolved.pptx_export_mode or manifest.get("pptx_export_mode")
    legacy_mode = manifest.get("mode")
    if legacy_mode and (not rebuild_mode or not export_mode):
        findings.append(Finding(
            "error",
            "legacy_ambiguous_mode",
            "Use explicit rebuild_mode and pptx_export_mode; a single `mode` field is ambiguous.",
            path,
        ))
    if rebuild_mode not in REBUILD_MODES:
        findings.append(Finding(
            "error",
            "invalid_rebuild_mode",
            f"rebuild_mode must be one of: {', '.join(sorted(REBUILD_MODES))}.",
            path,
        ))
    if export_mode not in PPTX_EXPORT_MODES:
        findings.append(Finding(
            "error",
            "invalid_pptx_export_mode",
            f"pptx_export_mode must be one of: {', '.join(sorted(PPTX_EXPORT_MODES))}.",
            path,
        ))


def _check_intake_soft(project: Path, manifest: dict[str, Any], findings: list[Finding]) -> None:
    path = str(project / "slide_image_rebuild_manifest.json")
    intake = manifest.get("intake", {})
    if not isinstance(intake, dict):
        return
    preprocess = intake.get("preprocess", {})
    if isinstance(preprocess, dict) and preprocess.get("enabled") is True:
        meta_rel = str(preprocess.get("meta_json", "images/source_meta.json")).strip() or "images/source_meta.json"
        meta_path = project / meta_rel
        if not meta_path.is_file():
            findings.append(Finding(
                "warning",
                "preprocess_meta_missing",
                "intake.preprocess.enabled is true but source_meta.json is missing; run preprocess_reference_image.py.",
                str(meta_path),
            ))
    precrop = intake.get("precrop_candidates", {})
    if isinstance(precrop, dict) and precrop.get("enabled") is True:
        out_rel = str(precrop.get("output_dir", "images/precrops")).strip() or "images/precrops"
        out_dir = project / out_rel
        layout = _load_json(project / "layout_reference.json")
        enabled = [
            item for item in layout.get("crop_candidates", [])
            if isinstance(item, dict)
            and isinstance(item.get("precrop"), dict)
            and item["precrop"].get("enabled") is True
        ]
        if enabled and not any(out_dir.glob("*.png")):
            findings.append(Finding(
                "warning",
                "precrop_pngs_pending",
                "intake.precrop_candidates.enabled is true but no PNG precrops found; run precrop_layout_candidates.py.",
                str(out_dir),
            ))


def _is_slide_image_rebuild(manifest: dict[str, Any]) -> bool:
    return manifest.get("workflow") == "slide-image-rebuild"


def _requires_rebuild2(manifest: dict[str, Any]) -> bool:
    """Whether this manifest must use the v2.0 / 复刻流程2 layout_reference schema.

    text-editable-snapshot is the documented exception: it has no vector
    structure to describe (no zones/icons/structure_contract to vector-rebuild),
    so forcing it through the heavyweight rebuild2 schema would be pointless --
    it's already gated on manifest.user_acceptance in resolve_rebuild_modes().
    """
    if not _is_slide_image_rebuild(manifest):
        return False
    resolved = resolve_rebuild_modes(manifest)
    rebuild_mode = resolved.rebuild_mode or manifest.get("rebuild_mode")
    return rebuild_mode != "text-editable-snapshot"


def _check_page_artifacts(
    project: Path,
    page: dict[str, Any],
    *,
    stage: str,
    manifest: dict[str, Any],
    findings: list[Finding],
) -> dict[str, Any]:
    script_dir = Path(__file__).resolve().parent
    page_id = str(page.get("page_id", "")).strip()
    page_dir = _page_dir(project, page)
    summary: dict[str, Any] = {
        "page_id": page_id,
        "page_dir": str(page_dir),
        "artifacts": {},
    }

    if not page_id:
        findings.append(Finding("error", "missing_page_id", "Manifest page entry needs a non-empty page_id."))
        return summary

    reference = _resolve_project_path(project, page.get("reference_image"))
    summary["reference_image"] = str(reference) if reference else ""
    if reference is None or not reference.is_file():
        findings.append(Finding(
            "error",
            "missing_reference_image",
            f"Page `{page_id}` reference_image does not exist.",
            str(reference or project / "slide_image_rebuild_manifest.json"),
        ))

    layout = _artifact(page_dir, page, "layout_reference", "layout_reference.json")
    mapping = _artifact(page_dir, page, "content_mapping", "content_mapping.json")
    summary["artifacts"]["layout_reference"] = str(layout)
    summary["artifacts"]["content_mapping"] = str(mapping)

    if _stage_at_least(stage, "extracted"):
        if not layout.is_file():
            findings.append(Finding("error", "missing_layout_reference", f"Page `{page_id}` needs layout_reference.json.", str(layout)))
        else:
            layout_data = _load_json(layout)
            if _requires_rebuild2(manifest):
                if layout_data.get("version") != "2.0":
                    findings.append(Finding(
                        "error",
                        "layout_reference_not_v2",
                        f"Page `{page_id}` layout_reference.json must have version 2.0 for slide-image-rebuild.",
                        str(layout),
                    ))
                if layout_data.get("workflow") != "layout-reference-rebuild-2":
                    findings.append(Finding(
                        "error",
                        "layout_reference_workflow_not_v2",
                        f"Page `{page_id}` layout_reference.json workflow must be layout-reference-rebuild-2.",
                        str(layout),
                    ))
                if not isinstance(layout_data.get("structure_contract"), dict):
                    findings.append(Finding(
                        "error",
                        "layout_reference_missing_structure_contract",
                        f"Page `{page_id}` layout_reference.json must include structure_contract.",
                        str(layout),
                    ))
            cmd = [sys.executable, str(script_dir / "validate_layout_reference.py"), str(layout)]
            use_rebuild2 = (
                _requires_rebuild2(manifest)
                or layout_data.get("workflow") == "layout-reference-rebuild-2"
                or layout_data.get("version") == "2.0"
            )
            if use_rebuild2:
                cmd.append("--rebuild2")
                if mapping.is_file():
                    cmd.extend(["--mapping", str(mapping)])
            _code, payload = _run_json(cmd)
            _append_tool_findings(findings, tool="validate_layout_reference", path=layout, payload=payload)
            for warning in payload.get("warnings", []) if isinstance(payload.get("warnings"), list) else []:
                if isinstance(warning, str):
                    findings.append(Finding("warning", "validate_layout_reference_warning", warning, str(layout)))

    if _stage_at_least(stage, "mapped"):
        if not mapping.is_file():
            findings.append(Finding("error", "missing_content_mapping", f"Page `{page_id}` needs content_mapping.json.", str(mapping)))
        else:
            cmd = [sys.executable, str(script_dir / "validate_content_mapping.py"), str(mapping)]
            if layout.is_file():
                cmd.extend(["--layout", str(layout)])
            _code, payload = _run_json(cmd)
            _append_tool_findings(findings, tool="validate_content_mapping", path=mapping, payload=payload)

    if _stage_at_least(stage, "svg"):
        text_map = _artifact(page_dir, page, "text_region_map", "text_region_map.json")
        if not text_map.is_file() and page_dir != project:
            text_map = project / "text_region_map.json"
        summary["artifacts"]["text_region_map"] = str(text_map)
        if not text_map.is_file():
            findings.append(Finding("error", "missing_text_region_map", f"Page `{page_id}` needs text_region_map.json.", str(text_map)))
        svg_files = _matching_svg_files(project, page_dir, page_id)
        summary["artifacts"]["svg_files"] = [str(path) for path in svg_files]
        if not svg_files:
            findings.append(Finding("error", "missing_page_svg", f"Page `{page_id}` has no matching SVG in svg_output/ or svg_final.", str(page_dir)))

    return summary


def verify_project(project: Path, *, stage: str = "intake") -> dict[str, Any]:
    findings: list[Finding] = []
    manifest_path = project / "slide_image_rebuild_manifest.json"
    manifest = _load_json(manifest_path)
    if not manifest:
        findings.append(Finding(
            "error",
            "missing_manifest",
            "slide_image_rebuild_manifest.json is required for slide-image rebuild projects.",
            str(manifest_path),
        ))
        return _payload(project, stage, findings, [], {})

    if manifest.get("workflow") != "slide-image-rebuild":
        findings.append(Finding(
            "warning",
            "manifest_workflow_unset",
            "Set workflow to `slide-image-rebuild` for clarity.",
            str(manifest_path),
        ))
    _check_modes(project, manifest, findings)
    if stage == "intake":
        _check_intake_soft(project, manifest, findings)

    pages = manifest.get("pages", [])
    if not isinstance(pages, list) or not pages:
        findings.append(Finding("error", "missing_pages", "Manifest pages must be a non-empty list.", str(manifest_path)))
        return _payload(project, stage, findings, [], manifest)

    seen_page_ids: set[str] = set()
    page_summaries: list[dict[str, Any]] = []
    root_page_count = 0
    ordered_page_ids: list[str] = []
    for page in pages:
        if not isinstance(page, dict):
            findings.append(Finding("error", "invalid_page_entry", "Each manifest page entry must be an object.", str(manifest_path)))
            continue
        page_id = str(page.get("page_id", "")).strip()
        if page_id in seen_page_ids:
            findings.append(Finding("error", "duplicate_page_id", f"Duplicate page_id `{page_id}`.", str(manifest_path)))
        if page_id:
            seen_page_ids.add(page_id)
            ordered_page_ids.append(page_id)
            if not _preferred_page_id(page_id):
                findings.append(Finding(
                    "warning",
                    "non_protocol_page_id",
                    f"Page id `{page_id}` works, but the multi-page protocol prefers P01/P02-style ids.",
                    str(manifest_path),
                ))
        page_dir = _page_dir(project, page)
        if page_dir == project:
            root_page_count += 1
        page_summaries.append(_check_page_artifacts(project, page, stage=stage, manifest=manifest, findings=findings))
        if page_id and _stage_at_least(stage, "svg") and not _exact_svg_exists(project, page_dir, page_id):
            findings.append(Finding(
                "warning",
                "non_protocol_svg_name",
                f"Page `{page_id}` has matching SVG files, but the protocol prefers svg_output/{page_id}.svg.",
                str(page_dir),
            ))

    if len(pages) > 1 and root_page_count == len(pages):
        findings.append(Finding(
            "warning",
            "multi_page_without_page_dirs",
            "Multiple pages all resolve to the project root; use pages/Pxx/ or explicit page_dir entries to avoid artifact collisions.",
            str(manifest_path),
        ))

    if _stage_at_least(stage, "export"):
        for path, code, message in [
            (project / "image_crops_manifest.json", "missing_image_crops_manifest", "Run build_image_crops_manifest.py before export QA."),
            (project / "notes" / "total.md", "missing_total_notes", "notes/total.md is required before export."),
            (project / "exports" / "qa" / "repair_tasks.json", "missing_repair_tasks", "Run aggregate_repair_tasks.py --write-report before export."),
        ]:
            if not path.is_file():
                findings.append(Finding("error", code, message, str(path)))
        repair_tasks = _load_json(project / "exports" / "qa" / "repair_tasks.json")
        if repair_tasks and repair_tasks.get("blocking_open_count", 0):
            findings.append(Finding(
                "error",
                "open_repair_tasks",
                f"repair_tasks.json has {repair_tasks.get('blocking_open_count')} open blocking task(s).",
                str(project / "exports" / "qa" / "repair_tasks.json"),
            ))
        if _latest_pptx(project) is None:
            findings.append(Finding("error", "missing_exported_pptx", "No exported PPTX found in exports/.", str(project / "exports")))
        if len(ordered_page_ids) > 1:
            notes_path = project / "notes" / "total.md"
            headings = _notes_headings(notes_path)
            missing_notes = [page_id for page_id in ordered_page_ids if page_id not in headings]
            for page_id in missing_notes:
                findings.append(Finding(
                    "error",
                    "missing_page_notes_heading",
                    f"Multi-page notes/total.md must contain `# {page_id}`.",
                    str(notes_path),
                ))

    return _payload(project, stage, findings, page_summaries, manifest)


def _payload(
    project: Path,
    stage: str,
    findings: list[Finding],
    pages: list[dict[str, Any]],
    manifest: dict[str, Any],
) -> dict[str, Any]:
    errors = [finding.as_dict() for finding in findings if finding.level == "error"]
    warnings = [finding.as_dict() for finding in findings if finding.level == "warning"]
    resolved = resolve_rebuild_modes(manifest)
    effective_rebuild = resolved.rebuild_mode or manifest.get("rebuild_mode", "")
    effective_export = resolved.pptx_export_mode or manifest.get("pptx_export_mode", "")
    return {
        "workflow": "slide-image-rebuild",
        "version": "1.0",
        "project": str(project),
        "stage": stage,
        "valid": not errors,
        "errors": errors,
        "warnings": warnings,
        "rebuild_mode": effective_rebuild,
        "pptx_export_mode": effective_export,
        "rebuild_quality_mode": manifest.get("rebuild_quality_mode", ""),
        "resolved_from_quality_mode": resolved.resolved_from_quality_mode,
        "pages": pages,
        "summary": {
            "page_count": len(pages),
            "error_count": len(errors),
            "warning_count": len(warnings),
        },
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Verify slide-image rebuild manifest and staged page artifacts.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("project_path", type=Path, help="Project directory")
    parser.add_argument(
        "--stage",
        choices=sorted(STAGE_ORDER),
        default="intake",
        help="Artifact depth to verify",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    project = args.project_path.resolve()
    if not project.is_dir():
        payload = {
            "valid": False,
            "errors": [{
                "level": "error",
                "code": "missing_project",
                "message": f"Project directory not found: {project}",
                "path": str(project),
            }],
            "warnings": [],
        }
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return 1
    payload = verify_project(project, stage=args.stage)
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0 if payload["valid"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
