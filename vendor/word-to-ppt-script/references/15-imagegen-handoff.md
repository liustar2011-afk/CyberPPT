# ImageGen 派生交接

## 1. 产物关系

`10-script-final.md` 是正式完整脚本。`12-imagegen-review.md` 是从完整脚本编译出的派生送图审阅稿，仅供内容页 ImageGen 使用。

```text
10-script-final.md
→ 页面类型识别
→ 模板页：代码生成SVG并组装
→ 内容页：页面内容 + 页面视觉结构 + visual/ACTIVE-STYLE.md
→ 组装单页送图契约并生成正文区图片
```

## 2. 编译命令

```bash
python scripts/build_generation_prompt.py 10-script-final.md \
  -o 12-imagegen-review.md \
  --project project-slug \
  --source-script /project/workbench/scripts/final/script-final.md
```

只编译指定页面：

```bash
python scripts/build_generation_prompt.py 10-script-final.md \
  -o p04-imagegen.md --page 4
```

支持页码和页段：`--page 4 --page 7-10 --page 12,14`。

临时覆盖活动风格：

```bash
python scripts/build_generation_prompt.py 10-script-final.md \
  -o p04-imagegen.md --page 4 \
  --style-template /absolute/path/style-10.md
```

## 3. 交接规则

内容页送入：

- 页面任务；
- 核心意思；
- 锁定关键文字；
- 完整上屏内容；
- 画布尺寸；
- 模板层禁绘规则；
- 清洗后的页面视觉结构；
- 从 `visual/ACTIVE-STYLE.md` 注入的全局视觉风格。

内容页不送入：

- Source IDs和证据映射；
- 演讲者备注；
- 文字取舍说明；
- 逻辑骨架和内部推理；
- 视觉候选方案、路由评分和原始 `visual_intent_type`；
- 页级合同JSON；
- 质量审计信息。

模板页只输出标准页面类型和不进入 ImageGen 的结论。

## 4. 唯一风格源

集成仓库运行时唯一读取：

```text
visual/ACTIVE-STYLE.md
```

页面脚本和页面视觉结构合同不得复制全局色板、材质、字体、场景质感或通用禁用项。修改活动风格并重新编译后，提示词的 `style_hash` 和 `assembly_hash` 自动变化，页面 `source_hash` 保持不变。

## 5. 验证

```bash
python scripts/validate_imagegen_contract.py 12-imagegen-review.md --strict
```

单页格式和黄金样例详见：

- `references/16-single-page-imagegen-contract.md`；
- `examples/golden/06953cb7-5f43-4d00-8b23-72af9dd467bc.md`。
