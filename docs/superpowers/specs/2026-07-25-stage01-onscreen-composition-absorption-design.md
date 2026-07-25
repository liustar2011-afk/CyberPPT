# Stage 01 上屏构图规则吸收方案

日期：2026-07-25  
状态：**已决议（用户确认 2026-07-25）**  
适用范围：CyberPPT Stage 01 内容页上屏文字与视觉结构；`script-audit`  
关联：`references/script-quality.md`、`cyberppt/script_quality_contract.py`、`scripts/dual_image_overlay/imagegen_handoff.py`  
来源参考（只吸收规则与可移植检查逻辑，不作为独立 Skill）：`vendor/ppt-script-visual-redesign`

---

## 1. 定位与判断

### 1.1 问题

本仓 Stage 01 已有较强的内容保真链（完整文字稿 → 上屏派生 → 证据映射），但上屏侧构图约束偏薄：`视觉结构` 常退化为一句图型标签，上屏易落成等权模块/卡片墙，与「上屏与语义图同构」目标不完全匹配。

`vendor/ppt-script-visual-redesign` 提供了有用的构图纪律（原语、一页一中心、反通用 AI 版式、空间关系语言），但其形态是独立 Codex Skill + 另一套 13 节脚本合同 + 下游「视觉重构」输出。

### 1.2 决议方向

**吸收其规则与可自动化检查逻辑进 Stage 01；不做独立 Skill；不新增 Stage 02 视觉层二次写作。**

理由：

1. 该 Skill 本质是「规则合同 + 文本模型写稿」，不是视觉模型排版；再开一轮视觉层等于对上屏做第二次同质工作。  
2. 本仓权威与门禁已在 Stage 01；构图纪律应在写上屏时一次到位，并由 `script-audit` 守门。  
3. 独立 Skill / 整包 validate 会引入第二套 Markdown 合同，与 `script_quality_contract` 冲突。

权威链保持不变：

```text
Source Truth → Outline → 完整文字稿 → 上屏文字 → 视觉结构（收紧）
                              ↓
                         script-audit
                              ↓
              imagegen_handoff（主判断 + 上屏 + 视觉结构 + 边界）
```

---

## 2. 目标与非目标

### 2.1 目标

1. 把「内容驱动构图」写进 `script-quality.md`，约束上屏模块划分与 `视觉结构` 写法。  
2. 引入受控**构图原语**词汇（写在 `视觉结构` 内，不强制新字段）。  
3. 将可机器检查的反模式与同构信号并入 `script_quality_contract.py` / `script-audit`。  
4. 从 vendor 包**摘逻辑进本仓代码与 reference**，安装/调用路径仍是本仓库 `cyber-ppt` Skill。  
5. 送图编译路径保持 `imagegen_handoff`；不新增批准门。

### 2.2 非目标（本期明确不做）

- 不安装、不维护独立 `$ppt-script-visual-redesign` 为生产入口。  
- 不新增 Stage 02 `onscreen_visual_layer` 工件与二次确认。  
- 不把 vendor 的 13 节合同、ASCII 草图必填、1280×720 坐标、`Codex生图执行摘要` 写入 Stage 01 脚本。  
- 不新增内容页必填字段「视觉主张 / 构图原语 / 上屏禁止事项」（避免存量大面积补字段）；其语义并入写作规则与 `视觉结构` 句式。  
- 不削弱完整文字稿权威，不把 vendor「终稿文字」概念替换文字稿/上屏二分。  
- 不用 vendor `validate_script.py` 替换 `script-audit`。  
- 不在本期引入视觉模型看图评版式。

---

## 3. 吸收清单（从 vendor 到本仓）

### 3.1 吸收进写作规则（`references/script-quality.md`）

| 来源概念 | 本仓落点 |
|---|---|
| 先页面使命/核心结论再构图 | 已有「一页一业务问题 + 视觉中心」；补充：上屏模块划分必须服务主判断与 `visual_center`，不得从「有 N 项」反推 N 张同权卡 |
| 一页一个视觉中心 | 写入上屏规则；次要信息必须是支撑，不得与核心同权 |
| 构图原语（非模板库） | 给出受控原语表；`视觉结构` 必须点名主原语 |
| 反通用 AI 版式 | 默认禁止：等宽卡片墙、六宫格、Bento 泛用、中心圆+周边图标、网页后台/数据大屏腔、紫蓝霓虹装饰话术 |
| 空间关系承载业务含义 | `视觉结构` 须含中心或主链方向或区域关系词，禁止空壳「××图」 |
| 上屏与关系同构 | 延续并收紧现有路径/矩阵/分层/闭环信号检查 |

### 3.2 构图原语枚举（初版）

写在 `视觉结构` 中，允许「主+辅」：

`贯穿主链` · `双侧协同` · `受控边界` · `分层剖面` · `汇聚引擎输出` · `判断证据支撑` · `非对称对照` · `机制作用范围` · `主体泳道` · `阶段推进` · `矩阵筛选` · `闭环回流`

### 3.3 `视觉结构` 句式合同（收紧，不加字段）

内容页 `视觉结构` 建议一句话，且同时满足：

1. **原语**：含上表主原语之一（或明确同义且可映射到枚举）；  
2. **中心或主链**：点明视觉中心或主链方向（如由左向右 / 自下而上 / 判断在上证据托举）；  
3. **与上屏一致**：不引入上屏未出现的一级模块名。

示例（合格）：

> 贯穿主链——沿「①数据治理 → ②模型生产 → ③报告发布 → ④跨主体协同」由左向右标断点；视觉中心在断点传导段。

示例（不合格）：

> 业务架构图。  
> 简洁现代的科技风信息图。

### 3.4 吸收进代码（本仓实现，不依赖 vendor 运行时）

从 `vendor/ppt-script-visual-redesign/scripts/validate_script.py` **移植思路与词表**，改写为 `script_quality_contract` 风格的 issue：

| 检查意向 | 建议 code | 初版级别 |
|---|---|---|
| `视觉结构` 过短或无空间/原语信号 | `VISUAL_STRUCTURE_TOO_THIN` | warning → 稳定后可升 error |
| `视觉结构` 仅风格词、无结构 | `VISUAL_STRUCTURE_STYLE_ONLY` | error |
| 上屏模块 >5 且无分组/层级/阶段信号 | 已有 `MODULE_HIERARCHY_MISSING` | 保持；补充反「纯并列卡片」文案 |
| 选路径/阶段类表达但无序信号 | 已有 `PATH_ORDER_SIGNAL_MISSING` 等 | 保持并与原语表对齐 |
| 上屏或视觉结构出现高风险版式词且无「禁止/不得」语境 | `ONSCREEN_ANTI_PATTERN` | warning |
| `视觉结构` 主原语与上屏信号明显冲突（如写矩阵筛选但无表/行列信号） | `PRIMITIVE_ONSCREEN_MISMATCH` | warning |

**不移植**：页级 13 节齐全性、星号列表禁令（本仓上屏允许既有 Markdown 约定）、`overlay` 字段检查（主线已禁止 overlay，不在脚本合同重复）、Codex 摘要长度检查。

### 3.5 可选短 reference

新增 `references/onscreen-composition.md`（一页纸）：原语表、合格/不合格 `视觉结构` 示例、反模式列表。  
`script-quality.md` 链到该文件；Stage 01 Reference Gate 在进入逐页脚本时将其列为上屏相关必读（或并入 `script-quality.md` 而不单列——实现时二选一，优先单文件免增 gate 负担）。

**实现偏好**：优先把精华直接写入 `script-quality.md`「上屏结构与语义图同构」一节扩写；仅当篇幅过长再拆文件。

---

## 4. 保真规则：明确边界

Vendor 几乎不增强证据保真。本期**不借 vendor 改保真**；保真继续以现有为准：

- 完整文字稿权威与派生关系  
- 证据映射 / Source ID  
- 状态不升级、边界旁白不上屏  
- `CONTENT_PROSE_*` / `PROSE_SOURCE_COVERAGE_GAP` 等既有审计  

本期只加强：**上屏如何图形化表达已审定内容**，不新增第二条内容源头。

---

## 5. Stage 02 与送图

- `imagegen_handoff` 输入集合不变：主判断、上屏、视觉结构、清洗后边界。  
- 收益来自 Stage 01 写出的更可执行 `视觉结构` + 更同构的上屏，而非新编译字段。  
- 8 种风格锁定顺序不变；无额外视觉层步骤。

---

## 6. 存量兼容与推行

1. **审计级别**：新检查默认 `warning` 一个迭代；fixtures/绿项目无回归后，将 `VISUAL_STRUCTURE_STYLE_ONLY` 与过薄结构升为 `error`。  
2. **存量稿**：不强制一次性补写；再跑 `script-audit` 时按页提示收紧 `视觉结构`。  
3. **vendor 目录**：可保留作设计来源与词表对照；`SKILL.md` / README 注明「非生产入口，规则已吸收至 `script-quality` + `script-audit`」。  
4. **禁止**：文档中引导用户 `$ppt-script-visual-redesign` 替代本仓脚本流程（与现有「不得调用旧 ppt-script」一致）。

---

## 7. 实现切片（供后续 plan）

1. 扩写 `references/script-quality.md`（上屏构图纪律 + `视觉结构` 句式 + 原语表 + 反模式）。  
2. 更新 `SKILL.md` 中 Stage 01 / 上屏相关摘要句（指向 script-quality，不引入独立 Skill）。  
3. 扩展 `script_quality_contract.py`：词表、检测函数、issue code；`script_retry_directive` 将新码归入 `semantic_diagram_realign`。  
4. 补测试：`tests/test_script_quality_contract.py` / fixtures。  
5. 在 `vendor/ppt-script-visual-redesign/README.md` 顶部加「已吸收声明」短注（可选）。  
6. **不改** `imagegen_handoff` 字段集，除非后续证明必须把反模式禁止项从视觉结构解析进「禁止项」（本期不做）。

---

## 8. 成功标准

1. 内容页脚本在审计中能拦截「空壳视觉结构 / 纯风格词 / 明显卡片墙话术」。  
2. 写上屏时有可执行的原语与同构规则，无需第二轮视觉重构稿。  
3. 完整文字稿与证据保真合同零回退。  
4. 生产路径仍是单一 `cyber-ppt` Skill + `python -m cyberppt script-audit`。

---

## 9. 待用户确认

请确认以下决议后，本文件状态改为「已决议」，再进入实现 plan：

1. **吸收位置**：仅 Stage 01 规则 + `script-audit` 代码。  
2. **不做成独立 Skill / 不做 Stage 02 视觉层。**  
3. **不加三个新必填字段**；收紧 `视觉结构` + 上屏写作规则。  
4. **新检查先 warning 后升 error。**  
5. **vendor 仅作来源保留，非生产入口。**
