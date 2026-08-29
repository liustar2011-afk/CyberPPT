from __future__ import annotations

import re
from pathlib import Path


def read(path: str) -> str:
    return Path(path).read_text(encoding="utf-8")


def write(path: str, text: str) -> None:
    Path(path).write_text(text, encoding="utf-8", newline="\n")


def replace_once(text: str, old: str, new: str, label: str) -> str:
    count = text.count(old)
    if count != 1:
        raise RuntimeError(f"{label}: expected one match, got {count}")
    return text.replace(old, new, 1)


# 1. Production context names the Stage2-owned intake artifact directly.
path = "cyberppt/stage02_production/models.py"
text = read(path)
text = replace_once(
    text,
    "    handoff_sha256: str\n",
    "    script_input_sha256: str\n",
    "Stage02BuildContext field",
)
write(path, text)

path = "cyberppt/stage02_production/preflight.py"
text = read(path)
text = replace_once(
    text,
    'handoff_sha256=sha256_file(script_input_path) or ""',
    'script_input_sha256=sha256_file(script_input_path) or ""',
    "preflight input hash field",
)
write(path, text)

# 2. Execution receipt binds the Stage2-owned snapshot by raw file SHA.
path = "cyberppt/visual_stage/execution.py"
text = read(path)
needle = '            "approved_script": str(script),\n            "visual_design_input": str(design_input),'
replacement = (
    '            "approved_script": str(script),\n'
    '            "approved_script_sha256": _sha256(script),\n'
    '            "visual_design_input": str(design_input),'
)
text = replace_once(text, needle, replacement, "execution receipt script hash")
write(path, text)

# 3. Compact-blueprint regression consumes canonical Stage2 script input.
path = "tests/test_imagegen_page_manifest.py"
text = read(path)
text = replace_once(
    text,
    "def test_compact_blueprint_uses_handoff_locked_text_without_full_prose(self) -> None:",
    "def test_compact_blueprint_uses_script_input_locked_text_without_full_prose(self) -> None:",
    "compact blueprint test name",
)
pattern = re.compile(
    r'''            handoff = \{\n.*?            with patch\(\n                "cyberppt\.stage02_handoff\.load_stage02_handoff",\n                return_value=handoff,\n            \):''',
    re.S,
)
replacement = '''            script_input = {
                "schema": "cyberppt.stage02_script_input.v1",
                "pages": [
                    {
                        "page_id": "p04",
                        "page_number": 4,
                        "render_role": "content",
                        "core_message": "跨主体需求与现实制约共同要求可信服务基座。",
                        "full_prose": "这段完整讲稿不得进入最终送图脚本。",
                        "onscreen_text": "业务演进与协同需求\\n现实制约\\n可信服务基座",
                    }
                ],
            }
            input_path = project / "workbench/stages/02-input/script-intake.json"
            input_path.parent.mkdir(parents=True, exist_ok=True)
            input_path.write_text(json.dumps(script_input, ensure_ascii=False), encoding="utf-8")
            with patch(
                "cyberppt.stage02_input.load_stage02_input",
                return_value=script_input,
            ):'''
text, count = pattern.subn(replacement, text, count=1)
if count != 1:
    raise RuntimeError(f"compact blueprint fixture: expected one match, got {count}")
text = replace_once(
    text,
    'self.assertIn("2048×1024（2:1）", prompt)',
    'self.assertIn("2048×1024 像素（2:1）", prompt)',
    "compact blueprint canvas assertion",
)
write(path, text)

# 4. Artifact-spec loader fixture creates the canonical Stage2 input file it hashes.
path = "tests/test_page_artifact_spec.py"
text = read(path)
old = '''            handoff_path = project / "workbench/stages/02-handoff/stage02-handoff.json"
            handoff_path.parent.mkdir(parents=True)
            handoff_path.write_text("{}\\n", encoding="utf-8")'''
new = '''            input_path = project / "workbench/stages/02-input/script-intake.json"
            input_path.parent.mkdir(parents=True)
            input_path.write_text("{}\\n", encoding="utf-8")'''
text = replace_once(text, old, new, "artifact-spec canonical input fixture")
write(path, text)

# 5. Visual gate regression prepares Stage2 input directly; no Stage1 outline/handoff fixture.
path = "tests/test_visual_structure_stage.py"
text = read(path)
pattern = re.compile(
    r'''            stage01 = project / "workbench" / "stages" / "01-analysis"\n.*?            visual = project / "visual"\n''',
    re.S,
)
replacement = '''            from cyberppt.stage02_input import INPUT_JSON, prepare_stage02_input

            input_report = prepare_stage02_input(project, script=script)
            self.assertEqual("passed", input_report["status"])
            script_input = project / INPUT_JSON
            visual = project / "visual"
'''
text, count = pattern.subn(replacement, text, count=1)
if count != 1:
    raise RuntimeError(f"visual gate fixture: expected one match, got {count}")
text = replace_once(
    text,
    'json.dumps({"source_sha256": _sha256(handoff)})',
    'json.dumps({"source_sha256": _sha256(script_input)})',
    "visual design input source hash",
)
write(path, text)

# 6. Architecture guard prevents the old cross-stage hash field from returning.
path = "tests/test_stage_file_boundary.py"
text = read(path)
marker = '    for token in ("deck-plan.json","foundation.json","source-truth.json","outline.json"): assert token not in text\n'
text = replace_once(
    text,
    marker,
    marker + '    assert "handoff_sha256" not in text\n',
    "architecture handoff hash guard",
)
write(path, text)

print("Stage2 file-boundary final fixes applied")
