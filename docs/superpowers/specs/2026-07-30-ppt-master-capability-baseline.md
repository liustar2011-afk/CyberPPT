# 阶段 0：PPT Master × CyberPPT 双图法能力基线

> 审计日期：2026-07-30
> CyberPPT 基线提交：`5746e0e507811c25192a429a2426396400515541`
> PPT Master 基线提交：`8a5ce7f00f54287fc600f5f2aabb1c2cbfa005e0`

## 结论

CyberPPT 的“双图法”不是一条需要从零移植的新路线：它沿用了 PPT Master 的
`slide-image-rebuild`/`dual-image-rebuild-ppt` 体系，并在 CyberPPT 中形成了
`editable-overlay → scene graph → template-rebuild` 的业务链。当前主要问题是
运行时版本分叉：CyberPPT 直接加载 `vendor/ppt_master_slide_image_rebuild` 的
快照，而 PPT Master 主仓库在 SVG→DrawingML、文本流、图片资源复用和 postflight
上已经继续演进。因此后续应做“版本收敛 + 能力差集补齐”，而不是整套重写。

阶段 0 只建立来源、版本、能力和证据基线；未修改任何运行逻辑。

## 来源与谱系

- CyberPPT 的入口在 `SKILL.md` 第 63、276–284 行明确声明 `editable-overlay`：
  full 图、无字底图、OCR/语义绑定、可编辑文字层和 `template-rebuild`。
- 业务代码在 `scripts/dual_image_overlay/rebuild_engine/`，并由
  `script_text_overlay.py` 在 `_apply_ppt_master_core_layout` 处调用 vendored
  `dual_image_rebuild_pptx.py`。
- `vendor/ppt_master_slide_image_rebuild/resource_bindings.json` 已声明优先使用
  PPT Master 的共享资源；该文件同时确认严格重建闸门和 PPTX 导出仍由
  `slide-image-rebuild` 负责。
- Git 谱系证据：`433d4129 chore: commit scene graph workflow updates` 是当前
  vendored 重建体系的提交；CyberPPT 当前分支为 `codex/scene-graph-first`。

## 能力分类

| 分类 | 当前能力 | 证据 | 后续归属 |
|---|---|---|---|
| `already_shared` | 双图契约、full/background 配对、OCR/文字锁定、严格重建闸门、PPTX 导出 | `SKILL.md`；`vendor/ppt_master_slide_image_rebuild/SKILL.md`；`vendor/.../workflows/dual-image-rebuild-ppt.md` | 保持单一契约，阶段 1 做入口收敛 |
| `vendored_snapshot` | 双图运行时、裁图 manifest、图标 manifest、相似度/修复聚合、旧 SVG→PPTX 与 QA | `vendor/ppt_master_slide_image_rebuild/scripts/dual_image_rebuild_pptx.py`；vendor `svg_to_pptx.py`、`svg_quality_checker.py` | 阶段 1 建 runtime bridge，阶段 5 收敛 QA |
| `CyberPPT_specific` | scene graph、语义容器、文本真值校验、语义排版、背景文字扫描、业务 SO WHAT 与本地工作台 ledger | `scripts/dual_image_overlay/scene_graph/{builder,layout,gate}.py`；`editable_overlay_rebuild.py`；`workbench/` | 阶段 2–3 保留并编译为 Page SVG IR |
| `upgrade_candidate` | 新 SVG→DrawingML 转换器；多语言字体/文本流；保留模式文本框重算；图片裁切与同源复用；资源/包 postflight；更严格 SVG checker；`data-pptx-bounds` 与文本安全区 | PPT Master `skills/ppt-master/scripts/svg_to_pptx/`、`svg_quality_checker.py`、`extract_svg_assets.py`、`resource_paths.py`；提交 `8a5416ac`、`3e54e96f`、`dd6c503d` | 阶段 1、3、4、5 分批接入，逐项回归 |

## 版本与文件证据

以下 SHA-256 用于后续升级前后的可追溯比较；路径均相对于各仓库根目录。

### CyberPPT 当前实现

| 文件 | SHA-256 |
|---|---|
| `vendor/ppt_master_slide_image_rebuild/scripts/dual_image_rebuild_pptx.py` | `A3A68F84AA008EB8342876D2F3E8CAF3EA8149F9CA7892024F65C273768B106D` |
| `vendor/ppt_master_slide_image_rebuild/workflows/dual-image-rebuild-ppt.md` | `8A77883DA7CE114331FF305212A9DA548DBE0C1C9C02B129AB30D01C2CFA8491` |
| `vendor/ppt_master_slide_image_rebuild/scripts/svg_to_pptx.py` | `A0C5B98EEA7A9D181A8EBB2B8913FE904D7F0B75C3E8E0D9E1E2F08C9CB3AE21` |
| `vendor/ppt_master_slide_image_rebuild/scripts/svg_quality_checker.py` | `ACA01EA6EF160CEF3BECAECCFB73B221D7AA77A4630400387C0B4AAE6CEF3BDE` |
| `scripts/dual_image_overlay/rebuild_engine/script_text_overlay.py` | `6EA9C75E0B57DC21321BA3DE3CFB507CBCBE44830FCCA3CC1F31181AA0461BFE` |
| `scripts/dual_image_overlay/scene_graph/builder.py` | `ADDFB5C8B6A7E1925EA0CECAD898AFE9D3563E3C652A005AEB52BDB9F58D8103` |
| `scripts/dual_image_overlay/scene_graph/gate.py` | `F64E58BA210368D5859E946339908058BE5885725A9556DC83BA69F132116184` |
| `scripts/dual_image_overlay/scene_graph/layout.py` | `F3F295E10D32DB16B1B48F49D55B16CBD41BEBC5CD6CEC3D03A8E6638BD5994E` |

### PPT Master 当前运行时

| 文件 | SHA-256 | 代表能力 |
|---|---|---|
| `skills/ppt-master/scripts/svg_to_pptx.py` | `3B59353C86B334F164965D08A4DD1F037174960C23AD22644FD3F6730DB8D7DA` | 新 DrawingML 入口 |
| `skills/ppt-master/scripts/svg_to_pptx/drawingml/elements.py` | （以 PPT Master HEAD 为准） | 文本框尺寸重算、文本流 |
| `skills/ppt-master/scripts/svg_quality_checker.py` | `9D872B72B7E1120BE42EF8660DCFB33974D882BACC6450932A37293619555D56` | 更严格 SVG QA |
| `skills/ppt-master/scripts/extract_svg_assets.py` | `EE402A528136A47330930573B71023D91A024790448B7D1B925CADC95CFD0BC6` | 图片/资源提取与复用 |
| `skills/ppt-master/scripts/resource_paths.py` | `AB9FF1406A1A4F47412DEF7ABA08FAB8E8F088259F7A1980A6EDD7326499C1AF` | 资源路径与包结构 |

## 不重复移植的能力

1. 不再复制一套新的双图入口；现有 `editable-overlay` 继续作为业务入口。
2. 不把 scene graph、语义容器和 CyberPPT 的内容真值校验下沉成通用 PPT Master
   逻辑；这些是 CyberPPT 的业务语义层。
3. 不以整页图片替代原生文本、图表和关键数字；双图底图只承担明确登记的复杂视觉资产。
4. 不在阶段 0 修改 vendor 快照、导出器、QA 规则或项目工作台。

## 阶段映射

| 阶段 | 目标 | 阶段 0 产出 |
|---|---|---|
| 1 | runtime bridge 与版本探测 | 已锁定 vendor 入口、共享资源绑定和 PPT Master HEAD |
| 2 | scene graph → Page SVG IR | 已锁定 scene graph 三个核心模块 |
| 3 | 文本度量、避让、异常处理 | 已识别文本流与 frame resize 差集 |
| 4 | 图片裁切/同源资源合同 | 已识别 `extract_svg_assets.py` 与 vendor crop manifest |
| 5 | 双图 QA × PPT Master QA | 已锁定两套 checker 与 manifest 闸门 |
| 6 | 代表页、真实渲染、逐页验收 | 已确定不能以结构检查代替视觉 QA |

## 工作树说明

本次审计发生时工作树已有大量用户未提交的生产资产变更（当前约 1200 条状态项）。
阶段 0 只新增本基线文档和机器可读摘要，不触碰这些既有变更。
