from cyberppt.full_image_rhythm_audit import audit_deck_visual_rhythm


def _sig(
    page: int,
    *,
    skeleton: str = "010111010",
    horizontal: str = "center",
    vertical: str = "middle",
    density: str = "medium",
    medium: str = "mixed",
    structure_hash: str = "0f0f0f0f0f0f0f0f",
):
    return {
        "page_number": page,
        "skeleton_3x3": skeleton,
        "gravity": {"horizontal": horizontal, "vertical": vertical},
        "density": density,
        "visual_medium": medium,
        "structure_hash": structure_hash,
    }


def test_adjacent_near_identical_composition_warns():
    result = audit_deck_visual_rhythm([
        _sig(1, structure_hash="0f0f0f0f0f0f0f0f"),
        _sig(2, structure_hash="0f0f0f0f0f0f0f0e"),
    ])
    assert result["status"] == "passed_with_warnings"
    assert any(item["code"] == "ADJACENT_COMPOSITION_REPEAT" for item in result["findings"])


def test_three_consecutive_near_identical_pages_block_freeze():
    result = audit_deck_visual_rhythm([
        _sig(1, structure_hash="0f0f0f0f0f0f0f0f"),
        _sig(2, structure_hash="0f0f0f0f0f0f0f0e"),
        _sig(3, structure_hash="0f0f0f0f0f0f0f0c"),
    ])
    assert result["status"] == "blocked"
    blocker = next(item for item in result["findings"] if item["code"] == "TRIPLE_RHYTHM_REPEAT")
    assert blocker["pages"] == [1, 2, 3]


def test_same_style_without_same_composition_does_not_block():
    result = audit_deck_visual_rhythm([
        _sig(1, skeleton="100100100", horizontal="left", structure_hash="f000f000f000f000"),
        _sig(2, skeleton="010010010", horizontal="center", structure_hash="0f000f000f000f00"),
        _sig(3, skeleton="001001001", horizontal="right", structure_hash="00f000f000f000f0"),
    ])
    assert result["status"] == "passed"
    assert result["blocker_count"] == 0


def test_medium_dominance_and_streak_are_warnings_only():
    signatures = [
        _sig(
            page,
            skeleton=("100100100" if page % 2 else "001001001"),
            horizontal=("left" if page % 2 else "right"),
            medium="business_scene",
            structure_hash=f"{page:016x}",
        )
        for page in range(1, 9)
    ]
    result = audit_deck_visual_rhythm(signatures)
    assert result["status"] == "passed_with_warnings"
    assert any(item["code"] == "MEDIUM_DOMINANCE" for item in result["findings"])
    assert not any(item["severity"] == "block" for item in result["findings"])
