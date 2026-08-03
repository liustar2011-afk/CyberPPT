# 项目文件结构

```text
<PROJECT_DIR>/
├── project.json
├── .ppt-script-skill-state.json
├── config/
│   └── project.yaml
├── source/
│   ├── original/
│   ├── source_blocks.json
│   ├── source_readable.md
│   └── chunks/
├── stages/
│   ├── 01_information_assets.json
│   ├── 02_page_plan.json
│   ├── 03_screen_copy.json
│   ├── 04_visual_plan.json
│   ├── 05_semantic_audit.json
│   └── chunks/
├── reports/
└── exports/
```

状态含义：

- `missing`：阶段文件不存在。
- `unlocked`：文件存在但尚未校验锁定。
- `current`：输入和输出哈希均与锁定记录一致。
- `dirty`：锁定后阶段文件被修改。
- `stale`：上游文件或项目配置在锁定后发生变化。
