from __future__ import annotations

from tests._imagegen_deliverable_prompt_base import *
from tests import _imagegen_deliverable_prompt_base as _base


class DualImageOverlayDeliverablePromptTests(_base.DualImageOverlayDeliverablePromptTests):
    def test_style_nine_safety_rules_are_injected_into_imagegen_prompt(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory)
            script = root / "script.md"
            style = write_project_style_lock(project=root / "project", style_id=9)
            script.write_text("## 第1页：测试\n组件A：业务内容\n", encoding="utf-8")

            prompt = compile_pages(script, [1], style_lock_path=style)

        self.assertIn("GPT Image 2.5 Artifact Spec 执行版", prompt)
        self.assertIn("不生成伪文字、虚构刻度、虚构 UI、无依据数据或随机标签", prompt)
        self.assertIn("不使用无关 Logo、水印、品牌标识和随机场景文字", prompt)
        self.assertIn("不让正面人物宣传照成为默认主视觉", prompt)
        self.assertIn("只使用来源明确支持的关系，不凭视觉需要补造层级、闭环、双向交互、比例或优先级", prompt)
        self.assertIn("不用面积、距离、颜色、箭头或层级暗示来源未支持的优先级、比例和关系", prompt)
        self.assertIn("最终结果应呈现：纯白、深蓝、编辑式、高端、精确、克制、内容驱动的领导汇报正文图。", prompt)
