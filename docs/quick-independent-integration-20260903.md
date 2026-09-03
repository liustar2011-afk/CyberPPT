# 高保真 Quick 独立集成验收

日期：2026-09-03

## 结论

独立代码集成已完成。正式生产入口继续使用 `final-script-pages --production-build`，页面通过本仓库的资产登记、原生文字转换、逐页预览、视觉复核和最终组装链路处理。运行时无需访问外部 ppt-master 仓库、项目或交付物，正式入口已停止调用旧自动清底生成器。

技术判断：**SUPPORT WITH CONDITIONS**。集成保留主 Agent 的参考图编辑、逐行 SVG 编写和看图复核职责。内置转换器已有的换行、Windows 路径等修复继续保留；全部替换为另一份源码可能回退这些修复。

## 已落实的边界

- 删除临时外部后端选择与 Quick 项目导入参数，保留经哈希验证的正式批次图片复用。
- 新增 `register-quick-page`，把已查看的同画布底图、SVG、全部本地图层与文字策略绑定到现有生产 manifest。输入变化会使登记与相应页面审核失效。
- 新合同采用参考图编辑及视觉复核，检查构图、图形身份、文字清除和背景连续性。旧 v3 清底验证代码保留用于历史合同；生产入口不执行旧生成器。
- SVG 使用显式文字位置与字号；样式锁继续接受跨区域 tspan 结构检查。
- 图层复制使用逐页隔离路径，避免不同页面的同名图片互相覆盖。
- 修复异常处理覆盖新检查点、跨页重复文字被全局去重的问题。
- 仓库 Stage 02 Skill、续跑说明与流程总览已同步更新；原生参考图编辑能力由当前主 Agent 的图像编辑工具提供。

核心实现：[资产登记与校验](/Volumes/DOC/CyberPPT/scripts/image_to_pptx_runtime/authored_layers.py)、[正式生产接入](/Volumes/DOC/CyberPPT/cyberppt/stage02_production/reconstruction_stage.py)、[Quick 消费与组装](/Volumes/DOC/CyberPPT/scripts/image_to_pptx_runtime/stage02_adapter.py)。

操作规则：[Stage 02 Skill](/Volumes/DOC/CyberPPT/.agents/skills/cyberppt-stage02-editable-pptx/SKILL.md)、[登记与续跑](/Volumes/DOC/CyberPPT/.agents/skills/cyberppt-stage02-editable-pptx/references/authored-svg-continuation.md)、[主流程](/Volumes/DOC/CyberPPT/docs/CYBERPPT_WORKFLOW.md)、[运行时维护边界](/Volumes/DOC/CyberPPT/scripts/image_to_pptx_runtime/UPSTREAM.md)。

## 验证结果

1. 定向回归：82 项通过，涵盖资产变更失效、来源哈希、外部路径拒绝、同名资产隔离、坐标结构、正式 CLI、恢复和组装。
2. 扩展回归：115 项通过，1 项既有提示词断言失败。失败项为 `test_compiles_pages_7_8_from_final_script_with_traceable_artifacts`，要求当前提示词包含旧英文禁绘句。当前提示词已有中文禁绘约束；使用 HEAD 原版 `prepare_manifest` 也复现该失败。本次保留该断言，未通过修改提示词或降低检查掩盖问题。
3. 真实渲染回归：两页合成样例从正式 CLI 经过真实 manifest 编排、登记、单页原生 PPTX、OfficeCLI 预览、审核回执、同批次恢复及整稿导出，测试通过。最终文字检查两页均通过，导出含两处可编辑“登记编目”。已查看两页渲染，文字位置稳定、底色正确、无重叠。
4. 测试把旧清底函数设为调用即失败，并拒绝通过 `Path.open` 访问名为 ppt-master 的外部目录；测试仍通过。
5. Skill 校验、Python 编译与 `git diff --check` 通过；Graft 图谱已刷新。

新增测试：[独立集成回归](/Volumes/DOC/CyberPPT/tests/test_quick_independent_integration.py)。

真实渲染命令：

```bash
CYBERPPT_TEST_REAL_RENDER=1 NODE_PATH=<已安装的-node_modules-路径> \
  .venv/bin/python3 -m pytest -q \
  tests/test_quick_independent_integration.py::test_two_page_official_entry_register_preview_resume_and_export
```

此次测试产物位于 pytest 临时目录，后续测试可能自动回收：

- [两页合成样例 PPTX](/private/var/folders/gk/frdqj5t92_z8l6f30xbg8sj80000gn/T/pytest-of-liuxing/pytest-12/test_two_page_official_entry_r0/standalone/workbench/stage02/production/editable_svg/exports/editable_svg.pptx)
- [第 1 页真实渲染](/private/var/folders/gk/frdqj5t92_z8l6f30xbg8sj80000gn/T/pytest-of-liuxing/pytest-12/test_two_page_official_entry_r0/standalone/workbench/stage02/production/qa-delivery/editable/renders/slide-1.png)
- [第 2 页真实渲染](/private/var/folders/gk/frdqj5t92_z8l6f30xbg8sj80000gn/T/pytest-of-liuxing/pytest-12/test_two_page_official_entry_r0/standalone/workbench/stage02/production/qa-delivery/editable/renders/slide-2.png)
- [OfficeCLI 检查记录](/private/var/folders/gk/frdqj5t92_z8l6f30xbg8sj80000gn/T/pytest-of-liuxing/pytest-12/test_two_page_official_entry_r0/standalone/workbench/stage02/production/qa-delivery/editable/officecli_render_qa.json)
- [最终文字检查记录](/private/var/folders/gk/frdqj5t92_z8l6f30xbg8sj80000gn/T/pytest-of-liuxing/pytest-12/test_two_page_official_entry_r0/standalone/workbench/stage02/production/qa-delivery/editable/final_visible_text_qa.json)

## 验证范围

本轮验收对象为代码集成与合成回归样例。测试替换了 Stage 01 输入检查与图像提供环节，未重新调用图像模型；实际页面仍须由主 Agent 准备并查看图层和 SVG。科标研训原两页业务内容未在本轮重新生产或批准，其历史排版缺陷需要按新流程逐页修订和验收。本次未覆盖或删除该项目已有图片、SVG 与 PPTX，也未修改无关工作区内容。
