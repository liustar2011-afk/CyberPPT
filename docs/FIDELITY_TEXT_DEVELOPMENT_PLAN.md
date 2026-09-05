# Stage 01 / Stage 02 保真文字改造开发方案

## 1. 目标与结论

本次改造建立三个职责清晰的文字层：

| 文字层 | 产生阶段 | 用途 | 是否允许 Stage 02 改写 |
|---|---|---|---|
| 完整文字稿 `full_copy` | Stage 01 AUTHOR | 页面完整语义、事实与论证来源 | 允许据此选择、改写、合并、精简和重排 |
| 上屏文字 `onscreen_text` | Stage 02 输入适配 | 送图模型使用的完整内容素材 | 允许自由处理 |
| 保真文字 `fidelity_text` | Stage 01 AUTHOR；外部稿可选 | 极少量必须保持字面准确的原子字符串 | 不允许改写 |

技术判断：`SUPPORT WITH CONDITIONS`。方案可行，实施时需要同步修改字段合同、解析渲染、Stage 02 输入适配、manifest、prompt 和窄范围文字验收。只修改文档措辞无法建立可靠的数据流。

## 2. 字段合同

### 2.1 `full_copy`

- 保持现有名称和权威地位。
- 内容页必须提供。
- 承载完整事实、主体、动作、关系、状态、责任、数字、条件、边界和论证。
- Stage 01 AUTHOR 完成 `full_copy` 后，只提取 `fidelity_text`，不再单独撰写 `onscreen`。

### 2.2 `fidelity_text`

建议采用字符串数组，JSON 示例：

```json
{
  "fidelity_text": [
    "2028年",
    "37.5%",
    "《国家数据基础设施建设指引》"
  ]
}
```

Markdown 示例：

```markdown
### 保真文字

- 2028年
- 37.5%
- 《国家数据基础设施建设指引》
```

准入范围：

- 精确数字及必要单位；
- 政策、规划、标准、机构的正式全称；
- 用户明确指定的专有名词、型号或固定字符串。

排除范围：

- 页面结论和普通句子；
- 完整段落；
- 为追求文案风格而锁定的表达；
- 可以安全同义改写的业务措辞。

确定性约束：

- 内容页允许空数组；
- 每项去除首尾空白后必须非空；
- 自动去重并保持原顺序；
- 每项必须能在 `full_copy` 中找到原文，用户显式指定的例外需有明确来源标记；
- 数字必须携带足以识别含义的单位，存在歧义时保留最短必要上下文；
- 设置保守容量门槛，初始建议每页不超过 8 项、合计不超过 120 个有效字符；超限进入人工审阅，不自动截断。

### 2.3 Stage 02 运行时 `onscreen_text`

该字段成为送图内容素材的统一内部接口：

- `source_mode=script_file`：取 Stage 01 `full_copy`；
- `source_mode=external_script`：优先取外部稿结构化 `内容` 字段；
- 外部稿没有结构化 `内容` 时：取页面标题下的自由正文；
- `fidelity_text` 始终独立传递，不拼入 `onscreen_text`。

## 3. 数据流设计

### 3.1 Stage 01 AUTHOR

```text
来源证据
  ↓
AUTHOR 编写并审阅 full_copy
  ↓
从 full_copy 提取少量 fidelity_text
  ↓
Final Script 保存 full_copy + fidelity_text
```

AUTHOR 阶段取消以下职责：

- 生成独立的上屏精炼稿；
- 为视觉密度压缩完整文字稿；
- 规划上屏模块、层级和逐项表达。

仍保留以下职责：

- 页面使命与核心结论；
- 完整论证与来源边界；
- 数字、政策名称等保真项识别；
- 演讲者备注；
- 事实、状态、责任和关系强度审计。

### 3.2 Stage 02 输入适配

在 Stage 02 自有输入快照中完成派生，不回写 Stage 01 权威脚本：

```text
内部 Stage 01 脚本
  full_copy ───────→ runtime.onscreen_text
  fidelity_text ───→ runtime.fidelity_text

外部稿
  内容/自由正文 ───→ runtime.onscreen_text
  保真文字（可选） → runtime.fidelity_text
```

该映射必须发生在 `prepare_stage02_input` / `build_stage02_input` 路径，确保后续 handoff、manifest、续跑哈希和 prompt 均消费同一份 Stage 02 快照。

### 3.3 送图 prompt

每页送图数据增加独立区块：

```text
【内容素材】
<runtime.onscreen_text>

【保真文字】
- <fidelity item 1>
- <fidelity item 2>
```

Prompt 合同：

- 内容素材允许模型选择、改写、合并、精简、重排、拆分和替换措辞；
- 保真文字若出现在图中，必须使用字段中的准确写法；
- 对声明为强制可见的保真项，还必须验证其实际出现；
- 不依据 `onscreen_text` 或 `full_copy` 做逐字 OCR 对齐。

为避免“保真”语义含混，建议为每项保留可见性属性。最小数据结构如下：

```json
{
  "text": "《国家数据基础设施建设指引》",
  "visibility": "required"
}
```

允许值：

- `required`：必须出现且字面准确；
- `if_rendered`：模型可以不显示，显示时必须字面准确。

如果首版希望保持简单，可以统一采用 `required`，并严格限制字段数量。

## 4. 代码修改范围

### 4.1 Stage 01 合同与作者规则

重点文件：

- `AGENTS.md`
- `docs/CYBERPPT_WORKFLOW.md`
- `.agents/skills/cyberppt-script-workflow/SKILL.md`
- `.agents/skills/cyberppt-script-workflow/references/authoring-contract.md`
- `contracts/final-script.schema.json`
- `script_engine/render.py`
- `script_engine/author_contracts.py`
- `script_engine/lint_contracts.py`
- `script_engine/structural_contracts.py`
- `script_engine/analysis_audits/final_lean.py`
- `script_engine/analysis_audits/final_onscreen.py`
- `script_engine/analysis_audits/final_authoring_expression.py`
- `script_engine/analysis_audits/final_authoring_structure.py`
- `script_engine/analysis_audits/composed_trace_core.py`

改动要点：

1. Final Script 内容页以 `full_copy + fidelity_text` 取代 `full_copy + onscreen` 的 AUTHOR 合同。
2. Markdown 渲染输出“完整文字稿”和“保真文字”。
3. 删除“完整文字稿与上屏文字必须保持差异”的审计。
4. 删除 Stage 01 上屏层级、模块、标点、长度、密度和投影审计。
5. 新增保真项来源、格式、数量和长度审计。
6. 继续审计完整文字稿的事实、状态、责任、数字和来源边界。

### 4.2 Stage 01 Markdown 解析

重点文件：

- `cyberppt/script_quality/parsing.py`
- `cyberppt/script_quality/models.py` 或实际 `ScriptPage` 定义位置
- `cyberppt/script_quality/text_rules.py`
- `cyberppt/script_quality/audit.py`
- `cyberppt/script_quality/presentation.py`

改动要点：

1. 增加 `fidelity_text` 和原始字段来源信息。
2. Stage 01 标准解析不再把 `full_copy` 自动视为 AUTHOR 上屏稿。
3. 移除 `CONTENT_PROSE_EQUALS_ONSCREEN` 等与新合同冲突的规则。
4. 删除 Stage 01 `上屏文字` 的字段职责和对应解析分支。

### 4.3 Stage 02 输入与 handoff

重点文件：

- `cyberppt/stage02_input.py`
- `cyberppt/stage02_handoff.py`
- `cyberppt/stage02_readiness.py`
- `cyberppt/stage02_production/preflight.py`

改动要点：

1. 在构建 Stage 02 快照时读取 `source_mode`。
2. 内部稿明确执行 `full_copy → onscreen_text`。
3. 外部稿增加 `内容` 字段解析和自由正文回退。
4. `fidelity_text` 写入 Stage 02 page record。
5. input、handoff 和 build context 的语义哈希覆盖新字段。
6. 源文件或保真字段变化后，旧 manifest 和文字验收回执不得复用。

### 4.4 Manifest 与 prompt 编译

重点文件：

- `scripts/imagegen_pipeline/page_manifest.py`
- `scripts/imagegen_pipeline/handoff/text.py`
- `scripts/imagegen_pipeline/handoff/prompt.py`
- `cyberppt/stage02_production/manifest_stage.py`
- `scripts/imagegen_pipeline/prompt_diagnostics.py`

建议 manifest 页面结构：

```json
{
  "page_number": 3,
  "content_text": "……完整内容素材……",
  "fidelity_text": [
    {"text": "2028年", "visibility": "required"}
  ],
  "full": {
    "prompt": "……",
    "prompt_sha256": "……"
  }
}
```

改动要点：

1. Prompt 编译器显式接收 `content_text` 和 `fidelity_text`。
2. 停止从普通内容推导大段 `image_locked_text`。
3. `select_image_locked_text` 只消费 `fidelity_text`，不得再扫描普通正文自动加锁。
4. prompt hash、input fingerprint 和复用判断包含保真字段。
5. 调试回执分别记录内容素材哈希和保真项哈希。

### 4.5 图片文字验收

重点文件：

- `cyberppt/image_text_gate.py`
- `cyberppt/stage02_production/image_stage.py`
- `scripts/imagegen_pipeline/prompt_diagnostics.py`
- `scripts/image_to_pptx_runtime/final_visible_text_qa.py`

验收分为两层：

1. 通用字形质量：继续检查明确错字、乱码和伪中文。
2. 保真项验收：仅对 `fidelity_text` 执行存在性和字面准确性检查。

验收不得执行：

- `full_copy` 与 OCR 全文匹配；
- `onscreen_text` 与 OCR 全文匹配；
- 因普通措辞变化判定失败；
- 因模型删减非保真文字判定失败。

OCR 对长政策名称可能分成多个文本框，匹配器需要支持：

- 空白和换行归一化；
- 相邻 OCR 片段按阅读顺序拼接；
- 中文书名号和全角标点的明确策略；
- 数字与单位保持严格一致；
- 低置信度结果进入视觉复核，避免无限自动重试。

## 5. 输入策略

### 5.1 新 Stage 01 脚本

- schema 升级一个明确版本；
- 内容页要求 `full_copy`；
- `fidelity_text` 可为空；
- 不再要求 AUTHOR 提供 `onscreen`。

### 5.2 外部稿

建议支持三类输入：

1. 结构化 Markdown：`页面标题 + 内容 + 保真文字`；
2. 自由 Markdown：页标题下全部正文作为内容，保真文字为空。

外部稿只在 `--external-script` 模式启用“内容字段”别名，防止 Stage 01 标准脚本出现两套内容权威。

## 6. 实施顺序

### 阶段 A：冻结合同

1. 更新工作流与 AUTHOR 文档。
2. 定义 schema 版本、字段类型、可见性语义和容量门槛。
3. 准备内部稿、结构化外部稿和自由外部稿 fixtures。

验收标准：字段职责没有交叉；示例可以覆盖所有来源模式。

### 阶段 B：完成 Stage 01 改造

1. 更新 Final Script schema。
2. 更新 JSON/Markdown 渲染与解析。
3. 删除旧 onscreen AUTHOR 审计。
4. 新增 fidelity 审计。
5. 更新 AUTHOR、Critic、Rewrite 合同测试。

验收标准：新脚本只需 `full_copy + fidelity_text` 即可通过 Stage 01 合同；普通正文不进入保真项。

### 阶段 C：完成 Stage 02 输入适配

1. 实现内部稿与外部稿的分流映射。
2. 更新 Stage 02 input/handoff page record。
3. 更新哈希、变更检测和断点续跑绑定。

验收标准：内部稿的运行时上屏文字等于 `full_copy`；外部稿等于 `内容` 或自由正文；保真项保持独立。

### 阶段 D：完成送图和验收

1. manifest 增加 `fidelity_text`。
2. prompt 增加独立保真区块。
3. 普通内容保持自由改写合同。
4. 增加保真项 OCR/视觉验收。
5. 更新重试、复用和回执逻辑。

验收标准：改写普通文案能够通过；遗漏或写错 required 保真项会失败；保真项之外的增删改不会触发逐字失败。

### 阶段 E：端到端验证

通过正式入口运行：

```bash
.venv/bin/python3 -m cyberppt final-script-pages ... --production-build
```

验证内部 Stage 01 稿和外部稿各一组，检查：

- Stage 02 input；
- handoff；
- page manifest；
- 实际送图 prompt；
- OCR/视觉验收回执；
- 断点续跑；
- image、editable、both 三个组装分支共享同一保真验收结果。

## 7. 测试矩阵

| 场景 | 预期结果 |
|---|---|
| Stage 01 有完整稿、无保真项 | 通过；Stage 02 收到完整内容素材；无精确字符串门禁 |
| Stage 01 有数字和政策名称保真项 | prompt 独立携带；图片中缺失或错写 required 项时失败 |
| Stage 01 普通正文被模型改写 | 通过 |
| 外部稿含 `内容` | `内容` 写入运行时上屏文字 |
| 外部稿含自由正文 | 自由正文写入运行时上屏文字 |
| 外部稿缺少内容 | 输入审计失败并指出具体页面 |
| 保真项不在完整稿中 | Stage 01 审计失败 |
| 保真项超过容量 | 进入人工审阅，不自动截断 |
| 普通措辞未出现在图片中 | 不触发文字一致性失败 |
| 保真字段变化后续跑 | prompt hash 改变，相关页重新生成和验收 |

建议重点更新或新增测试：

- `tests/script_engine/test_contract_and_render.py`
- `tests/script_engine/test_content_planning_fusion.py`
- `tests/test_stage02_handoff.py`
- `tests/test_stage02_input.py`
- `tests/_final_script_pages_base.py`
- `tests/test_prompt_compiler_production_entrypoints.py`
- `tests/test_image_text_gate.py`
- `tests/test_prompt_diagnostics.py`
- `tests/test_stage02_manifest_reuse_identity.py`

## 8. 发布

### 发布

- 一次性提交 schema、解析、Stage 02 映射和测试，避免中间版本出现字段错配；
- 新建项目只写新 schema；
- 生产前用一个内部脚本项目和一个外部稿项目做正式入口验证。

## 9. 完成定义

以下条件全部满足后，本次改造才算完成：

1. Stage 01 AUTHOR 产物使用 `完整文字稿 + 保真文字`；
2. Stage 01 不再要求独立上屏稿；
3. Stage 02 内部稿将完整文字稿映射为上屏内容素材；
4. Stage 02 外部稿将内容字段或自由正文映射为上屏内容素材；
5. manifest 和实际送图 prompt 均含独立保真字段；
6. 仅保真字段接受精确字符串验收；
7. 普通内容允许自由改写且不会触发逐字匹配失败；
8. 字段变化能正确使续跑回执失效；
9. 定向测试和正式入口端到端验证全部通过；
10. 工作流、AUTHOR 合同和 Stage 02 Skill 与代码行为一致。
