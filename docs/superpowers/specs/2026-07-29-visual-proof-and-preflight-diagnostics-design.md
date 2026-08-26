# 页面视觉证明与生图前诊断总研发方案

日期：2026-07-29
适用范围：CyberPPT Source Truth → Outline → 逐页设计脚本 → ImageGen handoff

## 1. 背景与目标

当前仓库已经建立从源材料到逐页脚本的完整链路，并通过 Source Truth、Outline、完整文字稿、上屏文字、视觉结构和脚本审计保证内容可追溯。本轮不另建一套页面模型，也不把评分公式、完整源文或长篇视觉理论写入每页生图提示。

本轮解决四个问题：

1. 页面关系枚举缺少“分层支撑”和“边界护栏”。
2. `visual_center` 说明看什么，但缺少一句明确说明“画面如何证明判断”。
3. 事实确定性、文字密度、双任务和主节点过多应在生图前诊断。
4. 每页 ImageGen 提示必须保持独立完整，同时只增加一行精简的视觉证明。

## 2. 设计原则

- 复用现有 Source Truth 的 `type`、`status`、`conditions`，不新增事实评分体系。
- `visual_proof` 首期为 Outline 内容页可选字段，存量 Outline 无需迁移。
- 显式页面值优先；缺失时由关系模板的 `visual_thesis` 稳定兜底。
- 诊断属于脚本审计层；ImageGen 编译器不得擅自改写事实、拆页或删减上屏文字。
- 除事实确定性明显越界外，新诊断首期以 warning 上线，经过项目回归后再评估升级。
- 最终提示不发送完整文字稿、证据映射、事实边界、评分过程和设计理论。

## 3. 数据流

```text
Source Truth
  type / status / conditions
        ↓
Outline 页面合同
  business_question / main_message / visual_center
  visual_proof? / visual_intent_type?
        ↓
逐页设计脚本与 contract receipt
        ↓
script-audit 生图前诊断
        ↓
content-first-v1
  页面任务 / 核心判断
  主导关系 / 视觉证明 / 空间组织 / 本页避免
  必须上屏文字 / 精简风格
```

## 4. 页面关系扩充

新增：

- `hierarchy_support`：上层结果依赖下层能力，贯穿能力作为底座或侧向支撑；不得退化为软件技术栈。
- `boundary_guardrail`：主体能力位于明确范围内，限制条件作为外围护栏；不得与主体模块同权并列。

选择顺序：

```text
页面 override
→ Outline visual_intent_type
→ 确定性信号分类
→ judgment_evidence 兜底
```

边界护栏信号优先于普通能力信号，避免“建设、平台、能力”等高频名词抢占分类。

## 5. visual_proof 合同

字段职责：

| 字段 | 含义 |
| --- | --- |
| `business_question` | 本页回答什么 |
| `main_message` | 观众形成什么判断 |
| `visual_center` | 第一眼看见什么 |
| `visual_proof` | 画面用什么关系证明判断 |
| `visual_intent_type` | 内部关系分类 |

优先级：

```text
page override.visual_proof
→ outline page.visual_proof
→ selected template.visual_thesis
```

首期不增加新的 Markdown 必填段。`visual_proof` 随 Outline 上下文和页面合同 receipt 传递；存量项目由模板兜底。

## 6. 生图前诊断

### 6.1 `FACT_CERTAINTY_LOST`

比较页面引用的 Source Truth 记录与主判断、上屏结论、上屏文字。对于 `proposed`、`conditional`、`unknown`、`pending` 等记录，如果可见主张删除“拟、建议、初步、待论证、可考虑、在……条件下”等限定，并使用“已确定、已批准、将建成、已实现”等确定性措辞，报错或警告。

投资、周期、正式立项、完整范围和最终技术路线越界为 error；一般限定弱化首期为 warning。

### 6.2 `ONSCREEN_LINE_TOO_LONG` / `ONSCREEN_TEXT_OVERLOADED`

复用现有 `onscreen_effective_char_target()`、模块解析和独立阅读规则。结论、模块标题或节点说明明显过长时报 warning；不复制一套固定字数理论。

### 6.3 `PAGE_DUAL_MISSION`

检查同页是否存在两个互不依赖的业务问题、两个同级主结论或两个面积相当的视觉中心。该诊断只要求回到 Outline 聚合/拆分或建立主从关系，不自动拆页。

### 6.4 `VISIBLE_NODE_OVERLOAD`

统计可见主模块、编号节点、表格主体项和显式数量。6–7 个未分组主节点 warning；8 个及以上未分组主节点 error。明确分组、条件矩阵或经批准的清单页可豁免。

## 7. 最终提示合同

```text
【页面逻辑｜不上屏】
主导关系：……
视觉证明：……
空间组织：……
本页避免：……

【锁定上屏文字】
正文结论与含数字的关键事实

【完整页面内容｜用于视觉叙事】
允许在语义完整前提下重组的页面内容
```

`visual_proof` 只出现一次。页面内容采用双层合同：锁定关键文字逐字准确，其余内容必须完整覆盖但允许重组、压缩并附着于业务场景。每页继续携带页面任务、核心判断、完整页面语义和精简风格，因此可以独立送入 ImageGen。

明确不发送：

- 完整内容语义和源页面全文；
- Source Truth 记录、证据编号和事实边界全文；
- 页面评分公式；
- 详细设计理论；
- 面积百分比、字体字号和后期制作规则。

## 8. 兼容与发布

1. 新字段全部可选，存量 Outline 和逐页脚本保持可解析。
2. 新关系只扩充分类结果，不修改现有关系语义。
3. 新诊断首期以 warning 为主，防止一次性阻断历史项目。
4. 事实明显越界保持 error。
5. 用 P09–P12 回归提示长度、关系分类、上屏文字完整性和视觉证明唯一性。

## 9. 验收标准

- `hierarchy_support` 与 `boundary_guardrail` 可由显式覆盖和确定性信号选择。
- Outline 显式 `visual_proof` 能进入页面提示；缺失时模板稳定兜底。
- 每页提示恰好出现一次“视觉证明”。
- 不重新注入完整文字稿、事实边界和证据编号。
- 四类诊断具有命中、不命中和兼容测试。
- P09–P12 必须上屏文字保持不变，单页提示只增加一行短视觉证明。
