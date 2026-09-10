from __future__ import annotations

import sys
from pathlib import Path


def replace_exact(path: str, old: str, new: str, *, count: int = 1) -> None:
    p = Path(path)
    with p.open("r", encoding="utf-8", newline="") as handle:
        text = handle.read()
    newline = "\r\n" if "\r\n" in text else "\n"
    old_native = old.replace("\n", newline)
    new_native = new.replace("\n", newline)
    found = text.count(old_native)
    if found != count:
        raise SystemExit(
            f"{path}: expected {count} matches, found {found}: {old[:120]!r}"
        )
    text = text.replace(old_native, new_native, count)
    with p.open("w", encoding="utf-8", newline="") as handle:
        handle.write(text)


def c1() -> None:
    replace_exact(
        "tests/test_content_route.py",
        '''    issues, warnings = audit_deck_plan(_plan(page), _foundation())
    assert any("AUTHOR_FIELDS_FORBIDDEN" in issue for issue in issues)
    assert warnings == []
''',
        '''    issues, warnings = audit_deck_plan(_plan(page), _foundation())
    assert any("AUTHOR_FIELDS_FORBIDDEN" in issue for issue in issues)
    assert any("PLAN_PAGE_WITHOUT_EVIDENCE" in warning for warning in warnings)
''',
    )


def c2() -> None:
    replace_exact(
        "tests/_final_script_pages_base.py",
        '''            self.assertIn("Do not render title, subtitle, logo, page number, footer, or template frame.", prompt)
''',
        '''            self.assertIn("不得绘制页面标题、副标题、页码、页面序号、Logo 或页脚", prompt)
''',
    )
    replace_exact(
        "tests/_final_script_pages_base.py",
        '''            "【核心意思表达要求", 1
''',
        '''            "【输出尺寸｜不上屏】", 1
''',
        count=2,
    )


def c3() -> None:
    for path in (
        "tests/fixtures/script_quality_contract_baseline.json",
        "tests/fixtures/script_quality_contract_baseline_2.json",
    ):
        replace_exact(
            path,
            '''        "onscreen_judgment_mode": "",
        "onscreen_text":''',
            '''        "onscreen_judgment_mode": "",
        "onscreen_source": "authored",
        "onscreen_text":''',
        )


def c4() -> None:
    replace_exact(
        "tests/test_skill_contract.py",
        '''PROJECT_AGENTS = ROOT / "projects" / "AGENTS.md"
''',
        '''''',
    )
    replace_exact(
        "tests/test_skill_contract.py",
        '''    def test_default_project_route_uses_current_strict_pipeline(self) -> None:
        agents = PROJECT_AGENTS.read_text(encoding="utf-8-sig")
        workflow = WORKFLOW.read_text(encoding="utf-8-sig")
        source_skill = SOURCE_SKILL.read_text(encoding="utf-8-sig")
        self.assertIn("New source-to-script projects use the `strict/legacy` profile by default", agents)
        self.assertIn("一次业务语义理解", workflow)
''',
        '''    def test_default_project_route_uses_current_profile_router(self) -> None:
        agents = AGENTS.read_text(encoding="utf-8-sig")
        workflow = WORKFLOW.read_text(encoding="utf-8-sig")
        source_skill = SOURCE_SKILL.read_text(encoding="utf-8-sig")
        self.assertIn("默认使用快速、忠实的 `script` profile", agents)
        self.assertIn("strict/legacy", agents)
        self.assertIn("一次业务语义理解", workflow)
''',
    )


def c5() -> None:
    replace_exact(
        "scripts/image_to_pptx_runtime/authored_layers.py",
        '''    temporary.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\\n", encoding="utf-8")
''',
        '''    temporary.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\\n",
        encoding="utf-8",
        newline="\\n",
    )
''',
    )
    replace_exact(
        "scripts/image_to_pptx_runtime/template_assembly.py",
        '''        output.write_text(ET.tostring(root, encoding="unicode") + "\\n", encoding="utf-8")
''',
        '''        output.write_text(
            ET.tostring(root, encoding="unicode") + "\\n",
            encoding="utf-8",
            newline="\\n",
        )
''',
    )
    replace_exact(
        "scripts/image_to_pptx_runtime/text_measure.py",
        '''        output_path.write_text(rendered_json + '\\n', encoding='utf-8')
''',
        '''        output_path.write_text(rendered_json + '\\n', encoding='utf-8', newline='\\n')
''',
    )
    replace_exact(
        "scripts/image_to_pptx_runtime/svg_quality/checker.py",
        '''        report_path.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2) + '\\n',
            encoding='utf-8',
        )
''',
        '''        report_path.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2) + '\\n',
            encoding='utf-8',
            newline='\\n',
        )
''',
    )


PHASES = {"c1": c1, "c2": c2, "c3": c3, "c4": c4, "c5": c5}


def main() -> int:
    if len(sys.argv) != 2 or sys.argv[1] not in PHASES:
        print(f"usage: {Path(sys.argv[0]).name} <{'|'.join(PHASES)}>", file=sys.stderr)
        return 2
    phase = sys.argv[1]
    PHASES[phase]()
    print(f"Track C {phase.upper()} patch applied")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
