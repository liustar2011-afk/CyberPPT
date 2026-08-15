# 旧链路与本地历史清理记录

## 一、清理边界

本次保留源材料忠实数据链、九段式 GPT Image 2 提示词、Style09/Style10、生图交接、正文图转可编辑 SVG/PPT、标题层和原生模板页生成能力。删除旧双图、三图、OCR 回填、图片反推页面结构、模板图片重建、兼容入口及运行产物。

远端 `origin` 不执行推送、强制推送、分支删除或其他写操作。本地历史重写只在当前树全部验证通过后执行。

## 二、清理前指标

- 当前分支：`agent/legacy-pipeline-history-cleanup`
- 本地分支：4 个
- 工作树：2 个
- 仓库目录：909652 KiB
- Git pack：85.16 MiB
- 待从历史清理的已跟踪路径：567 个

## 三、迁移原则

| 原位置 | 处理 | 目标位置 | 现行消费者 |
| --- | --- | --- | --- |
| `scripts/dual_image_overlay/` 中提示词、风格、生图交接及其实际依赖 | 迁移 | `scripts/imagegen_pipeline/` | `cyberppt` 正式命令、脚本编译和生图链 |
| 原生 SVG/PPT 组装及现行质检依赖 | 按实际依赖抽取 | 中性组装或质检命名空间 | 正文图转可编辑 PPT、生产质检 |
| 双图、OCR、scene graph、模板图片重建与兼容代码 | 删除 | 无 | 已退出正式主链 |
| `image2pptx_runs/`、`tmp/`、`prompts/attempts/`、`tmp_image_entry_scan.txt` | 删除 | 无 | 运行产物，不属于源码或正式资产 |

## 四、不可逆操作边界

代码迁移、当前树清理和保留测试全部通过前，不删除其他本地分支和工作树，不改写历史，不清理 reflog，不执行立即 GC。

## 五、当前树清理结果

- 正式 Stage 02 代码已集中到 `scripts/imagegen_pipeline/`，质检代码已集中到 `scripts/presentation_qa/`。
- 正式生产模式仅保留 `image-to-editable-svg`；项目落点统一为 `workbench/stages/02-imagegen/`。
- 原生模板资产保留在 `assets/presentation-templates/cec-lightweight/`。
- 已删除旧双图、OCR 回填、scene graph、模板图片重建、旧审批哈希兼容模块及其专属测试。
- 已删除并禁止跟踪 `image2pptx_runs/`、根目录 `tmp/`、`prompts/attempts/` 和 `tmp_image_entry_scan.txt`；清理后上述路径跟踪文件数为 0。
- 已删除 21 份仅描述退出路线的旧方案或设计文件，并更新现行 `SKILL.md`、仓库布局、自主运行和 ImageGen 文档。

## 六、验证结果（历史重写前）

- `python -m unittest discover -s tests -v`：625 项通过，0 失败，4 项因未安装可选 `pytest` 依赖而按合同跳过。
- `git diff --check`：通过。
- 当前工作树体积：812340 KiB，较清理前减少 97312 KiB。
- Git pack 仍为 85.16 MiB；这是预期状态，历史对象将在本地主分支合并后通过路径过滤、reflog 清理和 GC 移除。

## 七、远端保护

本次操作不执行 `git push`、强制推送、远端分支删除或任何其他远端写操作。历史清理完成后保留 `origin` URL，但移除本地远端跟踪引用和默认 fetch refspec，避免将本地重写历史误当作远端状态。

历史重写前的远端基线为 `origin/main`：`b1e95bd`；远端 URL 为 `https://github.com/liustar2011-afk/CyberPPT.git`。

## 八、本地分支与工作树整合

- `agent/legacy-pipeline-history-cleanup` 已快进合并到本地 `main`。
- 已删除附属工作树 `.worktrees/agent-gpt-image2-artifact-prompt`。
- 已删除本地分支 `agent/gpt-image2-artifact-prompt`、`agent/source-faithful-government-defaults` 和 `agent/legacy-pipeline-history-cleanup`。
- 历史重写前仅保留本地 `main` 和一个工作树。

## 九、本地历史清理结果

- 仅重写本地 `main`；历史清理后的主分支提交为 `bbcfe09`（最终报告提交前）。
- 清理路径在当前树中的跟踪文件数为 0，在 `git rev-list --objects --all` 全部本地可达历史中的匹配数为 0。
- 已清理 `refs/original`、全部 reflog 和不可达对象，并执行 `git gc --prune=now --aggressive`。
- Git pack：85.16 MiB → 27.17 MiB，减少 57.99 MiB（约 60.81 MB），降幅约 68.1%。
- 仓库目录：909652 KiB → 546948 KiB，减少 362704 KiB，降幅约 39.9%。
- 本地仅保留 `main`；工作树数量为 1。
- 远端跟踪引用数量为 0，fetch refspec 数量为 0；`origin` URL 保留不变。

## 十、历史重写后验证

- `python -m unittest discover -s tests`：625 项通过，0 失败，4 项按合同跳过。
- `git diff --check`：通过。
- 未执行任何远端写操作。
