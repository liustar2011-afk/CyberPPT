#!/usr/bin/env python3
"""
PPT Master - Mode-Aware Rebuild Regression Verifier

Aggregate the existing slide-image rebuild QA checks into one mode-aware report.

Usage:
    python3 scripts/verify_rebuild_regression.py <project_path> --mode auto

Examples:
    python3 scripts/verify_rebuild_regression.py projects/demo --mode vector-hifi
    python3 scripts/verify_rebuild_regression.py projects/demo --mode wps-hifi --render

Dependencies:
    None (only uses standard library; delegated tools may require their own deps)
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from zipfile import BadZipFile, ZipFile

try:
    from rebuild_quality_mode import resolve_rebuild_modes
except ImportError:  # pragma: no cover
    from scripts.rebuild_quality_mode import resolve_rebuild_modes  # type: ignore

try:
    from crop_intake_summary import summarize_page
except ImportError:  # pragma: no cover
    from scripts.crop_intake_summary import summarize_page  # type: ignore

MODES = ("auto", "vector-hifi", "text-editable-snapshot", "full-editable", "hifi", "editable", "wps-hifi")
STRICT_VISUAL_MODES = {"vector-hifi", "hifi", "wps-hifi"}


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


def _run_json(cmd: list[str]) -> tuple[int, dict[str, Any], str]:
    result = subprocess.run(cmd, text=True, capture_output=True, check=False)
    payload: dict[str, Any]
    if result.stdout.strip():
        try:
            payload = json.loads(result.stdout)
        except json.JSONDecodeError:
            payload = {"valid": result.returncode == 0, "stdout": result.stdout.strip()}
    else:
        payload = {"valid": result.returncode == 0}
    stderr = result.stderr.strip()
    if stderr:
        payload["stderr"] = stderr
    return result.returncode, payload, stderr


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


def _add_tool_findings(
    findings: list[Finding],
    *,
    name: str,
    path: Path,
    payload: dict[str, Any],
    advisory: bool = False,
) -> None:
    """Convert one tool's errors/warnings into findings.

    ``advisory`` demotes the tool's errors to warnings — per SKILL.md,
    similarity/pixel-drift checks are reported but never block export.
    """
    error_level = "warning" if advisory else "error"
    for item in payload.get("errors", []) if isinstance(payload.get("errors"), list) else []:
        if isinstance(item, dict):
            findings.append(Finding(
                error_level,
                str(item.get("code", f"{name}_error")),
                str(item.get("message", item)),
                str(item.get("path", path)),
            ))
        else:
            findings.append(Finding(error_level, f"{name}_error", str(item), str(path)))
    for item in payload.get("warnings", []) if isinstance(payload.get("warnings"), list) else []:
        if isinstance(item, dict):
            findings.append(Finding(
                "warning",
                str(item.get("code", f"{name}_warning")),
                str(item.get("message", item)),
                str(item.get("path", path)),
            ))
        else:
            findings.append(Finding("warning", f"{name}_warning", str(item), str(path)))


def _load_json(path: Path) -> dict[str, Any]:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}


def _effective_mode(project: Path, mode: str) -> str:
    if mode != "auto":
        return mode
    manifest = _load_json(project / "slide_image_rebuild_manifest.json")
    if manifest:
        resolved = resolve_rebuild_modes(manifest)
        if resolved.rebuild_mode:
            return resolved.rebuild_mode
    rebuild_mode = str(manifest.get("rebuild_mode", "")).strip()
    return rebuild_mode if rebuild_mode in set(MODES) - {"auto"} else "vector-hifi"


def _crop_regression_warnings(
    project: Path,
    crop_summary: dict[str, Any],
    intake_summary: dict[str, Any] | None,
    findings: list[Finding],
) -> None:
    if crop_summary.get("needs_review_count", 0) > 0:
        findings.append(Finding(
            "warning",
            "crop_candidates_need_review",
            f"{crop_summary['needs_review_count']} crop candidate(s) marked needs_review.",
            str(project / "layout_reference.json"),
        ))
    if crop_summary.get("precrop_missing_file_count", 0) > 0:
        findings.append(Finding(
            "warning",
            "crop_precrop_file_missing",
            f"{crop_summary['precrop_missing_file_count']} crop candidate(s) have precrop.enabled without file.",
            str(project / "layout_reference.json"),
        ))
    if intake_summary and intake_summary.get("preprocess_enabled") and not intake_summary.get("source_meta_present"):
        findings.append(Finding(
            "warning",
            "preprocess_meta_missing",
            "intake.preprocess.enabled is true but source_meta.json is missing.",
            intake_summary.get("source_meta_path", str(project)),
        ))
    layout = _load_json(project / "layout_reference.json")
    noise = layout.get("decorative_noise", [])
    noise_count = len(noise) if isinstance(noise, list) else 0
    if crop_summary.get("total", 0) == 0 and noise_count > 0:
        try:
            from layout_reference_rebuild2_lib import is_rebuild2
        except ImportError:
            from scripts.layout_reference_rebuild2_lib import is_rebuild2  # type: ignore
        if is_rebuild2(layout):
            findings.append(Finding(
                "warning",
                "crop_candidates_empty_with_noise",
                "layout has decorative_noise but no crop_candidates; confirm decorative handling.",
                str(project / "layout_reference.json"),
            ))


def _check_compat_report(pptx: Path, findings: list[Finding]) -> dict[str, Any]:
    report_path = Path(str(pptx) + ".compat_report.json")
    report = _load_json(report_path)
    if not report:
        findings.append(Finding(
            "error",
            "missing_compat_report",
            "Missing PPTX compatibility report; export with svg_to_pptx.py sanitizer enabled.",
            str(report_path),
        ))
        return {}
    _add_tool_findings(findings, name="compat_report", path=report_path, payload=report)
    if not report.get("valid", False):
        findings.append(Finding(
            "error",
            "invalid_compat_report",
            "PPTX compatibility report is not valid.",
            str(report_path),
        ))
    return report


def _check_wps_fonts(pptx: Path, findings: list[Finding]) -> dict[str, int]:
    counts = {
        "slide_cn_font": 0,
        "theme_cn_font": 0,
        "end_para_cn_font": 0,
    }
    try:
        with ZipFile(pptx) as package:
            names = package.namelist()
            for name in names:
                if name.startswith("ppt/slides/slide") and name.endswith(".xml"):
                    xml = package.read(name).decode("utf-8", errors="ignore")
                    counts["slide_cn_font"] += xml.count("微软雅黑")
                    counts["end_para_cn_font"] += xml.count("<a:endParaRPr")
                if name.startswith("ppt/theme/theme") and name.endswith(".xml"):
                    xml = package.read(name).decode("utf-8", errors="ignore")
                    counts["theme_cn_font"] += xml.count("微软雅黑")
    except (OSError, BadZipFile) as exc:
        findings.append(Finding("error", "pptx_read_failed", f"Cannot read PPTX for WPS font checks: {exc}", str(pptx)))
        return counts

    if counts["slide_cn_font"] == 0:
        findings.append(Finding(
            "error",
            "missing_wps_cn_slide_font",
            "wps-hifi requires Chinese run font declarations (`微软雅黑`) in slide XML.",
            str(pptx),
        ))
    if counts["theme_cn_font"] == 0:
        findings.append(Finding(
            "error",
            "missing_wps_cn_theme_font",
            "wps-hifi requires theme eastAsia font declarations (`微软雅黑`).",
            str(pptx),
        ))
    return counts


def _check_layout_confidence(project: Path, findings: list[Finding]) -> dict[str, Any]:
    layout_path = project / "layout_reference.json"
    layout = _load_json(layout_path)
    if not layout:
        return {}
    summary: dict[str, Any] = {
        "path": str(layout_path),
        "confidence": layout.get("confidence", {}),
        "needs_review": layout.get("needs_review", []),
        "page_type_classifier": layout.get("page_type_classifier", {}),
    }
    classifier = layout.get("page_type_classifier", {})
    if isinstance(classifier, dict):
        classifier_confidence = classifier.get("confidence")
        if isinstance(classifier_confidence, (int, float)) and float(classifier_confidence) < 0.7:
            findings.append(Finding(
                "warning",
                "low_page_type_confidence",
                f"Page type classifier confidence is {float(classifier_confidence):.2f}; confirm layout_grammar.page_type_hint.",
                str(layout_path),
            ))
        classifier_reviews = classifier.get("needs_review", [])
        if isinstance(classifier_reviews, list):
            for item in classifier_reviews:
                if isinstance(item, str) and item.strip():
                    findings.append(Finding("warning", "page_type_needs_review", item, str(layout_path)))
    confidence = layout.get("confidence", {})
    if isinstance(confidence, dict):
        for key, value in confidence.items():
            if isinstance(value, (int, float)) and float(value) < 0.5:
                findings.append(Finding(
                    "warning",
                    "low_layout_confidence",
                    f"layout_reference.confidence.{key} is {float(value):.2f}; confirm before export.",
                    str(layout_path),
                ))
    needs_review = layout.get("needs_review", [])
    if isinstance(needs_review, list):
        for item in needs_review:
            if isinstance(item, str) and item.strip():
                findings.append(Finding("warning", "layout_needs_review", item, str(layout_path)))
    return summary


def _check_visual_noise_policy(project: Path, findings: list[Finding]) -> dict[str, Any]:
    layout_path = project / "layout_reference.json"
    layout = _load_json(layout_path)
    if not layout:
        return {}
    layering = layout.get("visual_layering", {})
    noise = layout.get("decorative_noise", [])
    summary: dict[str, Any] = {
        "path": str(layout_path),
        "layers_present": [],
        "noise_count": 0,
        "treatment_counts": {},
        "structural_noise": [],
    }
    if isinstance(layering, dict):
        summary["layers_present"] = sorted(str(key) for key in layering.keys())
    else:
        findings.append(Finding(
            "warning",
            "visual_layering_missing",
            "layout_reference.visual_layering is missing or invalid; content/structure/decorative boundaries are not documented.",
            str(layout_path),
        ))
    if not isinstance(noise, list):
        findings.append(Finding(
            "warning",
            "decorative_noise_invalid",
            "layout_reference.decorative_noise is missing or invalid; decorative noise cannot be gated.",
            str(layout_path),
        ))
        return summary

    summary["noise_count"] = len(noise)
    treatment_counts: dict[str, int] = {}
    structural_noise: list[str] = []
    for item in noise:
        if not isinstance(item, dict):
            continue
        treatment = str(item.get("treatment", "unspecified"))
        treatment_counts[treatment] = treatment_counts.get(treatment, 0) + 1
        if item.get("semantic_weight") == "structural":
            structural_noise.append(str(item.get("id", "")))
    summary["treatment_counts"] = treatment_counts
    summary["structural_noise"] = [item for item in structural_noise if item]
    if not noise:
        findings.append(Finding(
            "warning",
            "decorative_noise_empty",
            "No decorative_noise entries found; confirm the page truly has no background texture, light effects, or ambient line art.",
            str(layout_path),
        ))
    for item_id in structural_noise:
        if item_id:
            findings.append(Finding(
                "warning",
                "structural_noise_needs_review",
                f"decorative_noise `{item_id}` is marked structural; ensure it is not ignored or converted into a decorative-only artifact.",
                str(layout_path),
            ))
    return summary


def _tool_checks(project: Path, mode: str, *, render: bool) -> dict[str, dict[str, Any]]:
    script_dir = Path(__file__).resolve().parent
    checks: dict[str, list[str]] = {
        "text_fit": [sys.executable, str(script_dir / "verify_text_fit.py"), str(project)],
        "svg_spacing": [sys.executable, str(script_dir / "verify_svg_spacing.py"), str(project)],
        "text_bearing_images": [sys.executable, str(script_dir / "verify_text_bearing_images.py"), str(project), "--write-report"],
    }
    if render:
        try:
            from render_backend_resolve_lib import resolve_project_render_backend
        except ImportError:  # pragma: no cover
            from scripts.render_backend_resolve_lib import resolve_project_render_backend  # type: ignore
        render_backend, _backend_warnings = resolve_project_render_backend(project, hard_gate=True)
        checks["svg_preview"] = [
            sys.executable,
            str(script_dir / "verify_svg_preview.py"),
            str(project),
            "--render",
            "--render-backend",
            render_backend,
            "--hard-gate",
        ]
        threshold = "58" if mode in STRICT_VISUAL_MODES else "72"
        anchor_threshold = "3" if mode in STRICT_VISUAL_MODES else "6"
        checks["reference_similarity"] = [
            sys.executable,
            str(script_dir / "verify_reference_similarity.py"),
            str(project),
            "--render",
            "--render-backend",
            render_backend,
            "--hard-gate",
            "--threshold",
            threshold,
            "--anchor-threshold",
            anchor_threshold,
        ]

    results: dict[str, dict[str, Any]] = {}
    for name, cmd in checks.items():
        returncode, payload, _stderr = _run_json(cmd)
        payload["returncode"] = returncode
        results[name] = payload
    return results


def verify_project(project: Path, *, mode: str = "auto", render: bool = False) -> dict[str, Any]:
    effective_mode = _effective_mode(project, mode)
    findings: list[Finding] = []
    page_summary = summarize_page(project)
    intake_summary = page_summary.get("intake_summary")
    crop_summary = page_summary.get("crop_candidates_summary", {})
    if isinstance(intake_summary, dict):
        _crop_regression_warnings(project, crop_summary, intake_summary, findings)
    elif isinstance(crop_summary, dict):
        _crop_regression_warnings(project, crop_summary, None, findings)
    layout_reference = _check_layout_confidence(project, findings)
    visual_noise_policy = _check_visual_noise_policy(project, findings)
    tool_results = _tool_checks(project, effective_mode, render=render)
    for name, payload in tool_results.items():
        similarity_advisory = name == "reference_similarity"
        _add_tool_findings(
            findings,
            name=name,
            path=project,
            payload=payload,
            advisory=similarity_advisory,
        )
        if payload.get("valid") is False:
            if similarity_advisory:
                findings.append(Finding(
                    "warning", f"{name}_invalid",
                    f"{name} did not pass (advisory, non-blocking).", str(project),
                ))
            else:
                findings.append(Finding("error", f"{name}_invalid", f"{name} did not pass.", str(project)))

    pptx = _latest_pptx(project)
    editable_result: dict[str, Any] = {}
    compat_report: dict[str, Any] = {}
    wps_font_counts: dict[str, int] = {}
    if pptx is None:
        findings.append(Finding("error", "missing_exported_pptx", "No exported PPTX found in exports/.", str(project / "exports")))
    else:
        script_dir = Path(__file__).resolve().parent
        _code, editable_result, _stderr = _run_json([
            sys.executable,
            str(script_dir / "verify_editable_pptx.py"),
            str(pptx),
            "--project",
            str(project),
        ])
        _add_tool_findings(findings, name="verify_editable_pptx", path=pptx, payload=editable_result)
        if editable_result.get("valid") is False:
            findings.append(Finding("error", "editable_pptx_invalid", "Editable PPTX verification failed.", str(pptx)))
        compat_report = _check_compat_report(pptx, findings)
        if effective_mode == "wps-hifi":
            wps_font_counts = _check_wps_fonts(pptx, findings)

    errors = [finding.as_dict() for finding in findings if finding.level == "error"]
    warnings = [finding.as_dict() for finding in findings if finding.level == "warning"]
    return {
        "workflow": "slide-image-rebuild",
        "version": "1.0",
        "mode": effective_mode,
        "requested_mode": mode,
        "valid": not errors,
        "errors": errors,
        "warnings": warnings,
        "tools": tool_results,
        "layout_reference": layout_reference,
        "visual_noise_policy": visual_noise_policy,
        "intake_summary": intake_summary,
        "crop_candidates_summary": crop_summary,
        "editable_pptx": editable_result,
        "compat_report": compat_report,
        "wps_font_counts": wps_font_counts,
        "exported_pptx": str(pptx) if pptx else "",
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Aggregate mode-aware slide-image rebuild regression checks.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("project_path", help="Project directory")
    parser.add_argument("--mode", choices=MODES, default="auto", help="Rebuild mode (default: auto reads slide_image_rebuild_manifest.json, then vector-hifi)")
    parser.add_argument("--render", action="store_true", help="Run render-dependent preview and similarity checks")
    parser.add_argument(
        "--output",
        help="Report path (default: <project_path>/rebuild_regression_report.json)",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    project = Path(args.project_path).resolve()
    if not project.is_dir():
        print(json.dumps({
            "valid": False,
            "errors": [{
                "level": "error",
                "code": "missing_project",
                "message": f"Project directory not found: {project}",
                "path": str(project),
            }],
            "warnings": [],
        }, ensure_ascii=False, indent=2))
        return 1

    report = verify_project(project, mode=args.mode, render=args.render)
    output = Path(args.output).resolve() if args.output else project / "rebuild_regression_report.json"
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report["valid"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
