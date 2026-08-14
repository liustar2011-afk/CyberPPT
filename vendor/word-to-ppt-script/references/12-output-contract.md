# 最终产出合同

`10-script-final.md` 是正式主产物，用于人工审阅、证据追溯、页面类型识别、内容页生图、模板页生成和PPT组装。

## 模板页

模板页包括封面、目录、章节过渡页和封底。固定包含：

- 页码和标题；
- 页面类型；
- 页面标题；
- `上屏文字（模板层）`；
- 模板层逻辑骨架；
- `visual_intent_type: template`；
- 明确不生成正文区ImageGen图。

模板页不得承载业务正文。下游代码根据页面类型生成SVG并写入可编辑PPT。

## 内容页

内容页固定顺序为：

1. 页面类型；
2. 页面标题；
3. 对应章节；
4. 主判断；
5. 完整文字稿；
6. 文字稿取舍说明；
7. 证据映射；
8. 上屏文字（严格锁定）；
   - 内容必须是可直接消费的纯文本，不含 Markdown 或后台结构语言；
   - 模块层级另写入 `上屏模块清单`、`上屏顶层模块清单` JSON 数组；
   - 每个模块标题只表达一个分组维度；异维度并列必须拆分，只有明确上位概念统摄子维度时才可使用“上位概念——子维度A与子维度B”；
9. 逻辑骨架；
10. 视觉结构（不上屏）；
11. 视觉意图与生图构图；
12. 演讲者备注。

### 页级合同 sidecar

正式 `10-script-final.md` 不得嵌入后台合同注释。每个内容页的合同写入同级或项目约定位置的 `page-contracts.json`，并绑定正式脚本 SHA-256：

```json
{
  "schema": "cyberppt.page_contracts.v1",
  "script": "10-script-final.md",
  "script_sha256": "...",
  "pages": {
    "p04": {
      "schema": "cyberppt.page_contract_receipt.v2",
      "page_id": "p04",
      "page_mission": "...",
      "core_message": "...",
      "source_refs": ["SRC-..."],
      "consumed_content_unit_ids": ["SRC-..."],
      "must_not_include": ["..."]
    }
  }
}
```

草稿可暂时携带 `cyberppt-page-contract` HTML 注释作为迁移载体；正式合稿器必须移除注释、生成 sidecar。无 sidecar 的旧项目仍可回退读取旧注释；sidecar 一旦存在，脚本哈希不匹配必须阻断。

其中：

- `page_mission`：页面任务；
- `core_message`：唯一核心判断；
- `source_refs`：来源证据；
- `visual_intent_type`：完整脚本的视觉语义；
- `consumed_content_unit_ids`：本页已消耗的内容单元；
- `must_not_include`：页面边界和禁止越界内容。

## 下游组装接口

完整脚本进入下游仓库后：

- 模板页由代码生成SVG并写入可编辑PPT；
- 内容页编译为单页ImageGen送图契约，生成正文区图片；
- 内容页标题由代码写入PPT标题层；
- 生成图片放入PPT正文区；
- 页码、Logo和模板公共元素由代码或母版统一处理。

单页送图契约详见 `references/16-single-page-imagegen-contract.md`。

## 文件规则

- 最终文件不附编制说明；
- 不在正文中输出质量审计过程；
- 用户要求替换原文件时保持原文件名、页序和字段格式；
- 机器JSON放在 `machine/`，不污染人工脚本；
- 完整脚本中的每页可独立审阅；
- 送图脚本是派生产物，不替代完整脚本。
