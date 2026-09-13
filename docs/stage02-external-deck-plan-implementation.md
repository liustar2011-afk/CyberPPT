# Stage 02 外部 Deck Plan 接入与验证

实现日期：2026-09-13。

## 交付结果

Stage 02 已支持通过 `--script <deck_plan.md> --external-script` 接收本次外部 Markdown 格式。保持原文件与既有页面顺序，通过原 final-script-pages 入口进行内容适配、关系判断、编译及后续生产。

本次实现完成代码与编译链路验证。未执行实际生图、PPTX 组装或视觉验收。

## 页面类型

| Page type 输入 | 页面模型 | 生产角色 |
| --- | --- | --- |
| content | content | content |
| template: cover | cover | cover |
| template: agenda / contents / toc | contents | agenda |
| template: transition / section / chapter | chapter | section |
| template: back-cover / closing / ending | closing | ending |

同时接受上述裸英文类型及封面、目录、目录页、过渡页、章节页、内容页、封底等中文别名。缺少类型的旧外部稿仍按 content 接收；显式空值或未知类型报错。Page Classification 保留为全稿说明，逐页 Page type 决定路由。Cover impact / Closing impact 不推断类型。模板页完整 Content 仍保存在输入中，后续沿用仓库现有模板生产合同。

## 字段消费

Title 映射页面标题，Content 独立映射正文，Core message 映射页面主旨。新增 part、audience_move、evidence、relationships、composition、rhythm、cover_impact、closing_impact、communication_contract 字段；其他加粗扩展字段存入 additional_fields。

字段同步进入 canonical intake、人工输入审阅稿与页面生产身份。主 Agent 关系判断读取来源说明和原始关系边界；内容页提示词在独立的不上屏区块读取新增上下文。Evidence 保持来源说明属性，不自动生成已核验 source_refs。Relationships 须对照正文核对，构图与节奏保持建议属性。字段中包含的操作指令不构成执行授权。

新增字段变化会使相关页面关系判断与复用身份失效；历史错误单页回退缓存须重新适配。输入完整性校验同时验证新增字段类型。

Reading Mode 的 balanced 保留原值，并明确标记用途未决。正式编译前需在页前声明 `> 交流方式：presented` 或 `> 交流方式：self_read`，也可在 Reading Mode 明确填写其中一种；冲突声明报错。此次代码测试使用测试材料中显式声明的 presented，用户真实材料保持原样。

## 真实文件验证

输入：[deck_plan.md](/Users/liuxing/.codex/worktrees/b42a/ppt-master/projects/power_data_cocreation_20260913/deck_plan.md)。

独立提取原文件的 12 个 Content 字段，与适配结果逐页比较，全部一致。解析结果如下：

| 页码 | 角色 | 标题 |
| --- | --- | --- |
| 01 | 封面 | 数据共享，场景共建 |
| 02 | 内容 | 数据基础设施建设正走向行业实践 |
| 03 | 内容 | 海量数据正在打开跨行业应用空间 |
| 04 | 内容 | 电力行业核心功能节点正在加速落地 |
| 05 | 内容 | 共建基础覆盖电力全产业链 |
| 06 | 内容 | 管理规则与服务实践推动数据用起来 |
| 07 | 内容 | 共建向全行业、跨领域伙伴开放 |
| 08 | 内容 | 五项行动把需求连接到创新成果 |
| 09 | 内容 | 从数据接入到产品封装，平台提供全链条支撑 |
| 10 | 内容 | 原始数据不出域，计算结果可输出 |
| 11 | 内容 | 带着数据、算法、需求或场景加入共建 |
| 12 | 封底 | 让数据在流通中创造价值 |

## 自动验证

使用仓库 `.venv/bin/python3` 执行：

```sh
.venv/bin/python3 -m pytest tests/test_stage02_*.py tests/test_external_deck_plan.py tests/test_relationship_judgment_v4.py -q
```

结果：184 passed。

覆盖：页码和正文边界、字段分流、多行正文、页面类型映射、保真项、错误页数与重复字段、未知类型、用途未决阻断、历史错误缓存重建、上下文变更失效、内部旧脚本回归。测试通过真正的 final-script-pages CLI 验证只编译入口、关系判断停点、提示词上下文、模板页与内容页分流及陈旧判断保护。另验证重建标题与最终文字 QA 消费端能读取末页类型与标题。

## 代码与合同

- [外部格式解析](/Volumes/DOC/CyberPPT/cyberppt/external_deck_plan.py)
- [页面字段模型](/Volumes/DOC/CyberPPT/cyberppt/script_quality/models.py)
- [Stage 02 适配入口](/Volumes/DOC/CyberPPT/cyberppt/stage02_script_adapter.py)
- [canonical intake 与字段身份](/Volumes/DOC/CyberPPT/cyberppt/stage02_input.py)
- [外部上下文编译](/Volumes/DOC/CyberPPT/cyberppt/external_page_context.py)
- [编译回归测试](/Volumes/DOC/CyberPPT/tests/test_external_deck_plan.py)
- [工作流合同](/Volumes/DOC/CyberPPT/docs/CYBERPPT_WORKFLOW.md)
- [Stage 02 Skill](/Volumes/DOC/CyberPPT/.agents/skills/cyberppt-stage02-editable-pptx/SKILL.md)

真实文件仍声明 balanced。开始制作该 PPT 时须明确主要交流用途，并沿用送图脚本审阅停点。引用原稿的事实正确性与最终 PPT 视觉效果不在此次代码兼容验证结果内。
