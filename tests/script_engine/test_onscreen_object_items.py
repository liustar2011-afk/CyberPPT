"""v1.1 item identifiers must not hide visible copy from semantic audits."""
from copy import deepcopy

from script_engine.analysis_audits.final_authoring_expression import _onscreen_module_lines
from script_engine.author_contracts import _onscreen_lines
from script_engine.onscreen_contracts import (
    check_onscreen_code_context, check_onscreen_hierarchy_punctuation,
    check_onscreen_projection_structure,
)
from script_engine.onscreen_projection import review_onscreen_projection
from script_engine.onscreen_quality import visible_character_count
from script_engine.semantic_text_primitives import onscreen_item_text


def test_identified_items_have_the_same_visible_payload_as_legacy_strings():
    legacy = {'heading': '实施计划', 'items': ['计划于2027年完成验收', '比例为15%至25%']}
    identified = deepcopy(legacy)
    identified['items'] = [{'id': f'M{i}', 'text': text} for i, text in enumerate(legacy['items'])]
    assert _onscreen_module_lines(identified) == _onscreen_module_lines(legacy)
    assert _onscreen_lines({'onscreen': [identified]}) == _onscreen_lines({'onscreen': [legacy]})
    assert visible_character_count([identified]) == visible_character_count([legacy])
    slide = {'page_type': 'content', 'onscreen': [identified, {'heading': '其他'}]}
    assert not check_onscreen_projection_structure({'slides': [slide]})


def test_item_metadata_is_not_visible_content():
    assert onscreen_item_text({'id': 'M2027', 'text': ''}) == ''
    assert onscreen_item_text({'id': 'M2027'}) == ''
    assert onscreen_item_text({'text': 2027}) == ''
    assert visible_character_count([{'items': [{'id': 'M2027'}]}]) == 0


def test_identified_items_still_detect_status_promotion_and_lost_conditions():
    slide = {'full_copy': '计划完成平台验收。\n在客户确认后，平台启动结算。',
             'onscreen': [{'items': [{'id': 'M1', 'text': '已完成平台验收'}]},
                          {'items': [{'id': 'M2', 'text': '平台启动结算'}]}]}
    codes = {f['code'] for f in review_onscreen_projection(slide)['findings']}
    assert 'ONSCREEN_LOCAL_STATUS_PROMOTED' in codes
    assert 'ONSCREEN_LOCAL_CONDITION_LOST' in codes


def test_identified_items_still_detect_bad_hierarchy_and_code_only_mapping():
    final = {'slides': [{'page_type': 'content', 'onscreen': [
        {'items': [{'id': 'M1', 'text': '部署：方式：本地部署'}]},
        {'items': [{'id': 'M2', 'text': 'A→B'}]},
    ]}]}
    assert check_onscreen_hierarchy_punctuation(final)
    assert check_onscreen_code_context(final)
