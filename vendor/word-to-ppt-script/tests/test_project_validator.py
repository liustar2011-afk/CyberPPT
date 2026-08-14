from pathlib import Path
import subprocess
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]


class ProjectValidatorTests(unittest.TestCase):
    def test_sample_project_passes(self):
        result = subprocess.run(
            [sys.executable, str(ROOT / "scripts" / "validate_project.py"), str(ROOT / "examples" / "sample-project"), "--strict"],
            cwd=str(ROOT / "scripts"),
            capture_output=True,
            text=True,
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


if __name__ == "__main__":
    unittest.main()
