from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from build_generation_prompt import build  # noqa: E402
from validate_imagegen_contract import validate as validate_handoff  # noqa: E402


class HandoffTests(unittest.TestCase):
    def setUp(self):
        self.text = (ROOT / "examples" / "sample-project" / "10-script-final.md").read_text(encoding="utf-8")
        self.out = build(
            self.text,
            project="sample-project",
            source_script="/project/script-final.md",
            style_source="visual/ACTIVE-STYLE.md",
        )

    def test_upstream_only_fields_are_not_exported(self):
        content = self.out.split("## 第2页：", 1)[1]
        for token in [
            "演讲者备注", "证据映射", "SRC-P0001", "逻辑骨架",
            "visual_intent_type", "visual_thesis", "cyberppt-page-contract",
        ]:
            self.assertNotIn(token, content)

    def test_template_and_content_contracts(self):
        self.assertIn("- 页面类型：`cover`", self.out)
        self.assertIn("- 页面类型：`closing`", self.out)
        self.assertIn("不生成正文区 ImageGen", self.out)
        self.assertIn("【锁定关键文字】", self.out)
        self.assertIn("【完整上屏内容】", self.out)
        self.assertIn("页面任务：", self.out)
        self.assertIn("核心意思：", self.out)
        self.assertIn("【模板层禁绘｜不上屏】", self.out)
        self.assertIn("2048×1024", self.out)

    def test_key_text_comes_from_bold_titles(self):
        self.assertIn("小标题", self.out)
        key_block = self.out.split("【锁定关键文字】", 1)[1].split("【完整上屏内容】", 1)[0]
        self.assertIn("小标题", key_block)

    def test_generated_contract_validates(self):
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "handoff.md"
            path.write_text(self.out, encoding="utf-8")
            count, issues = validate_handoff(path, strict=True)
        errors = [x for x in issues if x.level == "error"]
        self.assertEqual(count, 3)
        self.assertEqual(errors, [], [x.__dict__ for x in errors])


if __name__ == "__main__":
    unittest.main()
