from __future__ import annotations

from pathlib import Path

from scripts.dual_image_overlay.image_text_qa import inspect_image_text, write_image_text_qa


def test_image_text_qa_fails_on_process_instruction() -> None:
    report = inspect_image_text(
        page=16,
        image_path=Path("page_016_full.png"),
        allowed_lines=["资源保障", "风险管控"],
        ocr_text="资源保障\n本页说明：请将风险放在右侧",
    )

    assert report["status"] == "failed"
    assert report["deliverable_allowed"] is False
    assert report["forbidden_matches"][0]["class"] == "process_instruction"


def test_image_text_qa_requires_review_for_unexpected_business_text() -> None:
    report = inspect_image_text(
        page=16,
        image_path=Path("page_016_full.png"),
        allowed_lines=["资源保障", "风险管控"],
        ocr_text="资源保障\n风险管控\n新增未经锁定的判断",
    )

    assert report["status"] == "review_required"
    assert report["deliverable_allowed"] is False
    assert report["unexpected_text"] == ["新增未经锁定的判断"]


def test_image_text_qa_passes_when_observed_text_matches_allowed_content(tmp_path: Path) -> None:
    report = inspect_image_text(
        page=16,
        image_path=tmp_path / "page_016_full.png",
        allowed_lines=["资源保障", "风险管控"],
        ocr_text="资源保障\n风险管控",
    )
    output = write_image_text_qa(report, tmp_path / "page_016.json")

    assert report["status"] == "passed"
    assert report["deliverable_allowed"] is True
    assert output.exists()
