from __future__ import annotations

import json
import tempfile
import unittest
import zipfile
from pathlib import Path

from cyberppt.source_document_map import (
    SOURCE_HEADING_TREE,
    SOURCE_MAP_AUDIT,
    SOURCE_REGISTRY,
    SOURCE_UNITS,
    load_source_units,
    prepare_source_map,
    render_units_for_model,
)


DOCUMENT_XML = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"
 xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"
 xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main"
 xmlns:wp="http://schemas.openxmlformats.org/drawingml/2006/wordprocessingDrawing">
 <w:body>
  <w:p><w:pPr><w:pStyle w:val="Heading1"/></w:pPr><w:r><w:t>第一章 总体主张</w:t></w:r></w:p>
  <w:p><w:r><w:t>这是用于论证主张的正文。</w:t></w:r></w:p>
  <w:tbl><w:tr><w:tc><w:p><w:r><w:t>能力</w:t></w:r></w:p></w:tc><w:tc><w:p><w:r><w:t>说明</w:t></w:r></w:p></w:tc></w:tr></w:tbl>
  <w:p><w:r><w:drawing><wp:inline><wp:docPr id="1" name="Picture 1"/><a:graphic><a:graphicData><a:blip r:embed="rId1"/></a:graphicData></a:graphic></wp:inline></w:drawing></w:r></w:p>
 </w:body>
</w:document>
"""

STYLES_XML = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<w:styles xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">
 <w:style w:type="paragraph" w:styleId="Heading1"><w:name w:val="标题 1"/><w:pPr><w:outlineLvl w:val="0"/></w:pPr></w:style>
</w:styles>
"""

RELS_XML = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
 <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/image" Target="media/image1.png"/>
</Relationships>
"""


def _write_minimal_docx(path: Path) -> None:
    with zipfile.ZipFile(path, "w") as package:
        package.writestr("word/document.xml", DOCUMENT_XML)
        package.writestr("word/styles.xml", STYLES_XML)
        package.writestr("word/_rels/document.xml.rels", RELS_XML)
        package.writestr("word/media/image1.png", b"\x89PNG\r\n\x1a\nsource-map-test")


class SourceDocumentMapTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.project = Path(self.temp.name) / "project"
        (self.project / "source").mkdir(parents=True)

    def tearDown(self) -> None:
        self.temp.cleanup()

    def test_markdown_preserves_heading_tree_and_stable_unit_ids(self) -> None:
        (self.project / "source" / "material.md").write_text(
            "# 总论点\n正文证据。\n## 能力主张\n能力论据。\n",
            encoding="utf-8",
        )

        first = prepare_source_map(self.project)
        first_units = (self.project / SOURCE_UNITS).read_bytes()
        second = prepare_source_map(self.project)

        self.assertEqual("passed", first["status"])
        self.assertEqual(first["source_map_bundle_sha256"], second["source_map_bundle_sha256"])
        self.assertEqual(first_units, (self.project / SOURCE_UNITS).read_bytes())
        self.assertTrue((self.project / SOURCE_REGISTRY).is_file())
        self.assertTrue((self.project / SOURCE_HEADING_TREE).is_file())
        self.assertTrue((self.project / SOURCE_MAP_AUDIT).is_file())
        units = load_source_units(self.project)
        self.assertTrue(all(str(item["unit_id"]).startswith("SU-") for item in units))
        self.assertEqual(["总论点", "能力主张"], [item["title"] for item in first["headings"]])
        self.assertEqual(first["headings"][0]["heading_id"], first["headings"][1]["parent_heading_id"])

    def test_docx_registers_heading_table_and_uninterpreted_image(self) -> None:
        _write_minimal_docx(self.project / "source" / "material.docx")

        report = prepare_source_map(self.project)
        units = load_source_units(self.project)
        kinds = {str(item["kind"]) for item in units}
        warning_codes = {str(item["code"]) for item in report["warnings"]}

        self.assertEqual("passed", report["status"])
        self.assertTrue({"heading", "paragraph", "table_row", "image"}.issubset(kinds))
        self.assertEqual("第一章 总体主张", report["headings"][0]["title"])
        self.assertIn("SOURCE_IMAGE_SEMANTICS_PENDING", warning_codes)
        image = next(item for item in units if item["kind"] == "image")
        self.assertTrue(image["metadata"]["requires_visual_interpretation"])
        self.assertEqual("word/media/image1.png", image["metadata"]["media_path"])

    def test_model_render_uses_source_unit_ids_instead_of_legacy_paragraph_labels(self) -> None:
        (self.project / "source" / "material.txt").write_text("第一项\n第二项\n", encoding="utf-8")

        rendered = render_units_for_model(self.project)

        self.assertEqual(1, len(rendered))
        self.assertIn("[SU-", rendered[0][1])
        self.assertNotIn("[P0001]", rendered[0][1])
        registry = json.loads((self.project / SOURCE_REGISTRY).read_text(encoding="utf-8"))
        self.assertEqual(registry["sources"][0]["source_id"], rendered[0][0]["source_id"])


if __name__ == "__main__":
    unittest.main()
