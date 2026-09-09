from pathlib import Path


def replace_once(path: str, old: str, new: str) -> None:
    p = Path(path)
    text = p.read_text(encoding="utf-8")
    count = text.count(old)
    if count != 1:
        raise SystemExit(f"expected one match in {path}, found {count}: {old[:120]!r}")
    p.write_text(text.replace(old, new, 1), encoding="utf-8", newline="\n")


# Style 10 has its own live contract and dedicated palette asset; align registry reference.
replace_once(
    "scripts/imagegen_pipeline/style_presets/cyberppt_default_styles.json",
    '      "id": 10,\n      "slug": "ivory_deep_blue_scene_copy",\n      "name": "纯白 + 深蓝领导汇报（风格09复制版）",\n      "extension_only": true,\n      "colors": {\n        "background": "#F7F6F0",',
    '      "id": 10,\n      "slug": "ivory_deep_blue_scene_copy",\n      "name": "纯白 + 深蓝领导汇报（风格09复制版）",\n      "extension_only": true,\n      "colors": {\n        "background": "#F7F6F0",',
)
# Limit sample replacement to the Style 10 block by replacing the final occurrence.
p = Path("scripts/imagegen_pipeline/style_presets/cyberppt_default_styles.json")
text = p.read_text(encoding="utf-8")
marker = '"id": 10'
idx = text.index(marker)
head, tail = text[:idx], text[idx:]
old_sample = '"sample": "assets/palette-samples/palette-09.png"'
if tail.count(old_sample) != 1:
    raise SystemExit(f"unexpected Style 10 sample matches: {tail.count(old_sample)}")
tail = tail.replace(old_sample, '"sample": "assets/palette-samples/palette-10.png"', 1)
p.write_text(head + tail, encoding="utf-8", newline="\n")

# Migrate Style 09 assertions from retired English contract text to current live Artifact Spec.
p = Path("tests/test_extended_style_9.py")
text = p.read_text(encoding="utf-8")
old = '''    assert "视觉风格09：纯白 + 深蓝领导汇报" in contract\n    assert "Palette: white #FFFFFF" in contract\n    assert "deep blue #12355B" in contract\n    assert "muted amber #D9772B" in contract\n    assert "Reserve muted amber only for risks, exceptions, constraints, pending status" in contract\n    assert "Every page must establish one visually dominant focus" in contract\n    assert "Build one integrated, asymmetric and unequally weighted composition" in contract\n    assert "Repeated or equally weighted cards are allowed" in contract\n    assert "Avoid equal card walls" not in contract\n    assert "Apply a replaceability test" in contract\n    assert "dominant scene that only signals an industry category is insufficient" in contract\n    assert "Photography is optional" in contract\n    assert "Do not default to one large photograph" in contract\n    assert "several independent scene fragments" in contract\n    assert "Medium and small scenes" in contract\n    assert "Decorative use is acceptable in restrained amounts" in contract\n    assert "Prefer one coherent primary scene" not in contract\n    assert "Icons must not determine the composition" in contract\n    assert len(contract) > 2_000\n'''
new = '''    assert "视觉风格09：纯白 + 深蓝领导汇报｜GPT Image 2.5 Artifact Spec 执行版" in contract\n    assert "配色：纯白 `#FFFFFF`" in contract\n    assert "深蓝 `#12355B`" in contract\n    assert "低饱和琥珀色 `#D9772B`" in contract\n    assert "琥珀色只用于来源明确的风险、约束、例外、待定或决策重点" in contract\n    assert "第一眼必须识别正文主焦点" in contract\n    assert "来源存在主次时，可采用非对称与不等视觉权重；来源等权时保持同层均衡" in contract\n    assert "卡片只在业务信息本身具有明确独立边界时使用" in contract\n    assert "场景按需使用，可以为零" in contract\n    assert "图标只用于提高必要对象的识别效率" in contract\n    assert "每页采用一个主构图机制" in contract\n    assert "## 12｜最终风格收口｜最高视觉优先级" in contract\n    assert "strong visual hierarchy" in contract\n    assert len(contract) > 2_000\n'''
if text.count(old) != 1:
    raise SystemExit("Style 09 invariant assertion block not found uniquely")
text = text.replace(old, new, 1)
text = text.replace('    assert "Palette: white #FFFFFF" in refreshed["style"]["prompt_contract"]\n', '    assert "配色：纯白 `#FFFFFF`" in refreshed["style"]["prompt_contract"]\n', 1)
text = text.replace('    assert "Palette: white #FFFFFF" in contract\n    assert "Build one integrated, asymmetric and unequally weighted composition" in contract\n', '    assert "配色：纯白 `#FFFFFF`" in contract\n    assert "每页采用一个主构图机制" in contract\n', 1)
text = text.replace('    assert "Every page must establish one visually dominant focus" in runtime.terminal_lock\n', '    assert "strong visual hierarchy" in runtime.terminal_lock\n    assert "构图由当前页面语义决定" in runtime.terminal_lock\n', 1)
p.write_text(text, encoding="utf-8", newline="\n")

# Migrate Style 10 live-contract assertions and dedicated sample expectation.
p = Path("tests/test_extended_style_10.py")
text = p.read_text(encoding="utf-8")
text = text.replace(
    '    assert "Prefer a scene-supported executive-report language." in style10["prompt_contract"]\n    assert "Keep all locked Chinese text complete." not in style10["prompt_contract"]\n',
    '    assert "The default visual medium is one open, coherent business scene or concrete business-object field." in style10["prompt_contract"]\n    assert "Keep all locked Chinese text complete, unchanged and in its original order." in style10["prompt_contract"]\n',
    1,
)
text = text.replace(
    '    assert payload["reference_image"]["path"].endswith("palette-09.png")\n',
    '    assert payload["reference_image"]["path"].endswith("palette-10.png")\n',
    1,
)
text = text.replace(
    'def test_style_ten_is_not_advertised_and_reuses_style_nine_palette() -> None:\n',
    'def test_style_ten_is_not_advertised_and_uses_its_dedicated_palette() -> None:\n',
    1,
)
text = text.replace(
    '    assert not (ROOT / "assets" / "palette-samples" / "palette-10.png").exists()\n',
    '    assert (ROOT / "assets" / "palette-samples" / "palette-10.png").is_file()\n',
    1,
)
p.write_text(text, encoding="utf-8", newline="\n")

print("Track A2 style-contract patch applied")
