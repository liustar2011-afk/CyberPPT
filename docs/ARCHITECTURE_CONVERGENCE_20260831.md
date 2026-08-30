# CyberPPT 架构收敛实施记录（2026-08-31）

> 分支：`agent/architecture-convergence-20260831`
>
> Draft PR：`#24`
>
> 目的：按阶段实施架构收敛，每个小阶段独立提交，保证中断后可从最近提交继续。

## 技术判断

结论：`SUPPORT WITH CONDITIONS`

实施原则：

1. 优先修复会影响可复现性、权威边界和恢复语义的问题。
2. Stage 02 已完成较好的 pipeline 分层，保持现有生产路线，不进行推倒重写。
3. Stage 01 的大模块拆分采用行为保持型重构；本轮不把高风险语义改写与结构拆分混在同一提交。
4. 所有兼容迁移均保持单向：旧入口只能适配到新核心，不允许反向 monkey-patch 新核心。
5. 每阶段完成后更新本文档并提交。

## 阶段计划与状态

| 阶段 | 内容 | 状态 | 提交 |
|---|---|---|---|
| 0 | 建立独立分支与实施记录 | 完成 | `8f12875` |
| 1 | 真正冻结 Style 09 resolved contract，并建立运行输入 fingerprint | 完成 | 见阶段 1 记录 |
| 2 | 统一 Stage 01 Authority Map 与权威命名 | 完成 | 见阶段 2 记录 |
| 3 | Stage 02 正式状态机与 needs-action 语义 | 完成 | 见阶段 3 记录 |
| 4 | 收缩 Stage 02 compatibility facade，去除 monkey-patch 生产依赖 | 完成 | 见阶段 4 记录 |
| 5 | 将主观语义/文风检查从 hard blocker 分级为 warning/critic | 完成 | 见阶段 5 记录 |
| 6 | 修复 Python 包/运行时依赖边界，增加 production extras 与 wheel smoke CI | 完成 | 见阶段 6 记录 |
| 7 | 独立 `input_fingerprint` 与 `run_id/build_id` | 完成 | 见阶段 7 记录 |
| 8 | Stage 01 大模块行为保持型拆分（低风险子域优先） | 条件性完成 | 见阶段 8 记录 |
| 9 | 统一正式 Style 09 路由与 CLI/文档残留 | 完成 | 见阶段 9 记录 |
| 10 | 清理根目录临时文件与仓库治理规则 | 完成 | 见阶段 10 记录 |

## 阶段 1：视觉锁与输入身份

状态：完成。

### 1A. Style 09 resolved contract 真冻结

提交：

- `46c34f8` `fix(style): freeze resolved Style 09 contract in lock`
- `d159005` `test(style): cover frozen Style 09 snapshots`

完成内容：Style 09 在锁创建时冻结 resolved contract；运行时禁止 live refresh；legacy live lock 和篡改锁 fail-closed。

### 1B. Deterministic input fingerprint

提交：

- `bedefa0` `refactor(stage02): model deterministic input identity`
- `742e685` `feat(stage02): derive deterministic input fingerprint`
- `031f90f` `feat(stage02): persist input fingerprint in manifest`
- `408c4da` `feat(stage02): expose input identity in delivery receipts`
- `b960e7e` `test(stage02): cover deterministic input fingerprint`

完成内容：建立 timestamp-free input fingerprint，并持久化到 manifest、build context 和 run summary；默认 build ID 摘要由 fingerprint 派生。

### 1C. Prompt 变化后的产物失效

提交：

- `3b004a8` `fix(stage02): invalidate reused artifacts when prompt changes`
- `81dc232` `test(stage02): block stale prompt artifact reuse`

完成内容：正式 Stage 02 编排中的 full 图和其 clean base / authored SVG / Quick checkpoint 只能在页级 generated Prompt SHA 与当前 Prompt SHA 一致时复用。

## 阶段 2：Stage 01 Authority 收敛

状态：完成。

提交：

- `85a3dec` `docs(stage01): define canonical authority map`
- `889eefe` `docs(stage01): align strict skill with authority map`
- `f52f9b4` `docs(stage01): define semantic IR field ownership`
- `c707821` `test(stage01): enforce authority documentation boundary`

完成内容：

1. 新增 `docs/STAGE01_AUTHORITY_MAP.md`，统一 Source Evidence、SemanticIR、FoundationIR、DeckPlanIR、FinalScriptIR 五个运行层级，其中只有内容 authority 可以被直接修复。
2. strict/legacy 的 `normalized-facts.json`、`concept-base.json`、`relation-graph.json`、`argument-chain.json` 被定义为一个逻辑 SemanticIR 的字段分区，并明确各自字段所有权。
3. `semantic-argument-model.json`、`source-truth.json`、`outline.json` 在 strict/legacy 中统一定义为兼容/机械 projection；即使当前 runtime 消费它们，也不得手工修改为第二套语义 authority。
4. `script/foundation.json` 是 PLAN/AUTHOR 的统一语义入口；`script/deck-plan.json` 是 DeckPlanIR；`script/dist/final-script.md` 是 FinalScriptIR 和 Stage 02 唯一跨阶段业务输入。
5. 修订 `cyberppt-source-foundation` 与 `business-semantic-understanding` Skill，消除“canonical semantic-argument-model”与四文件 SemanticIR 并存的命名歧义。
6. 新增静态回归测试防止后续文档再次把 compatibility projection 提升为独立 authority。

## 阶段 3：Stage 02 needs-action 状态机

状态：完成。

提交：

- `01bcff8` `feat(stage02): add explicit needs-action state model`
- `b4b46cc` `refactor(stage02): carry pending actions in result model`
- `7a8febc` `feat(stage02): return needs-action instead of checkpoint exception`
- `2839669` `feat(stage02): persist needs-action delivery state`
- `4835b53` `test(stage02): cover explicit needs-action states`

完成内容：

1. 新增 `stage02_production/state.py`，区分正常待办和真正失败。
2. 缺少 authored SVG → `needs_action / author_svg`。
3. Quick 页已渲染待人工/Agent检查 → `needs_action / review_quick_page`。
4. Quick 视觉审核失败 → `needs_action / revise_quick_page`。
5. 几何、文字、运行时等未分类失败继续抛出原异常，保持 fail-closed。
6. `ReconstructionStageResult`、run summary 和 build context 均持久化 `needs_actions`。
7. `needs_action` 状态不启动整套 OfficeCLI 交付 QA；完成待办后使用同一 build 续跑。
8. 本阶段不新增独立 `build-status` CLI；现有 run summary / build context 已是稳定机器查询面，避免为了单一命令扩大 44KB CLI 的修改风险。

## 阶段 4：Compatibility facade 单向化

状态：完成。

提交：

- `a29a454` `refactor(stage02): make legacy patch seam non-mutating`
- `f2b4ad7` `refactor(stage02): make command facade a one-way adapter`
- `25c4697` `test(stage02): enforce non-mutating compatibility seam`
- `cea6f05` `test(stage02): migrate legacy facade patch targets`

完成内容：

1. `stage02_production/compat.py` 只保留历史 import 名，`sync_legacy_patch_points()` 变为 deprecated no-op。
2. `commands/final_script_pages.py` 只负责参数转换并调用 typed `run_production()`，正式执行前不再把 facade monkey-patch 写入 image/reconstruction/delivery 模块。
3. 正式依赖由 owning module 自己解析，运行行为不再受 facade import 顺序影响。
4. 首轮 PR CI 暴露历史测试仍 patch 旧 facade 名称；没有恢复生产 monkey-patch，而是在 `tests/conftest.py` 中把该历史回归模块的 patch target 定向到 owning module，作为测试迁移层。
5. 新代码测试继续要求生产 facade 非变异；待旧大测试文件后续自然拆分时可删除迁移 shim。

## 阶段 5：Hard Gate 与 Critic Advisory 分级

状态：完成。

提交：

- `9c5e42c` `refactor(lint): keep only hard phrasing blockers`
- `ce4222f` `feat(lint): add advisory phrasing rules`
- `f4a46e0` `feat(lint): add non-blocking Critic advisory scan`
- `a79114f` `docs(lint): route subjective heuristics to Critic warnings`
- `a7ffa6c` `test(lint): separate advisory warnings from hard blockers`

完成内容：

1. `contracts/banned-phrasing.json` 只保留高置信 hard blocker：显式禁止句式、作者/页面元信息泄漏、业务对象明显不完整、舞台说明标签等。
2. 口语复述、听众称谓、主持式口播、分析过程式论点等启发式规则迁入 `contracts/advisory-phrasing.json`。
3. 新增 `python -m script_engine.advisory_lint <final-script.json>`；命中 warning 时仍返回退出码 0。
4. Script Workflow 明确：advisory 进入 CRITIQUE，由 AUTHOR 结合真实页面/口播场景判断，不要求机械清零。
5. Schema、source refs、数字、责任、状态、条件、边界和高置信语义完整性检查保持 fail-closed。

## 阶段 6：Packaging 与能力边界

状态：完成。

提交：

- `bb7d035` `build: package formal runtime modules and source extras`
- `6b2a180` `ci: add wheel installation smoke test`
- `65646d2` `test(build): enforce formal runtime packaging contract`

完成内容：

1. setuptools package discovery 从 `cyberppt* / script_engine*` 扩展到正式依赖的 `scripts*` runtime。
2. `Pillow` 变为显式基础依赖。
3. XLSX/MarkItDown 来源抽取能力进入 `source` optional extra：`openpyxl`、`markitdown`。
4. ImageGen style preset JSON 等运行时数据加入 package-data。
5. CI 新增 wheel build；在 `/tmp` 新建 venv，安装 wheel 后离开仓库目录导入 `cyberppt`、`script_engine`、ImageGen runtime、Quick runtime 和 presentation QA，防止 editable-install 偶然掩盖漏打包问题。

## 阶段 7：Input Identity 与 Run Identity 分离

状态：完成。

提交：

- `4ae2c24` `refactor(stage02): expose run identity separately from input identity`
- `fd06687` `docs(stage02): define input and run identity semantics`
- `52f4bda` `test(stage02): enforce input and run identity separation`

完成内容：

1. `input_fingerprint` 是时间无关、确定性的输入身份。
2. 历史 `build_id` 明确定义为一次执行/恢复的 run identity；`Stage02BuildContext.run_id` 提供语义明确的只读别名。
3. 兼容期保持 `run_id == build_id`，不破坏旧 `--build-id` 恢复命令。
4. 禁止用 build/run ID 判断两次输入是否等价；输入等价只看 fingerprint。

## 阶段 8：大模块条件性拆分

状态：条件性完成。

提交：

- `0cc543f` `chore(arch): add Stage 01 module growth budgets`
- `dc8c0be` `docs(arch): define behavior-preserving decomposition seams`
- `a3984fe` `test(arch): prevent renewed semantic module growth`

已执行的真实拆分：阶段 5 已将 subjective phrasing/Critic heuristics 从原 Hard lint 职责域抽出为 `script_engine/advisory_lint.py`。

风险控制：

1. 新增 `config/architecture_module_budgets.json`，大语义模块允许缩小；超过审核预算的增长必须同时给出拆分决策。
2. `docs/STAGE01_DECOMPOSITION_PLAN.md` 明确 `contracts.py`、`stage01_compiler.py`、`source_argument_model.py`、`visual_structure_contract.py` 的下一步拆分 seams。
3. 本轮同时发生 Style 可复现性、状态机、兼容 seam、lint 和 packaging 行为变化，因此不再同批搬迁 60–90KB 语义核心，避免回归原因混杂。
4. 后续物理拆分按 A→B→C→D 单独阶段/PR推进，保持行为和 Authority Map 不变。

## 阶段 9：Production Style Policy 收敛

状态：完成。

提交：

- `b3e3b7f` `refactor(style): distinguish production Style 09 from legacy choices`
- `5590b88` `docs(style): define single production style policy`
- `a2a85b9` `test(style): enforce Style 09 production policy`

完成内容：

1. 新增 `PRODUCTION_STYLE_ID = 9`，Style 09 是当前唯一正式 Stage 02 production style。
2. 历史 1–8 风格明确为 reference/experimental catalogue，不再解释为当前 production choices。
3. Style 09 frozen lock 声明 `production_style = true`、`production_style_id = 9`。
4. Style 09 正式生产不再声明需要独立样张人工确认；1–8 历史/参考流程仍可保留样张机制。
5. 新增 `docs/PRODUCTION_STYLE_POLICY.md`，规定未来重新开放多风格生产必须先完成 frozen contract、fingerprint、QA 和恢复规则。

## 阶段 10：仓库治理清理

状态：完成。

提交：

- `85c2502` 删除根目录 `out.txt`
- `ebf37c3` 删除 `tmp_p15_prompt_after.md`
- `5068aab` 删除 `tmp_source_text.txt`
- `6cd21a4`、`282d8d5`、`fad9793`、`ece4482`、`f15b70b`、`da7992e` 删除已提交的 `cyberppt.egg-info/` 构建元数据
- `ceb9087` `chore(repo): ignore generated metadata and root scratch files`
- `50990f2` `test(repo): lock generated-file ignore rules`

完成内容：

1. 清除根目录临时输出和来源提取 scratch。
2. 清除 editable install 产生并被误提交的 `cyberppt.egg-info/`。
3. `.gitignore` 新增 `*.egg-info/`、`.pytest_cache/`、coverage、wheel、`/out.txt`、`/tmp_*` 等规则。
4. 保留正式 `projects/**/script/dist/**` 权威脚本例外，不扩大忽略范围到有效项目产物。

## CI

Draft PR #24 已创建，GitHub Actions `CyberPPT tests` 随 PR commit 自动执行。

- Stage 4 首轮 CI：10 failed / 755 passed / 1 skipped / 2 deselected。失败集中在历史 `test_final_script_pages.py` 仍 patch 已废止的 facade seam，未发现需要恢复生产 monkey-patch 的证据。
- 已提交 `cea6f05` 将这些 pytest patch target 映射到真正 owning module。
- Stage 6 起 CI 额外执行 wheel build + outside-repository wheel smoke test。
- 当前最新 head 的 CI 正在运行；最终合并前必须 Python 3.10 / 3.12 两套 matrix 全绿，并通过 wheel smoke。

## 续跑规则

发生中断时：

1. 切换到 `agent/architecture-convergence-20260831`。
2. 查看本文档最后一个“完成”阶段或子阶段。
3. 从下一个阶段继续，不重做已提交阶段。
4. 每个阶段必须同时包含代码/文档变更与对应测试或静态契约检查。

## 重要约束

- 保留“脚本 → 完整图片 → 图转可编辑 PPT”的生产路线。
- 保留 Final Script 作为 Stage 02 唯一跨阶段业务输入。
- 保留 audited full image 作为 editable reconstruction 的视觉权威。
- 保留 SHA-256 provenance、逐页 checkpoint、OfficeCLI 真渲染 QA。
- 不在本轮引入第二套平行工作目录或审批文件体系。
