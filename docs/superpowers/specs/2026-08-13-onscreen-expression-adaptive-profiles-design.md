# 上屏表达结构自适应档案设计

## 目标

让 Stage 02 明确消费 Stage 01 产生的十种 `onscreen_expression.form`，为视觉设计提供可复用的默认结构档案，同时允许基于页面使命、业务关系和整套节奏进行可审计的修改。

## 范围

本设计覆盖：

- 十种表达结构到默认结构档案的确定性映射；
- 视觉候选对默认档案的适配与偏离说明；
- 选中候选到可执行视觉规格的追溯；
- 跨输入、候选决策、视觉规格的确定性审计；
- 人读视觉结构稿中的候选取舍摘要。

不覆盖：

- 颜色、字体、形状、箭头外观、图片媒介或行业视觉风格；
- 直接生成图片、SVG、HTML、PPTX；
- 改写 Stage 01 锁定文字、事实、主体关系或页面顺序；
- 将十种表达结构变成固定版式模板。

## 当前事实

`cyberppt/onscreen_expression.py` 已定义十种表达结构，并在 `stage02_handoff.py` 中为内容页解析出 `onscreen_expression`。`visual-design-input.json` 已携带该字段，当前视觉设计任务要求记录阅读关系和均衡策略，审计也会检查该处置说明。

当前缺口是：表达结构只作为文字说明被消费，未形成候选的机器可验证约束，也没有进入最终 `deck-visual-spec.json` 的可追溯摘要。因此，审计无法判断候选及最终结构是否真的保持了因果、闭环、对照、分层或同层并列等表达关系。

## 设计原则

1. `onscreen_expression.form` 是表达约束，不是版式命令。
2. 默认档案提供候选起点；业务关系和页面使命优先于默认档案。
3. 任何偏离必须可解释，但偏离不等于失败。
4. 最终视觉规格必须保留其所消费的表达结构、已选候选和适配结论。
5. 同一种表达结构允许产生不同视觉意图、载体和空间组织；禁止仅因类型相同而套用同一模板。

## 默认结构档案

在 `cyberppt/onscreen_expression.py` 中，为现有 `ExpressionSpec` 增加中性结构约束。档案只声明关系、数量、阅读与均衡原则，不声明视觉实现。

| 表达结构 | 默认关系与最小约束 | 典型反模式 |
|---|---|---|
| `framework_4` | 4 个同层模块；同等可读性；无隐性主从 | 强制串成流程、一个中心吞没其余模块 |
| `key_points_3` | 3 个并列要点；共同服务页面判断 | 伪造因果或时间先后 |
| `flow_3_5` | 3–5 个动作节点；连续阅读方向 | 无顺序的等权罗列 |
| `operation_loop` | 3–5 个动作节点；至少一条可解释反馈/回流关系 | 直线流程、无回流边 |
| `architecture_layers` | 3–4 个层级；存在承载、接口或上下依赖 | 仅堆叠文字色块 |
| `pyramid_argument` | 3 个支撑命题共同收束到 1 个判断 | 三个结论并列、无收束 |
| `comparison_2col` | 两个对象；使用同一比较维度对应表达 | 两列各说各话 |
| `matrix_2x2` | 两个分类维度；四个位置均能说明归类依据 | 四张无坐标含义的卡片 |
| `causal_chain` | 3–4 个因果节点；方向可识别 | 同层罗列、无因果边 |
| `actions_3` | 3 项动宾举措；共同指向同一目标或结果 | 仅列名词、无行动对象 |

## 数据合同

### 表达约束

`ExpressionSpec` 增加 `constraints()`，输出稳定、可 JSON 序列化的对象：

```json
{
  "form": "causal_chain",
  "node_range": [3, 4],
  "relation_pattern": "directed_cause_to_effect",
  "reading_requirement": "directed",
  "balance_requirement": "each cause is attached to its consequence",
  "anti_patterns": ["unordered_peer_groups", "self_loop"]
}
```

`stage02_handoff.json` 与 `visual-design-input.json` 保留既有 `onscreen_expression` 决策，并新增派生字段 `expression_constraints`。该字段不能由视觉阶段重写。

### 候选适配

每个 `visual-design-decisions.json` 的候选新增 `expression_fit`：

```json
{
  "form": "causal_chain",
  "constraint_status": "default_profile" ,
  "satisfied_constraints": ["directed_cause_to_effect", "3_to_4_nodes"],
  "reading_relation": "two drivers converge into a constraint and lead to the required response",
  "balance_strategy": "parallel drivers have equal visual weight before convergence",
  "changed_constraints": [],
  "deviation_reason": ""
}
```

`constraint_status` 只能是 `default_profile` 或 `adapted`。当为 `adapted` 时，`changed_constraints` 必须非空，`deviation_reason` 必须说明：偏离的默认约束、业务原因，以及保留的表达核心。当为 `default_profile` 时，两个偏离字段必须为空。

### 可执行视觉规格

`deck-visual-spec.json` 每页新增 `expression_contract`：

```json
{
  "form": "causal_chain",
  "constraints_sha256": "...",
  "selected_candidate_id": "candidate-b",
  "fit_status": "adapted",
  "reading_relation": "...",
  "balance_strategy": "...",
  "deviation_reason": "..."
}
```

`constraints_sha256` 对规范化的 `expression_constraints` 哈希，保证最终 spec 可回溯到当前输入约束。

## 候选与选择规则

1. 每页仍须至少产生三个结构上不同的候选。
2. 每个候选必须覆盖全部证据单元和锁定文字 ID，并拥有 `expression_fit`。
3. 三个候选可以全部使用默认档案，也可以部分偏离；它们必须在语义焦点、空间语法或阅读序列上产生实质差异。
4. 候选不能仅改写视觉意图名称或媒介名称以满足差异要求。
5. 所选候选必须是有效评分最高者；若并列，必须用确定性的候选 ID 排序选择，或在决策包中声明可审计的并列裁决理由。

## 审计规则

`audit_visual_design_package` 新增以下阻断检查：

- 输入 `expression_constraints` 与 `onscreen_expression.form` 不匹配；
- 候选缺少 `expression_fit`、类型不一致或默认/偏离字段矛盾；
- 偏离未声明改动项或未说明业务理由；
- 候选的节点数、阅读序列、关系模式与表达约束不一致；
- `operation_loop` 无反馈边；`comparison_2col` 缺少成对维度；`matrix_2x2` 缺少两维分类；`pyramid_argument` 无收束判断；`causal_chain` 含自指向主边或缺少有向因果链；
- 编译 spec 缺少或漂移 `expression_contract`；
- spec 的所选候选 ID、约束哈希、阅读关系、均衡策略或偏离理由与 decision receipt 不一致。

审计不检查颜色、箭头外观、形状、卡片数量、左右位置或具体媒介。

## 人读审阅稿

`script-visual-structure.md` 每页新增“上屏表达结构与候选取舍”小节，仅展示：

- 表达结构及其核心约束；
- 候选 A/B/C 的语义焦点、空间语法、阅读关系、适配状态和总分；
- 已选候选与偏离理由；
- 最终执行结构摘要。

不得把候选的内部 ID、提示词字段名或实现指令写入最终生图文字。

## 测试与验收

1. 十种 form 都有稳定的默认约束快照测试。
2. 每种 form 至少有一份通过的 decision/spec fixture。
3. 每种关键反模式至少有一份失败 fixture；十类可分批测试，但总覆盖必须完整。
4. 测试默认适配、有效偏离、无理由偏离、偏离字段矛盾、spec 漂移和表达约束哈希漂移。
5. 测试同一 form 可形成不同视觉意图和空间语法，证明没有引入模板路由。
6. 运行 `PYTHONPATH=. pytest -q tests/test_onscreen_expression.py tests/test_visual_structure_contract.py tests/test_visual_structure_stage.py`；随后运行与变更相关的完整仓库测试。

## 兼容性与迁移

该合同适用于新生成的 Stage 02 handoff/视觉决策包。历史 `visual-design-decisions.v1` 不具备候选与约束证据，应明确判为 `legacy_non_governed`，不得作为当前生产前门禁的通过依据。历史项目需从当前 Stage 01 权威脚本重新生成 handoff 与视觉设计包。

