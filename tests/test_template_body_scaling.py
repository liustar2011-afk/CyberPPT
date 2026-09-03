"""Regression coverage for the original two-page Quick reconstruction."""

import xml.etree.ElementTree as ET

import pytest

from scripts.image_to_pptx_runtime.template_assembly import _materialize_body_scale


def test_inherited_and_overridden_metrics_are_scaled_once():
    root = ET.fromstring('''<svg><g font-size="20" letter-spacing="2" stroke-width="4">
        <g><text x="200" y="100">继承字号</text></g>
        <text x="400" y="150" font-size="30">单独字号<tspan font-size="10">补充</tspan></text>
    </g></svg>''')
    _materialize_body_scale(root, scale_x=0.5, scale_y=0.5)
    group = root.find('g')
    assert group.attrib == {'font-size': '10', 'letter-spacing': '1', 'stroke-width': '4'}
    inherited = group.find('g/text')
    assert inherited.attrib == {'x': '100', 'y': '50'}
    explicit = group.find('text')
    assert explicit.attrib == {'x': '200', 'y': '75', 'font-size': '15'}
    assert explicit.find('tspan').get('font-size') == '5'


@pytest.mark.parametrize('rotation,expected', [
    ('rotate(-10 1600 500)', 'rotate(-10 800 250)'),
    ('rotate(-10,1600,500)', 'rotate(-10 800 250)'),
    ('rotate(15)', 'rotate(15 0 0)'),
])
def test_native_text_rotation_retains_scaled_pivot(rotation, expected):
    text = ET.Element('text', {'x': '1600', 'y': '500', 'font-size': '20', 'transform': rotation})
    _materialize_body_scale(text, scale_x=0.5, scale_y=0.5)
    assert text.get('transform') == expected
    assert text.get('x') == '800'
    assert text.get('y') == '250'
    assert text.get('font-size') == '10'


@pytest.mark.parametrize('tag,transform,sx,sy', [
    ('g', 'rotate(10)', 0.5, 0.5),
    ('text', 'scale(2)', 0.5, 0.5),
    ('text', 'rotate(10 100 200)', 0.5, 0.6),
    ('text', 'rotate(10) translate(5 5)', 0.5, 0.5),
    ('text', 'rotate(10garbage)', 0.5, 0.5),
])
def test_unsupported_source_transforms_still_fail(tag, transform, sx, sy):
    with pytest.raises(ValueError, match='source transform'):
        _materialize_body_scale(ET.Element(tag, {'transform': transform}), scale_x=sx, scale_y=sy)


def test_path_metrics_are_not_scaled_twice():
    path = ET.Element('path', {'d': 'M 0 0 L 20 20', 'stroke-width': '4'})
    _materialize_body_scale(path, scale_x=0.5, scale_y=0.5)
    assert path.get('stroke-width') == '4'
    assert path.get('d') == 'M 0 0 L 20 20'
    assert path.get('transform') == 'matrix(0.5 0 0 0.5 0 0)'
