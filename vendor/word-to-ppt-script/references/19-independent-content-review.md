# 19. 内容复核记录（建议项，不是第二道闸门）

`outline-audit` 和 `script-audit` 负责确定性检查；`approve-stage01` 是唯一的人工批准边界。小工具不得在两者之间再制造一套必须由独立 Agent、逐页 JSON 和哈希绑定共同满足的审批流程。

## 运行规则

- `outline-audit` 无阻断 issue 时返回 `passed`。
- `script-audit` 无 error 时返回 `passed`；warning 保留在 `quality_status=passed_with_warnings` 中供用户判断。
- `outline-content-review.json`、`content-review.json` 和 `content_review_status()` 可以继续记录编辑意见、页面问题和审阅来源，但其状态只作建议证据，不改变 Outline/Script 审计主状态。
- 用户运行或授权执行 `approve-stage01`，即表示用户已经看过当前确认稿并作出最终人工决定；不得在批准之后再次要求同内容复核。
- 章节结构审阅可以帮助发现跨页重复、双使命和视觉结构问题；项目若声明其为 required，则只保留这一套章节审阅，不再叠加独立内容复核硬门。

## 可记录的判断维度

大纲可记录单一使命、跨页重复和内容边界；讲稿可记录单一使命、模块同维、非必要信息剔除和跨页新增价值。这些字段用于说明问题和支持人工判断，不是机器自动否决用户批准的依据。

## 兼容性

旧项目已有的内容复核 JSON 保留读取和状态展示。`missing`、`stale`、`unverified`、`incomplete` 不再令零错误审计退回 `content_review_required`；新报告写入 `content_review_gate: advisory` 明确其非阻断性质。
