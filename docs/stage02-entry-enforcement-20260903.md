# Stage 02 正式入口加固验收

日期：2026-09-03。

## 结果与边界

判断：**SUPPORT WITH CONDITIONS**。Stage 02 的正式适配器增加进程内调用门禁，复用现有编排入口、状态、清单与交付检查。模板修复、重新制作和重新组装纳入同一入口规则。

门禁用于防止绕过正式编排的误调用。具有任意代码执行或仓库写入权限的 Agent 可以修改门禁，仓库约束不构成安全隔离。底层工具继续服务单元测试和隔离诊断，诊断成果不得作为正式交付。

## 已修复的问题

| 问题 | 改动 | 验证 |
| --- | --- | --- |
| 有效磁盘记录可被直接重放至适配器 | 编排器建立调用期上下文，适配器核对项目、批次目录、页面顺序及组装模式 | 正式 CLI 成功；退出编排后直接重放被拒绝；异常退出后上下文清除 |
| 模板中的续跑命令遗漏生产参数、路径未引用 | 模板及交付记录共用命令生成器，使用仓库虚拟环境和 shell 引用，保留图片来源与提示词参数 | 三种组装分支、中文空格路径、模板与交付命令一致性通过 |
| 准备清单时先写文件，随后才验证导入来源 | 先在内存编译及验证，再发布提示词和清单；全部来源检查通过后再复制图像 | 第二页导入校验失败时，原清单、构建记录、提示词、编译稿和图像字节不变 |
| 重制和模板修复的入口约束覆盖不足 | 仓库规则明确禁止临时导出脚本、直接底层组装、修改最终包和单页成品合并代替生产 | 更新仓库规则与主流程总览 |

正常恢复不继承 `--force-images` 或审计绕过参数。进程内上下文不产生新的磁盘回执。清单保护覆盖编译及来源校验失败；文件系统写入中断和跨进程并发未新增跨文件事务保证。

## 测试

- 定向回归：**77 passed**。
- 真实 OfficeCLI 集成：**1 passed**。通过正式 CLI 执行两页登记、预览、审核、同批次恢复、原生导出与最终文字检查。图片供应使用本地测试素材，未调用付费生图服务；未在 Microsoft PowerPoint 应用内操作。
- 扩展回归：**115 passed，5 failed**。五项失败均用 HEAD 版本的清单编译代码在当前工作区环境重现；文件未回退或改写。涉及已有风格/提示词断言和已批准提示词的尾部换行差异，未扩大本次修改范围。
- `git diff --check` 通过。Graft 图谱已刷新。

定向命令：

```bash
.venv/bin/python3 -m pytest tests/test_stage02_invocation_contract.py tests/test_quick_independent_integration.py tests/test_image_to_pptx_runtime.py tests/test_template_assembly.py tests/test_template_body_scaling.py tests/test_final_visible_text_qa.py -q
```

五项已有失败：

1. `test_compiles_pages_7_8_from_final_script_with_traceable_artifacts`
2. `test_artifact_manifest_consumes_the_approved_seven_section_prompt_verbatim`
3. `test_strict_manifest_uses_content_first_canonical_prompt`
4. `test_style09_contract_is_single_complete_source_lock_after_stage02_summary`
5. `test_manifest_prompt_traces_back_without_a_shadow_reassembled_directory`

## 代码与规则

- [仓库入口约束](/Volumes/DOC/CyberPPT/AGENTS.md)
- [主流程总览](/Volumes/DOC/CyberPPT/docs/CYBERPPT_WORKFLOW.md)
- [调用期门禁](/Volumes/DOC/CyberPPT/cyberppt/stage02_production/state.py)
- [正式编排器](/Volumes/DOC/CyberPPT/cyberppt/stage02_production/orchestrator.py)
- [适配器入口检查](/Volumes/DOC/CyberPPT/scripts/image_to_pptx_runtime/stage02_adapter.py)
- [统一续跑命令](/Volumes/DOC/CyberPPT/cyberppt/stage02_production/delivery_stage.py)
- [清单准备及来源验证](/Volumes/DOC/CyberPPT/cyberppt/stage02_production/manifest_stage.py)
- [延迟发布提示词和清单](/Volumes/DOC/CyberPPT/scripts/imagegen_pipeline/page_manifest.py)
- [调用与恢复合同测试](/Volumes/DOC/CyberPPT/tests/test_stage02_invocation_contract.py)
- [正式 CLI 集成测试](/Volumes/DOC/CyberPPT/tests/test_quick_independent_integration.py)
- [适配器单元测试](/Volumes/DOC/CyberPPT/tests/test_image_to_pptx_runtime.py)

本轮未改写源脚本、正文 SVG 或用户项目 PPTX，未创建新的生产批次。
