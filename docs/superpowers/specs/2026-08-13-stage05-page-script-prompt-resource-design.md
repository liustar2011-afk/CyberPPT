# 阶段 5 逐页脚本写作规范资源化设计

## 目标

将 `cyberppt/commands/prepare_stage01_input.py` 中
`prepare_page_script_input()` 的静态写作规范迁移为独立 Markdown 资源，使规范可被单独 diff、review 和维护，同时保持该命令的输出逐字不变。

## 非目标

- 不改变阶段 5 的任何写作规范、顺序或措辞。
- 不改变 CLI 参数、项目目录结构、Stage 01/Stage 02 流程或生成产物。
- 不把按页的 Outline、证据、边界和内容单元等动态上下文移出 Python。
- 不引入新的控制文件、状态文件或审批机制。

## 方案

新增 `vendor/skills/ppt-script/system-prompt/stage1/61-page-script-authoring.md`。
该文件承载当前函数中从 `# Page script authoring input` 到逐页循环前的全部静态文本，保留原有顺序、空行和文字。

在 `prepare_stage01_input.py` 中定义资源路径及一个 UTF-8 文本加载边界。`prepare_page_script_input()` 先读取资源，以其内容初始化输出行，再沿用当前逻辑追加每个内容页的动态字段、内容单元、证据文本、边界约束和必要 Markdown 段落说明。

资源不存在或不可读取时，加载边界应抛出包含资源绝对或可定位路径的 `FileNotFoundError`，避免静默生成缺少写作契约的输入。

## 数据流

```text
静态 Markdown 写作规范 ──读取──┐
                                ├── prepare_page_script_input ──> CLI 标准输出
Outline / Source Truth 动态页面数据 ─┘
```

静态规范仅由资源文件提供；每次调用的项目事实仍从当前项目的 `outline.json` 和 Source Truth 记录读取。两者按当前既定顺序拼接。

## 兼容性与测试

1. 为固定的测试项目生成阶段 5 输入，并断言迁移后的全文与迁移前基线逐字一致。
2. 保留并运行现有测试，继续验证核心判断、写作规则和未知内容页的错误处理。
3. 新增资源消费测试：替换或读取资源中的唯一标记，证明函数实际通过资源加载静态规范，而不是保留另一份硬编码副本。
4. 运行定向测试 `tests/test_prepare_stage01_input.py`；若该文件所属测试集合可无额外成本运行，也一并执行。

## 验收标准

- 静态规范不再以内嵌 Python 字符串列表存放。
- Markdown 资源可独立审阅和修改。
- 对同一测试项目，迁移前后函数输出逐字一致。
- 资源缺失有明确、可诊断的失败信息。
