from __future__ import annotations

from cyberppt.script_quality_contract import audit_script_quality, parse_script_markdown


def _audit(script_text: str, *, question: str, status: str = "confirmed") -> set[str]:
    script = parse_script_markdown(script_text)
    outline = {
        "pages": [
            {
                "page_id": "p01",
                "page_type": "content",
                "business_question": question,
                "main_message": script.pages[0].main_message,
                "source_refs": ["S001"],
                "proof_points": [{"source_refs": ["S001"]}],
                "boundary_refs": [],
            }
        ]
    }
    source_truth = {
        "records": [
            {
                "id": "S001",
                "type": "U" if status != "confirmed" else "F",
                "status": status,
                "statement": "测试证据",
            }
        ]
    }
    return {
        issue.code
        for issue in audit_script_quality(script, outline, source_truth)
    }


def test_preflight_detects_certainty_loss_dual_mission_and_node_overload() -> None:
    codes = _audit(
        """## 第1页：测试页

- 页面类型：内容页
- 页面标题：测试页
- 主判断：项目已经批准并正式立项
- 完整文字稿：项目仍处于建议阶段，需要继续论证后再作决定。本页仅用于测试审计合同是否工作。
- 文字稿取舍说明：保留建议阶段限定。
- 证据映射：建议状态→S001。
- 上屏结论：项目已经批准并正式立项
- 上屏文字：
  **模块一**
  - ① 条目
  **模块二**
  - ② 条目
  **模块三**
  - ③ 条目
  **模块四**
  - ④ 条目
  **模块五**
  - ⑤ 条目
  **模块六**
  - ⑥ 条目
- 证据：S001。
- 边界：仍需论证。
- 视觉结构：六个模块并列展示。
""",
        question="为什么要建设？如何正式立项？",
        status="建议",
    )
    assert "FACT_CERTAINTY_LOST" in codes
    assert "PAGE_DUAL_MISSION" in codes
    assert "VISIBLE_NODE_OVERLOAD" in codes


def test_preflight_detects_long_visible_line() -> None:
    codes = _audit(
        """## 第1页：测试页

- 页面类型：内容页
- 页面标题：测试页
- 主判断：现有基础支持继续研究
- 完整文字稿：现有基础支持继续研究，但仍需通过后续工作形成更完整证据。本页保留必要事实和限定。
- 文字稿取舍说明：只保留本页判断。
- 证据映射：既有基础→S001。
- 上屏结论：现有基础支持继续研究
- 上屏文字：
  **既有基础**
  - 这是一条故意写得非常非常长的可见说明文字用于验证单行文字过长时系统能够在进入生图编译以前给出明确而稳定的诊断提醒
  **后续研究**
  - 继续形成证据。
- 证据：S001。
- 边界：不代表正式立项。
- 视觉结构：两类证据共同支撑判断。
""",
        question="现有基础能否支持继续研究",
    )
    assert "ONSCREEN_LINE_TOO_LONG" in codes
