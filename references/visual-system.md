# 视觉系统与 ImageGen 探索

## 默认视觉风格探索

当用户没有提供品牌或参考风格时，先展示 8 个固定 CyberPPT 视觉风格选项。可以根据源材料推荐一个，但不要替用户决定。这些是视觉系统，不只是配色。

| 选项 | 名称 | 颜色 | 适合场景 |
|---|---|---|---|
| 1 | 经典深红咨询风 | 背景 `#F3F4EF`; 标题/正文 `#111111`; 次级 `#555555`; 线条 `#D6D6D2`; 强调 `#8B1E1E` | 战略、竞品分析、行业研究、商业计划 |
| 2 | 冷灰 + 勃艮第红 | 背景 `#F5F5F2`; 标题 `#000000`; 正文 `#151515`; 次级 `#6B6B6B`; 线条 `#D9D9D6`; 强调 `#7A1F2B` | 财务、投研、咨询、风险分析 |
| 3 | 暖象牙白 + 暗酒红 | 背景 `#F4F1EA`; 标题 `#121212`; 正文 `#2B2B2B`; 次级 `#77736C`; 线条 `#D8D3CA`; 强调 `#8A1538` | 品牌战略、消费品、电商、用户研究 |
| 4 | 象牙白 + 深蓝强调 | 背景 `#F7F6F0`; 标题 `#101820`; 正文 `#303030`; 次级 `#6F7275`; 线条 `#C9CDD1`; 强调 `#12355B` | 科技、SaaS、B2B、企业数字化、AI Agent 报告 |
| 5 | 浅灰白 + 墨绿 | 背景 `#F2F3EF`; 标题 `#111111`; 正文 `#333333`; 次级 `#666666`; 线条 `#D7D9D3`; 强调 `#1F5B4D` | 可持续、海外市场、增长战略、长期趋势 |
| 6 | 纸张米色 + 铜棕 | 背景 `#F4F0E8`; 标题 `#161616`; 正文 `#2F2F2F`; 次级 `#76716A`; 线条 `#B8B6B1` / `#D8D5CE`; 强调 `#9A5A2E` | 消费、零售、奢侈品、商业模式分析 |
| 7 | 纯净浅灰 + 黑金 | 背景 `#F6F6F4`; 标题 `#000000`; 正文 `#252525`; 次级 `#707070`; 线条 `#DADADA`; 强调 `#A87932` | 高管汇报、融资材料、年度战略、董事会材料 |
| 8 | 冷白灰 + 深紫 | 背景 `#F4F5F6`; 标题 `#111111`; 正文 `#303030`; 次级 `#6D7175`; 线条 `#C8CCD0`; 强调 `#4B2E83` | AI、技术趋势、产品战略、创新研究 |

每个风格样张应使用可比的信息密度和页面结构，让用户可以判断语气、层级、图表语言和可读性。选定后，整份 PPT 锁定同一视觉系统。

## 第二步的两个子阶段

第二步不是一次性动作，必须分成“风格样张子阶段”和“逐页蓝图子阶段”。两个子阶段都要对照本文件执行。

### 风格样张子阶段

- 如果用户没有明确提供品牌、模板或替代风格，必须逐项生成上表固定 8 种 CyberPPT 视觉风格。
- 必须直接通过当前对话发送 8 张独立完整的 16:9 内置样张图片供用户选择，路径为：
  - `assets/palette-samples/palette-01.png`
  - `assets/palette-samples/palette-02.png`
  - `assets/palette-samples/palette-03.png`
  - `assets/palette-samples/palette-04.png`
  - `assets/palette-samples/palette-05.png`
  - `assets/palette-samples/palette-06.png`
  - `assets/palette-samples/palette-07.png`
  - `assets/palette-samples/palette-08.png`
- 如果决定重新生成样张，也必须交付 8 张真实图片；新图可以替代内置图，但不能只给文字说明。
- 网页、HTML、URL、文件夹路径、文件列表、Markdown 表格、文字说明、拼图或缩略图墙只能作为补充，不能替代当前对话中的 8 张独立样张图片。
- 如果使用网页辅助，网页只能作为附加浏览方式，不得作为风格确认的唯一依据。
- 不得用扩展风格替代默认 8 种；“8 个视觉方向”“8 个审美路线”或“8 个行业风格”不等于固定 8 种。
- 如果用户明确要求引入某个具体风格，只能替换最接近的默认项，并说明替换了哪个编号和原因。
- 每个选项必须是一张独立完整的 16:9 页面。拼图、缩略图墙、contact sheet 只能作为辅助总览，不能替代 8 张独立样张。
- 风格样张输出时，必须在图片外列出编号、名称、色板、语气、优势和风险。
- 不得把 `stage2_style_options.md`、Markdown 表格、文字列表或推荐理由当作风格确认物。它们只能作为图片后的辅助说明。
- 在用户能够在当前对话中直接看到 8 张样张之前，不得请求用户选择风格，不得进入逐页蓝图阶段。
- 如果当前界面无法显示图片，应停止并说明“风格样张展示门未通过”，不要让用户基于纯文本、网页、HTML、URL、文件夹路径或文件列表选择视觉风格。
- 如果网页中图片未加载、路径失效或用户无法看到样张，视为风格样张子阶段失败，不得继续。
- “只用源文件”表示最终事实、数字和文案只能来自源材料，不表示跳过本阶段的图片样张展示。

### 逐页蓝图子阶段

- 用户选定风格后，不再重新发散风格；先声明锁定风格编号、名称、色板、网格、标题层级、图表语言和信息密度规则。
- **送图脚本门禁**：调用 ImageGen 前，必须把将送入生图工具的明文 prompt 落盘到 `workbench/prompts/imagegen/`，在对话中展示，并等待用户修改或批准。送图内容只含主判断、上屏文字、视觉结构与清洗后的边界；禁止夹带完整文字稿、取舍说明、证据映射、证据编号、讲解提示。
- 每一页蓝图都必须沿用同一视觉系统，允许因页面角色调整密度，但不能改变配色、网格、标题层级、图表语言或页脚体系。
- 每一页蓝图提示词都必须包含锁定风格编号和名称，避免 ImageGen 默认漂移到其他审美方向。
- 蓝图生成后逐页检查风格漂移：如果出现深色驾驶舱、瑞士网格、杂志海报、科技蓝图等未被选定的扩展风格，必须重做该页。

## 可选的扩展风格探索

如果用户要求比配色更广的视觉探索，可以生成不同方向，例如：

1. MBB 高密度咨询风
2. 高级品牌战略风
3. 高管编辑杂志风
4. 瑞士国际主义网格
5. 现代数据叙事风

当某个方向不适合主题或受众时，可以替换，但要保持选项之间足够可区分。

如果用户提出具体风格，把它纳入 8 个选项，或替换最接近的选项。除非用户明确跳过，否则仍展示 8 个选择。扩展风格只能在用户明确要求时使用；默认流程不得用扩展风格替代默认 8 种。

## 图像生成规则

- 每个方向生成一张独立完整的 16:9 页面。
- 跨选项使用同一类代表性内容，确保可以公平比较风格。
- 不得创建拼图、缩略图墙或一张图里塞多页。
- 样张必须足以判断标题层级、网格、图表样式、注释、间距和密度。
- 避免细小伪文字。可以使用真实感文字块，但所有生成文字和数值都视为一次性占位。
- 选项标签放在图片外或文件名中，不依赖生成图里的文字。

用户可以明确跳过 ImageGen。跳过时，确认用户提供的模板、截图、品牌指南或文字规范是否足够具体。

## 将选定方向转成系统

记录：

- 页面尺寸和安全边距；
- 列网格和行网格；
- 固定 Typography Scale：`C0` 封面/章节幕标题，`T1-T14` 内容页文字层级，包括页码徽章、页面标题、副标题、模块/图表标题、证据标签、证据块标题、正文、结论条、SO WHAT、图表标签、KPI、注释和来源；
- 字体族和备选字体；
- 背景、文字、线条、中性色和强调色；
- 图表配色和强调规则；
- 表格边框、填充和层级；
- 圆角、阴影、分隔线、图标和图片处理；
- 页眉、页脚、来源和页码处理（默认策略见 `SKILL.md`"默认页面结构策略"：默认不设左上角页码徽章、不设独立页脚区、不含保密声明文字；来源/证据ID/口径改为内容区内联小字。仅当用户明确要求启用时才记录页码徽章/页脚样式）；
- 间距节奏和目标信息密度。
- 通用图标库选择：从 `chunk-filled`、`tabler-filled`、`tabler-outline` 或 `phosphor-duotone` 中锁定一个 stylistic library；`simple-icons` 仅作为真实品牌 logo 例外。

不要只因为颜色好看就批准风格。网格、密度、层级、图表语言和留白行为共同定义视觉系统。

图标风格也属于视觉系统。第二阶段锁定视觉方向后，应同时锁定通用图标库；第三阶段不得跨库混用普通概念图标。蓝图中的随机概念图标不要求逐像素复刻，但最终 PPT 图标必须语义近似、同库同风格，并通过空间注册反测。

必须额外记录统一页面表面系统：

- 页面如何使用已选风格的背景底色、面板色阶、细边框、栏头、分隔线、留白或轻微明暗差分区；
- 内容面板、图表区、侧栏、结论条、页脚分别使用什么底色；
- 白色是否为局部强调，还是全局内容底；
- 分区依赖细边框、栏头、分隔线、阴影还是留白；
- 后续 PPTX 还原是否允许大面积 `#FFFFFF` 卡片。

蓝图默认采用统一页面表面系统。除非蓝图明确把白色卡片作为主要分区语言，否则第三阶段不得把模块底色擅自改为大面积纯白卡片。该规则适用于全部 8 种固定视觉风格，不代表把其他风格改成象牙白或米黄色。

## 逐页正文内容区 ImageGen 蓝图

用户确认视觉方向后，必须为请求的全部页数，或已确认大纲所需的全部页数，生成逐页正文内容区 ImageGen 蓝图。这个步骤必须发生在混合还原 PPTX 之前。正文区蓝图是主线；页面标题、副标题、Logo、页脚、页码、蓝线、母版红线和公共模板元素不进入 ImageGen 蓝图画面，由模板/母版/可编辑文字层生成。

### 逐页正文区 ImageGen 蓝图真实性门

除非用户明确要求跳过 ImageGen，第二阶段逐页正文区蓝图必须由 ImageGen 生成 bitmap 图片。蓝图不是 PPT 草稿、HTML 页面、SVG 线框、canvas 截图、Markdown 图示或本地脚本绘图。主线 prompt 编译入口是 `scripts/body_blueprint_prompt.py`；该脚本只能组织正文区 ImageGen prompt、manifest 和策略记录，不能替代 ImageGen 生图。

本规则只约束第二阶段逐页蓝图交付，不限制第三阶段允许的 PPTX 还原辅助工具。PptxGenJS、SVG、custom geometry、Pillow、matplotlib、HTML 或 canvas 可以用于第三阶段 QA、裁图、overlay、metadata 或 prompt 管理，但不得作为第二阶段逐页蓝图的最终图像生成器。`python-pptx` 不得用于第三阶段正式 PPTX 生成。

允许脚本做以下辅助工作：

- 组织和批量生成 ImageGen prompt；
- 保存、复制、重命名 ImageGen 输出图片；
- 生成 metadata、manifest、QA 报告；
- 生成对照图、contact sheet 或检查用 overlay。

禁止脚本做以下替代：

- 用 HTML/CSS/SVG/canvas/Pillow/matplotlib/PptxGenJS/python-pptx 直接绘制逐页蓝图；
- 用 PowerPoint、网页截图、线框稿、结构草图或默认卡片页冒充 ImageGen 蓝图；
- 为了后续测量方便，把蓝图降级成规整占位图或低保真 mockup。

每页蓝图必须记录：

- `imagegen_prompt`；
- `imagegen_output_path`；
- `imagegen_generation_id` 或等价生成记录；
- `selected_style_id` 和 `selected_style_name`；
- `effective_language`；
- `density_target`；
- `visual_quality_check`。

如果用户明确跳过 ImageGen，必须记录：

- `imagegen_skipped_by_user=true`；
- 用户提供的模板、截图、品牌指南或视觉规范路径；
- 替代依据为什么足以作为蓝图；
- 不得声称该页是 ImageGen 蓝图。

### 逐页正文区蓝图质量门

逐页正文区蓝图必须延续已确认风格样张的正文区视觉系统，并达到第一阶段确认的信息密度和组件计划。ImageGen 文字和数字仍视为不可靠占位；本门只检查正文区视觉系统、密度和构图，不要求生成文字事实准确。页面标题、副标题、页脚、页码、Logo、蓝线和公共模板元素不属于正文区蓝图质量门的图内元素。

以下情况视为逐页蓝图失败，必须重做：

- 看起来像普通 PPT 原生卡片拼版、HTML dashboard、线框稿、低保真 mockup 或脚本绘图；
- 大面积默认白卡片、默认圆角矩形、默认阴影或默认 KPI 卡片替代已选视觉系统；
- 只增加卡片数量或文字数量，但缺少页面计划要求的主图、侧栏、注释、证据区、caveat、微图表、小表格、SO WHAT 或证据 ID；
- 信息密度低于第一阶段确认的页面计划；
- 风格样张中的色彩、材质、正文区网格、图表语言、正文区层级或注释系统没有延续到逐页蓝图；
- 为方便第三阶段还原、测量或可编辑性，主动降低蓝图视觉复杂度、信息密度或审美完成度。

### slide_content_lock 门

逐页正文区 ImageGen 蓝图生成前，必须先建立 `slide_content_lock`。该锁定文件必须来自第一阶段证据表、逐页大纲和用户确认内容，不得由 ImageGen 或第三阶段重新解释生成。

`slide_content_lock` 至少包含：

- 页面标题、副标题和语境说明；
- 每个图表的真实指标名、期间、单位和数值；
- 表格行列结构、真实行列标签和核心单元格内容；
- KPI、同比、CAGR、占比、差值等关键数值；
- 注释、caveat、来源口径和证据 ID；
- 右侧解读栏、管理启示或结论短句；
- SO WHAT 的真实分区、标题和要点；
- 不允许缺失的组件清单。

可以使用 `scripts/build_content_lock.py` 从已确认的逐页大纲/证据 JSON 生成锁定文件。蓝图画面可以出现文字渲染误差，但内容结构必须以 `slide_content_lock` 为准。第三阶段不得因为蓝图文字不清、数字变形或局部模糊而删减区域、降低信息密度或重组内容。

### blueprint_component_signature 冻结门

每页蓝图确认后，必须生成并冻结 `blueprint_component_signature`。该签名记录已批准蓝图的组件类型、组件结构、子组件、优先级、蓝图 hash 和对应 `slide_content_lock` hash。第三阶段只能读取，不得新建、重写或放宽组件签名。

组件签名必须记录：

- `slide_number`；
- `blueprint_path` 和 `blueprint_sha256`；
- `content_lock_path` 和 `content_lock_sha256`；
- `components[]`，每个组件包含 `id`、`type`、`priority`、`required_subcomponents`、`content_lock_refs` 和 `must_preserve_type=true`。

可以使用 `scripts/build_component_signature.py` 生成签名。如果第三阶段发现签名缺失或不完整，必须回到第二阶段补签名并重新确认，不得在第三阶段临时补写。

### visual_element_registry 门

每页蓝图确认后，必须建立 `visual_element_registry`，登记蓝图中的全部可见元素。所有文本、数字、图标、线条、箭头、面板、表格线、图表元素、SO WHAT 元素、装饰线、点阵和纹理都必须登记。

每个元素至少包含 `element_id`、`priority`、`element_type`、`source_component_id`、`blueprint_bbox_px` 和 `tolerance_px`。可以使用 `scripts/measure_blueprint.py` 结合人工/AI 标注生成 registry。完全自动识别任意 ImageGen 蓝图的所有元素并不可靠；因此缺少人工/AI 标注时，脚本必须显式失败，而不是自动声称覆盖完整。

### 测量元数据边界门

`visual_element_inventory_targets` 和 `blueprint_measurement_targets` 只是第二阶段蓝图记录的 metadata，用于第三阶段还原准备。它们不得改变第二阶段蓝图的交付物性质。

测量准备必须服务于 ImageGen 蓝图，而不是支配蓝图。不得因为需要后续测量，把蓝图做成结构草图、线框图、规整占位图、默认卡片页或脚本绘制图。

正文区蓝图规则：

- 每一页使用一张正文内容区图片；不得画入完整 PPT 外框。
- 保持选定配色、正文区网格、密度、图表语言和正文区间距一致。
- 不得画入页面标题、副标题、Logo、页脚、页码、蓝线、母版红线、保密声明或任何企业公共模板元素。
- 必须使用第一阶段确认的页面信息密度和组件清单，包括信息区数量、主图/侧栏比例、表格、注释、图例、微图表、证据 ID 和 SO WHAT。不得把高密度计划降级成宽松卡片。
- 使用已确认大纲作为内容结构，但生成文字、数字、引用、图表值、Logo 和标签都视为不可靠占位。
- 蓝图定义构图、层级、密度和视觉元素语言。最终 PPT 的文本、数据、表格值、图表值和来源说明必须从证据表重建。
- 蓝图不是最终 PPT 图片资产。除非用户明确要求静态图交付，第三阶段不得把正文区蓝图或大面积蓝图截图作为页面背景。
- 蓝图中的折线图、柱状图、坐标轴、标签、表格、对比条、流程箭头和 SO WHAT 只定义正文区视觉关系，第三阶段默认必须原生重建；真实文本和数据必须来自 `slide_content_lock`。页眉页脚、标题、副标题、页码、Logo 和蓝线由模板/母版/可编辑文字层生成，不从 ImageGen 蓝图复制。
- 除非用户明确要求，否则咨询报告封面蓝图保持低密度。
- 生成逐页蓝图前，必须自动判定默认 `target_language`，不得为语言选择单独增加确认步骤。
- 默认 `target_language` 判定优先级：用户明确指定的全局交付语言 > 源材料主要语言 > 当前对话语言。
- 只有源材料多语言且无明显主语言，或用户指令与源材料语言冲突时，才询问用户确认。
- 每页蓝图提示词必须显式包含 `target_language`、`language_source` 和本页生效的 `effective_language`。
- 如果用户明确要求某一页、某一节或某个组件使用不同语言，必须登记 `language_overrides`。
- `language_overrides` 至少记录：`scope`、`target`、`language`、`reason`。
- QA 时以 `effective_language` 为准，不得用全局 `target_language` 判定已登记覆盖范围失败。
- 蓝图正文区中的所有可见文字占位，包括模块标题、图表标签、图例、轴标签、注释、来源、SO WHAT 和按钮/标签，都必须使用对应范围的 `effective_language`。页面标题、副标题、页脚、页码、Logo、蓝线和公共模板元素不得作为蓝图画面中的可见文字。
- 不得因为 ImageGen、MBB、consulting slide、executive deck 或英文 prompt 模板更常见，就默认生成英文蓝图。
- 英文或其他外语只允许用于品牌名、产品名、专有名词、代码名、原文引用、指标缩写、用户明确要求保留原文的内容，或已登记的 `language_overrides` 范围，并应记录为 `allowed_foreign_terms` 或 `language_overrides`。
- `target_language`、`language_source`、`effective_language`、`language_overrides` 和 `allowed_foreign_terms` 是执行元数据，只能写入蓝图记录、prompt 说明、manifest 或 QA 记录，不得写入页面内容区，不得作为蓝图画面中的可见文字。

每张蓝图还要记录：

- `imagegen_prompt`；
- `imagegen_output_path`；
- `imagegen_generation_id` 或等价生成记录；
- `selected_style_id` 和 `selected_style_name`；
- 页码和页面角色；
- 计划保留为复杂视觉资产的区域或元素；
- 预留给可编辑文本的区域；
- 需要用 PowerPoint 原生形状、表格或图表重建的组件；
- 是否允许最终 `pictures > 0`，以及每个允许图片资产的必要性；如果复杂视觉扫描确认没有复杂照片、Logo、产品 UI、复杂插画、复杂纹理、复杂 3D、复杂图标、流线、异形边界、复杂弧线、非标准图表形态或其他非文字视觉资产，则记录为“无复杂视觉资产，通常可原生重建，pictures=0 仅为预期结果而非目标”；
- 支撑最终文本和数据的证据 ID；
- `target_language`：整套 PPT 的默认目标交付语言；
- `language_source`：`user_specified`、`source_material` 或 `conversation`；
- `effective_language`：本页实际使用语言，等于默认语言或页级覆盖语言；
- `language_overrides`：页级、章节级或组件级语言覆盖；
- `allowed_foreign_terms`：允许保留外语的品牌名、产品名、专有名词、指标缩写或原文引用；
- 预期信息密度和页面组件清单。

这些记录必须能直接转成第三阶段 `slide_manifest.json`。第二阶段蓝图记录中必须明确给出：

- `expected_pictures`：必须来自复杂视觉扫描和资产准入判断；无复杂视觉资产且蓝图允许完全原生重建时通常为 `0`，但不得作为第三阶段目标；
- `image_assets`：允许保留为图片的区域；每项必须写明区域、来源类型、必要性和可编辑性牺牲；
- `native_components`：折线图、柱状图、坐标轴、标签、关键数字、表格、对比条、流程箭头和 SO WHAT 默认都必须列入；标题、副标题、页眉页脚、页码、Logo 和蓝线另由模板/母版/可编辑文字层列入最终 PPT manifest。
- `text_objects`：正文区主要文字区域对应的 Typography Scale 层级，至少覆盖模块标题、正文、图表标签、关键数字、注释、来源和 SO WHAT；标题、副标题、页脚和页码作为模板/母版文字层记录，不得要求 ImageGen 画入正文区蓝图。
- `target_language`、`language_source`、`effective_language`、`language_overrides` 和 `allowed_foreign_terms`：语言规则执行记录；这些字段是元数据，不得进入页面可见内容。
- `complex_visual_scan`：记录扫描完成状态、复杂视觉候选、触发门、native-only 理由和 `pictures_zero_is_not_goal=true`；不得主动避免触发图片、曲线、异形或复杂视觉门。

以下情况视为逐页蓝图子阶段失败，不得进入 PPTX：

- 除非用户明确跳过 ImageGen，否则不能证明图片来自 ImageGen；
- 用 PptxGenJS、python-pptx、HTML、CSS、SVG、canvas、Pillow、matplotlib、PowerPoint 或任何本地绘图脚本直接绘制逐页蓝图；
- 用 PowerPoint 页面、网页截图、线框稿、结构草图、默认卡片页、低保真 mockup 或便于测量的规整占位图冒充 ImageGen 蓝图；
- 逐页蓝图看起来像普通 PPT 原生卡片拼版、HTML dashboard、线框稿、低保真 mockup 或脚本绘图；
- 为方便第三阶段还原、测量或可编辑性，主动降低蓝图视觉复杂度、信息密度或审美完成度；
- 未自动判定并记录 `target_language`；
- 每页未记录本页 `effective_language`；
- 用户未要求英文，且英文不是该页有效目标语言，却默认生成英文蓝图；
- 蓝图正文区模块标题、图表标签、SO WHAT、注释或来源等主要可见文字语言与 `effective_language` 不一致；
- 存在页级、章节级或组件级外语内容，但未记录在 `language_overrides` 或 `allowed_foreign_terms`；
- 用户只要求局部范围使用另一语言，却把未覆盖范围也改成该语言；
- 页面画面中出现语言元数据字段或类似“目标语言=中文”“language=Chinese”的执行指令文字。

每张蓝图还必须做图表语义和追踪触发记录：

| 项目 | 要求 |
|---|---|
| `chart_semantics` | 标明主图是普通柱线图、结构图、矩阵、迁移图、流线图、桑基图、弧线图、波形图、异形区域图等 |
| `visual_surface` | 标明连续纸面、白卡片、有色面板、透明面板或复杂背景 |
| `trace_required` | 出现曲线、流带、异形边界、非标准弧线或用户要求 1:1 时必须为 `true` |
| `trace_targets` | 需要追踪的区域或元素，如主流带、弯曲箭头、波形分割线、地图边界 |
| `native_labels_required` | 确认标签、数值、来源、页脚和 SO WHAT 后续必须原生重建 |
| `label_collision_risk` | 标明是否存在图标、节点、曲线、圆环、箭头密集区，第三阶段必须做标签避让检查 |
| `curve_fidelity_targets` | 标明核心曲线、弧线、流带或异形边界，后续需用 path/freeform/custom geometry 或密集采样 |
| `spatial_registration_targets` | 标明图标、节点、标签、箭头、连接线、组间距和阅读顺序等需要 1:1 锚点还原的区域 |
| `visual_element_inventory_targets` | 标明全部可见视觉元素或元素组，并预分配 P0/P1/P2 优先级 |
| `blueprint_measurement_targets` | 标明第三阶段必须逐项测量或装饰组测量的区域，并记录画布 px 到 PPT inch 的换算需求 |
| `container_overflow_targets` | 标明卡片、面板、表格单元格、SO WHAT、结论条、图表区等固定文字归属容器 |
| `continuous_text_flow_targets` | 标明含高亮、拆分片段、跨区域连续句或 SO WHAT 主句的文本流 |
| `table_semantic_typography_targets` | 标明表格正文、行动项、风险项、解释句、建议句、微标签分别对应的 Typography Scale |
| `table_density_targets` | 标明表格行高、列宽、单元格内容密度和允许留白节奏 |

触发 `trace_required=true` 的蓝图，在第三阶段不得被普通矩形、平行四边形、默认流程图、普通堆叠条或 ImageGen 重绘替代。必须走裁切、采样、trace debug、SVG path 或 PPT custom geometry 的精确追踪流程。

如果蓝图包含中心图、流程图、架构图、生态图、矩阵图、时间线、路径图或图标密集图，必须在蓝图记录中标出 `label_collision_risk=true`。第三阶段不得只按大致坐标摆放文字；必须做标签避让检查，确认文字不压住图标、节点、箭头、曲线、圆环或边框。

如果蓝图包含图标、节点、标签、箭头或连接线密集区域，必须在蓝图记录中标出 `spatial_registration_targets`。第三阶段不得只做“不重叠”的避让判断；必须检查图标是否在节点锚点、标签是否在图标/节点的正确相对位置、箭头端点是否接到正确边界、组间距和阅读顺序是否匹配蓝图。

蓝图记录必须为第三阶段准备 `visual_element_inventory_targets` 和 `blueprint_measurement_targets`。第三阶段必须登记正文区全部可见视觉元素：P0 覆盖主图、SO WHAT、关键数字、核心面板和用户指出区域；P1 覆盖普通卡片、图标、标签、箭头、表格和分隔线；P2 覆盖装饰线、点阵、纹理、重复刻度和背景纹样。页面标题、副标题、页脚、页码、Logo、蓝线和公共模板元素不由正文区蓝图测量，但仍必须在最终 PPT 的模板/可编辑文字层 QA 中检查。P0 必须逐项数值测量，P1 必须逐项或组内子锚点测量，P2 可以装饰组测量但不得跳过登记。

如果蓝图包含核心曲线或弧线，不得在第三阶段用少量折线点近似。蓝图记录应说明曲线是视觉语义核心还是装饰辅助；核心曲线必须进入曲线高保真检查。

如果蓝图包含卡片、面板、表格、结论条、SO WHAT、图表标注或固定区域文本，必须在蓝图记录中标出 `container_overflow_targets`。第三阶段不得只检查是否超出页面画布；必须检查文字是否留在归属容器内。

如果蓝图包含拆分文本、富文本高亮、跨区域连续句、SO WHAT 主句或结论句，必须在蓝图记录中标出 `continuous_text_flow_targets`。第三阶段必须检查基线、字距、空格、断句和阅读顺序。

如果蓝图包含表格、矩阵、行动清单、风险清单或网格化管理表，必须在蓝图记录中标出 `table_semantic_typography_targets` 和 `table_density_targets`。第三阶段必须按语义角色设置字号；表格正文、行动项、风险项、解释句和建议句不得登记为 `T11`。

如果蓝图记录无法判断某区域是否允许图片，默认不允许图片，第三阶段必须原生重建。不得把“蓝图复杂”作为图片准入理由。

## 可读性护栏

- 全篇锁定 15 个文字层级：`C0` 为封面/章节幕专用，`T1-T14` 为内容页层级。蓝图和 PPTX 还原都不得临时发明未记录的字号层级。
- 字号不足或容器溢出时，必须重组、分组、精炼文本、调整容器或拆页；不得用低于语义层级的字号解决。
- 关键数字和结论要能在正常演示缩放下快速扫读。
- 强调色只用于表达含义：优先级、例外、结论或行动。
- 保持有意图的留白，但拒绝由画布不匹配造成的大块右侧或底部空白。
- 图表标签必须横向直接标注；空间不足时必须调整图表布局，不得依赖图例替代关键标注。

## 确认输出

直接通过当前对话发送 8 张独立图片，并简要比较语气、密度、优势和风险。需要时给出推荐风格。网页、拼图或总览图只能作为辅助浏览，不能作为确认依据。停止并请求第二次确认，然后再进入混合还原 PPTX。

## 扩展风格9：纯白 + 深蓝领导汇报（精简优化版）

默认8种风格仍保持1—8不变。风格9是仅供显式选择的扩展风格，可通过 ID `9` 或 slug `ivory_deep_blue_scene` 调用，不进入默认候选。原风格4保持不变，既有风格4项目成果无需迁移。

Palette: pure white background #FFFFFF, deep blue #12355B, title #101820, body #303030, secondary #6F7275, divider #C9CDD1.

Create an executive briefing page in a scene-led editorial business-infographic style: authoritative, calm, refined, content-led and ready for formal presentation.

### 1. Style identity and semantic principle — hard

Build the page from recognizable business scenes, concrete objects, visible actions, evidence and outcomes; it should first communicate one clear business judgment, then reveal its supporting structure. Use abstract geometry, boundaries, color fields and connectors only to organize concrete meaning — do not let icons, decorative symbols or 3D objects become the page-level visual language when a recognizable scene or object can carry the meaning.

Keep the visual character editorial and matte — a refined executive-report spread, not a technology advertisement or icon-driven infographic.
Use pure white `#FFFFFF` as the page-level background. Do not shift the overall canvas toward ivory, cream, beige or warm paper tones. Pale blue-grey may be used only for local separation, evidence fields or subtle structural grouping.

### 2. Semantic anchor and composition — hard

1. Identify the page’s core judgment and primary business relationship.
2. Select one recognizable, page-specific business anchor: an operating scene, business object, content or data asset, professional work environment or visible outcome.
3. Give the dominant anchor approximately 35%–50% of the visual field when content permits.
4. Build one continuous, asymmetric and unequally weighted composition around it.
5. Organize two to five open semantic regions around, within or along the dominant anchor. These regions share one visual field and do not require independent cards or icon containers.
6. Use one or two large semantic actions to show comparison, convergence, transformation, separation, support, control, approval or result.
7. Complete the reading path with one clearly emphasized judgment or outcome region.
8. Do not use arrows anywhere on the page; express relationships through position, proximity, grouping or numbering, using a plain undirected line only if truly necessary.

Create hierarchy through crop, overlap, scale contrast, tonal separation, alignment, deep-blue emphasis and shallow foreground–background relationships.

Do not distribute content according to item count. Three, four or five text items do not automatically require equal columns, equal rows or equally detailed stages. The core judgment carries the greatest visual weight; supporting evidence remains quieter and subordinate.

Suitable anchors include: source materials parsed into one structured object; two fields compared around one visible gap; several inputs converging into one result; one operational environment showing monitoring or coordinated action.

### 3. Content fidelity and presentation expression — hard

Preserve the full factual meaning, core judgments, named entities, numbers, dates, units, causal relationships, conditional relationships, comparison relationships, scope boundaries and business logic of the provided Chinese content.

Do not add new facts, invent numbers, strengthen or weaken conclusions, change responsibility boundaries, alter policy meaning, omit required content or introduce unsupported labels. Do not shift modal strength while treating the wording as equivalent: do not turn a possibility into a certainty, a suggestion into a requirement, an exploratory or pilot description into a completed achievement, or a conditional statement into an unconditional conclusion.

Unless a passage is explicitly marked as verbatim text, locked text, quoted source text, formal name, number, metric, policy wording or other exact wording, the visible Chinese wording may be restructured for presentation readability.

Allowed presentation restructuring includes: splitting a long sentence into shorter presentation-scale statements; creating a short lead-in or micro-heading from wording already present in the source meaning; reorganizing parallel phrases into clearer visual levels; moving a qualifying phrase closer to the statement it qualifies; emphasizing key terms through weight, scale or deep-blue treatment; and reducing redundant function words when the factual meaning remains fully intact.

Every key metric number in the locked text (a count, percentage or threshold) must be visually emphasized through larger scale and deep-blue color directly inside its original sentence — plain body-text weight is not sufficient; never duplicate it as a separate large-number tile, badge or callout outside that sentence.

Presentation restructuring must improve hierarchy, rhythm and readability without changing semantic force. No factual meaning may be added, removed, narrowed, broadened, weakened or strengthened.

#### Verbatim text — hard when marked

Content explicitly marked as verbatim text, locked text, quoted source wording, official titles, formal product or institution names, numbers, units, dates, policy clauses or other exact wording must remain complete and unchanged.

Do not rewrite, shorten, relabel, reorder or paraphrase explicitly verbatim content.

#### Presentation-scale text layout

Allocate sufficient space for content before adding scenes, evidence, icons or decoration.

Use one clear readable text region for each primary semantic unit; regions do not need matching size or position — content weight decides how each is shaped, and a generic scene must not crowd text into a minor corner.

Keep body text at normal senior-presentation reading scale. If space is limited, simplify the scene or reorganize the wording — never shrink text into microcopy.

Render only source-supported Chinese content. Screens, documents and interfaces may contain large text-free structures, highlighted regions, check states or simplified diagrams, but must not contain invented readable microtext.

Each primary semantic region should read as one integrated unit of text and visual material. When a small supporting fragment genuinely clarifies one region, draw it from real business material relevant to that specific region — expressed in whatever concrete, recognizable form actually suits the content — rather than a symbolic icon or pictogram, and never repeat the same kind of fragment as a matching pair across every parallel region (see the icon discipline rules below). Regions do not have to be forced into perfectly equal treatment: some may carry a fuller scene-plus-text-plus-action unit, others may lean more on text with a lighter visual touch, depending on what each region's content actually needs.

Place text inside a quiet field within the scene, attach it to an object edge, align it with the corresponding action, or embed it in the outcome region. Visual splitting, line breaks and grouping must not alter the original sentence's logical relationship (for example turning a causal or conditional link into a flat parallel list). Font size, weight, color and position must not create a visual conclusion strength that misrepresents the source: a minor qualifier must not be made visually more prominent than the primary judgment it qualifies.

The governing principle is: factual fidelity is fixed; presentation wording and hierarchy may adapt to improve executive readability.

### 4. Reusable composition grammars

Select one primary grammar from the page semantics. Use a second only when the locked content clearly contains a second essential relationship.

#### A. Continuous object transformation

Show one recognizable business object changing through input, processing, review, control or output, expressed through object state and spatial progression — not step cards or icon rows.

#### B. Core scene with attached actions

Place one business object or operating environment in the main visual region. Attach supporting capabilities, conditions or outcomes directly to the scene through spatial relationship and unequal scale — not as separate icon modules.

#### C. Dual-field comparison

Use two concrete business fields or states in a controlled comparison; show the difference or transition through scale, alignment and one decisive judgment region — prefer concrete fields over symbolic icon comparisons.

#### D. Multi-source convergence

Show several distinct sources or actors entering one shared service, capability or result, through visible convergence into one dominant outcome field — concrete inputs, not a row of pictograms.

#### E. Concrete controlled containment

Place one recognizable protected object or operating scene inside a controlled field. Express access, isolation and approved output through checkpoints and state changes; keep the object visible, boundaries subordinate.

#### F. Parallel-direction shared evidence field

When the page names several parallel abstract directions or principles that share one evaluation or classification framework, do not give each direction its own icon or scene fragment. Instead let a small number of genuine evidence fragments serve the framework as a whole, choosing how many and where to place them based on what this page's specific content actually supports — some directions may carry a concrete fragment and others may rely on text hierarchy and spatial grouping alone; a page whose directions are too abstract for any genuine evidence may use none at all rather than inventing one.

### 5. Scene and evidence expression

Use one dominant scene or concrete business object, plus two to four quieter supporting scene or evidence fragments when needed. Vary scale, crop and viewpoint so the page reads as one composed visual field rather than assembled modules.

Create richness through semantic scene selection, cropping, scale and viewpoint changes — richness should come from meaningful business expression, not decorative objects.

When the page names several distinct top-level items, each item's own visual material must be specific enough that a viewer can tell which item it belongs to at a glance — not just that the page is generally about data or technology. Do not represent distinct named items with one shared undifferentiated panorama; give each its own recognizable fragment. If the items are abstract directions with no distinct concrete referent, drop the scene entirely and use a flat, structured relationship field instead.

Suitable visual material includes: professional operating environments; controlled content objects or data assets; documents in transformation; industry facilities; close-up evidence fragments. Any chosen anchor or fragment must depict something actually named in this page's content — never a generic control room, dashboard wall or stock BI screen used as decoration; with no distinct concrete referent among the locked content, prefer the flat structured relationship field over a generic technology scene.

Realistic or restrained semi-realistic materials are acceptable when they strengthen page-specific meaning. A workspace, device or interface must visibly demonstrate the relevant action or state, as supporting evidence inside a broader scene, not an isolated product.

### 6. Depth, material and icon discipline — hard

Maintain a restrained flat editorial foundation with shallow natural depth, created through overlap, cropping, scale contrast, tonal separation and subtle variations of pure white, pale blue-grey and deep blue.

Use matte surfaces, crisp edges and gentle tonal transitions; keep perspective natural and quiet.

Avoid glossy or decorative 3D rendering, exaggerated isometric perspective, cinematic depth, dramatic spotlighting, floating hero objects, glassmorphism, polished metal, reflective floors, neon glow, luminous edges and product-showcase presentation.

Visible drop shadows are generally discouraged; if needed, use an extremely soft, diffuse shadow. Business objects may retain natural physical form but must not be stylized into exhibition objects, toy-like miniatures or futuristic product concepts.

Icons are not a default visual language for Style 09. Start from zero icons.

Use an icon only when the page would lose immediate semantic clarity without it. A typical page should contain no icons; when genuinely necessary, use at most one very small, flat, deep-blue icon embedded inside an existing scene or text grouping.

Never assign one icon to each bullet, module, stage, actor, capability or message. Do not create icon rows, icon grids, icon walls, icon badges, icon cards, pictogram sequences or decorative symbol clusters. When a page presents several parallel metric lines or several parallel named directions or principles (for example four evaluation dimensions), do not place any icon, pictogram or colored glyph immediately beside each individual line; a row of icon-plus-label pairs is itself an icon wall even without visible borders, and remains forbidden.

Icons must never become the main visual carrier or repeated page structure. If a business meaning can be expressed through a scene, object or outcome region, remove the icon and use the concrete expression instead.

If one icon is indispensable, keep it simple, flat, deep blue, small and visually subordinate. Avoid 3D, gradient, glossy or holographic icon treatments.

### 7. Semantic economy and final priority — hard

Represent each source-supported concept once; supporting elements may add evidence or outcome, but must not restate the same label, sequence or conclusion.

When the composition already expresses a process, hierarchy or layered relationship, do not add a second icon chain, footer process or extra summary band unless explicitly required by the source content.

Use one primary visual metaphor per page; express remaining relationships through scene state, position, scale, crop, color fields and purposeful connectors, not a left-structure + right-explanation + bottom-summary formula.

Keep the result free from icon-led modular layouts, repeated device mockups, dense microtext and duplicated semantic summaries, and from any SaaS-marketing, app-store-style or futuristic 3D concept-art visual language (see the material and icon discipline rules above for the full decoration exclusion list). These exclusions are secondary: always prioritize content fidelity, recognizable business anchoring, open scene-led composition, semantic clarity, restrained editorial flatness and executive-level visual hierarchy.

Priority:
content fidelity, verbatim requirements and core judgment
→ recognizable business anchor
→ primary business relationship
→ large-scale semantic actions
→ evidence and outcomes
→ crop, overlap and shallow tonal depth
→ auxiliary symbols only when indispensable.

Final result: one calm, highly readable and visually refined executive-report composition with complete factual meaning and all required verbatim text, a recognizable business scene or object, open semantic grouping, clear page-specific meaning, strong hierarchy, restrained natural depth, minimal or zero icon use, no showy 3D rendering and no unnecessary semantic repetition.

### 8. Authority lock — hard

This Style 09 definition is the controlling visual authority for every page that selects it. Reference images may influence palette, crop and polish only, never the semantic structure, content fidelity, composition grammar or icon discipline defined above. When a conflict arises, remove the lower-priority decorative element and keep the higher-priority rule, in the order already stated in Section 7's priority list.

Do not reinterpret Style 09 into a card dashboard, icon infographic, SaaS marketing page or glossy 3D composition, even when such forms appear attractive in reference material. The final page must remain recognizably Style 09: concrete business meaning first, editorial hierarchy second, decoration last.

[Hard constraints]
Render only the PowerPoint body visual on a 2048x1024 canvas.
Do not render title, subtitle, logo, page number, footer, or template frame.
Do not render instructions, field labels, source references, evidence ids, or text ids.
Do not invent visible business facts, numbers, organizations, actors, or conclusions.
Do not change facts, numbers, dates or units.
Do not change actors, responsibilities or status.
Do not add presentation copy that is not part of the approved locked text.
For a "label: sentence" locked text item, render it once as that unit; do not repeat the label alone as a separate heading or tag, and do not invent a heading or label for text that has none.
Do not map each body item to an isolated icon or decorative image.
Do not create an independent text wall or second result chain.
Reserve page title and subtitle for the external PowerPoint text layer; do not render them in the body image.
Do not render the nodes as equal-weight peer cards; the declared relationship is not a flat list.
Do not invent a center hub or radial mechanism the declared relationship does not describe.
Preserve the approved source actors, relationships, conditions, status, and factual strength without reinterpretation.

【风格09最终执行锁｜最高优先级】
Treat the generated image as a reconstruction-friendly, editorial visual blueprint for editable PowerPoint conversion — keep the overall composition disciplined and magazine-orderly. Keep all locked Chinese text complete, unchanged and readable in clean high-contrast text-safe zones with stable geometry; place labels adjacent to the related object rather than baking them into screens, devices, icons or perspective surfaces. Icon count is zero by default.

Do not use arrows or arrowheads anywhere on the page. Express every relationship through position, proximity, grouping, numbering or a plain undirected line, never a pointed or directional connector. A line still must stand for one relationship named in the reading path; adjacency or enumeration alone is not a declared relationship.

Every scene, object or fragment must be traceable to a named actor, service, asset or outcome that actually appears on this page; if it cannot be tied to specific content here, remove it rather than keep it as ambience — do not substitute a generic senior-office tableau for content-specific imagery.

默认不出现人物；禁止正脸、围桌会议、多人讨论及摆拍办公场景。

Do not depict organization names, logos, seals, signage, recognizable headquarters or landmarks. Keep real organization and person names in the editable text layer only. Generic, non-location-specific facilities, layered workspaces, control consoles, equipment rooms, and industrial scenes may be used as illustrative carriers when they map to the locked content. Schematic screens, charts, maps, and interface labels may organize the composition, but generated values are non-evidentiary; factual numbers and labels must be verified and remain editable.

Render the page's locked on-screen text faithfully in the main composition. Auxiliary semantic imagery may use a small amount of clear Chinese labels, interface text, chart labels, or document wording when it directly clarifies the nearby business object or relationship. Do not add unrelated decorative text, dense pseudo-Chinese, or text that pretends to be factual evidence; keep supporting text subordinate to the page's locked on-screen text.

线条：主关系用细、实、方向一致的深蓝线；反馈或复盘最多一条浅灰短虚线，虚线不作装饰节点链、不沿页面三边绕行，也不同时承担边框、回流和装饰；每条线必须落在对象外边界，圆点只用于真实接口、汇聚或分支，禁止线端悬空、靠近但不接触或跨越文字。边框：整页可见边界最多两级，只用细线直角矩形或开放平面色场表达业务范围与必要子组；组内项目优先用留白、对齐、浅色底或短分隔线，不逐项完整套框；禁止胶囊、厚框、梯形、切角、异形、玻璃舱和立体门框。箭头：禁止使用，关系优先通过邻接、对齐、包含、留白和颜色表达；确需连线时只用细实线，不加箭头头，闭环用开放路径或短回接线。形状：默认使用平面直角矩形、开放色场和低矮哑光正视微立体，同页异形标题条最多一个；低矮平台只在平台承载、分层支撑或汇聚中枢语义明确时使用，且不得兼作页面外框、标题底座和装饰舞台；禁止徽章、盾牌、圆盘、梯形、六边形、切角容器、厚底座、多层台阶、夸张挤出和复杂光效；锁定内容未明确要求时，不生成对勾、警告三角、循环图标、定位针、盾牌或装饰性连续箭头。颜色：深蓝表达主关系和结论，浅蓝灰承载辅助信息，暖色只标记风险、异常、限制、禁止或待处理状态；不得仅为区分类目自动分配多色或彩虹色。
边框、分隔线、连接线、箭头和几何形状须体现精密矢量级工艺——线条粗细全程一致、直角平直、曲线圆滑连续无棱角抖动、边缘干净无锯齿，同一图形家族的圆角半径保持统一；多层堆叠色块须对齐同一网格、间距均匀，若使用分层立体效果须保持对称克制，禁止交错错位投影、锯齿状或不均匀阴影边缘；边框与连接线应呈现如专业矢量工具绘制的精度，禁止手绘感抖动线、粗细不均、转角处衔接错位或断裂。盾牌、立体等距图标等具象元素本身不受限制，可正常按语义使用，只需与整体精致优雅的线条工艺保持一致。若上屏文字本身已带有序号前缀（如①②③或数字编号），不得再额外绘制独立的装饰性数字徽章、圆盘或序号标记来重复表达同一序号；每个步骤/阶段的序号只呈现一次。线条与边框的"精密"只针对笔画本身的干净度（不歪、不抖、边缘清晰），不等于全页处处等大、等距、等圆角；禁止为了显得规整就把所有卡片、图标、连接线做成完全相同的尺寸和间距、套成一个僵硬的网格；应保留非对称留白、按内容重要性调整大小和视觉权重，让版式呈现高级编辑排版的手工节奏感，而不是模板化图表网格。

## 扩展风格10：纯白 + 深蓝领导汇报（与风格9相同，仅编号不同）

默认8种风格仍保持1—8不变。风格10是仅供显式选择的扩展风格，可通过 ID `10` 调用，不进入默认候选。

Palette: pure white background #FFFFFF, deep blue #12355B, title #101820, body #303030, secondary #6F7275, divider #C9CDD1.

Create an executive briefing page in a scene-led editorial business-infographic style: authoritative, calm, refined, content-led and ready for formal presentation.

### 1. Style identity and semantic principle — hard

Build the page from recognizable business scenes, concrete objects, visible actions, evidence and outcomes; it should first communicate one clear business judgment, then reveal its supporting structure. Use abstract geometry, boundaries, color fields and connectors only to organize concrete meaning — do not let icons, decorative symbols or 3D objects become the page-level visual language when a recognizable scene or object can carry the meaning.

Keep the visual character editorial and matte — a refined executive-report spread, not a technology advertisement or icon-driven infographic.
Use pure white `#FFFFFF` as the page-level background. Do not shift the overall canvas toward ivory, cream, beige or warm paper tones. Pale blue-grey may be used only for local separation, evidence fields or subtle structural grouping.

### 2. Semantic anchor and composition — hard

1. Identify the page’s core judgment and primary business relationship.
2. Select one recognizable, page-specific business anchor: an operating scene, business object, content or data asset, professional work environment or visible outcome.
3. Give the dominant anchor approximately 35%–50% of the visual field when content permits.
4. Build one continuous, asymmetric and unequally weighted composition around it.
5. Organize two to five open semantic regions around, within or along the dominant anchor. These regions share one visual field and do not require independent cards or icon containers.
6. Use one or two large semantic actions to show comparison, convergence, transformation, separation, support, control, approval or result.
7. Complete the reading path with one clearly emphasized judgment or outcome region.
8. Do not use arrows anywhere on the page; express relationships through position, proximity, grouping or numbering, using a plain undirected line only if truly necessary.

Create hierarchy through crop, overlap, scale contrast, tonal separation, alignment, deep-blue emphasis and shallow foreground–background relationships.

Do not distribute content according to item count. Three, four or five text items do not automatically require equal columns, equal rows or equally detailed stages. The core judgment carries the greatest visual weight; supporting evidence remains quieter and subordinate.

Suitable anchors include: source materials parsed into one structured object; two fields compared around one visible gap; several inputs converging into one result; one operational environment showing monitoring or coordinated action.

### 3. Content fidelity and presentation expression — hard

Preserve the full factual meaning, core judgments, named entities, numbers, dates, units, causal relationships, conditional relationships, comparison relationships, scope boundaries and business logic of the provided Chinese content.

Do not add new facts, invent numbers, strengthen or weaken conclusions, change responsibility boundaries, alter policy meaning, omit required content or introduce unsupported labels. Do not shift modal strength while treating the wording as equivalent: do not turn a possibility into a certainty, a suggestion into a requirement, an exploratory or pilot description into a completed achievement, or a conditional statement into an unconditional conclusion.

Unless a passage is explicitly marked as verbatim text, locked text, quoted source text, formal name, number, metric, policy wording or other exact wording, the visible Chinese wording may be restructured for presentation readability.

Allowed presentation restructuring includes: splitting a long sentence into shorter presentation-scale statements; creating a short lead-in or micro-heading from wording already present in the source meaning; reorganizing parallel phrases into clearer visual levels; moving a qualifying phrase closer to the statement it qualifies; emphasizing key terms through weight, scale or deep-blue treatment; and reducing redundant function words when the factual meaning remains fully intact.

Every key metric number in the locked text (a count, percentage or threshold) must be visually emphasized through larger scale and deep-blue color directly inside its original sentence — plain body-text weight is not sufficient; never duplicate it as a separate large-number tile, badge or callout outside that sentence.

Presentation restructuring must improve hierarchy, rhythm and readability without changing semantic force. No factual meaning may be added, removed, narrowed, broadened, weakened or strengthened.

#### Verbatim text — hard when marked

Content explicitly marked as verbatim text, locked text, quoted source wording, official titles, formal product or institution names, numbers, units, dates, policy clauses or other exact wording must remain complete and unchanged.

Do not rewrite, shorten, relabel, reorder or paraphrase explicitly verbatim content.

#### Presentation-scale text layout

Allocate sufficient space for content before adding scenes, evidence, icons or decoration.

Use one clear readable text region for each primary semantic unit; regions do not need matching size or position — content weight decides how each is shaped, and a generic scene must not crowd text into a minor corner.

Keep body text at normal senior-presentation reading scale. If space is limited, simplify the scene or reorganize the wording — never shrink text into microcopy.

Render only source-supported Chinese content. Screens, documents and interfaces may contain large text-free structures, highlighted regions, check states or simplified diagrams, but must not contain invented readable microtext.

Each primary semantic region should read as one integrated unit of text and visual material. When a small supporting fragment genuinely clarifies one region, draw it from real business material relevant to that specific region — expressed in whatever concrete, recognizable form actually suits the content — rather than a symbolic icon or pictogram, and never repeat the same kind of fragment as a matching pair across every parallel region (see the icon discipline rules below). Regions do not have to be forced into perfectly equal treatment: some may carry a fuller scene-plus-text-plus-action unit, others may lean more on text with a lighter visual touch, depending on what each region's content actually needs.

Place text inside a quiet field within the scene, attach it to an object edge, align it with the corresponding action, or embed it in the outcome region. Visual splitting, line breaks and grouping must not alter the original sentence's logical relationship (for example turning a causal or conditional link into a flat parallel list). Font size, weight, color and position must not create a visual conclusion strength that misrepresents the source: a minor qualifier must not be made visually more prominent than the primary judgment it qualifies.

The governing principle is: factual fidelity is fixed; presentation wording and hierarchy may adapt to improve executive readability.

### 4. Reusable composition grammars

Select one primary grammar from the page semantics. Use a second only when the locked content clearly contains a second essential relationship.

#### A. Continuous object transformation

Show one recognizable business object changing through input, processing, review, control or output, expressed through object state and spatial progression — not step cards or icon rows.

#### B. Core scene with attached actions

Place one business object or operating environment in the main visual region. Attach supporting capabilities, conditions or outcomes directly to the scene through spatial relationship and unequal scale — not as separate icon modules.

#### C. Dual-field comparison

Use two concrete business fields or states in a controlled comparison; show the difference or transition through scale, alignment and one decisive judgment region — prefer concrete fields over symbolic icon comparisons.

#### D. Multi-source convergence

Show several distinct sources or actors entering one shared service, capability or result, through visible convergence into one dominant outcome field — concrete inputs, not a row of pictograms.

#### E. Concrete controlled containment

Place one recognizable protected object or operating scene inside a controlled field. Express access, isolation and approved output through checkpoints and state changes; keep the object visible, boundaries subordinate.

#### F. Parallel-direction shared evidence field

When the page names several parallel abstract directions or principles that share one evaluation or classification framework, do not give each direction its own icon or scene fragment. Instead let a small number of genuine evidence fragments serve the framework as a whole, choosing how many and where to place them based on what this page's specific content actually supports — some directions may carry a concrete fragment and others may rely on text hierarchy and spatial grouping alone; a page whose directions are too abstract for any genuine evidence may use none at all rather than inventing one.

### 5. Scene and evidence expression

Use one dominant scene or concrete business object, plus two to four quieter supporting scene or evidence fragments when needed. Vary scale, crop and viewpoint so the page reads as one composed visual field rather than assembled modules.

Create richness through semantic scene selection, cropping, scale and viewpoint changes — richness should come from meaningful business expression, not decorative objects.

When the page names several distinct top-level items, each item's own visual material must be specific enough that a viewer can tell which item it belongs to at a glance — not just that the page is generally about data or technology. Do not represent distinct named items with one shared undifferentiated panorama; give each its own recognizable fragment. If the items are abstract directions with no distinct concrete referent, drop the scene entirely and use a flat, structured relationship field instead.

Suitable visual material includes: professional operating environments; controlled content objects or data assets; documents in transformation; industry facilities; close-up evidence fragments. Any chosen anchor or fragment must depict something actually named in this page's content — never a generic control room, dashboard wall or stock BI screen used as decoration; with no distinct concrete referent among the locked content, prefer the flat structured relationship field over a generic technology scene.

Realistic or restrained semi-realistic materials are acceptable when they strengthen page-specific meaning. A workspace, device or interface must visibly demonstrate the relevant action or state, as supporting evidence inside a broader scene, not an isolated product.

### 6. Depth, material and icon discipline — hard

Maintain a restrained flat editorial foundation with shallow natural depth, created through overlap, cropping, scale contrast, tonal separation and subtle variations of pure white, pale blue-grey and deep blue.

Use matte surfaces, crisp edges and gentle tonal transitions; keep perspective natural and quiet.

Avoid glossy or decorative 3D rendering, exaggerated isometric perspective, cinematic depth, dramatic spotlighting, floating hero objects, glassmorphism, polished metal, reflective floors, neon glow, luminous edges and product-showcase presentation.

Visible drop shadows are generally discouraged; if needed, use an extremely soft, diffuse shadow. Business objects may retain natural physical form but must not be stylized into exhibition objects, toy-like miniatures or futuristic product concepts.

Icons are not a default visual language for Style 09. Start from zero icons.

Use an icon only when the page would lose immediate semantic clarity without it. A typical page should contain no icons; when genuinely necessary, use at most one very small, flat, deep-blue icon embedded inside an existing scene or text grouping.

Never assign one icon to each bullet, module, stage, actor, capability or message. Do not create icon rows, icon grids, icon walls, icon badges, icon cards, pictogram sequences or decorative symbol clusters. When a page presents several parallel metric lines or several parallel named directions or principles (for example four evaluation dimensions), do not place any icon, pictogram or colored glyph immediately beside each individual line; a row of icon-plus-label pairs is itself an icon wall even without visible borders, and remains forbidden.

Icons must never become the main visual carrier or repeated page structure. If a business meaning can be expressed through a scene, object or outcome region, remove the icon and use the concrete expression instead.

If one icon is indispensable, keep it simple, flat, deep blue, small and visually subordinate. Avoid 3D, gradient, glossy or holographic icon treatments.

### 7. Semantic economy and final priority — hard

Represent each source-supported concept once; supporting elements may add evidence or outcome, but must not restate the same label, sequence or conclusion.

When the composition already expresses a process, hierarchy or layered relationship, do not add a second icon chain, footer process or extra summary band unless explicitly required by the source content.

Use one primary visual metaphor per page; express remaining relationships through scene state, position, scale, crop, color fields and purposeful connectors, not a left-structure + right-explanation + bottom-summary formula.

Keep the result free from icon-led modular layouts, repeated device mockups, dense microtext and duplicated semantic summaries, and from any SaaS-marketing, app-store-style or futuristic 3D concept-art visual language (see the material and icon discipline rules above for the full decoration exclusion list). These exclusions are secondary: always prioritize content fidelity, recognizable business anchoring, open scene-led composition, semantic clarity, restrained editorial flatness and executive-level visual hierarchy.

Priority:
content fidelity, verbatim requirements and core judgment
→ recognizable business anchor
→ primary business relationship
→ large-scale semantic actions
→ evidence and outcomes
→ crop, overlap and shallow tonal depth
→ auxiliary symbols only when indispensable.

Final result: one calm, highly readable and visually refined executive-report composition with complete factual meaning and all required verbatim text, a recognizable business scene or object, open semantic grouping, clear page-specific meaning, strong hierarchy, restrained natural depth, minimal or zero icon use, no showy 3D rendering and no unnecessary semantic repetition.

### 8. Authority lock — hard

This Style 09 definition is the controlling visual authority for every page that selects it. Reference images may influence palette, crop and polish only, never the semantic structure, content fidelity, composition grammar or icon discipline defined above. When a conflict arises, remove the lower-priority decorative element and keep the higher-priority rule, in the order already stated in Section 7's priority list.

Do not reinterpret Style 09 into a card dashboard, icon infographic, SaaS marketing page or glossy 3D composition, even when such forms appear attractive in reference material. The final page must remain recognizably Style 09: concrete business meaning first, editorial hierarchy second, decoration last.

[Hard constraints]
Render only the PowerPoint body visual on a 2048x1024 canvas.
Do not render title, subtitle, logo, page number, footer, or template frame.
Do not render instructions, field labels, source references, evidence ids, or text ids.
Do not invent visible business facts, numbers, organizations, actors, or conclusions.
Do not change facts, numbers, dates or units.
Do not change actors, responsibilities or status.
Do not add presentation copy that is not part of the approved locked text.
For a "label: sentence" locked text item, render it once as that unit; do not repeat the label alone as a separate heading or tag, and do not invent a heading or label for text that has none.
Do not map each body item to an isolated icon or decorative image.
Do not create an independent text wall or second result chain.
Reserve page title and subtitle for the external PowerPoint text layer; do not render them in the body image.
Do not render the nodes as equal-weight peer cards; the declared relationship is not a flat list.
Do not invent a center hub or radial mechanism the declared relationship does not describe.
Preserve the approved source actors, relationships, conditions, status, and factual strength without reinterpretation.

【风格09最终执行锁｜最高优先级】
Treat the generated image as a reconstruction-friendly, editorial visual blueprint for editable PowerPoint conversion — keep the overall composition disciplined and magazine-orderly. Keep all locked Chinese text complete, unchanged and readable in clean high-contrast text-safe zones with stable geometry; place labels adjacent to the related object rather than baking them into screens, devices, icons or perspective surfaces. Icon count is zero by default.

Do not use arrows or arrowheads anywhere on the page. Express every relationship through position, proximity, grouping, numbering or a plain undirected line, never a pointed or directional connector. A line still must stand for one relationship named in the reading path; adjacency or enumeration alone is not a declared relationship.

Every scene, object or fragment must be traceable to a named actor, service, asset or outcome that actually appears on this page; if it cannot be tied to specific content here, remove it rather than keep it as ambience — do not substitute a generic senior-office tableau for content-specific imagery.

默认不出现人物；禁止正脸、围桌会议、多人讨论及摆拍办公场景。

Do not depict organization names, logos, seals, signage, recognizable headquarters or landmarks. Keep real organization and person names in the editable text layer only. Generic, non-location-specific facilities, layered workspaces, control consoles, equipment rooms, and industrial scenes may be used as illustrative carriers when they map to the locked content. Schematic screens, charts, maps, and interface labels may organize the composition, but generated values are non-evidentiary; factual numbers and labels must be verified and remain editable.

Render the page's locked on-screen text faithfully in the main composition. Auxiliary semantic imagery may use a small amount of clear Chinese labels, interface text, chart labels, or document wording when it directly clarifies the nearby business object or relationship. Do not add unrelated decorative text, dense pseudo-Chinese, or text that pretends to be factual evidence; keep supporting text subordinate to the page's locked on-screen text.

线条：主关系用细、实、方向一致的深蓝线；反馈或复盘最多一条浅灰短虚线，虚线不作装饰节点链、不沿页面三边绕行，也不同时承担边框、回流和装饰；每条线必须落在对象外边界，圆点只用于真实接口、汇聚或分支，禁止线端悬空、靠近但不接触或跨越文字。边框：整页可见边界最多两级，只用细线直角矩形或开放平面色场表达业务范围与必要子组；组内项目优先用留白、对齐、浅色底或短分隔线，不逐项完整套框；禁止胶囊、厚框、梯形、切角、异形、玻璃舱和立体门框。箭头：禁止使用，关系优先通过邻接、对齐、包含、留白和颜色表达；确需连线时只用细实线，不加箭头头，闭环用开放路径或短回接线。形状：默认使用平面直角矩形、开放色场和低矮哑光正视微立体，同页异形标题条最多一个；低矮平台只在平台承载、分层支撑或汇聚中枢语义明确时使用，且不得兼作页面外框、标题底座和装饰舞台；禁止徽章、盾牌、圆盘、梯形、六边形、切角容器、厚底座、多层台阶、夸张挤出和复杂光效；锁定内容未明确要求时，不生成对勾、警告三角、循环图标、定位针、盾牌或装饰性连续箭头。颜色：深蓝表达主关系和结论，浅蓝灰承载辅助信息，暖色只标记风险、异常、限制、禁止或待处理状态；不得仅为区分类目自动分配多色或彩虹色。
边框、分隔线、连接线、箭头和几何形状须体现精密矢量级工艺——线条粗细全程一致、直角平直、曲线圆滑连续无棱角抖动、边缘干净无锯齿，同一图形家族的圆角半径保持统一；多层堆叠色块须对齐同一网格、间距均匀，若使用分层立体效果须保持对称克制，禁止交错错位投影、锯齿状或不均匀阴影边缘；边框与连接线应呈现如专业矢量工具绘制的精度，禁止手绘感抖动线、粗细不均、转角处衔接错位或断裂。盾牌、立体等距图标等具象元素本身不受限制，可正常按语义使用，只需与整体精致优雅的线条工艺保持一致。若上屏文字本身已带有序号前缀（如①②③或数字编号），不得再额外绘制独立的装饰性数字徽章、圆盘或序号标记来重复表达同一序号；每个步骤/阶段的序号只呈现一次。线条与边框的"精密"只针对笔画本身的干净度（不歪、不抖、边缘清晰），不等于全页处处等大、等距、等圆角；禁止为了显得规整就把所有卡片、图标、连接线做成完全相同的尺寸和间距、套成一个僵硬的网格；应保留非对称留白、按内容重要性调整大小和视觉权重，让版式呈现高级编辑排版的手工节奏感，而不是模板化图表网格。

