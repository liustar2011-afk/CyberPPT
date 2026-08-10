from pathlib import Path
import subprocess
import sys


ROOT = Path(__file__).resolve().parents[1]
FIXTURE_TEST = (
    ROOT
    / "vendor"
    / "skills"
    / "ppt-visual-structure-designer"
    / "scripts"
    / "test_domain_neutral_fixtures.py"
)


def test_domain_neutral_visual_structure_fixtures() -> None:
    result = subprocess.run(
        [sys.executable, str(FIXTURE_TEST)],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=True,
    )

    assert "6 valid" in result.stdout
    assert "60 invalid" in result.stdout
    assert "18 style variants" in result.stdout
