from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]


class SkillContractTests(unittest.TestCase):
    def test_identity_and_version(self):
        skill = (ROOT / "SKILL.md").read_text(encoding="utf-8")
        self.assertIn("name: word-to-ppt-script", skill)
        self.assertEqual((ROOT / "VERSION").read_text(encoding="utf-8").strip(), "2.2.0")
        for mode in ["full", "outline", "text", "visual", "compile", "revise", "audit"]:
            self.assertIn(f"`{mode}`", skill)

    def test_required_references_and_templates(self):
        refs = [
            "01-task-contract.md", "02-source-compilation.md", "03-argument-reconstruction.md",
            "04-outline-and-granularity.md", "05-page-boundary-and-ownership.md",
            "06-on-screen-text.md", "07-logic-and-parallelism.md", "08-speaker-notes.md",
            "09-visual-design.md", "10-visual-intent-router.md", "11-scene-and-image-integration.md",
            "12-output-contract.md", "13-quality-gates.md", "14-migration-from-v1.md",
            "15-imagegen-handoff.md", "16-single-page-imagegen-contract.md",
        ]
        for name in refs:
            self.assertTrue((ROOT / "references" / name).exists(), name)
        for name in ["05-page-boundary-matrix.md", "10-script-final.md", "visual-spec.schema.json", "imagegen/content-page-contract.md", "imagegen/template-page-contract.md"]:
            self.assertTrue((ROOT / "templates" / name).exists(), name)

    def test_scripts_exist(self):
        for name in ["extract_docx.py", "init_project.py", "validate_script.py", "validate_project.py", "build_manifest.py", "build_generation_prompt.py", "package_release.py", "release_check.py", "validate_imagegen_contract.py"]:
            self.assertTrue((ROOT / "scripts" / name).exists(), name)


if __name__ == "__main__":
    unittest.main()
