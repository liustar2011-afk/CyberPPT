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


# B5: one production diagnostics compatibility fix plus three wording migrations.
# Diagnostics must recognize both legacy and current deliverable prompt content markers.
replace_exact(
    "scripts/imagegen_pipeline/prompt_diagnostics.py",
    '''_CONTENT_START = "【上屏文字参考】"
_CONTENT_END = "【构图指令】"
''',
    '''_CONTENT_STARTS = (
    "【上屏文字参考】",
    "【内容锁定】",
    "【源文案语义输入】",
)
_CONTENT_END = "【构图指令】"
''',
)
replace_exact(
    "scripts/imagegen_pipeline/prompt_diagnostics.py",
    '''_CONTENT_FIRST_STARTS = (
    "【页面任务｜",
    "页面任务：",
)
''',
    '''_CONTENT_FIRST_STARTS = (
    "【页面使命（不上屏）】",
    "【页面任务｜",
    "页面任务：",
)
''',
)
replace_exact(
    "scripts/imagegen_pipeline/prompt_diagnostics.py",
    '''def _section(text: str, start: str, end: str | None = None) -> str:
    if start not in text:
        return ""
    value = text.split(start, 1)[1]
    if end and end in value:
        value = value.split(end, 1)[0]
    return value.strip()


def _content_first_page_section(text: str) -> str:
''',
    '''def _section(text: str, start: str, end: str | None = None) -> str:
    if start not in text:
        return ""
    value = text.split(start, 1)[1]
    if end and end in value:
        value = value.split(end, 1)[0]
    return value.strip()


def _first_marker(text: str, markers: tuple[str, ...]) -> str:
    """Return the earliest supported marker present in a compiled prompt."""

    present = [(text.index(marker), marker) for marker in markers if marker in text]
    return min(present)[1] if present else ""


def _content_first_page_section(text: str) -> str:
''',
)
replace_exact(
    "scripts/imagegen_pipeline/prompt_diagnostics.py",
    '''    content = _section(prompt, _CONTENT_START, _CONTENT_END)
    if not content:
        content = _content_first_page_section(prompt)
    composition = ""
    if _COMPOSITION_START in prompt and _CONTENT_START in prompt:
        composition = prompt.split(_COMPOSITION_START, 1)[1].split(_CONTENT_START, 1)[0]
''',
    '''    content_start = _first_marker(prompt, _CONTENT_STARTS)
    content = _section(prompt, content_start, _CONTENT_END) if content_start else ""
    if not content:
        content = _content_first_page_section(prompt)
    composition = ""
    if _COMPOSITION_START in prompt and content_start:
        composition = prompt.split(_COMPOSITION_START, 1)[1].split(content_start, 1)[0]
''',
)

# Page Manifest: retain provenance/authority checks, migrate retired prompt labels and
# Style09 English section headings to the current Chinese live contract.
replace_exact(
    "tests/_imagegen_page_manifest_base.py",
    '''        self.assertIn("【锁定关键文字】", prompt)
        self.assertIn("【页面内容素材｜允许提炼、改写、重组】", prompt)
''',
    '''        self.assertIn("【核心判断（不上屏）】", prompt)
        self.assertIn("【页面内容素材｜允许提炼、改写、重组】", prompt)
''',
)
replace_exact(
    "tests/test_imagegen_page_manifest.py",
    '''        self.assertIn("### 1. Style identity and semantic principle — hard", prompt)
        self.assertIn("### 2. Semantic anchor and composition — hard", prompt)
        self.assertIn("### 6. Depth, material and icon discipline — hard", prompt)
''',
    '''        self.assertIn("# 视觉风格09：纯白 + 深蓝领导汇报｜GPT Image 2.5 Artifact Spec 执行版", prompt)
        self.assertIn("## 00｜任务契约：先定义成品，再执行风格", prompt)
        self.assertIn("## 02｜Artifact Spec 内部编译：先把页面变成“可验收规格”", prompt)
''',
)

# Visual Grammar: align the exact snapshot with the current source-boundary wording.
replace_exact(
    "tests/test_visual_grammar.py",
    '''        "graphical state unless that text is present in the locked on-screen content."
''',
    '''        "graphical state unless that text is supported by the on-screen content reference."
''',
)

# Add current-marker diagnostic coverage so the production fix is pinned independently
# of the legacy 【内容锁定】 fixture.
replace_exact(
    "tests/test_imagegen_prompt_diagnostics.py",
    '''def test_analyze_prompt_is_read_only() -> None:
    original = PROMPT
    analyze_prompt(PROMPT, onscreen_text="正文")
    assert PROMPT == original


def test_analyze_prompt_measures_content_first_page_sections() -> None:
''',
    '''def test_analyze_prompt_is_read_only() -> None:
    original = PROMPT
    analyze_prompt(PROMPT, onscreen_text="正文")
    assert PROMPT == original


def test_analyze_prompt_measures_current_deliverable_source_section() -> None:
    prompt = """【页面编码】P02｜测试页
【源文案语义输入】
- **治理层｜质量与授权**
- 2025年完成率 95%。

【构图指令】
保持事实准确。
"""
    metrics = analyze_prompt(
        prompt,
        onscreen_text="**治理层｜质量与授权**\\n2025年完成率 95%。",
    )

    assert metrics.page_content_chars > 0
    assert metrics.global_rule_chars > 0
    assert 0 < metrics.page_specific_ratio < 1
    assert metrics.locked_text_preserved is True
    assert metrics.exact_facts_preserved is True


def test_analyze_prompt_measures_content_first_page_sections() -> None:
''',
)

print("Track B5 manifest/diagnostics/visual-grammar patch applied")
