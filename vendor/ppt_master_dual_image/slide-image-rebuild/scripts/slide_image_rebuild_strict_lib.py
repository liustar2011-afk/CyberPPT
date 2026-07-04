#!/usr/bin/env python3
"""
Shared helpers for run_slide_image_rebuild_strict.py.
"""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import shlex
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

_SCRIPTS_DIR = Path(__file__).resolve().parent
if str(_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_DIR))

try:
    from rebuild_quality_mode import resolve_rebuild_modes
except ImportError:  # pragma: no cover
    from scripts.rebuild_quality_mode import resolve_rebuild_modes  # type: ignore

try:
    from slide_image_rebuild_manifest_lib import resolve_text_granularity
except ImportError:  # pragma: no cover
    from scripts.slide_image_rebuild_manifest_lib import resolve_text_granularity  # type: ignore

try:
    from layout_reference_rebuild2_lib import PLACEHOLDER_TOKENS
except ImportError:  # pragma: no cover
    from scripts.layout_reference_rebuild2_lib import PLACEHOLDER_TOKENS  # type: ignore

try:
    from alignment_underlay import check_no_underlays, inject_underlays, strip_underlays
except ImportError:  # pragma: no cover
    from scripts.alignment_underlay import check_no_underlays, inject_underlays, strip_underlays  # type: ignore

try:
    from shared_ppt_resources import resource_path, svg_quality_checker_script
except ImportError:  # pragma: no cover
    resource_path = None
    svg_quality_checker_script = None

STAGE_ORDER = {
    "bootstrap": 0,
    "intake": 1,
    "layout": 2,
    "mapped": 3,
    "icon": 4,
    "svg": 5,
    "export": 6,
    "post-export": 7,
    "package": 8,
}

RUN_STAGE_ALIASES = {
    "pre-export": 5,
    "full": 8,
}

CAPTURE_MAX_BYTES = 512 * 1024
REPORT_VERSION = "1.0"
SUMMARY_VERSION = "1.0"
STRICT_RUNNER_REL = "scripts/run_slide_image_rebuild_strict.py"
SUMMARY_REL_PATH = "exports/qa/strict_run_summary.json"
REPORT_REL_PATH = "exports/qa/strict_run_report.json"
LAYOUT_STAMP_REL_PATH = "exports/qa/layout_artifacts_stamp.json"
LAYOUT_STAMP_VERSION = "1.0"
LAYOUT_TRUST_STAGES = frozenset({"layout", "mapped"})


@dataclass
class RunConfig:
    project: Path
    reference: Path | None
    rebuild_mode: str
    export_mode: str
    precise_lock: bool
    render: bool
    stage_requested: str
    stop_on_error: bool
    dry_run: bool
    skip_export: bool
    preview_render_backend: str
    repo_root: Path
    scripts_dir: Path
    python: str = sys.executable
    agent_summary_stdout: bool = False
    reference_threshold: float = 58.0
    icon_enforce: bool = False
    auto_repair: bool = False
    incremental: bool = False


@dataclass
class StepSpec:
    step_id: str
    stage: str
    gate: str  # hard | soft | conditional
    tool_name: str
    script: str | None
    argv: list[str]
    condition: Callable[[RunConfig, dict[str, Any]], bool] | None = None
    inline: Callable[[RunConfig], dict[str, Any]] | None = None
    report_paths: list[str] = field(default_factory=list)
    scope_page_id: str | None = None


@dataclass
class StepRecord:
    spec: StepSpec
    seq: int
    status: str = "pending"
    timing: dict[str, Any] = field(default_factory=dict)
    result: dict[str, Any] = field(default_factory=dict)
    errors: list[dict[str, Any]] = field(default_factory=list)
    warnings: list[dict[str, Any]] = field(default_factory=list)
    outputs: dict[str, list[str]] = field(default_factory=lambda: {"report_files": [], "side_effect_files": []})


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


try:  # shared helper; see scripts/json_io.py
    from json_io import load_json
except ImportError:  # pragma: no cover - package-context import
    from scripts.json_io import load_json  # type: ignore


def parse_tool_output(stdout_text: str, exit_code: int) -> dict[str, Any]:
    """Parse a sub-tool's stdout into a payload dict.

    Falls back to ``{"valid": exit_code == 0}`` when stdout is empty, and to
    ``{"valid": ..., "stdout": ...}`` when stdout is non-JSON. Mirrors the
    historical inline logic used by run_step / _verify_editable_pptx_step.
    """
    if stdout_text.strip():
        try:
            return json.loads(stdout_text)
        except json.JSONDecodeError:
            return {"valid": exit_code == 0, "stdout": stdout_text.strip()}
    return {"valid": exit_code == 0}


def repo_root_from_scripts(scripts_dir: Path) -> Path:
    return scripts_dir.parent


def resolve_modes(project: Path, rebuild_mode: str, export_mode: str) -> tuple[str, str]:
    manifest = load_json(project / "slide_image_rebuild_manifest.json")
    resolved = resolve_rebuild_modes(manifest)
    text_resolved = resolve_text_granularity(manifest)
    effective_rebuild = rebuild_mode
    effective_export = export_mode
    if effective_rebuild == "auto":
        effective_rebuild = resolved.rebuild_mode or manifest.get("rebuild_mode", "vector-hifi") or "vector-hifi"
    if effective_export == "auto":
        effective_export = resolved.pptx_export_mode or manifest.get("pptx_export_mode", "hifi") or "hifi"
    if effective_rebuild in {"hifi", "editable", "wps-hifi"}:
        effective_export = effective_rebuild
        effective_rebuild = "vector-hifi"
    if text_resolved.force_hifi_export and effective_export == "editable":
        effective_export = "hifi"
    return str(effective_rebuild), str(effective_export)


def resolve_precise_lock(project: Path, flag: bool) -> bool:
    if flag:
        return True
    manifest = load_json(project / "slide_image_rebuild_manifest.json")
    profile = manifest.get("execution_profile") or manifest.get("chatgpt_profile")
    return profile == "chatgpt_precise_rebuild"


def manifest_pages(project: Path) -> list[dict[str, Any]]:
    manifest = load_json(project / "slide_image_rebuild_manifest.json")
    pages = manifest.get("pages", [])
    if isinstance(pages, list) and pages:
        return [page for page in pages if isinstance(page, dict)]
    return [{"page_id": "01", "page_dir": "."}]


def page_dir(project: Path, page: dict[str, Any]) -> Path:
    raw = page.get("page_dir") or page.get("page_project") or page.get("project_path")
    if isinstance(raw, str) and raw.strip():
        path = Path(raw)
        if not path.is_absolute():
            path = project / path
        return path.resolve()
    page_id = str(page.get("page_id", "")).strip()
    candidate = project / "pages" / page_id
    return candidate if candidate.is_dir() else project


def iter_layout_artifact_paths(project: Path) -> list[Path]:
    """Paths whose content defines the layout/mapped validation fingerprint."""
    paths: list[Path] = []
    manifest = project / "slide_image_rebuild_manifest.json"
    if manifest.is_file():
        paths.append(manifest)
    text_map = project / "text_region_map.json"
    if text_map.is_file():
        paths.append(text_map)
    for name in (
        "layout_reference_brief.md",
        "design_spec.md",
        "svg_build_plan.json",
        "svg_build_plan.md",
    ):
        candidate = project / name
        if candidate.is_file():
            paths.append(candidate)
    for _page_id, layout_path in layout_paths(project):
        parent = layout_path.parent
        for name in ("layout_reference.json", "content_mapping.json"):
            candidate = parent / name
            if candidate.is_file():
                paths.append(candidate)
    deduped: list[Path] = []
    seen: set[str] = set()
    for path in paths:
        key = str(path.resolve())
        if key in seen:
            continue
        seen.add(key)
        deduped.append(path)
    return sorted(deduped, key=lambda item: str(item.relative_to(project)))


def compute_layout_fingerprint(project: Path) -> str:
    digest = hashlib.sha256()
    for path in iter_layout_artifact_paths(project):
        rel = str(path.relative_to(project))
        digest.update(rel.encode("utf-8"))
        digest.update(b"\0")
        digest.update(path.read_bytes())
        digest.update(b"\0")
    return f"sha256:{digest.hexdigest()}"


def load_layout_artifacts_stamp(project: Path) -> dict[str, Any] | None:
    stamp_path = project / LAYOUT_STAMP_REL_PATH
    if not stamp_path.is_file():
        return None
    payload = load_json(stamp_path)
    return payload if payload.get("fingerprint") else None


def layout_stamp_trusted(project: Path, stage_requested: str) -> bool:
    """True when layout/mapped gates may be skipped (resume from icon/svg/export)."""
    if stage_index(stage_requested) <= stage_index("mapped"):
        return False
    stamp = load_layout_artifacts_stamp(project)
    if not stamp:
        return False
    return stamp.get("fingerprint") == compute_layout_fingerprint(project)


def write_layout_artifacts_stamp(project: Path, stage_reached: str) -> Path:
    stamp_path = project / LAYOUT_STAMP_REL_PATH
    stamp_path.parent.mkdir(parents=True, exist_ok=True)
    artifact_paths = [str(path.relative_to(project)) for path in iter_layout_artifact_paths(project)]
    payload = {
        "version": LAYOUT_STAMP_VERSION,
        "fingerprint": compute_layout_fingerprint(project),
        "stamped_at": utc_now(),
        "stamped_by": STRICT_RUNNER_REL,
        "stage_reached": stage_reached,
        "artifact_paths": artifact_paths,
    }
    stamp_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return stamp_path


def should_trust_skip_layout_step(spec: StepSpec, ctx: dict[str, Any]) -> bool:
    if not ctx.get("layout_stamp_trusted"):
        return False
    if spec.stage in LAYOUT_TRUST_STAGES:
        return True
    return spec.step_id == "1.1.manifest_intake"


SVG_STAGE_STATE_REL_PATH = "exports/qa/svg_stage_state.json"
SVG_REUSE_NON_SKIPPABLE_STEP_IDS = frozenset({
    "5.0a.strip_alignment_underlay_before_validation",
    "5.0b.check_alignment_underlay_stripped",
    "5.13.inject_alignment_underlay",
})


def svg_output_signature(project: Path) -> str | None:
    """Content hash of svg_output/ (sorted), or None when no SVGs exist.

    Content-based (not mtime) so a checkout / touch that leaves bytes unchanged
    still counts as unchanged, and a sub-second content edit cannot be missed.
    """
    svg_dir = project / "svg_output"
    if not svg_dir.is_dir():
        return None
    digest = hashlib.sha256()
    found = False
    for svg in sorted(svg_dir.glob("*.svg")):
        found = True
        digest.update(svg.name.encode("utf-8"))
        digest.update(b"\0")
        digest.update(svg.read_bytes())
        digest.update(b"\0")
    return digest.hexdigest() if found else None


def should_reuse_skip_svg_step(spec: StepSpec, ctx: dict[str, Any]) -> bool:
    """Skip svg-stage re-verification when --incremental and svg_output is unchanged.

    Only fires when a prior run validated the svg stage for the identical
    svg_output content. Never skips a changed deck, and is off unless opted in.
    """
    if not ctx.get("reuse_svg_stage"):
        return False
    if spec.step_id in SVG_REUSE_NON_SKIPPABLE_STEP_IDS:
        return False
    return spec.stage == "svg"


def icon_contract_needed(config: RunConfig) -> bool:
    return (
        config.precise_lock
        or has_icon_slots(config.project)
        or (config.project / "icon_manifest.json").is_file()
    )


def layout_paths(project: Path) -> list[tuple[str, Path]]:
    out: list[tuple[str, Path]] = []
    for page in manifest_pages(project):
        page_id = str(page.get("page_id", "")).strip() or "01"
        layout = page_dir(project, page) / "layout_reference.json"
        if layout.is_file():
            out.append((page_id, layout))
    root_layout = project / "layout_reference.json"
    if root_layout.is_file() and not out:
        out.append(("01", root_layout))
    return out


def latest_pptx(project: Path) -> Path | None:
    exports = project / "exports"
    if not exports.is_dir():
        return None
    pptxs = sorted(
        (path for path in exports.glob("*.pptx") if not path.name.startswith("~$")),
        key=lambda path: path.stat().st_mtime,
        reverse=True,
    )
    return pptxs[0] if pptxs else None


def pptx_slide_count(pptx: Path) -> int:
    import zipfile

    try:
        with zipfile.ZipFile(pptx) as archive:
            return sum(
                1
                for name in archive.namelist()
                if name.startswith("ppt/slides/slide") and name.endswith(".xml")
            )
    except (OSError, zipfile.BadZipFile):
        return 0


def _resolve_officecli_binary() -> Path | None:
    env_bin = os.environ.get("OFFICECLI_BIN", "").strip()
    if env_bin:
        candidate = Path(env_bin).expanduser()
        if candidate.is_file():
            return candidate

    candidates: list[Path] = []
    if resource_path is not None:
        try:
            officecli_dir = resource_path("officecli_dir")
            candidates.extend([
                officecli_dir / "bin" / "release" / "officecli-mac-arm64",
                officecli_dir / "bin" / "release" / "officecli-mac-x64",
                officecli_dir / "bin" / "release" / "officecli-linux-arm64",
                officecli_dir / "bin" / "release" / "officecli-linux-x64",
                officecli_dir / "bin" / "release" / "officecli-win-arm64.exe",
                officecli_dir / "bin" / "release" / "officecli-win-x64.exe",
            ])
        except FileNotFoundError:
            pass

    path_bin = shutil.which("officecli")
    if path_bin:
        candidates.append(Path(path_bin))

    for candidate in candidates:
        if candidate.is_file() and os.access(candidate, os.X_OK):
            return candidate
    return None


def has_icon_slots(project: Path) -> bool:
    for _page_id, layout_path in layout_paths(project):
        layout = load_json(layout_path)
        icons = layout.get("icon_reconstruction", {})
        if isinstance(icons, dict) and icons.get("icons"):
            return True
        zones = layout.get("zones", [])
        if isinstance(zones, list):
            for zone in zones:
                if not isinstance(zone, dict):
                    continue
                role = str(zone.get("role", "")).lower()
                component = str(zone.get("component", "")).lower()
                if "icon" in role or "icon_slot" in component:
                    return True
    return False


def has_text_regions(project: Path) -> bool:
    text_map = load_json(project / "text_region_map.json")
    pages = text_map.get("pages")
    if isinstance(pages, list):
        for page in pages:
            if not isinstance(page, dict):
                continue
            regions = page.get("regions", [])
            if isinstance(regions, list) and regions:
                return True
    regions = text_map.get("regions", [])
    return isinstance(regions, list) and bool(regions)


def has_text_fit_report_items(project: Path) -> bool:
    """True when the text-fit engine wrote fit_id-level items to cross-repair."""
    report = load_json(project / "exports" / "qa" / "text_fit_report.json")
    items = report.get("items")
    return isinstance(items, list) and bool(items)


def has_connector_svgs(project: Path) -> bool:
    """True when any rebuilt SVG carries a data-chain-connector element."""
    for sub in ("svg_final", "svg_output"):
        folder = project / sub
        if not folder.is_dir():
            continue
        for svg in folder.glob("*.svg"):
            try:
                if "data-chain-connector" in svg.read_text(encoding="utf-8"):
                    return True
            except OSError:
                continue
    return False


def has_connector_report_items(project: Path) -> bool:
    """True when the connector engine wrote per-connector items to cross-repair."""
    report = load_json(project / "exports" / "qa" / "connector_geometry_report.json")
    items = report.get("items")
    return isinstance(items, list) and bool(items)


def has_geometry_locks(project: Path) -> bool:
    for _page_id, layout_path in layout_paths(project):
        layout = load_json(layout_path)
        locks = layout.get("geometry_locks")
        if isinstance(locks, list) and locks:
            return True
    return False


def has_layout_zones(project: Path) -> bool:
    for _page_id, layout_path in layout_paths(project):
        layout = load_json(layout_path)
        zones = layout.get("zones", [])
        if isinstance(zones, list) and zones:
            return True
    return False


def has_harvestable_asset_candidates(project: Path) -> bool:
    for _page_id, layout_path in layout_paths(project):
        layout = load_json(layout_path)
        candidates = layout.get("crop_candidates", [])
        if not isinstance(candidates, list):
            continue
        for candidate in candidates:
            if (
                isinstance(candidate, dict)
                and str(candidate.get("editability_intent", "")).strip() == "asset"
            ):
                return True
    return False


def resolve_reference_image(project: Path, explicit: Path | None) -> Path | None:
    if explicit is not None and explicit.is_file():
        return explicit
    for candidate in (
        project / "images" / "reference_layout.png",
        project / "images" / "reference_layout.normalized.png",
    ):
        if candidate.is_file():
            return candidate
    images = project / "images"
    if images.is_dir():
        for path in sorted(images.glob("reference_pages/*.png")):
            return path
    return None


def intake_preprocess_enabled(project: Path) -> bool:
    manifest = load_json(project / "slide_image_rebuild_manifest.json")
    intake = manifest.get("intake", {})
    if not isinstance(intake, dict):
        return False
    preprocess = intake.get("preprocess", {})
    return isinstance(preprocess, dict) and preprocess.get("enabled") is True


def intake_precrop_enabled(project: Path) -> bool:
    manifest = load_json(project / "slide_image_rebuild_manifest.json")
    intake = manifest.get("intake", {})
    if not isinstance(intake, dict):
        return False
    precrop = intake.get("precrop_candidates", {})
    return isinstance(precrop, dict) and precrop.get("enabled") is True


def _has_placeholder(value: Any) -> bool:
    if not isinstance(value, str):
        return False
    lowered = value.strip().lower()
    return any(token in lowered for token in PLACEHOLDER_TOKENS)


def scan_layout_placeholders(project: Path) -> dict[str, Any]:
    errors: list[str] = []
    for page_id, layout_path in layout_paths(project):
        text = layout_path.read_text(encoding="utf-8")
        for token in PLACEHOLDER_TOKENS:
            if token in text.lower():
                errors.append(f"Page `{page_id}` layout contains placeholder token `{token}` in {layout_path.name}.")
                break
        layout = load_json(layout_path)
        for key in ("page_type_hint", "layout_type"):
            if _has_placeholder(layout.get(key)):
                errors.append(f"Page `{page_id}` field `{key}` still contains a placeholder.")
    return {"valid": not errors, "errors": errors, "warnings": []}


def check_notes_total_md(project: Path) -> dict[str, Any]:
    notes = project / "notes" / "total.md"
    if not notes.is_file():
        return {
            "valid": False,
            "errors": [f"Missing speaker notes: {notes}"],
            "warnings": [],
        }
    return {"valid": True, "errors": [], "warnings": []}


def check_artifact_files(project: Path, paths: list[str], *, base: Path | None = None) -> dict[str, Any]:
    errors: list[str] = []
    missing: list[str] = []
    root = base if base is not None else project
    for rel in paths:
        path = root / rel
        if not path.exists():
            missing.append(rel)
            errors.append(f"Required artifact missing: {rel}")
    return {"valid": not errors, "errors": errors, "warnings": [], "missing": missing}


def check_svg_final_freshness(project: Path) -> dict[str, Any]:
    svg_final = project / "svg_final"
    svg_output = project / "svg_output"
    if not svg_final.is_dir() or not any(svg_final.glob("*.svg")):
        return {"valid": False, "errors": ["svg_final/ is missing or has no SVG pages."], "warnings": []}
    if not svg_output.is_dir():
        return {"valid": True, "errors": [], "warnings": ["svg_output/ missing; freshness check skipped."]}
    final_mtime = max(path.stat().st_mtime for path in svg_final.glob("*.svg"))
    output_mtime = max((path.stat().st_mtime for path in svg_output.glob("*.svg")), default=0)
    if output_mtime > final_mtime:
        return {
            "valid": False,
            "errors": ["svg_output/ is newer than svg_final/; re-run finalize_svg.py before export."],
            "warnings": [],
        }
    return {"valid": True, "errors": [], "warnings": []}


def package_artifact_paths(project: Path, pptx: Path | None) -> list[str]:
    # Note: strict_run_report.json / strict_run_summary.json are deliberately not
    # listed here -- run() only writes them once, after every step (including this
    # one) has already finished. Checking for them mid-run can only ever see a
    # stale report from a previous invocation, never this run's own output.
    required: list[str] = []
    repair_tasks = project / "exports" / "qa" / "repair_tasks.json"
    if repair_tasks.is_file():
        required.append("exports/qa/repair_tasks.json")
    object_report = project / "exports" / "qa" / "object_similarity_report.json"
    if object_report.is_file():
        required.append("exports/qa/object_similarity_report.json")
    if (project / "svg_final").is_dir():
        required.append("svg_final")
    if pptx is not None:
        required.extend([
            str(pptx.relative_to(project)),
            str(pptx.with_name(pptx.name + ".compat_report.json").relative_to(project)),
            "exports/qa/officecli_screenshot.png",
            "exports/qa/officecli_screenshot.json",
        ])
        trace_alias = project / "exports" / "pptx" / "conversion_trace.json"
        trace_legacy = pptx.with_name(pptx.name + ".trace.json")
        if trace_alias.is_file():
            required.append(str(trace_alias.relative_to(project)))
        elif trace_legacy.is_file():
            required.append(str(trace_legacy.relative_to(project)))
    preview_dir = project / "exports" / "preview_qa"
    if preview_dir.is_dir() and any(preview_dir.glob("*.png")):
        required.append("exports/preview_qa")
    return required


def stage_index(stage: str) -> int:
    if stage in RUN_STAGE_ALIASES:
        return RUN_STAGE_ALIASES[stage]
    return STAGE_ORDER[stage]


def stage_reached(requested: str, current: str) -> bool:
    return stage_index(current) <= stage_index(requested)


def resolve_strict_preview_render_backend(project: Path) -> str:
    try:
        from render_backend_resolve_lib import resolve_project_render_backend
    except ImportError:  # pragma: no cover
        from scripts.render_backend_resolve_lib import resolve_project_render_backend  # type: ignore
    backend, _warnings = resolve_project_render_backend(project, hard_gate=True)
    return backend


def _script_argv(config: RunConfig, script_name: str, *args: str) -> list[str]:
    script_path = config.scripts_dir / script_name
    if script_name == "svg_quality_checker.py" and svg_quality_checker_script is not None:
        try:
            script_path = svg_quality_checker_script()
        except FileNotFoundError:
            script_path = config.scripts_dir / script_name
    return [config.python, str(script_path), *args]


def _icon_contract_argv(config: RunConfig, project: Path, *, write_report: bool) -> list[str]:
    args: list[str] = [str(project)]
    icon_manifest = load_json(project / "icon_manifest.json")
    policy = icon_manifest.get("policy", {}) if isinstance(icon_manifest.get("policy"), dict) else {}
    if policy.get("style_check") is not False:
        args.append("--style-check")
    if write_report:
        args.append("--write-report")
    if config.icon_enforce:
        args.append("--enforce")
    args.extend(_render_gate_args(config))
    return _script_argv(config, "verify_icon_contract.py", *args)


def _render_gate_args(config: RunConfig) -> list[str]:
    if not config.render:
        return []
    return [
        "--render",
        "--render-backend",
        config.preview_render_backend,
        "--hard-gate",
    ]


def build_steps(config: RunConfig) -> list[StepSpec]:
    project = config.project
    rebuild_mode = config.rebuild_mode
    export_mode = config.export_mode
    steps: list[StepSpec] = []

    bootstrap_step_id = "0.1.check_cairo_backend"
    bootstrap_tool = "check_cairo_backend"
    bootstrap_script = "check_cairo_backend.py"
    steps.append(StepSpec(
        bootstrap_step_id,
        "bootstrap",
        "hard" if config.render else "conditional",
        bootstrap_tool,
        bootstrap_script,
        _script_argv(config, bootstrap_script),
        condition=lambda cfg, _ctx: cfg.render,
    ))
    steps.append(StepSpec(
        "0.2.manifest_exists",
        "bootstrap",
        "hard",
        "inline",
        None,
        [],
        inline=lambda cfg: {
            "valid": (cfg.project / "slide_image_rebuild_manifest.json").is_file(),
            "errors": [] if (cfg.project / "slide_image_rebuild_manifest.json").is_file()
            else ["slide_image_rebuild_manifest.json is required."],
            "warnings": [],
        },
    ))
    steps.append(StepSpec(
        "0.4.consolidate_page_svgs",
        "bootstrap",
        "soft",
        "inline",
        None,
        [],
        inline=_consolidate_page_svgs_step,
    ))
    steps.append(StepSpec(
        "0.3.project_validate",
        "bootstrap",
        "soft",
        "project_manager",
        "project_manager.py",
        _script_argv(config, "project_manager.py", "validate", str(project)),
    ))

    steps.append(StepSpec(
        "1.1.manifest_intake",
        "intake",
        "hard",
        "verify_slide_image_rebuild_manifest",
        "verify_slide_image_rebuild_manifest.py",
        _script_argv(config, "verify_slide_image_rebuild_manifest.py", str(project), "--stage", "intake"),
    ))
    steps.append(StepSpec(
        "1.2.preprocess_reference",
        "intake",
        "conditional",
        "preprocess_reference_image",
        "preprocess_reference_image.py",
        _script_argv(
            config,
            "preprocess_reference_image.py",
            str(resolve_reference_image(project, config.reference) or project / "images" / "reference_layout.png"),
            "--project",
            str(project),
        ),
        condition=lambda cfg, _ctx: (
            intake_preprocess_enabled(cfg.project)
            and resolve_reference_image(cfg.project, cfg.reference) is not None
            and stage_index(cfg.stage_requested) > stage_index("intake")
            and not (cfg.project / "images" / "source_meta.json").is_file()
        ),
        report_paths=["images/source_meta.json"],
    ))
    steps.append(StepSpec(
        "1.3.precrop_candidates",
        "intake",
        "conditional",
        "precrop_layout_candidates",
        "precrop_layout_candidates.py",
        _script_argv(
            config,
            "precrop_layout_candidates.py",
            str(project),
            "--source-image",
            "images/reference_layout.normalized.png",
            "--write-back",
        ),
        condition=lambda cfg, _ctx: intake_precrop_enabled(cfg.project),
    ))
    steps.append(StepSpec(
        "1.4.crop_intake_summary",
        "intake",
        "soft",
        "crop_intake_summary",
        "crop_intake_summary.py",
        _script_argv(config, "crop_intake_summary.py", str(project)),
    ))

    steps.append(StepSpec(
        "2.1.manifest_extracted",
        "layout",
        "hard",
        "verify_slide_image_rebuild_manifest",
        "verify_slide_image_rebuild_manifest.py",
        _script_argv(config, "verify_slide_image_rebuild_manifest.py", str(project), "--stage", "extracted"),
    ))
    # text-editable-snapshot has no vector structure to describe (no zones/icons/
    # structure_contract), so it's exempt from the v2.0 / 复刻流程2 schema --
    # already gated on manifest.user_acceptance in resolve_rebuild_modes().
    rebuild2_args = ["--rebuild2"] if rebuild_mode != "text-editable-snapshot" else []
    for page_id, layout_path in layout_paths(project):
        steps.append(StepSpec(
            f"2.2.validate_layout_reference.page.{page_id}",
            "layout",
            "hard",
            "validate_layout_reference",
            "validate_layout_reference.py",
            _script_argv(config, "validate_layout_reference.py", str(layout_path), *rebuild2_args),
            scope_page_id=page_id,
        ))
        mapping = layout_path.parent / "content_mapping.json"
        if mapping.is_file():
            steps.append(StepSpec(
                f"2.3.validate_layout_with_mapping.page.{page_id}",
                "layout",
                "hard",
                "validate_layout_reference",
                "validate_layout_reference.py",
                _script_argv(
                    config,
                    "validate_layout_reference.py",
                    str(layout_path),
                    *rebuild2_args,
                    "--mapping",
                    str(mapping),
                ),
                scope_page_id=page_id,
            ))
        steps.append(StepSpec(
            f"2.4.verify_icon_text_fit.page.{page_id}",
            "layout",
            "soft",
            "verify_icon_text_fit",
            "verify_icon_text_fit.py",
            _script_argv(config, "verify_icon_text_fit.py", str(layout_path)),
            scope_page_id=page_id,
        ))
    steps.append(StepSpec(
        "2.5.placeholder_scan",
        "layout",
        "hard",
        "inline",
        None,
        [],
        inline=lambda cfg: scan_layout_placeholders(cfg.project),
    ))

    steps.append(StepSpec(
        "3.1.manifest_mapped",
        "mapped",
        "hard",
        "verify_slide_image_rebuild_manifest",
        "verify_slide_image_rebuild_manifest.py",
        _script_argv(config, "verify_slide_image_rebuild_manifest.py", str(project), "--stage", "mapped"),
    ))
    for page_id, layout_path in layout_paths(project):
        mapping = layout_path.parent / "content_mapping.json"
        if mapping.is_file():
            steps.append(StepSpec(
                f"3.2.validate_content_mapping.page.{page_id}",
                "mapped",
                "hard",
                "validate_content_mapping",
                "validate_content_mapping.py",
                _script_argv(
                    config,
                    "validate_content_mapping.py",
                    str(mapping),
                    "--layout",
                    str(layout_path),
                ),
                scope_page_id=page_id,
            ))
    def _check_artifacts_design_spec(cfg: RunConfig) -> dict[str, Any]:
        required = ["layout_reference_brief.md", "svg_build_plan.json", "svg_build_plan.md"]
        pages = layout_paths(cfg.project)
        bases = [layout_path.parent for _page_id, layout_path in pages] or [cfg.project]
        errors: list[str] = []
        missing: list[str] = []
        for base in bases:
            result = check_artifact_files(cfg.project, required, base=base)
            errors.extend(result["errors"])
            missing.extend(result["missing"])
        return {"valid": not errors, "errors": errors, "warnings": [], "missing": missing}

    steps.append(StepSpec(
        "3.3.artifacts_design_spec",
        "mapped",
        "hard",
        "inline",
        None,
        [],
        inline=_check_artifacts_design_spec,
    ))
    steps.append(StepSpec(
        "3.4.layout_family_contract",
        "mapped",
        "soft",
        "verify_layout_family_contract",
        "verify_layout_family_contract.py",
        _script_argv(config, "verify_layout_family_contract.py", str(project), "--write-report"),
        report_paths=["exports/qa/layout_family_contract_report.json"],
        # Layout-family classification (hub_and_spoke, chevron columns, ...) and its
        # icon_reconstruction requirement only make sense for a vector-rebuilt page.
        # text-editable-snapshot has no icons to classify -- aggregate_repair_tasks
        # would otherwise turn this soft/advisory check into a hard export blocker.
        condition=lambda cfg, _ctx: has_layout_zones(cfg.project) and rebuild_mode != "text-editable-snapshot",
    ))
    steps.append(StepSpec(
        "3.5.harvest_reference_assets",
        "mapped",
        "soft",
        "harvest_reference_assets",
        "harvest_reference_assets.py",
        _script_argv(config, "harvest_reference_assets.py", str(project)),
        report_paths=["image_asset_manifest.json", "images/harvested_assets"],
        condition=lambda cfg, _ctx: has_harvestable_asset_candidates(cfg.project),
    ))

    steps.append(StepSpec(
        "4.0.build_icon_manifest",
        "icon",
        "soft",
        "build_icon_manifest_from_layout",
        "build_icon_manifest_from_layout.py",
        _script_argv(
            config,
            "build_icon_manifest_from_layout.py",
            str(project),
            "--write",
        ),
        condition=lambda cfg, _ctx: has_icon_slots(cfg.project) and not (cfg.project / "icon_manifest.json").is_file(),
    ))
    steps.append(StepSpec(
        "4.1.icon_manifest_exists",
        "icon",
        "conditional",
        "inline",
        None,
        [],
        inline=lambda cfg: {
            "valid": (cfg.project / "icon_manifest.json").is_file(),
            "errors": [] if (cfg.project / "icon_manifest.json").is_file()
            else ["icon_manifest.json is required for precise-lock or icon-slot pages."],
            "warnings": [],
        },
        condition=lambda cfg, _ctx: cfg.precise_lock or has_icon_slots(cfg.project) or (cfg.project / "icon_manifest.json").is_file(),
    ))
    steps.append(StepSpec(
        "4.2.verify_icon_contract",
        "icon",
        "hard",
        "verify_icon_contract",
        "verify_icon_contract.py",
        _icon_contract_argv(config, project, write_report=True),
        report_paths=["exports/qa/icon_contract_report.json"],
        condition=lambda cfg, _ctx: icon_contract_needed(cfg),
    ))
    steps.append(StepSpec(
        "4.3.chatgpt_precise_lock",
        "icon",
        "conditional",
        "verify_chatgpt_precise_rebuild_lock",
        "verify_chatgpt_precise_rebuild_lock.py",
        _script_argv(config, "verify_chatgpt_precise_rebuild_lock.py", str(project), "--enforce"),
        condition=lambda cfg, _ctx: cfg.precise_lock,
    ))

    crop_mode = rebuild_mode if rebuild_mode in {"vector-hifi", "text-editable-snapshot", "full-editable"} else "vector-hifi"
    steps.extend([
        StepSpec(
            "5.0.prerender_previews",
            "svg",
            "soft",
            "inline",
            None,
            [],
            inline=_prerender_previews_step,
        ),
        StepSpec(
            "5.0a.strip_alignment_underlay_before_validation",
            "svg",
            "hard",
            "inline",
            None,
            [],
            condition=lambda cfg, _ctx: stage_index(cfg.stage_requested) >= stage_index("svg"),
            inline=lambda cfg: strip_underlays(cfg.project),
        ),
        StepSpec(
            "5.0b.check_alignment_underlay_stripped",
            "svg",
            "hard",
            "inline",
            None,
            [],
            condition=lambda cfg, _ctx: stage_index(cfg.stage_requested) >= stage_index("svg"),
            inline=lambda cfg: check_no_underlays(cfg.project),
        ),
        StepSpec(
            "5.1.svg_quality_checker",
            "svg",
            "hard",
            "svg_quality_checker",
            "svg_quality_checker.py",
            _script_argv(config, "svg_quality_checker.py", str(project)),
        ),
        StepSpec(
            "5.2.verify_svg_preview",
            "svg",
            "hard",
            "verify_svg_preview",
            "verify_svg_preview.py",
            _script_argv(config, "verify_svg_preview.py", str(project), *_render_gate_args(config)),
            report_paths=["exports/preview_qa"],
        ),
        StepSpec(
            "5.2a.build_visual_contact_sheet",
            "svg",
            "soft",
            "build_visual_contact_sheet",
            "build_visual_contact_sheet.py",
            _script_argv(config, "build_visual_contact_sheet.py", str(project)),
            report_paths=["exports/qa/contact_sheets"],
        ),
        StepSpec(
            "5.3.layout_executor_contract",
            "svg",
            "hard",
            "inline",
            None,
            [],
            inline=_layout_executor_contract_step,
            # The executor contract checks an SVG against structure_contract /
            # required_primitives, which only exist for the v2.0 / 复刻流程2
            # vector-rebuild schema. text-editable-snapshot has no vector
            # structure to check, so the underlying tool errors immediately --
            # skip it for that mode instead of failing on an inapplicable check.
            condition=lambda cfg, _ctx: rebuild_mode != "text-editable-snapshot",
        ),
        StepSpec(
            "5.3b.svg_rebuild_completeness",
            "svg",
            "hard",
            "verify_svg_rebuild_completeness",
            "verify_svg_rebuild_completeness.py",
            _script_argv(
                config,
                "verify_svg_rebuild_completeness.py",
                str(project),
                "--strict",
                "--write-report",
            ),
            report_paths=["exports/qa/svg_completeness_report.json"],
            condition=lambda cfg, _ctx: has_layout_zones(cfg.project),
        ),
        StepSpec(
            "5.3c.verify_connector_geometry",
            "svg",
            "soft",
            "verify_connector_geometry",
            "verify_connector_geometry.py",
            _script_argv(config, "verify_connector_geometry.py", str(project), "--write-report"),
            report_paths=["exports/qa/connector_geometry_report.json"],
            condition=lambda cfg, _ctx: has_connector_svgs(cfg.project),
        ),
        StepSpec(
            "5.3d.connector_repairs",
            "svg",
            "soft",
            "apply_connector_repairs",
            "apply_connector_repairs.py",
            _script_argv(config, "apply_connector_repairs.py", str(project)),
            report_paths=["exports/qa/connector_repair_suggestions.json"],
            condition=lambda cfg, _ctx: has_connector_report_items(cfg.project),
        ),
        StepSpec(
            "5.4.verify_text_fit",
            "svg",
            "hard",
            "verify_text_fit",
            "verify_text_fit.py",
            _script_argv(config, "verify_text_fit.py", str(project)),
        ),
        StepSpec(
            "5.4a.text_fit_repairs",
            "svg",
            "soft",
            "apply_text_fit_repairs",
            "apply_text_fit_repairs.py",
            _script_argv(config, "apply_text_fit_repairs.py", str(project)),
            report_paths=["exports/qa/text_fit_repair_suggestions.json"],
            condition=lambda cfg, _ctx: has_text_fit_report_items(cfg.project),
        ),
        StepSpec(
            "5.4b.text_wrap_similarity",
            "svg",
            "soft",  # advisory: reference-similarity is reported, not a repair-loop trigger
            "verify_text_wrap_similarity",
            "verify_text_wrap_similarity.py",
            _script_argv(
                config,
                "verify_text_wrap_similarity.py",
                str(project),
                "--write-report",
            ),
            report_paths=["exports/qa/text_wrap_similarity_report.json"],
            condition=lambda cfg, _ctx: has_text_regions(cfg.project),
        ),
        StepSpec(
            "5.5.verify_svg_spacing",
            "svg",
            "hard",
            "verify_svg_spacing",
            "verify_svg_spacing.py",
            _script_argv(config, "verify_svg_spacing.py", str(project)),
        ),
        StepSpec(
            "5.5a.verify_alignment_rules",
            "svg",
            "hard",
            "verify_alignment_rules",
            "verify_alignment_rules.py",
            _script_argv(config, "verify_alignment_rules.py", str(project)),
        ),
        StepSpec(
            "5.5b.verify_composition_balance",
            "svg",
            "hard",
            "verify_composition_balance",
            "verify_composition_balance.py",
            _script_argv(config, "verify_composition_balance.py", str(project)),
        ),
        StepSpec(
            "5.5c.verify_transparent_assets",
            "svg",
            "hard",
            "verify_transparent_assets",
            "verify_transparent_assets.py",
            _script_argv(config, "verify_transparent_assets.py", str(project)),
        ),
        StepSpec(
            "5.5d.verify_layer_order",
            "svg",
            "hard",
            "verify_layer_order",
            "verify_layer_order.py",
            _script_argv(config, "verify_layer_order.py", str(project)),
        ),
        StepSpec(
            "5.5d.verify_architecture_inventory",
            "svg",
            "hard",
            "verify_architecture_inventory",
            "verify_architecture_inventory.py",
            _script_argv(config, "verify_architecture_inventory.py", str(project)),
        ),
        StepSpec(
            "5.5e.verify_asset_classification",
            "svg",
            "hard",
            "verify_asset_classification",
            "verify_asset_classification.py",
            _script_argv(config, "verify_asset_classification.py", str(project)),
        ),
        StepSpec(
            "5.6.build_image_crops_manifest",
            "svg",
            "hard",
            "build_image_crops_manifest",
            "build_image_crops_manifest.py",
            _script_argv(
                config,
                "build_image_crops_manifest.py",
                str(project),
                "--source",
                "output",
                "--mode",
                crop_mode,
            ),
            report_paths=["image_crops_manifest.json"],
        ),
        StepSpec(
            "5.7.verify_text_bearing_images",
            "svg",
            "hard",
            "verify_text_bearing_images",
            "verify_text_bearing_images.py",
            _script_argv(config, "verify_text_bearing_images.py", str(project), "--write-report"),
            report_paths=["qa_text_bearing_images.json"],
        ),
        StepSpec(
            "5.8.reference_similarity",
            "svg",
            "soft",  # advisory: reference-similarity is reported, not a repair-loop trigger
            "verify_reference_similarity",
            "verify_reference_similarity.py",
            _script_argv(
                config,
                "verify_reference_similarity.py",
                str(project),
                *_render_gate_args(config),
                "--threshold",
                str(config.reference_threshold),
                "--anchor-threshold",
                "3",
            ),
        ),
        StepSpec(
            "5.8b.object_similarity",
            "svg",
            "soft",  # advisory: reference-similarity is reported, not a repair-loop trigger
            "verify_reference_object_similarity",
            "verify_reference_object_similarity.py",
            _script_argv(
                config,
                "verify_reference_object_similarity.py",
                str(project),
                *_render_gate_args(config),
                "--bbox-threshold",
                "3",
                "--icon-threshold",
                "4",
                "--anchor-threshold",
                "3",
                "--write-report",
            ),
            report_paths=["exports/qa/object_similarity_report.json"],
        ),
        StepSpec(
            "5.8c.geometry_locks",
            "svg",
            "soft",  # advisory: reference-similarity is reported, not a repair-loop trigger
            "verify_geometry_locks",
            "verify_geometry_locks.py",
            _script_argv(
                config,
                "verify_geometry_locks.py",
                str(project),
                "--write-report",
            ),
            report_paths=["exports/qa/geometry_locks_report.json"],
            condition=lambda cfg, _ctx: has_geometry_locks(cfg.project),
        ),
        StepSpec(
            "5.8d.visual_diff_report",
            "svg",
            "soft",
            "generate_visual_diff_report",
            "generate_visual_diff_report.py",
            _script_argv(
                config,
                "generate_visual_diff_report.py",
                str(project),
                *_render_gate_args(config),
                "--write-report",
            ),
            report_paths=[
                "exports/qa/failure_summary.md",
                "exports/qa/compare_side_by_side.png",
                "exports/qa/visual_diff_report.json",
            ],
        ),
        StepSpec(
            "5.9.manifest_svg",
            "svg",
            "hard",
            "verify_slide_image_rebuild_manifest",
            "verify_slide_image_rebuild_manifest.py",
            _script_argv(config, "verify_slide_image_rebuild_manifest.py", str(project), "--stage", "svg"),
        ),
        StepSpec(
            "5.10.icon_contract_svg",
            "svg",
            "conditional",
            "verify_icon_contract",
            "verify_icon_contract.py",
            _icon_contract_argv(config, project, write_report=True),
            report_paths=["exports/qa/icon_contract_report.json"],
            condition=lambda cfg, ctx: (
                not ctx.get("icon_contract_verified")
                and icon_contract_needed(cfg)
            ),
        ),
        StepSpec(
            "5.11.notes_total_md",
            "svg",
            "hard",
            "inline",
            None,
            [],
            inline=lambda cfg: check_notes_total_md(cfg.project),
        ),
        StepSpec(
            "5.12.aggregate_repair_tasks",
            "svg",
            "hard",
            "aggregate_repair_tasks",
            "aggregate_repair_tasks.py",
            _script_argv(
                config,
                "aggregate_repair_tasks.py",
                str(project),
                "--write-report",
                *(() if config.auto_repair else ("--enforce",)),
            ),
            report_paths=["exports/qa/repair_tasks.json"],
        ),
        StepSpec(
            "5.12a.apply_rebuild_repairs",
            "svg",
            "soft",
            "apply_rebuild_repairs",
            "apply_rebuild_repairs.py",
            _script_argv(
                config,
                "apply_rebuild_repairs.py",
                str(project),
                "--write",
                "--refresh-tasks",
            ),
            condition=lambda cfg, _ctx: cfg.auto_repair,
            report_paths=["exports/qa/repair_tasks.json"],
        ),
        StepSpec(
            "5.12b.aggregate_repair_tasks_enforce",
            "svg",
            "hard",
            "aggregate_repair_tasks",
            "aggregate_repair_tasks.py",
            _script_argv(
                config,
                "aggregate_repair_tasks.py",
                str(project),
                "--write-report",
                "--enforce",
            ),
            condition=lambda cfg, _ctx: cfg.auto_repair,
            report_paths=["exports/qa/repair_tasks.json"],
        ),
        StepSpec(
            "5.13.inject_alignment_underlay",
            "svg",
            "soft",
            "inline",
            None,
            [],
            condition=lambda cfg, _ctx: cfg.stage_requested == "svg",
            inline=lambda cfg: inject_underlays(cfg.project),
        ),
    ])

    if not config.skip_export:
        steps.extend([
            StepSpec(
                "6.1.total_md_split",
                "export",
                "hard",
                "total_md_split",
                "total_md_split.py",
                _script_argv(config, "total_md_split.py", str(project)),
            ),
            StepSpec(
                "6.2.finalize_svg",
                "export",
                "hard",
                "finalize_svg",
                "finalize_svg.py",
                _script_argv(config, "finalize_svg.py", str(project)),
                report_paths=["svg_final"],
            ),
            StepSpec(
                "6.3.svg_to_pptx",
                "export",
                "hard",
                "svg_to_pptx",
                "svg_to_pptx.py",
                _script_argv(
                    config,
                    "svg_to_pptx.py",
                    str(project),
                    "-s",
                    "output",
                    "--merge-paragraphs" if export_mode == "editable" else "--no-merge",
                    "--only",
                    "native",
                    "--conversion-trace",
                    "--no-cache",
                ),
                report_paths=["exports", "exports/pptx/conversion_trace.json"],
            ),
            StepSpec(
                "6.4.svg_final_freshness",
                "export",
                "hard",
                "inline",
                None,
                [],
                inline=lambda cfg: check_svg_final_freshness(cfg.project),
            ),
            StepSpec(
                "6.5.sanitize_pptx",
                "export",
                "hard",
                "inline",
                None,
                [],
                inline=_sanitize_pptx_step,
            ),
        ])

        steps.extend([
            StepSpec(
                "7.1.verify_editable_pptx",
                "post-export",
                "hard",
                "verify_editable_pptx",
                "verify_editable_pptx.py",
                [],
                inline=lambda cfg: _verify_editable_pptx_step(cfg),
            ),
            StepSpec(
                "7.2.build_image_crops_manifest_final",
                "post-export",
                "hard",
                "build_image_crops_manifest",
                "build_image_crops_manifest.py",
                _script_argv(
                    config,
                    "build_image_crops_manifest.py",
                    str(project),
                    "--source",
                    "final",
                    "--mode",
                    crop_mode,
                ),
            ),
            StepSpec(
                "7.3.verify_text_bearing_final",
                "post-export",
                "hard",
                "verify_text_bearing_images",
                "verify_text_bearing_images.py",
                _script_argv(config, "verify_text_bearing_images.py", str(project), "--write-report"),
            ),
            # 7.4.reference_similarity_final removed: similarity is advisory and the
            # SVG-stage gate 5.8 already reports it; svg_to_pptx is deterministic, so a
            # second post-export render added cost without new signal.
            StepSpec(
                "7.5.rebuild_regression",
                "post-export",
                "hard",
                "verify_rebuild_regression",
                "verify_rebuild_regression.py",
                _script_argv(
                    config,
                    "verify_rebuild_regression.py",
                    str(project),
                    "--mode",
                    "auto",
                    *(["--render"] if config.render else []),
                ),
                report_paths=["rebuild_regression_report.json"],
            ),
            StepSpec(
                "7.6.manifest_export",
                "post-export",
                "hard",
                "verify_slide_image_rebuild_manifest",
                "verify_slide_image_rebuild_manifest.py",
                _script_argv(config, "verify_slide_image_rebuild_manifest.py", str(project), "--stage", "export"),
            ),
            StepSpec(
                "7.7.verify_pptx_export_source",
                "post-export",
                "hard",
                "verify_pptx_export_source",
                "verify_pptx_export_source.py",
                _script_argv(config, "verify_pptx_export_source.py", str(project), "--strict", "--write-report"),
                report_paths=["exports/qa/export_source_report.json"],
            ),
            StepSpec(
                "7.8.officecli_screenshot",
                "post-export",
                "hard",
                "officecli_screenshot",
                None,
                [],
                inline=lambda cfg: _officecli_screenshot_step(cfg),
                report_paths=["exports/qa/officecli_screenshot.json", "exports/qa/officecli_screenshot.png"],
            ),
            StepSpec(
                "7.9.generate_qa_report",
                "post-export",
                "hard",
                "generate_rebuild_qa_report",
                "generate_rebuild_qa_report.py",
                _script_argv(config, "generate_rebuild_qa_report.py", str(project), *rebuild2_args),
                report_paths=["qa_report.md"],
            ),
            # 7.9.visual_diff_report removed: duplicate of the advisory SVG-stage
            # 5.8d.visual_diff_report; the post-export re-render produced the same diff.
        ])

        steps.append(StepSpec(
            "8.1.artifact_manifest_check",
            "package",
            "hard",
            "inline",
            None,
            [],
            inline=lambda cfg: check_artifact_files(
                cfg.project,
                package_artifact_paths(cfg.project, latest_pptx(cfg.project)),
            ),
        ))

    return steps


def _prerender_previews_step(config: RunConfig) -> dict[str, Any]:
    """Render all page previews concurrently to warm the mtime-keyed preview cache.

    Soft and best-effort: the svg-stage gates each render lazily and cache previews
    by mtime, so a missed prerender just means a gate renders that page serially.
    Real work only for multi-page decks (the serial-render hotspot); single-page
    is a no-op. Never fails the run.
    """
    if not config.render:
        return {"valid": True, "warnings": [], "rendered": 0, "skip_reason": "no_render"}
    svg_dir = config.project / "svg_output"
    svgs = sorted(svg_dir.glob("*.svg")) if svg_dir.is_dir() else []
    if len(svgs) < 2:
        return {"valid": True, "warnings": [], "rendered": 0, "skip_reason": "single_page"}

    try:
        from render_preview_backend import ensure_preview_for_svg
    except ImportError:  # pragma: no cover - package-context import
        from scripts.render_preview_backend import ensure_preview_for_svg  # type: ignore

    preview_dir = config.project / "exports" / "preview_qa"
    preview_dir.mkdir(parents=True, exist_ok=True)

    def _render_one(svg: Path) -> tuple[bool, str]:
        preview = preview_dir / f"{svg.stem}.preview.png"
        try:
            result = ensure_preview_for_svg(
                config.project,
                svg,
                preview,
                render=True,
                render_backend=config.preview_render_backend,
            )
            return (result.ok, "" if result.ok else f"{svg.name}: {'; '.join(result.errors)}")
        except Exception as exc:  # best-effort warmer; a failure just defers to the gate
            return (False, f"{svg.name}: {exc}")

    warnings: list[str] = []
    rendered = 0
    max_workers = min(8, (os.cpu_count() or 2), len(svgs))
    with ThreadPoolExecutor(max_workers=max_workers) as pool:
        for ok, msg in pool.map(_render_one, svgs):
            if ok:
                rendered += 1
            elif msg:
                warnings.append(msg)
    return {"valid": True, "warnings": warnings, "rendered": rendered, "page_count": len(svgs)}


def _consolidate_page_svgs_step(config: RunConfig) -> dict[str, Any]:
    """Copy each page's authored svg_output/<page_id>.svg into the project-root
    svg_output/ directory.

    svg_quality_checker.py, verify_svg_preview.py, verify_svg_rebuild_completeness.py,
    and svg_to_pptx.py all only look at <project>/svg_output (or svg_final) -- none
    of them know about manifest page_dir. For a single-page project page_dir()
    already resolves to the project root, so this is a no-op there; for a
    multi-page project (page_dir: "pages/P01", ...) it's required before any
    SVG-stage check or export can see the per-page SVGs at all.
    """
    warnings: list[str] = []
    copied: list[str] = []
    for page in manifest_pages(config.project):
        page_id = str(page.get("page_id", "")).strip() or "01"
        page_root = page_dir(config.project, page)
        if page_root == config.project:
            continue
        src_dir = page_root / "svg_output"
        if not src_dir.is_dir():
            continue
        dest_dir = config.project / "svg_output"
        dest_dir.mkdir(parents=True, exist_ok=True)
        for svg in sorted(src_dir.glob("*.svg")):
            dest = dest_dir / svg.name
            try:
                if not dest.is_file() or dest.read_bytes() != svg.read_bytes():
                    dest.write_bytes(svg.read_bytes())
                    copied.append(str(dest.relative_to(config.project)))
            except OSError as exc:
                warnings.append(f"Page `{page_id}`: failed to consolidate {svg}: {exc}")
    return {"valid": True, "errors": [], "warnings": warnings, "copied": copied}


def _layout_executor_contract_step(config: RunConfig) -> dict[str, Any]:
    """Run verify_layout_executor_contract.py once per page directory.

    The underlying script only looks at <target>/layout_reference.json,
    <target>/svg_build_plan.json, and <target>/svg_output|svg_final -- it has
    no multi-page awareness of its own. For multi-page projects (page_dir set
    per manifest page) that means invoking it against the project root finds
    nothing; pass each page's own directory as the target instead.
    """
    pages = layout_paths(config.project)
    bases = [layout_path.parent for _page_id, layout_path in pages] or [config.project]
    errors: list[str] = []
    warnings: list[str] = []
    for base in bases:
        result = subprocess.run(
            [config.python, str(config.scripts_dir / "verify_layout_executor_contract.py"), str(base)],
            text=True,
            capture_output=True,
            check=False,
        )
        payload = parse_tool_output(result.stdout, result.returncode)
        prefix = f"{base.relative_to(config.project)}: " if base != config.project else ""
        errors.extend(f"{prefix}{item}" for item in payload.get("errors", []) if isinstance(item, str))
        warnings.extend(f"{prefix}{item}" for item in payload.get("warnings", []) if isinstance(item, str))
    return {"valid": not errors, "errors": errors, "warnings": warnings}


def _sanitize_pptx_step(config: RunConfig) -> dict[str, Any]:
    """Run sanitize_pptx_package.py --in-place against the freshly exported PPTX.

    verify_rebuild_regression.py (post-export) hard-fails without a sibling
    <pptx>.compat_report.json next to the export. The sanitizer is the only
    tool that writes it, and svg_to_pptx.py never calls it on its own --
    this step has to run between export and the post-export regression check.
    """
    pptx = latest_pptx(config.project)
    if pptx is None:
        return {"valid": False, "errors": ["No exported PPTX found in exports/."], "warnings": []}
    result = subprocess.run(
        [config.python, str(config.scripts_dir / "sanitize_pptx_package.py"), str(pptx), "--in-place"],
        text=True,
        capture_output=True,
        check=False,
    )
    payload = parse_tool_output(result.stdout, result.returncode)
    payload["pptx"] = str(pptx)
    payload["returncode"] = result.returncode
    return payload


def _verify_editable_pptx_step(config: RunConfig) -> dict[str, Any]:
    pptx = latest_pptx(config.project)
    if pptx is None:
        return {"valid": False, "errors": ["No exported PPTX found in exports/."], "warnings": []}
    result = subprocess.run(
        [
            config.python,
            str(config.scripts_dir / "verify_editable_pptx.py"),
            str(pptx),
            "--write-report",
            "--project",
            str(config.project),
        ],
        text=True,
        capture_output=True,
        check=False,
    )
    payload = parse_tool_output(result.stdout, result.returncode)
    payload["pptx"] = str(pptx)
    payload["returncode"] = result.returncode
    return payload


def _officecli_screenshot_step(config: RunConfig) -> dict[str, Any]:
    pptx = latest_pptx(config.project)
    if pptx is None:
        return {"valid": False, "errors": ["No exported PPTX found in exports/."], "warnings": []}

    officecli = _resolve_officecli_binary()
    if officecli is None:
        return {
            "valid": False,
            "errors": ["OfficeCLI binary not found. Expected repository-local skills/officecli/bin/release/officecli-* or PATH officecli."],
            "warnings": [],
        }

    qa_dir = config.project / "exports" / "qa"
    qa_dir.mkdir(parents=True, exist_ok=True)
    screenshot = qa_dir / "officecli_screenshot.png"
    report_path = qa_dir / "officecli_screenshot.json"
    slide_count = pptx_slide_count(pptx)
    grid_cols = min(4, max(1, slide_count)) if slide_count else 1
    argv = [
        str(officecli),
        "view",
        str(pptx),
        "screenshot",
        "-o",
        str(screenshot),
        "--render",
        "html",
        "--json",
    ]
    if slide_count > 1:
        argv.extend(["--page", f"1-{slide_count}", "--grid", str(grid_cols)])

    result = subprocess.run(
        argv,
        cwd=str(config.repo_root),
        text=True,
        capture_output=True,
        check=False,
    )
    errors: list[str] = []
    warnings: list[str] = []
    if result.returncode != 0:
        message = result.stderr.strip() or result.stdout.strip() or f"OfficeCLI screenshot failed with exit code {result.returncode}."
        errors.append(message.splitlines()[-1])
    if not screenshot.is_file():
        errors.append(f"OfficeCLI screenshot was not created: {screenshot}")
    elif screenshot.stat().st_size == 0:
        errors.append(f"OfficeCLI screenshot is empty: {screenshot}")

    stdout_payload: Any
    try:
        stdout_payload = json.loads(result.stdout) if result.stdout.strip() else None
    except json.JSONDecodeError:
        stdout_payload = result.stdout.strip()
    if result.returncode != 0 and not result.stderr.strip() and isinstance(stdout_payload, dict):
        error_payload = stdout_payload.get("error")
        if isinstance(error_payload, dict):
            error_message = str(error_payload.get("error", "")).strip()
            if error_message:
                errors[0:1] = [error_message]
        elif isinstance(error_payload, str) and error_payload.strip():
            errors[0:1] = [error_payload.strip()]

    report = {
        "valid": not errors,
        "workflow": "slide-image-rebuild",
        "check": "officecli_screenshot",
        "pptx": str(pptx.relative_to(config.project)),
        "slide_count": slide_count,
        "officecli": str(officecli),
        "screenshot": str(screenshot.relative_to(config.project)) if screenshot.exists() else None,
        "command": argv,
        "returncode": result.returncode,
        "stdout": stdout_payload,
        "stderr": result.stderr.strip(),
        "errors": errors,
        "warnings": warnings,
    }
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    return report


def _capture_path(project: Path, step_id: str, suffix: str) -> Path:
    safe = step_id.replace(".", "_")
    return project / "exports" / "qa" / "captures" / f"{safe}.{suffix}"


def _write_capture(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    encoded = content.encode("utf-8")
    truncated = len(encoded) > CAPTURE_MAX_BYTES
    if truncated:
        encoded = encoded[:CAPTURE_MAX_BYTES]
    path.write_bytes(encoded)
    if truncated:
        path.with_suffix(path.suffix + ".truncated").write_text("1\n", encoding="utf-8")


def _extract_tool_errors(payload: dict[str, Any], source_prefix: str) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    errors: list[dict[str, Any]] = []
    warnings: list[dict[str, Any]] = []
    for idx, item in enumerate(payload.get("errors", []) if isinstance(payload.get("errors"), list) else []):
        if isinstance(item, dict):
            errors.append({
                "level": "error",
                "code": str(item.get("code", "tool_error")),
                "message": str(item.get("message", item)),
                "path": str(item.get("path", "")),
                "source": f"{source_prefix}.errors[{idx}]",
            })
        elif isinstance(item, str):
            errors.append({
                "level": "error",
                "code": "tool_error",
                "message": item,
                "source": f"{source_prefix}.errors[{idx}]",
            })
    for idx, item in enumerate(payload.get("warnings", []) if isinstance(payload.get("warnings"), list) else []):
        if isinstance(item, dict):
            warnings.append({
                "level": "warning",
                "code": str(item.get("code", "tool_warning")),
                "message": str(item.get("message", item)),
                "path": str(item.get("path", "")),
                "source": f"{source_prefix}.warnings[{idx}]",
            })
        elif isinstance(item, str):
            warnings.append({
                "level": "warning",
                "code": "tool_warning",
                "message": item,
                "source": f"{source_prefix}.warnings[{idx}]",
            })
    if not errors and payload.get("valid") is False:
        errors.append({
            "level": "error",
            "code": "tool_invalid",
            "message": "Tool reported valid=false without detailed errors.",
            "source": f"{source_prefix}.valid",
        })
    return errors, warnings


def run_step(config: RunConfig, spec: StepSpec, seq: int, ctx: dict[str, Any]) -> StepRecord:
    record = StepRecord(spec=spec, seq=seq)
    started = utc_now()
    record.timing["started_at"] = started

    if should_trust_skip_layout_step(spec, ctx):
        record.status = "skipped"
        record.result = {
            "exit_code": 0,
            "valid": True,
            "skipped": True,
            "skip_reason": "layout_stamp_trusted",
        }
        record.timing["finished_at"] = utc_now()
        return record

    if should_reuse_skip_svg_step(spec, ctx):
        record.status = "skipped"
        record.result = {
            "exit_code": 0,
            "valid": True,
            "skipped": True,
            "skip_reason": "svg_unchanged_reuse",
        }
        record.timing["finished_at"] = utc_now()
        return record

    if spec.condition is not None and not spec.condition(config, ctx):
        record.status = "skipped"
        record.result = {"exit_code": 0, "valid": True, "skipped": True, "skip_reason": "condition_not_met"}
        record.timing["finished_at"] = utc_now()
        return record

    if config.dry_run:
        record.status = "skipped"
        record.result = {"exit_code": 0, "valid": True, "skipped": True, "skip_reason": "dry_run"}
        record.timing["finished_at"] = utc_now()
        return record

    payload: dict[str, Any]
    exit_code = 0
    stdout_text = ""
    stderr_text = ""

    if spec.inline is not None:
        payload = spec.inline(config)
        exit_code = 0 if payload.get("valid", False) else 1
        stdout_text = json.dumps(payload, ensure_ascii=False, indent=2)
    else:
        if spec.step_id == "7.1.verify_editable_pptx":
            payload = _verify_editable_pptx_step(config)
            exit_code = 0 if payload.get("valid") else 1
            stdout_text = json.dumps(payload, ensure_ascii=False, indent=2)
        else:
            result = subprocess.run(
                spec.argv,
                cwd=str(config.repo_root),
                text=True,
                capture_output=True,
                check=False,
            )
            exit_code = result.returncode
            stdout_text = result.stdout
            stderr_text = result.stderr
            payload = parse_tool_output(stdout_text, exit_code)

    capture_base = _capture_path(config.project, spec.step_id, "stdout")
    parsed = False
    ref_path: str | None = None
    try:
        json.loads(stdout_text)
        parsed = True
        capture_path = capture_base.with_suffix(".stdout.json")
    except json.JSONDecodeError:
        capture_path = capture_base.with_suffix(".stdout.txt")
    _write_capture(capture_path, stdout_text)
    ref_path = str(capture_path.relative_to(config.project))
    if stderr_text:
        stderr_path = _capture_path(config.project, spec.step_id, "stderr.txt")
        _write_capture(stderr_path, stderr_text)

    tool_errors, tool_warnings = _extract_tool_errors(payload, "tool_payload")
    record.errors.extend(tool_errors)
    record.warnings.extend(tool_warnings)

    if exit_code != 0 and stderr_text.strip():
        stderr_summary = stderr_text.strip().splitlines()[-1]
        if record.errors and record.errors[-1].get("code") == "tool_invalid":
            record.errors[-1]["message"] = stderr_summary
            record.errors[-1]["source"] = "subprocess.stderr"
        elif not any(stderr_summary in str(err.get("message", "")) for err in record.errors):
            record.errors.append({
                "level": "error",
                "code": "tool_exit_nonzero",
                "message": stderr_summary,
                "source": "subprocess.stderr",
            })

    valid = payload.get("valid", exit_code == 0) and exit_code == 0
    if spec.gate == "soft" and not valid:
        record.status = "warned"
        valid = True
    elif not valid:
        record.status = "failed"
    else:
        record.status = "passed"

    report_path = None
    for rel in spec.report_paths:
        candidate = config.project / rel
        if candidate.exists():
            report_path = rel
            record.outputs["report_files"].append(rel)

    record.result = {
        "exit_code": exit_code,
        "valid": valid if record.status != "failed" else False,
        "skipped": False,
        "stdout_json": {
            "parsed": parsed,
            "path": report_path,
            "inline": spec.inline is not None and spec.script is None and spec.step_id != "7.1.verify_editable_pptx",
            "ref": ref_path,
        },
    }
    record.timing["finished_at"] = utc_now()
    if spec.step_id == "4.2.verify_icon_contract" and record.status == "passed":
        ctx["icon_contract_verified"] = True
    return record


def step_record_to_dict(record: StepRecord) -> dict[str, Any]:
    spec = record.spec
    return {
        "id": spec.step_id,
        "stage": spec.stage,
        "stage_index": STAGE_ORDER[spec.stage],
        "seq": record.seq,
        "gate": spec.gate,
        "status": record.status,
        "tool": {
            "name": spec.tool_name,
            "script": f"scripts/{spec.script}" if spec.script else None,
        },
        "invocation": {"argv": record.spec.argv},
        "scope": {
            "page_id": spec.scope_page_id,
            "multi_page": spec.scope_page_id is not None,
        },
        "timing": record.timing,
        "result": record.result,
        "outputs": record.outputs,
        "errors": record.errors,
        "warnings": record.warnings,
    }


def summarize_stages(steps: list[StepRecord]) -> list[dict[str, Any]]:
    grouped: dict[str, list[StepRecord]] = {}
    for record in steps:
        grouped.setdefault(record.spec.stage, []).append(record)

    summaries: list[dict[str, Any]] = []
    for stage, stage_name in sorted(STAGE_ORDER.items(), key=lambda item: item[1]):
        records = grouped.get(stage, [])
        if not records:
            continue
        failed = [record for record in records if record.status == "failed"]
        passed = [record for record in records if record.status == "passed"]
        skipped = [record for record in records if record.status == "skipped"]
        summaries.append({
            "stage": stage,
            "stage_index": stage_name,
            "status": "failed" if failed else "passed",
            "valid": not failed,
            "steps_total": len(records),
            "steps_passed": len(passed),
            "steps_failed": len(failed),
            "steps_skipped": len(skipped),
            "failed_step_ids": [record.spec.step_id for record in failed],
            "step_ids": [record.spec.step_id for record in records],
        })
    return summaries


def build_report(
    config: RunConfig,
    *,
    run_id: str,
    started_at: str,
    completed_at: str,
    status: str,
    steps: list[StepRecord],
) -> dict[str, Any]:
    blocking_errors: list[dict[str, Any]] = []
    warnings: list[dict[str, Any]] = []
    failed_step_id: str | None = None

    for record in steps:
        for warning in record.warnings:
            warnings.append({**warning, "step_id": record.spec.step_id, "stage": record.spec.stage})
        if record.status != "failed":
            continue
        if failed_step_id is None:
            failed_step_id = record.spec.step_id
        for error in record.errors:
            blocking_errors.append({
                "step_id": record.spec.step_id,
                "stage": record.spec.stage,
                "code": error.get("code", "step_failed"),
                "message": error.get("message", ""),
                "path": error.get("path", ""),
                "page_id": record.spec.scope_page_id,
                "stdout_json_ref": record.result.get("stdout_json", {}).get("ref"),
            })

    valid = status == "completed" and not blocking_errors
    pptx = latest_pptx(config.project)
    artifacts = {
        "strict_run_report": "exports/qa/strict_run_report.json",
        "qa_report_md": "qa_report.md" if (config.project / "qa_report.md").is_file() else None,
        "rebuild_regression_report": "rebuild_regression_report.json"
        if (config.project / "rebuild_regression_report.json").is_file() else None,
        "latest_pptx": str(pptx.relative_to(config.project)) if pptx else None,
        "conversion_trace": "exports/pptx/conversion_trace.json"
        if (config.project / "exports" / "pptx" / "conversion_trace.json").is_file() else None,
        "compat_report": str(pptx.with_name(pptx.name + ".compat_report.json").relative_to(config.project))
        if pptx and pptx.with_name(pptx.name + ".compat_report.json").is_file() else None,
    }
    artifacts = {key: value for key, value in artifacts.items() if value}

    passed = sum(1 for record in steps if record.status == "passed")
    failed = sum(1 for record in steps if record.status == "failed")
    skipped = sum(1 for record in steps if record.status == "skipped")

    stage_reached = config.stage_requested
    if failed_step_id:
        for record in steps:
            if record.spec.step_id == failed_step_id:
                stage_reached = record.spec.stage
                break

    return {
        "version": REPORT_VERSION,
        "workflow": "slide-image-rebuild",
        "check": "strict_run",
        "run_id": run_id,
        "generated_at": started_at,
        "completed_at": completed_at,
        "status": status,
        "valid": valid,
        "project": str(config.project.relative_to(config.repo_root))
        if config.project.is_relative_to(config.repo_root)
        else str(config.project),
        "runner": {
            "script": STRICT_RUNNER_REL,
            "stage_requested": config.stage_requested,
            "stage_reached": stage_reached,
            "stop_on_error": config.stop_on_error,
            "dry_run": config.dry_run,
            "skip_export": config.skip_export,
        },
        "resolved": {
            "rebuild_mode": config.rebuild_mode,
            "export_mode": config.export_mode,
            "precise_lock": config.precise_lock,
            "render_enabled": config.render,
            "preview_render_backend": config.preview_render_backend,
            "reference_threshold": config.reference_threshold,
            "icon_enforce": config.icon_enforce,
            "page_count": len(manifest_pages(config.project)),
            "pages": [str(page.get("page_id", "")) for page in manifest_pages(config.project)],
        },
        "summary": {
            "steps_total": len(steps),
            "steps_passed": passed,
            "steps_failed": failed,
            "steps_skipped": skipped,
            "failed_step_id": failed_step_id,
            "first_blocking_error_code": blocking_errors[0]["code"] if blocking_errors else None,
        },
        "blocking_errors": blocking_errors,
        "warnings": warnings,
        "artifacts": artifacts,
        "stages": summarize_stages(steps),
        "steps": [step_record_to_dict(record) for record in steps],
    }


def resolve_resume_stage(config: RunConfig, failed_stage: str | None) -> str:
    if not failed_stage:
        return config.stage_requested
    if failed_stage in {"export", "post-export", "package"}:
        return "full"
    if failed_stage == "pre-export":
        notes = config.project / "notes" / "total.md"
        return "full" if notes.is_file() else "pre-export"
    return "svg"


def format_resume_command(config: RunConfig, resume_stage: str) -> str:
    project_arg = str(config.project)
    if config.project.is_relative_to(config.repo_root):
        project_arg = str(config.project.relative_to(config.repo_root))
    argv = [
        config.python,
        str(config.scripts_dir / "run_slide_image_rebuild_strict.py"),
        "--project",
        project_arg,
        "--stage",
        resume_stage,
        "--export-mode",
        config.export_mode,
    ]
    if config.render or stage_index(resume_stage) >= stage_index("svg"):
        argv.append("--render")
    if config.precise_lock:
        argv.append("--precise-lock")
    if config.reference_threshold != 58.0:
        argv.extend(["--reference-threshold", str(config.reference_threshold)])
    if config.icon_enforce:
        argv.append("--icon-enforce")
    if config.skip_export and resume_stage == "svg":
        argv.append("--skip-export")
    return " ".join(shlex.quote(part) for part in argv)


def collect_reread_paths(
    project: Path,
    blocking_errors: list[dict[str, Any]],
    failed_records: list[StepRecord],
) -> list[str]:
    paths: list[str] = []
    seen: set[str] = set()

    def add(path: str) -> None:
        if path and path not in seen:
            seen.add(path)
            paths.append(path)

    for error in blocking_errors:
        add(str(error.get("stdout_json_ref", "")).strip())

    for record in failed_records:
        for rel in record.outputs.get("report_files", []):
            if (project / rel).is_file():
                add(rel)

    for candidate in (
        "exports/qa/repair_tasks.json",
        "exports/qa/object_similarity_report.json",
        "exports/qa/text_wrap_similarity_report.json",
        "exports/qa/geometry_locks_report.json",
        "exports/qa/layout_family_contract_report.json",
        "exports/qa/icon_contract_report.json",
        "exports/qa/visual_diff_report.json",
    ):
        if (project / candidate).is_file():
            add(candidate)

    return paths


def build_agent_summary(
    report: dict[str, Any],
    config: RunConfig,
    *,
    failed_records: list[StepRecord],
) -> dict[str, Any]:
    summary = report.get("summary", {})
    failed_step_id = summary.get("failed_step_id")
    failed_stage = report.get("runner", {}).get("stage_reached")
    blocking_errors = report.get("blocking_errors", [])
    resume_stage = resolve_resume_stage(config, failed_stage if blocking_errors else None)

    artifact_candidates = {
        "strict_run_report": REPORT_REL_PATH,
        "strict_run_summary": SUMMARY_REL_PATH,
        "latest_pptx": report.get("artifacts", {}).get("latest_pptx"),
        "qa_report_md": report.get("artifacts", {}).get("qa_report_md"),
    }
    if (config.project / "exports" / "qa" / "editability_score.json").is_file():
        artifact_candidates["editability_score"] = "exports/qa/editability_score.json"
    artifact_refs = {key: value for key, value in artifact_candidates.items() if value}

    editability_summary: dict[str, Any] = {}
    editability_path = config.project / "exports" / "qa" / "editability_score.json"
    if editability_path.is_file():
        editability_payload = load_json(editability_path)
        score = editability_payload.get("editable_score")
        if isinstance(score, (int, float)):
            editability_summary = {
                "editable_score": score,
                "text_frame_count": editability_payload.get("text_frame_count"),
                "shape_count": editability_payload.get("shape_count"),
                "picture_count": editability_payload.get("picture_count"),
            }

    return {
        "version": SUMMARY_VERSION,
        "workflow": report.get("workflow", "slide-image-rebuild"),
        "check": "strict_run_summary",
        "run_id": report.get("run_id"),
        "generated_at": report.get("generated_at"),
        "completed_at": report.get("completed_at"),
        "valid": report.get("valid", False),
        "status": report.get("status"),
        "project": report.get("project"),
        "failed_step_id": failed_step_id,
        "failed_stage": failed_stage,
        "first_blocking_error_code": summary.get("first_blocking_error_code"),
        "blocking_errors": blocking_errors,
        "warnings_count": len(report.get("warnings", [])),
        "steps_total": summary.get("steps_total", 0),
        "steps_passed": summary.get("steps_passed", 0),
        "steps_failed": summary.get("steps_failed", 0),
        "steps_skipped": summary.get("steps_skipped", 0),
        "resolved": report.get("resolved", {}),
        **({"editability_score": editability_summary} if editability_summary else {}),
        "runner": {
            "stage_requested": report.get("runner", {}).get("stage_requested"),
            "stage_reached": failed_stage,
            "dry_run": report.get("runner", {}).get("dry_run", False),
        },
        "artifacts": artifact_refs,
        "next_action": {
            "reread": collect_reread_paths(config.project, blocking_errors, failed_records),
            "resume_stage": resume_stage,
            "resume_command": format_resume_command(config, resume_stage),
        },
    }


def verify_agent_summary_consistency(
    report: dict[str, Any],
    summary: dict[str, Any],
) -> list[str]:
    errors: list[str] = []
    for field in ("valid", "status", "run_id"):
        if report.get(field) != summary.get(field):
            errors.append(f"{field} mismatch: report={report.get(field)!r} summary={summary.get(field)!r}")
    if report.get("blocking_errors", []) != summary.get("blocking_errors", []):
        errors.append("blocking_errors mismatch between report and summary")
    report_summary = report.get("summary", {})
    # failed_step_id lives under report["summary"], but at summary top level.
    if report_summary.get("failed_step_id") != summary.get("failed_step_id"):
        errors.append(
            f"failed_step_id mismatch: report={report_summary.get('failed_step_id')!r} "
            f"summary={summary.get('failed_step_id')!r}"
        )
    for field in ("steps_total", "steps_passed", "steps_failed", "steps_skipped"):
        if report_summary.get(field) != summary.get(field):
            errors.append(f"summary.{field} mismatch")
    return errors


def filter_steps_by_stage(steps: list[StepSpec], stage_requested: str) -> list[StepSpec]:
    max_index = stage_index(stage_requested)
    return [step for step in steps if STAGE_ORDER[step.stage] <= max_index]


def _append_timing_log(project: Path, run_id: str, records: list[StepRecord]) -> None:
    """Append one per-round timing line to exports/qa/strict_run_timings.jsonl.

    The main report is overwritten each run; this sidecar accumulates so the
    real cost of each round (and each gate) stays measurable across repairs.
    """
    steps = [
        {
            "id": record.spec.step_id,
            "status": record.status,
            "duration_ms": record.timing.get("duration_ms", 0.0),
        }
        for record in records
    ]
    line = {
        "run_id": run_id,
        "total_ms": round(sum(s["duration_ms"] for s in steps), 1),
        "step_count": len(steps),
        "slowest": sorted(steps, key=lambda s: -s["duration_ms"])[:5],
        "steps": steps,
    }
    log_path = project / "exports" / "qa" / "strict_run_timings.jsonl"
    try:
        with log_path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(line, ensure_ascii=False) + "\n")
    except OSError as exc:  # timing log is best-effort; never fail a run on it
        print(f"Warning: could not write timing log ({exc}).", file=sys.stderr)


def _svg_stage_reusable(config: RunConfig, current_sig: str | None) -> bool:
    """True when --incremental and a prior run validated this exact svg_output."""
    if not config.incremental or not current_sig:
        return False
    stored = load_json(config.project / SVG_STAGE_STATE_REL_PATH)
    return bool(stored.get("valid")) and stored.get("signature") == current_sig


def _write_svg_stage_state(project: Path, signature: str | None, records: list[StepRecord]) -> None:
    """Record whether the svg stage validated for this svg_output signature.

    Only written when the svg stage actually ran (not reused); reused runs leave
    the prior state intact. ``valid`` is False if any svg-stage gate failed, so a
    later --incremental run will re-verify rather than trust a bad stage.
    """
    svg_records = [r for r in records if r.spec.stage == "svg" and r.status != "skipped"]
    if not signature or not svg_records:
        return
    valid = all(r.status in {"passed", "warned"} for r in svg_records)
    state = {"signature": signature, "valid": valid, "step_count": len(svg_records)}
    try:
        (project / SVG_STAGE_STATE_REL_PATH).write_text(
            json.dumps(state, ensure_ascii=False), encoding="utf-8",
        )
    except OSError as exc:  # best-effort; never fail a run on the cache
        print(f"Warning: could not write svg-stage state ({exc}).", file=sys.stderr)


def run_pipeline(config: RunConfig) -> dict[str, Any]:
    qa_dir = config.project / "exports" / "qa"
    qa_dir.mkdir(parents=True, exist_ok=True)

    started_at = utc_now()
    run_id = started_at.replace(":", "").replace("-", "")
    all_steps = build_steps(config)
    selected = filter_steps_by_stage(all_steps, config.stage_requested)
    current_svg_sig = svg_output_signature(config.project)
    ctx: dict[str, Any] = {
        "layout_stamp_trusted": layout_stamp_trusted(config.project, config.stage_requested),
        "icon_contract_verified": False,
        "reuse_svg_stage": _svg_stage_reusable(config, current_svg_sig),
    }
    records: list[StepRecord] = []
    aborted = False

    for seq, spec in enumerate(selected, start=1):
        step_t0 = time.perf_counter()
        record = run_step(config, spec, seq, ctx)
        # Real wall-clock per step (utc_now timestamps are only second-precision).
        record.timing["duration_ms"] = round((time.perf_counter() - step_t0) * 1000, 1)
        records.append(record)
        if record.status == "failed" and config.stop_on_error and spec.gate in {"hard", "conditional"}:
            aborted = True
            break

    _append_timing_log(config.project, run_id, records)
    _write_svg_stage_state(config.project, current_svg_sig, records)
    completed_at = utc_now()
    status = "failed" if aborted or any(record.status == "failed" for record in records) else "completed"
    report = build_report(
        config,
        run_id=run_id,
        started_at=started_at,
        completed_at=completed_at,
        status=status,
        steps=records,
    )
    report_path = qa_dir / "strict_run_report.json"
    report["artifacts"]["strict_run_report"] = str(report_path.relative_to(config.project))
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    failed_records = [record for record in records if record.status == "failed"]
    summary = build_agent_summary(report, config, failed_records=failed_records)
    summary_path = qa_dir / "strict_run_summary.json"
    summary_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    report["artifacts"]["strict_run_summary"] = str(summary_path.relative_to(config.project))
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    consistency_errors = verify_agent_summary_consistency(report, summary)
    if consistency_errors:
        report["valid"] = False
        report["status"] = "failed"
        for err in consistency_errors:
            report["blocking_errors"].append({
                "step_id": "agent_summary",
                "stage": "package",
                "code": "summary_inconsistent",
                "message": err,
                "path": SUMMARY_REL_PATH,
                "page_id": None,
                "stdout_json_ref": None,
            })
        summary["valid"] = False
        summary["status"] = "failed"
        summary["blocking_errors"] = report["blocking_errors"]
        summary_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
        report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    report["agent_summary"] = summary

    if status == "completed" and stage_index(config.stage_requested) >= stage_index("mapped"):
        stage_reached = str(report.get("runner", {}).get("stage_reached", config.stage_requested))
        stamp_path = write_layout_artifacts_stamp(config.project, stage_reached)
        report["artifacts"]["layout_artifacts_stamp"] = str(stamp_path.relative_to(config.project))
        report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    return report
