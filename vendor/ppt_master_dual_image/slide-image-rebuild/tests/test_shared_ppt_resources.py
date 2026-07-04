from __future__ import annotations

import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parent.parent
SCRIPTS_DIR = REPO_ROOT / "scripts"
PPT_MASTER_ROOT = REPO_ROOT.parent

if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from shared_ppt_resources import icons_dir, resource_report, svg_quality_checker_script  # noqa: E402
from slide_image_rebuild_strict_lib import RunConfig, _script_argv  # noqa: E402


def test_shared_icons_dir_prefers_host_ppt_master() -> None:
    resolved = icons_dir()
    assert resolved == PPT_MASTER_ROOT / "skills" / "ppt-master" / "templates" / "icons"
    assert (resolved / "tabler-outline").is_dir()


def test_resource_report_exposes_shared_templates_and_tools() -> None:
    report = resource_report()
    assert report["ppt_master_repo_root"] == str(PPT_MASTER_ROOT)
    resources = report["resources"]
    assert resources["charts_dir"]["source"] == "shared"
    assert resources["svg_quality_checker"]["source"] == "shared"
    assert resources["svg_editor_server"]["source"] == "shared"


def test_strict_runner_uses_shared_svg_quality_checker() -> None:
    config = RunConfig(
        project=REPO_ROOT,
        reference=None,
        rebuild_mode="vector-hifi",
        export_mode="hifi",
        precise_lock=False,
        render=False,
        stage_requested="svg",
        stop_on_error=True,
        dry_run=True,
        skip_export=True,
        preview_render_backend="cairo",
        repo_root=REPO_ROOT,
        scripts_dir=SCRIPTS_DIR,
        python=sys.executable,
    )
    argv = _script_argv(config, "svg_quality_checker.py", str(REPO_ROOT))
    assert Path(argv[1]) == svg_quality_checker_script()
    assert Path(argv[1]) == PPT_MASTER_ROOT / "skills" / "ppt-master" / "scripts" / "svg_quality_checker.py"
