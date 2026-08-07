from pathlib import Path
import tempfile
import unittest
import sys

from docx import Document

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from extract_docx import extract  # noqa: E402


class ExtractDocxTests(unittest.TestCase):
    def test_extracts_headings_paragraphs_and_tables(self):
        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / "source.docx"
            doc = Document()
            doc.add_heading("第一章 测试", level=1)
            doc.add_paragraph("这是正文。")
            table = doc.add_table(rows=2, cols=2)
            table.cell(0, 0).text = "字段"
            table.cell(0, 1).text = "内容"
            table.cell(1, 0).text = "A"
            table.cell(1, 1).text = "B"
            doc.save(p)
            out = extract(p)
            self.assertIn("SRC-P0001", out)
            self.assertIn("SRC-P0002", out)
            self.assertIn("SRC-T0001", out)
            self.assertIn("第一章 测试", out)


if __name__ == "__main__":
    unittest.main()
