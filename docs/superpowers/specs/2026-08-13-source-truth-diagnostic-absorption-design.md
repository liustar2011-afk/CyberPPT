# Source Truth 非阻断诊断吸收设计

## 目标

在既有严格 Source Truth 与语义—证据交叉审计之后，提供更易定位和修复的质量提示；不改变任何 Stage 01 或 Stage 02 的通过条件、返回码、审批节点和权威输入。

## 范围

新增三类 `WARN` 诊断并将其汇总到既有审计报告：

1. 原子项拆分建议：复用既有 `SOURCE_RECORD_ATOMICITY_WARNING`，提示一条 Source Truth 记录的可追溯源单元和语义单元粒度不匹配，建议拆分为可独立保留的原子项。
2. 优先级叙事失衡建议：在同一可追溯业务关联内，提示 `premise`、`driver`、`consequence`、`gap` 等叙事骨架被赋为低优先级，而 `boundary`、`metadata` 或细节项取得更高优先级的情形。
3. 修复摘要：汇总未覆盖源单元、不可回查核心论点、建议拆分的原子项和建议复核的优先级关系数量，并列出有限条可定位 ID 与最小修复动作。

## 约束

- 只消费 `source-truth.json`、`semantic-argument-model.json` 和已存在的 `SU-*` 引用。
- 所有新增项均为 `WARN`；不得改变 `semantic-check`、`source-truth-audit` 的退出码和 passed/rewrite_required 语义。
- 不以文本长度、关键词、通用文本相似度或 Markdown 同步关系作为硬判断。
- 不自动改写 Source Truth、论点优先级或原子项；诊断只指出记录、源单元和建议动作。
- 不创建新的审批、状态、attempt、manifest 或绑定文件；报告继续是既有审计的派生产物。
- 报告摘要不复制源正文，只输出计数、记录 ID、`SU-*` ID、问题代码和修复策略。

## 设计

在 `source_truth_contract.py` 中将新增诊断保持为纯函数，输入为已加载的 Source Truth 记录与可选的语义模型索引，输出 `SourceTruthIssue` 风格的提示对象。现有阻断 `audit_source_truth()` 保持原输出；新入口单独收集建议项，使调用方可以把它们写入报告而不混入阻断问题。

原子项诊断复用现有 `semantic_units` 与 `source_unit_refs` 的结构化粒度信息；`SOURCE_RECORD_MIXED_CLAIMS` 仍是既有阻断错误，不重复生成为警告。规则不从中文句式猜测事实。

优先级诊断按共享 `semantic_node_ids`、`source_unit_refs`、actors 或业务对象交集建立候选关联。只有骨架职责为较低优先级、关联的边界/元数据或细节职责为更高优先级时才提示。候选关系不充分时跳过，避免用词面相似度制造噪声。

`source_truth_audit.py` 汇总阻断问题、既有原子性警告、语义—证据交叉审计与优先级建议项，但仅由阻断问题决定状态和返回码。JSON 报告增加“修复摘要”与“非阻断建议”字段。

公开报告字段如下；其中只允许记录 ID、问题码和计数，不得包含源材料正文：

```json
{
  "warning_count": 2,
  "warnings": [
    {
      "code": "SOURCE_RECORD_ATOMICITY_WARNING",
      "source_ids": ["S001"]
    }
  ],
  "repair_summary": {
    "uncovered_source_units": 0,
    "unresolved_core_claims": 0,
    "atomic_split_suggestions": 1,
    "priority_review_suggestions": 1
  }
}
```

## 验收

1. 既有合法/非法测试夹具的硬问题集合、审计状态和退出码不变。
2. 原子性粒度不匹配的 Source Truth 记录会产生包含记录 ID、`SU-*` 引用和 `split_semantic_units` 的 `WARN`。
3. 可证明关联的骨架项被低优先级、边界项被高优先级时产生 `WARN`；缺少关联证据时不提示。
4. 报告包含四项固定计数与有限条 ID，不包含源正文。
5. 新增诊断不会写入 Source Truth、语义模型或任何新控制文件。
