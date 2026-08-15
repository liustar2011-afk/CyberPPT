# 旧双图链路、模板重建与本地 Git 历史清理设计

## 一、目标与授权边界

本批次在不改变远端 `origin` 的前提下，完成三项工作：

1. 从现行主链中拆出仍然有效的提示词、Style、生图交接和原生模板页能力；
2. 删除旧双图、三图、OCR 回填、editable overlay、图片反推模板及其兼容代码、测试和文档；
3. 删除仓库内运行产物和大体积历史对象，改写本地 Git 历史，只保留清理后的 `main`。

用户已明确选择：旧代码直接删除，不做仓库内或仓库外归档；删除其他本地分支和工作树；只改写本地历史，不改写或强制推送远端历史。

本批次不得破坏上一批次刚完成的源材料忠实数据链，也不得删除正文图转可编辑 SVG/PPT、Style09/Style10、九段式 GPT Image 2 提示词、外部 PPT 标题层及原生模板页生成能力。

## 二、现状判断

当前 `scripts/dual_image_overlay/` 同时混有两类代码：

- 现行主链仍使用的模块，包括九段式提示词、Style lock、生图交接、页面清单和图像提供方适配；
- 已退出主链的双图、OCR overlay、scene graph 反推、模板图片重建和大量兼容模块。

因此不能直接删除整个目录。正确做法是先把现行能力迁出旧命名空间，完成引用切换和测试，再删除旧目录。

当前主要体积如下：

- `.git/` 约 90MB，其中 pack 约 85MB；
- `image2pptx_runs/` 约 85MB，包含 261 个已跟踪文件；
- `tmp/` 约 2.9MB，包含 174 个已跟踪文件；
- `scripts/dual_image_overlay/` 共 129 个已跟踪文件；
- 根目录还存在约 2.2MB 的 `tmp_image_entry_scan.txt`。

## 三、目标架构

### （一）现行生图主链

将仍被正式主链消费的模块迁入语义明确的新目录：

```text
scripts/imagegen_pipeline/
├── artifact_prompt.py
├── deliverable_prompt.py
├── imagegen_handoff.py
├── prompt_compiler.py
├── prompt_diagnostics.py
├── prompt_send_enrich.py
├── production_readiness.py
├── style_library.py
├── style09_adapter.py
├── style_presets/
├── page_manifest.py
└── providers/
    ├── codex_oauth_image.py
    ├── config.py
    └── console_encoding.py
```

最终文件清单以现行 CLI 和 Python import 的实际传递依赖闭包为准。迁移不得复制两份实现；每个保留模块只能存在一个正式位置。

`cyberppt/page_artifact_spec.py`、`cyberppt/commands/final_script_pages.py`、`prepare_imagegen_send.py`、`semantic_intent_audit.py`、`speaker_notes.py` 和 `body_blueprint_prompt.py` 等调用方统一切换到新命名空间。

Stage 02 的正式目录名称从带有旧实现含义的 `02-blueprint-dual-image` 调整为 `02-imagegen`。旧目录名不继续兼容；已有旧项目需要重新运行 Stage 02。

### （二）可编辑 PPT 主链

保留下列正式能力：

- `scripts/image_to_editable_svg/`：正文图到可编辑 SVG/PPT 的正式转换路径；
- 封面、目录、章节过渡、封底的原生 SVG/PPT 模板生成；
- 当前生产质检所需的渲染与文本检查；
- 标题、副标题和公共模板元素由 PPT 层生成的约束。

如果原生模板页组装仍依赖 `template_image_ppt_export.py` 中的有效代码，只抽取“原生模板页生成与最终组装”部分到中性命名空间 `scripts/ppt_assembly/`。不得保留图片反推模板、双图 overlay 或历史 manifest 兼容分支。

### （三）明确删除的代码

完成依赖迁移后，删除以下类别：

- 双图、三图和 `dual_image_editable_overlay` 模式；
- OCR 定位、文字回填、背景图/文字图对齐和双图坐标融合；
- scene graph、container workspace、workspace assignment 等图片反推页面结构链；
- editable overlay rebuild、template rebuild、template image rebuild；
- 已移出正式能力后的整个 `scripts/dual_image_overlay/`；
- `source-capture`、`template-rebuild`、`render-dual-image-overlay`、旧 `image-ppt` 等 CLI、Makefile、npm 和 script alias；
- 仅用于上述链路的配置、测试、测试夹具和依赖；
- 讲述旧双图、模板反推和兼容方案的过时设计文档。

不得仅保留一个返回错误的兼容入口。旧命令应从帮助、命令注册、文档和测试中同时消失。

## 四、运行产物与大文件清理

当前树直接删除：

- `image2pptx_runs/`；
- `tmp/` 中全部运行结果；仅在确有空目录契约时重建 `.gitkeep`；
- `tmp_image_entry_scan.txt`；
- `prompts/attempts/`；
- 其他经清单确认的渲染图、临时 PDF/PPTX、diff heatmap、OCR 中间结果和重复输入图。

不因文件较大而删除正式产品资产。Style 调色板、仍在使用的模板背景、测试必需的最小夹具必须通过引用和测试证明后保留。

更新 `.gitignore`，至少覆盖运行目录、缓存、渲染结果、OCR 中间结果、临时 PPT/PDF/PNG、`__pycache__` 和本地依赖目录，防止再次提交。

仓库保留一份清理清单，记录删除类别、删除路径、迁移映射、删除前后体积和验证结果；清单只记录元数据，不保存被删除文件。

## 五、测试与合同调整

测试分三类处理：

1. 迁移：仍验证九段式提示词、Style、生图交接、页面清单、原生模板页和可编辑 SVG/PPT 的测试，改用新模块名；
2. 删除：只验证双图、OCR overlay、模板图片反推和旧兼容命令的测试；
3. 新增：断言旧命令和旧 import 不存在，运行目录不会被 Git 跟踪，正式主链不再出现 `dual_image_overlay`、`editable_overlay` 或 `template_rebuild`。

正式验收命令包括：

- 源材料忠实链与九段式提示词定向测试；
- `final_script_pages`、Style09/10、生图交接、正文图转可编辑 SVG/PPT 和原生模板页测试；
- CLI、Skill 合同和 import 编译检查；
- 对保留测试执行完整 `unittest discover`。

清理后的保留测试必须零失败、零错误。确实依赖不可用系统组件的测试只能按明确条件跳过，不得以删除测试掩盖现行主链缺陷。

## 六、本地 Git 历史改写

### （一）实施前置条件

只有在代码迁移、当前树删除和全部保留测试通过后，才能进入历史改写阶段。进入该阶段前输出精确删除路径和大对象清单。

本机未安装 `git-filter-repo`。本仓库当前提交数量较少，因此使用 Git 自带的 `git filter-branch --index-filter`，按已经确认的路径清单从本地 `main` 的全部提交中移除旧文件；不采用逐提交工作树扫描的 `--tree-filter`。

### （二）本地引用处理

历史改写前：

- 删除 `.worktrees/agent-gpt-image2-artifact-prompt`；
- 将验证通过的本批次功能分支快进合并到 `main`，再删除本批次功能分支；
- 删除 `agent/gpt-image2-artifact-prompt` 和 `agent/source-faithful-government-defaults`；
- 最终只保留 `main`。

为使旧对象可被本地 GC 清除，还需删除本地的 `refs/remotes/origin/*` 引用，并移除 `remote.origin.fetch` 自动抓取规则。远端仓库和远端分支不发生任何写入；`origin` URL 保留，便于以后由用户另行决定是否重新连接、推送或重新获取远端历史。

历史改写后删除 `refs/original/*`，清空 reflog，执行立即 GC。由于远端仍保留旧历史，未来重新配置并抓取 `origin/main` 会再次下载旧对象并形成分叉；这一行为不属于本批次。

### （三）不可逆性

用户已选择不制作代码归档，并授权删除其他本地分支。完成 reflog 清理和 GC 后，本地无法通过普通 Git 操作恢复被删除对象。远端未改写的历史是唯一外部旧版本来源。

## 七、验收标准

1. 现行主链不再 import `scripts.dual_image_overlay`；
2. 仓库中不存在旧双图、OCR overlay、模板图片反推和兼容命令；
3. 九段式提示词、Style09/10、生图、正文图转可编辑 PPT 和原生模板页能力保持可用；
4. `image2pptx_runs/`、已跟踪 `tmp/` 运行结果和 `prompts/attempts/` 被删除并纳入忽略规则；
5. 保留测试零失败、零错误，源材料忠实链回归通过；
6. 本地仅保留 `main`，无额外工作树；
7. 本地 Git 历史不再包含清理清单中的旧路径和大对象；
8. 工作树体积至少减少 80MB，Git pack 体积至少减少 60MB；
9. 远端仓库没有新增提交、强制推送、分支删除或其他写操作；
10. 形成清理前后指标和不可逆操作记录。

## 八、实施顺序

本批次必须按以下顺序执行：

1. 建立正式保留模块清单和 import 依赖闭包；
2. 迁移现行生图与原生模板页能力；
3. 切换 CLI、Skill、文档和测试；
4. 删除旧代码、旧测试和运行产物；
5. 完成当前树回归并提交；
6. 删除其他本地分支和工作树；
7. 改写本地 `main` 历史并执行 GC；
8. 重新验证当前树、历史路径和体积指标。

任何一步发现仍有正式主链依赖旧代码，应停止删除，先完成迁移，不得用兼容壳掩盖依赖。
