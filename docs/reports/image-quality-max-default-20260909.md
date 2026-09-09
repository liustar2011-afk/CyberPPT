# 生图默认画质调整

流程默认画质已统一为 `max`，请求模型继续采用 `gpt-image-2.5-sunburst`。命令行、正式生产函数、运行参数和 OAuth 生图提供器的默认值均已更新。显式 `--image-quality high` 等参数仍可覆盖默认值。已有批次按原 `resume_command` 继续运行，保留命令中记录的画质；直接复用旧命令且省略画质参数时会采用新默认值，可能触发输入绑定不一致检查。

流程总览和 Stage 02 Skill 已同步。没有重新生成项目图片。

## 验证

- 正式流程 dry-run 验证请求回执与 manifest 均记录 `max`，恢复命令携带 `--image-quality max`。
- 检查 CLI 默认值、显式 high 覆盖、运行参数默认值和提供器默认值。
- 模型、调用合同、输入绑定三组定向测试通过。
- 加上 final-script-pages 扩展检查后：44 项通过、2 项失败。失败位于 `tests/_final_script_pages_base.py:818` 的英文标题禁用语句断言及 `:157` 的旧正文分隔标记断言；这些提示词内容与本轮画质默认值修改无关。本轮未修改对应提示词或放宽测试。

## 更新文件

- [cyberppt/cli.py](/Volumes/DOC/CyberPPT/cyberppt/cli.py)
- [cyberppt/commands/final_script_pages.py](/Volumes/DOC/CyberPPT/cyberppt/commands/final_script_pages.py)
- [cyberppt/stage02_production/models.py](/Volumes/DOC/CyberPPT/cyberppt/stage02_production/models.py)
- [scripts/imagegen_pipeline/providers/codex_oauth_image.py](/Volumes/DOC/CyberPPT/scripts/imagegen_pipeline/providers/codex_oauth_image.py)
- [tests/test_stage02_image_model.py](/Volumes/DOC/CyberPPT/tests/test_stage02_image_model.py)
- [docs/CYBERPPT_WORKFLOW.md](/Volumes/DOC/CyberPPT/docs/CYBERPPT_WORKFLOW.md)
- [.agents/skills/cyberppt-stage02-editable-pptx/SKILL.md](/Volumes/DOC/CyberPPT/.agents/skills/cyberppt-stage02-editable-pptx/SKILL.md)
