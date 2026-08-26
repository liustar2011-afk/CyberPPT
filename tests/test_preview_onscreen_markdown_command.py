from __future__ import annotations

import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from cyberppt.commands.preview_onscreen_markdown import (
    preview_onscreen_markdown,
    render_onscreen_markdown,
)

_SCRIPT = """## 第9页：示例页
- 页面类型：内容页
- 副标题：示例判断句
- 上屏文字：

  ①第一组
    标签：
      项一
      项二
    其他：短句内容

  ②第二组
    标签：短语内容
- 视觉意图类型：判断—两组构成
"""


class PreviewOnscreenMarkdownTests(unittest.TestCase):
    def test_renders_nested_bullets_from_indentation(self) -> None:
        with TemporaryDirectory() as tmp:
            script_path = Path(tmp) / "p09.md"
            script_path.write_text(_SCRIPT, encoding="utf-8")
            rendered = render_onscreen_markdown(script_path)
        self.assertIn("**副标题：** 示例判断句", rendered)
        self.assertIn("- ①第一组", rendered)
        self.assertIn("  - 标签：", rendered)
        self.assertIn("    - 项一", rendered)
        self.assertIn("    - 项二", rendered)
        self.assertIn("  - 其他：短句内容", rendered)
        self.assertIn("- ②第二组", rendered)
        self.assertIn("  - 标签：短语内容", rendered)

    def test_does_not_modify_the_source_script(self) -> None:
        with TemporaryDirectory() as tmp:
            script_path = Path(tmp) / "p09.md"
            script_path.write_text(_SCRIPT, encoding="utf-8")
            before = script_path.read_text(encoding="utf-8")
            render_onscreen_markdown(script_path)
            after = script_path.read_text(encoding="utf-8")
        self.assertEqual(before, after)

    def test_writes_to_an_output_path_when_given(self) -> None:
        with TemporaryDirectory() as tmp:
            script_path = Path(tmp) / "p09.md"
            script_path.write_text(_SCRIPT, encoding="utf-8")
            output_path = Path(tmp) / "p09-preview.md"
            result = preview_onscreen_markdown(script_path, output_path=output_path)
            self.assertEqual(result, output_path.resolve())
            self.assertTrue(output_path.exists())
            self.assertIn("①第一组", output_path.read_text(encoding="utf-8"))

    def test_missing_script_raises_file_not_found(self) -> None:
        with self.assertRaises(FileNotFoundError):
            render_onscreen_markdown(Path("/nonexistent/p09.md"))


if __name__ == "__main__":
    unittest.main()
