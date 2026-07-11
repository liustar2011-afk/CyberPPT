from __future__ import annotations

import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SKILL = ROOT / "SKILL.md"
README = ROOT / "README.md"
LAYOUT = ROOT / "docs" / "repository-layout.md"


class SkillContractTests(unittest.TestCase):
    def test_active_docs_expose_only_full_image_production(self) -> None:
        for text in (README.read_text(encoding="utf-8-sig"), SKILL.read_text(encoding="utf-8-sig"), LAYOUT.read_text(encoding="utf-8-sig")):
            self.assertNotIn("Legacy/Advanced", text)
            self.assertNotIn("editable rebuild", text)
            self.assertNotIn("template-rebuild", text)
            self.assertNotIn("dual_image_editable_overlay", text)

        skill = SKILL.read_text(encoding="utf-8-sig")
        self.assertIn("full_image_ppt", skill)
        self.assertIn("body_content_editable=false", skill)

    def test_active_docs_keep_production_state_machine(self) -> None:
        for text in (README.read_text(encoding="utf-8-sig"), SKILL.read_text(encoding="utf-8-sig"), LAYOUT.read_text(encoding="utf-8-sig")):
            self.assertIn("python3 -m cyberppt produce prepare", text)
            self.assertIn("python3 -m cyberppt produce assemble", text)
            self.assertIn("python3 -m cyberppt produce verify", text)


if __name__ == "__main__":
    unittest.main()
