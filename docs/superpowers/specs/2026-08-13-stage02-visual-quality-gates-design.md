# Stage 02 视觉结构质量门设计（第一期）

## 目标

在当前受治理的 Stage 02 链路中，补齐候选质量、关系覆盖、页间节奏、文本容量、生图可执行性与真实 QA 的确定性检查，使“脚本语义正确”能稳定转化为“可生成、可审阅、整套不重复”的视觉结构。

## 范围

本期只处理新生成的受治理决策包与视觉规格，依赖“上屏表达结构自适应档案”合同已可用。

包含：

- 候选反事实淘汰理由；
- 关键业务关系的视觉承载覆盖；
- 候选和整套的可生成性评分；
- 文本容量预算；
- 语义焦点竞争检查；
- 相邻内容页的节奏审计；
- 编译期 QA 改为待审计，审计写入真实 QA。

不包含：

- 历史 `visual-design-decisions.v1`、旧 validation report 或任何历史项目产物的迁移、修复或重跑；
- 颜色、字体、形状、坐标、媒介和具体视觉风格；
- 直接生成图片、PPTX 或调整 ImageGen 模型参数；
- 修改 Stage 01 的页面文案、事实、关系或锁定文字。

## 设计原则

1. 业务关系覆盖是内容忠实度门，不因“画面好看”而降级。
2. 生图可执行性影响候选排序和人工复核，但不可以覆盖内容忠实度失败。
3. 页间差异检查只针对连续内容页；同一视觉意图可复用，但必须有叙事理由。
4. 所有分数必须有维度和证据，不能由编译器预设通过。
5. 视觉设计继续允许结构自由；本期只检查关系、阅读、容量和重复风险，不引入模板路由。

## 数据合同

### 候选质量说明

每个候选新增：

```json
{
  "selection_rationale": {
    "mission_fit": "该候选将两类驱动因素汇聚到建设响应，直接回答本页必要性判断。",
    "generation_feasibility": {
      "score": 82,
      "dimensions": {
        "single_focus": 20,
        "text_capacity": 17,
        "relation_clarity": 20,
        "composition_stability": 18,
        "anti_pattern_risk": 7
      },
      "risks": ["两组驱动因素需控制标签长度"]
    }
  }
}
```

除选中候选外，每个候选必须有 `rejection_rationale`。该字段说明相对选中候选的具体不足，不得使用“得分较低”“不够美观”等空泛理由。

### 关系覆盖

每页决策包新增 `relationship_coverage`，逐项消费 `stage01_relationship_features.actions` 和 `business_relationships` 中的关键关系：

```json
{
  "relation_key": "R02",
  "source": "business_relationships",
  "subject": "资源方",
  "relation": "authorizes",
  "object": "运营平台",
  "visual_status": "primary",
  "evidence_refs": ["E2"],
  "text_ids": ["P08-T03"],
  "rationale": "授权关系是本页权责边界的主判断。"
}
```

`visual_status` 只能是 `primary`、`secondary`、`not_rendered`。`not_rendered` 必须有原因，并且不得用于页面使命、核心判断或 P0 证据所必需的关系。

### 文本容量预算

每个候选新增 `text_capacity_budget`：锁定文字总数、各证据单元文字数、可容纳的最大行数、单行最大字符数、估计密度和风险项。预算只使用锁定文字 ID 与文本长度，不更改文字内容。

### Spec 的质量合同

`deck-visual-spec.json` 每页新增 `quality_contract`，投影已选候选的可生成性评分、文本容量预算摘要、关系覆盖摘要、焦点竞争检查结果和选择理由。编译器写入：

```json
{
  "status": "pending_audit",
  "generation_feasibility": {"score": 82, "risks": ["..."]},
  "relationship_coverage": {"total": 4, "primary": 1, "secondary": 3, "not_rendered": 0},
  "text_capacity": {"risk_level": "medium", "locked_text_count": 7},
  "focus_competition": {"status": "passed", "primary_ref": "E2"}
}
```

编译器不写 `qa.status=passed` 或评分。`visual-structure-audit` 汇总真实校验结果后，才将 QA 写为 `passed` 或 `failed`。

## 规则

### 候选与淘汰理由

- 每个候选必须有页面使命适配说明和 5 维可生成性评分，维度总和为 100。
- 选中候选必须拥有最高有效可生成性总分；内容忠实度、表达结构、锁定文字和关系覆盖任何一项失败时，即使总分最高也不得选中。
- 未选候选必须逐一列出与选中候选相比的具体劣势，例如“使闭环反馈边弱化为线性顺序”或“锁定文字超过关联节点的容量预算”。

### 关系覆盖

- 所有关键业务关系必须被逐项登记。
- 与核心判断、页面使命、P0 证据直接相关的关系必须为 `primary` 或 `secondary`，不得为 `not_rendered`。
- 关系的 `evidence_refs` 必须是当前候选证据单元，`text_ids` 必须为当前锁定文字 ID。

### 文本容量与焦点竞争

- 预算超过目标容量时为候选风险；超过阻断容量时不可选。
- 选中焦点必须承载至少一个 P0 证据，并拥有最多的主级文字绑定；若另一个非焦点节点拥有相同或更多主级绑定，则判定为焦点竞争失败。

### 页间节奏

- 检查相邻 3 个内容页的选中视觉意图、空间语法、主阅读方向、焦点类型和文本承载模式。
- 连续 3 页的上述结构签名完全相同为阻断。
- 连续 2 页高度相似为警告；若 decision receipt 提供 `rhythm_exception_reason`，则保留警告但不阻断。
- 节奏审计不要求所有页面不同，也不要求模板页进入视觉设计。

## 审计与输出

`audit_visual_design_package` 负责跨输入、候选和 spec 的页级一致性。新增 deck 级 `audit_visual_deck_rhythm`，由 `run_visual_structure_audit` 调用并写入 validation report。

审计通过后：

1. 基于当前 spec 重建 `generation-prompts.md`；
2. 将实际校验结果写入 `deck-visual-spec.json` 的 `qa_summary` 和页级 `qa`；
3. 写入 `visual/visual-review-summary.md`，只供人工审阅，包含每页选中候选、淘汰理由、可生成性风险、文本容量与关系覆盖，以及整套节奏警告。

审计失败时不得重建提示词，也不得将 pending QA 改为 passed。

## 测试与验收

1. 候选缺少淘汰理由、评分维度不完整、评分总和不为 100 或选中候选不满足硬门时失败。
2. 关键业务关系漏登记、错误 evidence/text ID、关键关系标为 `not_rendered` 时失败。
3. 文本容量超出阻断阈值、主焦点无 P0 绑定或存在竞争焦点时失败。
4. 连续三页结构签名相同失败；两页相似产生警告；有节奏例外理由保留警告且不失败。
5. 编译后 spec 初始为 `pending_audit`；通过审计才变为 passed；失败审计保持/写为 failed。
6. 运行：

```bash
PYTHONPATH=. pytest -q \
  tests/test_visual_structure_contract.py \
  tests/test_visual_structure_stage.py \
  tests/test_onscreen_expression.py \
  tests/test_visual_structure_skill_fixtures.py
PYTHONPATH=. pytest -q
```

## 依赖与实施顺序

本期依赖“上屏表达结构自适应档案”先完成并稳定其候选合同。之后按：页级候选质量与关系覆盖 → 编译投影与真实 QA → deck 级节奏审计与人工审阅摘要 → 回归验证 的顺序实施。

