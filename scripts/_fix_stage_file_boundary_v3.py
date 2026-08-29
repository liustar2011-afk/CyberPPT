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
    'assert "parse_script_path" not in (repo/"cyberppt/stage02_input.py").read_text(encoding="utf-8"); assert "script_semantic_digest" not in (repo/"cyberppt/stage02_input.py").read_text(encoding="utf-8")',
)
# Modernize tests whose purpose was specifically to enforce the retired cross-stage handoff.
text += r'''

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
# The later script-mutation test now validates the Stage2 file snapshot binding.
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
