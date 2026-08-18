# Stage 2 Final ImageGen Prompt Compiler Optimization Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 将 Stage 2 最终 ImageGen 提示词从多套字符串拼接和内部字段泄漏，收敛为单一、结构化、可校验、低冗余的最终提示词编译链路。

**Architecture:** 以现有 `PageArtifactSpec` 为权威输入，新增轻量 Prompt IR 和唯一 renderer。最终送图文本与 debug/provenance receipt 分离；页面语义、阅读路径、文字合同和风格运行规则在编译前完成归一化，最终文本只保留 ImageGen 必需信息。

**Tech Stack:** Python 3.12、现有 `scripts/imagegen_pipeline`、`dataclasses`、pytest、仓库 `.venv/bin/python3`。

## Global Constraints

- Stage 2 正式生产只允许一个最终提示词组装入口，优先使用 `artifact-spec-v2`。
- 不修改 Source Truth、Stage 01 语义事实或最终页面文字事实。
- 内部审计字段保存在 sidecar receipt，不直接进入最终 ImageGen prompt。
- 保留现有 `build_page_prompt()` 字符串兼容接口，但其内部必须调用新的唯一 renderer。
- 不新增第二套并行风格系统，不通过字符串切段覆盖原始提示词。
- 运行 Python 命令必须使用仓库 `.venv/bin/python3`。
- 不改变现有图片生成器、PPTX 还原器和 Stage 02 handoff 的外部契约，除非测试证明契约需要更新。

## 现状与问题

当前相关入口包括：

- `scripts/imagegen_pipeline/handoff/prompt.py::compile_page_prompt`
- `scripts/imagegen_pipeline/artifact_prompt.py::render_artifact_prompt`
- `scripts/imagegen_pipeline/page_manifest.py::build_manifest`
- `cyberppt/visual_prompt_consumer.py`

当前最终提示词存在以下可验证问题：

1. 多个 compiler、legacy 路径和外部重组脚本并存，最终文本来源不唯一。
2. `PageArtifactSpec` 的证据、关系、载体和内部字段未经降噪直接输出。
3. 页面核心论点、阅读路径和空间组织可能互相矛盾。
4. 同一业务判断、语义组和风格规则重复出现。
5. 后端字段可能泄漏到最终 prompt，例如 `P0 process`、`main chain`、`outside_to_center`。
6. 缺少最终 prompt 的长度、重复率、占位符和语义一致性门禁。
7. 外部 `reassemble_style10_prompts.py` 通过文本切割二次重组，破坏正式编译链路。

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

### 修改文件

- `scripts/imagegen_pipeline/handoff/prompt.py`
  - 让 `compile_page_prompt()` 统一调用 IR builder 和 renderer。
- `scripts/imagegen_pipeline/artifact_prompt.py`
  - 将现有九段 artifact spec 输入转换为 IR；不再直接承担最终文本拼接职责。
- `scripts/imagegen_pipeline/page_manifest.py`
  - 保存最终 prompt 的 hash、IR 版本、contract 结果和 debug receipt 路径。
- `cyberppt/visual_prompt_consumer.py`
  - 仅提供结构化视觉设计输入，不向最终 prompt 注入内部字段。
- 相关 CLI 或 Stage 02 receipt 写入逻辑
  - 取消外部字符串重组作为正式生产步骤。

## 实施任务

### Task 1: 建立最终 Prompt IR

**Files:**

- Create: `scripts/imagegen_pipeline/final_prompt_ir.py`
- Test: `tests/imagegen_pipeline/test_final_prompt_ir.py`

**Interfaces:**

- Produces `FinalPromptIR`、`SemanticGroupIR`、`CompositionIR`、`RuntimeLockIR`。
- `FinalPromptIR` 至少包含：`deliverable`、`page_judgment`、`dominant_relationship`、`reading_path`、`semantic_groups`、`visible_text`、`hard_constraints`、`runtime_lock`。

- [ ] **Step 1: Write failing tests**

测试必须覆盖：

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

测试 P04 类输入：

- 只能产生一个 `reading_path`；
- `primary_focus` 必须在路径中；
- 语义组数量不超过 4；
- 完整判断不得以“可信”等悬空短语结尾；
- 内部关系元数据不进入 `page_judgment` 或 `composition` 的可见文本。

- [ ] **Step 2: Run tests and confirm failure**

```bash
.venv/bin/python3 -m pytest -q tests/imagegen_pipeline/test_final_prompt_ir.py -k normalization
```

- [ ] **Step 3: Implement normalization**

规则：

1. 从 `PageArtifactSpec` 读取事实，不重新推断事实。
2. 将同一主题的 visible text 聚合为不超过 4 个语义组。
3. 从 `composition.reading_path` 只选择一个主路径。
4. 将关系、方向、置信度等内部信息写入 debug metadata，而非 prompt prose。
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
```

- [ ] **Step 2: Implement fixed seven-section rendering**

Renderer 只渲染 IR 的最终字段，不读取原始 Markdown，也不执行正则切段、风格替换或旧 prompt 拼接。

- [ ] **Step 3: Add a prompt budget**

初始上限建议：`12_000` 字符。超过上限时先报错，不自动截断。后续通过真实 ImageGen 评测调整阈值。

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
- 发现 `P0 process`、`outside_to_center`、`main chain`；
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
- manifest 增加：`prompt_ir_version`、`prompt_sha256`、`prompt_contract`、`debug_receipt`。

- [ ] **Step 1: Add integration tests against a real project page**

选择 P04 作为回归样本，验证：

- 输出仅有一个正式来源；
- prompt 长度在预算内；
- 文字合同完整；
- 阅读路径唯一；
- 不含内部字段；
- style runtime lock 只出现一次。

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
  tests/imagegen_pipeline/test_final_prompt_contract.py
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

以 P04 为代表的最终 prompt 必须满足：

- 字符数不超过设定预算；
- 只有一个页面判断；
- 只有一个主阅读路径；
- 语义组不超过 4 个；
- 所有锁定文字完整且各出现一次；
- 不出现内部审计字段或编译字段；
- 不出现截断句和未解析占位符；
- 不出现重复风格说明和重复执行锁；
- prompt 与 debug receipt 可以相互追溯；
- `CompiledPagePrompt.prompt` 只能由唯一 renderer 生成。

## 风险与控制

| 风险 | 控制措施 |
|---|---|
| 旧消费者依赖九段 prompt | 保留 `build_page_prompt()` 和 `CompiledPagePrompt` 的兼容接口 |
| 页面文字被错误压缩 | visible text 以结构化 tuple 保存，并执行精确合同校验 |
| 视觉判断过度模板化 | IR 只固定关系和层级，不固定具体场景或图形载体 |
| 旧项目无法迁移 | 保留 legacy compiler，但禁止其进入新 Stage 2 正式生产 |
| 风格更新导致 prompt 膨胀 | 只允许 StyleRuntimeContract 进入 renderer，并执行长度门禁 |

## 建议实施顺序

1. Task 1：Prompt IR。
2. Task 2：ArtifactSpec 归一化。
3. Task 3：唯一 Renderer。
4. Task 4：Contract 门禁。
5. Task 5：接入 Stage 2。
6. Task 6：清理外部二次重组路径。

每个任务独立测试通过后再进入下一任务；不建议先大范围重构 `handoff/prompt.py`，应先让新 IR 和 renderer 在旁路测试中稳定，再替换正式调用点。
