# 生图后暂停：实现与验证

正式入口新增 `--stop-after-images`。本次电力数据共建项目已通过只编译入口记录此选项，尚未生图。

## 行为

- 全部内容页图片完成尺寸归一化并通过图片文字审计后，返回 `paused_after_images`。
- 暂停发生在节奏检查、重建视觉来源绑定、清底、SVG 编写和 PPTX 组装之前，适用于 image、editable、both 三种分支。
- 原 manifest、build context 与运行汇总记录暂停状态；运行汇总列出已审计图片。没有新增审批文件。
- 用户明确继续后执行运行汇总的 resume_command。命令保留原批次、目录、页面范围及生产参数，去掉暂停开关；retry_command 保留开关。
- 审计失败保持失败；只编译和 dry-run 不报告图片已完成。暂停控制不改变内容身份与有效图片回执。

## 验证

仓库 `.venv/bin/python3` 运行 Stage 02、外部稿和关系判断相关测试：191 passed。

新增测试验证三种分支均不会越过停点、Office QA 不执行、状态写入与继续命令正确、继续后可进入重建、审计失败和跳过审计请求不会报告成功暂停。

正式 CLI 已在当前项目以只编译模式执行成功，运行结果为 `ready_for_image_generation` 且 `stop_after_images: true`。未调用真实生图服务，未生成 PPTX。本报告不声称完成真实图片暂停的端到端视觉验证。

## 文件

- [编排代码](/Volumes/DOC/CyberPPT/cyberppt/stage02_production/orchestrator.py)
- [状态与继续命令](/Volumes/DOC/CyberPPT/cyberppt/stage02_production/delivery_stage.py)
- [新增测试](/Volumes/DOC/CyberPPT/tests/test_stage02_stop_after_images.py)
- [工作流](/Volumes/DOC/CyberPPT/docs/CYBERPPT_WORKFLOW.md)
- [Stage 02 Skill](/Volumes/DOC/CyberPPT/.agents/skills/cyberppt-stage02-editable-pptx/SKILL.md)
- [当前项目运行记录](/Users/liuxing/.codex/worktrees/b42a/ppt-master/projects/power_data_cocreation_20260913/workbench/stages/02-imagegen/pages_001_012_power-data-cocreation-stage02-20260913/pages_001_012_final_script_pages_run.json)
- [当前编译脚本](/Users/liuxing/.codex/worktrees/b42a/ppt-master/projects/power_data_cocreation_20260913/workbench/stages/02-imagegen/pages_001_012_power-data-cocreation-stage02-20260913/final-script_cyberppt_deliverable_p1_p12.md)
- [当前逐页清单](/Users/liuxing/.codex/worktrees/b42a/ppt-master/projects/power_data_cocreation_20260913/workbench/stages/02-imagegen/pages_001_012_power-data-cocreation-stage02-20260913/page_image_pairs.json)
- [当前构建上下文](/Users/liuxing/.codex/worktrees/b42a/ppt-master/projects/power_data_cocreation_20260913/workbench/stages/02-imagegen/pages_001_012_power-data-cocreation-stage02-20260913/build_context.json)
- [当前模板文字记录](/Users/liuxing/.codex/worktrees/b42a/ppt-master/projects/power_data_cocreation_20260913/workbench/locks/template_text/pages_001_012_template_text_lock.json)
- [当前风格记录](/Users/liuxing/.codex/worktrees/b42a/ppt-master/projects/power_data_cocreation_20260913/workbench/locks/visual_style_lock.json)
