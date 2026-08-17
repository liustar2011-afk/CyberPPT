from cyberppt.script_quality.onscreen import _onscreen_detail_terminal_punctuation_hits


def test_flags_label_detail_lines_ending_in_terminal_punctuation() -> None:
    text = (
        "①常态质量保障\n"
        "  标准分工：数据、模型、场景和商务履约各设质量标准。\n"
        "  统一受理：数智公司统一受理客户咨询投诉，伙伴保障响应\n"
        "  监测内容：数据质量、接口运行、模型输出和安全事件；\n"
    )
    hits = _onscreen_detail_terminal_punctuation_hits(text)
    assert hits == (
        "标准分工：数据、模型、场景和商务履约各设质量标准。",
        "监测内容：数据质量、接口运行、模型输出和安全事件；",
    )


def test_leaves_bare_module_headings_and_boundary_sentences_alone() -> None:
    text = (
        "【质量保障主链条】\n"
        "①常态质量保障\n"
        "接入不改变合作伙伴控制关系。\n"
    )
    assert _onscreen_detail_terminal_punctuation_hits(text) == ()


def test_ignores_a_trailing_dunhao_list_that_ends_cleanly() -> None:
    text = "  评估标准：需求真实性、资源可用性、技术可行性\n"
    assert _onscreen_detail_terminal_punctuation_hits(text) == ()
