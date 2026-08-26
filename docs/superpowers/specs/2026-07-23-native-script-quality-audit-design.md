# CyberPPT 原生脚本质量审计设计

## 1. 背景与目标

CyberPPT 已具备 Source Truth、严格大纲论证链、失败换方向重试、脚本保存与批准、图片型 PPT 生产和视觉 QA。旧 `ppt-script` 中仍有价值但尚未产品化的部分，主要集中在逐页脚本和章级结构质量控制。

本设计新增仓库原生 `script-audit`，复用现有 Source Truth、Outline 和项目工作区，不迁移旧 `project_manager.py`，不建立第二套项目生命周期。

目标：

1. 在脚本进入生图批准前，检查页面合同、来源状态、章内推进、跨页重复、上屏结构与语义图同构、页面密度。
2. 准确拦截“工作基础页提前给出首期范围或建设结论”等论证顺序错误。
3. 审计失败时给出页面级返工范围和换方向重试建议。
4. 生成结构化 JSON 和可读 Markdown，并登记逐次尝试。
5. 保持现有 Source Truth、Outline、Stage 02 与 PPT 生产流程兼容。

## 2. 范围

### 2.1 本期包含

- 新增 `script-audit` CLI 命令。
- 新增纯规则脚本质量审计合同。
- 解析当前项目采用的批次脚本 Markdown。
- 复用严格 Outline 的页面角色、前置依赖、主张状态、Source ID 和视觉中心。
- 复用 Source Truth 的事实、判断、建议、边界、待核状态。
- 输出审计报告、逐次尝试和重试指令。
- 更新根 `SKILL.md`，将脚本质量审计加入 Stage 01 到 Stage 02 的正式门槛。
- 新增 `references/script-quality.md`，保存详细写稿和审计规则。
- 新增单元测试、命令测试和真实项目回归测试。

### 2.2 本期不包含

- 旧 `project_manager.py`。
- 忠实阅读与决策阅读双工作区。
- 总编、反方等多角色运行器。
- 历史案例索引与检索。
- 旧项目目录结构。
- 旧 `assemble`、`handoff` 命令。
- 自动修改脚本内容。
- PPT 页面视觉渲染质量检查；该职责继续由后续 QA 流程承担。

## 3. 用户入口

命令：

```powershell
python -m cyberppt script-audit <project> `
  --input <script.md> `
  --outline <outline.json> `
  --source-truth <source-truth.json>
```

参数规则：

- `<project>`：CyberPPT 项目目录。
- `--input`：必填，单批或完整脚本 Markdown。
- `--outline`：可选；默认使用 `workbench/stages/01-analysis/outline.json`。
- `--source-truth`：可选；默认使用 `workbench/stages/01-analysis/source-truth.json`。
- `--attempt`：可选；未提供时根据已有尝试自动递增。
- `--max-attempts`：可选，默认 3。

退出码：

- `0`：通过。
- `2`：输入、路径、JSON 或脚本结构错误。
- `4`：审计失败，仍可按 `retry_directive` 换方向返工。
- `5`：达到尝试上限，需要用户从升级选项中决策。

## 4. 工件与目录

默认输出：

```text
workbench/scripts/audits/
├─ script-audit.json
├─ script-audit.md
└─ attempts/
   ├─ attempt-01.json
   ├─ attempt-02.json
   └─ ...
```

`script-audit.json` 为最新权威报告，至少记录：

- `schema`
- `status`
- `attempt`
- `max_attempts`
- `remaining_attempts`
- `input`
- `outline`
- `source_truth`
- `coverage`
- `issues`
- `failed_pages`
- `retry_scope`
- `retry_directive`

每个 issue 至少记录：

- `code`
- `severity`
- `message`
- `pages`
- `source_ids`
- `evidence`
- `suggested_action`

`script-audit.md` 是从 JSON 报告生成的可读视图，不成为第二事实源。

成功生成报告后，将相关工件登记到 `artifact-ledger.json`，记录 `stage`、`page`、`path`、`status`、`depends_on`、`supersedes`、`resume_command` 和 SHA-256。

## 5. 代码结构

### 5.1 `cyberppt/script_quality_contract.py`

职责：

- 定义脚本页、脚本模块和审计问题的数据结构。
- 解析脚本 Markdown 为规范化页面列表。
- 执行确定性规则。
- 返回审计问题和失败页面，不执行文件写入。

核心公开接口建议：

```python
parse_script_markdown(text: str) -> ScriptDocument

audit_script_quality(
    script: ScriptDocument,
    outline: dict[str, object],
    source_truth: dict[str, object],
) -> list[ScriptQualityIssue]

script_retry_directive(
    issues: list[ScriptQualityIssue],
    previous_strategy: str = "",
) -> dict[str, object]
```

### 5.2 `cyberppt/commands/script_audit.py`

职责：

- 解析路径和命令参数。
- 读取脚本、Outline 与 Source Truth。
- 调用纯审计合同。
- 自动确定尝试编号。
- 写入最新报告、Markdown 视图与 attempts。
- 达到尝试上限时生成升级选项。
- 更新 artifact ledger。
- 返回标准退出码。

### 5.3 `cyberppt/cli.py`

职责：

- 注册 `script-audit`。
- 提供参数帮助和默认路径说明。
- 将命令分派到 `commands/script_audit.py`。

### 5.4 Skill 与 reference

- `SKILL.md` 只增加脚本审计入口、执行时点、阻断规则和确认门。
- `references/script-quality.md` 保存页面合同、审计规则、写稿协议、问题代码和重试策略。
- 不把完整规则重复写入多个文件。

## 6. 审计规则

### 6.1 页面合同

检查：

- 脚本页码按输入范围连续。
- 页面能够映射到 Outline。
- 章节页只保留“第X章：XXX”。
- 章节页不包含主判断、正文模块、方法或任务说明。
- 内容页具有标题、主判断、证据和视觉结构。
- 标题与主判断分离。
- 每个内容页只承载一个业务问题和一个视觉中心。

主要问题代码：

- `SCRIPT_PAGE_SEQUENCE_GAP`
- `SCRIPT_PAGE_NOT_IN_OUTLINE`
- `CHAPTER_PAGE_HAS_CONTENT`
- `CONTENT_PAGE_FIELDS_MISSING`
- `TITLE_MAIN_MESSAGE_COLLISION`
- `MULTIPLE_PAGE_MISSIONS`

### 6.2 来源与状态

检查：

- 内容页引用 Outline 中分配的 Source ID。
- 引用的 Source ID 能够在 Source Truth 中解析。
- 脚本不会将事实、建议、边界和待核内容混为确定事实。
- 保留“拟、建议、首期建议、待摸底、待基线、条件成熟后、暂缓、后续验证”等状态。
- 待核或边界记录不能成为无条件建设承诺。

主要问题代码：

- `SCRIPT_SOURCE_REF_MISSING`
- `SCRIPT_SOURCE_REF_UNKNOWN`
- `SOURCE_STATE_UPGRADED`
- `BOUNDARY_DROPPED`
- `UNRESOLVED_AS_CONFIRMED`

### 6.3 章内推进

检查：

- 页面顺序符合 Outline 的 `prerequisite_pages`。
- 页面内容符合 `argument_role`。
- `foundation` 页只陈述工作基础。
- `change` 页只说明环境和要求变化。
- `gap` 页说明现有方式与新要求之间的断点。
- `necessity` 页推导研究必要性，不提前展开首期范围和实施方案。
- `solution`、`scope`、`implementation`、`assurance`、`decision` 只在前置条件满足后出现。

主要问题代码：

- `SCRIPT_PREREQUISITE_ORDER`
- `SCRIPT_ROLE_CONTENT_CONFLICT`
- `PREMATURE_SCOPE_CLAIM`
- `PREMATURE_IMPLEMENTATION_CLAIM`
- `PREMATURE_DECISION_CLAIM`

### 6.4 跨页重复

检查：

- 相邻页面主判断高度相似。
- 同章页面大段上屏文字重复。
- 同一业务问题在多页重复完整展开。
- 后页可以回指前页，但不得复制前页完整论证。

首期采用确定性文本归一化与 n-gram/Jaccard 相似度，不引入外部模型。报告必须提供匹配文本证据，避免只输出相似度数字。

主要问题代码：

- `ADJACENT_MAIN_MESSAGE_DUPLICATE`
- `INTRA_CHAPTER_TEXT_DUPLICATE`
- `BUSINESS_QUESTION_REEXPANDED`

### 6.5 上屏结构与语义图同构

检查：

- 路径型视觉结构存在序号、箭头或明确顺序词。
- 闭环型视觉结构存在回流关系。
- 矩阵型视觉结构包含可识别的行列对象。
- 分层架构存在层级关系。
- 页面声明 N 类、N 项或 N 步时，上屏模块数量与 N 对齐。
- 视觉结构不得声称路径，而上屏模块仅为等权并列。

主要问题代码：

- `PATH_ORDER_SIGNAL_MISSING`
- `LOOP_RETURN_SIGNAL_MISSING`
- `MATRIX_AXES_MISSING`
- `LAYER_HIERARCHY_MISSING`
- `DECLARED_COUNT_MISMATCH`
- `SEMANTIC_DIAGRAM_MISMATCH`

### 6.6 页面密度与可读性

检查：

- 内容页不能只有标题和少量口号。
- 内容页一级模块默认 2—5 个。
- 超过 5 个模块时必须存在明确分组或层级。
- 章节页、封面、目录和封底使用模板页密度，不套用内容页下限。
- 单页包含多个互不依赖的主结论时，提示重新聚合或拆页。

密度阈值放在单一配置或 reference 中，不在多个模块重复定义。

主要问题代码：

- `CONTENT_PAGE_TOO_SPARSE`
- `CONTENT_PAGE_TOO_FRAGMENTED`
- `MODULE_HIERARCHY_MISSING`
- `MULTIPLE_INDEPENDENT_CONCLUSIONS`

## 7. 重试与升级

默认最多 3 次。每次保存输入指纹、问题列表、失败页面和本次策略。

重试方向按主要问题选择：

1. `mission_restructure`：页面使命、章内推进或结论提前失败。
2. `source_state_rebuild`：来源引用、状态升级或边界丢失失败。
3. `cross_page_dedup`：跨页重复失败。
4. `semantic_diagram_realign`：上屏结构与语义图不同构。
5. `density_recompose`：页面过稀、过碎或模块层级失败。

同一问题再次出现时，`retry_directive` 必须更换策略，不能只要求措辞修补。

达到上限后：

- 保留当前最佳脚本和全部 attempts。
- 输出仍未解决的问题与影响页面。
- 给出 2—3 个互斥决策选项，例如合并页面、调整大纲页面合同、保留当前结构并接受已记录风险。
- 不删除脚本，不直接放弃任务。

## 8. 流程接入

正式流程调整为：

```text
Source Truth 审计
→ Outline 论证链审计
→ 用户批准章节与逐页大纲
→ 编写批次或完整脚本
→ script-audit
→ 用户批准脚本
→ Stage 02 正文区 ImageGen full 图
→ 图片型 PPT 组装
→ 渲染 QA
```

门槛：

- `script-audit` 未通过时，不得将相应脚本标记为最终批准。
- `approve-script` 在本期保持兼容；后续可单独设计 SHA 绑定的审计前置检查，不在本期隐式改变其行为。
- 批次脚本可以独立审计；完整脚本形成后必须再运行一次全稿审计，以覆盖跨批次重复和章节衔接。

## 9. 错误处理

- 路径不存在、JSON 无法解析、脚本缺少任何页面：退出码 2，不计审计尝试。
- 页面只覆盖完整 Outline 的一部分：按批次范围审计，不把未出现页面报为缺失。
- 脚本页存在但 Outline 无对应页面：报 `SCRIPT_PAGE_NOT_IN_OUTLINE`。
- Source Truth 缺失但 Outline 为严格模式：输入错误并停止，避免降级为无来源审计。
- Markdown 个别后台字段缺失：形成页面级 issue；解析器仍尽量保留其他页面，避免一处错误阻断全部诊断。
- artifact ledger 更新失败：审计报告仍保留，但命令返回输入/落盘错误，提示恢复命令。

## 10. 测试设计

### 10.1 纯规则单元测试

- 正常批次脚本通过。
- 工作基础页出现“首期聚焦”“建设范围”等内容时失败。
- `necessity` 页提前展开投资和实施模式时失败。
- 状态从“首期建议”升级为“已经确定”时失败。
- 章节页出现正文模块时失败。
- 路径图没有顺序信号时失败。
- 矩阵图没有行列对象时失败。
- 声明“五类能力”但只有四个模块时失败。
- 相邻页面主判断和大段上屏文本重复时失败。
- 必要回指不被误判为完整重复。
- 批次范围不会要求未出现页面。

### 10.2 命令测试

- 默认路径解析。
- 自动尝试编号。
- 报告与 Markdown 生成。
- 退出码 0、2、4、5。
- 尝试上限和升级选项。
- artifact ledger 登记与 SHA-256。

### 10.3 真实项目回归

使用 `power-supply-demand-forecast-early-warning`：

- 已修订的 P01—P23 脚本能够完成审计。
- 构造旧版错误 P04，确认能够命中 `PREMATURE_SCOPE_CLAIM` 或 `SCRIPT_ROLE_CONTENT_CONFLICT`。
- P19 的场景矩阵能够识别行列与实际取舍，不因存在筛选条件而误判为方法论孤立页。
- P13 纯章节页通过。

## 11. 成功标准

1. 此前的工作基础页结论提前问题能够稳定复现并被阻断。
2. 当前电力供需项目 P01—P23 能生成结构化和可读审计报告。
3. 每个失败项明确到页面、问题证据和建议动作。
4. 失败后能够给出不同方向的重试策略。
5. 新功能不改变现有 Source Truth、Outline、Stage 02 和 PPT 生产命令行为。
6. 新规则有测试覆盖，Skill 入口和 reference 保持单一权威、避免重复。

