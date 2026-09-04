# Stage 02 外部脚本表达合同修正报告

日期：2026-09-04

## 技术判断

结论：`SUPPORT`

外部脚本通过 `--external-script` 保留输入身份、来源追溯、变更检测和续跑绑定。可见文案使用 `content-first-v1`，在完整上屏内容的事实边界内进行结论先行、层级重组与适度压缩。

## 修复内容

- 外部脚本与项目内脚本共用 `content-first-v1` 编译合同。
- 可见文字可改写、提炼、合并、拆分、重排和重设标题层级；业务对象、事实关系、数字、时间、范围、责任主体、条件、状态和结论力度保持准确。
- Style 09 提供视觉语言，页面任务、核心意思和语义关系共同支持结论先行的上屏表达。
- `external_script` 写入 source mode、输入指纹、manifest 和 build context。
- resume command 保留 `--external-script`。
- 同一 build 不跨不同 source mode 复用图片、文字审计或 Quick checkpoint。
- page manifest 将选定编译器传给逐页编译函数。

## 验证结果

- 外部脚本编排测试：通过。

## 未执行事项

本次未重新生成用户项目图片或 PPTX。
