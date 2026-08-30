# CyberPPT Production Style Policy

## 正式 Stage 02

当前唯一正式生产视觉风格为 `Style 09`（纯白 + 深蓝领导汇报）。

`final-script-pages --production-build`：

- 未传锁时自动创建 Style 09 frozen lock；
- 传入锁时只接受 Style 09；
- 不在正式生产入口展示 1–8 的风格选择；
- 不设置独立的风格人工确认停点；
- 后续 Prompt、full image、重建和 QA 全部消费同一份冻结锁。

## 1–8 风格库

历史 1–8 风格继续保留，作为：

- 参考/实验风格目录；
- 历史项目兼容数据；
- 未来重新开放多风格生产时的候选资产。

它们不构成当前 Stage 02 正式生产路由。

`default_style_choices()` 因兼容历史工具仍返回 1–8，这个函数的含义是 reference catalogue，不代表 production choices。

## Lock policy

Style 09 lock 必须声明：

- `policy.production_style = true`；
- `policy.production_style_id = 9`；
- `policy.samples_are_required_for_user_confirmation = false`；
- `policy.runtime_contract_refresh_forbidden = true`；
- resolved prompt contract 及其 SHA-256 已冻结在锁内。

旧锁缺少 frozen contract 时不得自动刷新，必须重新创建。

## 重新开放多风格生产的条件

未来若要让 1–8 或其他 style 进入正式生产，需要作为独立 feature 完成：

1. 每种风格有可冻结 contract；
2. 正式样张和参考图来源可审计；
3. input fingerprint 纳入 resolved contract；
4. Style QA 有对应测试；
5. 明确恢复/失效规则；
6. 更新 Stage 02 routing 后才可将其列为 production choice。

在此之前，文档中的“8 种风格”均应理解为风格资产库，不应与当前 Style 09 正式生产入口混用。
