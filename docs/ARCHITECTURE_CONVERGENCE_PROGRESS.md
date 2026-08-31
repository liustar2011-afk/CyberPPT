# CyberPPT 架构收敛当前状态

本文件是架构收敛工作的唯一当前入口。详细历史按阶段分卷保存，避免会话、Agent 或本地进程中断后出现“对话进度”和 GitHub 实际状态两套口径。

## 正式路线

保持以下生产路线不变：

`源材料 → 脚本 → 完整图片 → 图转可编辑 PPT → QA 交付`

架构收敛只处理权威模型、运行状态、依赖边界、兼容层、可复现性、质量门禁和可维护性，不改变上述生产路线。

## 当前结论

- 架构收敛里程碑已完成至 **Stage 76**，本轮收敛正式关闭。
- Stage 75 最后一项代码职责域收敛 checkpoint：`4a7f58a02e7220e7dbdd711357ef14566a3f26c0`，workflow run `33375703037` 五项全部 `success`。
- Stage 76 状态收口 implementation checkpoint：`acc79fd0ebc3f2a7f9c8e000688c3e9651cfa079`，workflow run `33376132351` 五项全部 `success`。
- 原架构收敛 backlog 当前没有未关闭的强制项。
- 后续不再按文件大小机械拆分模块。只有出现真实的多权威、运行时隐式 patch、compat facade 回长业务实现、跨职责耦合导致变更风险、打包/恢复/CI 边界回退时，才从 Stage 77 继续编号。

## 恢复入口

需要恢复工作时，按以下顺序读取：

1. `docs/ARCHITECTURE_CONVERGENCE_PROGRESS.md`：唯一当前状态与恢复规则。
2. `docs/ARCHITECTURE_CONVERGENCE_CHECKPOINTS_66PLUS.md`：最新阶段明细，覆盖 Stage 66–76。
3. `docs/ARCHITECTURE_CONVERGENCE_CHECKPOINTS_50PLUS.md`：Stage 50–65。
4. `docs/ARCHITECTURE_CONVERGENCE_CHECKPOINTS_30PLUS.md`：Stage 30–49。
5. `docs/ARCHITECTURE_CONVERGENCE_CHECKPOINTS_01_29.md`：Stage 1–29 历史归档。

任何恢复动作均以 GitHub `main` 的实际 commit 和对应 GitHub Actions 结果为准。只有同时满足“变更已进入 main、五项 CI 全绿、checkpoint 已记录”三个条件，才允许宣布某个 Stage 正式完成。

## 当前架构结果

### Stage 01：语义与脚本权威

- strict whole-document 单一可写语义权威为 `semantic-argument-model.json`。
- `source-truth.json` 为 deterministic projection。
- `script/foundation.json` 为 PLAN/AUTHOR 语义合同。
- `script/deck-plan.json` 负责章节、页序、页面使命和来源范围。
- `script/dist/final-script.md` 是 Stage 02 唯一跨阶段内容权威。
- `projects/AGENTS.md` 已与仓库正式流程统一。
- 详细规则见 `docs/CYBERPPT_AUTHORITY_MAP.md`。

### Stage 02：视觉、运行状态与恢复

- Style registry `scripts/imagegen_pipeline/style_presets/cyberppt_default_styles.json` 是可执行视觉合同唯一解析源。
- Style09 为 canonical production style；Style10 仅保留 legacy alias，不再形成第二套视觉权威。
- Style Lock 为 immutable snapshot；历史 pre-snapshot lock 只迁移一次。
- `input_fingerprint` 表达输入身份，`run_id/build_id` 表达执行身份。
- Manifest 恢复同时校验 input fingerprint 与 Prompt SHA；旧无 fingerprint 项目仅进入明确 legacy compatibility。
- `needs_svg_authoring`、`needs_visual_review` 等为正常 action state，并写入 manifest、回执和 `build_context.json`。
- Full image 审计通过后继续作为 editable reconstruction 的视觉权威。

### Compatibility seam

- Stage02 生产代码的 module-global monkey-patch 已清零。
- 历史 `LegacyPatchSet` 名称仅转换为显式 `Stage02Dependencies`，不再修改生产模块全局。
- Script Engine 的旧入口继续通过 thin compatibility facade 保持历史 import/API，但 facade 不再承载业务实现。

### Script Engine / QA

- `contracts.py`、`contract_rules.py` 已收敛为稳定 facade；schema、source trace、AUTHOR、full-copy、onscreen、delivery、structural 等规则均有 focused implementation。
- `cli.py` 已收敛为参数分发、stdout/stderr 与 exit-code 适配；parser、project scaffold/status、audit reports、Final Script delivery/quality 均迁入 focused modules。
- `source_index.py` 已收敛为 builder/render/write facade；阅读策略、legacy Word extract、v2 validation 均独立。
- deterministic finding 已正式区分 blocker/advisory；未知 finding 继续 fail-closed。

### Analysis Audits

- 原约 47.9KB `analysis_audits/final_script.py` 已收敛为 thin compatibility facade。
- Final Script 审计已拆为 authoring、lean、onscreen、deck 与 orchestrator focused domains，runtime 动态 rebinding 已删除。
- `final_authoring.py` 已进一步拆为 expression 与 structure 两个 focused domain，并降为 facade。
- 原约 21.9KB `common.py` 已拆为 `common_primitives.py` 与 `common_contracts.py`，自身降为 facade。
- 原约 12.6KB `composed_trace.py` 已拆为 trace core 与 Critic priorities 两个 focused domain，自身降为 facade。
- 所有上述迁移均保持 finding 文案、顺序、trace schema、历史公开对象与必要私有兼容属性。

### Packaging / CI

正式回归基线为五项 GitHub Actions：

1. Linux Python 3.10 全量 pytest + wheel repo 外 smoke。
2. Linux Python 3.12 全量 pytest + wheel repo 外 smoke。
3. macOS wheel smoke。
4. Windows wheel smoke。
5. OfficeCLI 真实 PPTX → HTML → Chromium PNG render smoke。

关键 runtime、Style09 registry/palette、动画预设、preset-shape、SVG Editor、references/contracts/assets 均进入 wheel 包边界。

## 原“尚未完成”事项的关闭情况

早期总进度文件曾列出三项待办，现均已关闭：

1. Creative brief、page manifest、no-visual-structure 中旧 Style09 精确字符串/标题断言：Stage 31–33 完成迁移。
2. `references/visual-system.md` 中旧象牙白说明及 Style10 定位：Stage 36 完成统一，Style10 明确为 compatibility alias。
3. LegacyPatchSet module-global patch、quality policy、wheel fixture 与 Office 集成 CI：Stage 37–45 完成，生产 module-global patch 清零，quality policy 与三平台/OfficeCLI CI 已接入。

随后 Stage 46–75 完成 Script Engine 与 analysis audit God Module 的职责域收敛，Stage 76 完成恢复权威与状态入口统一。因此，原架构收敛 backlog 当前没有未关闭的强制项。

## 退出准则与后续规则

本轮架构收敛在 Stage 76 正式关闭。后续开发遵循以下规则：

- 不新增第二套可写权威或第二套视觉执行权威。
- 不恢复生产 module-global monkey-patch。
- compatibility facade 只做显式转发，不承载新的业务实现。
- 新功能优先落入现有 focused domain；只有职责确实独立时再新增模块。
- 不以单文件大小作为拆分理由；以职责耦合、变更风险和测试边界作为判断依据。
- 每次架构级变更必须通过五项 CI；若重新开启架构收敛编号，从 Stage 77 开始。
