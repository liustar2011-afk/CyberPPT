from __future__ import annotations

import json
from pathlib import Path

import pytest
from PIL import Image

from cyberppt.commands.editable_text_three_image import (
    assert_editable_text_batch_ready,
    build_editable_text_batch,
    build_three_image_batch,
    get_production_mode,
    run_three_image_batch,
)
from cyberppt.commands.init_project import init_project


def _write_image(path: Path, size: tuple[int, int] = (320, 180)) -> Path:
    Image.new("RGB", size, "#ffffff").save(path)
    return path


def test_default_production_mode_is_full_image_ppt(tmp_path: Path) -> None:
    project = tmp_path / "project"
    init_project(project)

    assert get_production_mode(project) == "full_image_ppt"


def test_default_editable_batch_uses_two_image_without_text(tmp_path: Path) -> None:
    pairs = tmp_path / "page_image_pairs.json"
    full = _write_image(tmp_path / "full.png")
    background = _write_image(tmp_path / "background.png")
    ocr = tmp_path / "ocr.json"
    ocr.write_text(
        json.dumps({"canonical": {"lines": [{"text": "测试", "bbox": [1, 1, 30, 20], "score": 0.99}]}}),
        encoding="utf-8",
    )
    registration = tmp_path / "registration.json"
    registration.write_text(
        json.dumps({"transform_id": "TF-GLOBAL", "matrix": [[1, 0, 0], [0, 1, 0]]}),
        encoding="utf-8",
    )
    pairs.write_text(
        json.dumps(
            {
                "pairs": [
                    {
                        "page_number": 4,
                        "full": {"path": str(full)},
                        "background": {"path": str(background)},
                        "ocr": str(ocr),
                        "registration": str(registration),
                    }
                ]
            }
        ),
        encoding="utf-8",
    )

    batch = build_three_image_batch(tmp_path, "4", pairs)

    assert batch["input_mode"] == "two-image"
    assert "text" not in batch["pages"][0]
    assert set(batch["pages"][0]["inputs"]) == {"full", "background", "ocr", "registration"}


def test_explicit_three_image_batch_prepares_text_when_missing(tmp_path: Path) -> None:
    pairs = tmp_path / "page_image_pairs.json"
    full = _write_image(tmp_path / "full.png")
    background = _write_image(tmp_path / "background.png")
    ocr = tmp_path / "ocr.json"
    ocr.write_text(
        json.dumps({"canonical": {"lines": [{"text": "测试", "bbox": [1, 1, 30, 20], "score": 0.99}]}}),
        encoding="utf-8",
    )
    registration = tmp_path / "registration.json"
    registration.write_text(
        json.dumps({"transform_id": "TF-GLOBAL", "matrix": [[1, 0, 0], [0, 1, 0]]}),
        encoding="utf-8",
    )
    pairs.write_text(
        json.dumps(
            {
                "pairs": [
                    {
                        "page_number": 4,
                        "full": {"path": str(full)},
                        "background": {"path": str(background)},
                        "ocr": str(ocr),
                        "registration": str(registration),
                    }
                ]
            }
        ),
        encoding="utf-8",
    )

    calls: list[tuple[Path, Path, Path]] = []

    def fake_text_renderer(ocr_path: Path, reference_path: Path, output_path: Path) -> Path:
        calls.append((ocr_path, reference_path, output_path))
        return _write_image(output_path)

    batch = build_editable_text_batch(
        tmp_path,
        "4",
        pairs,
        input_mode="three-image",
        text_renderer=fake_text_renderer,
    )

    assert batch["input_mode"] == "three-image"
    assert Path(batch["pages"][0]["text"]).is_file()
    assert batch["pages"][0]["inputs"]["text"]["path"] == batch["pages"][0]["text"]
    assert calls == [(ocr, full, Path(batch["pages"][0]["text"]))]


def test_build_batch_prepares_missing_two_image_assets(tmp_path: Path) -> None:
    project = tmp_path / "project"
    project.mkdir()
    pairs = project / "page_image_pairs.json"
    full = project / "expected_full.png"
    pairs.write_text(
        json.dumps(
            {
                "pairs": [
                    {
                        "page_number": 4,
                        "full": {
                            "path": str(full),
                            "prompt": "FULL PROMPT MUST BE USED AS-IS",
                        },
                    }
                ]
            }
        ),
        encoding="utf-8",
    )
    calls: list[tuple[str, Path, Path | None, str | None]] = []

    def fake_full_generator(prompt: str, output_path: Path) -> Path:
        calls.append(("full", output_path, None, prompt))
        assert prompt == "FULL PROMPT MUST BE USED AS-IS"
        return _write_image(output_path)

    def fake_background_generator(full_path: Path, output_path: Path) -> Path:
        calls.append(("background", output_path, full_path, None))
        return _write_image(output_path)

    def fake_ocr_generator(image_path: Path, output_path: Path) -> Path:
        calls.append(("ocr", output_path, image_path, None))
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(
            json.dumps({"canonical": {"lines": [{"text": "测试", "bbox": [1, 1, 30, 20], "score": 0.99}]}}),
            encoding="utf-8",
        )
        return output_path

    batch = build_editable_text_batch(
        project,
        "4",
        pairs,
        full_generator=fake_full_generator,
        background_generator=fake_background_generator,
        ocr_generator=fake_ocr_generator,
    )

    job = batch["pages"][0]
    assert batch["input_mode"] == "two-image"
    assert Path(job["full"]).is_file()
    assert Path(job["background"]).is_file()
    assert Path(job["ocr"]).is_file()
    assert Path(job["registration"]).is_file()
    assert "text" not in job
    assert [call[0] for call in calls] == ["full", "background", "ocr"]
    assert "line_corrections" not in json.loads(Path(job["registration"]).read_text(encoding="utf-8"))


def _write_complete_pairs(project: Path, pages: list[int]) -> Path:
    image_dir = project / "inputs"
    image_dir.mkdir(parents=True, exist_ok=True)
    pairs: list[dict[str, object]] = []
    for page in pages:
        full = _write_image(image_dir / f"page_{page:03d}_full.png")
        background = _write_image(image_dir / f"page_{page:03d}_background.png")
        text = _write_image(image_dir / f"page_{page:03d}_text.png")
        ocr = image_dir / f"page_{page:03d}_ocr.json"
        ocr.write_text(json.dumps({"canonical": {"lines": [{"text": "测试", "bbox": [1, 1, 30, 20], "confidence": 0.99}]}}), encoding="utf-8")
        registration = image_dir / f"page_{page:03d}_registration.json"
        registration.write_text(json.dumps({"transform_id": "TF-GLOBAL", "matrix": [[1, 0, 0], [0, 1, 0]]}), encoding="utf-8")
        pairs.append(
            {
                "page_number": page,
                "full": {"path": str(full)},
                "background": {"path": str(background)},
                "text": {"path": str(text)},
                "ocr": str(ocr),
                "registration": str(registration),
            }
        )
    manifest = project / "page_image_pairs.json"
    manifest.write_text(json.dumps({"pairs": pairs}), encoding="utf-8")
    return manifest


def test_review_result_requires_explicit_approval(tmp_path: Path, monkeypatch) -> None:
    project = tmp_path / "project"
    init_project(project)
    pairs = _write_complete_pairs(project, [4])

    def fake_vendor_run(command, check=False, **kwargs):
        output_dir = Path(json.loads(Path(command[-1]).read_text(encoding="utf-8"))["pages"][0]["output_dir"])
        output_dir.mkdir(parents=True, exist_ok=True)
        (output_dir / "page.json").write_text(json.dumps({"text_lines": [{"line_id": "T01-L01", "text": "测试"}]}), encoding="utf-8")
        (output_dir / "qa.json").write_text(json.dumps({"status": "review"}), encoding="utf-8")
        (output_dir / "slide-1.png").write_bytes(b"render")
        return type("Completed", (), {"returncode": 0})()

    monkeypatch.setattr("cyberppt.commands.editable_text_three_image.subprocess.run", fake_vendor_run)
    result = run_three_image_batch(project, "4")
    assert result["status"] == "review_required"
    with pytest.raises(ValueError, match="editable-text review approval"):
        assert_editable_text_batch_ready(project, "4")


def test_failed_page_preserves_other_results(tmp_path: Path, monkeypatch) -> None:
    project = tmp_path / "project"
    init_project(project)
    _write_complete_pairs(project, [4, 5])

    def fake_vendor_run(command, check=False, **kwargs):
        payload = json.loads(Path(command[-1]).read_text(encoding="utf-8"))
        for job in payload["pages"]:
            output_dir = Path(job["output_dir"])
            output_dir.mkdir(parents=True, exist_ok=True)
            status = "failed" if job["page_number"] == 4 else "passed"
            (output_dir / "qa.json").write_text(json.dumps({"status": status}), encoding="utf-8")
            if status == "passed":
                (output_dir / "page.json").write_text(json.dumps({"text_lines": [{"line_id": "T01-L01", "text": "测试"}]}), encoding="utf-8")
                (output_dir / "slide-1.png").write_bytes(b"render")
        return type("Completed", (), {"returncode": 1})()

    monkeypatch.setattr("cyberppt.commands.editable_text_three_image.subprocess.run", fake_vendor_run)
    pages = run_three_image_batch(project, "4-5")["pages"]
    assert pages["4"]["status"] == "failed"
    assert pages["5"]["status"] == "passed"
