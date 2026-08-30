# CyberPPT 权威产物地图

本文件定义 CyberPPT 各阶段唯一可写权威及派生产物。发生冲突时，先按本文件判断“应修改谁”，再重新生成下游派生产物。

## 总原则

每一层只保留一个可写语义权威。Projection、audit、receipt、manifest、review 均不得反向覆盖其来源权威。

## Stage 00 / Source

### 权威

- 原始源文件。
- `workbench/stages/00-source/source-registry.json`、source units、heading tree 等确定性来源索引。

### 规则

来源索引保存原文、顺序、locator、稳定 ID 和哈希，不解释业务语义。

## Stage 01 / Strict semantic understanding

### 唯一可写语义权威

`semantic-argument-model.json`

它承载 whole-document 业务理解、document thesis、semantic nodes、argument relations、source coverage、状态、责任和 evidence references。

### 上游语义工作产物

当 strict source-foundation 路线使用 `business-semantic-understanding` 时，`normalized-facts.json`、`concept-base.json`、`relation-graph.json`、`argument-chain.json` 是该理解步骤的受控输入/工作产物；进入当前 strict 主流程后，应投影到 `semantic-argument-model.json`，不得与其并行作为下游可写语义源。

### 派生产物

- `source-truth.json`：由 semantic model + source units 确定性编译；不得人工修改后反向更新 semantic model。
- `semantic-report.json`、source-truth audit：验证回执，不是内容权威。
- 历史 `outline.json`：兼容投影，不是当前新项目权威。

## Stage 01 / PLAN-AUTHOR

### Foundation 权威

`script/foundation.json`

- strict profile：由已验证 `source-truth.json` 机械投影。
- script profile：由轻量 UNDERSTAND 直接写入。

进入 PLAN 后，下游只消费当前 Foundation，不重新建立第二套全文语义模型。

### Deck Plan 权威

`script/deck-plan.json`

只负责交流目标、章节、页序、页面问题/使命和来源范围。核心判断、完整论证、上屏结构和视觉关系由 AUTHOR 形成。

### Final Script 权威

`script/dist/final-script.md` 是 Stage 02 唯一跨阶段内容权威。若存在 JSON 镜像，JSON 只用于确定性审计和同步检查；修改最终内容后必须保持两者同步。

## Stage 02 / Visual production

### 内容权威

Stage 02 自有快照：`workbench/inputs/final-script.md`，绑定输入脚本 SHA-256。

### 视觉权威

每页通过文字审计和 deck rhythm QA 后的 `audited_full_image`。进入 editable reconstruction 后以 SHA-256 写入 `reconstruction_visual_source`；下游允许拆层、清字和原生文字重建，不重新设计已接受构图。

### Style 权威

`workbench/locks/visual_style_lock.json`。Style 09 live contract 只在创建锁时解析一次；生产读取旧锁时不得从 `references/visual-system.md` 刷新。

### 运行派生物

Prompt、manifest、clean base、authored SVG、Quick checkpoint、PPTX、QA report、artifact ledger 均是绑定输入哈希的派生产物。

## 修改规则

| 发现问题 | 应修改 | 不应直接修改 |
|---|---|---|
| 原文提取错误 | Source index / extractor | Semantic model 中手工补事实 |
| strict 业务理解错误 | semantic-argument-model | source-truth / foundation |
| 页面范围或页序错误 | deck-plan | Stage 02 manifest |
| 页面判断或上屏错误 | final-script | ImageGen prompt |
| 视觉结构错误且尚未接受 full 图 | Stage 02 visual structure / prompt | SVG 重建层 |
| 已接受 full 图后的文字位置/可编辑问题 | authored SVG / clean-base reconstruction | 重绘并重新设计 full 图 |
| 视觉风格规则需要升级 | `references/visual-system.md` 后创建新 style lock | 动态刷新历史 style lock |

## 失效传播

上游权威变化只使依赖它的下游派生产物失效。派生产物变化不得使上游权威自动变化。
