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

        self.assertIn("默认不出现人物", prompt)
        self.assertIn("禁止正脸、围桌会议、多人讨论及摆拍办公场景", prompt)
        self.assertIn("organization names, logos, seals, signage", prompt)
        self.assertIn("Auxiliary semantic imagery may use a small amount of clear Chinese labels", prompt)
        self.assertIn("Preserve the full factual meaning", prompt)
        self.assertIn("pseudo-Chinese", prompt)
        self.assertIn("Do not use arrows or arrowheads anywhere on the page", prompt)
        self.assertIn("共享谓词、共享限定语和父级说明不得复制或改写到每个并列子项", prompt)
        self.assertIn("页面任务、核心意思、页面逻辑、视觉结构、语义关系和所有不上屏区块只决定构图", prompt)
