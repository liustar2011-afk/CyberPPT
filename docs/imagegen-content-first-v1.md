# ImageGen 正式提示词链路

CyberPPT 从完整页面脚本生成单图提示词时，默认使用 `content-first-v1`。

正式脚本生成入口是 `python -m scripts.dual_image_overlay.imagegen_handoff`。
入口通过 `compile_page_prompt` 输入页面任务、核心判断、精简页面逻辑、
锁定关键文字和完整页面语义，并把结果写入 `workbench/prompts/imagegen/` 等待审阅。

`content-first-v1` 使用双层文字合同：

- `锁定上屏文字`：正文结论和含数字的关键事实逐字准确。
- `完整页面内容｜用于视觉叙事`：核心判断、业务对象、逻辑关系和关键限定必须完整覆盖，但允许调整语序、合并重复、拆分为场景标签或适度压缩。

不得新增未经页面内容支持的上屏文字；可以增加不带文字的行业场景、业务动作、环境细节和视觉隐喻，让画面参与解释，而不是形成“文字排版 + 装饰图片”。

`legacy` 和 `creative-brief-v1` 仅作为显式兼容/回滚编译器：

```text
--prompt-compiler legacy
--prompt-compiler creative-brief-v1
```

## 核心判断上屏模式

页面模型支持 `onscreen_judgment_mode`：

- `locked`：默认值，核心判断进入锁定上屏文字。
- `semantic_only`：核心判断仍进入页面任务、完整语义和构图约束，但不强制逐字上屏。适用于定位、边界、分工、协同等更适合由画面关系证明的判断。

该模式由上游页面合同显式选择，编译器不根据项目、页码或具体句子做特判。含数字的关键事实仍独立锁定。

本流程只负责编译和暂存提示词脚本，不执行 ImageGen，也不修改生图调用参数。
