"""Run every fixture under fixtures/image_rebuild/ against its declared validator(s).

Each fixture directory has a fixture_config.json describing:
  - which boolean flags select a validator script to run (see FLAG_RUNNERS below)
  - "reuse_project": copy another fixture's project files in as a base
  - "expect_invalid": {check_name: true} -- check_name's "valid" must be False
    (default: every selected check must come back valid: true)
  - "expected_error_codes" / "expected_warning_codes" / "<check>_expected_error_codes":
    error/warning codes that must appear in the corresponding check's output
  - various "expected_*" scalar assertions matched against specific output fields

A handful of negative fixtures only ship a fixture_config.json (no project files)
because they reuse another fixture's project and apply a synthetic corruption.
Those corruptions are reconstructed in SYNTHETIC_MUTATIONS below -- they are a
best-effort inference (the original mutation code was not part of this skill's
standalone export), not a verbatim port. If one starts failing, re-check the
mutation against the fixture's "purpose" string before assuming the validator
regressed.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path
from typing import Any, Callable

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
FIXTURES_DIR = REPO_ROOT / "fixtures" / "image_rebuild"
SCRIPTS_DIR = REPO_ROOT / "scripts"
PYTHON = sys.executable


def discover_fixtures() -> list[str]:
    return sorted(
        p.parent.name
        for p in FIXTURES_DIR.glob("*/fixture_config.json")
    )


def materialize(name: str, dest: Path) -> dict[str, Any]:
    """Copy a fixture's project files (plus its reuse_project base, if any) into dest."""
    fixture_dir = FIXTURES_DIR / name
    config = json.loads((fixture_dir / "fixture_config.json").read_text(encoding="utf-8"))

    reuse = config.get("reuse_project")
    if reuse:
        _copy_project_files(FIXTURES_DIR / reuse, dest)
    _copy_project_files(fixture_dir, dest)

    for mutate in SYNTHETIC_MUTATIONS.get(name, []):
        mutate(dest, config)

    _refresh_preview_mtimes(dest)
    return config


def _refresh_preview_mtimes(dest: Path) -> None:
    """Committed fixtures pair an SVG with an already-rendered preview PNG, but
    git does not preserve mtimes on checkout/copy -- so a freshly materialized
    copy can randomly look "stale" to render_preview_backend's mtime-based
    freshness check. Bump preview mtimes ahead of their SVGs to restore the
    relationship the fixture actually encodes (preview generated after SVG).
    """
    now = time.time()
    for preview in dest.rglob("*.preview.png"):
        os.utime(preview, (now, now))


def _copy_project_files(src: Path, dest: Path) -> None:
    dest.mkdir(parents=True, exist_ok=True)
    for item in src.iterdir():
        if item.name in {"fixture_config.json"} or item.name.startswith("_"):
            continue
        target = dest / item.name
        if item.is_dir():
            shutil.copytree(item, target, dirs_exist_ok=True)
        else:
            shutil.copy2(item, target)


# --- Synthetic mutations for reuse_project-only negative fixtures ----------

def _mutate_remove_zone_id(dest: Path, config: dict[str, Any]) -> None:
    svg_path = dest / "svg_output" / "01.svg"
    text = svg_path.read_text(encoding="utf-8")
    text = text.replace(' data-zone-id="zone_intake"', "", 1)
    svg_path.write_text(text, encoding="utf-8")


def _mutate_duplicate_text_line(dest: Path, config: dict[str, Any]) -> None:
    svg_path = dest / "svg_output" / "01.svg"
    text = svg_path.read_text(encoding="utf-8")
    extra_line = (
        '\n  <text data-text-region-id="card_body" x="130" y="300" '
        'font-family="Microsoft YaHei" font-size="28" fill="#073A7C">Extra</text>'
    )
    text = text.replace("</svg>", f"{extra_line}\n</svg>")
    svg_path.write_text(text, encoding="utf-8")


def _mutate_bad_preview(dest: Path, config: dict[str, Any]) -> None:
    from PIL import Image

    for preview in dest.glob("pages/*/exports/preview_qa/*.preview.png"):
        with Image.open(preview) as img:
            size = img.size
        Image.new("RGB", size, color=(0, 0, 0)).save(preview)


def _mutate_override_layout_family(dest: Path, config: dict[str, Any]) -> None:
    override = config["layout_family_contract_override_family"]
    layout_path = dest / "layout_reference.json"
    data = json.loads(layout_path.read_text(encoding="utf-8"))
    data["layout_type"] = override
    layout_path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


SYNTHETIC_MUTATIONS: dict[str, list[Callable[[Path, dict[str, Any]], None]]] = {
    "svg_rebuild_completeness_negative": [_mutate_remove_zone_id],
    "text_wrap_similarity_negative": [_mutate_duplicate_text_line],
    "object_similarity_negative": [_mutate_bad_preview],
    "layout_family_contract_negative": [_mutate_override_layout_family],
}


# --- Running a script and parsing its JSON stdout ---------------------------

class CheckResult:
    def __init__(self, returncode: int, payload: dict[str, Any] | None, raw: str):
        self.returncode = returncode
        self.payload = payload or {}
        self.raw = raw

    @property
    def valid(self) -> bool:
        return bool(self.payload.get("valid"))

    def codes(self, key: str) -> set[str]:
        out = set()
        for item in self.payload.get(key, []) or []:
            if isinstance(item, dict) and "code" in item:
                out.add(item["code"])
            elif isinstance(item, str):
                out.add(item)
        return out


def run_script(script: str, args: list[str]) -> CheckResult:
    proc = subprocess.run(
        [PYTHON, str(SCRIPTS_DIR / script), *args],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    raw = proc.stdout.strip()
    try:
        payload = json.loads(raw) if raw else None
    except json.JSONDecodeError:
        payload = None
    return CheckResult(proc.returncode, payload, raw or proc.stderr)


# --- Flag -> validator dispatch ---------------------------------------------
# Each runner takes (project, config) and returns {check_name: CheckResult}.

def _run_layout_reference(project: Path, config: dict[str, Any]) -> dict[str, CheckResult]:
    args = [str(project / "layout_reference.json")]
    if config.get("rebuild2"):
        args.append("--rebuild2")
    return {"layout_reference": run_script("validate_layout_reference.py", args)}


def _run_geometry_locks(project: Path, config: dict[str, Any]) -> dict[str, CheckResult]:
    return {"geometry_locks": run_script("verify_geometry_locks.py", [str(project)])}


def _run_text_bearing_images(project: Path, config: dict[str, Any]) -> dict[str, CheckResult]:
    return {"text_bearing_images": run_script("verify_text_bearing_images.py", [str(project)])}


def _run_icon_contract(project: Path, config: dict[str, Any]) -> dict[str, CheckResult]:
    args = [str(project)]
    if config.get("icon_contract_style_check"):
        args.append("--style-check")
    return {"icon_contract": run_script("verify_icon_contract.py", args)}


def _run_layout_family_contract(project: Path, config: dict[str, Any]) -> dict[str, CheckResult]:
    return {"layout_family_contract": run_script("verify_layout_family_contract.py", [str(project)])}


def _run_build_icon_manifest(project: Path, config: dict[str, Any]) -> dict[str, CheckResult]:
    return {"build_icon_manifest": run_script("build_icon_manifest_from_layout.py", [str(project), "--dry-run"])}


def _run_crop_intake_summary(project: Path, config: dict[str, Any]) -> dict[str, CheckResult]:
    return {"crop_intake_summary": run_script("crop_intake_summary.py", [str(project)])}


def _run_precrop_layout_candidates(project: Path, config: dict[str, Any]) -> dict[str, CheckResult]:
    return {"precrop_layout_candidates": run_script("precrop_layout_candidates.py", [str(project)])}


def _run_svg_rebuild_completeness(project: Path, config: dict[str, Any]) -> dict[str, CheckResult]:
    args = [str(project)]
    if config.get("svg_rebuild_completeness_strict"):
        args.append("--strict")
    return {"svg_rebuild_completeness": run_script("verify_svg_rebuild_completeness.py", args)}


def _run_text_wrap_similarity(project: Path, config: dict[str, Any]) -> dict[str, CheckResult]:
    return {"text_wrap_similarity": run_script("verify_text_wrap_similarity.py", [str(project)])}


def _run_object_similarity(project: Path, config: dict[str, Any]) -> dict[str, CheckResult]:
    # Deliberately ignores config["render"]: that flag governs the reference_similarity
    # check's own render step. object_similarity should compare against whatever
    # preview PNG is already committed in the fixture (or the synthetic bad one).
    return {"object_similarity": run_script("verify_reference_object_similarity.py", [str(project)])}


def _run_reference_similarity(project: Path, config: dict[str, Any]) -> dict[str, CheckResult]:
    args = [str(project)]
    if config.get("render"):
        args.append("--render")
    backend = config.get("reference_similarity_render_backend")
    if backend:
        args += ["--render-backend", backend]
    return {"reference_similarity": run_script("verify_reference_similarity.py", args)}


def _run_repair_tasks(project: Path, config: dict[str, Any]) -> dict[str, CheckResult]:
    return {"repair_tasks": run_script("aggregate_repair_tasks.py", [str(project), "--enforce"])}


def _run_manifest_stage(project: Path, config: dict[str, Any]) -> dict[str, CheckResult]:
    stage = config["manifest_stage"]
    return {
        "slide_image_rebuild_manifest": run_script(
            "verify_slide_image_rebuild_manifest.py", [str(project), "--stage", stage]
        )
    }


def _run_strict_runner(project: Path, config: dict[str, Any]) -> dict[str, CheckResult]:
    stage = config.get("strict_runner_stage", "intake")
    args = ["--project", str(project), "--stage", stage]
    if config.get("strict_runner_precise_lock"):
        args.append("--precise-lock")
    return {"strict_runner": run_script("run_slide_image_rebuild_strict.py", args)}


def _run_render_backend_smoke(project: Path, config: dict[str, Any]) -> dict[str, CheckResult]:
    return {"render_backend_smoke": run_script("check_cairo_backend.py", ["--render", str(project)])}


# Order matters only for readability; each flag is independent.
FLAG_RUNNERS: dict[str, Callable[[Path, dict[str, Any]], dict[str, CheckResult]]] = {
    "layout_reference": _run_layout_reference,
    "geometry_locks": _run_geometry_locks,
    "icon_contract": _run_icon_contract,
    "layout_family_contract": _run_layout_family_contract,
    "build_icon_manifest": _run_build_icon_manifest,
    "crop_intake_summary": _run_crop_intake_summary,
    "precrop_layout_candidates": _run_precrop_layout_candidates,
    "svg_rebuild_completeness": _run_svg_rebuild_completeness,
    "text_wrap_similarity": _run_text_wrap_similarity,
    "object_similarity": _run_object_similarity,
    "reference_similarity": _run_reference_similarity,
    "repair_tasks": _run_repair_tasks,
    "render_backend_smoke": _run_render_backend_smoke,
}

# Flags that gate a runner but aren't booleans (handled separately).
SPECIAL_FLAGS = {"manifest_stage": _run_manifest_stage, "strict_runner": _run_strict_runner}

# Fixtures with no boolean flag at all that still need verify_text_bearing_images
# (triggered by the presence of image_crops_manifest.json -- see module docstring).
IMPLICIT_TEXT_BEARING_IMAGES_CHECK = {"crop_footer_allowed", "crop_role_warning", "crop_policy_guard"}

# Flags/keys present in fixture_config.json that aren't run directives -- skip them
# when iterating for boolean flags.
NON_RUNNER_KEYS = {
    "purpose", "reuse_project", "rebuild2", "render", "expect_invalid",
    "expected_error_codes", "expected_warning_codes", "expected_layout_reference_warnings",
    "icon_contract_style_check", "icon_contract_expected_error_codes",
    "svg_rebuild_completeness_strict", "svg_completeness_bad_zone", "text_wrap_bad_svg",
    "object_similarity_bad_preview", "layout_family_contract_override_family",
    "expected_layout_family", "expected_icon_manifest_icons", "expected_crop_candidates_total",
    "expected_precrop_items", "cleanup_precrop_outputs", "cleanup_render_outputs",
    "manifest_stage", "strict_runner_stage", "strict_runner_precise_lock",
    "expected_intake_rebuild_mode", "render_backend_smoke_backend", "render_backend_smoke_page",
    "expected_render_backend", "expected_smoke_non_blank", "expected_smoke_no_cjk_tofu",
    "expected_mean_diff_max", "reference_similarity_render_backend", "reference_similarity_expected_error_codes",
    "reference_preview_rms", "reference_preview_rms_page", "expected_rms_verdict", "expected_rms_max",
    "layout_reference_to_layout_plan", "expected_layout_plan_elements_min", "cleanup_render_outputs",
}


def run_all_checks(project: Path, config: dict[str, Any]) -> dict[str, CheckResult]:
    results: dict[str, CheckResult] = {}
    for flag, runner in FLAG_RUNNERS.items():
        if config.get(flag):
            results.update(runner(project, config))
    for flag, runner in SPECIAL_FLAGS.items():
        if config.get(flag):
            results.update(runner(project, config))
    return results


# --- Assertions ---------------------------------------------------------

def assert_fixture(name: str, config: dict[str, Any], results: dict[str, CheckResult]) -> None:
    expect_invalid = config.get("expect_invalid", {})
    for check_name, result in results.items():
        expected_valid = not expect_invalid.get(check_name, False)
        assert result.valid == expected_valid, (
            f"[{name}] {check_name}: expected valid={expected_valid}, "
            f"got {result.valid}\n{result.raw[:2000]}"
        )

    for codes_key, target_check in (
        ("expected_error_codes", None),
        ("expected_warning_codes", None),
        ("icon_contract_expected_error_codes", "icon_contract"),
        ("reference_similarity_expected_error_codes", "reference_similarity"),
    ):
        expected = config.get(codes_key)
        if not expected:
            continue
        field = "warnings" if "warning" in codes_key else "errors"
        if target_check:
            result = results.get(target_check)
            assert result is not None, f"[{name}] missing check {target_check} for {codes_key}"
            actual = result.codes(field)
        else:
            actual = set()
            for result in results.values():
                actual |= result.codes(field)
        missing = set(expected) - actual
        assert not missing, f"[{name}] {codes_key}: missing {missing} in {actual}"


# --- The test ------------------------------------------------------------

@pytest.mark.parametrize("name", discover_fixtures())
def test_fixture(name: str, tmp_path: Path) -> None:
    project = tmp_path / name
    config = materialize(name, project)
    results = run_all_checks(project, config)

    if not results and name not in IMPLICIT_TEXT_BEARING_IMAGES_CHECK:
        pytest.skip(f"[{name}] no recognized run directive in fixture_config.json")

    if name in IMPLICIT_TEXT_BEARING_IMAGES_CHECK:
        results.update(_run_text_bearing_images(project, config))

    assert_fixture(name, config, results)

    # Spot-check a few scalar expectations beyond valid/codes.
    if "expected_layout_family" in config:
        assert results["layout_family_contract"].payload["pages"][0]["family"] == config["expected_layout_family"]
    if "expected_icon_manifest_icons" in config:
        icons = results["build_icon_manifest"].payload["pages"][0]["icons"]
        assert len(icons) == config["expected_icon_manifest_icons"]
    if "expected_crop_candidates_total" in config:
        total = results["crop_intake_summary"].payload["crop_candidates_summary"]["total"]
        assert total == config["expected_crop_candidates_total"]
    if "expected_precrop_items" in config:
        items = results["precrop_layout_candidates"].payload["items"]
        assert len(items) == config["expected_precrop_items"]
    if "expected_intake_rebuild_mode" in config:
        assert results["slide_image_rebuild_manifest"].payload["rebuild_mode"] == config["expected_intake_rebuild_mode"]
