# Script Quality Issue Taxonomy

本表冻结当前脚本质量体系中与本阶段叙事增强直接相关的稳定 code。完整运行时仍保留现有消费者和历史 code；新增规则不得用近义 code 重复表达同一问题。

| code | owner | 阶段 | 作用域 | 默认等级 | 阻断 | 证据 | 建议动作 |
|---|---|---|---|---|---|---|---|
| `NARRATIVE_PAGE_CHAPTER_MISMATCH` | `script_engine.analysis_audits.deck_plan` | PLAN | 页/章节 | error | 是 | `page.chapter_id` 与章节集合 | 修正页面归属或补齐已批准章节 |
| `NARRATIVE_PAGE_CHAPTER_ORDER_CONFLICT` | `script_engine.analysis_audits.deck_plan` | PLAN | 整稿 | error | 是 | 页面章节序列与章节序列 | 恢复来源顺序或记录授权重组 |
| `NARRATIVE_CHAPTER_ID_DUPLICATE` | `script_engine.analysis_audits.deck_plan` | PLAN | 章节 | error | 是 | 章节 ID 集合 | 为每章分配稳定唯一 ID |
| `NARRATIVE_PLAN_FIELDS_INCOMPLETE` | `script_engine.analysis_audits.deck_plan` | PLAN | 整稿 | warning | 否 | 缺失 thesis/arc/storyline | 从已确认规划补齐叙事字段 |
| `NARRATIVE_CHAPTER_FIELDS_INCOMPLETE` | `script_engine.analysis_audits.deck_plan` | PLAN | 章节 | warning | 否 | purpose/question/message/handoff | 完成章节使命、问题、结论和承接 |
| `NARRATIVE_PAGE_HANDOFF_MISSING` | `script_engine.analysis_audits.deck_plan` | PLAN | 页/跨页 | warning | 否 | 缺失 receives/next | 补充页面接收点和后续去向 |
| `NARRATIVE_NEXT_RECEIVES_CONFLICT` | `script_engine.analysis_audits.deck_plan` | PLAN | 跨页 | warning | 否 | `next` 与下一页 question 的显式文本 | 对齐承接表达与下一页问题 |
| `NARRATIVE_TITLE_MESSAGE_OBJECT_MISMATCH` | `script_engine.analysis_audits.deck_plan` | PLAN | 页内 | warning | 否 | 标题与核心判断无共同对象词 | 检查标题是否覆盖页面实际判断 |
| `NARRATIVE_CHAPTER_MESSAGE_UNSUPPORTED` | `script_engine.analysis_audits.deck_plan` | PLAN | 章节 | warning | 否 | 章节 message 与所属页 message 集合 | 收窄章节结论或补足页面支撑 |
| `ADJACENT_PLAN_MESSAGE_DUPLICATE` | `script_engine.analysis_audits.deck_plan` | PLAN | 跨页 | warning | 否 | 相邻页 message 相似度 | 保留一个判断并让相邻页推进不同问题 |
| `ADJACENT_PAGE_RESPONSIBILITY_DUPLICATE` | `cyberppt.script_quality.relationships` | AUTHOR | 跨页 | error | 是 | 页面关系摘要与职责相似度 | 合并职责或改写相邻页推进关系 |
| `ADJACENT_MAIN_MESSAGE_DUPLICATE` | `cyberppt.script_quality.audit` | AUTHOR | 跨页 | error | 是 | 相邻页主判断相似度 | 让后页推进新的业务问题 |
| `PAGE_SCOPE_PREEMPTED` | `cyberppt.script_quality.relationships` | AUTHOR | 跨页 | error | 是 | 后页保留范围命中 | 移除当前页抢占内容 |
| `DECLARED_RELATION_NOT_VISIBLE` | `cyberppt.script_quality.relationships` | AUTHOR/Stage 02 | 页内 | warning | 否 | 声明关系与可见承载 | 补充经批准的关系载体 |

等级仍限于 `error` 和 `warning`。`NARRATIVE_*` 语义判断首期采用 warning-first；Schema、来源、事实强度和显式引用错误继续按现有 error 规则阻断对应阶段。`evidence` 与 `suggested_action` 是 Script Quality issue 的最小可审计信息；Deck Plan audit 的兼容文本以 `code: ...; evidence=...; suggested_action=...` 形式携带同等信息。
