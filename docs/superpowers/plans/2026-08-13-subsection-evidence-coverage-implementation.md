# 二级论点证据覆盖 Implementation Plan

**Goal:** 防止内容页以单条代表性来源替代原文二级标题的完整论证链。

**Architecture:** 候选编译将每个二级节点作为内容页主承载单元；Outline 审计使用 Source Truth 反向核验主二级节点的页面证据覆盖；一级核心章节继续由作者化章节页映射承载。

### Task 1: 候选编译保持二级节点边界

- [ ] 将 `cyberppt/stage01_compiler.py` 中首个二级节点与一级章节的合并逻辑改为 `primary_node_id=node_id`、`consumed_node_ids=[node_id]`。
- [ ] 将该节点的 disposition 固定为 `standalone_page`，由章节页承担一级目录映射。
- [ ] 更新 `tests/test_stage01_compiler.py`，断言内容页只主承载二级节点。

### Task 2: 增加页面级 Source Truth 覆盖审计

- [ ] 为 `audit_outline_consumption()` 增加可选 `source_truth` 参数。
- [ ] 对内容页的主二级节点，收集 Source Truth 中同节点、非 metadata 的记录；缺少任一记录时返回 `PAGE_SOURCE_SECTION_COVERAGE_INCOMPLETE`。
- [ ] 更新 `outline_contract.py` 和 `commands/outline_audit.py` 传入 Source Truth。
- [ ] 在 `tests/test_source_argument_model.py` 增加“单条代表性引用不能覆盖二级节点”失败测试。

### Task 3: 迁移并验证 V16 P04

- [ ] 将 P04 改为主承载 N002，引用 ST0006–ST0009，并按需求、供给障碍、回应路径重建内容单元。
- [ ] 运行 Outline 审计和定向测试；只在通过后重写 P04 页面稿。
