# Stage2 视觉设计改造实施记录

## 目标

按《CyberPPT Stage2 视觉设计改造开发方案》依次落地 Stage2 视觉设计改造，保持既定生产路线：

> 脚本 → 完整图片 → 图转可编辑 PPT

本记录作为长任务断点。每完成一个可独立验证的步骤，即提交代码并在此登记状态、主要变更、验证结果和 commit SHA。

## 实施原则

- 直接以 `main` 为落地主线。
- 每个步骤形成独立 GitHub commit，避免长流程中断造成未落盘修改丢失。
- 后续步骤只建立在已提交且通过对应测试的前一步之上。
- full image 通过审计后仍作为可编辑重建的视觉权威；authored SVG / PPTX 阶段不进行第二轮视觉设计。
- 优先修正合同与结构，再扩展 Region Graph、Visual Medium Policy、Prompt 和图像级 Deck Rhythm QA。

## 实施清单

### Phase 0｜断点与基线
- [x] P0.0 建立仓库内实施记录。
- [x] P0.1 核对 Stage2 相关代码、Schema、Skill 与测试基线。

### Phase 1｜合同修正
- [x] P1.1 修正 Generation Feasibility 评分：允许真实 0–100 分，`score == sum(dimensions)`，取消候选必须 100 分。
- [x] P1.2 引入 `focus_policy`，保留旧 `visual_center_count` 兼容读取。
- [x] P1.3 修复 `parallel_set` 与唯一 result / 唯一视觉中心冲突。
- [x] P1.4 将 scene 布尔值升级为 scene policy，支持 `required / allowed / forbidden / auto`，消除 `semantic_brief -> use_scene=False` 的硬绑定。

### Phase 2｜Region Graph
- [x] P2.1 定义 Region Graph 数据合同与 Schema。
- [x] P2.2 实现 topology → Region Graph 编译。
- [x] P2.3 实现 evidence / locked text → region binding。
- [x] P2.4 增加 Region Graph 审计与错误码。
- [x] P2.5 投影到 PageArtifactSpec / Prompt IR。

### Phase 3｜Visual Medium Policy
- [x] P3.1 定义 `visual_medium_policy`。
- [x] P3.2 将媒介选择与 relationship topology 解耦。
- [x] P3.3 更新 Skill 规则、Schema 与审计。

### Phase 4｜Prompt 编译
- [x] P4.1 Prompt 明确消费宏观区域、阅读轴、focus policy、媒介策略和文字归属。
- [x] P4.2 明确 ImageGen 微观自由边界。
- [x] P4.3 增加 Prompt 回归测试。

### Phase 5｜Full Image Deck Rhythm QA
- [x] P5.1 生成整套 full-image contact sheet。
- [x] P5.2 建立图像级页面视觉签名。
- [x] P5.3 检查连续构图、视觉重心、媒介和密度重复。
- [x] P5.4 将结果写入现有 Stage2 manifest / QA receipt，并在视觉权威冻结前执行阻断。

### Phase 6｜综合回归
- [x] P6.1 覆盖 parallel / convergence / flow / layered / boundary / ecosystem / allocation / conclusion / lifecycle 等固定测试页。
- [x] P6.2 验证旧项目兼容路径。
- [x] P6.3 验证 full image → authored SVG → editable PPTX 路径不发生第二轮视觉设计。

## 已完成记录

### P0.0｜建立实施记录
状态：完成。

变更：新增本文件，建立 Phase 0–6 的持久化执行清单。

验证：GitHub Actions `CyberPPT tests` 已在 Python 3.10 / 3.12 矩阵下通过。

Commit：`68b7f7dcf19c4765f774a0b94589aba4847acfc1`

### P0.1｜Stage2 基线核对
状态：完成。

基线确认：
- Stage2 视觉结构主实现：`cyberppt/visual_stage/compiler.py`、`cyberppt/visual_structure_contract.py`、`cyberppt/page_artifact_spec.py`。
- Stage2 视觉结构 Skill：`vendor/skills/ppt-visual-structure-designer/SKILL.md` 及其 `assets/`、`references/`、`scripts/`。
- 关键回归测试：`tests/test_visual_structure_contract.py`、`tests/test_visual_structure_stage.py`、`tests/test_page_artifact_spec.py`、`tests/test_final_prompt_ir.py`、`tests/test_final_prompt_renderer.py`。
- `main` CI：`.github/workflows/tests.yml`，Python 3.10 / 3.12 双版本执行完整 `pytest -q`。

已确认待修问题：
1. `_audit_generation_feasibility()` 强制候选满分 100。
2. compiler 全局写入 `visual_center_count = 1`。
3. `semantic_brief` 默认落为 `use_scene = False`。
4. geometry 主要仍是单一 `R_RELATION`。

Commit：`ec9566f7cd69aff5f1abdaca3810132cbc01a953`

### P1.1｜Generation Feasibility 真实评分
状态：完成。

变更：
- `_audit_generation_feasibility()` 保留五项 0–20 维度，允许真实的 0–100 总分。
- `score` 必须等于五项实际得分之和。
- 更新 Skill 评分合同。
- 新增真实 92 分及 score/sum 不一致回归测试。

验证：定向回归、runner 全量测试、清理后 Python 3.10 / 3.12 标准 CI 全部通过。

代码 Commit：`ed64f3675332cfe02244b326eb50f9d3027a48d1`

临时 runner 清理 Commit：`13e698e101a2a5f0df6d725df4ebdbad71fa8689`

### P1.2｜Focus Policy 合同
状态：完成。

变更：
- 新增 `single_anchor`、`paired_focus`、`peer_field`、`distributed_focus`、`sequence_focus` 五类 `focus_policy`。
- compiler 按 topology 生成兼容默认值：`parallel_set -> peer_field`、`causal_convergence/conclusion_anchor -> single_anchor`、`governance_boundary -> paired_focus`、`ecosystem_map -> distributed_focus`、流程/分层/循环/分配类 -> `sequence_focus`。
- `visual_decision` 开始稳定输出 `focus_policy`。
- `visual_center_count` 继续保留为 deprecated 兼容字段。

验证：P1.2 定向回归、runner 全量测试、清理后 Python 3.10 / 3.12 标准 CI 全部通过。

代码 Commit：`63f6ecf7e108a7232e1116955878b392a7262b9a`

临时 runner 清理 Commit：`e6206303bd8db171fdb502192b3910184fe37430`

### P1.3｜Parallel Set 真并列视觉重心
状态：完成。

变更：
- `parallel_set / peer_field` 不再把任一并列证据伪装成 `result` 或 `judgment`。
- 所有 P0 peer 共同进入主表达区域，禁止人为制造唯一 result binding。
- focus audit、topology audit、Schema、Skill 与 quality gates 同步支持真并列。

验证：P1.3 定向回归、runner 全量测试、标准 Python 3.10 / 3.12 CI 全部通过。

代码 Commit：`4acb15b16af65fe84ff2323284c879c770e7e0a2`

临时 runner 清理 Commit：`80373fc8ea1f828c9dd979be5325460d2bb7bdc5`

### P1.4｜Scene Policy 合同闭环
状态：完成。

变更：
- 场景合同升级为 `scene_policy`，支持 `required`、`allowed`、`forbidden`、`auto`。
- `semantic_brief` 默认使用 `auto`，不再预先排除业务场景、对象插图或混合视觉。
- VisualCarrier、visual budget、VisualDesignIR、审计、Schema、Skill 和 quality gates 全部消费 scene policy。
- 旧规格只有 `use_scene` 时继续兼容映射。

验证：domain-neutral fixtures、定向回归、runner 全量回归及标准 Python 3.10 / 3.12 CI 全部通过。

代码 Commit：`0e715752ff3dfc111f625e880a2857d5621dea73`

临时 runner 最终清理 Commit：`a7740e26fd2298ad77c76d2ea58e4526c3ce4aad`

### Phase 2｜Region Graph
状态：完成。

主要结果：
- 建立 Region Graph 合同、Schema、compiler、exact text binding 与审计。
- 九类视觉拓扑获得不同的区域结构、区域角色、锚点、权重与关系。
- `final_text.region_id` 与 locked text ownership 形成一一绑定。
- PageArtifactSpec / FinalPromptIR 开始消费 Region Graph；旧 `R_RELATION` 保留兼容，不再作为新逻辑权威。

关键 Commit：
- P2.1：`3bcf58e`、`b34bfc3`、`4953e9b`、`d2c677c`
- P2.2：`ede6cbb`、`2d4e431`、`d4b4b2b`
- P2.3：`cee53d4`、`6c6e522`、`fe5bc17`、`ff7296f`
- P2.4：`43c6b5e`、`5b1b334`、`9de751b`
- P2.5：`d0d191f`

### Phase 3｜Visual Medium Policy
状态：完成。

主要结果：
- 建立 `visual_medium_policy`，支持 `business_scene`、`object_illustration`、`relationship_diagram`、`data_visualization`、`mixed` 等媒介。
- relationship topology 与 visual medium 解耦；是否有箭头不再决定能否使用业务场景或插图。
- Skill、Schema、Audit、PageArtifactSpec / IR 均以 medium policy 为正式权威。

关键 Commit：
- P3.1：`e32528f`、`435f6ea`、`e11648b`
- P3.2：`66fd606`
- P3.3：`f69ba92`、`fcca149`、`3edba6f`

### Phase 4｜Prompt 编译
状态：完成。

主要结果：
- Final Prompt 明确输出 macro reading axis、Region 角色/锚点/权重/关系、focus policy、visual medium policy 与 exact visible-text ownership。
- `semantic_brief` 不再把宏观空间组织交给 ImageGen。
- 新增结构化 `micro_visual_freedom`：ImageGen 可处理区域内部对象表现、局部排布、材质、光影与从属细节；禁止改写宏观 Region、阅读轴、focus、媒介边界与文字归属。
- 九类 topology × prompt mode 回归矩阵通过。

关键 Commit：
- P4.1：`731a99e`
- P4.2：`b03d7bb`
- P4.3：`4be40ab`

### Phase 5｜Full Image Deck Rhythm QA
状态：完成。

主要结果：
- 生成 audited full-image contact sheet。
- 从真实成品图建立页面视觉签名：3×3 构图骨架、视觉重心、密度、结构哈希、源图哈希；medium 优先读取已审计元数据。
- deck rhythm audit 区分“风格一致”与“构图复制”，对连续同构页面执行 warning / blocked 判定。
- 生产顺序固定为：`require_generated → full-image deck rhythm QA → reconstruction_visual_source freeze`。
- blocked 时先写 QA receipt / manifest，再阻止视觉权威冻结；image-only 模式不执行重建权威冻结门，editable/both 强制执行。

关键 Commit：
- P5.1：`5414249`
- P5.2：`6a50934`、`51c68d1`
- P5.3：`ffcdede`、`d053a88`
- P5.4：`3f4b142`、`3986982`、`9cc5947`、`da91c0a`
- P5.4 兼容修复：`4eebeab`

验证：P5.1–P5.4 定向回归与完整 `pytest` 通过；P5.2 / P5.3 标准 Python 3.10 / 3.12 CI 均通过。

### Phase 6｜综合回归与重建权威闭环
状态：完成。

主要结果：
- P6.1：九类 topology 综合链回归覆盖 `Region Graph → exact text binding → audit → PageArtifactSpec → FinalPromptIR → Prompt`；综合测试按 renderer 的公开 Prompt 合同验证 macro reading axis、Region、medium、micro freedom 与 backend ID 隔离。
- P6.2：旧 visual spec 缺少 Region Graph、Visual Medium Policy、scene_policy 时仍可通过 legacy `use_scene` 兼容路径。
- P6.3：新增 reconstruction visual authority validator；editable/both 在 clean-base 生成前后复核 audited full image 的 path/hash/immutable 标记，Quick adapter 入口再次复核，Quick checkpoint 持久化 `reconstruction_visual_source_sha256`。
- full image 一旦冻结为 `reconstruction_visual_source`，后续 clean-base / authored SVG / Quick editable PPTX 必须继续绑定同一视觉权威；重建阶段只允许拆解和可编辑重建，不允许第二轮视觉设计。

关键 Commit：
- P6.1：`b0c793e`；公开 Prompt 合同修订：`b9d5096`
- P6.2：`5250616`
- P6.3 validator：`6312a14`
- reconstruction stage authority guard：`88b302c`
- authority 故障测试：`9bdf5e9`
- 最终 adapter guard、Quick checkpoint authority SHA 与兼容回归闭环：`f4ec386`

验证：
- 最终 Phase 6 聚焦回归全部通过。
- 最终 runner 完整 `pytest` 全部通过。
- 临时 `stage2-p6-3-authority-adapter.yml` 已在生产提交中自删除。

## 最终架构结论

Stage2 的职责边界已收敛为：

1. Stage1：语义脚本权威。
2. Stage2 PageVisualSpec / Region Graph / Visual Medium Policy：宏观视觉生成约束权威。
3. ImageGen：在宏观合同内拥有区域内部的微观视觉实现自由。
4. Audited Full Image：通过文字与整套节奏 QA 后冻结为重建视觉权威。
5. Clean base / Authored SVG / Editable PPTX：忠实重建已接受构图，不再进行第二轮视觉设计。

核心原则：

> Stage2 控制宏观视觉设计，ImageGen 保留微观视觉自由；审计通过的完整图片控制后续可编辑重建。
