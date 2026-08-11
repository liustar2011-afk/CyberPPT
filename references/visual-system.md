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
- 通用图标策略：仅当所选视觉风格允许普通概念图标时，才从 `chunk-filled`、`tabler-filled`、`tabler-outline` 或 `phosphor-duotone` 中锁定一个 stylistic library；`simple-icons` 仅作为真实品牌 logo 例外。对于明确采用“无图标优先”的视觉风格（如风格09），记录 `icon_policy=none_by_default`，不得预先锁定普通概念图标库；仅当页面脚本明确要求某个具体图标或符号时，才为该页登记例外。

不要只因为颜色好看就批准风格。网格、密度、层级、图表语言和留白行为共同定义视觉系统。

图标风格属于视觉系统，但并非所有视觉系统都必须使用图标。第二阶段锁定视觉方向后，应先记录 `icon_policy`。仅当 `icon_policy=allowed` 时才锁定通用图标库，第三阶段不得跨库混用普通概念图标；若 `icon_policy=none_by_default`，第二阶段与第三阶段不得为了“视觉丰富度”“语义识别”或“模块区分”主动补充普通概念图标。只有页面脚本明确指定的图标或符号才可作为例外，并须保持小型、从属且不决定构图。

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

## 扩展风格9：纯白 + 深蓝领导汇报

默认8种风格仍保持1—8不变。风格9仅供显式选择，可通过 ID `9` 或 slug `ivory_deep_blue_scene` 调用。

Palette: pure white #FFFFFF, deep blue #12355B, title #101820, body #303030, secondary #6F7275, divider #C9CDD1.

Identity: senior leadership briefing / speech-support — editorial, restrained, content-led.

### 核心视觉语法

<!-- style09:scope=base -->

生成克制、清晰、高级的政企领导汇报页。优先使用可识别的业务场景、具体对象、动作、证据和结果；抽象主题则使用开放、非对称的平面2D编辑式关系场。当平台、中枢、引擎、中心等本身就是页面明确表达的业务对象时，可以成为中心载体或主关系枢纽，但必须与真实业务对象、输入输出、边界和结果发生可读联系，不得退化为脱离语义的展台、圆盘装饰或夸张发光装置。

默认媒介是一处开放、连贯且具有行业辨识度的业务场或具体对象面；页面先读到行业环境中的业务动作、对象状态或受控结果，再读到与其就近结合的文字关系。主业务锚点优先由真实设施、设备、作业环境、人员动作、物流或信息流等可观察对象共同形成；页面明确要求的平台、中枢、引擎或中心可以组织这些对象和关系，但资料容器或通用办公物件不得替代实际业务过程。行业场景与文字共同构成主视觉，不预设单一对象必须占据大幅面；2—5个文字组分布在同一连续关系场中，不要求独立卡片、图标容器或抬高面。只有当页面语义确实没有可识别的行业环境、业务对象或动作时，才使用纯平面关系表达。

生成优先级：核心判断 → 行业环境与业务对象 → 业务动作、状态或结果 → 图文共同形成的主关系 → 辅助证据 → 必要连接。行业环境不是装饰或末端点缀，必须在有明确行业语义时参与承载主关系；后一级不得压过前一级，装饰原则上不主动增加。

- 每页只保留一个核心判断和一种主关系。
- **文字型视觉主线**：当锁定上屏文字中已有组标题、阶段名、关键判断或关键数字时，可选择少量内容以深蓝突出，并沿页面主要阅读路径形成连续主线；正文使用深灰或黑色，就近从属于对应引导项。细线、圆点或短分隔线只作轻量串联。不得把每条文字都染成深蓝，不得新增非锁定标签，也不得据此固定生成时间轴、卡片墙、左右分栏或等宽多列。
- 使用一组彼此关联的行业对象、动作或状态形成主业务锚点，配合2—5个就近嵌入场景的开放文字组及一个明确结果；不按条目数量机械均分，不另建大面积结果框。
- 用对齐、留白、比例、裁切、重叠、色块、局部边界和少量连接线表达汇聚、转化、对比、支撑、控制或输出。
- 保留页面所需的“收束”关系；其视觉方式优先采用对齐、色调、留白和连接关系。短连接箭头可以保留，但标签、色块和承载面必须是普通矩形或开放平面色场，不得做成梯形、切角、箭头带、徽章或异形几何容器。
- 保留页面所需的色块层次；色块优先作为普通平面色场使用，避免变成异形容器、厚重框体或装饰性立体模块。
- 实景可保留自然透视；信息图、关系图和语义结构以平面2D为主，允许极浅的微立体承载面、低浮雕层次或轻微前后关系，但必须正视、哑光、克制。
- 锁定中文必须完整、清晰、原序呈现；文字与行业场景同步规划空间，使文字贴近对应对象、动作、边界或结果，不得先切出独立文字区再把场景填入剩余区域，不生成伪中文或无关标签。
- 中文字体统一使用微软雅黑（Microsoft YaHei）；所有可读文字的视觉字号不得小于 14pt 等效尺寸。空间不足时应减少装饰、资料性物件和重复结构，并调整图文共同构图，不得通过缩小字体或挤压行业场景解决。
- **图文融合**：图形、场景或对象必须实际承载锁定文字中的业务对象、动作、状态或边界，文字就近附着并共同形成一条主关系。禁止图形区与文字区各自完整重复同一组内容；左右分区仅用于不同且互补的业务角色，并以共享对象、接口、流向或结果相连。禁止用抽象中心框、渐变底板和放射连线把文字列表伪装成关系图；删除视觉部分后若业务逻辑不变，应改用具体对象、连续业务场或方向与边界明确的平面关系场。
- 允许根据页面语义采用自然的图文布局，但避免刻意堆叠、过度分区和装饰性照片墙。
- 当无法找到有意义的场景或证据时，使用干净的平面2D关系表达，不强行添加照片或复杂视觉素材。
- 图标默认数量为零。只有页面脚本明确指定某个具体图标时才允许小型、扁平、从属地使用。
- 整体使用纯白、浅蓝灰与深蓝，保持编辑式不对称布局、平静留白和高层级可读性。

### 高端咨询报告构图

- 先把本页核心判断转化为一个明确的视觉命题，再决定场景、文字和连接；所有区域共同证明这一命题，不做“内容齐全但没有视觉重心”的资料汇编。
- 建立明显的三级权重：一个主视觉或主关系约占画面视觉注意力的40%—55%，一个关键判断或转折约占20%—30%，其余区域作为辅助证据。比例指视觉注意力，不要求画成固定分栏或矩形面积。
- 每个主要语义区域都可以有行业配图，但配图应通过近景与远景、完整场景与局部切片、清晰与弱化、大小与裁切形成节奏；至少一处行业场景采用大胆裁切或延伸至画面边缘，形成高质量报告封面级冲击力。
- 阅读主线优先使用非对称的斜向推进、前后景递进、由大到小的证据收束或沿真实业务流向的连续运动。除非页面语义明确要求中心辐射、循环或同心关系，否则禁止对称圆环、中央圆盘、四周均匀分布和上下等高横条。
- 文字层级像咨询报告而不是软件界面：核心判断短而醒目，组标题与对应对象紧密结合，正文克制地嵌入留白或轻量局部色场。避免每组都有相同边框、相同标题条、相同图标和相同尺寸。
- 用一个高对比深蓝焦点、少量方向线和大面积纯白或低纹理空间建立高级感；不以增加发光、渐变、仪表盘、图标数量或复杂装饰制造视觉冲击。

### 硬性禁令

- 禁止图标墙、图标行、图标网格、一条一图标、徽章、图标卡片和卡片墙。
- 禁止夸张厚重的展陈舞台、讲台、圆盘、圆柱、同心环、穹顶、胶囊及复杂光效；底部承载台、浅层基座或低浮雕关系面可以使用，但必须低矮、正视、哑光、无戏剧性透视。
- 禁止玻璃舱、透明壳、立方体、全息物体、金属镜面、霓虹、强辉光、悬浮物、明显挤出和装饰性3D。
- 禁止仪表盘、SaaS产品营销、应用商店、科技发布会、展陈和未来概念海报语言。
- 禁止重复表达同一语义，或额外添加底部总结链、第二套流程、装饰性模块。
- 禁止把文档、合同、报告、档案、文件夹、活页册、表单、屏幕或仪表盘作为大幅主锚点、页面底板或独立文字岛；此类资料对象仅可在语义确有需要时作为小型局部证据，不得替代行业设施、设备、环境、动作和状态。
- 禁止把页面切成“集中排字的一大区”和“孤立配图的另一大区”；文字必须沿行业对象、动作、接口、边界或结果分布，图形与文字共同完成同一条主关系。

### 重复表达压制（硬约束）

- 同一页每个核心概念只允许一个主文字载体和一个主要图形承载面；不得把同一标题、阶段名、能力层或结论在另一侧再次完整复述。
- 若主构图已经表达某条业务关系或结果链，禁止再生成第二套同类关系结构、并行能力层、重复总结区或回顾性副本。
- 视觉状态只能补充文字未表达的对象、动作、边界或结果，不得把同一句话改写后再画成第二个模块、流程或卡片。
- 两个模块回答同一问题时，合并为一条更强的图文关系并删除较弱者；优先保留行业场景、留白和单一结果，不以扩大承载面、缩小文字或增加卡片解决重复。

### 机械表达控制

避免把页面机械化为等权模块、重复卡片、密集表格、连续箭头或装饰性流程。不要为了整齐而牺牲语义主次，结构应服务于业务关系、对象状态、动作、证据和结果。

当多个输入、输出或节点承担不同业务角色时，必须用对象、状态、材质或空间位置把角色区分开；不得把不同角色复制成同一种设备、同一种几何符号或同一种装饰。只有源内容明确表示同类对象时，才允许重复同一视觉载体。

### 基础组件表达规范（通用）

<!-- style09:scope=base-and-qa -->

以下规则只精细化已经形成的视觉表达，不得据此改变页面的业务结构、元素数量、空间关系、阅读路径或主次关系，也不得新增、删除或重排关系。

- **线条**：保持纤细、匀净、连续，主线可比辅线略粗，但同类线宽必须一致；直线端点、折点和曲线切线要干净，无毛刺、断裂、突兀折角、双线、外发光或描边叠影。连接线必须避开文字、数字和关键对象，线端准确接触对象边界，不悬空、不穿透、不停在边界附近；接口圆点仅在原有关系需要时使用，并与线端同心对齐。
- **边框**：仅当业务关系已经需要局部边界时，保留必要边界并优化描边质量；本规则不得诱导新增、放大或复制容器。边框使用细、低对比、单层描边；同一层级的线宽、颜色、透明度及圆角或直角处理保持一致。边缘清晰但不抢文字，不使用双描边、高亮轮廓、发光、厚阴影、内外多重描边或立体门框；局部开放边界的断口应整齐，并与内容对齐。
- **箭头**：保留已经确定的方向、数量和连接关系，只优化箭身与箭头头。箭身细而等宽，曲线转向平滑、切线连续；箭头头使用贴近线端的小型简洁三角形，与箭身同轴，宽度不明显超过线宽的2—3倍，尖端准确落在目标边界。不得出现粗大箭头头、宽箭头带、渐变块箭头、双层箭头、发光、阴影、立体挤出或箭头与线身脱节；跨越或转折处保持足够净空，不压文字、不擦边。
- **形状**：仅优化业务关系确有需要的局部形状、表面与边缘；不得据此新增大底板、资料容器、独立文字面或扩大既有载体面积。同层必要形状的直角或圆角、描边、明度和厚度保持一致；平面色场边缘清楚，必要的微立体关系面保持低矮、正视、哑光，仅用极浅的前后差。不得把结果区、关系面或平台加厚成展台、多层底座或台阶，不增加高光金属边、玻璃质感、夸张倒角、挤出、悬浮和复杂光效。
- **颜色角色**：不改变既有信息主次和色块面积关系。深蓝用于主关系和关键结论，浅蓝灰用于辅助信息与背景承载；同一语义角色保持同色，同层色块保持接近的饱和度和明度。暖色只标记风险、异常、限制、禁止或待处理状态；避免大面积高饱和蓝、霓虹蓝、彩虹分类、无语义渐变和高亮描边，确保文字与承载面有稳定、清晰的对比。
- **层次**：保留已经确定的前后关系与视觉重心，只用明度差、边缘清晰度、局部色场、轻微重叠和极浅阴影做精细区分。前景边缘与对比略清晰，背景承载面更轻、更弱；同层阴影方向、软硬和透明度保持一致，阴影不得形成厚度错觉、黑边或悬浮感。不得通过多层套框、连续抬高、重复底板或新增底座制造层次。

### 条件构图规则（编译器按需选择）

<!-- style09:scope=conditional -->

以下规则由编译器按页面实际语义标签选择，可组合命中；未命中的小节不进入该页 ImageGen Prompt。

#### 多行正文或多个维度

semantic_tags: [dense_text, multi_dimension]

把内容组织为一个连续且具有行业辨识度的业务场，优先选择真实设施、设备、作业环境、人员动作、物流或信息流共同承载核心判断，让文字组贴近对应对象、动作、接口、边界或结果自然展开。正文很多时通过减少装饰、资料性物件和重复结构，并调整文字在行业场景中的分布来解决密度；不得扩大单一文件、合同、报告、屏幕、面板或其他资料容器，不得把它们变成页面底板、大幅主对象或独立文字区。整页可由同一行业环境中的多个关联对象共同成景，并只保留必要的小型证据碎片。
#### 分类或矩阵

semantic_tags: [classification, matrix]

用不等宽、不等高、开放边缘、局部色场、重叠和少量连接线组织分类关系，不默认做成等宽表格、泳道、卡片墙或铺满整页的规则网格。允许局部保留必要的平面结构，但它只从属于主业务工作面，并且只保留能说明主判断的部分。

#### 步骤、流程或输入输出

semantic_tags: [flow, input_output, sequence]

让流程或环节依附于同一业务对象或连续路径的状态变化，不自动画成编号圆点、连续箭头节点链、等宽阶段框或步骤卡。不同输入、输出或节点承担不同业务角色时，用位置、状态、色调或材质区分；只有源内容明确表示同类对象时才适度重复同一载体。

#### 权利边界

semantic_tags: [boundary, authorization]

把权利、责任、准入、控制或使用范围表达为与业务对象直接相关的边界、门控、内外位置或受控状态，不把每条边界要求重复套成独立小框，也不额外生成第二套说明链。

#### 闭环语义

semantic_tags: [feedback, loop]

仅当源内容明确出现“闭环”“闭合”“循环”或反馈回接关系时，才使用偏向一侧的开放路径、对象状态回到起点或短回接线；不得直接绘制完整圆环、环形节点、中心辐射、圆形流程图或仪表盘。只有源内容明确要求离散图表时才局部使用。

### Final ImageGen execution lock — hard

<!-- style09:scope=terminal -->

This block must be repeated verbatim at the absolute end of every Style 09 ImageGen prompt and overrides conflicting carrier language elsewhere:

保持扁平2D、无图标优先和克制政企气质，呈现高端咨询报告的判断力、编辑感和视觉冲击。先确定一个视觉命题和唯一阅读主线，再组织一个占主导的行业场景或主关系、一个关键判断或转折、若干从属证据；不得让所有区域等权。有明确行业语义时，可配置与主关系直接相关的多处行业配图或对象，每个主要语义区域都可以有配图，不得退化成纯文字；但每一处图片、对象或场景都必须明确承担至少一个锁定文字组中的业务对象、动作、状态、边界或结果，并与对应文字就近附着、穿插或共同形成关系。允许一句主要判断、一个业务动作或一个重要明细拥有一张独立配图，不得为了减少图片数量而强行合并或压缩有明确语义价值的配图；判断标准不是“一句话一张图”的数量，而是图片是否真正解释对应文字，以及多图之间是否形成清晰主次和阅读主线。无法指出所对应锁定文字组的图片不得出现，尤其不得把泛行业照片铺在页边、页角或底层充当气氛装饰，再用独立白底文字区承载全部信息；应删除无语义装饰，把面积让给真正解释主关系的场景、对象和文字。多处配图必须通过大胆裁切、大小差、前后景、清晰度和跨区流向形成三级权重，至少一处真实行业场景延伸至画面边缘。优先采用非对称斜向推进、前后递进、由大到小收束或沿真实业务流向的连续运动；除非语义明确要求中心辐射或循环，否则不得使用对称圆环、中央圆盘、均匀四象限或上下等高横条。文字贴近对应对象、动作、接口、边界和结果，可使用少量轻量局部承载面，但不得形成等权卡片墙、相同标题条或软件界面式模块。文档、合同、报告、文件夹、表单、屏幕和仪表盘仅可作为小型证据细节，全部合计不得压过主要行业场景。若提供风格参考图，只继承色彩、材质、留白、字体层级和编辑节奏，不复制其具体物件或固定分区。允许一个必要收束区，但不得放在底部通栏重复全文结论。页面语义、锁定文字和唯一视觉命题优先于装饰与固定版式。
配图粒度必须跟随语义粒度。一张大场景只有在其中可识别的对象、动作或流向能够同时解释多个文字组及其关系时才可合并承载；否则应为主要文字组配置各自贴合的语义场景、对象切片或关系画面。不得用只证明行业身份的全景照片替代对具体业务对象、动作、状态和结果的表达。

## 扩展风格10：象牙白 + 深蓝双层语义汇报2

默认8种风格仍保持1—8不变。风格10是仅供显式选择的扩展风格，可通过 ID `10` 调用，不进入默认候选。

Palette: ivory #F7F6F0, deep blue #12355B, title #101820, body #303030, secondary #6F7275, divider #C9CDD1.

Create a high-end senior leadership briefing page in a structured editorial business-infographic style: authoritative, calm, polished, content-led and presentation-ready.

Build one integrated, asymmetric and unequally weighted composition with one dominant judgment and one clear reading path. Use one main page-level structure, two to five primary content regions, one outcome or conclusion region, and only a few essential connectors. Derive the composition from the actual page semantics rather than from the number of text items.

Locked Chinese text — hard:

Keep all locked Chinese text complete, unchanged and in its original order. Do not summarize, rewrite, shorten, relabel or convert paragraphs into compressed tags. Allocate space for the locked text before adding scenes, evidence, icons or decoration.

Use one complete and clearly readable text region for each primary content region. Do not split one paragraph across several small boxes. Keep body text at normal senior-presentation reading scale, visually equivalent to approximately 24–30 px at 1280 × 720. Do not create miniature captions, secondary microcopy or dense annotation layers.

Place the locked text directly beside, above, below or partially within the related business object or scene, so text and visual material form one semantic unit. Make their relationship visible through shared geometry, alignment, proximity, grouping or short connectors.

Scene-supported semantic expression:

Prefer realistic or semi-realistic scenes with page-specific business meaning. Each scene must visibly communicate the corresponding business action, transformation, judgment or outcome, rather than merely showing a related office, device, document pile or workplace.

Express each primary business action through one dominant large-scale semantic structure and, only when necessary, one supporting evidence object. Use no more than two semantic visual elements within one primary content region.

Translate business meaning into presentation-scale forms, such as:

- heterogeneous source materials converging into one structured outline;
- two knowledge or evidence fields compared with one clearly highlighted gap;
- several conditions feeding one content blueprint that produces distinct outputs;
- one content object moving through review, approval, use and feedback;
- multiple foundations jointly supporting one shared judgment;
- a controlled boundary separating inputs, processing and approved outputs.

Use large shapes, clear grouping, selective highlights, controlled overlap, restrained directional extension and short thin connectors. The semantic meaning must remain legible from normal presentation viewing distance.

Do not express meaning mainly through miniature document pages, file-browser lists, dense tables, multi-row matrices, full software interfaces, repeated dashboard panels or collections of small screenshots. Screens, documents and charts should function as simplified semantic objects, not as containers for detailed information.

Text and semantic evidence discipline — hard:

Render only the locked Chinese text explicitly provided in the page script. Do not invent additional titles, labels, captions, numbers, footnotes, interface copy, document paragraphs, signage or decorative microtext.

Screens, documents, charts and interfaces may contain clear text-free visual structures, including large blocks, major sections, highlighted differences, check states, approval marks, contrast regions, output groups and simplified diagrams. Do not use blank or generic screens when a screen is expected to explain a business action, but do not fill it with readable microtext.

When space is insufficient, simplify the composition, reduce scene detail, remove supporting evidence, enlarge the text region or reduce the number of visual fragments. Never solve space pressure by shrinking the locked text, splitting it into tiny fragments or adding smaller explanatory text.

Component and hierarchy discipline:

Use:

- one dominant page-level structure;
- two to five primary content regions;
- one large semantic object per region;
- at most one supporting evidence object per region;
- no more than four to six essential connectors across the page;
- no more than one or two small auxiliary icons on a typical page.

Do not automatically translate four text items into four equal columns, four equal rows or four equally detailed stages. Use unequal width, scale, density and visual weight according to the page judgment. The core judgment or principal business relationship must dominate; supporting regions remain quieter and subordinate.

Icons are optional and strictly secondary. Keep them small, simple, deep blue and embedded within an existing text, scene or business region. Do not give icons independent cards, circular badges, decorative containers or dedicated display areas. Icons must not determine the composition, create extra modules, form icon rows or replace semantic scenes.

Screens and devices may appear only as supporting evidence inside a broader working or operational scene. Avoid repeated devices, isolated UI screenshots, dashboards, SaaS interfaces and product-display layouts.

Use broad flat fields, ivory or white content regions, deep-blue headings, thin dividers, restrained connectors, matte materials and very shallow depth.

Avoid equal card walls, equal modular grids, left-text / center-image / right-text layouts, panoramic posters, giant hero illustrations, abstract data landscapes, dense flowing-line fields, radial hubs, generic timelines, step-card sequences, software-architecture diagrams, icon grids, glossy 3D objects, glassmorphism, neon glow and floating icons.

People should be absent or minimal. Reference images may inform palette, spacing, scene mood, material restraint and overall polish only; do not copy their fixed layout scaffold.

Priority: locked Chinese text and core judgment → business relationships → large-scale semantic scenes and objects → evidence and outcomes → boundaries and connectors → auxiliary symbols.

Final result: a calm, highly readable executive-report page with complete locked text, strong hierarchy, few components, page-specific semantic scenes, large-scale visual meaning and no invented or unreadable microtext.
