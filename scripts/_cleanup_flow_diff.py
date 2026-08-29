from __future__ import annotations

import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main_blob(path: str) -> bytes:
    return subprocess.check_output(["git", "show", f"origin/main:{path}"], cwd=ROOT)


# Restore generated packaging metadata exactly to main.
for rel in ("cyberppt.egg-info/PKG-INFO", "cyberppt.egg-info/SOURCES.txt"):
    (ROOT / rel).write_bytes(main_blob(rel))

# Rebuild README from main bytes so its original CRLF layout is preserved,
# then apply only the intended workflow wording changes.
readme = main_blob("README.md").decode("utf-8")
replacements = {
    "- 生成逐页正文内容区 ImageGen 蓝图，用于锁定正文区构图、层级、密度、色板和图表语言；标题、副标题和公共模板元素由模板/可编辑文字层生成。":
        "- 根据逐页脚本生成完整正文视觉稿，锁定页面主体的构图、层级、密度、色板和图表语言。",
    "- 使用“复杂视觉保真 + 主要文字可编辑”的混合还原策略生成 PPTX。":
        "- 使用“完整图视觉保真 + 原生文字/形状可编辑”的重建策略生成 PPTX。",
    "- 第三阶段只使用已审计 full 图 → 可编辑 SVG → 原生 PPTX 的重建链。每页先盘点可还原区域和注册图层；未验证的数据图、标识或文字必须标记 `manual_required` 并阻断交付，禁止以整页截图蒙版回退。":
        "- 第三阶段只使用已审计 full 图 → 可编辑 SVG → 原生 PPTX 的重建链。可编辑分支对通过审计的 full 图写入 SHA-256 视觉来源绑定；SVG 阶段负责高保真复刻和拆层，不重新设计页面。每页先盘点可还原区域和注册图层；未验证的数据图、标识或文字必须标记 `manual_required` 并阻断交付，禁止以整页截图蒙版回退。",
    "关键原则：`结构可编辑` 和 `视觉还原` 是同等硬门槛；`strict QA` 通过不等于视觉合格；ImageGen 蓝图是参考，不是最终 PPT 背景。":
        "关键原则：`结构可编辑` 和 `视觉还原` 是同等硬门槛；`strict QA` 通过不等于视觉合格；通过审计并完成来源绑定的 full 图是可编辑重建的视觉来源，后续拆层保持其已接受的视觉构图。",
    "git clone https://github.com/crazyykhllc-bit/CyberPPT.git CyberPPT":
        "git clone https://github.com/liustar2011-afk/CyberPPT.git CyberPPT",
}
for old, new in replacements.items():
    if old not in readme:
        raise RuntimeError(f"README cleanup anchor missing: {old}")
    readme = readme.replace(old, new, 1)
(ROOT / "README.md").write_bytes(readme.encode("utf-8"))

# Restore the production CI definition; temporary cleanup tooling must not
# survive the final commit.
workflow = '''name: CyberPPT tests\n\non:\n  pull_request:\n  push:\n    branches:\n      - main\n\njobs:\n  test:\n    runs-on: ubuntu-latest\n    strategy:\n      fail-fast: false\n      matrix:\n        python-version: ["3.10", "3.12"]\n    steps:\n      - uses: actions/checkout@v4\n      - uses: actions/setup-python@v5\n        with:\n          python-version: ${{ matrix.python-version }}\n          cache: pip\n      - name: Install package and test dependencies\n        run: |\n          python -m pip install --upgrade pip\n          python -m pip install -e ".[test]"\n      - name: Environment check\n        run: |\n          python -m pip check\n          python -m pytest --version\n      - name: Run test suite\n        run: python -m pytest -q\n'''
(ROOT / ".github/workflows/tests.yml").write_text(workflow, encoding="utf-8", newline="\n")
Path(__file__).unlink()
