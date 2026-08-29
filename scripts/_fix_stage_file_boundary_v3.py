from pathlib import Path

root = Path(__file__).resolve().parents[1]
helper = root / "scripts/_apply_stage_file_boundary_v2.py"
text = helper.read_text(encoding="utf-8")
text = text.replace('from cyberppt.semantic_digest import script_semantic_digest\n', '')
text = text.replace('"semantic_sha256":script_semantic_digest(snapshot)', '"semantic_sha256":_sha256(snapshot)')
text = text.replace('binding["source_semantic_sha256"]=script_semantic_digest(source)', 'binding["source_semantic_sha256"]=_sha256(source)')
text = text.replace(
    'if legacy_script.is_file() and (source == legacy_script or source == target): return legacy_script',
    'if legacy_script.is_file() and (source == legacy_script or source == target):\n                if binding.get("sha256") and binding.get("sha256") != _sha256(legacy_script): raise ValueError("Stage 02 script input changed; rebuild Stage 02 visual artifacts from the updated file")\n                return legacy_script',
)
text = text.replace(
    'assert "parse_script_path" not in (repo/"cyberppt/stage02_input.py").read_text(encoding="utf-8")',
    'assert "parse_script_path" not in (repo/"cyberppt/stage02_input.py").read_text(encoding="utf-8"); assert "script_semantic_digest" not in text',
)
# Modernize tests whose purpose was specifically to enforce the retired cross-stage handoff.
text += r'''

# Formal Stage2 freshness is byte-bound to its input snapshot. It must not call
# the Stage1 semantic-digest helper, which can read sidecars and apply Stage1 contracts.
path="cyberppt/visual_stage/execution.py"; source=read(path)
source=source.replace('from cyberppt.semantic_digest import script_semantic_digest\n','')
source=source.replace('            "approved_script_semantic_sha256": script_semantic_digest(script),\n','')
source=source.replace('            f"- approved_script_semantic_sha256: {script_semantic_digest(script)}",\n','')
source=source.replace('            "approved_script_semantic_sha256": script_semantic_digest(script),','            "approved_script_sha256": _sha256(script),')
source=source.replace('        "approved_script_semantic_sha256": script_semantic_digest(script),','        "approved_script_sha256": _sha256(script),')
source=source.replace('        "approved_script_semantic_sha256": str(script),','        "approved_script_sha256": str(script),')
write(path,source)

path="cyberppt/visual_stage/audit.py"; source=read(path)
source=source.replace('from cyberppt.semantic_digest import script_semantic_digest\n','')
source=source.replace('        "script_semantic_sha256": script_semantic_digest(script),','        "script_input_sha256": _sha256(script),\n        "script_semantic_sha256": _sha256(script),  # deprecated compatibility alias')
write(path,source)

path="cyberppt/visual_stage/prompt_gate.py"; source=read(path)
source=source.replace('from cyberppt.semantic_digest import script_semantic_digest\n','')
old='''    try:
        script_digest = script_semantic_digest(script)
    except ValueError:
        script_digest = _sha256(script)
'''
new='''    script_digest = _sha256(script)
'''
if old not in source: raise RuntimeError("prompt gate semantic digest block missing")
source=source.replace(old,new,1)
write(path,source)

# Test migration: formal Stage2 no longer treats legacy handoff as a prerequisite.
path="tests/test_cli.py"; source=read(path)
source=source.replace('self.assertIn("Stage 02 handoff is missing requested page 3", buffer.getvalue())','self.assertNotIn("Stage 02 handoff", buffer.getvalue())')
write(path,source)

path="tests/test_page_artifact_spec.py"; source=read(path)
source=source.replace('with patch("cyberppt.stage02_handoff.load_stage02_handoff", return_value=payload):','with patch("cyberppt.stage02_input.load_stage02_input", return_value=payload):')
write(path,source)

path="tests/test_visual_structure_stage.py"; source=read(path)
old='''            with self.assertRaisesRegex(ValueError, "HANDOFF_BINDING_STALE"):
                prepare_visual_structure_stage(project, script, reuse_current_handoff=True)

            self.assertFalse((project / VISUAL_FILES["design_input"]).exists())'''
new='''            invocation = prepare_visual_structure_stage(project, script, reuse_current_handoff=True)
            self.assertTrue(invocation.is_file())
            self.assertTrue((project / VISUAL_FILES["design_input"]).exists())
            self.assertTrue((project / "workbench/stages/02-input/script-intake.json").is_file())'''
if old not in source: raise RuntimeError("stale handoff compatibility test block not found")
source=source.replace(old,new,1)
marker='''            with self.assertRaisesRegex(ValueError, "HANDOFF_BINDING_STALE"):
                assert_visual_structure_ready(project, script)'''
replacement='''            with self.assertRaisesRegex(ValueError, "Stage 02 script input changed"):
                assert_visual_structure_ready(project, script)'''
if marker not in source: raise RuntimeError("visual gate stale-script assertion not found")
source=source.replace(marker,replacement,1)
write(path,source)
'''
helper.write_text(text, encoding="utf-8", newline="\n")
print("v3 refinements applied")
