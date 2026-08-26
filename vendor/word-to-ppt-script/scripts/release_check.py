#!/usr/bin/env python3
from __future__ import annotations

import compileall
import json
import subprocess
import sys
import tempfile
from pathlib import Path

try:
    import yaml
except ImportError:
    yaml = None


def run(cmd, cwd):
    result = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True)
    return result.returncode == 0, (result.stdout + result.stderr).strip()


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    checks = []
    checks.append(("python_compileall", compileall.compile_dir(str(root / "scripts"), quiet=1)))
    ok, out = run([sys.executable, "-m", "unittest", "discover", "-s", "tests", "-v"], root)
    checks.append(("unit_tests", ok))
    ok_script, _ = run([sys.executable, "scripts/validate_script.py", "examples/sample-project/10-script-final.md", "--strict"], root)
    checks.append(("example_script_validation", ok_script))
    ok_project, _ = run([sys.executable, "scripts/validate_project.py", "examples/sample-project", "--strict"], root)
    checks.append(("example_project_validation", ok_project))
    yaml_ok = True
    if yaml is not None:
        for path in (root / "config").glob("*.yaml"):
            try:
                yaml.safe_load(path.read_text(encoding="utf-8"))
            except Exception:
                yaml_ok = False
    checks.append(("yaml_loading", yaml_ok))
    handoff = root / "examples" / "sample-project" / "12-imagegen-review.md"
    ok_handoff, _ = run([sys.executable, "scripts/build_generation_prompt.py", "examples/sample-project/10-script-final.md", "-o", str(handoff)], root)
    handoff_text = handoff.read_text(encoding="utf-8") if handoff.exists() else ""
    visual_isolated = ok_handoff and "演讲者备注" not in handoff_text and "SRC-P" not in handoff_text and "visual_intent_type" not in handoff_text.split("## 第2页：", 1)[-1]
    checks.append(("imagegen_handoff_isolation", visual_isolated))
    ok_contract, _ = run([sys.executable, "scripts/validate_imagegen_contract.py", str(handoff), "--strict"], root)
    checks.append(("imagegen_contract_validation", ok_contract))
    golden = root / "examples" / "golden" / "06953cb7-5f43-4d00-8b23-72af9dd467bc.md"
    ok_golden, _ = run([sys.executable, "scripts/validate_imagegen_contract.py", str(golden)], root)
    checks.append(("golden_contract_validation", ok_golden))
    if handoff.exists():
        handoff.unlink()
    with tempfile.TemporaryDirectory() as td:
        # Run the installer against a temporary HOME.
        env_result = subprocess.run(["bash", "scripts/install.sh", "user"], cwd=root, env={**__import__('os').environ, "HOME": td}, capture_output=True, text=True)
        installed = Path(td) / ".agents" / "skills" / "word-to-ppt-script" / "SKILL.md"
        checks.append(("temporary_install", env_result.returncode == 0 and installed.exists()))
    passed = all(v for _, v in checks)
    payload = {"passed": passed, "checks": [{"check": k, "passed": v} for k, v in checks]}
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0 if passed else 2


if __name__ == "__main__":
    raise SystemExit(main())
