from __future__ import annotations

import json
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT_ENGINE_ROOT = REPO_ROOT / "script-engine"
if str(SCRIPT_ENGINE_ROOT) not in sys.path:
    sys.path.insert(0, str(SCRIPT_ENGINE_ROOT))

from script_engine.contracts import validate_final_script  # noqa: E402
from script_engine.render import render_stage02_markdown  # noqa: E402
from cyberppt.stage02_handoff import build_stage02_handoff  # noqa: E402


def test_script_engine_final_script_is_direct_stage02_input(tmp_path: Path) -> None:
    example = json.loads(
        (SCRIPT_ENGINE_ROOT / "examples" / "final-script.example.json").read_text(
            encoding="utf-8"
        )
    )
    assert validate_final_script(example) == []

    script = tmp_path / "external-final-script.md"
    script.write_text(render_stage02_markdown(example), encoding="utf-8")

    project = tmp_path / "host-project"
    project.mkdir()
    handoff = build_stage02_handoff(project, script=script)

    assert handoff["source_bindings"]["script"]["path"] == str(script.resolve())
    assert handoff["page_order"] == ["p01"]
    page = handoff["pages"][0]
    assert page["render_role"] == "content"
    assert page["title"] == example["slides"][0]["title"]
    assert page["core_message"] == example["slides"][0]["core_message"]
    assert page["onscreen_text"]
    assert page["stage02_visual_input"] is not None


def test_stage02_boundary_does_not_require_script_engine_internals(tmp_path: Path) -> None:
    example = json.loads(
        (SCRIPT_ENGINE_ROOT / "examples" / "final-script.example.json").read_text(
            encoding="utf-8"
        )
    )
    script = tmp_path / "external-final-script.md"
    script.write_text(render_stage02_markdown(example), encoding="utf-8")

    project = tmp_path / "host-project"
    project.mkdir()
    handoff = build_stage02_handoff(project, script=script)

    serialized = json.dumps(handoff, ensure_ascii=False)
    assert "foundation.json" not in serialized
    assert "deck-plan.json" not in serialized
    assert "semantic-argument-model.json" not in serialized
    assert "source-truth.json" not in serialized
