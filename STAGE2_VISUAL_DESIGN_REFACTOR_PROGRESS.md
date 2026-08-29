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
- [ ] P1.3 修复 `parallel_set` 与唯一 result / 唯一视觉中心冲突。
- [ ] P1.4 将 scene 布尔值升级为 scene policy，支持 `required / allowed / forbidden / auto`，消除 `semantic_brief -> use_scene=False` 的硬绑定。

### Phase 2｜Region Graph
- [ ] P2.1 定义 Region Graph 数据合同与 Schema。
- [ ] P2.2 实现 topology → Region Graph 编译。
- [ ] P2.3 实现 evidence / locked text → region binding。
- [ ] P2.4 增加 Region Graph 审计与错误码。
- [ ] P2.5 投影到 PageArtifactSpec / Prompt IR。

### Phase 3｜Visual Medium Policy
- [ ] P3.1 定义 `visual_medium_policy`。
- [ ] P3.2 将媒介选择与 relationship topology 解耦。
- [ ] P3.3 更新 Skill 规则、Schema 与审计。

### Phase 4｜Prompt 编译
- [ ] P4.1 Prompt 明确消费宏观区域、阅读轴、focus policy、媒介策略和文字归属。
- [ ] P4.2 明确 ImageGen 微观自由边界。
- [ ] P4.3 增加 Prompt 回归测试。

### Phase 5｜Full Image Deck Rhythm QA
- [ ] P5.1 生成整套 full-image contact sheet。
- [ ] P5.2 建立图像级页面视觉签名。
- [ ] P5.3 检查连续构图、视觉重心、媒介和密度重复。
- [ ] P5.4 将结果写入现有 Stage2 manifest / QA receipt。

### Phase 6｜综合回归
- [ ] P6.1 覆盖 parallel / convergence / flow / layered / boundary / ecosystem / allocation / conclusion 等固定测试页。
- [ ] P6.2 验证旧项目兼容路径。
- [ ] P6.3 验证 full image → authored SVG → editable PPTX 路径不发生第二轮视觉设计。

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
- `visual_center_count` 继续保留为 deprecated 兼容字段，尚未在本步骤改变旧语义。
- page visual schema 增加 `focus_policy` 枚举；Skill 增加 focus policy 决策说明。
- 新增 `tests/test_stage2_focus_policy.py` 覆盖并列、汇聚、边界三类默认映射。

验证：P1.2 定向回归、runner 全量测试、清理后 Python 3.10 / 3.12 标准 CI 全部通过。

代码 Commit：`63f6ecf7e108a7232e1116955878b392a7262b9a`

临时 runner 清理 Commit：`e6206303bd8db171fdb502192b3910184fe37430`
