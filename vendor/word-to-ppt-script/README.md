# Word 稿编译 PPT 脚本 Skill v2.2.0

`word-to-ppt-script` 将正式 Word 报告、合作方案、研究报告、工作汇报和政企材料编译为完整的 PPT 生产脚本。

## 核心定位

正式主产物是 `10-script-final.md`。它同时服务于：

- 人工审阅；
- 页面边界和证据追溯；
- 下游页面类型识别；
- 内容页生图；
- 模板页SVG/PPT生成；
- PPT自动组装；
- 后续修改和质量审计。

下游组装关系：

```text
完整脚本
├─模板页：cover / contents / chapter / closing
│  └─代码生成SVG并写入可编辑PPT
└─内容页：content
   └─编译单页ImageGen契约→生成正文区图片→写入PPT

页面标题、副标题、页码、Logo和模板公共元素由PPT代码/模板层处理。
```

## 编译链路

```text
.docx
→ 源文规范化
→ 事实与边界地图
→ 论证重构
→ PPT提纲
→ 页面边界矩阵
→ 过渡文字稿
→ 终稿上屏文字
→ 演讲者备注
→ 视觉结构规格
→ SCRIPT-FINAL完整脚本
→ 质量报告
→ 可选ImageGen送图审阅稿
```

## v2.2.0 重点能力

1. **完整脚本真实格式**：主判断、完整文字稿、文字取舍说明、证据映射、锁定上屏文字、逻辑骨架、视觉合同、页级合同注释和演讲者备注。
2. **页面类型接口**：模板页与内容页可被下游代码稳定识别。
3. **内容—结构—风格分离**：单页契约固定锁定文字、页面任务和清洗后的视觉结构；通用视觉风格由总仓库 `visual/ACTIVE-STYLE.md` 在送图前统一注入。
4. **字段隔离**：证据编号、演讲备注和逻辑骨架不进入 ImageGen；视觉结构只以清洗后的页级合同进入，不发送内部标签。
5. **黄金样例回归**：仓库内置实际33页送图审阅稿，用于检查输出格式。
6. **逻辑质量校验**：页面越界、跨页重复、错误并列、服务/费用混排、交付维度混排和禁用句式。

## 主要目录

```text
word-to-ppt-script/
├── SKILL.md
├── config/
│   ├── cec-formal.yaml
│   ├── imagegen-page-contract.yaml
│   ├── quality-rules.yaml
│   └── visual-intent-registry.yaml
├── references/
│   ├── 12-output-contract.md
│   ├── 15-imagegen-handoff.md
│   └── 16-single-page-imagegen-contract.md
├── templates/
│   ├── 10-script-final.md
│   └── imagegen/
├── scripts/
│   ├── build_generation_prompt.py
│   ├── validate_script.py
│   └── validate_imagegen_contract.py
├── examples/
│   ├── sample-project/
│   └── golden/
└── tests/
```

## 使用方式

### 1. 校验完整脚本

```bash
python scripts/validate_script.py 10-script-final.md --strict
```

### 2. 编译ImageGen送图审阅稿

```bash
python scripts/build_generation_prompt.py 10-script-final.md \
  -o 12-imagegen-review.md \
  --project project-slug \
  --source-script /project/workbench/scripts/final/script-final.md
```

只编译单页或页段：

```bash
python scripts/build_generation_prompt.py 10-script-final.md \
  -o p04-imagegen.md --page 4
```

### 3. 校验送图契约

```bash
python scripts/validate_imagegen_contract.py 12-imagegen-review.md --strict
```

### 4. 校验完整项目

```bash
python scripts/validate_project.py . --strict
```

## 黄金样例

`examples/golden/06953cb7-5f43-4d00-8b23-72af9dd467bc.md` 是实际下游 ImageGen 送图脚本审阅稿。它仅作为派生格式样例，不替代正式完整脚本。


## 统一视觉风格文件

总仓库中的 `visual/ACTIVE-STYLE.md` 是唯一运行时视觉风格源。`09-visual-design-spec.md` 和 `SCRIPT-FINAL` 只描述每页业务关系、主视觉载体、空间组织、阅读路径和文字融合方式，不重复保存色板、材质和通用审美长提示。修改活动风格文件后重新编译即可。
