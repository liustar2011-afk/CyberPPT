# 阶段3：上屏文字与内容锁定

## 输入

- `stages/01_information_assets.json`
- `stages/02_page_plan.json`，且状态为`current`
- `config/project.yaml`
- Schema：`references/schemas/screen_copy.schema.json`

## 目标

把页面规划转为可直接上屏的终稿文字，并锁定语义边界。不得改变页数、顺序、页面使命、核心判断和资产归属。

## 写作规则

1. 每个`page_id`与页面规划一一对应，不新增、删除、合并或拆分页面。
2. 本页文字只能使用本页`source_asset_ids`，不得从其他页借用信息。
3. `title`应表达核心判断或页面职能，短句化；不把章节名当标题。
4. `subtitle`可以为空，不为版式对称强行生成。
5. `modules`按真实逻辑关系组织，不默认三栏等宽，不按“一条资产一个模块”机械映射。
6. `body_lines`是可直接上屏的终稿短句，不写解释模型如何思考的过程性文字。
7. `conclusion`是全页落点，不重复正文，不喊口号。
8. 数字、单位、日期、责任主体、专业术语、限定条件和安全边界保持原意。
9. 不生成源材料没有的“核心能力、几大机制、价值体系、保障体系”。
10. 严格遵守`config/project.yaml`中的字数、模块数和禁用句式。

## 内容锁定

每页必须填写：

- `title_meaning`：标题不得偏离的语义。
- `core_judgment`：页面已锁定判断。
- `required_facts`：删掉后会改变结论的事实。
- `required_terms`：必须保持统一的专业名称。
- `prohibited_rewrites`：会导致口径变化的改写。
- `prohibited_additions`：最容易被模型擅自补充的内容。

## 出口条件

- 文字集合与页面规划完全一致。
- 所有模块资产均属于本页。
- 无禁用句式、无标题重复、无明显文字过载。
- 每页可以在不看源文的情况下准确说清一个判断，但不能超出源文。
