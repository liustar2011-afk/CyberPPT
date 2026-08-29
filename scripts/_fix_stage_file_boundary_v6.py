from pathlib import Path

helper = Path(__file__).with_name("_apply_stage_file_boundary_v2.py")
text = helper.read_text(encoding="utf-8")
append = r'''

# All --script inputs are one Stage2 file-input category. The compatibility
# --external-script flag no longer creates a separate execution path.
path="tests/test_final_script_pages.py"; source=read(path)
source=source.replace('from cyberppt.stage02_handoff import SCRIPT_PATH\n','from cyberppt.stage02_input import INPUT_SCRIPT_PATH\n')
source=source.replace('self.assertEqual("external_script", summary["source_mode"])','self.assertEqual("script_file", summary["source_mode"])',1)
source=source.replace('self.assertEqual("external_script", context["source_mode"])','self.assertEqual("script_file", context["source_mode"])',1)
source=source.replace('str((project / SCRIPT_PATH).resolve()),','str((project / INPUT_SCRIPT_PATH).resolve()),',1)
source=source.replace('self.assertEqual("external_script", manifest["source_mode"])','self.assertEqual("script_file", manifest["source_mode"])',1)
write(path,source)
'''
helper.write_text(text + append, encoding="utf-8", newline="\n")
print("v6 refinements applied")
