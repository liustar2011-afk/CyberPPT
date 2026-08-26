# Stage 01 生成稳定性增强设计

在现有 Source Truth、Outline、Script Audit 之上补充可执行输入包，不增加阶段。

1. `prepare-outline-input <project>`：输出章节使命、候选页面、证据、已消费关系和页面合同写作要求。
2. `prepare-page-script-input <project> [--page p10]`：按页输出唯一任务、证明点、允许证据、前页新增关系和后页保留内容。
3. `script-final.md`是唯一权威全稿；其他派生稿不得使用 final 命名。
4. `proof_points`增加 `consumption`，取值 `overview/primary/supporting`；每条证据最多一个 primary 页面。
5. 跨页检查覆盖全部前置页及非相邻页面，不局限于相邻且完全相同的证据集合。
6. 内容复核按内容页逐页记录四项决定和说明，并绑定脚本哈希。
7. Source Truth对复合语义单元给出可操作警告，不自动改写事实。
8. 输出简明页面质量表，展示页面任务、新增价值、主证据、重合风险和状态。

所有功能使用现有Python、JSON和Markdown，不调用外部服务。
