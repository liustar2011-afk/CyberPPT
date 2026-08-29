# Stage2 视觉设计改造持续断点

本文件是 Stage2 长流程开发的当前恢复点。每完成一个步骤立即更新；`STAGE2_VISUAL_DESIGN_REFACTOR_PROGRESS.md` 保留为历史实施记录，并在最终收口时同步。

## 当前状态

- Phase 0：完成。
- Phase 1：完成。
- Phase 2 Region Graph：完成。
- Phase 3 Visual Medium Policy：完成。
- Phase 4 Prompt 编译：完成。
- Phase 5 Full Image Deck Rhythm QA：进行中，P5.1 完成，下一步 P5.2。
- Phase 6 综合回归：未开始。

## 已完成关键提交

### Phase 2
- P2.1 Region Graph 合同 / Schema：`3bcf58e`、`b34bfc3`、`4953e9b`、`d2c677c`
- P2.2 topology → Region Graph：`ede6cbb`、`2d4e431`、`d4b4b2b`
- P2.3 exact text → Region binding：`cee53d4`、`6c6e522`、`fe5bc17`、`ff7296f`
- P2.4 Region Graph 审计：`43c6b5e`、`5b1b334`、`9de751b`
- P2.5 PageArtifactSpec / FinalPromptIR 投影：`d0d191f`

### Phase 3
- P3.1 Visual Medium Policy：`e32528f`、`435f6ea`、`e11648b`
- P3.2 medium / topology 解耦：`66fd606`
- P3.3 Skill / Schema / Audit / IR 权威化：`f69ba92`、`fcca149`、`3edba6f`

### Phase 4
- P4.1 Prompt 消费 Region Graph、阅读轴、focus、medium、文字归属：`731a99e`
- P4.2 ImageGen 微观视觉自由边界：`b03d7bb`
- P4.3 九类 topology Prompt 回归矩阵：`4be40ab`

### Phase 5
- P5.1 audited full-image contact sheet：`5414249`

## 当前恢复指令

从 P5.2 开始：建立实际成品图的页面视觉签名，至少记录构图骨架、视觉重心、密度等级、结构哈希和已审计 visual medium；不得使用 OCR 推断视觉结构。随后执行 P5.3 deck rhythm 检查、P5.4 接入 Stage2 manifest / QA receipt，并确保 deck-level QA 位于 `require_generated` 之后、`bind_reconstruction_visual_sources` 之前。
