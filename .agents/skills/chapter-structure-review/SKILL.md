---
name: chapter-structure-review
description: >-
  Review a PPT chapter at the approved Outline gate or after page scripts are
  drafted. Use for 章结构审阅、页面结构梳理、chapter structure review、提纲章审、
  合并合理性、章内页序、跨页去重、页面使命检查，或在页面详细内容编写前预审
  Outline. At Outline stage review missions, sequence, merges, evidence duties,
  and future onscreen risks without inventing scripts; after drafting also review
  onscreen autonomy and semantic-diagram isomorphism. Output repo Markdown under
  review/ in Codex and Cursor; never replace it with Cursor Canvas.
---

# 章结构审阅（Codex / Cursor 共用）

## 输入阶段

先判断当前权威输入：

- **Outline 预审**：尚未写页面稿。审阅章内问题链、单页使命、合并依据、页序、证据职责、跨页边界与后续上屏风险。不得虚构上屏文字、生图提示词或语义图。
- **页面脚本章审**：页面稿已经存在。除上述项目外，继续审阅上屏自洽、上屏与语义图同构、视觉载体和跨页重复。

本 Skill **不替代** `quality-check`；它做章级结构与表达逻辑对照。

## 平台差异（硬规则）

| 平台 | 权威交付物 |
|------|------------|
| **Codex** | 只写 `projects/<项目>/review/NN-<章次>-structure-review.md` |
| **Cursor** | **必须先写**同上 Markdown；可另做 Canvas 可视化，Canvas **不得**代替 Markdown，且不进 `assemble` |

禁止：只出 Cursor Canvas、不落仓库 `review/` 文件。

## 启动前

1. 读取适用 `AGENTS.md`，确认项目、章次、权威阶段与页范围。
2. Outline 预审读取当前权威 Outline、语义理解/Source Truth 中目标章证据、用户已确认的结构决定及相邻章合同。
3. 页面脚本章审另读取现行表达逻辑和该章全部页面稿中的完整稿、上屏文字、视觉结构、生图提示词和推荐主语义图类型；不存在的字段必须标为未检查。
4. 可选运行仓库现有质量命令作为机器侧参考，不替代本审阅，也不得为了审阅跨越当前人工门。

## 审阅要点

1. **章内推进链**：是否符合工作逻辑（事实→条件→主体→缺口→摸底等），有无结论先行回潮。
2. **页使命唯一**：每页只推进一步；邻页是否抢戏。
3. **上屏阅读自洽**：仅在已有页面稿时检查；Outline 预审改为检查哪些结构性前提、驱动、结果、缺口、回应和边界必须在后续上屏可见。
4. **上屏 ↔ 语义图同构**：仅在已有页面稿时作实审；Outline 预审只建议与页面主关系一致的候选结构，不得当成已经完成的视觉设计。
5. **跨页重复带**：完整信息是否只在一页展开，邻页是否半行回指。
6. **密度与主次**：等权多块墙、辅助区口号占版、生图提示词是否发明上屏没有的字。

## 输出

1. 按 [`templates/chapter-structure-review.md`](templates/chapter-structure-review.md) 写审阅稿到 `review/NN-<章次>-structure-review.md`，在元数据中明确 `Outline 预审` 或 `页面脚本章审`。
2. 在当轮回复给出总判 + 落地顺序 + **可点击** `file:///` 链接（遵守 `AGENTS.md` 交接规则）。
3. 若用户要求消费审阅：Outline 阶段只修改权威 Outline 及确有必要的上游语义关系；页面脚本阶段按落地顺序修改页面稿。不得以审阅稿替代权威产物。
4. 消费后写/更新 `review/*-structure-consume.md`，运行当前阶段正式检查；只有页面稿已存在时才运行页面脚本 `notes-check` / `quality-check`。

## 与 ppt-script 主 Skill 的关系

- 主入口仍是 `.agents/skills/ppt-script/SKILL.md`。
- 模式名：`chapter-structure-review`（可在 ppt-script Modes 表中选用）。
- 生图交付仍以 `pages/` → `script-imagegen.md` 为准；本审阅只指导改页。
