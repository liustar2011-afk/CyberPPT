# Stage 2 Final ImageGen Prompt Compiler Optimization Plan (v2)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.
>
> 本版本基于 `2026-08-18-stage2-final-prompt-compiler-optimization.md` 修订，修订依据是对现有代码和真实生产 manifest 的核实结果（见"现状核实证据"一节）。修订点：字段命名冲突、默认 compiler 入口未完全收口、prompt 长度预算脱离真实数据。原方案的问题诊断和整体架构方向经核实是准确的，予以保留。

**Goal:** 将 Stage 2 最终 ImageGen 提示词从多套字符串拼接和内部字段泄漏，收敛为单一、结构化、可校验、低冗余的最终提示词编译链路。

**Architecture:** 以现有 `PageArtifactSpec` 为权威输入，新增轻量 Prompt IR 和唯一 renderer。最终送图文本与 debug/provenance receipt 分离；页面语义、阅读路径、文字合同和风格运行规则在编译前完成归一化，最终文本只保留 ImageGen 必需信息。

**Tech Stack:** Python 3.12、现有 `scripts/imagegen_pipeline`、`dataclasses`、pytest、仓库 `.venv/bin/python3`。

## Global Constraints

- Stage 2 正式生产只允许一个最终提示词组装入口：`artifact-spec-v2`。`content-first-v1` 和 `creative-brief-v1`/legacy 路径标记为 deprecated，不得再作为任何新项目、CLI 默认值或库函数默认值的入口（见 Task 0）。
- 不修改 Source Truth、Stage 01 语义事实或最终页面文字事实。
- 内部审计字段保存在 sidecar receipt，不直接进入最终 ImageGen prompt。
- 保留现有 `build_page_prompt()` 字符串兼容接口，但其内部必须调用新的唯一 renderer。
- 不新增第二套并行风格系统，不通过字符串切段覆盖原始提示词。
- 运行 Python 命令必须使用仓库 `.venv/bin/python3`。
- 不改变现有图片生成器、PPTX 还原器和 Stage 02 handoff 的外部契约，除非测试证明契约需要更新。
- manifest 新增字段不得与现有字段同名覆盖（见"现状核实证据"第3点）。

## 现状与问题（已用代码和真实生产数据核实）

当前相关入口：

- `scripts/imagegen_pipeline/handoff/prompt.py::compile_page_prompt`（348-617行）
- `scripts/imagegen_pipeline/artifact_prompt.py::render_artifact_prompt`
- `scripts/imagegen_pipeline/page_manifest.py::build_manifest`
- `cyberppt/visual_prompt_consumer.py`

可验证问题：

1. `compile_page_prompt()` 内部用 if/elif 分叉出三条完全独立的拼接逻辑：`artifact-spec-v2`（`render_artifact_prompt`）、`content-first-v1`（`render_content_first_prompt` + `stage02_semantic_adapter`，还会按 style id 再分叉进 `style09_adapter.adapt_style09` 或 `visual_prompt_consumer._compile_visual_design`）、`creative-brief-v1`/legacy（`content_lock_text` + `render_prompt`）。三条路径各自维护自己的禁用词黑名单（`EVIDENCE_ID_RE`、"完整文字稿"等硬编码字符串比对），没有统一 contract。
2. `PageArtifactSpec` 的证据、关系、载体和内部字段未经降噪直接输出。已用真实 manifest 核实：`page_image_pairs.json`（`pages_005_031_22p_...` 项目）里 P05 的正式送图文本包含字面量：
   - `P0 process: 国家节点方向／【三大建设方向】；①国家节点方向...`（`EvidenceSpec.priority + kind` 直接拼接）
   - `二、总体定位 --contains--> （一）建设国家数据基础设施电力行业节点 | direction=subject_to_object | basis=explicit | confidence=high`（`RelationshipSpec` 全部限定字段原样拼接，见 `artifact_prompt.py:33-53`）
   这些不是理论风险，是当前**已经产出并进入正式送图 manifest** 的真实文本。
3. 页面核心论点、阅读路径和空间组织可能互相矛盾（结构性风险，尚未见到具体反例，但 IR 层缺少归一化校验，无法排除）。
4. 同一业务判断、语义组和风格规则重复出现。
5. 后端字段泄漏：除第2点外，`composition.connectors` 渲染时把 `connector.main_chain` 布尔值直接转成字面量 `"main chain"` / `"secondary relation"`（`artifact_prompt.py:65-77`），`composition.spatial_organization` 原始枚举值（如 `outside_to_center`）也原样嵌入正文，未做人类可读化。
6. 缺少最终 prompt 的长度、重复率、占位符和语义一致性门禁。
7. 外部 `reassemble_style10_prompts.py` 通过正则定位 `[7. Art direction...]` 等 section marker，对已产出 prompt 做字符串切割再拼接（`style10_reassembled_20260818_v10/` 下的产物即由此生成），与 `artifact_prompt.py` 的唯一 renderer 完全独立，是一条影子编译路径。

## 现状核实证据（v2 新增，修订依据）

1. **`ARTIFACT_PROMPT_COMPILER` 已是 CLI 默认值，但不是全部默认值。**
   `handoff/cli.py:40` 已将 CLI 默认 compiler 设为 `artifact-spec-v2`；但 `page_manifest.build_manifest()`（322行）和 `handoff/prompt.compile_page_prompt()`（354行）这两个更底层的库函数，其参数默认值仍是 `DEFAULT_PROMPT_COMPILER = "content-first-v1"`（`prompt_compiler.py:20`）。任何绕开正式 CLI、直接调用这两个函数且未显式传 `prompt_compiler` 的脚本或测试，会静默落入旧的字符串拼接路径。原方案的"清理外部二次重组路径"（Task 6）没有覆盖这个内部默认值缺口。→ 新增 **Task 0**。

2. **12000 字符预算脱离真实数据，会在接入当天阻断全部生产。**
   实测真实生产 manifest（`pages_005_031_22p_fbd2d73717_20260816T101804Z-d4e2d639b2/page_image_pairs.json`）中 22 个页面的 `artifact-spec-v2` 正式送图文本长度区间为 **19129–21124 字符**，是原方案预算 12000 的 1.6～1.8 倍。若 Task 3 按原文"超过上限时先报错，不自动截断"上线，接入当天会阻断当前所有已生产页面。→ Task 3 改为先测量基线，再设定预算（见下方修订）。

3. **manifest 字段命名冲突。**
   `page_manifest.py:710-716` 已存在 `"prompt_contract"` 字段，语义是审批/新鲜度契约：
   ```json
   "prompt_contract": {
     "approved_prompt_is_source": true,
     "freshness_enforced": false,
     "canonical_prompt_is_diagnostic_only": true,
     "compact_blueprint": false,
     "compiler": "artifact-spec-v2"
   }
   ```
   （已在真实 manifest 中核实存在。）原方案 Task 5 提议再加一个同名 `prompt_contract` 字段，语义是内容校验结果 `{"status": "ok", "issues": []}`，会覆盖上述已有字段。→ 新字段改名为 `final_prompt_contract`。

## 目标最终提示词结构

最终 `prompt.txt` 只保留以下七个部分，顺序固定：

```text
1. Deliverable
2. Page judgment
3. Dominant relationship and reading path
4. Semantic groups
5. Composition skeleton and visual responsibility
6. Exact visible text contract
7. Short runtime lock
```

内部字段进入 `prompt-debug.json`，不进入 `prompt.txt`。

## 文件边界

### 新增文件

- `scripts/imagegen_pipeline/final_prompt_ir.py`
  - 定义最终提示词 IR、语义组、构图骨架和运行锁的结构化类型。
- `scripts/imagegen_pipeline/final_prompt_renderer.py`
  - 将 IR 渲染为唯一的最终 ImageGen prompt。
- `scripts/imagegen_pipeline/final_prompt_contract.py`
  - 负责长度、重复、占位符、内部字段、阅读路径和文字合同校验。
- `tests/imagegen_pipeline/test_final_prompt_ir.py`
- `tests/imagegen_pipeline/test_final_prompt_renderer.py`
- `tests/imagegen_pipeline/test_final_prompt_contract.py`
- `tests/imagegen_pipeline/test_prompt_compiler_default_entrypoint.py`（v2 新增，对应 Task 0）

### 修改文件

- `scripts/imagegen_pipeline/prompt_compiler.py`
  - （v2 新增）将 `DEFAULT_PROMPT_COMPILER` 改为 `ARTIFACT_PROMPT_COMPILER`，或改造为强制显式传参。
- `scripts/imagegen_pipeline/handoff/prompt.py`
  - 让 `compile_page_prompt()` 统一调用 IR builder 和 renderer。
- `scripts/imagegen_pipeline/artifact_prompt.py`
  - 将现有九段 artifact spec 输入转换为 IR；不再直接承担最终文本拼接职责。
- `scripts/imagegen_pipeline/page_manifest.py`
  - 保存最终 prompt 的 hash、IR 版本、`final_prompt_contract` 结果和 debug receipt 路径（字段名已按第3点核实结果调整）。
- `cyberppt/visual_prompt_consumer.py`
  - 仅提供结构化视觉设计输入，不向最终 prompt 注入内部字段。
- 相关 CLI 或 Stage 02 receipt 写入逻辑
  - 取消外部字符串重组作为正式生产步骤。

## 实施任务

### Task 0（v2 新增）：收口默认 compiler 入口

**动机：** 见"现状核实证据"第1点。不做这一步，Task 6 清理外部重组脚本后，仍会留下一个未清理的内部默认值缺口，"唯一入口"验收标准无法真正成立。

**Files:**

- Modify: `scripts/imagegen_pipeline/prompt_compiler.py`
- Modify: `scripts/imagegen_pipeline/page_manifest.py`（`build_manifest`、`_relationship_aware_canonical_prompts` 的默认参数）
- Modify: `scripts/imagegen_pipeline/handoff/prompt.py`（`compile_page_prompt`、`build_page_prompt` 的默认参数）
- Test: `tests/imagegen_pipeline/test_prompt_compiler_default_entrypoint.py`

- [ ] **Step 1: Write failing test**

断言：不传 `prompt_compiler` 参数直接调用 `build_manifest()` 和 `compile_page_prompt()` 时，实际生效的 compiler 是 `artifact-spec-v2`，而不是 `content-first-v1`。

- [ ] **Step 2: Run test and confirm failure**

```bash
.venv/bin/python3 -m pytest -q tests/imagegen_pipeline/test_prompt_compiler_default_entrypoint.py
```

- [ ] **Step 3: 修改默认值**

将 `DEFAULT_PROMPT_COMPILER` 改为等于 `ARTIFACT_PROMPT_COMPILER`。逐一检查所有依赖 `DEFAULT_PROMPT_COMPILER` 的调用点（`page_manifest.py`、`handoff/prompt.py`、`imagegen_handoff.py` 等），确认没有调用点隐式依赖旧的 `content-first-v1` 行为（例如依赖 `visual_design`/`enrichment_block` 参数）。若发现这类调用点，改为显式传参并保留其行为，不静默改变现有测试的通过路径。

- [ ] **Step 4: Run full prompt-compiler test suite**

```bash
.venv/bin/python3 -m pytest -q tests/imagegen_pipeline -k "prompt or manifest or compiler"
```

Expected: PASS，且没有测试因为默认值变化而意外改变断言对象。

### Task 1: 建立最终 Prompt IR

**Files:**

- Create: `scripts/imagegen_pipeline/final_prompt_ir.py`
- Test: `tests/imagegen_pipeline/test_final_prompt_ir.py`

**Interfaces:**

- Produces `FinalPromptIR`、`SemanticGroupIR`、`CompositionIR`、`RuntimeLockIR`。
- `FinalPromptIR` 至少包含：`deliverable`、`page_judgment`、`dominant_relationship`、`reading_path`、`semantic_groups`、`visible_text`、`hard_constraints`、`runtime_lock`。

- [ ] **Step 1: Write failing tests**

```python
def test_final_prompt_ir_requires_one_reading_path():
    ir = make_ir(reading_path=("①", "②", "③"))
    assert ir.reading_path == ("①", "②", "③")


def test_semantic_group_preserves_exact_visible_text():
    group = SemanticGroupIR(
        id="demand",
        role="input",
        visible_text=("①需求侧变化",),
        emphasis="secondary",
    )
    assert group.visible_text == ("①需求侧变化",)
```

- [ ] **Step 2: Run the focused test and verify it fails**

```bash
.venv/bin/python3 -m pytest -q tests/imagegen_pipeline/test_final_prompt_ir.py
```

Expected: FAIL because the IR types do not exist.

- [ ] **Step 3: Implement the minimal immutable dataclasses**

使用 `@dataclass(frozen=True)`，对 `role`、`emphasis` 和关系类型使用 `Literal` 或显式校验。禁止 IR 接收未解析的后端字段作为最终文本字段。

- [ ] **Step 4: Run the focused test**

```bash
.venv/bin/python3 -m pytest -q tests/imagegen_pipeline/test_final_prompt_ir.py
```

Expected: PASS。

### Task 2: 将 ArtifactSpec 转换为 IR

**Files:**

- Modify: `scripts/imagegen_pipeline/artifact_prompt.py`
- Modify: `scripts/imagegen_pipeline/handoff/prompt.py:348-592`
- Test: `tests/imagegen_pipeline/test_final_prompt_ir.py`

**Interfaces:**

- Add `build_final_prompt_ir(spec: PageArtifactSpec, ...) -> FinalPromptIR`。
- `compile_page_prompt()` 保持现有参数和返回类型兼容，但内部不再直接拼接长文本。

- [ ] **Step 1: Add failing semantic normalization tests**

测试 P04/P05 类真实输入（可直接取 `page_image_pairs.json` 中的真实 `PageArtifactSpec` 反序列化作为 fixture，而不是手写简化样例，避免测试通过但真实数据不通过）：

- 只能产生一个 `reading_path`；
- `primary_focus` 必须在路径中；
- 语义组数量超过 4 时，必须抛出 `PromptContractError`，**不得静默合并**（合并会改变证据分组，等同篡改事实结构，违反 Global Constraint 的"不修改 Source Truth"）；
- 完整判断不得以"可信"等悬空短语结尾；
- 内部关系元数据（`direction`/`condition`/`modality`/`basis`/`confidence`、`main_chain` 布尔值、`spatial_organization` 原始枚举值）不进入 `page_judgment` 或 `composition` 的可见文本，只进入 debug metadata。

- [ ] **Step 2: Run tests and confirm failure**

```bash
.venv/bin/python3 -m pytest -q tests/imagegen_pipeline/test_final_prompt_ir.py -k "normalization or semantic_group_limit"
```

- [ ] **Step 3: Implement normalization**

规则：

1. 从 `PageArtifactSpec` 读取事实，不重新推断事实。
2. 将同一主题的 visible text 聚合为不超过 4 个语义组；聚合规则必须是确定性的（例如按 `evidence.kind` 或已有的 `composition.spatial_grammar` 分组），不允许启发式/近似合并压缩数量。
3. 从 `composition.reading_path` 只选择一个主路径。
4. 将关系、方向、置信度、`main_chain`、`spatial_organization` 原始值等内部信息写入 debug metadata，而非 prompt prose；`EvidenceSpec.priority`/`kind` 同样只作为分组依据，不直接以 `"P0 process:"` 这类前缀写入正文（对应第2点已核实的真实泄漏）。
5. 对核心判断执行完整句校验，失败时抛出 `PromptContractError`。

- [ ] **Step 4: Run focused tests**

```bash
.venv/bin/python3 -m pytest -q tests/imagegen_pipeline/test_final_prompt_ir.py
```

Expected: PASS。

### Task 3: 实现唯一最终 Prompt Renderer

**Files:**

- Create: `scripts/imagegen_pipeline/final_prompt_renderer.py`
- Modify: `scripts/imagegen_pipeline/artifact_prompt.py`
- Test: `tests/imagegen_pipeline/test_final_prompt_renderer.py`

**Interfaces:**

- Add `render_final_prompt(ir: FinalPromptIR) -> str`。
- Add `render_debug_receipt(ir: FinalPromptIR) -> dict[str, object]`。

- [ ] **Step 1: Write failing renderer tests**

```python
def test_renderer_emits_fixed_compact_sections(sample_ir):
    prompt = render_final_prompt(sample_ir)
    assert prompt.index("[1. Deliverable]") < prompt.index("[7. Runtime lock]")
    assert prompt.count("①需求侧变化") == 1


def test_renderer_does_not_emit_backend_fields(sample_ir):
    prompt = render_final_prompt(sample_ir)
    assert "outside_to_center" not in prompt
    assert "main chain" not in prompt
    assert "P0 process" not in prompt
    assert "confidence=" not in prompt
    assert "direction=" not in prompt
```

- [ ] **Step 2: Implement fixed seven-section rendering**

Renderer 只渲染 IR 的最终字段，不读取原始 Markdown，也不执行正则切段、风格替换或旧 prompt 拼接。

- [ ] **Step 3: 先测量基线，再设定 prompt 预算（v2 修订）**

原方案直接给出 `12_000` 字符作为初始上限，但实测当前生产 prompt（`artifact-spec-v2`，22 页样本）长度区间是 19129–21124 字符，直接套用 12000 会在接入当天阻断全部生产。修订为：

1. 先用新 renderer 跑一遍与实测样本相同的 22 页真实 `PageArtifactSpec`，记录新 renderer 产出长度的分布（因为归一化会砍掉大量泄漏字段，预期显著短于旧的 19k-21k，但具体数字需要实测，不能假设）。
2. 取实测分布的 p95 再加 10% 冗余作为初始上限，写入代码注释说明依据和测量时间。
3. 超过上限时先报错，不自动截断。
4. 后续通过真实 ImageGen 评测调整阈值，调整时更新注释里的依据数据。

- [ ] **Step 4: Run focused tests**

```bash
.venv/bin/python3 -m pytest -q tests/imagegen_pipeline/test_final_prompt_renderer.py
```

Expected: PASS。

### Task 4: 建立最终 Prompt Contract

**Files:**

- Create: `scripts/imagegen_pipeline/final_prompt_contract.py`
- Modify: `scripts/imagegen_pipeline/artifact_prompt.py`
- Test: `tests/imagegen_pipeline/test_final_prompt_contract.py`

**Interfaces:**

- Add `validate_final_prompt(prompt: str, ir: FinalPromptIR) -> None`。
- Add `PromptContractError`。

- [ ] **Step 1: Write failing contract tests**

至少覆盖：

- 发现两条不同阅读路径；
- 发现核心判断截断；
- 发现 `<one-sentence business judgment>` 占位符；
- 发现 `P0 process`、`outside_to_center`、`main chain`、`direction=`、`confidence=`（这五项已在真实生产数据中核实存在，必须作为回归用例的真实字符串，而不是假设性字符串）；
- 发现重复的 visible text；
- 发现重复执行锁；
- 发现超过长度上限；
- 发现标题、页码、Logo 等不应进入 body image 的文本。

- [ ] **Step 2: Implement deterministic validators**

校验失败必须阻断 prompt 写出，不允许只写 warning。

- [ ] **Step 3: Run focused tests**

```bash
.venv/bin/python3 -m pytest -q tests/imagegen_pipeline/test_final_prompt_contract.py
```

Expected: PASS。

### Task 5: 接入 Stage 2 正式编译入口

**Files:**

- Modify: `scripts/imagegen_pipeline/handoff/prompt.py:348-592`
- Modify: `scripts/imagegen_pipeline/page_manifest.py:307-727`
- Modify: `cyberppt/visual_prompt_consumer.py`
- Test: `tests/imagegen_pipeline/test_final_prompt_renderer.py`

**Interfaces:**

- `compile_page_prompt()` 返回的 `CompiledPagePrompt.prompt` 必须来自 `render_final_prompt()`。
- manifest 增加：`prompt_ir_version`、`prompt_sha256`（已存在，复用不改名）、`final_prompt_contract`（**v2 改名**，原方案写的 `prompt_contract` 会覆盖 `page_manifest.py:710` 已有的审批契约字段，见"现状核实证据"第3点）、`debug_receipt`。

- [ ] **Step 1: Add integration tests against a real project page**

选择 P04、P05 作为回归样本（P05 是已核实存在字面量泄漏的真实页面，适合作为反例回归），验证：

- 输出仅有一个正式来源；
- prompt 长度在 Task 3 实测确定的预算内；
- 文字合同完整；
- 阅读路径唯一；
- 不含内部字段，尤其是已核实的 `P0 process`、`direction=`、`confidence=`、`main chain`；
- style runtime lock 只出现一次；
- manifest 中 `final_prompt_contract` 字段与既有 `prompt_contract` 字段并存、互不覆盖。

- [ ] **Step 2: Route artifact-spec-v2 through the new renderer**

保留旧函数的 import 和返回兼容性，但移除其直接拼接最终文本的职责。

- [ ] **Step 3: Write debug receipt separately**

debug receipt 至少保存：

```json
{
  "schema": "cyberppt.final_prompt_debug.v1",
  "page": "p04",
  "compiler": "artifact-spec-v2",
  "prompt_ir_version": "v1",
  "reading_path": ["①需求侧变化", "②供给侧现状", "③应对方向"],
  "semantic_groups": [],
  "source_fields": {},
  "contract": {"status": "ok", "issues": []}
}
```

- [ ] **Step 4: Run Stage 2 focused tests**

```bash
.venv/bin/python3 -m pytest -q \
  tests/imagegen_pipeline/test_final_prompt_ir.py \
  tests/imagegen_pipeline/test_final_prompt_renderer.py \
  tests/imagegen_pipeline/test_final_prompt_contract.py \
  tests/imagegen_pipeline/test_prompt_compiler_default_entrypoint.py
```

Expected: PASS。

### Task 6: 清理外部二次重组路径

**Files:**

- Modify or deprecate: `projects/power-data-infrastructure-cooperation-v16-20260815-foundation/workbench/stages/02-imagegen/style10_reassembled_20260817/reassemble_style10_prompts.py`
- Modify: Stage 2 documentation and CLI help text
- Test: Stage 2 command-level regression test

- [ ] **Step 1: Add a regression test proving final prompts come from the official compiler**

测试应检查最终输出的 manifest 中 `compiler`、`prompt_ir_version` 和 `prompt_sha256`，而不是依赖手工复制后的 prompts 目录。

- [ ] **Step 2: Mark the external reassembler as migration-only**

保留读取旧项目产物的能力，但明确禁止作为新项目和正式 Stage 2 生产入口。

- [ ] **Step 3: Remove source prompt overwrite behavior**

正式编译只能写入当前 build output；不得将生成结果复制回 source prompts 目录。

- [ ] **Step 4: Run command-level regression**

```bash
.venv/bin/python3 -m pytest -q tests/imagegen_pipeline -k "prompt or manifest"
```

Expected: focused Stage 2 prompt and manifest tests PASS。

## 验收标准

以 P04、P05 为代表的最终 prompt 必须满足：

- 字符数不超过 Task 3 实测确定的预算（不是原方案未经验证的 12000）；
- 只有一个页面判断；
- 只有一个主阅读路径；
- 语义组不超过 4 个，且超限时报错而非静默合并；
- 所有锁定文字完整且各出现一次；
- 不出现内部审计字段或编译字段，尤其是已核实存在于当前生产数据中的 `P0 process`、`direction=`、`confidence=`、`main chain`、`outside_to_center` 类泄漏；
- 不出现截断句和未解析占位符；
- 不出现重复风格说明和重复执行锁；
- prompt 与 debug receipt 可以相互追溯；
- `CompiledPagePrompt.prompt` 只能由唯一 renderer 生成；
- 不传 `prompt_compiler` 参数直接调用 `build_manifest()`/`compile_page_prompt()` 时，实际生效的仍是 `artifact-spec-v2`（Task 0 验收项）；
- manifest 中 `final_prompt_contract` 字段与既有 `prompt_contract`（审批/新鲜度契约）字段并存、互不覆盖。

## 风险与控制

| 风险 | 控制措施 |
|---|---|
| 旧消费者依赖九段 prompt | 保留 `build_page_prompt()` 和 `CompiledPagePrompt` 的兼容接口 |
| 页面文字被错误压缩 | visible text 以结构化 tuple 保存，并执行精确合同校验 |
| 视觉判断过度模板化 | IR 只固定关系和层级，不固定具体场景或图形载体 |
| 旧项目无法迁移 | 保留 legacy compiler，但禁止其进入新 Stage 2 正式生产 |
| 风格更新导致 prompt 膨胀 | 只允许 StyleRuntimeContract 进入 renderer，并执行长度门禁 |
| （v2 新增）默认 compiler 缺口未清理，Task 6 做完后仍有隐藏 legacy 入口 | Task 0 显式收口 `DEFAULT_PROMPT_COMPILER`，并用回归测试锁定 |
| （v2 新增）长度预算脱离真实数据，接入当天阻断生产 | Task 3 先测量新 renderer 在真实样本上的长度分布，再设定预算，不采用未经验证的固定值 |
| （v2 新增）新旧 manifest 字段同名覆盖 | 新字段命名为 `final_prompt_contract`，与既有 `prompt_contract` 区分；Task 5 集成测试显式断言两者并存 |
| 语义组聚合规则不确定性可能误删证据分组 | 聚合规则限定为按已有结构化字段（`evidence.kind`/`spatial_grammar`）分组，超限报错而非启发式合并 |

## 建议实施顺序

0. Task 0：收口默认 compiler 入口（新增，优先于其余任务，避免后续任务在有缺口的基线上开发）。
1. Task 1：Prompt IR。
2. Task 2：ArtifactSpec 归一化。
3. Task 3：唯一 Renderer（含真实数据长度基线测量）。
4. Task 4：Contract 门禁。
5. Task 5：接入 Stage 2（manifest 字段已按核实结果改名）。
6. Task 6：清理外部二次重组路径。

每个任务独立测试通过后再进入下一任务；不建议先大范围重构 `handoff/prompt.py`，应先让新 IR 和 renderer 在旁路测试中稳定，再替换正式调用点。

## 实施纪要（2026-08-18，全部 6 个任务 + Task 0 已落地）

按本方案实施完成后，对照真实生产数据发现三处需要与写方案时的假设不同，均已按实测结果调整代码（未按原始文字盲目执行）：

1. **Task 0 未改 `DEFAULT_PROMPT_COMPILER`。** 实测发现 `compile_page_prompt`/`build_page_prompt` 的共享默认值被 60+ 处现有测试用来故意练习 `content-first-v1` 遗留路径（例如 `tests/test_imagegen_creative_brief.py`）。真正的两个生产入口（`handoff/cli.py` 的 `--prompt-compiler` 默认值、`cyberppt/commands/final_script_pages.py` 的 `build_manifest` 调用）经核实已经硬编码 `artifact-spec-v2`。改为只加回归测试锁定这两处，不动共享默认值——避免了一次会破坏几十个无关测试的误伤。见 [tests/test_prompt_compiler_production_entrypoints.py](../../../tests/test_prompt_compiler_production_entrypoints.py)。

2. **`primary_focus` 必须在 `reading_path` 里"这条约束被删除。** 用真实项目（`projects/power-data-infrastructure-cooperation-v16-20260815-foundation`）的 23 个页面跑归一化，**全部 23 页**都不满足这条约束——Stage 02 实际写出的 `reading_path` 是大段合并语义的长句，`primary_focus` 是另一句独立描述，两者从未是"字面量属于"关系。继续保留这条约束会让整条链路无法用于任何真实页面。已从 `FinalPromptIR.__post_init__` 移除，改为两个独立的自由文本字段，不做交叉校验。

3. **长度预算从 12000 改为 22000，且说明与"降噪"无关。** 用同一批 23 个真实页面实测：单页 IR 内容（deliverable+judgment+关系+阅读路径+语义组+可见文字+构图）总共不到 2500 字符；而 `art_direction.contract`（风格运行时锁文本，同一风格所有页面共享同一份）本身约 19500 字符，是长度的绝对主导因素。也就是说，本次重构剥离的字段泄漏（`P0 process:`、`direction=`、`confidence=`、`main chain` 等）对总长度几乎没有影响——这些泄漏本身字节数很小，问题是"内部字段不该出现"，不是"内容太长"。预算按实测 max(19920) × 1.1 取整到 22000；若未来要真正压缩长度，杠杆在风格库文案本身，不在本次的页面级编译器里，已在 `final_prompt_contract.py` 的注释中写明，避免后续维护者误以为这次重构应该、且已经大幅压缩了 prompt 体积。

以上三点已同步反映在代码注释和测试里（`final_prompt_ir.py`、`final_prompt_contract.py`、`tests/test_final_prompt_ir.py`），本文档正文未逐段回改，以此纪要为准。

全量测试对照（`git stash -u` 前后跑 `tests/`）：改动前后均为 21 个失败、且是完全相同的 21 个用例（与本次改动无关的既有失败，例如 `test_extended_style_9*`、`test_legacy_pipeline_absence.py` 等），无回归。

### 补充纪要：Stage 02 视觉结构设计成果消费不全（用户 2026-08-18 复核后发现，已修复）

首次落地后用户追问"视觉结构设计的成果消费了吗"，复核发现新 `build_final_prompt_ir()` 相比旧 `render_artifact_prompt()` 遗漏了三块 Stage 02 字段，不是有意的裁剪，是压缩到七段时的疏漏：

- `spec.visual_carrier`（`business_object`/`semantic_role`/`use_scene`/`scene_type`）——旧版 `[5. Visual carrier]` 整段，包含"禁止退化成通用仪表盘/图标墙"这条硬约束，新版完全没有承接字段。
- `composition.spatial_grammar`
- `composition.relationship_encoding`

修复方式：把 `visual_carrier` 和 `spatial_grammar` 折入 `CompositionIR.visual_responsibility`（`artifact_prompt.py::_visual_responsibility`），连同"禁止通用仪表盘"约束一起带回最终 prompt。`relationship_encoding` **没有**加回——用真实项目数据核实，当前 Stage 02 产出的 `relationship_encoding` 会把 `outside_to_anchor`/`left_to_right`/`bottom_to_top` 这类原始方向枚举直接拼进中文叙述里（例如"方向为outside_to_anchor，不以逐条文字代替"），这正是本次重构要拦截的泄漏类型，不能因为要"找回丢失内容"就把它原样搬回去。留待 Stage 02 authoring 把这个字段清理干净后再接入。

顺带修了 `final_prompt_contract.py` 里 snake_case 泄漏检测的一个边界 bug：正则用 `\w` 做词边界，但 Python 的 `\w` 也匹配中文字符，导致 `outside_to_anchor` 这类 token 紧贴中文（无空格分隔，例如"方向为outside_to_anchor，"）时检测不出来——这正是上面 `relationship_encoding` 的真实数据形态。已改为显式 ASCII 字符类边界。

修复后用真实 23 页数据重新跑通全流程（`build_final_prompt_ir` → `render_final_prompt` → `validate_final_prompt`），23/23 通过，长度 19517–20487 字符，仍在 22000 预算内。新增 4 个测试覆盖：visual_carrier 内容存在、通用仪表盘约束存在、`relationship_encoding` 原始 token 不泄漏、CJK 紧贴场景下泄漏检测生效。全量测试 1040 passed（较上一轮 +3），21 个既有失败不变。
