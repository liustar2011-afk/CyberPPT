from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from scripts.dual_image_overlay.source_capture import build_source_capture


class DualImageOverlaySourceCaptureTests(unittest.TestCase):
    def test_builds_unified_capture_from_existing_rebuild_artifacts(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project_dir = Path(tmp)
            _write_artifacts(project_dir)

            capture = build_source_capture(project_dir)

        self.assertEqual(capture["schema"], "cyberppt.dual_image.source_capture.v1")
        self.assertEqual(capture["inputs"]["ocr_text_mappings"], 2)
        self.assertEqual(capture["capture_policy"]["text_wrap_before_shrink"], True)
        self.assertEqual(len(capture["pages"]), 1)

        page = capture["pages"][0]
        self.assertEqual(page["page_number"], 2)
        self.assertEqual(page["source_images"]["full"]["filename"], "page_002_full.png")
        self.assertEqual(page["image_regions"]["generation_contract"]["brand_body_region"]["x"], 58)
        self.assertEqual(page["containers"][0]["id"], "so_what_band")

        text_objects = page["text_objects"]
        self.assertEqual(text_objects[0]["style"]["typography_role"], "T8")
        self.assertEqual(text_objects[0]["rendered_text"], "建议按规则先行路径\n启动首阶段工作")
        self.assertTrue(text_objects[0]["layout"]["needs_wrapping"])
        self.assertEqual(text_objects[1]["source"]["kind"], "script_matched")

        inventory = page["visual_element_inventory"]
        self.assertTrue(any(item["element_id"] == "so_what_band" and item["element_type"] == "container" for item in inventory))
        self.assertTrue(any(item["element_id"] == "text_001" and item["priority"] == "P0" for item in inventory))
        self.assertTrue(any(gap["code"] == "render_delta_not_measured" for gap in page["capture_gaps"]))

        rules = page["layout_rules"]
        self.assertTrue(rules["avoidance_policy"]["text_should_wrap_before_shrink"])
        self.assertEqual(rules["baseline_groups"][0]["candidate_y"], 621.45)


def _write_artifacts(project_dir: Path) -> None:
    (project_dir / "images").mkdir(parents=True)
    (project_dir / "analysis" / "ocr").mkdir(parents=True)
    (project_dir / "analysis" / "semantic_containers").mkdir(parents=True)
    (project_dir / "analysis" / "typography").mkdir(parents=True)
    (project_dir / "svg_output").mkdir(parents=True)

    _write_json(
        project_dir / "images" / "page_image_pairs.json",
        {
            "generation_contract": {
                "slide_canvas": {"width": 1280, "height": 720},
                "brand_body_region": {"x": 58, "y": 122, "width": 1164, "height": 554},
            },
            "pairs": [
                {
                    "page_number": 2,
                    "full": {"filename": "page_002_full.png", "path": "/tmp/page_002_full.png", "status": "ready"},
                    "background": {
                        "filename": "page_002_background.png",
                        "path": "/tmp/page_002_background.png",
                        "status": "ready",
                    },
                }
            ],
        },
    )
    _write_json(
        project_dir / "analysis" / "ocr" / "page_002_text_mapping.json",
        {
            "page_number": 2,
            "boxes": [
                _box("建议按规则先行路径启动首阶段工作", 166, 604, 460, 22, "ocr_unmatched"),
                _box("规则先行", 720, 621, 72, 22, "script_matched"),
            ],
        },
    )
    _write_json(
        project_dir / "analysis" / "semantic_containers" / "page_002_containers.json",
        {
            "page_number": 2,
            "containers": [
                {
                    "id": "so_what_band",
                    "role": "foundation_base",
                    "x": 58,
                    "y": 582,
                    "w": 1164,
                    "h": 91,
                    "background": "dark",
                    "fill": "#FFFFFF",
                }
            ],
        },
    )
    _write_json(
        project_dir / "analysis" / "typography" / "page_002_cyberppt_typography.json",
        {
            "decisions": [
                {
                    "text": "建议按规则先行路径启动首阶段工作",
                    "rendered_text": "建议按规则先行路径\n启动首阶段工作",
                    "role": "T8",
                    "applied_px": 16,
                },
                {"text": "规则先行", "rendered_text": "规则先行", "role": "T6", "applied_px": 14.67},
            ]
        },
    )
    _write_json(
        project_dir / "analysis" / "candidate_layout_rules.json",
        {
            "line_break": {
                "phrase_breaks": [
                    {
                        "compact_text": "建议按规则先行路径启动首阶段工作",
                        "break_text": "建议按规则先行路径\n启动首阶段工作",
                        "support": 1,
                    }
                ]
            },
            "baseline_groups": [
                {"page_number": 2, "candidate_y": 621.45, "labels": ["建议", "规则先行"], "support": 2}
            ],
            "alignment_issues": [],
        },
    )
    (project_dir / "svg_output" / "page_002.svg").write_text(
        '<svg><text x="166" y="616" font-size="16">建议按规则先行路径启动首阶段工作</text></svg>',
        encoding="utf-8",
    )


def _box(text: str, x: float, y: float, w: float, h: float, source: str) -> dict[str, object]:
    return {
        "text": text,
        "x": x,
        "y": y,
        "w": w,
        "h": h,
        "font_size": 14,
        "font_family": "Microsoft YaHei",
        "fill": "#FFFFFF",
        "font_weight": "700",
        "align": "center",
        "word_wrap": True,
        "source": source,
        "confidence": 0.96,
    }


def _write_json(path: Path, payload: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    unittest.main()
