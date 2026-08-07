from pathlib import Path
import re
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from build_generation_prompt import build  # noqa: E402

PAGE_RE = re.compile(r"^##\s*第(\d+)页[：:]\s*(.+?)\s*$", re.M)
KEY_RE = re.compile(r"【锁定关键文字】\s*\n(.*?)\n\s*【完整上屏内容】", re.S)
VISIBLE_RE = re.compile(r"【完整上屏内容】\s*\n(.*?)\n\s*【结论句要求｜不上屏】", re.S)
MISSION_RE = re.compile(r"页面任务[：:]\s*\n(.*?)\n\s*核心意思[：:]", re.S)
CORE_RE = re.compile(r"核心意思[：:]\s*\n(.*?)\n\s*【输出尺寸｜不上屏】", re.S)
TYPE_RE = re.compile(r"^-\s*页面类型[：:]\s*`?([^`\n]+)`?", re.M)


def split_pages(text: str) -> dict[int, str]:
    matches = list(PAGE_RE.finditer(text))
    result = {}
    for i, m in enumerate(matches):
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        result[int(m.group(1))] = text[m.start():end]
    return result


def norm(text: str) -> str:
    text = re.sub(r"\s+", "", text)
    return text


class GoldenRoundTripTests(unittest.TestCase):
    def test_full_script_compiles_to_golden_page_contract(self):
        source = (ROOT / "examples" / "golden" / "6b157323-3d6e-4507-93b2-ea7ba571548a.md").read_text(encoding="utf-8")
        golden = (ROOT / "examples" / "golden" / "06953cb7-5f43-4d00-8b23-72af9dd467bc.md").read_text(encoding="utf-8")
        generated = build(
            source,
            project="uploaded-script-20260804",
            source_script="D:/CyberPPT/projects/gansu-electric-investment-data-infrastructure-cooperation-20260804/workbench/scripts/final/script-final.md",
            style_source="visual/ACTIVE-STYLE.md",
        )
        gp = split_pages(golden)
        op = split_pages(generated)
        self.assertEqual(sorted(gp), sorted(op))
        for number in sorted(gp):
            g, o = gp[number], op[number]
            gt = TYPE_RE.search(g)
            ot = TYPE_RE.search(o)
            if gt or ot:
                self.assertEqual(gt.group(1) if gt else "content", ot.group(1) if ot else "content", number)
            if "【完整上屏内容】" not in g:
                continue
            for regex in [KEY_RE, VISIBLE_RE]:
                gm, om = regex.search(g), regex.search(o)
                self.assertIsNotNone(gm, (number, regex.pattern))
                self.assertIsNotNone(om, (number, regex.pattern))
                self.assertEqual(norm(gm.group(1)), norm(om.group(1)), number)
            for regex in [MISSION_RE, CORE_RE]:
                self.assertIsNotNone(regex.search(g), (number, regex.pattern))
                self.assertIsNotNone(regex.search(o), (number, regex.pattern))


if __name__ == "__main__":
    unittest.main()
