# CyberPPT 架构收敛恢复点（阶段 50+）

本文件续接 `docs/ARCHITECTURE_CONVERGENCE_CHECKPOINTS_30PLUS.md`。继续执行“每完成一个小阶段立即提交并记录恢复点”。

| 阶段 | Commit | 内容 |
|---|---|---|
| 50 | `bccc2e022c2a3da2c63c1ea5214c4b6dc7a8940f` | 将 banned-phrasing 读取、Final Script 全字段遍历和 `lint_final_script` 组合器迁入 `lint_contracts.py`；主 CLI/quality policy 继续通过 `contracts` facade 调用，AUTHOR/full-copy/onscreen 子检查暂时由旧 `contract_rules.py` 提供。实现提交：`faebb81`、`7765133`、`bccc2e0` |
| 51 | `f8f8b81ef2412106cf6b5a451fac7fdc4d3974b7` | 新增共享 `semantic_text_primitives.py`，并将 mission/argument/visual_thesis/relationships/speaker_notes 的 AUTHOR supporting-field 机械合同迁入 `author_contracts.py`；`lint_contracts` 与 `contracts` facade 已切换到 focused implementation。实现提交：`2612508`、`bc4f33f`、`555980e`、`6f90f91`、`f8f8b81` |
| 52 | `b1812c48ad5f3096c043f0480c95acf31f1ecc9a` | 将 full-copy 段落结构、段首语义完整性和显式并列分支子结论三类检查迁入 `full_copy_contracts.py`，复用共享 semantic text primitives；`lint_contracts` 与 `contracts` facade 已切换到 focused implementation，并以架构测试锁定公共出口。实现提交：`2204cdc`、`9c56549`、`5cdc4d3`、`b1812c4` |
| 53 | `bf016b2065ca0a62e16afa64a5ed80e744bd82ff` | 将 onscreen 标题语义、细项语义、证据层、层级标点、代码自解释和 core_message 可见投影六类检查迁入 `onscreen_contracts.py`，统一复用共享 semantic text primitives；`lint_contracts` 与 `contracts` facade 已切换到 focused implementation，并以架构测试锁定公共出口。实现提交：`eaa179f`、`c33ea96`、`69f9ec2`、`bf016b2` |
| 54 | `806ff5cc805b068ed3b204ea6137115583debb9f` | 移除 `contracts.py` 对 `contract_rules.py` 的运行时 wildcard fallback；正式 facade 仅显式导出 focused modules，旧 `contract_rules.py` 暂保留供直接历史 import 兼容，并新增静态门禁禁止 legacy fallback 回流。实现提交：`d7dc8ba`、`806ff5c` |
| 55 | `d5c478fdfd2f2856d655dfb741e32d69c0c790dd` | 将约 52KB 的旧 `contract_rules.py` 收缩为实现为空的历史兼容 facade，全部公开符号直接转发 `contracts.py`；新增身份级回归测试，保证 legacy import 与正式 facade 使用同一对象并禁止旧规则实现重新长回。实现提交：`17d67da`、`d5c478f` |
| 56 | `0fbb81aa7724e86da139d3df83d42aedcd2c0325` | 新增 `final_quality.py` 作为 Final Script 确定性质量评估的 focused composition boundary，集中组合 language/structure/full-copy/speaker-notes/delivery-cleanliness/terminal-punctuation/detail-length 检查及 blocker/advisory policy；`cli.py` 保留 `_final_lint_issues` monkeypatch seam 并将 lint/status/render/check-sync 四条路径路由到 focused evaluator。实现提交：`b9a7a59`、`c0d6ac1`、`0fbb81a` |
| 57 | `dfdadc3bc25f35bb804aebb32b981e8d78ec9b8b` | 将 `new-project` 的 slug 规则、目录树创建和非权威产物 `.gitignore` 模板迁入 `project_scaffold.py`；CLI 仅保留异常/成功结果到既有 JSON 输出和退出码的适配，并以架构测试禁止脚手架常量与文件系统实现回流。实现提交：`8e21ae7`、`ea2ff31`、`dfdadc3` |
| 58 | `1afd0fe944bb03ca09270b0d275254eb8d0bd081` | 将 `status` 的项目布局识别、artifact 校验、Foundation/PLAN/Final 审计、source-index 状态和阶段判定迁入 `project_status.py`；CLI 仅打印 focused evaluator 返回的既有 JSON，并通过 callback 保留 `_final_lint_issues` 动态 monkeypatch 兼容及 profile resolver 身份。实现提交：`e222eef`、`ba1c08f`、`1afd0fe` |
| 59 | `26506bbc690ed63557d8d7d5d49c3d66bad39344` | 将完整 argparse 命令树、帮助文本、choices、默认值和参数定义迁入 `cli_parser.py`；保留 `cli.build_parser()` 兼容入口，仅向 focused parser schema 传递现有 validation kinds，并以架构测试禁止 argparse 配置回流。实现提交：`8bdf0e2`、`86102f4`、`26506bb` |
| 60 | `b5e1c1fabd538df39c8e9adf00a38f8b418c2ce0` | 新增 `audit_reports.py`，集中构造 validate、Foundation/PLAN/Final 审计、plan review、composed trace、source refs 和 source-index build 八类命令结果；CLI handler 统一降为“调用 focused builder → 输出 → 返回 exit code”，并移除对 `analysis_audit`、`composed_trace`、`plan_review`、`source_index` 的直接报告组装依赖。实现提交：`1857734`、`4bafe85`、`b5e1c1f` |

## 验证记录

- 阶段 50 workflow run `33362154737`：五个 job 全部 `success`。Linux Python3.10/3.12 全量 pytest、wheel repo 外 smoke、OfficeCLI 真实渲染、macOS/Windows wheel smoke均通过；`lint_final_script` 调度迁移后 banned-phrasing 命中、severity policy 和 CLI 退出语义保持兼容。
- 阶段 51 workflow run `33362447591`：五个 job 全部 `success`。AUTHOR supporting-field 迁移后全量测试、三平台 wheel smoke 与 OfficeCLI 真实渲染均通过；`AUTHOR_MISSION_GENERIC`、`AUTHOR_VISUAL_THESIS_NONRELATIONAL`、`AUTHOR_VISUAL_TOPOLOGY_CONFLICT` 的 advisory 分类保持原行为。
- 阶段 52 workflow run `33362901587`：五个 job 全部 `success`。Linux Python3.10/3.12 全量 pytest、wheel repo 外 smoke、OfficeCLI 真实渲染、macOS/Windows wheel smoke均通过；full-copy focused module、lint 调度和 facade 公共导出切换后保持现有 deterministic finding 与退出语义兼容。
- 阶段 53 workflow run `33363190081`：五个 job 全部 `success`。Linux Python3.10/3.12 全量 pytest、wheel repo 外 smoke、OfficeCLI 真实渲染、macOS/Windows wheel smoke均通过；onscreen focused module、lint 调度和 facade 公共导出切换后保持现有 deterministic finding 与退出语义兼容。
- 阶段 54 workflow run `33363394820`：五个 job 全部 `success`。Linux Python3.10/3.12 全量 pytest、wheel repo 外 smoke、OfficeCLI 真实渲染、macOS/Windows wheel smoke均通过；production `contracts.py` 已不再 import 或 wildcard-reexport `contract_rules.py`，focused facade 成为唯一正式公共出口。
- 阶段 55 workflow run `33365229408`：五个 job 全部 `success`。Linux Python3.10/3.12 全量 pytest、wheel repo 外 smoke、OfficeCLI 真实渲染、macOS/Windows wheel smoke均通过；legacy `contract_rules.py` 仅剩 thin facade，历史直接 import 仍保持与正式 `contracts.py` 相同的公开 API 身份。
- 阶段 56 workflow run `33365693202`：五个 job 全部 `success`。Linux Python3.10/3.12 全量 pytest、wheel repo 外 smoke、OfficeCLI 真实渲染、macOS/Windows wheel smoke均通过；Final Script quality composition 从 `cli.py` 迁出后，既有 advisory/blocker 分类、CLI 退出语义及测试 monkeypatch seam 保持兼容。
- 阶段 57 workflow run `33365981529`：五个 job 全部 `success`。Linux Python3.10/3.12 全量 pytest、wheel repo 外 smoke、OfficeCLI 真实渲染、macOS/Windows wheel smoke均通过；`new-project` 抽取后非法 slug、重复目录、目录结构、JSON 输出和退出码保持兼容。
- 阶段 58 workflow run `33366336229`：五个 job 全部 `success`。Linux Python3.10/3.12 全量 pytest、wheel repo 外 smoke、OfficeCLI 真实渲染、macOS/Windows wheel smoke均通过；`status` 抽取后既有 JSON 字段、中文阶段文案、strict/legacy profile 分支、source-index 行为、advisory monkeypatch 与退出码保持兼容。
- 阶段 59 workflow run `33366643152`：五个 job 全部 `success`。Linux Python3.10/3.12 全量 pytest、wheel repo 外 smoke、OfficeCLI 真实渲染、macOS/Windows wheel smoke均通过；parser schema 抽取后全部子命令名称、help、choices、默认值、必填参数、原 `cli.build_parser()` 入口和 CLI 分发行为保持兼容。
- 阶段 60 workflow run `33367035037`：五个 job 全部 `success`。Linux Python3.10/3.12 全量 pytest、wheel repo 外 smoke、OfficeCLI 真实渲染、macOS/Windows wheel smoke均通过；八类审计/追溯命令迁入 focused report builders 后，报告字段、plan review 文本、source-index 产出路径、退出码及 CLI 分发行为保持兼容。
