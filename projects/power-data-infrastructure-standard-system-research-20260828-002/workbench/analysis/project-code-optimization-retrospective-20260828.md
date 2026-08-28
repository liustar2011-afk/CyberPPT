# 项目代码优化复盘

## 一、技术判断

**Verdict：SUPPORT WITH CONDITIONS**

本项目确实暴露出需要从代码层修复的问题。最高优先级集中在 Stage 01 最终脚本向 Stage 02 交接时的权威绑定、新鲜度校验和跨机器可迁移性。P04 信息密度问题已经在当前代码中完成修复，相关能力无需重复开发。

本次仅完成诊断和建议排序，未修改仓库代码、业务脚本或 Stage 02 生产产物。

## 二、项目当前状态

| 环节 | 已验证状态 | 证据与说明 |
|---|---|---|
| Source Foundation | 通过 | `semantic-report.json` 为 `ok`，保留 1 项歧义、1 项推断关系和 3 项论证诊断警告 |
| Stage 01 Plan/AUTHOR | 通过 | 当前 `audit-final` 通过，`final-script.json` 与 `final-script.md` 同步 |
| Stage 01 Lint | 通过并有 2 条警告 | P10、P23 的“七大类”被计数规则解释为七个上屏模块，属于高概率误报 |
| Stage 02 handoff | 当前环境失败 | 持久化回执显示 Windows 环境曾通过；当前 Mac 重新审计触发 `HANDOFF_BINDING_MISSING` |
| 视觉结构 | 仅完成准备 | 已有 design input、skill request、invocation；缺少 visual decisions、执行回执、视觉规格和视觉审计结果 |
| 图片与 PPTX 生产 | 未发现产物 | 缺少风格锁、生产 manifest、逐页图片、图片文字审计、PPTX、OfficeCLI 渲染和交付 QA |

Stage 02 可能由操作者主动停在视觉结构准备节点。现有产物无法证明后续生产曾经启动，因此“不完整”属于已验证事实，“为什么停止”仍属未知。

## 三、关键发现

### 1. Stage 01 权威稿与 Stage 02 绑定副本发生语义漂移

- Stage 01 当前权威稿：`script/dist/final-script.md`
  - 文件 SHA-256：`62ea0987054b1632bd23357cd4a0dc03df03401fad71b4a225c9b020021fac24`
  - 语义 SHA-256：`3e7e52bc19e8c16b4180624b55706182417d377c5b92276db12478637bf40b0a`
- Stage 02 绑定副本：`workbench/scripts/final/script-final.md`
  - 文件 SHA-256：`0df8d20b0523770c0ff9fbed0e964a26ae0a49b8bb71622fca4b58fe78d1a669`
  - 语义 SHA-256：`50c30fb14f32ffc9e16c16a07ca7e66b3feaecff16b330619593985bba015324`

两份稿件存在 14 行新增、6 行删除。差异集中在 P04：当前权威稿已经补齐国家建设部署、制度与流通依据、先行先试项目依托三个模块；Stage 02 副本仍保留旧版单模块稿。

代码在 handoff 建立时把传入脚本复制到 `workbench/scripts/final/script-final.md`，随后只绑定并审计该副本。`external_path` 只承担来源记录职责。内存反例显示：当副本哈希仍匹配、上游权威稿已经改变时，`audit_stage02_handoff` 仍返回 `passed`。

这会让 Stage 02 在旧脚本上继续生产，并且现有新鲜度门禁无法发现。

### 2. 绝对路径绑定使项目无法跨机器续跑

handoff、视觉请求和部分 Source Foundation 报告内共保留 19 个 Windows 绝对路径。当前 handoff 的脚本绑定为：

`D:\CyberPPT\projects\power-data-infrastructure-standard-system-research-20260828-002\workbench\scripts\final\script-final.md`

项目复制到 `/Volumes/DOC/CyberPPT` 后，审计器直接对该字符串执行 `Path(...).resolve()`，最终在当前仓库下形成一个包含盘符文本的无效路径并触发 `HANDOFF_BINDING_MISSING`。内存反例还确认，当前审计器无法直接消费项目相对路径。

哈希绑定本身应保留；路径表示需要支持 project-relative locator，并将外部绝对路径降为非门禁的 provenance。

### 3. P04 原始缺陷已修复，但语义单元门禁仍可被整体省略

当前代码已经具备：

- `SOURCE_CONSUMPTION_UNIT_MISSING`
- `FULL_COPY_SEMANTIC_UNIT_GAP`
- `ONSCREEN_SOURCE_DETAIL_INSUFFICIENT`
- `FULL_COPY_DUPLICATION`

P04 已按 14 个语义单元补齐消费合同并重写，相关 100 个定向测试全部通过。

剩余风险位于兼容分支：`source_consumption.unit_dispositions` 整体缺失时，严格页面仍会直接跳过语义单元级检查。当前实现只在作者主动声明该数组后才实现完整门禁。新建 required-policy 项目仍可能复现“一个记录级锚点代表整条多事实记录”的问题。

### 4. 项目状态缺少跨阶段统一计算

`manifest.yml` 初始化后永久保留 `status.stage: initialized`。`cyberppt-script status` 会动态计算 Stage 01，并正确显示“最终脚本已生成”，但它不读取 Stage 02 handoff、视觉结构、风格锁、production manifest 和交付 QA。

当前项目因此同时存在三种状态叙述：

- manifest：initialized
- Script Engine：最终脚本已生成
- Stage 02 实际门禁：handoff 失效，视觉结构未完成

建议提供一个只读、实时计算的项目级状态视图，直接复用现有权威产物和审计函数，不新增状态文件。

### 5. 上屏计数规则产生可预测误报

`check_declared_count` 从标题或副标题提取单个中文数量词，然后与上屏模块数量比较。

- P10 的“七大类体系”表达研究产出的体系规模，页面展示两个方法模块。
- P23 的“七大类标准体系框架”表达结论对象，页面展示一个研究结论模块。

两页均没有声称屏幕上会列出七个并列模块。当前正则无法区分“对象固有数量”和“本页枚举数量”，因此持续产生低价值警告。

### 6. `stage02-handoff-check` 具有未显式提示的写入副作用

该命令会把重新计算的结果写回 `stage02-handoff-audit.json`。正式流水线需要持久化审计回执，这一能力有合理用途；只读诊断也需要安全入口。建议增加 `--no-write`，默认行为可保持兼容，帮助复盘、CI 预检和跨环境检查避免改变项目产物。

## 四、代码优化优先级

### P0：统一 Stage 01 → Stage 02 脚本权威与新鲜度

建议：

1. 项目内部 `script/dist/final-script.md` 直接作为正式项目脚本绑定，不再按 external script 复制后脱离上游权威。
2. 真正位于项目外部的脚本继续落项目副本，handoff 同时记录：副本 locator/hash、来源 locator/hash、来源可用性策略。
3. 来源存在时，预检同时比较来源与副本；来源语义摘要变化时阻断并要求重新 prepare handoff。
4. 来源暂时不可用时，仅在旧 handoff 能证明副本来源与字节绑定一致的条件下继续复用。
5. `final-script-pages` 预检必须比较本次命令传入脚本、handoff 脚本和项目 Stage 01 权威稿的语义摘要。

验收反例：保持副本不变，只修改 `script/dist/final-script.md` 的 P04；handoff audit 或 production preflight 必须失败并报告上游脚本漂移。

### P0：引入可迁移的项目相对 locator

建议使用结构化 locator，例如：

```json
{
  "scope": "project",
  "path": "workbench/scripts/final/script-final.md",
  "sha256": "...",
  "semantic_sha256": "..."
}
```

审计时先验证路径位于项目根目录内，再解析文件和哈希。外部来源使用 `scope: external`，绝对路径只保留来源线索。对 v1 绝对路径保留兼容读取，并提供重新 prepare 的迁移路径。

验收反例：在 Windows 生成 handoff，将完整项目复制到 macOS 临时目录；无需修改 JSON，handoff audit 仍应通过。修改任一绑定文件后必须失败。

### P1：required-policy 新项目强制语义单元 disposition

建议仅对新 schema 或新投影的 `source_consumption_policy: required` 内容页强制 `unit_dispositions`。历史项目通过显式兼容版本继续读取。

强制 disposition 不等于强制上屏或强制扩写。`reserved_for_later`、`trace_only`、`intentional_omission` 可继续表达合理取舍，并要求具体理由。

验收反例：删除严格页面的整个 `unit_dispositions` 字段，PLAN audit 必须失败；来源较薄页面只要完整声明其少量单元即可通过。

### P1：增加只读的全流程项目状态

建议新增顶层项目状态命令或扩展现有状态命令，按实时证据计算：

`Source Foundation → PLAN/AUTHOR → handoff → visual structure → style lock → production manifest → page checkpoints → assembly → OfficeCLI QA`

状态输出应优先展示首个阻断点，并列出已完成与尚未开始的阶段。`manifest.yml` 中静态 `status.stage` 建议删除或明确标注为初始化元数据，避免被误认为实时状态。

### P2：将数量检查改为显式合同驱动

建议以 `onscreen_contract.expected_peer_count` 或同类显式字段作为检查依据。标题中出现“七大类”等数量词时，只有 PLAN 声明该数量对应本页可见并列集合，才与模块或条目数量比较。纯正则推断可降级为低置信提示或移除。

### P2：为审计命令增加只读模式

为 `stage02-handoff-check` 增加 `--no-write` 或 `--output -`。正式 gate 保持持久化回执，诊断模式只输出 stdout 和退出码。

## 五、无需重复开发的事项

以下 P04 根因已在当前提交 `c66c6f3` 中处理：

- 语义单元级来源消费合同
- AUTHOR 对完整稿语义单元缺失的检查
- 上屏来源细节不足检查
- 完整稿句子近重复检查
- P04 三模块重写及 137 字反例回归测试

本次复盘的后续开发重点应转向交接权威、跨机器恢复、门禁强制范围和状态可观察性。

## 六、验证记录

- `.venv/bin/python3` 已确认使用仓库虚拟环境，`rapidocr_onnxruntime`、`jsonschema` 可导入。
- `audit-final`：passed，0 issue，0 warning。
- `lint`：passed，2 warnings；人工核对后判定为计数语义误报。
- `check-sync`：passed。
- `stage02-handoff-check`：failed，`HANDOFF_BINDING_MISSING`。
- `visual-structure-audit`：被失效 handoff 阻断。
- 定向测试：`100 passed in 0.18s`。
- 内存反例：绑定副本保持有效、Stage 01 权威稿发生语义漂移时，handoff audit 仍返回 passed。
- 本轮曾执行会回写审计回执的 check 命令；取证完成后已恢复原文件，工作区未留下该诊断副作用。

## 七、建议实施顺序

1. 先修 P0 脚本权威与项目相对 locator，并补跨平台迁移和上游漂移回归测试。
2. 再将语义单元 disposition 纳入新 required-policy 项目的强制门禁。
3. 增加全流程只读状态，统一展示真实阻断点。
4. 收敛计数误报并补充 check-only 模式。
