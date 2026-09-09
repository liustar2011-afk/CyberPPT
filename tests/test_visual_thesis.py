import pytest

from cyberppt.visual_thesis import has_relationship_signal, thesis_similarity, validate_visual_thesis


def test_visual_thesis_is_required_and_never_falls_back():
    with pytest.raises(ValueError, match="VISUAL_THESIS_REQUIRED"):
        validate_visual_thesis("", "形成可信协同能力")


def test_visual_thesis_equal_to_core_judgment_is_blocked():
    with pytest.raises(ValueError, match="VISUAL_THESIS_DUPLICATES_CORE_JUDGMENT"):
        validate_visual_thesis("形成可信协同能力", "形成可信协同能力")


def test_near_duplicate_visual_thesis_is_blocked():
    assert thesis_similarity("形成统一可信协同服务能力", "形成统一可信协同服务能力。") >= 0.9
    with pytest.raises(ValueError, match="VISUAL_THESIS_DUPLICATES_CORE_JUDGMENT"):
        validate_visual_thesis("形成统一可信协同服务能力", "形成统一可信协同服务能力。")


def test_non_relational_slogan_is_blocked():
    with pytest.raises(ValueError, match="VISUAL_THESIS_RELATIONSHIP_MISSING"):
        validate_visual_thesis("可信协同能力全面提升", "提升可信协同能力")


def test_relational_visual_thesis_passes():
    thesis = "多主体通过受控接口连接，并汇聚形成可审计的可信协同结果"
    assert has_relationship_signal(thesis)
    assert validate_visual_thesis(thesis, "形成可信协同能力") == thesis


def test_flow_and_boundary_theses_are_relational():
    assert validate_visual_thesis(
        "数据从来源进入受控处理区，再流向服务输出",
        "提升数据服务能力",
    )
    assert validate_visual_thesis(
        "外部主体通过授权边界进入受控空间并形成允许输出",
        "保障数据安全使用",
    )
