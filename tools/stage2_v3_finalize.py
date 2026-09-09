from __future__ import annotations

from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[1]
LEDGER = ROOT / "docs/development/stage2-artifact-contract-v3-progress.md"


def run(*args: str, check: bool = True) -> subprocess.CompletedProcess[str]:
    return subprocess.run(args, cwd=ROOT, check=check, text=True, capture_output=False)


AGGREGATE_TESTS = (
    "tests/test_copy_contract.py",
    "tests/test_copy_contract_pipeline.py",
    "tests/test_composition_strategy.py",
    "tests/test_region_graph_composition_strategy.py",
    "tests/test_visual_medium_policy.py",
    "tests/test_visual_medium_resolver_v2.py",
    "tests/test_visual_medium_prompt_v2.py",
    "tests/test_text_capacity_v2.py",
    "tests/test_visual_thesis.py",
    "tests/test_visual_thesis_compiler_contract.py",
    "tests/test_full_slide_context.py",
    "tests/test_full_slide_prompt_context.py",
    "tests/test_acceptance_contract.py",
    "tests/test_acceptance_prompt_contract.py",
)

run("python", "-m", "pytest", "-q", *AGGREGATE_TESTS)

ledger = LEDGER.read_text(encoding="utf-8").rstrip()
if "## Step 5.1｜Visual Thesis 强校验" not in ledger:
    ledger += '''

## Step 5.1｜Visual Thesis 强校验

状态：已完成

已完成工作：
- 新增 `cyberppt/visual_thesis.py`，将 visual thesis 固化为独立语义合同。
- 缺失 thesis、与 core judgment 相同或高相似度、纯口号式且缺少关系性信号的 thesis 均阻断。
- Visual Stage compiler 删除 `selected.visual_thesis or core_judgment` fallback；PageArtifactSpec 增加第二道防绕过校验。
- `ppt-visual-structure-designer/SKILL.md` 同步升级为可执行强约束。
- 新增 `tests/test_visual_thesis.py`、`tests/test_visual_thesis_compiler_contract.py`。

验证结果：
- Visual Thesis 领域与生产链定向测试通过，并回归 Text Capacity 与 Visual Medium v2。
- 业务提交：`ed6a692e565190681b1ba93a2a44a1ad2431a3a0`（`stage2-v3: enforce relational visual thesis`）。
- Phase 5 验收完成：`visual_thesis == core_judgment` 被阻断，且不存在 core judgment fallback。

下一阶段工作：
- Phase 6：增加完整 16:9 Full-slide Design Context，同时保持 external title layer 和 2048×1024 body export 兼容。

## Step 6.1｜16:9 Full-slide Design Context

状态：已完成

已完成工作：
- 新增 `cyberppt/full_slide_context.py`，建立 1920×1080（16:9）完整页面设计坐标合同。
- 外置标题区为 `x=128, y=52, w=1664, h=120`；正文图区为 `x=128, y=216, w=1664, h=832`，保持 2:1。
- Stage02 handoff、PageArtifactSpec、FinalPromptIR、Renderer、validator、debug receipt 全部贯通 full-slide context。
- 标题与副标题继续由 external text layer 提供，正文图继续独立导出为 2048×1024。
- 旧 handoff 缺少 full-slide 字段时通过 `legacy_stage02_prompt_contract` 做兼容投影。

验证结果：
- `test_full_slide_context + test_full_slide_prompt_context` 及 Visual Thesis / Text Capacity / Medium 回归测试通过。
- 业务提交：`21ab6b1fdfc2beffcedc3e2f7836edb657bc3109`（`stage2-v3: add full-slide design context to production chain`）。
- Phase 6 验收完成：构图知道完整 16:9 标题区域，同时既有 body-image 和 editable reconstruction 边界保持兼容。

下一阶段工作：
- Phase 7：新增 AcceptanceSpec，将生成要求升级为可机器校验的验收合同，并启用 artifact-spec-v3 正式路径。

## Step 7.1｜Acceptance Contract 与 artifact-spec-v3

状态：已完成

已完成工作：
- 新增 `cyberppt/acceptance_contract.py` 与 `AcceptanceSpec`。
- 八项验收字段完整落地：exact copy coverage、extra text count、region ownership、relationship accuracy、hierarchy preservation、minimum readability、forbidden structure absence、style lock conformance。
- PageArtifactSpec 同时补齐 `composition_strategy` 审计字段，确保 v3 正式路径具备完整权威链。
- FinalPromptIR 升级至 v6；最终 Prompt 新增 `[Acceptance criteria]`；validator 校验出现次数、顺序和关键值；debug receipt 与该合同保持一致。
- 新增 `artifact-spec-v3` 编译器标识并保留 `artifact-spec-v2`；v3 要求 Copy Contract、Composition Strategy、Region Graph、Visual Medium Policy、Acceptance、Full-slide Context 和 passed Text Capacity 全部存在。
- 新增 `tests/test_acceptance_contract.py`、`tests/test_acceptance_prompt_contract.py`。

验证结果：
- Acceptance domain 与生产链集成测试通过，并同时回归前六阶段核心合同。
- 业务提交：`df36e28b3e59847f7813de2924f5edad531c4907`（`stage2-v3: add production acceptance contract`）。
- Phase 7 验收完成，七个功能阶段全部进入正式生产链。

下一阶段工作：
- 执行聚合定向测试、清理临时开发执行器，再运行仓库全量 CI 与兼容性检查。

## Step 8｜聚合定向测试与临时开发设施清理

状态：已完成聚合定向测试；全量 CI 待最终核对

已完成工作：
- 聚合执行 Phase 1–7 新增测试及跨阶段回归测试。
- 删除本次开发使用的临时 `tools/stage2_v3_*.py` 执行器。
- 删除本次开发使用的 `.github/workflows/stage2-v3-apply.yml` 专用工作流。
- 正式功能代码、领域合同、生产链改造和长期回归测试全部保留。

验证结果：
- Phase 1–7 聚合定向测试全部通过后才执行清理提交。

下一阶段工作：
- 由仓库常规 `CyberPPT tests` 工作流执行全量 CI；对照开发基线区分既有失败与本次增量回归，并据此决定 PR 是否可转 Ready for review。
'''
    LEDGER.write_text(ledger + "\n", encoding="utf-8", newline="\n")

run("git", "config", "user.name", "github-actions[bot]")
run("git", "config", "user.email", "41898282+github-actions[bot]@users.noreply.github.com")
run("git", "add", str(LEDGER.relative_to(ROOT)))

tracked = subprocess.run(
    ["git", "ls-files", "tools/stage2_v3_*.py"],
    cwd=ROOT,
    check=True,
    text=True,
    capture_output=True,
).stdout.splitlines()
cleanup = [path for path in tracked if path]
workflow = ".github/workflows/stage2-v3-apply.yml"
if (ROOT / workflow).exists():
    cleanup.append(workflow)
if cleanup:
    run("git", "rm", "--", *cleanup)

if run("git", "diff", "--cached", "--quiet", check=False).returncode != 0:
    run("git", "commit", "-m", "stage2-v3: finalize implementation and remove dev runners")
    run("git", "push", "origin", "HEAD:feature/stage2-artifact-contract-v3")
