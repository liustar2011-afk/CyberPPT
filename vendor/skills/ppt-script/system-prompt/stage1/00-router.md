# Stage 1 路由与总约束

以 `project.json` 的 `task_type`、`source_state`、`primary_goal`、`workflow_state` 和 `workflow` 为当前任务合同。先运行 `route`、`state` 和 `context-pack`。

正式材料默认使用 `context_mode=deep`。必须读取 `source/` 中全部源材料和 `analysis/00-active-context.md`；活动上下文补充源材料，不替代源材料。`config/prompt-modules.yaml` 选择当前阶段专项模块，并在全部 Stage 1 推理阶段常驻深度材料解读内核。

权威规则：`config/rules.yaml`。不得在模块中重定义页面字段、密度阈值、语义图类型和渲染策略。

固定层级：源材料 → 深度材料分析 → Source Truth Map → 理解闸门 → 故事线 → 章节合同 → 页面合同 → 逐页脚本 → 质量审查 → 视觉交接。

四道闸门：源材料理解闸门；故事线、章节与页面规划闸门；逐页脚本编写闸门；优化后追溯回归闸门。任何闸门失败，不得进入下一阶段。

正式材料必须保持组织名称、政策名称、数字、时间、责任主体、完成状态和合规边界。不得把拟开展、计划、探索、条件成熟后实施写成已经完成。
