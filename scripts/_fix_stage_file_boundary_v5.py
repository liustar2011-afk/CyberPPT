from pathlib import Path

root = Path(__file__).resolve().parents[1]
helper = root / "scripts/_apply_stage_file_boundary_v2.py"
text = helper.read_text(encoding="utf-8")

append = r"""

# ImageGen manifest is part of formal Stage2. It consumes the Stage2-owned file
# intake and must not import the legacy cross-stage handoff module.
path="scripts/imagegen_pipeline/page_manifest.py"; source=read(path)
source=source.replace('''    try:
        from cyberppt.stage02_handoff import handoff_page_map, load_stage02_handoff

        handoff = load_stage02_handoff(project_path)
    except (FileNotFoundError, ValueError):
        handoff = None
    handoff_pages = handoff_page_map(handoff) if handoff else {}
''','''    try:
        from cyberppt.stage02_input import input_page_map, load_stage02_input

        script_input = load_stage02_input(project_path)
    except (FileNotFoundError, ValueError):
        script_input = None
    input_pages = input_page_map(script_input) if script_input else {}
''',1)
source=source.replace('handoff_page = handoff_pages.get(page_number) or {}','input_page = input_pages.get(page_number) or {}',1)
source=source.replace('handoff_visual = handoff_page.get("visual_structure") or {}','input_visual = input_page.get("visual_structure") or {}',1)
source=source.replace('page_mission = str(handoff_page.get("page_mission") or missions.get(page.page_id, ""))','page_mission = str(input_page.get("page_mission") or missions.get(page.page_id, ""))',1)
source=source.replace('if isinstance(handoff_visual, dict):\n            if handoff_visual.get("intent_type"):\n                visual_context["visual_intent_type"] = str(handoff_visual["intent_type"])\n            if handoff_visual.get("dominant_carrier"):\n                visual_context["visual_carrier"] = str(handoff_visual["dominant_carrier"])','if isinstance(input_visual, dict):\n            if input_visual.get("intent_type"):\n                visual_context["visual_intent_type"] = str(input_visual["intent_type"])\n            if input_visual.get("dominant_carrier"):\n                visual_context["visual_carrier"] = str(input_visual["dominant_carrier"])',1)
old='''    stage02_handoff: dict[str, Any] | None = None
    stage02_handoff_path: Path | None = None
    handoff_pages: dict[int, dict[str, Any]] = {}
    if project_path is not None:
        from cyberppt.stage02_handoff import HANDOFF_JSON, handoff_page_map, load_stage02_handoff

        stage02_handoff = load_stage02_handoff(project_path)
        if stage02_handoff is not None:
            stage02_handoff_path = project_path / HANDOFF_JSON
            handoff_pages = handoff_page_map(stage02_handoff)
            role_aliases_from_handoff = {
                "cover": "cover",
                "agenda": "agenda",
                "section": "section",
                "content": "content",
                "ending": "ending",
            }
            for number in page_numbers:
                handoff_page = handoff_pages.get(number)
                if handoff_page is None:
                    raise ValueError(f"Stage 02 handoff is missing requested page {number}")
                page_roles[number] = role_aliases_from_handoff[str(handoff_page["render_role"])]
'''
new='''    stage02_input: dict[str, Any] | None = None
    stage02_input_path: Path | None = None
    input_pages: dict[int, dict[str, Any]] = {}
    if project_path is not None:
        from cyberppt.stage02_input import input_page_map, input_path, load_stage02_input

        stage02_input = load_stage02_input(project_path)
        if stage02_input is not None:
            stage02_input_path = input_path(project_path)
            input_pages = input_page_map(stage02_input)
            role_aliases_from_input = {
                "cover": "cover",
                "agenda": "agenda",
                "section": "section",
                "content": "content",
                "ending": "ending",
            }
            for number in page_numbers:
                input_page = input_pages.get(number)
                if input_page is None:
                    raise ValueError(f"Stage 02 script input is missing requested page {number}")
                page_roles[number] = role_aliases_from_input[str(input_page["render_role"])]
'''
if old not in source: raise RuntimeError("page manifest Stage2 source block missing")
source=source.replace(old,new,1)
source=source.replace('compact_blueprint and handoff_pages','compact_blueprint and input_pages')
source=source.replace('handoff_page=handoff_pages[page_number]','handoff_page=input_pages[page_number]')
source=source.replace('handoff_page = handoff_pages.get(page_number) or {}','input_page = input_pages.get(page_number) or {}')
source=source.replace('if not handoff_page:\n                raise ValueError(\n                    f"compact blueprint requires Stage 02 handoff page {page_number}"\n                )','if not input_page:\n                raise ValueError(\n                    f"compact blueprint requires Stage 02 script input page {page_number}"\n                )')
source=source.replace('handoff_page=handoff_page','handoff_page=input_page')
source=source.replace('''                **(
                    {
                        "stage02_handoff": str(stage02_handoff_path.resolve()),
                    }
                    if stage02_handoff_path is not None
                    else {}
                ),''','''                **(
                    {
                        "stage02_script_input": str(stage02_input_path.resolve()),
                    }
                    if stage02_input_path is not None
                    else {}
                ),''')
source=source.replace('''        "stage02_handoff": (
            {
                "path": str(stage02_handoff_path.resolve()),
                "schema": stage02_handoff.get("schema"),
            }
            if stage02_handoff_path is not None and stage02_handoff is not None
            else None
        ),''','''        "stage02_script_input": (
            {
                "path": str(stage02_input_path.resolve()),
                "schema": stage02_input.get("schema"),
            }
            if stage02_input_path is not None and stage02_input is not None
            else None
        ),''')
write(path,source)

# The FinalScriptPages fixture is migrated to the same Stage2-owned input file,
# rather than manufacturing a legacy cross-stage handoff.
path="tests/test_final_script_pages.py"; source=read(path)
source=source.replace('handoff = project / "workbench" / "stages" / "02-handoff" / "stage02-handoff.json"','handoff = project / "workbench" / "stages" / "02-input" / "script-intake.json"',1)
old='''        bound_script = script
        if external_script:
            bound_script = project / SCRIPT_PATH
            bound_script.parent.mkdir(parents=True, exist_ok=True)
            bound_script.write_bytes(script.read_bytes())
'''
new='''        bound_script = project / "workbench" / "inputs" / "final-script.md"
        bound_script.parent.mkdir(parents=True, exist_ok=True)
        bound_script.write_bytes(script.read_bytes())
'''
if old not in source: raise RuntimeError("FinalScriptPages legacy bound script block missing")
source=source.replace(old,new,1)
source=source.replace('"schema": "cyberppt.stage02_handoff.v1",','"schema": "cyberppt.stage02_script_input.v1",',1)
needle='''                            "semantic_sha256": hashlib.sha256(bound_script.read_bytes()).hexdigest(),
                            **(
                                {
                                    "source_mode": "external_script",
                                    "external_path": str(script.resolve()),
                                }
                                if external_script
                                else {}
                            ),
'''
replacement='''                            "semantic_sha256": hashlib.sha256(bound_script.read_bytes()).hexdigest(),
                            "source_path": str(script.resolve()),
                            "source_sha256": hashlib.sha256(script.read_bytes()).hexdigest(),
                            "source_semantic_sha256": hashlib.sha256(script.read_bytes()).hexdigest(),
'''
if needle not in source: raise RuntimeError("FinalScriptPages legacy source binding block missing")
source=source.replace(needle,replacement,1)
source=source.replace('with self.assertRaisesRegex(FileNotFoundError, "Stage 02 handoff"):', 'with self.assertRaisesRegex(FileNotFoundError, "visual structure spec"):',1)
write(path,source)

# Broaden the architectural guard to the whole formal Stage2 production surface.
path="tests/test_stage_file_boundary.py"; source=read(path)
old='''    repo=Path(__file__).resolve().parents[1]; files=[repo/"cyberppt/stage02_input.py",repo/"cyberppt/visual_stage/execution.py",repo/"cyberppt/visual_stage/audit.py",repo/"cyberppt/visual_stage/prompt_gate.py",repo/"cyberppt/stage02_production/preflight.py",repo/"cyberppt/page_artifact_spec.py"]
    text="\\n".join(path.read_text(encoding="utf-8") for path in files)
'''
new='''    repo=Path(__file__).resolve().parents[1]
    files=[repo/"cyberppt/stage02_input.py",repo/"cyberppt/page_artifact_spec.py",repo/"scripts/imagegen_pipeline/page_manifest.py"]
    files.extend(sorted((repo/"cyberppt/visual_stage").glob("*.py")))
    files.extend(sorted((repo/"cyberppt/stage02_production").glob("*.py")))
    text="\\n".join(path.read_text(encoding="utf-8") for path in files)
'''
if old not in source: raise RuntimeError("architecture file list block missing")
source=source.replace(old,new,1)
write(path,source)
'''

helper.write_text(text + append, encoding="utf-8", newline="\n")
print("v5 refinements applied")
