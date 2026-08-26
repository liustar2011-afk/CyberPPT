from pathlib import Path
import tempfile
import unittest
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from validate_script import validate  # noqa: E402


class ValidatorTests(unittest.TestCase):
    def test_example_passes_strict(self):
        pages, issues = validate(ROOT / "examples" / "sample-project" / "10-script-final.md", strict=True)
        self.assertEqual(len(pages), 3)
        self.assertFalse([i for i in issues if i.level == "error"], issues)

    def _run_text(self, text: str):
        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / "script.md"
            p.write_text(text, encoding="utf-8")
            return validate(p, strict=True)[1]

    def test_banned_contrast_and_missing_visual(self):
        text = """## 第1页：测试
- 页面类型：内容页
- 页面标题：测试
- 本页只回答：测试什么。
- 本页不得包含：其他内容。
- 主判断：这不是A而是B。
### Source IDs
- SRC-P0001
### 上屏文字（严格锁定）
### 一、两个方面｜测试
- **事项一**
  - 这是内容一，具有完整的对象、动作、结果和必要边界，用于形成足够的信息密度。
- **事项二**
  - 这是内容二，具有完整的对象、动作、结果和必要边界，用于形成足够的信息密度。
### 逻辑骨架
```text
A→B
```
### 演讲者备注
这里提供足够长度的演讲说明，解释页面逻辑、事实依据、边界条件和下一页过渡，避免逐字重复上屏内容，并保持正式口吻。
"""
        issues = self._run_text(text)
        codes = {i.code for i in issues if i.level == "error"}
        self.assertIn("BANNED_CONTRAST", codes)
        self.assertIn("MISSING_VISUAL", codes)

    def test_service_fee_mix_and_count_mismatch(self):
        text = """## 第1页：测试
- 页面类型：内容页
- 页面标题：测试
- 本页只回答：测试分类。
- 本页不得包含：其他内容。
- 主判断：分类需要保持同一维度。
### Source IDs
- SRC-P0001
### 上屏文字（严格锁定）
### 一、三类内容｜分类
- **数据服务**
  - 提供数据。
- **平台服务费**
  - 对应费用。
### 逻辑骨架
```text
分类
```
### 视觉结构（不上屏）
主结构。
### 视觉意图与生图构图
- visual_intent_type：taxonomy_to_service
- visual_thesis：同一维度分类。
- decision_relationship：分类。
- dominant_visual_carrier：服务谱系。
- spatial_organization：纵向谱系。
- reading_path：自上而下。
- relationship_encoding：分支。
- text_integration_method：标签贴附。
- industry_scene_anchor：无。
- visual_hierarchy：主次明确。
- avoid_on_this_page：卡片墙。
- 生图要求：标题由PPT文字层处理，不绘制标题区。
### 演讲者备注
这里提供足够长度的备注说明分类规则、来源依据、边界条件和后续衔接，避免重复可见文字并保持正式表达。
"""
        issues = self._run_text(text)
        codes = {i.code for i in issues if i.level == "error"}
        self.assertIn("SERVICE_FEE_MIX", codes)
        self.assertIn("COUNT_MISMATCH", codes)

    def test_missing_order_signal_and_logic_skeleton_not_onscreen(self):
        # Reproduces the real-world defect found in
        # power-data-infrastructure-cooperation-v12-20260807/script-final.md
        # p04: four flat, unnumbered module headings whose logic skeleton
        # claims a causal chain that never surfaces on screen.
        text = """## 说明
视觉设计范围：不含视觉设计

## 第1页：测试页
- 页面类型：内容页
- 页面标题：测试页
- 主判断：业务演进和协同需求造成现实制约，进而催生基础需求。
### Source IDs
- SRC-P0001
### 上屏文字（严格锁定）
#### 业务演进
- **系统运行更加复杂**
  - 电源结构和负荷特征加快变化。
  - 交易决策和燃料采购需求增加。
#### 协同需求
- **跨企业协同**
  - 跨企业数据需共同参与。
  - 跨领域数据需协同支撑。
#### 现实制约
- **资源连接困难**
  - 数据分散，对接成本较高。
  - 资源缺统一说明，难快速组合。
#### 基础需求
- **统一连接基础**
  - 建立可信接入，降低对接成本。
  - 建立授权控制，保障合规使用。
### 逻辑骨架
```text
业务演进＋协同需求
↓
现实制约
↓
需要建设统一的行业级基础
```
### 演讲者备注
这里提供足够长度的演讲说明，解释页面逻辑、事实依据、边界条件和下一页过渡，避免逐字重复上屏内容，并保持正式口吻表达。
<!-- cyberppt-page-contract {"schema":"cyberppt.page_contract_receipt.v2","page_id":"p01","page_mission":"测试","core_message":"业务演进和协同需求造成现实制约，进而催生基础需求。","must_not_include":["其他页面内容"]} -->
"""
        issues = self._run_text(text)
        codes = {i.code for i in issues if i.level == "error"}
        self.assertIn("MISSING_ORDER_SIGNAL", codes)
        self.assertIn("LOGIC_SKELETON_NOT_ONSCREEN", codes)

    def test_order_signal_present_clears_both_checks(self):
        # Same content and same causal logic skeleton as above, but module
        # headings are numbered — this is the fix the rule asks for, and it
        # must actually satisfy the checker rather than just look different.
        text = """## 说明
视觉设计范围：不含视觉设计

## 第1页：测试页
- 页面类型：内容页
- 页面标题：测试页
- 主判断：业务演进和协同需求造成现实制约，进而催生基础需求。
### Source IDs
- SRC-P0001
### 上屏文字（严格锁定）
#### ①业务演进
- **系统运行更加复杂**
  - 电源结构和负荷特征加快变化。
  - 交易决策和燃料采购需求增加。
#### ②协同需求
- **跨企业协同**
  - 跨企业数据需共同参与。
  - 跨领域数据需协同支撑。
#### ③现实制约
- **资源连接困难**
  - 数据分散，对接成本较高。
  - 资源缺统一说明，难快速组合。
#### ④基础需求
- **统一连接基础**
  - 建立可信接入，降低对接成本。
  - 建立授权控制，保障合规使用。
### 逻辑骨架
```text
业务演进＋协同需求
↓
现实制约
↓
需要建设统一的行业级基础
```
### 演讲者备注
这里提供足够长度的演讲说明，解释页面逻辑、事实依据、边界条件和下一页过渡，避免逐字重复上屏内容，并保持正式口吻表达。
<!-- cyberppt-page-contract {"schema":"cyberppt.page_contract_receipt.v2","page_id":"p01","page_mission":"测试","core_message":"业务演进和协同需求造成现实制约，进而催生基础需求。","must_not_include":["其他页面内容"]} -->
"""
        issues = self._run_text(text)
        codes = {i.code for i in issues if i.level == "error"}
        self.assertNotIn("MISSING_ORDER_SIGNAL", codes)
        self.assertNotIn("LOGIC_SKELETON_NOT_ONSCREEN", codes)

    def test_template_business_text(self):
        text = """## 第1页：封面
- 页面类型：封面
- 页面标题：封面
### 上屏文字（严格锁定）
本页详细说明业务机制、客户报价、收益结算和技术路径，属于明显的业务正文内容。
### 视觉意图与生图构图
- visual_intent_type：template
"""
        issues = self._run_text(text)
        self.assertIn("TEMPLATE_BUSINESS_TEXT", {i.code for i in issues if i.level == "error"})


if __name__ == "__main__":
    unittest.main()
