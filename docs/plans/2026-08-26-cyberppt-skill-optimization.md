# CyberPPT 多 Skill 优化分析与开发计划

## 结论

独立技术判断：`SUPPORT WITH CONDITIONS`。

流程中的 Skill 需要局部完善，整体重写缺少证据。当前项目已经证明语义理解、提纲规划和 Handoff 的核心业务契约有效；单页写作与 Stage 02 authored SVG 续跑存在明确的可执行性缺口；正式命令示例还需统一使用仓库 `.venv`。

本轮采用窄修复：保留已验证的业务规则，修复命令、发现描述、续跑说明和失效样例，并增加契约测试。

## 证据范围

本次抽查了六个仓库项目目录及相关 Git 演进记录，重点证据如下：

| 证据 | 已验证事实 | 对 Skill 的判断 |
|---|---|---|
| `projects/ai_power_training_business_feasibility` | 280 条原子事实完成语义承接；`semantic-report.status=ok`；Outline 的结构、来源、作者化和 Handoff 门禁均通过；CyberPPT runtime audit 通过 | `business-semantic-understanding`、`ppt-outline-planning`、`cyberppt-handoff` 的核心契约有效 |
| `projects/power-data-infrastructure-cooperation-v16-20260815-foundation` | Handoff 投影通过，runtime validation 未运行；后续 Outline audit 仍为 `rewrite_required` | 投影校验与运行时校验必须分开，现有 Handoff Skill 已保留该边界 |
| `projects/ai-power-education-training-business-feasibility-20260822` | 最终脚本审计仍有上屏密度、内容单元覆盖和完整稿映射错误 | 单页 Skill 需要保持写前约束，同时应消除自身命令矛盾和失效样例 |
| `projects/power-industry-data-infrastructure-stage02-20260825` | 当前 24 个内容页均已生成并通过 full 图文字审计，editable 分支统一停在 `requires a hand-authored SVG from the image-to-PPTX runtime` | Stage 02 Skill 缺少从 active manifest 进入作者化、登记策略和原位续跑的完整操作合同 |
| `projects/power-data-infrastructure-cooperation-stage02-20260824` | 16 个内容页出现同一 authored SVG 停点 | 该问题具有跨项目重复性 |
| `projects/ai-power-education-training-business-feasibility-20260822` 的成功批次 | 13 页具备真实 `authoring_svg`、完整 `graphic_text_policy`、clean base 和 Quick 产物 | authored SVG 续跑路径可行，适合沉淀为 Stage 02 参考流程 |

## 独立技术判断

### 目标

提高多 Skill 流程的准确路由、可执行性、可恢复性和跨机器一致性。

### 待验证方案

根据历史和当前项目表现，判断流程所引用的 Skill 是否需要整体优化，并在有证据时开发落地。

### 反例

当前 AI+电力教育培训项目已经完成语义、Outline、Handoff 和 runtime audit 全链通过。若整体重写这些 Skill，回归风险高于可见收益。V16 项目的失败还显示 Handoff Skill 对 runtime 未运行的区分是必要门禁，该规则应继续保留。

### 替代方案

采用基于证据的窄修复：

- 业务语义、提纲作者化和确定性投影规则保持现状。
- 所有正式命令统一到仓库 `.venv/bin/python3`。
- 单页 Skill 修复 CLI 矛盾，删除失效历史路径，将枚举压缩细节下沉到参考文档。
- Stage 02 Skill 扩展发现描述，补充 authored SVG active-build 续跑参考。
- 契约测试锁定上述不变量。

### 最终判断

`SUPPORT WITH CONDITIONS`。支持优化和开发；条件为限制修改范围，不调整已有通过证据支持的语义、Outline 和 Handoff 业务模型。

## Skill 逐项结论

| Skill | 判断 | 本轮处理 |
|---|---|---|
| `cyberppt-workflow` | `SUPPORT` | 保持导航职责；主流程中的正式命令改用仓库 `.venv` |
| `source-to-markdown` | `SUPPORT WITH CONDITIONS` | 保留转换规则；命令和 usage 统一到仓库 `.venv` |
| `source-structure-factbase` | `SUPPORT WITH CONDITIONS` | 保留确定性解析边界；命令统一到仓库 `.venv` |
| `business-semantic-understanding` | `SUPPORT WITH CONDITIONS` | 业务语义规则保持现状；命令统一到仓库 `.venv` |
| `ppt-outline-planning` | `SUPPORT WITH CONDITIONS` | 作者化和消费契约保持现状；命令统一到仓库 `.venv` |
| `cyberppt-handoff` | `SUPPORT WITH CONDITIONS` | 投影与 runtime 双层验证保持现状；命令统一到仓库 `.venv` |
| `cyberppt-write-single-page` | `SUPPORT WITH CONDITIONS` | 修复 `--lightweight` 自相矛盾、失效历史样例和入口过载；补充枚举压缩参考 |
| `cyberppt-stage02-editable-pptx` | `SUPPORT WITH CONDITIONS` | 扩展 editable、image、both 路由发现；补充 authored SVG active-build 续跑合同；同步 UI 元数据 |
| `independent-technical-judgment` | `SUPPORT` | 本轮已按其 Goal、Evidence、Counter-case、Alternative、Verdict 门禁执行，无需修改 |

## 开发计划与状态

| 阶段 | 内容 | 状态 |
|---|---|---|
| 证据盘点 | 抽查历史/当前项目的 semantic、Outline、Handoff、script audit、visual audit 和 manifest | 已完成 |
| 独立判断 | 验证整体重写反例，确定窄修复范围 | 已完成 |
| Skill 开发 | 统一 Python 运行时；修复单页合同；新增 authored SVG 续跑参考；同步 Stage 02 元数据 | 已完成 |
| 契约测试 | 增加虚拟环境命令、单页 CLI/样例、Stage 02 路由与续跑不变量 | 已完成 |
| 验证 | Skill 快速校验、CLI help、定向 pytest、工作区边界检查 | 已完成 |

## 已落地修改

1. 正式链八个 Skill 及主流程文档的命令示例统一使用仓库 `.venv/bin/python3`。
2. 单页 Skill 删除统一追加 `--lightweight` 的错误指令，命令与当前 CLI 对齐。
3. 单页格式参考删除仓库中缺失的 v12 项目路径，格式依据调整为当前模板、当前项目脚本和当前审计。
4. 枚举压缩规则从 Skill 入口的单一事故叙述收敛为通用规则，并下沉到参考文档。
5. Stage 02 Skill 的 frontmatter 和 UI 元数据覆盖 editable、picture、dual delivery 三类请求。
6. 新增 authored SVG 续跑参考，明确 active build、manifest、SVG、`graphic_text_policy`、clean base、原命令续跑和逐页视觉回执。
7. 新增 3 组 Skill 契约测试，覆盖运行时、单页可移植性和 Stage 02 续跑合同。

## 验证结果

- 8 个修改后的 Skill 均通过 `quick_validate.py`。
- `page-preflight`、`page-lint`、`script-audit`、`final-script-pages`、`review-quick-page` 的仓库 `.venv` CLI help 均通过。
- Source Foundation、Markdown 转换、结构解析、语义、Outline 和 Handoff 文档中的命令均完成真实 `--help` 解析。
- `tests/test_skill_contract.py`：31 项通过。
- Stage 02 manifest/Quick 定向测试：2 项通过。
- 附加的 `test_production_build_propagates_authored_svg_build_failure` 在 authored SVG 分支前被当前工作区已有的 `CONTENT_STRUCTURE_MISSING` handoff 门禁阻断；本轮未修改相关生产代码或测试夹具。
- `git diff --check` 通过。

## 剩余风险

- Stage 02 authored SVG 仍需要主 Agent 逐页完成真实视觉作者化；参考文档提升续跑可执行性，无法替代视觉判断。
- 当前工作区另有脚本审计相关未提交改动。本轮未覆盖、删除或回退这些文件。
- `CONTENT_STRUCTURE_MISSING` 的既有定向测试问题建议在当前脚本审计改动稳定后单独处理，避免与 Skill 优化混合。
