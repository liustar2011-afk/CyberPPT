# Stage2 Artifact Contract v3 开发台账

开发分支：`feature/stage2-artifact-contract-v3`

本台账用于记录 Stage2 送图脚本优化改造全过程。每完成一个可验证的小步骤，必须同步记录已完成工作、验证结果和下一阶段工作；代码提交信息同时采用相同口径。

## Step 0｜开发基线与实施机制

状态：已完成

已完成工作：
- 以 `main@7bfdf58cf6cbe0317dc038691433dd797d7d6444` 创建独立开发分支。
- 核对 Stage2 现有代码，确认 `VisibleTextBindingSpec` 已实现但在 `build_page_artifact_spec()` 被置空。
- 核对最终 Prompt 链，确认 locked copy 权威与 downstream rewrite/source-material 口径存在冲突。
- 核对 Region Graph、Visual Medium、Text Capacity、Visual Thesis、Stage02 body canvas 和 Prompt validator 的现状。
- 确定采用“每个小步骤独立提交 + 定向 pytest + Draft PR 统一台账”的实施机制。

验证结果：
- 仓库 Issues 功能关闭，因此改用 Draft PR 作为统一过程台账。
- 仓库现有 PR CI 可运行 Ubuntu Python 3.10/3.12 全量测试，并含 macOS / Windows wheel smoke 与 OfficeCLI smoke。

下一阶段工作：
- Step 1.1：新增独立 Copy Contract 领域合同与权威规则测试。

## Step 1.1｜Copy Contract 领域模型

状态：已完成

已完成工作：
- 新增 `cyberppt/copy_contract.py`。
- 建立 `CopyContractSpec`、`LockedCopySpec`、`RewriteableCopySpec`、`ExtraTextPolicySpec`。
- authored visible copy 默认进入 locked copy；仅显式授权的 text_id 才允许进入 rewriteable copy。
- locked copy 强制 `count=1`，并限制 transformation 只能是 line break / grouping / position_change 等不改变文案的操作。
- extra text 默认 `allowed=false`、`max_count=0`。
- 新增 `tests/test_copy_contract.py`，覆盖默认锁定、显式改写授权、region ownership、重复 id、权限重叠、非法 transformation、extra text 等规则。

验证结果：
- Copy Contract 领域模型与测试已作为独立提交进入 PR #29。
- 当前全量 CI 仍包含仓库基线既有失败，不能以全量 CI 作为本步骤增量正确性的唯一判据；后续步骤继续采用定向测试 + PR CI 双层验证。

下一阶段工作：
- Step 1.2：恢复 `_visible_text_bindings()` 权威链，将 Copy Contract 接入 `PageArtifactSpec → FinalPromptIR → Renderer → Validator`，并删除 locked copy 的 rewrite/source-material 冲突授权。

## Step 1.2｜Copy Contract 权威链闭环

状态：已完成

已完成工作：
- 恢复 `_visible_text_bindings()`，不再将 authored visible copy 主动降级为空绑定。
- `PageArtifactSpec` 增加 `copy_contract`，并校验 Copy Contract 对全部 visible text binding 的唯一覆盖。
- 将 Region Graph 的 `text_ids` 映射到 Copy Contract，保留每条上屏文字的 macro region ownership。
- `FinalPromptIR` 增加 `copy_contract` 并将 IR 版本升级至 v5。
- Renderer 对 locked copy 使用 `Exact visible text` 合同，每条逐字声明一次；rewriteable copy 仅对显式授权项输出 rewrite goal。
- 删除 Copy Contract 路径中的 blanket `rewrite / merge / shorten / reorder / split / select / replace` 授权。
- extra text 默认在最终 Prompt 中显式禁止。
- Validator 分别校验 exact copy、rewriteable copy、extra text policy，并继续阻止 backend/internal 字段泄漏。
- Debug receipt 增加 Copy Contract sidecar 信息。
- 新增 `tests/test_copy_contract_pipeline.py`，覆盖 locked-only、mixed copy、coverage drift。

验证结果：
- 第一次定向测试发现 `claim_strength` 内部字段会泄漏到 Prompt；未提交半成品。
- 修正为公共表述 `claim strength`，保持 backend leak validator 严格不放宽。
- 第二次执行 `tests/test_copy_contract.py + tests/test_copy_contract_pipeline.py` 全部通过。
- 业务提交：`64a50136a81b6b57b7cc1a4d1ce67ced1a123f0d`（`stage2-v3: close copy contract authority chain`）。
- Phase 1 验收目标已形成代码闭环：locked copy 逐字唯一声明、Region ownership 保留、Copy Contract 路径不存在 blanket rewrite 与 strict lock 并存。

下一阶段工作：
- Phase 2 / Step 2.1：新增 `CompositionStrategy` contract，删除 topology 对 macro axis/geometry 的一对一权威关系；Region Graph 改为消费 composition strategy，并建立同一 topology 至少 3 种合法宏观构图策略的测试。

## Step 2.1｜CompositionStrategy 独立合同

状态：已完成

已完成工作：
- 新增 `cyberppt/composition_strategy.py` 与 `CompositionStrategySpec`。
- topology 仅约束合法策略集合，macro geometry 由独立 resolver 决定。
- 建立 horizontal / vertical / open spatial / radial / layered / split boundary / stepped path 等宏观策略。
- resolver 使用 focus policy、evidence count、visual medium、page rhythm 等输入评分。
- 新增 `tests/test_composition_strategy.py`。

验证结果：
- 9 类 render topology 均提供不少于 3 种合法 macro strategy。
- 相邻页面重复策略会被显式降权。
- 定向测试 `tests/test_composition_strategy.py` 全部通过。

下一阶段工作：
- Step 2.2：Region Graph 消费 CompositionStrategy，移除 topology → axis 一对一权威映射，并接入实际 Visual Stage 编译链。

## Step 2.2｜Topology 与 Composition 生产链解耦

状态：已完成

已完成工作：
- `region_graph.py` 移除 `_AXIS_BY_TOPOLOGY` 生产权威；Region Graph 接收 `CompositionStrategySpec`。
- Region Graph 的 primary axis、anchor、span 由 composition strategy 决定；semantic topology 继续决定 region role 与 relationship truth。
- 保留 `legacy_composition_strategy()` 仅用于旧调用兼容投影。
- Visual Stage 在生成 Region Graph 前独立执行 `resolve_composition_strategy()`，并将结果持久化为 `composition_strategy`。
- 保留 semantic topology compatibility audit，避免构图自由改变业务关系语义。
- 新增 `tests/test_region_graph_composition_strategy.py`，验证同一 `directed_flow` 在 3 种宏观几何下关系边完全一致。

验证结果：
- 定向执行 `tests/test_composition_strategy.py + tests/test_region_graph_composition_strategy.py + tests/test_region_graph.py` 通过。
- 业务提交：`801f84a71d29dbb2fc0bf2f70be29f0f023a2d41`（`stage2-v3: decouple topology from composition strategy`）。
- Phase 2 验收完成：同一 topology 可生成至少 3 种合法 macro composition；生产链不再由 topology 强制固定 axis；业务关系 truth 保持不变。

下一阶段工作：
- Phase 3 / Step 3.1：升级 Visual Medium Resolver v2，增加页面语义评分、confidence、forbidden media，取消 `mixed` 无条件默认，并保证 rationale 与实际评分依据一致。

## Step 3.1｜Visual Medium Resolver v2 语义评分合同

状态：已完成

已完成工作：
- `VisualMediumPolicy` 升级为 v2，新增 `secondary`、`forbidden`、`confidence`、`scores`、`version`。
- scene policy 仅负责媒介资格边界；preferred medium 由页面使命、业务关系、可画业务对象、主体类型、数据信号和轻量密度信号评分。
- `mixed` 取消无条件默认，仅在确有跨媒介需求且两个专业媒介同时强、分差接近时进入首选竞争。
- 收紧 data visualization 触发条件，普通“数据提供方”等数据主体不再被误判为图表任务；指标、趋势、统计、监测、预测、分布等读数/读趋势任务才形成数据表达强信号。
- 扩展 visual-medium-policy JSON Schema，保持旧 required 字段兼容。
- 新增 `tests/test_visual_medium_resolver_v2.py` 并更新 `tests/test_visual_medium_policy.py`。

验证结果：
- 第一轮 10 passed / 2 failed，暴露 mixed 过度抢占；未进入生产链接入。
- 第二轮 11 passed / 1 failed，定位“数据提供方”误触 data visualization；继续阻断接入。
- 第三轮全部通过：同一 scene policy 下，操作场景、关系治理、对象说明、数据趋势可得到不同 preferred medium；mixed 不再作为兜底。

下一阶段工作：
- Step 3.2：将 v2 resolver 接入 Visual Stage，并把 secondary / forbidden / confidence 贯通 FinalPromptIR、生产 Prompt 和 debug receipt。

## Step 3.2｜Visual Medium Resolver v2 生产链闭环

状态：已完成

已完成工作：
- Visual Stage 向 resolver 提供 page mission、verified business relationships、正文数量/字符数、business object、actor type、data availability 等语义输入。
- `FinalPromptIR.VisualMediumPolicyIR` 增加 secondary / forbidden / confidence 并做合法性校验。
- `artifact_prompt.py` 完整投影 v2 medium contract。
- 最终 Prompt 输出 preferred、secondary、allowed、forbidden、confidence、scene policy 和公共化 rationale；内部枚举下划线不直接泄漏到 Prompt。
- Debug receipt 保留原始 v2 medium 字段，便于追溯评分与选择依据。
- 新增 `tests/test_visual_medium_prompt_v2.py`，同时回归 Phase 2 的 Region Graph / CompositionStrategy 集成。

验证结果：
- 定向执行 `test_visual_medium_policy + test_visual_medium_resolver_v2 + test_visual_medium_prompt_v2 + test_region_graph_composition_strategy` 全部通过。
- 业务提交：`430019a2f6d80d83ec23742b31505a80dab4f0bd`（`stage2-v3: integrate semantic visual medium resolver`）。
- Phase 3 验收完成：相同 scene policy + 不同页面语义可选择不同 preferred medium；medium 具备 score / confidence / forbidden；rationale 与真实评分输入一致。

下一阶段工作：
- Phase 4 / Step 4.1：为 Text Capacity 增加 `content_action`，删除 dense text 对 visual budget 的直接降级路径；blocked 页面明确返回 Stage01 内容工程处理，Visual Medium Resolver 只消费容量通过页面。

## Step 4.1｜Text Capacity 与内容工程分离

状态：已完成

已完成工作：
- `TextCapacityAssessment` 新增 `content_action`，passed 对应 `continue_stage02`，blocked 对应 `return_to_stage01`。
- `assert_text_capacity()` 的 blocked 错误明确要求返回 Stage01 做拆页、取舍或正文修订，禁止让 ImageGen 通过漏字、改写或减视觉规避容量问题。
- PageArtifactSpec 对全部 authored visible text 执行容量评估并保留 `text_capacity`；blocked 页面在进入后续视觉规划前阻断。
- Visual Stage 新增 `_stage02_text_capacity()`，在 `_decision_execution_design()` 和 Visual Medium Resolver 之前执行。
- 删除 PageArtifactSpec 的 `dense text → relationship_field_only → zero auxiliary visuals` 分支。
- 删除 Visual Stage visual budget 对 dense flag 的直接响应；保留 legacy 私有函数参数但明确忽略。
- Visual Stage 持久化 text capacity status / content_action / pressure score / structural indicators。
- 新增 `tests/test_text_capacity_v2.py`，验证 passed/blocked action、blocked 回 Stage01，以及 dense flag 不再导致零视觉。

验证结果：
- 定向执行 `test_text_capacity_v2 + test_visual_medium_policy + test_visual_medium_resolver_v2 + test_region_graph_composition_strategy` 全部通过。
- 业务提交：`fae03b7bd64d7382b02686800db26ab4b3b1876d`（`stage2-v3: separate text capacity from visual planning`）。
- Phase 4 验收完成：文字多不再自动导致 zero auxiliary visuals；只有容量真正 blocked 时返回 Stage01，medium resolver 仅消费容量通过页面。

下一阶段工作：
- Phase 5：Visual Thesis 必填，禁止 fallback 到 core_judgment，增加与 core judgment 的重复度校验和关系性校验。

## Step 5.1｜Visual Thesis 强校验

状态：已完成

已完成工作：
- 新增 `cyberppt/visual_thesis.py`，将 visual thesis 固化为独立语义合同。
- 缺失 thesis、与 core judgment 相同或高相似度、纯口号式且缺少关系性信号的 thesis 均阻断。
- Visual Stage compiler 删除 `selected.visual_thesis or core_judgment` fallback；PageArtifactSpec 增加第二道防绕过校验。
- `ppt-visual-structure-designer/SKILL.md` 同步升级为可执行强约束。
- 新增 `tests/test_visual_thesis.py`、`tests/test_visual_thesis_compiler_contract.py`。

验证结果：
- Visual Thesis 领域与生产链定向测试通过，并回归 Text Capacity 与 Visual Medium v2。
- 业务提交：`ed6a692e565190681b1ba93a2a44a1ad2431a3a0`（`stage2-v3: enforce relational visual thesis`）。
- Phase 5 验收完成：`visual_thesis == core_judgment` 被阻断，且不存在 core judgment fallback。

下一阶段工作：
- Phase 6：增加完整 16:9 Full-slide Design Context，同时保持 external title layer 和 2048×1024 body export 兼容。

## Step 6.1｜16:9 Full-slide Design Context

状态：已完成

已完成工作：
- 新增 `cyberppt/full_slide_context.py`，建立 1920×1080（16:9）完整页面设计坐标合同。
- 外置标题区为 `x=128, y=52, w=1664, h=120`；正文图区为 `x=128, y=216, w=1664, h=832`，保持 2:1。
- Stage02 handoff、PageArtifactSpec、FinalPromptIR、Renderer、validator、debug receipt 全部贯通 full-slide context。
- 标题与副标题继续由 external text layer 提供，正文图继续独立导出为 2048×1024。
- 旧 handoff 缺少 full-slide 字段时通过 `legacy_stage02_prompt_contract` 做兼容投影。

验证结果：
- `test_full_slide_context + test_full_slide_prompt_context` 及 Visual Thesis / Text Capacity / Medium 回归测试通过。
- 业务提交：`21ab6b1fdfc2beffcedc3e2f7836edb657bc3109`（`stage2-v3: add full-slide design context to production chain`）。
- Phase 6 验收完成：构图知道完整 16:9 标题区域，同时既有 body-image 和 editable reconstruction 边界保持兼容。

下一阶段工作：
- Phase 7：新增 AcceptanceSpec，将生成要求升级为可机器校验的验收合同，并启用 artifact-spec-v3 正式路径。

## Step 7.1｜Acceptance Contract 与 artifact-spec-v3

状态：已完成

已完成工作：
- 新增 `cyberppt/acceptance_contract.py` 与 `AcceptanceSpec`。
- 八项验收字段完整落地：exact copy coverage、extra text count、region ownership、relationship accuracy、hierarchy preservation、minimum readability、forbidden structure absence、style lock conformance。
- PageArtifactSpec 同时补齐 `composition_strategy` 审计字段，确保 v3 正式路径具备完整权威链。
- FinalPromptIR 升级至 v6；最终 Prompt 新增 `[Acceptance criteria]`；validator 校验出现次数、顺序和关键值；debug receipt 与该合同保持一致。
- 新增 `artifact-spec-v3` 编译器标识并保留 `artifact-spec-v2`；v3 要求 Copy Contract、Composition Strategy、Region Graph、Visual Medium Policy、Acceptance、Full-slide Context 和 passed Text Capacity 全部存在。
- 新增 `tests/test_acceptance_contract.py`、`tests/test_acceptance_prompt_contract.py`。

验证结果：
- Acceptance domain 与生产链集成测试通过，并同时回归前六阶段核心合同。
- 业务提交：`df36e28b3e59847f7813de2924f5edad531c4907`（`stage2-v3: add production acceptance contract`）。
- Phase 7 验收完成，七个功能阶段全部进入正式生产链。

下一阶段工作：
- 执行聚合定向测试、清理临时开发执行器，再运行仓库全量 CI 与兼容性检查。

## Step 8｜聚合定向测试与临时开发设施清理

状态：已完成聚合定向测试；全量 CI 待最终核对

已完成工作：
- 聚合执行 Phase 1–7 新增测试及跨阶段回归测试。
- 删除本次开发使用的临时 `tools/stage2_v3_*.py` 执行器。
- 删除本次开发使用的 `.github/workflows/stage2-v3-apply.yml` 专用工作流。
- 正式功能代码、领域合同、生产链改造和长期回归测试全部保留。

验证结果：
- Phase 1–7 聚合定向测试全部通过后才执行清理提交。

下一阶段工作：
- 由仓库常规 `CyberPPT tests` 工作流执行全量 CI；对照开发基线区分既有失败与本次增量回归，并据此决定 PR 是否可转 Ready for review。

