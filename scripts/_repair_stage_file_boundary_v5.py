from pathlib import Path

path = Path(__file__).with_name("_fix_stage_file_boundary_v5.py")
text = path.read_text(encoding="utf-8")
old = "\n'''\n\nhelper.write_text(text + append, encoding=\"utf-8\", newline=\"\\n\")"
new = '\n"""\n\nhelper.write_text(text + append, encoding="utf-8", newline="\\n")'
if old not in text:
    raise RuntimeError("v5 closing delimiter not found")
path.write_text(text.replace(old, new, 1), encoding="utf-8", newline="\n")
print("v5 syntax repaired")
