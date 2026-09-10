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


# B3 is a compatibility-test migration. The modular implementation and facade are
# already the same callable objects; keep that strong parity check and migrate only
# retired Style09 English wording/section markers to the current Chinese live contract.
replace_exact(
    "tests/test_imagegen_handoff_modularization.py",
    '''    assert "pure white background #FFFFFF" in via_facade
''',
    '''    assert "GPT Image 2.5 Artifact Spec 执行版" in via_facade
    assert "配色：纯白 `#FFFFFF`，深蓝 `#12355B`" in via_facade
''',
)
replace_exact(
    "tests/test_imagegen_handoff_modularization.py",
    '''    assert "### 2. Semantic anchor and composition — hard" in prompt
    assert "【最终视觉执行约束｜最高优先级】" in prompt
''',
    '''    assert "【页面使命（不上屏）】" in prompt
    assert "【核心判断（不上屏）】" in prompt
    assert "【页面内容素材｜允许提炼、改写、重组】" in prompt
    assert "GPT Image 2.5 Artifact Spec 执行版" in prompt
    assert "【最终视觉执行约束｜最高优先级】" in prompt
''',
)
replace_exact(
    "tests/test_imagegen_handoff_modularization.py",
    '''    assert metadata["compiler_version"]
    assert metadata["text_render_mode"]
    assert "pure white background #FFFFFF" in compiled.prompt
''',
    '''    assert metadata["compiler_version"] == "content-first-v1"
    assert metadata["text_render_mode"] == "full_image"
    assert metadata["style_selection"]["id"] == 9
    assert metadata["style_selection"]["name"] == "纯白 + 深蓝领导汇报"
    assert "style.selected_lock" in metadata["injected_rule_ids"]
    assert "GPT Image 2.5 Artifact Spec 执行版" in compiled.prompt
''',
)

print("Track B3 handoff-modularization test contract patch applied")
