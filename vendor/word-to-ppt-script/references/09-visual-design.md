# 视觉结构设计

视觉设计的任务是把业务语义转换为空间语义。

## 页级视觉合同

每页必须明确：

- 页面角色；
- 核心判断；
- 决策关系（继承自Gate 4逻辑骨架，本阶段核对并空间化，不得重新判定，见`07-logic-and-parallelism.md`）；
- 视觉意图；
- 主视觉载体；
- 空间组织；
- 阅读路径；
- 关系编码；
- 文字嵌入方式；
- 行业实景锚点；
- 主次层级；
- 禁止事项。

## 单一视觉中心

主视觉必须承载页面核心判断。辅助说明依附于主链、节点或关系线，不形成第二个中心。

## 图文融合

- 文字应贴附业务对象和关系；
- 实景图应参与表达资源、场景、对象或结果；
- 禁止无关大图加旁边文字；
- 禁止把每个要点机械转成图标；
- 禁止默认左右图文两栏；
- 箭头方向与业务方向一致。

## 整套节奏

- 连续页面不得机械复用同一骨架；
- 章节页、判断页、架构页、流程页、商务页和收束页应有职能差异；
- 视觉差异来自内容关系，不来自随机装饰。


## Visual style separation

This stage outputs only the page-specific visual-structure contract. Do not copy reusable palette, typography, material, scene treatment or universal exclusions into every page. Those rules are injected from the repository-level `visual/ACTIVE-STYLE.md` during prompt assembly.

The page contract answers “what relationship is spatialized”; the active style answers “what visual language is used”.
