# Slide Image Rebuild Capability Roadmap 落地方案

本文用于把“按图重建 PPT”流程的能力建设拆成可执行、可验收、可回滚的增量。原则：只把确定性工程问题做成硬门禁；审美、相似度和场景化偏好先做报告或可选 contract，避免误伤不同版式。

## 1. 当前判断

| Layer | 当前状态 | 是否进入默认流程 | 结论 |
|---|---|---|---|
| Asset Reliability | 已有 `icon_manifest.json`、透明 PNG 检查、可选 `grid_contract.json` | 否 | 保持 opt-in；只在真实 C×R / N×N 网格资产时启用 |
| Visual QA | 已有整页 preview、similarity、visual diff；缺少多区域 contact sheet | 是，作为报告产物 | 优先落地，不作为硬门禁 |
| Editable Semantics | SVG 有语义 ID；PPTX selection pane 名称仍偏泛化 | 是 | 应进入导出层，属于确定性可编辑性提升 |
| Multi-page Engine | manifest 支持 `pages[]`；多页端到端协议还不完整 | 分阶段 | 先固化协议，再做 PPTX/PDF 批量入口 |
| Style Library | 复用宿主资源；缺少按图复刻 archetype 库 | 否 | 先沉淀少量高频版式，不做大而全 |
| Agentic Review | 已有 repair tasks 和有限 auto-repair | 否 | 先生成修正清单，默认不自动改 |

---

## 2. P0：Visual QA Contact Sheet

**目标**：把人工复核从“只看整页预览”升级为“一张图同时看全页和关键区域”，优先解决偏上、压线、底部过空、局部错位等问题。

| 项目 | 方案 |
|---|---|
| 新脚本 | `scripts/build_visual_contact_sheet.py` |
| 输入 | `<project>/exports/preview_qa/*.preview.png`、参考图、`layout_reference.json`、`text_region_map.json`、`icon_manifest.json` |
| 输出 | `<project>/exports/qa/contact_sheets/P01.contact_sheet.png` |
| strict runner | 接入为 soft/report step，不影响 `valid` |
| 默认区域 | full page、top band、main content、bottom band、text dense regions、icon regions |

**实现步骤**：

1. 从 `slide_image_rebuild_manifest.json` 建立 page id 到 reference / preview 的映射。
2. 从 `layout_reference.zones[]`、`text_region_map.regions[]`、`icon_manifest.icons[]` 提取候选区域。
3. 对候选区域做去重、扩边、裁剪到画布内。
4. 生成 contact sheet：每个区域显示 reference crop、preview crop、diff crop，可选标注 bbox 名称。
5. 在 `strict_run_report.json` 中记录 contact sheet 路径。

**验收**：

| 检查 | 标准 |
|---|---|
| 单页项目 | 生成 1 张 contact sheet |
| 多页项目 | 每页 1 张，文件名与 SVG stem 对齐 |
| 无 reference 图 | 降级为 preview-only sheet，不失败 |
| strict runner | `valid` 不因 contact sheet 失败而改变，但报告 warning |

---

## 3. P1：Selection Pane 语义命名

**目标**：PPT 打开后，选择窗格里能看到可读对象名，而不是 `TextBox 12` / `Line 7`。

| 对象 | 命名来源 | 示例 |
|---|---|---|
| 文本 | `data-text-region-id` | `P01_text_main_title` |
| 图标 | `data-icon-id` | `P01_icon_security` |
| 区域容器 | `data-zone-id` + `data-primitive` | `P01_card_short_term` |
| 连接线 | `data-chain-connector` | `P01_connector_short_to_mid` |
| 图片裁剪 | `data-crop-id` / `data-crop-role` | `P01_crop_footer_pattern` |

**实现步骤**：

1. 在 SVG → PPTX 转换层增加 `shape_name_from_svg(elem, page_id, shape_id)`。
2. 优先读取语义属性，兜底到现有泛名。
3. 对名称做 PowerPoint 兼容清洗：ASCII 前缀 + 下划线 + 长度上限。
4. 为 group / text / icon / image / connector 分别加测试。
5. 在 `verify_editable_pptx.py` 或新增脚本中抽检 selection pane 名称。

**验收**：

| 检查 | 标准 |
|---|---|
| 文本框 | 主要文本对象不再全部叫 `TextBox N` |
| 图标 | `icon_manifest` 中的图标在 PPTX 中有可读名称 |
| 回退 | 没有语义属性的对象仍可导出 |
| 兼容 | PowerPoint 打开不触发修复 |

**落地状态**：

| 项目 | 文件 |
|---|---|
| 语义命名规则 | `scripts/svg_to_pptx/semantic_names.py` |
| 导出层接入 | `scripts/svg_to_pptx/drawingml_elements.py`、`scripts/svg_to_pptx/drawingml_converter.py` |
| 单子节点语义 group 保留 | `scripts/svg_to_pptx/drawingml_converter.py` |
| 回归测试 | `tests/test_selection_pane_semantic_names.py` |

---

## 4. P1：多页复刻协议

**目标**：把单页成功路径推广到多页，但不先做复杂自动化。先统一项目结构、命名、报告和合并规则。

| Artifact | 规则 |
|---|---|
| reference pages | `images/reference_pages/P01.png`, `P02.png` |
| SVG | `svg_output/P01.svg`, `P02.svg` |
| notes | `notes/total.md` 使用 `# P01` / `# P02` heading |
| preview | `exports/preview_qa/P01.preview.png` |
| QA | 每页报告保留 page id，聚合报告给 deck-level 摘要 |
| PPTX | 只导出一个 deck，页序按 manifest `pages[]` |

**实现步骤**：

1. 更新 manifest 文档，明确 `pages[]` 是页序唯一来源。
2. 在 scaffold 阶段允许传入目录或 PDF/PPTX 渲染后的图片序列。
3. Phase A 为每页生成 layout/text/content/svg plan。
4. Phase B 明确逐页生成，不并发编辑同一项目文件。
5. Phase C 由 strict runner 聚合多页 preview、editability、warnings。

**验收**：

| 检查 | 标准 |
|---|---|
| 3 页图片输入 | 生成 3 页 SVG + 1 个 PPTX |
| 单页失败 | 报告能指出具体 page id |
| 页序 | PPTX 页序与 manifest 一致 |
| 断点续跑 | 失败后 `resume_command` 不丢页 |

**落地状态**：

| 项目 | 文件 |
|---|---|
| 协议文档 | `docs/zh/multi-page-rebuild-protocol.md` |
| page id / SVG 命名 warning | `scripts/verify_slide_image_rebuild_manifest.py` |
| 多页 notes heading hard gate | `scripts/verify_slide_image_rebuild_manifest.py` |

---

## 5. P2：Asset Reliability 增强

**目标**：只在明确资产网格场景下提高可靠性，避免把普通页面强行网格化。

| 子项 | 当前 | 后续 |
|---|---|---|
| `grid_contract.json` | 已有可选校验 | 保持 opt-in |
| 透明 PNG padding | 已有最终资产检查 | 保持 hard gate |
| 图标拼板切割 | 暂无默认实现 | 需要时新增独立工具 |
| 自适应 chroma-key | 仅规则说明 | 不进默认流程 |

**实现步骤**：

1. 保持 `verify_grid_contract.py` 独立，不接入默认 strict runner。
2. 只有当项目有 `grid_contract.json` / `asset_grid_contract.json` 时运行。
3. 若后续出现批量图标拼板需求，再新增 `grid_chroma_cut.py`。
4. `grid_chroma_cut.py` 必须先检测真实内容中心，再算 cell edges，禁止从 `(0,0)` 机械硬切。

**验收**：

| 检查 | 标准 |
|---|---|
| 无 contract | 明确 skipped |
| N×N 非正方形 | 报错 |
| 图标偏离 cell center | 报错 |
| safe zone 偏离 | warning，不阻断 |

**落地状态**：

| 项目 | 文件 |
|---|---|
| C×R / N×N 可选校验 | `scripts/verify_grid_contract.py` |
| 图标拼板自适应切割 | `scripts/grid_chroma_cut.py` |
| 切割器回归测试 | `tests/test_grid_chroma_cut.py` |
| 触发说明 | `references/required-reads.md` |

---

## 6. P2：中文商务与政务版式样例库

**目标**：为按图复刻提供少量高频 archetype，而不是大而全模板库。

| Archetype | 用途 |
|---|---|
| `three_stage_goal_timeline` | 三阶段目标 / 路线图 |
| `policy_pathway` | 政策路径 / 建设路径 |
| `capability_matrix` | 能力矩阵 / 责任矩阵 |
| `left_right_comparison` | 前后对比 / 方案对比 |
| `four_quadrant_framework` | 四象限分析 |
| `kpi_dashboard` | 指标看板 |
| `organization_architecture` | 组织架构 / 技术架构 |
| `table_with_callouts` | 表格重点标注 |

**实现步骤**：

1. 在 `references/layout-archetypes.md` 中定义 archetype 名称、识别信号、必备对象。
2. 在 `layout_family_lib.py` 中只做轻量分类，不强制生成。
3. 在 `svg_build_plan.md` 中写入推荐 archetype，供 Executor 使用。
4. 每个 archetype 配一个小 fixture 和 validator，不一次性建设大库。

**验收**：

| 检查 | 标准 |
|---|---|
| 识别 | 能给出 layout family + confidence |
| 不误伤 | custom 页面可不归类 |
| 可复用 | 同类页面的 plan 有稳定对象清单 |

**落地状态**：

| 项目 | 文件 |
|---|---|
| Archetype 库定义 | `references/layout-archetypes.md` |
| 轻量分类输出 | `scripts/layout_family_lib.py` |
| `svg_build_plan` 透传 | `scripts/layout_reference_to_svg_plan.py` |
| 回归测试 | `tests/test_layout_archetypes.py` |

---

## 7. P2：Agentic Review 受控回修

**目标**：让 Codex 基于报告生成修正清单，但不默认自动修改所有视觉差异。

| 问题类型 | 默认动作 |
|---|---|
| 文本溢出 / CJK mojibake / 非 editable | hard error，可自动建议修复 |
| 压线 / 重叠 / 底部过空 / 主体偏上 | hard 或 warning，生成 repair task |
| reference similarity 低 | warning，人工判断 |
| 图标风格不一致 | warning 或 hard，取决于 icon contract |
| 色差 / 审美偏差 | 只生成观察项 |

**实现步骤**：

1. 扩展 `repair_tasks.json` schema，增加 `confidence`、`auto_apply_allowed`、`requires_human_review`。
2. 将 contact sheet、composition、alignment、spacing 的结果纳入任务聚合。
3. `--auto-repair` 只处理低风险坐标修复、文本 fit、重复组间距。
4. 同一 failed step 连续 3 次失败，停止自动回修。

**验收**：

| 检查 | 标准 |
|---|---|
| 修正清单 | 每个任务有 source check、对象 selector、建议动作 |
| 自动修复 | 只处理 allowlist 类型 |
| 人工边界 | similarity / 审美不自动改 |

---

## 8. 推荐实施顺序

| 阶段 | 工作项 | 预期收益 |
|---|---|---|
| 1 | Visual QA contact sheet | 立即提升人工复核效率 |
| 2 | Selection pane 语义命名 | 提升 PPT 可编辑交付质量 |
| 3 | 多页 manifest / QA 协议 | 支撑批量页复刻 |
| 4 | 少量 archetype 库 | 提升常见中文页面稳定性 |
| 5 | Agentic Review schema | 让回修闭环可控 |
| 6 | 图标拼板切割器 | 仅在出现稳定需求后投入 |

---

## 9. 不做事项

| 不做 | 原因 |
|---|---|
| 不把 C×R / N×N 设为全局硬规则 | 会误伤时间轴、流程图、非均衡卡片页 |
| 不把 similarity 作为默认阻断 | 视觉复刻存在合理重建差异 |
| 不默认自动应用所有 repair tasks | 容易把审美判断误当工程错误 |
| 不先建设大而全 style library | 维护成本高，复用率不确定 |
| 不把 chroma-key 切割器接入默认流程 | 只有图标拼板场景才需要 |

---

## 10. Definition of Done

每个能力进入默认流程前必须满足：

1. 有独立脚本或明确 workflow 入口。
2. 有 fixture 或测试覆盖正反例。
3. 有报告路径，能被 `strict_run_report.json` 引用。
4. 明确 hard / soft / advisory 级别。
5. 有跳过条件，不适用页面不会被误伤。
6. 至少在一个真实项目上跑通。
