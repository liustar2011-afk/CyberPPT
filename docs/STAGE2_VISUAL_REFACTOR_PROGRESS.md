# Stage2 视觉设计改造实施记录

> 本文件是 Stage2 视觉设计改造的仓库内断点记录。每完成一个可验证开发步骤，必须同步更新本文件并提交到 `main`，以便任何中断后从最后一次提交继续。

## 固定生产路线

`Stage1 脚本 → Stage2 完整图片 → 图转可编辑 PPT`

本次改造仅优化 Stage2 的视觉设计约束、Prompt 编译、full image QA 与后续重建接口，不改变上述生产路线。

## 目标架构

`Stage1 Final Script → Semantic Graph → Visual Structure Decision → Region Graph → Visual Medium Decision → PageVisualSpec → Style Lock → FinalPromptIR / Manifest → ImageGen → Full Image → QA → Audited Full Image → Editable Reconstruction`

其中：

- Stage1：语义脚本权威；
- Stage2 PageVisualSpec：生成约束权威；
- Audited Full Image：重建视觉权威；
- Editable Reconstruction：忠实可编辑重建，不进行第二轮视觉设计。

## 实施阶段

### Step 0｜建立断点记录机制

状态：DONE

完成内容：

- 新增本实施记录文件；
- 明确后续每个步骤均采用“代码改造 → 测试/核验 → 更新本记录 → 提交 main”的闭环；
- 后续不将多个未验证阶段堆积为一次大提交。

### Phase 1｜合同修正

状态：IN PROGRESS

已确认当前 `main` 已存在的部分能力：

- `focus_policy` 已进入 `cyberppt/visual_stage/compiler.py`；
- 已定义 `single_anchor / paired_focus / peer_field / distributed_focus / sequence_focus`；
- `parallel_set` 默认映射 `peer_field`；
- `visual_center_count` 已被标记为兼容字段，新结构开始消费 `focus_policy`；
- `visual_structure_contract.py` 的 generation feasibility 已允许 `score == dimensions sum` 且范围为 0–100；
- `peer_field` 已拥有独立 focus competition 审计逻辑。

仍待完成：

1. `semantic_brief` 不再硬编码 `use_scene=False`；
2. `scene_policy` 从布尔语义升级为 `required / allowed / forbidden / auto`；
3. `parallel_set` 与其他非定向页面不再因 topology/prompt_mode 被自动压缩为 `relationship_field_only`；
4. 清理仍然使用“唯一视觉焦点”的 fallback 文案，使其服从 `focus_policy`；
5. 增加 Phase 1 回归测试。

### Phase 2｜Region Graph

状态：TODO

计划：

- 增加 `region_graph` 数据合同；
- topology → region graph；
- P0 evidence → region binding；
- 替换单一 `R_RELATION` 作为默认宏观空间合同；
- 增加 Region Graph validator 与回归测试。

### Phase 3｜Visual Medium Policy

状态：TODO

计划：

- 增加 `business_scene / object_illustration / relationship_diagram / data_visualization / mixed`；
- 将 visual medium 与 semantic topology 解耦；
- 由页面使命、业务对象、可画动作、信息密度、Style lock 和 deck rhythm 共同决定媒介策略。

### Phase 4｜Prompt 编译升级

状态：TODO

计划：

- Prompt 显式携带 Region Graph、Focus Policy、Visual Medium Policy、主阅读方向和 text-region binding；
- ImageGen 保留区域内部微观构图自由；
- 宏观业务关系和区域主次不得由 ImageGen 重写。

### Phase 5｜Full Image Deck Rhythm QA

状态：TODO

计划：

- full image 生成后增加 contact sheet；
- 检查实际视觉骨架、视觉重心、媒介重复和信息密度节奏；
- QA 通过后再将 full image 锁定为 reconstruction authority。

## 当前下一步

执行 Phase 1 剩余合同修正，优先修改 `cyberppt/visual_stage/compiler.py` 中：

- semantic_brief scene policy；
- visual budget；
- fallback focus 文案。

随后补充相应测试并再次更新本记录。
