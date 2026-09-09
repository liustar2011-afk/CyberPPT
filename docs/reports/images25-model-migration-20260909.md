# Stage 02 默认生图模型升级实施记录

日期：2026年9月9日。

## 已落实行为

- 新建 Stage 02 批次默认请求 `gpt-image-2.5-sunburst`，默认值统一来自现有 OAuth 生图适配器。
- CLI 和函数入口省略模型时，在生产预检后、写入 manifest 前解析实际请求参数。
- 同批次省略模型续跑时，依次读取原 manifest 或 build context 的 `input_identity.image_model`，保留原模型。
- 继续支持显式 `--image-model gpt-image-2` 等覆盖参数。恢复命令保存解析后的模型。用户显式改变模型时，继续执行现有输入身份和图片复用校验。
- 历史批次缺少模型记录时，要求依据原请求显式指定模型，避免猜测其来源。
- 请求回执保留兼容字段 `model`，增加 `requested_model`、`actual_model: null` 和 `model_verification: unknown_backend_model_not_captured`。实际模型证据当前未由后端适配器捕获，回执明确标记未知。
- Stage 02 技能说明已同步。风格、提示词和下游重建逻辑保持现有实现。

## 验证

相关回归：**56 passed**。包含新默认、显式旧模型、manifest/context 模型恢复、历史缺失元数据、正式函数入口 dry-run、请求回执、恢复命令、图片续跑、尺寸处理和架构边界。

相邻页面脚本套件：**22 passed，2 failed**。失败分别为旧英文约束句匹配，以及正文截取后包含风格文字的断言。失败位于当前页面提示词表达相关逻辑，本次未修改该提示词实现；保留诊断，不宣称整套测试全绿。未在干净基线环境重跑这两项，因此本记录不对它们的引入时间作判断。

`git diff --check` 通过。CLI 帮助已显示新批次默认 Sunburst、续跑沿用记录模型。

本轮采用无网络 dry-run 验证真实参数传递与产物消费，未额外生图。前一轮指定 Sunburst 的实际调用已成功并通过中文审计；本轮不新增实际后端版本证明，不制作新的 PPTX。

## 用法

新批次使用原有正式命令，省略 `--image-model` 即采用新默认。旧批次优先使用其记录的恢复命令；省略该参数时仍读取批次模型。需要显式使用旧模型时添加：

```text
--image-model gpt-image-2
```

## 本轮修改文件

- [scripts/imagegen_pipeline/providers/codex_oauth_image.py](/Volumes/DOC/CyberPPT/scripts/imagegen_pipeline/providers/codex_oauth_image.py)
- [cyberppt/cli.py](/Volumes/DOC/CyberPPT/cyberppt/cli.py)
- [cyberppt/commands/final_script_pages.py](/Volumes/DOC/CyberPPT/cyberppt/commands/final_script_pages.py)
- [cyberppt/stage02_production/models.py](/Volumes/DOC/CyberPPT/cyberppt/stage02_production/models.py)
- [cyberppt/stage02_production/preflight.py](/Volumes/DOC/CyberPPT/cyberppt/stage02_production/preflight.py)
- [cyberppt/stage02_production/orchestrator.py](/Volumes/DOC/CyberPPT/cyberppt/stage02_production/orchestrator.py)
- [cyberppt/stage02_production/image_stage.py](/Volumes/DOC/CyberPPT/cyberppt/stage02_production/image_stage.py)
- [.agents/skills/cyberppt-stage02-editable-pptx/SKILL.md](/Volumes/DOC/CyberPPT/.agents/skills/cyberppt-stage02-editable-pptx/SKILL.md)
- [tests/test_stage02_image_model.py](/Volumes/DOC/CyberPPT/tests/test_stage02_image_model.py)
- [tests/test_stage02_orchestrator_expected_actions.py](/Volumes/DOC/CyberPPT/tests/test_stage02_orchestrator_expected_actions.py)

## 测试日志

- [images25-model-migration-tests-20260909.log](/Volumes/DOC/CyberPPT/docs/reports/images25-model-migration-tests-20260909.log)
- [images25-adjacent-tests-20260909.log](/Volumes/DOC/CyberPPT/docs/reports/images25-adjacent-tests-20260909.log)
