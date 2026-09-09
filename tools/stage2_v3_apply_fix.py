from __future__ import annotations

from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[1]


def run(*args: str, check: bool = True) -> subprocess.CompletedProcess[str]:
    return subprocess.run(args, cwd=ROOT, check=check, text=True)


first = run("python", "tools/stage2_v3_apply.py", check=False)
if first.returncode != 0:
    renderer = ROOT / "scripts/imagegen_pipeline/final_prompt_renderer.py"
    content = renderer.read_text(encoding="utf-8")
    old = "        lines.append(f\"  - rewrite goal: {rewriteable.rewrite_goal}{length}; preserve {', '.join(rewriteable.preserve)}.\")\n"
    new = (
        "        preserve = \", \\".join(item.replace(\"_\", \" \") for item in rewriteable.preserve)\n"
        "        lines.append(f\"  - rewrite goal: {rewriteable.rewrite_goal}{length}; preserve {preserve}.\")\n"
    )
    if old not in content:
        raise RuntimeError("expected Step 1.2 preserve-rendering target was not generated")
    renderer.write_text(content.replace(old, new, 1), encoding="utf-8", newline="\n")

    run("python", "-m", "pytest", "-q", "tests/test_copy_contract.py", "tests/test_copy_contract_pipeline.py")
    run("git", "config", "user.name", "github-actions[bot]")
    run("git", "config", "user.email", "41898282+github-actions[bot]@users.noreply.github.com")
    run(
        "git", "add",
        "cyberppt/page_artifact_spec.py",
        "scripts/imagegen_pipeline/final_prompt_ir.py",
        "scripts/imagegen_pipeline/artifact_prompt.py",
        "scripts/imagegen_pipeline/final_prompt_renderer.py",
        "scripts/imagegen_pipeline/final_prompt_contract.py",
        "tests/test_copy_contract_pipeline.py",
    )
    diff = run("git", "diff", "--cached", "--quiet", check=False)
    if diff.returncode != 0:
        run("git", "commit", "-m", "stage2-v3: close copy contract authority chain")
        run("git", "push", "origin", "HEAD:feature/stage2-artifact-contract-v3")
