from pathlib import Path


def replace_exact(path: str, old: str, new: str, *, count: int = 1) -> None:
    p = Path(path)
    text = p.read_text(encoding="utf-8")
    found = text.count(old)
    if found != count:
        raise SystemExit(f"{path}: expected {count} matches, found {found}: {old[:100]!r}")
    p.write_text(text.replace(old, new, count), encoding="utf-8", newline="\n")


# Production fix: composition review metadata belongs after page semantics, never inside
# the title/mission/core-meaning context block.  Keep it immediately before the
# presentation/canvas contracts in both semantic_visual and full_image branches.
replace_exact(
    "scripts/imagegen_pipeline/handoff/prompt.py",
    '''            logic_contract if include_logic_context else "",\n            "",\n            presentation_contract,\n''',
    '''            logic_contract if include_logic_context else "",\n            "",\n            semantic_composition_contract.strip(),\n            "",\n            presentation_contract,\n''',
    count=2,
)
replace_exact(
    "scripts/imagegen_pipeline/handoff/prompt.py",
    '''    if semantic_composition_contract:\n        # Composition guidance is semantic metadata, never visible copy.\n        insert_at = 2 if semantic_visual else 3\n        parts[insert_at:insert_at] = [semantic_composition_contract, ""]\n    return relation, "\\n".join(parts).strip() + "\\n"\n''',
    '''    return relation, "\\n".join(parts).strip() + "\\n"\n''',
)

# Migrate Creative Brief tests from retired empty-allowlist / no-context wording to
# the current permissive-but-grounded visual grammar and explicit non-visible context.
p = Path("tests/_imagegen_creative_brief_base.py")
text = p.read_text(encoding="utf-8")
text = text.replace(
    '''    assert "empty auxiliary-label allowlist" in grammar\n    assert "only when the upstream script explicitly supplies a non-empty" in grammar\n    assert "use at most two short labels" not in grammar\n''',
    '''    assert "concise auxiliary labels are allowed" in grammar\n    assert "They do not need a one-to-one mapping" in grammar\n    assert "keep them tied to the content reference" in grammar\n    assert "Do not invent summary, goal, value, outcome, or conclusion sections or labels" in grammar\n''',
    1,
)
text = text.replace(
    '''    assert page.title not in prompt\n''',
    '''    title_context = prompt.split("【标题（不上屏）】", 1)[1].split("【页面使命（不上屏）】", 1)[0]\n    assert page.title in title_context\n    onscreen_material = prompt.split("【页面内容素材｜允许提炼、改写、重组】", 1)[1]\n    assert page.title not in onscreen_material\n''',
    1,
)
text = text.replace(
    '''    assert page.core_message not in prompt\n    assert "页面任务与核心意思用于推导语义关系，也可用于生成结论、总结框或标题" in prompt\n''',
    '''    assert "【核心判断（不上屏）】" in prompt\n    core_context = prompt.split("【核心判断（不上屏）】", 1)[1].split("【完整文字稿（不上屏）】", 1)[0]\n    assert page.core_message in core_context\n    assert "【页面使命（不上屏）】" in prompt\n''',
    1,
)
text = text.replace(
    '''    assert "empty auxiliary-label allowlist" in prompt\n    assert "one-to-one mapping" in prompt\n''',
    '''    assert "concise auxiliary labels are allowed" in prompt\n    assert "do not need a one-to-one mapping" in prompt\n''',
    1,
)
p.write_text(text, encoding="utf-8", newline="\n")

# Current Style09 typography/content authority is the Chinese live Artifact Spec plus
# the content-first conclusion contract, not retired English typography wording.
p = Path("tests/test_imagegen_creative_brief.py")
text = p.read_text(encoding="utf-8")
old = '''    assert "如【锁定关键文字】含正文结论句" in prompt\n    assert "不得通栏放大" in prompt\n    assert "标题竖线、横线等装饰" in prompt\n\n    hierarchy_lock = (\n        "Create hierarchy through crop, overlap, scale contrast, tonal separation, "\n        "alignment, deep-blue emphasis and shallow foreground–background relationships."\n    )\n    assert style_contract.count(hierarchy_lock) == 1\n    assert prompt.count(hierarchy_lock) == 1\n'''
new = '''    assert "【结论句要求｜不上屏】" in prompt\n    assert "结论先行、层级清晰" in prompt\n    assert "不得新增事实" in prompt\n    assert "第一眼必须识别正文主焦点" in style_contract\n    assert prompt.count("第一眼必须识别正文主焦点") == 1\n'''
if text.count(old) != 1:
    raise SystemExit("current visible-judgment legacy assertion block not found uniquely")
text = text.replace(old, new, 1)
p.write_text(text, encoding="utf-8", newline="\n")

print("Track B1 creative-brief patch applied")
