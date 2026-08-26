# Stage 01 全稿质量维度摘要设计

## 目标

增强现有 `script-audit` 的可读性与对话审阅价值，使最终全稿在进入 Stage 02 前能够明确展示五类质量维度：内容与证据、页面关系、上屏阅读自洽、讲解词职责、最终稿形式。

本功能只提供非阻断审阅提示。现有错误、警告、`failed_pages`、`retry_scope` 和 Stage 02 handoff 放行条件保持不变。

## 边界

- 不新增审批文件、状态 JSON、哈希绑定、人工停点、平行目录或独立 CLI。
- 不引入参考仓库的 `pages_content_digest`、多份持久化报告或人工批准状态机。
- 不重新判断现有 `ScriptQualityIssue` 的严重级别；摘要只归类既有审计结果和既有 `communication_review` 数据。
- 不将确定性不足的编辑判断伪装成机器结论。页面语义维度应标为“建议人工复核”，并给出对应页面和检查问题。

## 数据流

`run_script_audit()` 已经生成：

1. `issues`：带 code、severity、pages、evidence 和 suggested_action 的结构化问题；
2. `communication_review`：逐页可见核心信息、页面使命、上屏表达方式、模块关系和密度等确定性分析；
3. `failed_pages` / `retry_scope`：阻断问题的局部返工范围。

新增纯函数 `build_quality_review_summary()`，只消费这些内存数据，返回并写入现有审计报告字段：

```json
{
  "quality_review_summary": {
    "status": "review_recommended",
    "dimensions": [
      {
        "id": "content_evidence",
        "label": "内容与证据",
        "status": "passed|warning|failed|manual_review",
        "pages": ["p01"],
        "issue_codes": ["..."],
        "review_question": "..."
      }
    ],
    "conversation_review_checklist": ["..."]
  }
}
```

摘要状态不参与 `status`、`quality_status`、`failed_pages` 或 `retry_scope` 的计算。

## 五个维度

1. **内容与证据**：归类来源状态、证据映射、完整文字稿和 Source Truth 覆盖问题；没有既有问题时显示通过。
2. **页面关系**：归类跨页重复、重扩张、页面推进和第 1 环新增的关系连续性问题；没有确定性问题时提示人工确认“各页是否各自交付不同判断”。
3. **上屏阅读自洽**：归类上屏结论、模块层级、关系同构、长文本、元语言和核心信息可见性问题；没有既有问题时仍提示人工确认“脱离讲解是否读懂页面判断与模块关系”。
4. **讲解词职责**：归类讲解词缺失、过薄、页面/制作元语言及边界说教问题；没有既有问题时提示人工确认“讲解词是否只展开、不替代上屏主旨”。
5. **最终稿形式**：只针对 final script 归类草稿横幅、页序、合稿形式问题；批次草稿标记为不适用。

维度状态按既有问题严重级别计算：存在 error 为 `failed`，仅 warning 为 `warning`，无问题但需语义判断为 `manual_review`，其余为 `passed`。

## 对话审阅清单

从五个维度生成最多五条简洁问题，供最终全稿展示时直接使用：

- 每页是否承担不可替代的业务判断，并向相邻页交付清晰输入或结论？
- 上屏不听讲解是否能够读懂页面主旨、模块关系和关键依据？
- 讲解词是否仅展开业务含义、边界和转场，没有补写上屏缺失的逻辑？
- 关键主体、状态、数字、条件和来源边界是否保持原材料强度？
- 全稿是否已消除草稿/批次痕迹并形成连续页序？

当某个维度出现已有问题时，对应清单项须附带受影响页码和现有建议动作；不得生成第二套改写策略。

## 实现与测试范围

- 修改 `cyberppt/script_quality_contract.py`：增加问题代码到五个维度的静态映射及纯摘要构造函数。
- 修改 `cyberppt/commands/script_audit.py`：将摘要加入现有 report。
- 修改 `tests/test_script_quality_contract.py` 或现有 script-audit 定向测试：覆盖 error/warning/manual_review/not_applicable，以及摘要不改变放行状态和 retry scope。
- 如现有可读 Markdown 渲染器已消费 report，则只在该渲染器增加“质量维度摘要 / 最终审阅清单”；不得创建独立报告文件。

## 验收

1. 含既有来源错误与讲解词错误的夹具，摘要能分别定位到“内容与证据”“讲解词职责”。
2. 无错误但存在内容页的合格脚本，页面关系和上屏阅读自洽显示 `manual_review`，且 `status=passed` 不变。
3. 批次草稿的最终稿形式显示不适用；最终全稿正常显示该维度。
4. `failed_pages`、`retry_scope`、Stage 02 handoff 的通过/阻断结果与启用摘要前完全一致。
