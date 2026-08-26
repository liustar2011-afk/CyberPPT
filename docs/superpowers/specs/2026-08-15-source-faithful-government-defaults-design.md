# 源材料忠实与政府公文式默认策略设计

## 目标

CyberPPT 从 Word、PDF、Markdown 等源材料生成 PPT 时，默认采用政府公文式、央企正式交流语体，并以源材料的标题、顺序、内容和事实强度为权威边界。只有用户明确要求重构叙事、咨询化表达、路演化表达或压缩重组时，才允许解除默认结构锁定。

## 默认行为

1. 默认文体为政府公文式、央企正式交流语体，使用正式、稳健、克制的表达。
2. 默认保留源材料章节标题、内容标题和先后顺序。
3. 默认完整保留源材料事实、条件、状态、责任、数字和表述强度，不主动裁减重要内容。
4. 允许仅因 PPT 单页容量进行拆页。
5. 允许合并源材料中的重复内容，但不得改变重复内容所属主题、事实强度和责任边界。
6. 不允许自造章节逻辑、问题路径、交流路径、咨询式金句或营销标题。
7. 目录页只列源材料章节；其标题使用源材料目录标题，源材料未提供时使用“目录”。
8. 只有用户明确授权时，才允许重新命名标题、重排章节、改变叙事路径或大幅压缩内容。

## 允许的页面级整理

### 容量拆页

一个源标题内容超过单页合理容量时，可以拆成连续多页。拆分页必须：

- 共同引用同一个源标题；
- 保持源材料内部顺序；
- 使用“源标题（一）”“源标题（二）”或源材料已有同级子项作为标题；
- 不得以新造结论句替代源标题。

### 重复合并

源材料在不同位置重复陈述同一事项时，可以合并到首次完整承担该事项的页面。合并必须：

- 保留全部实质信息；
- 记录所有来源引用；
- 不得将不同条件、阶段或责任主体误判为重复；
- 不得因合并改变原章节顺序和业务归属。

## 工作包契约

`outline-workpack.json.planning_policy` 默认写入：

- `writing_style_mode = government_official`
- `source_structure_mode = locked`
- `source_title_mode = locked`
- `source_order_mode = locked`
- `source_content_mode = preserve`
- `capacity_split_allowed = true`
- `duplicate_content_merge_allowed = true`
- `reframing_requires_explicit_user_request = true`
- `agenda_mode = source_sections_only`

旧的 `source_headings_are_not_mandatory_slide_structure=true` 和 `may_reorder_and_deduplicate_supported_material=true` 不再作为默认策略。

结构化请求可以显式设置 `source_structure_mode = flexible` 或 `writing_style_mode = consulting`。原始文本请求只有明确包含重构叙事、咨询化、路演化或压缩重组授权时，作者才可解除默认锁定；不得仅凭“面向领导汇报”“合作交流”等一般用途推断已授权重构。

## 提纲作者契约

`ppt-outline-planning` 默认先消费源材料原生标题和顺序，再确定单页容量。Deck Thesis、页面使命和论证链用于说明原文内容，不得覆盖源材料标题体系。

标题规则：

- 封面使用源材料正式题名；
- 目录使用源材料目录名称或“目录”；
- 章节页使用源材料章标题；
- 内容页使用源材料同级标题；
- 拆分页使用源标题加序号或源材料已有子项；
- 不得使用“若干问题构成交流路径”“从某某走向某某”等模板化咨询标题。

## 下游契约

`cyberppt-handoff` 继续确定性复制 `title_intent`、页面顺序和章节映射，不重新规划。`cyberppt-write-single-page` 默认不得改写已验证 Outline 的页面标题；页面命题、主判断和业务小标题可以在源材料边界内组织，但不能反向覆盖页面标题。

## 验证与旧工作包处理

1. `ppt-outline-planning` 验证器读取同目录 `outline-workpack.json`。
2. 工作包存在时，验证器检查其语义层哈希仍与当前语义输入一致。
3. 工作包默认处于源结构锁定模式时，`deck-brief.json` 必须声明相同的写作与结构策略。
4. 默认目录页不得使用判断句、问题句、交流路径或营销式标题。
5. 页面计划必须连续，并保持 Deck Brief 中章节与页面映射一致。
6. 工作包请求与提纲策略冲突时验证失败，不得仅给警告。
7. 兼容旧项目：没有 `outline-workpack.json` 的旧提纲仍按现有结构校验；存在旧工作包但请求与新产物不一致时要求重新准备工作包。

## 修改范围

- `.agents/skills/ppt-outline-planning/SKILL.md`
- `.agents/skills/ppt-outline-planning/ppt_outline_planning/prepare.py`
- `.agents/skills/ppt-outline-planning/ppt_outline_planning/validate.py`
- `.agents/skills/ppt-outline-planning/references/outline-contract.md`
- `.agents/skills/cyberppt-write-single-page/SKILL.md`
- `.agents/skills/cyberppt-write-single-page/references/professional-page-authoring.md`
- `projects/AGENTS.md`
- `tests/test_skill_contract.py`
- 新增提纲工作包与验证器测试

`cyberppt-handoff` 当前已按已验证提纲原样复制标题和顺序，不改变其生产逻辑，仅补充必要测试以确认该边界。

## 验收标准

1. 默认工作包明确输出政府公文式和源结构锁定策略。
2. Skill 不再要求默认重排源标题和章节。
3. 默认提纲标题、章节和目录忠实于源材料；容量拆页和重复合并仍可执行。
4. 目录页不能被命名为“四个合作问题构成交流路径”或同类判断句。
5. 旧工作包与当前语义或请求不一致时，验证器阻断。
6. 显式咨询化或结构重构请求仍可使用灵活模式。
7. 相关单元测试和 V16 真实流程验证通过。
