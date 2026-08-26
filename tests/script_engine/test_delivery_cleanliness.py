from __future__ import annotations

import json
from pathlib import Path

from script_engine.delivery_cleanliness import (
    argument_pattern_label,
    check_delivery_cleanliness,
    sanitize_delivery_prose,
    sanitize_relation_text,
)
from script_engine.render import render_stage02_markdown

ROOT = Path(__file__).resolve().parents[2]


def test_argument_pattern_label_maps_internal_models_to_delivery_chinese() -> None:
    assert argument_pattern_label("problem-to-response mapping") == "问题回应"
    assert argument_pattern_label("classification / taxonomy") == "分类结构"
    assert argument_pattern_label("progression / maturity") == "演进路径"
    assert argument_pattern_label("implementation") == "推进流程"


def test_relation_cleanup_removes_evidence_grade_annotation() -> None:
    assert sanitize_relation_text("问题到响应映射（inferred，源文未逐一显式配对）") == "问题到响应映射"
    assert sanitize_relation_text("并列支撑（explicit）") == "并列支撑"


def test_delivery_prose_removes_page_navigation_and_guardrail_commentary() -> None:
    text = (
        "面对上一页所述的三方面压力，平台以三重定位组织回应。"
        "三重定位与三方面压力的对应关系是分析性归纳而非源文逐条列出的显式配对，但支撑关系清楚。"
        "下一页将说明它们如何组合形成不同成熟度的场景服务形态。"
    )
    cleaned = sanitize_delivery_prose(text)
    assert "上一页" not in cleaned
    assert "分析性归纳" not in cleaned
    assert "下一页" not in cleaned
    assert "针对上述三方面压力" in cleaned
    assert "按业务需求组合" in cleaned


def test_delivery_prose_removes_stale_split_merge_markers() -> None:
    cleaned = sanitize_delivery_prose("六步路径的前三步。前三项依次推进。后三步。第四步继续深化方案。")
    assert "六步路径的前三步" not in cleaned
    assert "后三步。" not in cleaned
    assert "前三项依次推进" in cleaned
    assert "第四步继续深化方案" in cleaned


def test_delivery_cleanliness_flags_dirty_markdown() -> None:
    markdown = "- 主论证链：classification / taxonomy｜A → B\n### 完整文字稿\n面对上一页的结论。\n"
    issues = check_delivery_cleanliness(markdown)
    assert any("internal analysis/model label" in issue for issue in issues)
    assert any("page/chapter navigation" in issue for issue in issues)


def test_delivery_cleanliness_allows_page_navigation_only_in_mission_metadata() -> None:
    markdown = "- 页面使命：承接上一页，为下一页做铺垫。\n### 完整文字稿\n直接陈述业务内容。\n"
    assert check_delivery_cleanliness(markdown) == []


def test_real_power_industry_deck_renders_delivery_clean() -> None:
    path = ROOT / "tests" / "script_engine" / "fixtures" / "projects" / "power-industry-data-infrastructure" / "dist" / "final-script.json"
    payload = json.loads(path.read_text(encoding="utf-8"))
    markdown = render_stage02_markdown(payload)
    assert check_delivery_cleanliness(markdown) == []
    assert "explicit" not in markdown
    assert "inferred" not in markdown
    assert "classification / taxonomy" not in markdown
    assert "进入下一页" not in markdown
    assert "本页展示其中两个" not in markdown
    assert "六步路径的前三步" not in markdown
    assert "后三步。" not in markdown
    assert "主论证链：分类结构" in markdown
