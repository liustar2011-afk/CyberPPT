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


# B2 is a test-contract migration. The current deliverable compiler intentionally
# supports an omitted explicit style lock by resolving the default Style 09 contract,
# strips authoring field labels from visible source material, and carries the current
# Chinese live Artifact Spec as the Style 09 safety authority.
replace_exact(
    "tests/_imagegen_deliverable_prompt_base.py",
    '''    def test_compile_requires_style_lock(self) -> None:
        with TemporaryDirectory() as directory:
            script = Path(directory) / "script.md"
            script.write_text("## P2 核心结论\\n组件A：最终内容\\n", encoding="utf-8")

            with self.assertRaisesRegex(ValueError, "missing visual style lock"):
                compile_pages(script, [2])
''',
    '''    def test_compile_without_explicit_style_lock_uses_default_style09_contract(self) -> None:
        with TemporaryDirectory() as directory:
            script = Path(directory) / "script.md"
            script.write_text("## P2 核心结论\\n组件A：最终内容\\n", encoding="utf-8")

            prompt = compile_pages(script, [2])

        default_contract = str(
            resolve_default_style(style_id=9).get("prompt_contract") or ""
        ).strip()
        self.assertTrue(default_contract)
        self.assertIn("最终内容", prompt)
        self.assertIn("【源头视觉规则权威｜最高优先级】", prompt)
        self.assertIn(default_contract.splitlines()[0], prompt)
''',
)
replace_exact(
    "tests/_imagegen_deliverable_prompt_base.py",
    '''        self.assertNotIn("页面使命", prompt)
''',
    '''        self.assertNotIn("本页结论标题", prompt)
''',
)
replace_exact(
    "tests/_imagegen_deliverable_prompt_base.py",
    '''        self.assertIn("上屏文字", prompt)
        self.assertIn("关键变化", prompt)
''',
    '''        self.assertNotIn("【源文案语义输入】\\n- 上屏文字", prompt)
        self.assertIn("关键变化", prompt)
        self.assertIn("全社会用电量增长", prompt)
''',
)

replace_exact(
    "tests/test_imagegen_deliverable_prompt.py",
    '''        self.assertIn("默认不出现人物", prompt)
        self.assertIn("禁止正脸、围桌会议、多人讨论及摆拍办公场景", prompt)
        self.assertIn("organization names, logos, seals, signage", prompt)
        self.assertIn("Auxiliary semantic imagery may use a small amount of clear Chinese labels", prompt)
        self.assertIn("Preserve the full factual meaning", prompt)
        self.assertIn("pseudo-Chinese", prompt)
        self.assertIn("Do not use arrows or arrowheads anywhere on the page", prompt)
        self.assertIn("共享谓词、共享限定语和父级说明不得复制或改写到每个并列子项", prompt)
        self.assertIn("页面任务、核心意思、页面逻辑、视觉结构、语义关系和所有不上屏区块只决定构图", prompt)
''',
    '''        self.assertIn("GPT Image 2.5 Artifact Spec 执行版", prompt)
        self.assertIn("不生成伪文字、虚构刻度、虚构 UI、无依据数据或随机标签", prompt)
        self.assertIn("不使用无关 Logo、水印、品牌标识和随机场景文字", prompt)
        self.assertIn("不让正面人物宣传照成为默认主视觉", prompt)
        self.assertIn("只使用来源明确支持的关系，不凭视觉需要补造层级、闭环、双向交互、比例或优先级", prompt)
        self.assertIn("不用面积、距离、颜色、箭头或层级暗示来源未支持的优先级、比例和关系", prompt)
        self.assertIn("最终结果应呈现：纯白、深蓝、编辑式、高端、精确、克制、内容驱动的领导汇报正文图。", prompt)
''',
)

print("Track B2 deliverable-prompt test contract patch applied")
