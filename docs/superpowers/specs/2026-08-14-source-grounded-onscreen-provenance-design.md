# 来源事实优先的上屏表达归属设计

## 背景与问题

当前页面脚本审计已经能检查表达模型的槽位是否在可见文字中有覆盖，但覆盖单位仍是整页文字和聚合后的 `content_units`。因此，`ST0008` 的“分散资源尚未形成稳定的行业服务供给”可以和 `ST0009` 的“形成可管理、可交付、可计量的数据服务和场景服务”被编辑成一条“尚未形成稳定的数据服务和场景服务供给”。

这条话表面上含有来源词，实质却将回应事实倒灌为缺口事实：它不是任一 Source Truth 的直接表述，也未声明为作者综合。现有 `_model_slot_coverage_issues()` 只要发现页面可见层与某个合并内容单元存在词面或语义重叠，就将该单元的全部来源标为已覆盖；无法判断每个可见模块实际承担的是哪条事实、哪个模型槽位。

本设计只处理 Stage 01 正式 Outline、页面脚本生成和页面脚本审计。它不重跑源登记、语义理解或 Source Truth，不改变 Source Truth 作为事实权威的职责，也不进入 Stage 02。

## 目标

1. 可见模块必须以 Source Truth 的直接事实为起点，保留原始事实的对象、动作、状态和关系方向。
2. 多条事实的综合只能在 Outline 中显式声明，并说明综合关系、参与事实和允许的可见表达；未声明的跨事实拼接应被阻断。
3. 表达模型槽位只能消费其 `source_mapping` 中的事实；一个模块跨槽位时须作为显式的关系模块，而不能将一个槽位的结果改写成另一个槽位的状态或对象。
4. 作者仍可做自然的短语化压缩；规则禁止的是未申明的事实混写，不是逐字复制原文。
5. JSON 与权威 Markdown 页面稿同时呈现同一套不上屏归属信息，避免人工转换造成漂移。

## 非目标

- 不要求所有上屏行逐字对应一条 Source Truth。
- 不以关键词黑名单判断事实归属。
- 不允许审计器自动猜测或补写 `synthesis`。
- 不对既有页面批量重写；只在重新编写或局部审计的页面应用新契约。

## 术语与数据契约

在每个内容页的 `content_units` 内新增可选但受 `source_grounding_mode=required` 约束的 `onscreen_modules`。每一项代表一个读者可见的顶层模块或其完整业务明细组：

```json
{
  "module_id": "p04-M03",
  "display_title": "服务供给断点",
  "source_refs": ["ST0008"],
  "model_slots": ["complication"],
  "derivation_mode": "direct",
  "allowed_visible_claim": "分散资源尚未形成稳定的行业服务供给",
  "required_characteristics": [
    "目录标识、数据口径、接口方式和授权条件不统一",
    "资源说明、质量标准、版本管理和服务责任尚未形成统一规范",
    "跨主体信任机制仍需完善",
    "供需对接、产品封装、授权执行、服务计量和价值结算尚未形成完整机制"
  ]
}
```

`derivation_mode` 只有三种：

| 模式 | 可引用来源 | 允许表达 | 禁止表达 |
|---|---|---|---|
| `direct` | 仅一条 Source Truth | 忠实压缩该事实 | 混入其他事实的结果、对象或状态 |
| `synthesis` | 两条及以上 Source Truth | 在 `relation` 和 `allowed_visible_claim` 中预先说明的等强度综合 | 将一个事实的状态改写为另一个事实的对象或结果 |
| `relation` | 两个及以上表达模型槽位 | 明示“需求—缺口—回应”等阅读关系 | 伪装成任一槽位的来源事实 |

`synthesis` 和 `relation` 必须同时给出：`source_refs`、`model_slots`、`relation`、`allowed_visible_claim`、`synthesis_rationale`。`direct` 不得引用多条 Source Truth，也不得跨模型槽位。

## 编译与 Markdown 生成

### Outline 内容单元生成

`refresh-outline-content-units` 在生成或刷新目标页时，按 Source Truth 记录边界生成 `onscreen_modules`：

- 每条 `direct` 模块只绑定一条来源记录及其实际模型槽位；
- 原始记录含多个并列断点时，可在同一直接模块下保留同一记录的多个明细；
- 不将来源记录 A 的对象与来源记录 B 的结果合并为新的状态句；
- 仅当语义关系模型已经声明跨记录关系，才生成候选 `relation` 模块，并将其标为作者待确认，不自动选择。

### 页面脚本编译

`compile-page-script-authoring` 在每页 Markdown 的“表达模型（不上屏）”之后写入：

```markdown
### 上屏来源归属（不上屏）

- M03｜服务供给断点｜direct｜complication｜ST0008
  - 允许命题：分散资源尚未形成稳定的行业服务供给
  - 必留特征：资源发现、组合使用、跨主体信任、服务运营机制
```

此段不进入 `上屏文字（严格锁定）`，但为作者、审计与人工复核提供同一份事实归属。

## 审计规则

### 1. Outline 审计

新增 `SOURCE_GROUNDING_MODULE_INVALID`：

- `direct` 引用多条来源，或多个模型槽位；
- `synthesis/relation` 缺少关系说明、允许命题或综合理由；
- 模块来源不属于当前页 `source_refs`；
- 模块槽位不属于该页表达模型 `source_mapping`；
- `direct` 模块的允许命题与唯一来源记录没有足够的来源特征重叠。

### 2. 页面脚本审计

将当前“整页可见文字覆盖一个聚合内容单元”的豁免替换为逐模块审计：

- `direct` 模块必须在对应可见模块内覆盖 `allowed_visible_claim` 或其自然压缩，并保留至少一个 `required_characteristics`；
- `synthesis` 模块必须匹配登记的 `allowed_visible_claim`，并分别覆盖参与来源的必要特征；
- `relation` 模块只校验已声明的关系词与参与槽位，不能作为任何一条直接事实的覆盖证据；
- 未能归属至任何登记模块的可见业务命题报 `ONSCREEN_FACT_PROVENANCE_MISSING`；
- 将两个或以上槽位的事实写成单一 `direct` 命题，或把回应槽位的结果置入缺口槽位，报 `ONSCREEN_CROSS_SLOT_FACT_MIXING`。

错误信息必须给出：可见模块、实际命中的来源或槽位、期望来源或槽位，以及“拆回直接事实 / 登记 synthesis / 改为 relation”的修复路径。

### 3. 兼容策略

缺少 `onscreen_modules` 的旧 Outline 仍沿用当前内容单元审计，不产生新阻断；新生成或作者确认后设置 `source_grounding_mode=required` 的 Outline 必须满足新契约。这样不以新规则篡改既有人工页面，也保证当前项目后续页面能采用更严格的来源归属。

## P04 验收样例

P04 的“服务供给断点”应为一个绑定 `ST0008`、`complication` 的 `direct` 模块：

```text
服务供给断点
  供给状态：分散资源尚未形成稳定的行业服务供给
  资源发现：目录标识、数据口径、接口方式和授权条件不统一
  组合使用：资源说明、质量标准、版本管理和服务责任尚未形成统一规范
  可信协同：跨主体信任机制仍需完善
  服务运营：供需对接、产品封装、授权执行、服务计量和价值结算尚未形成完整机制
```

下列句子必须被 `ONSCREEN_CROSS_SLOT_FACT_MIXING` 阻断：

```text
分散的数据、知识、模型和专业能力尚未形成稳定的数据服务和场景服务供给
```

它将 `ST0009` 的回应对象与结果提前放入 `ST0008` 的缺口状态，且未登记为可审阅的综合关系。

## 实施范围与测试

- `cyberppt/stage01_compiler.py`：生成按来源记录切分的上屏归属候选。
- `cyberppt/commands/compile_page_script_authoring.py`：将归属信息写入权威 Markdown。
- `cyberppt/outline_audit_semantics.py`：验证归属契约与表达模型映射。
- `cyberppt/script_quality_contract.py`：以逐模块来源归属取代聚合单元的可见覆盖豁免。
- 对应测试：编译、Outline 审计、Markdown 输出、直接压缩放行、未声明跨槽位混写阻断、已声明 synthesis/relation 放行、旧 Outline 兼容。

## 验收标准

1. P04 的原文直接断点模块通过，且每一条关键特征可追溯到 `ST0008`。
2. 同页“稳定的数据服务和场景服务供给”作为缺口事实被拒绝，除非作者显式登记综合关系；即使登记，也不得把回应结果伪装为缺口状态。
3. 已登记、关系正确且来源特征完整的 `synthesis/relation` 模块通过。
4. 当前项目不重跑上游阶段；局部刷新 Outline、重编目标页 Markdown并运行 `outline-audit` 与 `script-audit` 即可验证。
5. 现有不带新归属字段的项目继续通过其既有审计路径。
