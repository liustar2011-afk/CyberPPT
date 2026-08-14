from __future__ import annotations

from pathlib import Path

from scripts.dual_image_overlay.prompt_send_enrich import (
    SEND_ENRICH_HEADER,
    apply_deterministic_enrich,
    assert_locked_text_preserved,
    extract_structure_cue,
    resolve_send_prompt,
)


SAMPLE = """【锁定关键文字】
01｜三类知识来源
通用知识沉淀跨学科共性

【完整上屏内容】
**01｜三类知识来源**
 - 通用知识沉淀跨学科共性，专业知识组织30个学科内容。

【页面逻辑｜不上屏】
主导关系：路径转化。
结构形态：贯穿主链——来源归一为对象再进入服务供给；质量与生命周期贯穿主链。
"""


def test_deterministic_enrich_appends_structure_and_materials() -> None:
    out = apply_deterministic_enrich(SAMPLE)
    assert SEND_ENRICH_HEADER in out
    assert "path transformation" in out.lower() or "crosscutting" in out.lower()
    assert "flat editorial" in out or "Materials: flat editorial" in out
    assert "People: default absent" in out
    assert "50/50" in out
    assert "one integrated layout" in out or "Composition:" in out
    assert "Chrome ban" in out
    assert "slide title" in out
    assert "resin/plastic" in out
    assert "01｜三类知识来源" in out
    assert out.index("【锁定关键文字】") < out.index(SEND_ENRICH_HEADER)


def test_structure_cue_maps_path_and_crosscut() -> None:
    cue = extract_structure_cue(SAMPLE)
    assert "Structure:" in cue
    assert "path" in cue.lower() or "crosscut" in cue.lower() or "贯穿" in cue


def test_locked_text_gate_rejects_dropped_onscreen() -> None:
    bad = "【锁定关键文字】\nchanged\n\n【完整上屏内容】\nalso changed\n"
    try:
        assert_locked_text_preserved(SAMPLE, bad)
        raise AssertionError("expected ValueError")
    except ValueError as exc:
        assert "locked section" in str(exc)


def test_resolve_send_modes(tmp_path: Path) -> None:
    off = resolve_send_prompt(approved_prompt=SAMPLE, mode="off")
    assert SEND_ENRICH_HEADER not in off.prompt
    assert off.mode == "off"

    det = resolve_send_prompt(approved_prompt=SAMPLE, mode="deterministic")
    assert SEND_ENRICH_HEADER in det.prompt
    assert det.mode == "deterministic"

    send_path = tmp_path / "send.md"
    send_path.write_text(apply_deterministic_enrich(SAMPLE) + "\nExtra English cue.\n", encoding="utf-8")
    send = resolve_send_prompt(
        approved_prompt=SAMPLE,
        mode="send",
        send_final_path=send_path,
    )
    assert send.used_send_script is True
    assert "Extra English cue" in send.prompt
