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

## 提交记录

- Step 0：`c89dfc8` — 建立 Stage2 改造断点记录。
- Phase 1 代码：`7312524` — Scene Policy、Visual Budget、focus-aware fallback。
- Phase 1 测试：`3a4ccb7` — Scene Policy 与 fallback 回归测试。

## 实施阶段

### Step 0｜建立断点记录机制

状态：DONE

完成内容：

- 新增本实施记录文件；
- 明确后续每个步骤均采用“代码改造 → 测试/核验 → 更新本记录 → 提交 main”的闭环；
- 后续不将多个未验证阶段堆积为一次大提交。

### Phase 1｜合同修正

状态：DONE

仓库原有能力：

- `focus_policy` 已进入 `cyberppt/visual_stage/compiler.py`；
- 已定义 `single_anchor / paired_focus / peer_field / distributed_focus / sequence_focus`；
- `parallel_set` 默认映射 `peer_field`；
- `visual_center_count` 已被标记为兼容字段；
- `visual_structure_contract.py` 的 generation feasibility 已允许 `score == dimensions sum` 且范围为 0–100；
- `peer_field` 已拥有独立 focus competition 审计逻辑。

本阶段新增：

1. `semantic_brief` 默认输出 `scene_policy=auto`，不再硬编码 `use_scene=False`；
2. 新增 `required / allowed / forbidden / auto` 四类 Scene Policy；
3. 旧 `use_scene` 继续作为兼容字段，`scene_policy` 成为权威字段；
4. visual budget 改为由文字密度和 scene policy 决定，不再因 `semantic_brief` 或 `parallel_set` 自动压缩；
5. 非高密度 `semantic_brief` / `parallel_set` 可进入 `integrated_scene`；
6. fallback 构图文案按 `focus_policy` 区分 single / peer / paired / distributed / sequence；
7. generation handoff 显式传递 `scene_policy` 与 `focus_policy`；
8. `representation_freedom` 从完全 free 调整为 bounded；
9. 新增 `tests/test_stage2_scene_policy.py`。

核验：

- GitHub 提交内容已回读并确认 diff；
- 当前仓库未返回与该提交关联的 CI status，因此尚无远端自动测试结果；
- 下一阶段继续保持兼容字段，Region Graph 完成后再统一升级 schema。

### Phase 2｜Region Graph

状态：IN PROGRESS

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

执行 Phase 2：先在 compiler 中建立 topology-driven Region Graph，并将 P0 evidence / final_text 绑定到具体 Region；随后在 `visual_structure_contract.py` 增加独立 Region Graph 审计，再补回归测试。
