# 双图复刻 PPT 工作流诊断说明

本文面向代码诊断与架构复核。目标是让另一个模型或工程师快速理解 `dual-image-rebuild-ppt` 的当前设计、代码入口、产物链路、验收口径和仍需重点审查的问题。

## 1. 工作流定位

| 项目 | 说明 |
|---|---|
| 工作流名称 | 双图复刻 PPT / `dual-image-rebuild-ppt` |
| 适用输入 | 同一页的两张图片：完整有字图 + 无字背景图 |
| 输出 | 无字背景图作为锁定底图，文字以可编辑 PowerPoint 文本框覆盖 |
| 不做事项 | 不重画背景对象、图标、卡片、连接线、图表；这些都保留在背景图里 |
| 核心价值 | 保留视觉稳定性，同时让文字可编辑、可调整、可校验 |
| 和严格按图重建的区别 | 严格按图重建追求对象级可编辑；双图复刻只重建文字层 |

一句话：这个流程不是“把图片变成全对象 PPT”，而是“用无字底图承载视觉，用语义文字层生成可编辑文本框”。

## 2. 当前最高原则

| 原则 | 解释 |
|---|---|
| 语义优先 | 先识别文本的语义角色和所属容器，再决定排版 |
| OCR 只做定位证据 | OCR / vision bbox 用于找到文字和容器关系，不直接作为最终文本框几何 |
| 容器安全区优先 | 文本必须先放入所属容器的可用安全区 |
| 先用空间，再缩字号 | 对换行正文，先扩展到安全区可用宽高，再考虑缩小字体 |
| 不机械短语化 | 默认保留清楚完整表达；只有安全区内仍放不下时，才触发语义改写或移入 notes |
| 不照抄 full 图硬换行 | full 图的换行是风格证据，不是最终排版真值 |
| 可读性高于相似度 | 相似度只作为调试参考，不作为验收目标 |

## 3. 主要文件

| 文件 | 作用 |
|---|---|
| `workflows/dual-image-rebuild-ppt.md` | workflow 契约与人工执行说明 |
| `scripts/dual_image_rebuild_pptx.py` | 当前实现主入口 |
| `tests/test_dual_image_rebuild_pptx.py` | 单页双图复刻的回归测试 |
| `scripts/dual_image_similarity_report.py` | 可选相似度/裁图诊断脚本，目前不是验收核心 |
| `slide-image-rebuild/SKILL.md` | 按图重建技能总入口，包含双图路线触发说明 |
| `resource_bindings.json` | 嵌入 `ppt-master` 时的共享资源绑定 |
| `fixtures/dual_image_rebuild/page012/`、`fixtures/dual_image_rebuild/page014/` | 2026-07-04 新增：真实图片对 + semantic_plan，分别覆盖 auto-inferred fallback 路径和 explicit containers 路径，取代此前只存在于被 `.gitignore` 的 `projects/` 目录里、未沉淀的验证历史 |

## 4. 命令入口

常规运行：

```bash
cd /Volumes/DOC/ppt-master/slide-image-rebuild

scripts/repo_python.sh scripts/dual_image_rebuild_pptx.py \
  --full /Users/liuxing/Documents/script_imagegen/page_012_场景五_知识产权全周期保护_full.png \
  --background /Users/liuxing/Documents/script_imagegen/page_012_场景五_知识产权全周期保护_background.png \
  --semantic-plan tmp/page012_semantic_plan.final.json \
  --name page012_dual_image_rebuild_example \
  --no-align
```

测试：

```bash
cd /Volumes/DOC/ppt-master/slide-image-rebuild
scripts/repo_python.sh -m pytest tests/test_dual_image_rebuild_pptx.py -q
```

当前最近一次验证结果：

```text
42 passed
```

## 5. 执行链路

| 阶段 | 函数 / 动作 | 输出 |
|---|---|---|
| 项目初始化 | `ProjectManager(...).init_project(...)` | `projects/<name>_ppt169_<date>/` |
| 图片归档 | copy full/background 到 `sources/` | 原始输入留档 |
| 图片归一化 | `normalize_image(...)` | `images/P01_full_1280x720.png`, `images/P01_background_1280x720.png` |
| 架构 intake | `run_architecture_intake(...)` | `layout_reference.json`, `content_mapping.json`, `text_region_map.json`, `design_spec.md`, `svg_build_plan.md` |
| 文字布局归一 | `normalize_text_layout(...)` | 标准化 OCR / vision items |
| 语义计划归一 | `normalize_semantic_plan(...)` | 标准化 semantic plan |
| 语义覆盖 | `semantic_items_or_layout(...)` | 语义文本替代原始 OCR 文本 |
| 风格学习 | `build_text_style_profile(...)` | `P01_text_style_profile.json` |
| 安全区推断 | `infer_semantic_containers_from_full_style(...)` | `P01_safe_area_inference.json` |
| 排版策略 | `apply_typesetting_policy(...)` | `P01_typesetting_report.json` |
| 布局计划 | `build_layout_plan(...)` | `P01_layout_plan.json` |
| 应用布局 | `apply_layout_plan(...)` | 更新后的 text items |
| 构造文本框 | `build_overlay_boxes(...)` | `OverlayTextBox[]` |
| 机器 QA | `build_layout_qa_report(...)` | `P01_layout_qa.json` |
| SVG 预览 | `render_overlay_svg(...)` | `svg_output/01_dual_image_rebuild.svg` |
| PPTX 导出 | `export_pptx(...)` | `exports/dual_image_rebuild_*.pptx` |
| PDF 后台预览 | `build_pdf_preview(...)` | `qa_pdf/slide.pdf`, `qa_pdf/page-1.png` |

## 6. 关键中间产物

| 产物 | 用途 |
|---|---|
| `analysis/dual_image_rebuild/P01_text_style_profile.json` | 记录 full 图文字风格，不作为几何锁 |
| `analysis/dual_image_rebuild/P01_safe_area_inference.json` | 记录 fallback 容器和安全区推断 |
| `analysis/dual_image_rebuild/P01_typesetting_report.json` | 记录自动换行、硬换行归一、字号下限等动作 |
| `analysis/dual_image_rebuild/P01_layout_plan.json` | 渲染前的布局计划，是定位问题的首要文件 |
| `analysis/dual_image_rebuild/P01_layout_qa.json` | 机器可读 QA：安全区、重叠、字体下限、垂直容量等 |
| `analysis/dual_image_rebuild/P01_text_mapping.json` | 最终文本框坐标、字号、文本、角色、容器等 |
| `qa_pdf/page-1.png` | 后台视觉 QA 图，优先用于复核可读性和局部拥挤 |

## 7. 当前容器角色

`infer_semantic_containers_from_full_style(...)` 在 semantic plan 没有显式 `containers[]` 时，会尝试从 full 图文字分组推断容器。

| container_role | 用途 | 当前状态 |
|---|---|---|
| `stage_card` | 上方五阶段卡片 | 已支持标题、编号、正文分区 |
| `process_chain_card` | 中部加工链条卡片 | 已新增，避免正文跨箭头/跨卡片 |
| `product_panel` | 服务产品 / 权属证据类横向面板 | 已支持 |
| `service_card` | 底部第三方服务方卡片 | 已支持 |
| `trust_card` | 右侧可信机制分项 | 已支持标题/正文间距 |
| `side_actor_panel` | 左右侧数据来源方/用户方说明 | 已支持 |
| `chain_terminal_note` | 中部链条末端虚线说明框 | 已支持 |
| `isolated_text_region` | 仍无法归属的孤立文字 | 兜底策略，风险最高 |

诊断时应重点检查 `isolated_text_region` 是否吞掉了本该属于明确容器的文字。此前中部加工链条问题就是这个原因。

## 8. 布局和字体策略

| 策略 | 当前实现 |
|---|---|
| 正文角色集合 | `BODY_TEXT_ROLES` |
| 字号下限 | `ROLE_TYPESETTING_POLICY` |
| 硬换行处理 | `_normalize_full_image_linebreaks(...)` |
| 原文恢复 | `apply_typesetting_policy(...)` 在可放下时恢复 `source_text` |
| 夹入安全区 | `_clamp_box_to_bbox(...)`（`build_overlay_boxes` 中先执行） |
| 容器内扩高 | `_expand_wrapped_box_height_inside_safe_area(...)`（在夹入之后执行） |
| 字号拟合 | `_fit_font_size_to_box(...)`（最后执行） |

当前原则是：对可换行正文，先用安全区宽高，后做字号拟合。不能因为 OCR 原 bbox 很矮就直接缩字号。

2026-07-04 复核更正：`build_overlay_boxes(...)` 里的真实调用顺序是**先夹入（clamp）、再扩高（expand）、最后字号拟合（fit）**，不是本节曾经描述的"扩高 → 字号拟合 → 最后夹入安全区"。这不是一个活跃 bug —— `_expand_wrapped_box_height_inside_safe_area(...)` 自己会把扩高结果重新限制在传入的 `safe_bbox` 内（不是天真地"先夹紧再无脑扩"），所以夹入在先并不会导致扩高后的框被二次裁切。但这个顺序是一个脆弱不变式：任何未来重构如果误以为文档描述的顺序才是真实实现，在 `_clamp_box_to_bbox(...)` 之后又调用一次裸的夹紧，就会立刻把刚扩好的框重新裁掉。`tests/test_dual_image_rebuild_pptx.py` 中的 `test_build_overlay_boxes_clamp_before_expand_does_not_reclip_expanded_box` 把这个不变式钉成了回归测试。

另外，`P01_layout_plan.json` 每个 item 携带的 `fit_order`（例如 `["nudge_into_text_safe_bbox", "shrink_font", "semantic_revision_if_still_overflow"]`）只是各 container_role 分支写入的说明性标签，供人工阅读排版意图；`build_overlay_boxes(...)` 并不读取 `fit_order` 的内容来决定执行顺序——不管 `fit_order` 写了什么，实际执行顺序永远是上面这三步的固定顺序。诊断时不要把 `fit_order` 字符串误当作真实调用序列。

## 9. QA 口径

| QA 类型 | 当前定位 |
|---|---|
| `P01_layout_qa.json` | 几何和容量机器检查 |
| Codex 右侧 / 内置预览 | 人工视觉主参考 |
| `qa_pdf/page-1.png` | 后台可重复视觉证据 |
| PowerPoint / WPS | 交叉确认实际 Office 表现 |
| OfficeCLI PPT screenshot | 只做打开/导出烟测，不作为视觉通过判定 |
| 相似度报告 | 可选调试，不作为验收目标 |

这个口径是近期修正过的：OfficeCLI PPT screenshot 曾经把真实排版问题“看起来正常化”，不能再作为主验收依据。

## 10. 最近样例项目

最近一次生成项目：

```text
/Volumes/DOC/ppt-master/slide-image-rebuild/projects/page012_dual_image_rebuild_chain_card_pdf_final_ppt169_20260703
```

关键文件：

```text
exports/dual_image_rebuild_20260703_092826.pptx
qa_pdf/slide.pdf
qa_pdf/page-1.png
analysis/dual_image_rebuild/P01_layout_plan.json
analysis/dual_image_rebuild/P01_text_mapping.json
analysis/dual_image_rebuild/P01_layout_qa.json
```

该版本的 `P01_layout_qa.json` 当前为：

```json
{
  "issue_count": 0,
  "warning_count": 0
}
```

## 11. 已修过的问题

| 问题 | 修复方向 |
|---|---|
| 机械短语化导致表达不清 | 默认保留完整清楚表达，只有放不下才请求语义改写 |
| full 图硬换行被复制到 PPT | 硬换行降级为布局证据，非语义锁 |
| `许可、转让` 被不必要换行 | 不再按顿号硬插换行 |
| 阶段卡片正文没用下方空间就缩字号 | 安全区下沿扩展，正文先用可用高度 |
| 右侧 `trust_card` 标题/正文压线 | 标题和正文分区，保留垂直间距 |
| 中部加工链文字跨箭头/跨卡片 | 新增 `process_chain_card`，限制正文在本卡片内 |
| OfficeCLI 截图误导视觉 QA | 新增 PDF 预览，并把 OfficeCLI 截图降级为烟测 |

## 12. 仍需重点诊断的问题

| 方向 | 诊断问题 |
|---|---|
| 泛化能力 | 目前 `infer_semantic_containers_from_full_style(...)` 对 page012 有较多坐标阈值，是否需要抽成更通用的容器识别器 |
| 语义计划 schema | `semantic_plan` 对 containers、items、roles、safe bbox 的 schema 还不够正式，Claude 可检查是否应补 schema 文档和校验 |
| fallback 风险 | `isolated_text_region` 很容易掩盖“容器识别失败”，是否应把某些角色的 isolated fallback 提升为 warning |
| Office 真实渲染 | `python-pptx` 生成文本框和 PowerPoint/WPS/PDF 的换行估计仍可能有差异，是否需要更严格的 PDF OCR/视觉检测 |
| 容器安全区计算 | 当前安全区主要靠规则推断，是否应让 AI/视觉模型直接输出 container + safe bbox |
| 可读性量化 | 机器 QA 目前能查几何和估算高度，但不能真正判断“看起来压线/拥挤”，是否需要 crop sheet 或视觉模型评分 |
| 多页复用 | 当前主要验证单页 page012，多页双图复刻的项目结构和聚合 QA 尚未系统化 |
| 角色命名 | 角色如 `chain_body`、`service_item`、`trust_body` 等是约定，不是强 schema；错误角色会直接影响布局 |
| preflight 与文档不一致 | 2026-07-04 新发现：`workflows/dual-image-rebuild-ppt.md` 曾写“无显式 semantic containers 时仍可导出诊断用 PPTX”，但当前 `validate_semantic_plan(...)` 只要 `--semantic-plan` 被传入且任一 item 缺少可解析的 `container_id`，就会在导出前直接 abort（`semantic_plan_preflight_valid: false`，不写 `P01_layout_qa.json`），并非导出后再标记 invalid。只有完全不传 `--semantic-plan`（只传 `--text-layout`）才会真正走到 fallback 推断。已在 workflow.md 里更正说明，但代码是否应该恢复"有 semantic_plan 但缺 containers 时仍走 fallback 导出"这个行为，还是保持当前更严格的硬门禁，是一个需要产品决策的开放问题，本次改造未擅自变更。 |

## 13. 建议 Claude 优先看的代码点

| 优先级 | 位置 | 看什么 |
|---|---|---|
| P0 | `infer_semantic_containers_from_full_style(...)` | 容器推断是否过拟合、fallback 顺序是否合理 |
| P0 | `build_layout_plan(...)` | 每种 `container_role` 的分区是否符合“先容器后文本” |
| P0 | `build_overlay_boxes(...)` | 安全区夹入、扩高、字号拟合的顺序是否正确 |
| P1 | `build_layout_qa_report(...)` | QA 是否能抓住真实视觉问题 |
| P1 | `build_pdf_preview(...)` | PDF 预览失败/降级是否合理 |
| P1 | `tests/test_dual_image_rebuild_pptx.py` | 回归测试是否覆盖了真实失败案例，而不是只覆盖实现细节 |
| P2 | `workflows/dual-image-rebuild-ppt.md` | 契约是否和代码实际一致 |

## 14. 建议 Claude 回答的问题

1. 当前架构是否应该继续用规则推断容器，还是应引入显式 AI container extraction 阶段？
2. `semantic_plan` 应该设计成什么正式 schema，才能避免 OCR bbox 继续污染最终几何？
3. 哪些 `isolated_text_region` 情况应变成 warning 或 hard error？
4. `process_chain_card`、`stage_card`、`trust_card` 这类容器分支是否应该抽象成统一的 card layout policy？
5. PDF 渲染图能否进一步自动检测文本压线、越界、重叠和过密？
6. 对中文文本，如何更准确估算 PowerPoint 实际换行和文本高度？
7. 哪些测试应该增加，才能防止“看似通过但右侧预览仍不可读”的情况再次发生？

## 15. 诊断结论模板

建议 Claude 输出时按下面结构组织：

```markdown
# 双图复刻 PPT 工作流诊断结论

## 1. 总体判断

## 2. 关键架构问题

## 3. 代码级风险点

## 4. QA 链路缺口

## 5. 建议的最小改造方案

## 6. 建议新增测试

## 7. 不建议做的事
```

## 16. 当前边界

这个 workflow 的边界必须保持清楚：

- 背景不编辑。
- 背景对象不重画。
- 文字可编辑。
- OCR 是 locator，不是 truth。
- semantic plan / AI 语义是文字真值。
- container safe area 是排版真值。
- 可读性优先于相似度。
