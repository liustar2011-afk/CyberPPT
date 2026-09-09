from __future__ import annotations

from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[1]


def read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def write(path: str, content: str) -> None:
    (ROOT / path).write_text(content, encoding="utf-8", newline="\n")


def replace_once(path: str, old: str, new: str) -> None:
    content = read(path)
    count = content.count(old)
    if count != 1:
        raise RuntimeError(f"{path}: expected one patch target, found {count}: {old[:120]!r}")
    write(path, content.replace(old, new, 1))


def run(*args: str, check: bool = True) -> subprocess.CompletedProcess[str]:
    return subprocess.run(args, cwd=ROOT, check=check, text=True)


compiler = "cyberppt/visual_stage/compiler.py"
if "from cyberppt.visual_thesis import validate_visual_thesis" not in read(compiler):
    replace_once(
        compiler,
        "from cyberppt.visual_medium_policy import resolve_visual_medium_policy\n",
        "from cyberppt.visual_medium_policy import resolve_visual_medium_policy\n"
        "from cyberppt.visual_thesis import validate_visual_thesis\n",
    )

if "def _selected_visual_thesis(" not in read(compiler):
    marker = "\ndef _build_executable_page(source: dict[str, Any], decision: dict[str, Any]) -> dict[str, Any]:\n"
    helper = '''\ndef _selected_visual_thesis(\n    selected: dict[str, Any],\n    source: dict[str, Any],\n    page_id: str,\n) -> str:\n    try:\n        return validate_visual_thesis(\n            selected.get("visual_thesis"),\n            source.get("core_judgment"),\n        )\n    except ValueError as exc:\n        _fail(f"{page_id}: {exc}")\n    raise AssertionError("unreachable")\n\n'''
    replace_once(compiler, marker, helper + marker)

if "    visual_thesis = _selected_visual_thesis(selected, source, page_id)" not in read(compiler):
    target = '''    if compatible_topologies and topology not in compatible_topologies:\n        _fail(\n            f"{page_id}: selected candidate topology {topology!r} is incompatible with "\n            f"verified semantic topology {verified_topology!r}"\n        )\n    semantic_annotation_contract = _semantic_annotation_contract(\n'''
    replacement = '''    if compatible_topologies and topology not in compatible_topologies:\n        _fail(\n            f"{page_id}: selected candidate topology {topology!r} is incompatible with "\n            f"verified semantic topology {verified_topology!r}"\n        )\n    visual_thesis = _selected_visual_thesis(selected, source, page_id)\n    semantic_annotation_contract = _semantic_annotation_contract(\n'''
    replace_once(compiler, target, replacement)

fallback = '            "visual_thesis": str(selected.get("visual_thesis") or source["core_judgment"]),\n'
if fallback in read(compiler):
    replace_once(compiler, fallback, '            "visual_thesis": visual_thesis,\n')

# Defense in depth at the artifact boundary: hand-edited / legacy visual JSON
# cannot bypass the strong thesis contract.
page = "cyberppt/page_artifact_spec.py"
if "from cyberppt.visual_thesis import validate_visual_thesis" not in read(page):
    replace_once(
        page,
        "from cyberppt.visual_medium_policy import VisualMediumPolicy, validate_visual_medium_policy\n",
        "from cyberppt.visual_medium_policy import VisualMediumPolicy, validate_visual_medium_policy\n"
        "from cyberppt.visual_thesis import validate_visual_thesis\n",
    )
old = '        visual_thesis=_required_text(visual_decision.get("visual_thesis"), "visual thesis"),\n'
if old in read(page):
    replace_once(
        page,
        old,
        '        visual_thesis=validate_visual_thesis(visual_decision.get("visual_thesis"), core_judgment),\n',
    )

# Strengthen the human/agent authoring contract to match executable validation.
skill = "vendor/skills/ppt-visual-structure-designer/SKILL.md"
old_phrase = "每个候选还必须写入候选自身的`visual_thesis`和`selection_rationale`：`visual_thesis`必须说明画面要证明的对象关系，不能复用页面核心结论充当占位；"
new_phrase = (
    "每个候选还必须写入候选自身的`visual_thesis`和`selection_rationale`："
    "`visual_thesis`为必填独立合同，必须说明画面要证明的对象关系、路径、依赖、汇聚、边界、交换或转化结果；"
    "不得为空，不得直接或近似复用`core_judgment`，不得使用纯口号、纯价值判断或仅重复页面结论的句子充当占位。"
    "仓库编译器会对缺失、与核心结论高重复以及缺少关系性信号的`visual_thesis`执行阻断；"
)
if old_phrase in read(skill):
    replace_once(skill, old_phrase, new_phrase)

# Focused integration tests.
test = ROOT / "tests/test_visual_thesis_compiler_contract.py"
test.write_text(
    '''from pathlib import Path\n\nimport pytest\n\nfrom cyberppt.visual_stage.compiler import _selected_visual_thesis\n\n\nROOT = Path(__file__).resolve().parents[1]\n\n\ndef test_compiler_blocks_missing_visual_thesis_without_core_judgment_fallback():\n    with pytest.raises(ValueError, match="P03: VISUAL_THESIS_REQUIRED"):\n        _selected_visual_thesis({}, {"core_judgment": "形成可信协同能力"}, "P03")\n\n\ndef test_compiler_blocks_visual_thesis_equal_to_core_judgment():\n    with pytest.raises(ValueError, match="VISUAL_THESIS_DUPLICATES_CORE_JUDGMENT"):\n        _selected_visual_thesis(\n            {"visual_thesis": "形成可信协同能力"},\n            {"core_judgment": "形成可信协同能力"},\n            "P03",\n        )\n\n\ndef test_compiler_accepts_relational_visual_thesis():\n    thesis = "数据从来源进入受控处理区，并通过接口流向可信服务结果"\n    assert _selected_visual_thesis(\n        {"visual_thesis": thesis},\n        {"core_judgment": "形成可信服务能力"},\n        "P03",\n    ) == thesis\n\n\ndef test_compiler_source_contains_no_visual_thesis_core_judgment_fallback():\n    source = (ROOT / "cyberppt" / "visual_stage" / "compiler.py").read_text(encoding="utf-8")\n    assert 'selected.get("visual_thesis") or source["core_judgment"]' not in source\n    assert '"visual_thesis": visual_thesis' in source\n\n\ndef test_visual_structure_skill_documents_strong_visual_thesis_contract():\n    skill = (ROOT / "vendor" / "skills" / "ppt-visual-structure-designer" / "SKILL.md").read_text(encoding="utf-8")\n    assert "`visual_thesis`为必填独立合同" in skill\n    assert "不得直接或近似复用`core_judgment`" in skill\n    assert "缺少关系性信号" in skill\n''',
    encoding="utf-8", newline="\n",
)

run(
    "python", "-m", "pytest", "-q",
    "tests/test_visual_thesis.py",
    "tests/test_visual_thesis_compiler_contract.py",
    "tests/test_text_capacity_v2.py",
    "tests/test_visual_medium_resolver_v2.py",
)

run("git", "config", "user.name", "github-actions[bot]")
run("git", "config", "user.email", "41898282+github-actions[bot]@users.noreply.github.com")
run("git", "add", compiler, page, skill, "tests/test_visual_thesis_compiler_contract.py")
if run("git", "diff", "--cached", "--quiet", check=False).returncode != 0:
    run("git", "commit", "-m", "stage2-v3: enforce relational visual thesis")
    run("git", "push", "origin", "HEAD:feature/stage2-artifact-contract-v3")
