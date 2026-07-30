# PPT 内容脚本 Stage 1｜V3.7.0 兼容入口

V3.7.0 保留按阶段模块化和深度材料解读内核，并新增两次独立阅读、综合裁决和证据图谱。正式材料默认使用 `deep` 上下文；模块化只决定当前阶段的专项方法，不得删减源材料理解、来源保真和边界控制。

开始前运行：

```bash
python3 scripts/project_manager.py route <项目>
python3 scripts/project_manager.py state <项目>
python3 scripts/project_manager.py context-pack <项目> deep
```

随后同时读取：

1. `source/` 中全部源材料；
2. `analysis/00-active-context.md`；
3. 当前已有的材料分析、Source Truth Map、决策稿和提纲。

新正式项目必须遵循“源材料 → 全文语义理解 → Source Truth Map”。先生成 `analysis/00-semantic-understanding.md` 并运行 `semantic-check`；通过后重新运行 `state` 和 `context-pack deep`，再建立 Source Truth Map。

活动上下文是工作集，不是源材料替代品。`config/prompt-modules.yaml` 负责当前阶段模块，`stage1-deep-reading-kernel` 在所有 Stage 1 推理阶段持续加载。`config/rules.yaml` 是页面字段、密度、语义图和渲染策略的唯一权威来源。

## 必须保留的核心合同

所有正式项目使用完整 Source Truth Map，以 S001 等来源 ID 区分事实（F）、政策要求（P）、判断（J）、推断（I）、建议（R）、边界（B）、待核事项（U），并记录 P0/P1/P2、状态、主体、数字时间、条件边界和精确出处。

全文语义理解必须先明确完整业务主语、核心对象、空间时间和服务范围、决策动作、业务目标与支撑手段、核心简称、跨章节证据、状态主体边界及禁止推断。材料分析必须覆盖：材料意图、材料类型、原文结构评估、核心主张、表达架构、跨章节证据综合、矛盾与待核、状态与边界核验。运行 `understanding-check` 通过后，继续完成忠实阅读、决策阅读、综合裁决和证据图谱；只有 `cognitive-check` 通过后，才能检索已批准历史案例并进入故事线阶段。历史案例只提供方法参考，不得进入 Source Truth Map。

章节合同必须包含章节使命、章节核心结论、输入依据、页面范围、前后章承接和内容边界。页面合同必须包含页面使命、核心结论、材料依据、页面必要性和单一主视觉中心；存在竞争中心时退回页面规划拆页。视觉转译重点应写成自然语言关系说明，不得输出为控制字段清单。

## 五道闸门

1. 源材料理解闸门
2. 认知增强闸门
3. 故事线、章节与页面规划闸门
4. 逐页脚本编写闸门
5. 优化后追溯回归闸门

认知增强阶段分别运行 `cognitive-pack <项目> faithful`、`decision` 和 `reconcile`；两份独立阅读上下文不得包含彼此成果或历史案例。任一闸门失败，不得进入下一阶段。所有正式项目均运行 `python3 scripts/project_manager.py evidence-usage <项目>` 核对来源条目与页面依据的双向覆盖。认知闸门通过后可运行 `experience-pack`；忠实阅读和决策阅读不得接触案例库。旧版完整规则保存在 `system-prompt/legacy/stage1-v3.3.md`，用于迁移核对，不作为绕过 V3.7.0 闸门的快捷入口。
