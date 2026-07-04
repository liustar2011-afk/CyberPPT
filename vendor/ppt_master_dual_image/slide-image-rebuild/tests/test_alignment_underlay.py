from __future__ import annotations

import json
import sys
from pathlib import Path
from xml.etree import ElementTree as ET

SCRIPTS_DIR = Path(__file__).resolve().parent.parent / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

import alignment_underlay
from slide_image_rebuild_strict_lib import RunConfig, build_steps, should_reuse_skip_svg_step


def _run_config(project: Path, stage: str) -> RunConfig:
    return RunConfig(
        project=project,
        reference=None,
        rebuild_mode="vector-hifi",
        export_mode="hifi",
        precise_lock=False,
        render=False,
        stage_requested=stage,
        stop_on_error=True,
        dry_run=False,
        skip_export=False,
        preview_render_backend="cairo",
        repo_root=project.parent,
        scripts_dir=SCRIPTS_DIR,
    )


def _write_project(project: Path) -> Path:
    (project / "images" / "reference_pages").mkdir(parents=True)
    (project / "svg_output").mkdir()
    (project / "images" / "reference_pages" / "P01.png").write_bytes(b"png")
    (project / "slide_image_rebuild_manifest.json").write_text(
        json.dumps(
            {
                "workflow": "slide-image-rebuild",
                "pages": [
                    {
                        "page_id": "P01",
                        "reference_image": "images/reference_pages/P01.png",
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    svg_path = project / "svg_output" / "P01.svg"
    svg_path.write_text(
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1200 675">'
        '<rect id="kept" x="10" y="20" width="30" height="40" fill="#123456"/>'
        "</svg>\n",
        encoding="utf-8",
    )
    return svg_path


def _root(svg_path: Path) -> ET.Element:
    return ET.parse(svg_path).getroot()


def _underlay_groups(root: ET.Element) -> list[ET.Element]:
    return [elem for elem in root.iter() if elem.get("data-alignment-underlay") == "temporary"]


def _underlay_href(svg_path: Path) -> str | None:
    root = _root(svg_path)
    groups = _underlay_groups(root)
    if not groups:
        return None
    image = list(groups[0])[0]
    return image.get("href")


def test_inject_adds_temporary_reference_layer_policy_opacity_and_href(tmp_path: Path) -> None:
    svg_path = _write_project(tmp_path)

    payload = alignment_underlay.inject_underlays(tmp_path, opacity=0.31)

    assert payload["valid"]
    root = _root(svg_path)
    first = list(root)[0]
    assert first.get("data-alignment-underlay") == "temporary"
    assert first.get("data-export-policy") == "strip-before-export"
    assert first.get("opacity") == "0.31"
    image = list(first)[0]
    assert image.get("data-alignment-underlay-image") == "reference"
    assert image.get("href") == "../images/reference_pages/P01.png"
    assert image.get("x") == "0"
    assert image.get("y") == "0"
    assert image.get("width") == "1200"
    assert image.get("height") == "675"


def test_inject_uses_reference_pages_fallback_without_usable_manifest_reference(tmp_path: Path) -> None:
    svg_path = _write_project(tmp_path)
    (tmp_path / "slide_image_rebuild_manifest.json").write_text(
        json.dumps(
            {
                "workflow": "slide-image-rebuild",
                "pages": [
                    {
                        "page_id": "P01",
                        "reference_image": "images/missing/P01.png",
                    }
                ],
            }
        ),
        encoding="utf-8",
    )

    payload = alignment_underlay.inject_underlays(tmp_path)

    assert payload["valid"]
    assert payload["injected"] == 1
    assert payload["skipped"] == 0
    assert _underlay_href(svg_path) == "../images/reference_pages/P01.png"


def test_inject_manifest_reference_wins_over_reference_pages_fallback(tmp_path: Path) -> None:
    svg_path = _write_project(tmp_path)
    (tmp_path / "images" / "custom").mkdir()
    (tmp_path / "images" / "custom" / "P01-reference.png").write_bytes(b"png")
    (tmp_path / "slide_image_rebuild_manifest.json").write_text(
        json.dumps(
            {
                "workflow": "slide-image-rebuild",
                "pages": [
                    {
                        "page_id": "P01",
                        "reference_image": "images/custom/P01-reference.png",
                    }
                ],
            }
        ),
        encoding="utf-8",
    )

    payload = alignment_underlay.inject_underlays(tmp_path)

    assert payload["valid"]
    assert payload["injected"] == 1
    assert _underlay_href(svg_path) == "../images/custom/P01-reference.png"


def test_inject_missing_svg_output_is_warning_only(tmp_path: Path) -> None:
    payload = alignment_underlay.inject_underlays(tmp_path)

    assert payload["valid"]
    assert payload["count"] == 0
    assert payload["injected"] == 0
    assert payload["warnings"]


def test_inject_missing_reference_for_existing_svg_is_warning_only(tmp_path: Path) -> None:
    (tmp_path / "svg_output").mkdir()
    svg_path = tmp_path / "svg_output" / "P01.svg"
    svg_path.write_text(
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1200 675">'
        '<rect id="kept" x="10" y="20" width="30" height="40" fill="#123456"/>'
        "</svg>\n",
        encoding="utf-8",
    )

    payload = alignment_underlay.inject_underlays(tmp_path)

    assert payload["valid"]
    assert payload["count"] == 1
    assert payload["injected"] == 0
    assert payload["skipped"] == 1
    assert payload["warnings"]
    assert not _underlay_groups(_root(svg_path))


def test_cli_inject_missing_svg_output_returns_zero_and_valid_json(tmp_path: Path, capsys) -> None:
    code = alignment_underlay.main([str(tmp_path), "inject"])
    captured = capsys.readouterr()
    payload = json.loads(captured.out)

    assert code == 0
    assert payload["valid"]
    assert payload["action"] == "inject"
    assert payload["warnings"]


def test_cli_check_returns_nonzero_when_temporary_underlay_remains(tmp_path: Path, capsys) -> None:
    _write_project(tmp_path)
    alignment_underlay.inject_underlays(tmp_path)

    code = alignment_underlay.main([str(tmp_path), "check"])
    captured = capsys.readouterr()
    payload = json.loads(captured.out)

    assert code != 0
    assert not payload["valid"]
    assert payload["action"] == "check"
    assert payload["remaining"] == 1


def test_check_missing_svg_output_fails_closed(tmp_path: Path) -> None:
    payload = alignment_underlay.check_no_underlays(tmp_path)

    assert not payload["valid"]
    assert payload["count"] == 0
    assert payload["errors"]
    assert payload["warnings"]


def test_cli_check_missing_svg_output_returns_nonzero_and_invalid_json(tmp_path: Path, capsys) -> None:
    code = alignment_underlay.main([str(tmp_path), "check"])
    captured = capsys.readouterr()
    payload = json.loads(captured.out)

    assert code != 0
    assert not payload["valid"]
    assert payload["action"] == "check"
    assert payload["count"] == 0
    assert payload["errors"]


def test_inject_is_idempotent(tmp_path: Path) -> None:
    svg_path = _write_project(tmp_path)

    first = alignment_underlay.inject_underlays(tmp_path)
    second = alignment_underlay.inject_underlays(tmp_path)

    assert first["valid"]
    assert second["valid"]
    groups = _underlay_groups(_root(svg_path))
    assert len(groups) == 1


def test_strip_removes_only_temporary_layer_and_keeps_other_svg_content(tmp_path: Path) -> None:
    svg_path = _write_project(tmp_path)
    alignment_underlay.inject_underlays(tmp_path)

    payload = alignment_underlay.strip_underlays(tmp_path)

    assert payload["valid"]
    root = _root(svg_path)
    assert not _underlay_groups(root)
    assert root.find(".//*[@id='kept']") is not None


def test_check_fails_when_underlay_remains_and_passes_after_strip(tmp_path: Path) -> None:
    _write_project(tmp_path)
    alignment_underlay.inject_underlays(tmp_path)

    dirty = alignment_underlay.check_no_underlays(tmp_path)
    alignment_underlay.strip_underlays(tmp_path)
    clean = alignment_underlay.check_no_underlays(tmp_path)

    assert not dirty["valid"]
    assert dirty["remaining"] == 1
    assert clean["valid"]
    assert clean["remaining"] == 0


def test_strip_and_check_handle_nested_temporary_underlay(tmp_path: Path) -> None:
    svg_path = _write_project(tmp_path)
    svg_path.write_text(
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1200 675">'
        '<g id="outer">'
        '<g id="nested-underlay" data-alignment-underlay="temporary">'
        '<image data-alignment-underlay-image="reference" href="../images/reference_pages/P01.png"/>'
        "</g>"
        '<rect id="kept" x="10" y="20" width="30" height="40" fill="#123456"/>'
        "</g>"
        "</svg>\n",
        encoding="utf-8",
    )

    dirty = alignment_underlay.check_no_underlays(tmp_path)
    stripped = alignment_underlay.strip_underlays(tmp_path)
    clean = alignment_underlay.check_no_underlays(tmp_path)

    root = _root(svg_path)
    assert not dirty["valid"]
    assert dirty["remaining"] == 1
    assert stripped["valid"]
    assert stripped["removed"] == 1
    assert clean["valid"]
    assert not _underlay_groups(root)
    assert root.find(".//*[@id='outer']") is not None
    assert root.find(".//*[@id='kept']") is not None


def test_runner_includes_alignment_underlay_injection_for_svg_stage(tmp_path: Path) -> None:
    cfg = _run_config(tmp_path, "svg")
    steps = build_steps(cfg)
    ids = [step.step_id for step in steps]

    assert "5.0a.strip_alignment_underlay_before_validation" in ids
    assert "5.0b.check_alignment_underlay_stripped" in ids
    assert ids.index("5.0a.strip_alignment_underlay_before_validation") < ids.index("5.0b.check_alignment_underlay_stripped")
    assert ids.index("5.0b.check_alignment_underlay_stripped") < ids.index("5.1.svg_quality_checker")
    assert ids.index("5.0b.check_alignment_underlay_stripped") < ids.index("5.3b.svg_rebuild_completeness")
    assert "5.13.inject_alignment_underlay" in ids
    assert ids.index("5.3b.svg_rebuild_completeness") < ids.index("5.13.inject_alignment_underlay")
    assert ids.index("5.12.aggregate_repair_tasks") < ids.index("5.13.inject_alignment_underlay")
    strip = next(step for step in steps if step.step_id == "5.0a.strip_alignment_underlay_before_validation")
    check = next(step for step in steps if step.step_id == "5.0b.check_alignment_underlay_stripped")
    assert strip.condition is None or strip.condition(cfg, {})
    assert check.condition is None or check.condition(cfg, {})
    inject = next(step for step in steps if step.step_id == "5.13.inject_alignment_underlay")
    assert inject.condition is not None
    assert inject.condition(cfg, {})


def test_runner_includes_alignment_underlay_cleanup_before_export_stage(tmp_path: Path) -> None:
    cfg = _run_config(tmp_path, "pre-export")
    steps = build_steps(cfg)
    ids = [step.step_id for step in steps]

    assert "5.0a.strip_alignment_underlay_before_validation" in ids
    assert "5.0b.check_alignment_underlay_stripped" in ids
    assert ids.index("5.0a.strip_alignment_underlay_before_validation") < ids.index("5.0b.check_alignment_underlay_stripped")
    assert ids.index("5.0b.check_alignment_underlay_stripped") < ids.index("5.1.svg_quality_checker")
    assert ids.index("5.0b.check_alignment_underlay_stripped") < ids.index("5.3b.svg_rebuild_completeness")
    assert ids.index("5.0b.check_alignment_underlay_stripped") < ids.index("6.1.total_md_split")
    inject = next(step for step in steps if step.step_id == "5.13.inject_alignment_underlay")
    assert inject.condition is not None
    assert not inject.condition(cfg, {})


def test_incremental_svg_reuse_does_not_skip_alignment_underlay_steps(tmp_path: Path) -> None:
    steps = {step.step_id: step for step in build_steps(_run_config(tmp_path, "svg"))}
    ctx = {"reuse_svg_stage": True}

    assert not should_reuse_skip_svg_step(steps["5.0a.strip_alignment_underlay_before_validation"], ctx)
    assert not should_reuse_skip_svg_step(steps["5.0b.check_alignment_underlay_stripped"], ctx)
    assert not should_reuse_skip_svg_step(steps["5.13.inject_alignment_underlay"], ctx)
    assert should_reuse_skip_svg_step(steps["5.1.svg_quality_checker"], ctx)
