from __future__ import annotations

from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[1]
PATH = ROOT / "cyberppt/visual_medium_policy.py"


def replace_once(content: str, old: str, new: str) -> str:
    count = content.count(old)
    if count != 1:
        raise RuntimeError(f"expected one medium-resolver patch target, found {count}: {old!r}")
    return content.replace(old, new, 1)


def run(*args: str, check: bool = True) -> subprocess.CompletedProcess[str]:
    return subprocess.run(args, cwd=ROOT, check=check, text=True)


content = PATH.read_text(encoding="utf-8")
content = replace_once(
    content,
    '_DATA_RE = re.compile(r"数据|指标|趋势|占比|对比|统计|监测|预测|变化|曲线|分布|排名|data|metric|trend|share|forecast|comparison|distribution", re.I)',
    '_DATA_RE = re.compile(r"指标|趋势|占比|对比|统计|监测|预测|变化|曲线|分布|排名|metric|trend|share|forecast|comparison|distribution|statistics|chart", re.I)',
)
content = replace_once(content, "    evidence_signals = 0\n", "    evidence_signals = 0\n    signal_families: set[str] = set()\n")
content = replace_once(content, "        evidence_signals += 1\n    elif scene_policy == \"forbidden\":\n", "        evidence_signals += 1\n        signal_families.add(\"scene\")\n    elif scene_policy == \"forbidden\":\n")
content = replace_once(content, "        evidence_signals += 1\n    if _OBJECT_RE.search(mission + \" \" + object_text):\n", "        evidence_signals += 1\n        signal_families.add(\"process\")\n    if _OBJECT_RE.search(mission + \" \" + object_text):\n")
content = replace_once(content, "        evidence_signals += 1\n    elif object_text and object_text not in {\"业务关系\", \"business relationship\", \"业务关系场\"}:\n", "        evidence_signals += 1\n        signal_families.add(\"object\")\n    elif object_text and object_text not in {\"业务关系\", \"business relationship\", \"业务关系场\"}:\n")
content = replace_once(content, "        evidence_signals += 1\n    if _RELATION_RE.search(mission + \" \" + relationships) or relationships:\n", "        evidence_signals += 1\n        signal_families.add(\"object\")\n    if _RELATION_RE.search(mission + \" \" + relationships) or relationships:\n")
content = replace_once(content, "        evidence_signals += 1\n    if _DATA_RE.search(mission + \" \" + relationships) or data_available:\n", "        evidence_signals += 1\n        signal_families.add(\"relationship\")\n    if _DATA_RE.search(mission + \" \" + relationships) or data_available:\n")
content = replace_once(content, "        evidence_signals += 1\n    if re.search(r\"企业|机构|部门|人员|客户|供应商|organization|person|customer|supplier\", actor, re.I):\n", "        evidence_signals += 1\n        signal_families.add(\"data\")\n    if re.search(r\"企业|机构|部门|人员|客户|供应商|organization|person|customer|supplier\", actor, re.I):\n")
content = replace_once(content, "        evidence_signals += 1\n\n    # Density is a weak medium signal only.", "        evidence_signals += 1\n        signal_families.add(\"actor\")\n\n    # Density is a weak medium signal only.")
content = replace_once(
    content,
    "        if first[1] >= 0.58 and second[1] >= 0.56 and abs(first[1] - second[1]) <= 0.08:\n",
    "        if (\n            \"data\" in signal_families\n            and len(signal_families - {\"density\", \"scene\"}) >= 2\n            and first[1] >= 0.58\n            and second[1] >= 0.56\n            and abs(first[1] - second[1]) <= 0.08\n        ):\n",
)
PATH.write_text(content, encoding="utf-8", newline="\n")

run("python", "-m", "pytest", "-q", "tests/test_visual_medium_policy.py", "tests/test_visual_medium_resolver_v2.py")
run("git", "config", "user.name", "github-actions[bot]")
run("git", "config", "user.email", "41898282+github-actions[bot]@users.noreply.github.com")
run("git", "add", "cyberppt/visual_medium_policy.py")
if run("git", "diff", "--cached", "--quiet", check=False).returncode != 0:
    run("git", "commit", "-m", "stage2-v3: tighten semantic medium scoring")
    run("git", "push", "origin", "HEAD:feature/stage2-artifact-contract-v3")
