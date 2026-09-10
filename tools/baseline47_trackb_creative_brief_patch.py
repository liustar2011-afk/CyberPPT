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


# B4 keeps current production semantics: macro-region copy ownership already exists
# in the v3 MicroVisualFreedom contract. Migrate old wording and bring legacy test
# fixtures up to the authored-onscreen/full-prose/independent-thesis authorities required by Stage2 v3.
replace_exact(
    "tests/test_imagegen_micro_freedom.py",
    '''    assert "Do not move exact visible text from its assigned macro region to another region." in prompt
''',
    '''    assert "Keep each declared copy item within its assigned macro semantic region." in prompt
''',
)

replace_exact(
    "tests/_imagegen_no_visual_structure_base.py",
    '''        self.assertIn("页面任务", prompt)
''',
    '''        self.assertIn("【页面使命（不上屏）】", prompt)
''',
)
replace_exact(
    "tests/_imagegen_no_visual_structure_base.py",
    '''        self.assertIn("核心意思", prompt)
''',
    '''        self.assertIn("【核心判断（不上屏）】", prompt)
''',
)
replace_exact(
    "tests/_imagegen_no_visual_structure_base.py",
    '''        self.assertNotIn("页面使命", prompt)
''',
    '''        self.assertNotIn("【页面使命（不上屏）】", prompt)
''',
)
replace_exact(
    "tests/_imagegen_no_visual_structure_base.py",
    '''        self.assertIn(
            "Do not invent section labels like meta headers; only render 上屏文字 modules.",
            prompt,
        )
''',
    '''        self.assertIn(
            "Do not render prompt field labels or meta headers. Rewrite the source copy into conclusion-first visible Chinese while preserving its factual boundary.",
            prompt,
        )
''',
)
replace_exact(
    "tests/_imagegen_no_visual_structure_base.py",
    '''            "visual_thesis": "Input visibly supports the result through one relationship field.",
''',
    '''            "visual_thesis": "The image shows Input supporting Result through one directed relationship.",
''',
)
replace_exact(
    "tests/_imagegen_no_visual_structure_base.py",
    '''            "core_message": "Input visibly supports the result through one relationship field.",
            "must_not_include": [],
''',
    '''            "core_message": "Input visibly supports the result through one relationship field.",
            "full_prose": "Input supports Result through one relationship field.",
            "onscreen_source": "authored",
            "onscreen_text": "Input\\nResult",
            "must_not_include": [],
''',
)

replace_exact(
    "tests/test_imagegen_no_visual_structure.py",
    '''        self.assertLess(
            prompt.index("Page-specific visual intent"),
            prompt.index("### 2. Semantic anchor and composition — hard"),
        )
''',
    '''        self.assertLess(
            prompt.index("Page-specific visual intent"),
            prompt.index("GPT Image 2.5 Artifact Spec 执行版"),
        )
''',
)
replace_exact(
    "tests/test_imagegen_no_visual_structure.py",
    '''        self.assertNotIn(
            "Keep all locked Chinese text complete.",
            spec10.art_direction.contract,
        )
''',
    '''        self.assertIn(
            "Keep all locked Chinese text complete, unchanged and in its original order.",
            spec10.art_direction.contract,
        )
''',
)
replace_exact(
    "tests/test_imagegen_no_visual_structure.py",
    '''        self.assertEqual(spec9.typography, spec10.typography)
        self.assertEqual(spec9.hard_constraints, spec10.hard_constraints)

        hashes9 = {key: value for key, value in spec9.source_hashes if key != "style_lock"}
''',
    '''        self.assertEqual(spec9.typography, spec10.typography)
        self.assertEqual(spec9.hard_constraints, spec10.hard_constraints)
        self.assertEqual(spec9.copy_contract, spec10.copy_contract)
        self.assertEqual(spec9.composition_strategy, spec10.composition_strategy)
        self.assertEqual(spec9.region_graph, spec10.region_graph)
        self.assertEqual(spec9.visual_medium_policy, spec10.visual_medium_policy)
        self.assertEqual(spec9.text_capacity, spec10.text_capacity)
        self.assertEqual(spec9.full_slide_design_context, spec10.full_slide_design_context)
        self.assertEqual(spec9.acceptance, spec10.acceptance)

        hashes9 = {key: value for key, value in spec9.source_hashes if key != "style_lock"}
''',
)

print("Track B4 micro-freedom/no-visual-structure contract patch applied")
