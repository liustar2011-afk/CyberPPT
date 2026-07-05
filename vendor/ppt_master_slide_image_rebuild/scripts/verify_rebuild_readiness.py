#!/usr/bin/env python3
"""
PPT Master - Rebuild Readiness Verifier

Verify hard workflow gates for layout-reference-rebuild projects before
Strategist, Executor, export, or final QA steps.

Usage:
    python3 scripts/verify_rebuild_readiness.py <project_path> [--stage final]

Examples:
    python3 scripts/verify_rebuild_readiness.py projects/demo --stage pre-strategist
    python3 scripts/verify_rebuild_readiness.py projects/demo --stage final

Dependencies:
    None (only uses standard library)
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from xml.etree import ElementTree as ET

SVG_NS = "{http://www.w3.org/2000/svg}"
XLINK_HREF = "{http://www.w3.org/1999/xlink}href"

STAGE_ORDER = {
    "pre-strategist": 1,
    "pre-executor": 2,
    "pre-export": 3,
    "final": 4,
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


def _strip_ns(tag: str) -> str:
    return tag.replace(SVG_NS, "")


def _load_json(path: Path) -> dict[str, Any]:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}


def _run_json(cmd: list[str]) -> dict[str, Any]:
    result = subprocess.run(cmd, text=True, capture_output=True, check=False)
    if result.stdout.strip():
        try:
            payload = json.loads(result.stdout)
        except json.JSONDecodeError:
            payload = {"valid": False, "errors": [result.stdout.strip()]}
    else:
        payload = {"valid": result.returncode == 0, "errors": []}
    if result.stderr.strip():
        payload.setdefault("stderr", result.stderr.strip())
    return payload


def _append_tool_findings(
    findings: list[Finding],
    *,
    tool: str,
    path: Path,
    result: dict[str, Any],
) -> None:
    errors = result.get("errors", [])
    warnings = result.get("warnings", [])
    for item in errors if isinstance(errors, list) else [str(errors)]:
        findings.append(Finding("error", f"{tool}_error", str(item), str(path)))
    for item in warnings if isinstance(warnings, list) else [str(warnings)]:
        findings.append(Finding("warning", f"{tool}_warning", str(item), str(path)))


def _require_file(findings: list[Finding], path: Path, code: str, message: str) -> bool:
    if path.exists():
        return True
    findings.append(Finding("error", code, message, str(path)))
    return False


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


def _svg_files(project: Path) -> list[Path]:
    final_files = sorted((project / "svg_final").glob("*.svg"))
    output_files = sorted((project / "svg_output").glob("*.svg"))
    return final_files or output_files


def _stage_at_least(stage: str, target: str) -> bool:
    return STAGE_ORDER[stage] >= STAGE_ORDER[target]


def _is_rebuild2_project(project: Path) -> bool:
    layout = _load_json(project / "layout_reference.json")
    if not layout:
        return False
    try:
        from layout_reference_rebuild2_lib import is_rebuild2
    except ImportError:
        from scripts.layout_reference_rebuild2_lib import is_rebuild2  # type: ignore
    return is_rebuild2(layout)


def _check_pre_strategist(project: Path, findings: list[Finding], *, rebuild2: bool = False) -> None:
    script_dir = Path(__file__).resolve().parent
    layout = project / "layout_reference.json"
    mapping = project / "content_mapping.json"
    use_rebuild2 = rebuild2 or _is_rebuild2_project(project)

    if _require_file(findings, layout, "missing_layout_reference", "layout_reference.json is required before Strategist."):
        cmd = [sys.executable, str(script_dir / "validate_layout_reference.py"), str(layout)]
        if use_rebuild2:
            cmd.append("--rebuild2")
            if mapping.exists():
                cmd.extend(["--mapping", str(mapping)])
        result = _run_json(cmd)
        _append_tool_findings(findings, tool="validate_layout_reference", path=layout, result=result)

        # Soft Phase-A coherence advisory (facts↔zones drift, confidence, contract,
        # geometric constraints). Low confidence should prompt human review, not
        # hard-block Strategist, so its errors are surfaced as warnings here.
        lu = _run_json([sys.executable, str(script_dir / "verify_layout_understanding.py"), str(project)])
        lu_soft = {
            "warnings": list(lu.get("warnings", []))
            + [f"(coherence) {item}" for item in lu.get("errors", [])],
        }
        _append_tool_findings(findings, tool="verify_layout_understanding", path=layout, result=lu_soft)

        data = _load_json(layout)
        source = data.get("source_reference", {}) if isinstance(data, dict) else {}
        if isinstance(source, dict) and source.get("copy_text_from_reference") is True:
            findings.append(Finding(
                "warning",
                "reference_text_trusted",
                "Reference text is marked copyable; confirm the user explicitly authorized it.",
                str(layout),
            ))

    if _require_file(findings, mapping, "missing_content_mapping", "content_mapping.json is required before Strategist."):
        result = _run_json([
            sys.executable,
            str(script_dir / "validate_content_mapping.py"),
            str(mapping),
            "--layout",
            str(layout),
        ])
        _append_tool_findings(findings, tool="validate_content_mapping", path=mapping, result=result)

    source_dir = project / "sources"
    source_files = [path for path in source_dir.glob("*") if path.is_file()] if source_dir.is_dir() else []
    if not source_files:
        findings.append(Finding(
            "warning",
            "missing_formal_sources",
            "No files found in sources/. If content came only from chat, document that in README or content_mapping terminology_notes.",
            str(source_dir),
        ))

    for path, code, message in [
        (project / "layout_reference_brief.md", "missing_bridge_brief", "layout_reference_brief.md should be generated before Strategist."),
        (project / "svg_build_plan.json", "missing_svg_build_plan_json", "svg_build_plan.json should be generated before Strategist."),
        (project / "svg_build_plan.md", "missing_svg_build_plan_md", "svg_build_plan.md should be generated before Strategist."),
    ]:
        _require_file(findings, path, code, message)


def _check_pre_executor(project: Path, findings: list[Finding], *, rebuild2: bool = False) -> None:
    _require_file(
        findings,
        project / "design_spec.md",
        "missing_design_spec",
        "design_spec.md is required before Executor. For slide-image rebuilds, run "
        "`python3 scripts/layout_reference_to_design_spec.py <project_path> --write-design-spec`.",
    )
    spec_lock = project / "spec_lock.md"
    if _require_file(findings, spec_lock, "missing_spec_lock", "spec_lock.md is required before Executor."):
        text = spec_lock.read_text(encoding="utf-8", errors="ignore")
        for token in ["page_rhythm", "page_layouts", "page_charts"]:
            if token not in text:
                findings.append(Finding(
                    "warning",
                    f"spec_lock_missing_{token}",
                    f"spec_lock.md should explicitly contain {token} so per-page SVG generation cannot drift.",
                    str(spec_lock),
                ))

    gen_script = project / "_gen.py"
    if gen_script.exists():
        message = (
            "_gen.py is present; confirm this is an intentional UTF-8 SVG writer and not a cross-page batch generator."
        )
        if rebuild2:
            message = (
                "_gen.py may only write SVG with encoding=utf-8; it does not replace Executor visual review. "
                "Open images/reference_layout.png while editing; pre-export requires "
                "verify_reference_similarity.py against exports/preview_qa/*.preview.png."
            )
        findings.append(Finding(
            "warning",
            "generator_script_present",
            message,
            str(gen_script),
        ))

    master_candidates = [
        project / "templates" / "master_elements.svg",
        project / "templates" / "brand" / "master_elements.svg",
    ]
    master_candidates.extend(sorted((project / "templates").glob("*/master_elements.svg")))
    if any(path.exists() for path in master_candidates) and not (project / "chrome_dedup_report.md").exists():
        findings.append(Finding(
            "warning",
            "missing_chrome_dedup_report",
            "Template master chrome is present; run verify_chrome_dedup.py before Executor removes or keeps reference chrome.",
            str(project / "chrome_dedup_report.md"),
        ))


def _check_svg_raster_policy(project: Path, findings: list[Finding]) -> None:
    layout = _load_json(project / "layout_reference.json")
    image_allowed = set()
    policy = layout.get("editability_policy", {}) if isinstance(layout, dict) else {}
    if isinstance(policy, dict):
        raw_allowed = policy.get("image_allowed", [])
        if isinstance(raw_allowed, list):
            image_allowed = {str(item) for item in raw_allowed}

    for svg in _svg_files(project):
        try:
            root = ET.parse(svg).getroot()
        except ET.ParseError as exc:
            findings.append(Finding("error", "svg_parse_error", f"Cannot parse SVG: {exc}", str(svg)))
            continue
        view_box = root.get("viewBox", "").split()
        try:
            canvas_w = float(view_box[2])
            canvas_h = float(view_box[3])
        except (IndexError, ValueError):
            canvas_w = 1280.0
            canvas_h = 720.0
        for image in root.iter():
            if _strip_ns(image.tag) != "image":
                continue
            href = image.get("href") or image.get(XLINK_HREF) or ""
            zone_id = image.get("data-zone-id") or image.get("data-layout-zone") or ""
            try:
                width = float(image.get("width", "0"))
                height = float(image.get("height", "0"))
            except ValueError:
                width = 0
                height = 0
            area_ratio = (width * height) / max(canvas_w * canvas_h, 1)
            if area_ratio >= 0.85:
                findings.append(Finding(
                    "error",
                    "full_slide_raster_image",
                    "SVG contains a near-full-slide raster image; rebuild should use editable elements, not a flattened reference image.",
                    str(svg),
                ))
            elif href and zone_id and image_allowed and zone_id not in image_allowed:
                findings.append(Finding(
                    "warning",
                    "raster_zone_not_allowed",
                    f"Raster image in zone `{zone_id}` is not listed in editability_policy.image_allowed.",
                    str(svg),
                ))


def _check_pre_export(project: Path, findings: list[Finding], *, rebuild2: bool = False) -> None:
    script_dir = Path(__file__).resolve().parent
    svg_files = _svg_files(project)
    if not svg_files:
        findings.append(Finding("error", "missing_svg_pages", "No SVG pages found in svg_final/ or svg_output/."))
        return
    _check_svg_raster_policy(project, findings)
    for tool in ["verify_text_fit.py", "verify_svg_spacing.py"]:
        result = _run_json([sys.executable, str(script_dir / tool), str(project)])
        if not result.get("valid", result.get("ok", False)):
            _append_nested_results(findings, tool.replace(".py", ""), result)
    layout = project / "layout_reference.json"
    use_rebuild2 = rebuild2 or _is_rebuild2_project(project)
    if use_rebuild2:
        result = _run_json([
            sys.executable,
            str(script_dir / "verify_layout_executor_contract.py"),
            str(project),
        ])
        _append_tool_findings(findings, tool="verify_layout_executor_contract", path=project, result=result)
    if layout.exists():
        for svg in svg_files:
            icon_cmd = [
                sys.executable,
                str(script_dir / "verify_icon_text_fit.py"),
                str(layout),
                "--svg",
                str(svg),
            ]
            if use_rebuild2:
                icon_cmd.append("--strict")
            result = _run_json(icon_cmd)
            if not result.get("valid", False):
                _append_tool_findings(findings, tool="verify_icon_text_fit", path=svg, result=result)
    if use_rebuild2:
        try:
            from render_backend_resolve_lib import resolve_project_render_backend
        except ImportError:  # pragma: no cover
            from scripts.render_backend_resolve_lib import resolve_project_render_backend  # type: ignore
        render_backend, _backend_warnings = resolve_project_render_backend(project, hard_gate=True)
        similarity_cmd = [
            sys.executable,
            str(script_dir / "verify_reference_similarity.py"),
            str(project),
            "--render",
            "--render-backend",
            render_backend,
            "--hard-gate",
        ]
        result = _run_json(similarity_cmd)
        _append_tool_findings(
            findings,
            tool="verify_reference_similarity",
            path=project,
            result=result,
        )


def _append_nested_results(findings: list[Finding], tool: str, result: dict[str, Any]) -> None:
    nested = result.get("results")
    if isinstance(nested, list):
        for item in nested:
            if not isinstance(item, dict):
                continue
            path = str(item.get("path", ""))
            for error in item.get("errors", []) or []:
                findings.append(Finding("error", f"{tool}_error", str(error), path))
            for warning in item.get("warnings", []) or []:
                findings.append(Finding("warning", f"{tool}_warning", str(warning), path))
        return
    _append_tool_findings(findings, tool=tool, path=Path(""), result=result)


def _check_final(project: Path, findings: list[Finding]) -> None:
    script_dir = Path(__file__).resolve().parent
    pptx = _latest_pptx(project)
    if not pptx:
        findings.append(Finding("error", "missing_exported_pptx", "No exported PPTX found in exports/."))
    else:
        result = _run_json([sys.executable, str(script_dir / "verify_editable_pptx.py"), str(pptx)])
        _append_tool_findings(findings, tool="verify_editable_pptx", path=pptx, result=result)
    qa_report = project / "qa_report.md"
    if not qa_report.exists():
        findings.append(Finding(
            "warning",
            "missing_qa_report",
            "qa_report.md has not been generated; run generate_rebuild_qa_report.py after export.",
            str(qa_report),
        ))


def verify_project(project: Path, *, stage: str, rebuild2: bool = False) -> dict[str, Any]:
    findings: list[Finding] = []
    if not project.exists():
        findings.append(Finding("error", "missing_project", "Project path does not exist.", str(project)))
    elif not project.is_dir():
        findings.append(Finding("error", "project_not_directory", "Project path is not a directory.", str(project)))
    else:
        use_rebuild2 = rebuild2 or _is_rebuild2_project(project)
        _check_pre_strategist(project, findings, rebuild2=use_rebuild2)
        if _stage_at_least(stage, "pre-executor"):
            _check_pre_executor(project, findings, rebuild2=use_rebuild2)
        if _stage_at_least(stage, "pre-export"):
            _check_pre_export(project, findings, rebuild2=use_rebuild2)
        if _stage_at_least(stage, "final"):
            _check_final(project, findings)

    errors = [finding for finding in findings if finding.level == "error"]
    warnings = [finding for finding in findings if finding.level == "warning"]
    return {
        "valid": not errors,
        "stage": stage,
        "project": str(project),
        "errors": [finding.as_dict() for finding in errors],
        "warnings": [finding.as_dict() for finding in warnings],
        "summary": {
            "error_count": len(errors),
            "warning_count": len(warnings),
        },
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Verify layout-reference-rebuild workflow gates.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("project_path", type=Path, help="Project directory")
    parser.add_argument(
        "--stage",
        choices=sorted(STAGE_ORDER),
        default="final",
        help="Gate depth to verify",
    )
    parser.add_argument(
        "--rebuild2",
        action="store_true",
        help="Apply 复刻流程2 strict gates (structure contract + executor contract)",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    payload = verify_project(args.project_path, stage=args.stage, rebuild2=args.rebuild2)
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0 if payload["valid"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
