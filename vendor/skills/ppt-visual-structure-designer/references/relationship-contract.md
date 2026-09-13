# v4 关系判断合同

写入 `visual/visual-design-decisions.json`：

```json
{
  "schema": "cyberppt.visual_design_decisions.v4",
  "executor": "main_agent",
  "skill_sha256": "当前 SKILL.md 文件的 SHA256",
  "pages": [{
    "page_id": "p01",
    "input_sha256": "入口待办给出的页面摘要",
    "status": "supported",
    "analysis": "解释页面完整语义、关系读法及关键排除项。",
    "source_check": "说明核对的讲稿或原文范围、证据与关系方向是否一致，以及核验限制。",
    "relations": [{
      "statement": "来源支持的业务关系，使用自然语言保留实体、方向与条件。",
      "evidence": [{"field": "content_text", "quote": "该字段内实际存在的原文片段"}]
    }],
    "constraints": ["只写本页需要的误读防护。"],
    "uncertainties": []
  }]
}
```

`status` 为 `supported`、`ambiguous` 或 `none`。supported 至少有一条有依据关系；none 的 relations 为空；ambiguous 说明具体未决边界，同时允许保留已有依据关系。constraints 可以为空。无需声明拓扑类型、评分、核心结论或构图候选。

证据 field 只允许 `full_prose`、`content_text`、`onscreen_text`。新判断优先引用 `content_text`；完整背景独有条件可引用 `full_prose`。`content_contract_version: 2` 的 `onscreen_text` 证据别名统一对当前 `content_text` 校验，不能引用过期副本。quote 必须定位到实际文本。引用长度按证明关系所需选择；只出现对象名称通常不足以证明方向。来源没有可用原始资料时，以讲稿作为本次核对范围，并明确限制。

input_sha256 由 `cyberppt.visual_stage.relationship_judgment.digest(page)` 计算。`content_contract_version: 2` 使用 `production_page_input` 的版本化语义投影，绑定当前内容、不同于内容的完整背景、交流方式、标题、使命、保真项及来源语义；重复别名与旧拓扑诊断不参与这份生产身份。未声明版本的历史页继续使用完整页摘要；两种身份不能互相代替。完整 intake 的 semantic_sha256 仍校验所有持久化字段。保留其他未变页面的判断。Skill 更新、相关语义变化、证据缺失或重复页 ID 会阻止当前页消费；旧 v3 合同不会自动转换成已完成的主 Agent 判断。

`constraints` 继续使用字符串列表。主 Agent 在 analysis/source_check 中交代条件、状态、责任、数字对象或等权性约束的依据；当前机器检查不证明约束的语义正确性。不要把普通语义约束移入 fidelity_text 来制造逐字锁。

执行者声明和字段验证属于运行证据。程序不鉴定作者身份或推理真实性，主 Agent 的实际阅读、判断和语义复核承担质量责任。
