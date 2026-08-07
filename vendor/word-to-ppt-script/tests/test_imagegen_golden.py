from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from validate_imagegen_contract import validate  # noqa: E402


class ImageGenGoldenTests(unittest.TestCase):
    def test_uploaded_golden_example_is_present(self):
        path = ROOT / "examples" / "golden" / "06953cb7-5f43-4d00-8b23-72af9dd467bc.md"
        self.assertTrue(path.exists())
        text = path.read_text(encoding="utf-8")
        self.assertIn("# ImageGen 送图脚本审阅稿", text)
        self.assertIn("【锁定关键文字】", text)
        self.assertIn("【完整上屏内容】", text)
        self.assertIn("- 页面类型：`cover`", text)

    def test_golden_example_contract_structure(self):
        path = ROOT / "examples" / "golden" / "06953cb7-5f43-4d00-8b23-72af9dd467bc.md"
        count, issues = validate(path, strict=False)
        errors = [x for x in issues if x.level == "error"]
        self.assertEqual(count, 33)
        self.assertEqual(errors, [], [x.__dict__ for x in errors])


if __name__ == "__main__":
    unittest.main()
