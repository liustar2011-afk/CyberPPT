---
name: chapter-structure-review
description: >-
  Review a finished chapter of PPT page scripts for intra-chapter flow, onscreen
  structure vs semantic diagram, cross-page redundancy, and prioritized edits.
  Use when the user asks for 章结构审阅、页面结构梳理、chapter structure review,
  or after a chapter's pages are drafted. Works in Codex and Cursor; output is
  repo markdown under review/, not Cursor Canvas.
---

# 章结构审阅（Codex / Cursor 共用）

## 何时启用

任一成立即启用本 Skill：

- 用户要求「章结构审阅 / 结构梳理 / chapter structure review」
- 某一章的 `pages/pNN-*.md` 已成批写出，需总览后再改
- 优化前需要跨页去重与语义图同构检查

本 Skill **不替代** `quality-check`；它做章级结构与表达逻辑对照。

## 平台差异（硬规则）

| 平台 | 权威交付物 |
|------|------------|
| **Codex** | 只写 `projects/<项目>/review/NN-<章次>-structure-review.md` |
| **Cursor** | **必须先写**同上 Markdown；可另做 Canvas 可视化，Canvas **不得**代替 Markdown，且不进 `assemble` |

禁止：只出 Cursor Canvas、不落仓库 `review/` 文件。

## 启动前

1. 确认项目名与章次（如第一章 = P01–P05）。
2. 读取：`decision/02-expression-logic.md`（或现行表达逻辑）、该章全部 `pages/pNN-*.md` 的**上屏文字 + 生图提示词 + 推荐主语义图类型**。
3. 可选：`python scripts/project_manager.py quality-check <项目>` 作机器侧参考，不替代本审阅。

## 审阅要点

1. **章内推进链**：是否符合工作逻辑（事实→条件→主体→缺口→摸底等），有无结论先行回潮。
2. **页使命唯一**：每页只推进一步；邻页是否抢戏。
3. **上屏阅读自洽**：不依赖讲解词能否读懂意图、模块关系与关键事实（`onscreen_text.reading_autonomous`）。
4. **上屏 ↔ 语义图同构**：声明的路径/汇聚/分层等是否与模块数、箭头、主辅关系一致。
5. **跨页重复带**：完整信息是否只在一页展开，邻页是否半行回指。
6. **密度与主次**：等权多块墙、辅助区口号占版、生图提示词是否发明上屏没有的字。

## 输出

1. 按 [`templates/chapter-structure-review.md`](templates/chapter-structure-review.md) 写审阅稿到 `review/`。
2. 在当轮回复给出总判 + 落地顺序 + **可点击** `file:///` 链接（遵守 `AGENTS.md` 交接规则）。
3. 若用户要求「按审阅改页」或仓库约定须消费：立即按落地顺序改 `pages/`，并写/更新 `review/*-structure-consume.md`（见 `AGENTS.md` Canvas/结构审阅消费链）。
4. 改页后跑 `notes-check`、`quality-check`。

## 与 ppt-script 主 Skill 的关系

- 主入口仍是 `.agents/skills/ppt-script/SKILL.md`。
- 模式名：`chapter-structure-review`（可在 ppt-script Modes 表中选用）。
- 生图交付仍以 `pages/` → `script-imagegen.md` 为准；本审阅只指导改页。
