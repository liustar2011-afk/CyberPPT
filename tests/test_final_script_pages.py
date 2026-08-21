from __future__ import annotations

import json
import hashlib
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

from cyberppt.commands.final_script_pages import (
    BODY_IMAGE_CANVAS_CONTRACT,
    _generate_manifest_images,
    _page_range_slug,
    _seed_verified_stage02_assets,
    run_final_script_pages,
)
from cyberppt.commands.init_project import init_project
from cyberppt.commands.visual_structure_stage import (
    VISUAL_FILES,
    _prompt_inputs_sha256,
    _sha256,
    _skill_root,
)
from cyberppt.commands.script_gate import stage_script
from scripts.imagegen_pipeline.deliverable_prompt import parse_page_blocks, render_prompt
from scripts.imagegen_pipeline.imagegen_handoff import build_page_prompt
from cyberppt.script_quality_contract import parse_script_markdown
from cyberppt.semantic_digest import outline_semantic_digest, source_truth_semantic_digest
from cyberppt.onscreen_expression import expression_constraints
from scripts.imagegen_pipeline.style_library import write_project_style_lock


class FinalScriptPagesTests(unittest.TestCase):
    def test_seeded_stage02_assets_copy_without_resizing(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source_image = root / "source.png"
            source_clean = root / "source-clean.png"
            source_image.write_bytes(b"source-image")
            source_clean.write_bytes(b"clean-base")
            seed_path = root / "seed.json"
            seed_path.write_text(
                json.dumps(
                    {
                        "source_script_sha256": "script-hash",
                        "pairs": [
                            {
                                "page_number": 1,
                                "full": {"path": str(source_image), "text_audit": {"valid": True}},
                                "clean_base": {"status": "complete", "path": str(source_clean)},
                            }
                        ],
                    }
                ),
                encoding="utf-8",
            )
            target = root / "new-build"
            manifest = {
                "source_script_sha256": "script-hash",
                "pairs": [{"page_number": 1, "full": {"path": str(target / "page_001_full.png")}}],
            }

            report = _seed_verified_stage02_assets(
                manifest,
                seed_manifest_path=seed_path,
                output_dir=target,
            )

            pair = manifest["pairs"][0]
            self.assertEqual(b"source-image", Path(pair["full"]["path"]).read_bytes())
            self.assertEqual(b"clean-base", Path(pair["clean_base"]["path"]).read_bytes())
            self.assertTrue(pair["clean_base"]["baseline_seed"])
            self.assertEqual("seed.json", Path(pair["clean_base"]["baseline_provenance"]["seed_manifest"]).name)
            self.assertNotIn("graphic_text_policy", pair)
            self.assertEqual([1], [item["page_number"] for item in report["pages"]])

    def test_long_discontinuous_page_set_uses_windows_safe_slug(self) -> None:
        pages = [4, 5, 6, 7, 8, 10, 11, 12, 13, 14, 15, 16, 18, 19, 20, 21, 22, 23, 25, 26, 27]
        slug = _page_range_slug(pages)
        self.assertLessEqual(len(slug), 80)
        self.assertTrue(slug.startswith("pages_004_027_21p_"))
        self.assertEqual(slug, _page_range_slug(pages))

    def test_semantic_only_judgment_moves_to_subtitle_not_body_prompt(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            project = root / "client-report"
            init_project(project)
            script = root / "script-final.md"
            judgment = "30个电力学科、约30万条题目和40年行业数据构成核心资产基础"
            subtitle = "30个学科、30万道题目、40年数据，夯实智能应用底座"
            script.write_text(
                f"""## 第4页：知识资产基础
- 页面类型：内容页
- 页面标题：知识资产基础
- 副标题：{subtitle}
- 主判断：{judgment}
- 上屏结论模式：semantic_only
- 上屏结论：{judgment}
- 上屏文字：

  **01｜30个电力学科**
  - 覆盖专业知识与规范
""",
                encoding="utf-8",
            )
            page = parse_script_markdown(script.read_text(encoding="utf-8")).pages[0]
            style_lock = write_project_style_lock(
                project=project,
                style_id=9,
                source_script=script,
            )
            prompt = build_page_prompt(page, style_lock)

        body = prompt.split("【完整上屏内容】", 1)[1].split(
            "【核心意思表达要求", 1
        )[0]
        self.assertNotIn(judgment, body)
        self.assertNotIn(subtitle, body)
        self.assertIn("01｜30个电力学科", body)

    def test_subtitle_migration_preserves_existing_body_copy(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            project = root / "client-report"
            init_project(project)
            script = root / "script-final.md"
            judgment = "三类知识资产共同构成智能应用基础"
            original_body = (
                "**01｜30个电力学科**\n"
                "  - 原有说明文字保持不变\n"
                "  **02｜约30万条题目**\n"
                "  - 原有证据关系保持不变\n"
                "  **03｜40年行业数据**"
            )
            script.write_text(
                f"""## 第4页：知识资产基础
- 页面类型：内容页
- 页面标题：知识资产基础
- 副标题：三类知识资产夯实智能应用底座
- 主判断：{judgment}
- 上屏结论模式：semantic_only
- 上屏结论：{judgment}
- 上屏文字：

  {original_body}
""",
                encoding="utf-8",
            )
            page = parse_script_markdown(script.read_text(encoding="utf-8")).pages[0]
            style_lock = write_project_style_lock(
                project=project,
                style_id=9,
                source_script=script,
            )
            prompt = build_page_prompt(page, style_lock)

        body = prompt.split("【完整上屏内容】", 1)[1].split(
            "【核心意思表达要求", 1
        )[0]
        normalized_original = "\n".join(
            line.strip() for line in original_body.splitlines()
        )
        normalized_body = "\n".join(
            line.strip() for line in body.strip().splitlines()
        )
        self.assertEqual(normalized_original, normalized_body)
        self.assertNotIn(judgment, body)

    def test_full_image_payload_forces_body_region_two_to_one_canvas(self) -> None:
        manifest = {
            "production_mode": "image-to-editable-svg",
            "pairs": [
                {
                    "page_number": 4,
                    "full": {
                        "path": "page-004.png",
                        "prompt": "页面正文提示词",
                        "canvas": "2048x1024",
                    },
                }
            ],
        }
        with patch("cyberppt.commands.final_script_pages.run_codex_image") as generate:
            _generate_manifest_images(
                manifest,
                full_reference_images=[Path("palette-09.png")],
                model="gpt-image-2",
                quality="high",
                timeout=600,
                force=False,
                dry_run=True,
            )

        kwargs = generate.call_args.kwargs
        self.assertEqual("页面正文提示词", kwargs["prompt"])
        self.assertEqual("2048x1024", kwargs["size"])
        self.assertEqual([Path("palette-09.png")], kwargs["image_paths"])
        self.assertFalse(kwargs["postprocess"])

    def test_transient_network_fault_on_one_page_does_not_abort_the_batch(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            output_4 = Path(tmp) / "page-004.png"
            output_5 = Path(tmp) / "page-005.png"
            manifest = {
                "production_mode": "image-to-editable-svg",
                "pairs": [
                    {
                        "page_number": 4,
                        "full": {"path": str(output_4), "prompt": "p4", "canvas": "2048x1024"},
                    },
                    {
                        "page_number": 5,
                        "full": {"path": str(output_5), "prompt": "p5", "canvas": "2048x1024"},
                    },
                ],
            }

            def generate_image(**kwargs: object) -> None:
                output_path = Path(str(kwargs["output_path"]))
                if output_path == output_4:
                    raise BrokenPipeError(32, "Broken pipe")
                output_path.write_bytes(b"generated")

            with (
                patch(
                    "cyberppt.commands.final_script_pages.run_codex_image",
                    side_effect=generate_image,
                ),
                patch("cyberppt.commands.final_script_pages.ensure_output_size"),
            ):
                summary = _generate_manifest_images(
                    manifest,
                    model="gpt-image-2",
                    quality="high",
                    timeout=600,
                    force=True,
                    dry_run=False,
                )

            self.assertEqual([str(output_5)], summary["generated"])
            self.assertEqual(1, len(summary["failed"]))
            self.assertEqual(4, summary["failed"][0]["page_number"])
            self.assertIn("Broken pipe", summary["failed"][0]["error"])
            self.assertEqual("Failed", manifest["pairs"][0]["full"]["status"])
            self.assertIn("Broken pipe", manifest["pairs"][0]["full"]["last_error"])
            self.assertEqual("Generated", manifest["pairs"][1]["full"]["status"])
            self.assertNotIn("last_error", manifest["pairs"][1]["full"])

    def test_typo_audit_regenerates_before_enhancement(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / "page-004.png"
            reference = Path(tmp) / "palette-09.png"
            reference.write_bytes(b"reference")
            manifest = {
                "production_mode": "image-to-editable-svg",
                "pairs": [
                    {
                        "page_number": 4,
                        "reference_images": [{"path": str(reference)}],
                        "image_text_truth": {
                            "script_text": "数据产品\n数据服务",
                            "scope": "typo_and_gibberish_only",
                        },
                        "full": {
                            "path": str(output),
                            "prompt": "prompt",
                            "canvas": "2048x1024",
                        },
                    }
                ],
            }
            failed = {
                "valid": False,
                "issues": [
                    {
                        "type": "typo",
                        "expected": "数据服务",
                        "observed": "数据服努",
                        "bbox": [10, 20, 30, 40],
                    }
                ],
            }
            passed = {"valid": True, "issues": []}

            def generate_image(**kwargs: object) -> None:
                Path(str(kwargs["output_path"])).write_bytes(b"generated")

            with (
                patch(
                    "cyberppt.commands.final_script_pages.run_codex_image",
                    side_effect=generate_image,
                ) as generate,
                patch(
                    "cyberppt.image_text_gate.audit_generated_image_text",
                    side_effect=[failed, passed],
                ),
                patch("cyberppt.commands.final_script_pages.ensure_output_size") as enhance,
            ):
                summary = _generate_manifest_images(
                    manifest,
                    model="gpt-image-2",
                    quality="high",
                    timeout=600,
                    force=True,
                    dry_run=False,
                )

            failed_image = Path(tmp) / "page-004.attempt-01-text-audit-failed.png"
            self.assertEqual(2, generate.call_count)
            first_call, second_call = generate.call_args_list
            self.assertEqual([reference], first_call.kwargs["image_paths"])
            self.assertEqual([failed_image, reference], second_call.kwargs["image_paths"])
            self.assertIn("第一张输入图片是上一轮生成", second_call.kwargs["prompt"])
            self.assertIn('"expected": "数据服务"', second_call.kwargs["prompt"])
            self.assertIn('"observed": "数据服努"', second_call.kwargs["prompt"])
            attempt_records = summary["imagegen_attempts"]
            self.assertEqual(2, len(attempt_records))
            first_sent = Path(attempt_records[0]["prompt_path"])
            second_sent = Path(attempt_records[1]["prompt_path"])
            second_record = json.loads(
                Path(attempt_records[1]["request_record_path"]).read_text(encoding="utf-8")
            )
            self.assertEqual(first_call.kwargs["prompt"], first_sent.read_text(encoding="utf-8"))
            self.assertEqual(second_call.kwargs["prompt"], second_sent.read_text(encoding="utf-8"))
            self.assertEqual(
                second_call.kwargs["prompt"].encode("utf-8"),
                second_sent.read_bytes(),
            )
            self.assertTrue(second_record["correction_retry"])
            self.assertEqual(failed["issues"], second_record["correction_issues"])
            self.assertEqual("gpt-image-2", second_record["model"])
            self.assertEqual("high", second_record["quality"])
            self.assertEqual("2048x1024", second_record["size"])
            self.assertEqual(
                first_call.kwargs["prompt"], second_record["original_prompt"]
            )
            self.assertEqual(str(failed_image), second_record["failed_image"])
            self.assertEqual(
                second_record["prompt_sha256"],
                hashlib.sha256(
                    second_sent.read_text(encoding="utf-8").encode("utf-8")
                ).hexdigest(),
            )
            self.assertEqual(
                [str(failed_image.resolve()), str(reference.resolve())],
                second_record["input_images"],
            )
            self.assertTrue(failed_image.is_file())
            self.assertEqual(str(failed_image), summary["text_audits"][0]["image"])
            enhance.assert_called_once_with(output, "2048x1024")
            self.assertTrue(manifest["pairs"][0]["full"]["text_audit"]["valid"])
            self.assertEqual(2, len(summary["text_audits"]))

    def test_skip_text_audit_generates_once_without_ocr_or_correction_retry(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / "page-004.png"
            manifest = {
                "production_mode": "image-to-editable-svg",
                "pairs": [
                    {
                        "page_number": 4,
                        "image_text_truth": {"script_text": "数据产品"},
                        "full": {
                            "path": str(output),
                            "prompt": "prompt",
                            "canvas": "2048x1024",
                        },
                    }
                ],
            }

            def generate_image(**kwargs: object) -> None:
                Path(str(kwargs["output_path"])).write_bytes(b"generated")

            with (
                patch(
                    "cyberppt.commands.final_script_pages.run_codex_image",
                    side_effect=generate_image,
                ) as generate,
                patch("cyberppt.image_text_gate.audit_generated_image_text") as audit,
                patch("cyberppt.commands.final_script_pages.ensure_output_size") as enhance,
            ):
                summary = _generate_manifest_images(
                    manifest,
                    model="gpt-image-2",
                    quality="high",
                    timeout=600,
                    force=True,
                    dry_run=False,
                    skip_text_audit=True,
                )

            generate.assert_called_once()
            audit.assert_not_called()
            enhance.assert_called_once_with(output, "2048x1024")
            self.assertTrue(summary["text_audit_skipped"])
            self.assertEqual([], summary["text_audits"])
            self.assertNotIn("text_audit", manifest["pairs"][0]["full"])
            self.assertEqual(
                {
                    "required_before_enhancement": False,
                    "scope": "disabled_for_visual_composition_test",
                    "max_generation_attempts": 1,
                    "failure_action": "not_applicable",
                },
                manifest["text_audit_contract"],
            )

    def _approve_inputs_and_prompts(self, project: Path, script: Path, style_id: int = 4) -> None:
        manifest = project / "manifest.yml"
        manifest.write_text(
            manifest.read_text(encoding="utf-8").replace(
                "semantic_understanding: required",
                "semantic_understanding: optional",
            ).replace(
                "communication_strategy: required",
                "communication_strategy: optional",
            ),
            encoding="utf-8",
        )
        analysis = project / "workbench" / "stages" / "01-analysis"
        outline = analysis / "outline.json"
        source_truth = analysis / "source-truth.json"
        outline.write_text("{}\n", encoding="utf-8")
        source_truth.write_text("{}\n", encoding="utf-8")
        audit = project / "workbench" / "scripts" / "audits" / "script-audit.json"
        audit.parent.mkdir(parents=True, exist_ok=True)
        audit.write_text(
            json.dumps(
                {
                    "status": "passed",
                    "input": str(script.resolve()),
                    "outline": str(outline.resolve()),
                    "source_truth": str(source_truth.resolve()),
                }
            ),
            encoding="utf-8",
        )
        review_input = project / "workbench" / "scripts" / "audits" / "chapter-review-input.json"
        review_input.write_text(
            json.dumps(
                {
                    "schema": "cyberppt.chapter_review_input.v1",
                    "level": "script",
                    "input_path": str(script.resolve()),
                },
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )
        chapter_review = project / "workbench" / "scripts" / "audits" / "chapter-review-audit.json"
        chapter_review.write_text(
            json.dumps(
                {
                    "schema": "cyberppt.chapter_review_audit.v1",
                    "status": "passed",
                    "input": str(review_input.resolve()),
                    "input_sha256": hashlib.sha256(review_input.read_bytes()).hexdigest(),
                },
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )
        visual_dir = project / "visual"
        visual_dir.mkdir(parents=True, exist_ok=True)
        spec_json = visual_dir / "deck-visual-spec.json"
        spec_md = visual_dir / "script-visual-structure.md"
        review_summary = visual_dir / "visual-review-summary.md"
        generation_prompts = visual_dir / "generation-prompts.md"
        spec_json.write_text(json.dumps({"schema": "cyberppt.visual_spec.v1"}), encoding="utf-8")
        spec_md.write_text("# visual structure\n", encoding="utf-8")
        review_summary.write_text("# visual review summary\n", encoding="utf-8")
        prompt_pages = []
        for page_number in range(1, 31):
            prompt_pages.append(
                "\n".join(
                    [
                        f"# Page {page_number}: fixture",
                        "[Mandatory composition guidance] Apply this layout guidance before placing any on-screen text. Do not render its field names or instruction text.",
                        "Use the approved page relationship.",
                        "[Connector map]",
                        "Keep the main relation clear.",
                        "[Text rendering]",
                        "Render locked text verbatim.",
                        "[Style]",
                        "Use the project style lock.",
                        "[Negative constraints]",
                        "Do not add slide chrome.",
                        "---",
                    ]
                )
            )
        generation_prompts.write_text("\n".join(prompt_pages) + "\n", encoding="utf-8")
        fixture_pages = sorted(parse_page_blocks(script))
        spec_json.write_text(
            json.dumps(
                {
                    "pages": [
                        {
                            "page_id": f"P{page_number:02d}",
                            "page_number": page_number,
                            "page_role": "evidence",
                            "page_mission": "Fixture mission",
                            "core_judgment": "Fixture message",
                            "content_lock": {
                                "locked_items": [
                                    {
                                        "id": f"P{page_number:02d}-T01",
                                        "type": "body",
                                        "text": "Fixture text",
                                    }
                                ],
                                "allowed_transformations": ["line_break", "grouping"],
                                "forbidden_transformations": ["change facts"],
                            },
                            "evidence_units": [
                                {
                                    "id": "E1",
                                    "text": "Fixture evidence",
                                    "kind": "evidence",
                                    "priority": "P0",
                                }
                            ],
                            "semantic_graph": {
                                "topology": "directed_flow",
                                "decision_relationship": "Fixture evidence supports fixture result"
                            },
                            "visual_decision": {
                                "visual_thesis": "Fixture relationship",
                                "spatial_organization": "Fixture spatial organization",
                                "reading_path": ["Fixture evidence", "Fixture result"],
                                "relationship_encoding": "Fixture relation",
                                "text_integration_method": "Attach locked text to its object",
                                "visual_hierarchy": {
                                    "primary": "Fixture focus",
                                    "secondary": ["Fixture evidence"],
                                },
                            },
                            "image_plan": {
                                "business_object": "Fixture business object",
                                "semantic_role": "Fixture semantic role",
                                "use_scene": False,
                                "scene_type": "Fixture relationship field",
                            },
                            "structural_decision": {"spatial_grammar": ["fixture"]},
                            "text_integration": {
                                "title_render_mode": "external_text_layer",
                                "subtitle_render_mode": "external_text_layer",
                                "body_render_mode": "in_image",
                            },
                            "geometry": {
                                "canvas": {"width": 2048, "height": 1024, "ratio": "2:1"}
                            },
                            "final_text": [
                                {"id": f"P{page_number:02d}-T01", "text": "Fixture text"}
                            ],
                            "generation_handoff": {
                                "required_text": ["Fixture text"],
                                "title_exclusion_instruction": "Do not render title or subtitle.",
                            },
                            "avoid": ["Do not add slide chrome"],
                        }
                        for page_number in fixture_pages
                    ]
                },
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )
        handoff = project / "workbench" / "stages" / "02-handoff" / "stage02-handoff.json"
        handoff.parent.mkdir(parents=True, exist_ok=True)
        handoff.write_text(
            json.dumps(
                {
                    "schema": "cyberppt.stage02_handoff.v1",
                    "source_bindings": {
                        "script": {
                            "path": str(script.resolve()),
                            "sha256": hashlib.sha256(script.read_bytes()).hexdigest(),
                            "semantic_sha256": hashlib.sha256(script.read_bytes()).hexdigest(),
                        },
                        "outline": {
                            "path": str(outline.resolve()),
                            "sha256": hashlib.sha256(outline.read_bytes()).hexdigest(),
                            "semantic_sha256": outline_semantic_digest(outline),
                        },
                        "source_truth": {
                            "path": str(source_truth.resolve()),
                            "sha256": hashlib.sha256(source_truth.read_bytes()).hexdigest(),
                            "semantic_sha256": source_truth_semantic_digest(source_truth),
                        },
                    },
                    "pages": [
                        {
                            "page_id": f"p{page_number:02d}",
                            "page_number": page_number,
                            "render_role": "content",
                            "title": f"Page {page_number}",
                            "page_mission": "Fixture mission",
                            "core_message": "Fixture message",
                            "onscreen_text": "Fixture text",
                            "onscreen_items": ["Fixture text"],
                            "onscreen_expression": {
                                "form": "key_points_3",
                                "source": "fallback",
                                "confidence": 0.2,
                                "evidence": ["fixture"],
                                "candidates": [["key_points_3", 0.2]],
                            },
                            "expression_constraints": expression_constraints("key_points_3"),
                            "stage02_visual_input": {
                                "locked_text_items": [
                                    {
                                        "text_id": f"P{page_number:02d}-T01",
                                        "text": "Fixture text",
                                        "ordinal": 1,
                                    }
                                ],
                                "business_relationships": [],
                                "stage01_relationship_features": {
                                    "authority": "stage01_semantic_handoff",
                                    "actors": ["Fixture"],
                                    "actions": [
                                        {
                                            "subject": "Fixture",
                                            "relation": "supports",
                                            "object": "Fixture result",
                                        }
                                    ],
                                    "directions": [],
                                    "conditions": [],
                                    "branches": [],
                                    "feedback": [],
                                    "source_visual_notes": "",
                                },
                                "author_visual_notes_authority": "advisory_only",
                                "expression_constraints": expression_constraints("key_points_3"),
                                "body_image_canvas": {"width": 2048, "height": 1024, "ratio": "2:1"},
                                "title_render_mode": "external_text_layer",
                                "subtitle_render_mode": "external_text_layer",
                            },
                        }
                        for page_number in fixture_pages
                    ],
                },
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )
        extra_visual_artifacts = {
            key: project / VISUAL_FILES[key]
            for key in ("design_input", "skill_request", "decisions", "execution_receipt")
        }
        for key, path in extra_visual_artifacts.items():
            path.write_text(key + "\n", encoding="utf-8")
        visual_artifacts = {
            **extra_visual_artifacts,
            "spec_json": spec_json,
            "spec_markdown": spec_md,
            "review_summary": review_summary,
            "generation_prompts": generation_prompts,
        }
        visual_report = visual_dir / "validation-report.json"
        visual_report.write_text(
            json.dumps(
                {
                    "schema": "cyberppt.visual_structure_stage.v2",
                    "status": "passed",
                    "artifact_sha256": {
                        key: _sha256(path) for key, path in visual_artifacts.items()
                    },
                    "prompt_inputs_sha256": _prompt_inputs_sha256(
                        project, script, _skill_root()
                    ),
                },
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )
        audit_patcher = patch(
            "cyberppt.commands.script_audit.run_script_audit",
            return_value=(0, {"status": "passed"}),
        )
        audit_patcher.start()
        self.addCleanup(audit_patcher.stop)
        handoff_digest_patcher = patch(
            "cyberppt.stage02_handoff.script_semantic_digest",
            side_effect=lambda path: hashlib.sha256(path.read_bytes()).hexdigest(),
        )
        handoff_digest_patcher.start()
        self.addCleanup(handoff_digest_patcher.stop)
        style_lock = write_project_style_lock(project=project, style_id=style_id, source_script=script)
        script_pages = {
            int(page.page_id[1:]): page
            for page in parse_script_markdown(script.read_text(encoding="utf-8")).pages
        }
        from cyberppt.page_artifact_spec import load_project_page_artifact_specs
        from scripts.imagegen_pipeline.imagegen_handoff import compile_page_prompt

        artifact_specs = load_project_page_artifact_specs(project, style_lock=style_lock)
        for page_number in parse_page_blocks(script):
            prompt = project / f"prompt-{page_number}.md"
            prompt.write_text(
                compile_page_prompt(
                    script_pages[page_number],
                    style_lock,
                    prompt_compiler="artifact-spec-v2",
                    artifact_spec=artifact_specs[page_number],
                ).prompt,
                encoding="utf-8",
            )
            stage_script(project, page_number, "imagegen", "final", prompt)
        for page_number in parse_page_blocks(script):
            from cyberppt.commands.script_gate import approve_script

            approve_script(project, page_number, "imagegen", note="test")

    def test_compiles_pages_7_8_from_final_script_with_traceable_artifacts(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            project = root / "client-report"
            init_project(project)
            script = root / "script-final.md"
            script.write_text(
                """# 终稿脚本

## 第7页：态势感知能力
本页结论标题为“态势感知能力要从工具堆叠转向风险闭环”
组件A（左侧主图）——三层能力链：
数据接入、模型研判、处置反馈

## 第8页：运营保障机制
本页结论标题为“运营保障机制需要责任、流程和审计同时落地”
组件A（中部流程）——责任闭环：
授权、执行、复盘、追踪
""",
                encoding="utf-8",
            )
            self._approve_inputs_and_prompts(project, script)

            summary = run_final_script_pages(
                project=project,
                script=script,
                pages_raw="7-8",
                style_id=4,
            )

            manifest = json.loads(Path(summary["artifacts"]["page_image_pairs"]).read_text(encoding="utf-8"))
            lock = json.loads(Path(summary["artifacts"]["template_text_lock"]).read_text(encoding="utf-8"))
            visual_lock = json.loads(Path(summary["artifacts"]["visual_style_lock"]).read_text(encoding="utf-8"))
            build_context = json.loads(Path(summary["artifacts"]["build_context"]).read_text(encoding="utf-8"))
            prompt = Path(summary["artifacts"]["compiled_deliverable_prompt"]).read_text(encoding="utf-8")
            ledger = json.loads((project / "workbench/artifact-ledger.json").read_text(encoding="utf-8"))

            self.assertEqual([7, 8], summary["pages"])
            self.assertEqual(summary["build_id"], build_context["build_id"])
            self.assertEqual([7, 8], build_context["page_set"])
            self.assertEqual(summary["source_script_sha256"], build_context["source_script_sha256"])
            self.assertIn("page_image_pairs", build_context["artifacts"])
            self.assertEqual([7, 8], [pair["page_number"] for pair in manifest["pairs"]])
            self.assertEqual(4, visual_lock["style"]["id"])
            self.assertEqual(manifest["style_lock"], summary["artifacts"]["visual_style_lock"])
            self.assertIn("#12355B", prompt)
            self.assertNotIn("【完整内容语义｜仅供理解，不要求逐字上屏】", prompt)
            self.assertNotIn("【页面逻辑｜不上屏】", prompt)
            self.assertIn("[1. Deliverable]", prompt)
            self.assertIn("[6. Exact visible text contract]", prompt)
            self.assertIn("[7. Runtime lock]", prompt)
            self.assertIn("Do not render title, subtitle, logo, page number, footer, or template frame.", prompt)
            self.assertEqual("artifact-spec-v2", manifest["prompt_contract"]["compiler"])
            self.assertEqual("态势感知能力要从工具堆叠转向风险闭环", lock["records"][0]["title"])
            self.assertEqual("运营保障机制需要责任、流程和审计同时落地", lock["records"][1]["title"])
            self.assertIn("presentation", lock["records"][0])
            self.assertIn("editable_body_text", lock["records"][0])
            self.assertTrue(Path(summary["artifacts"]["compiled_deliverable_prompt"]).exists())
            self.assertTrue(Path(summary["artifacts"]["page_image_pairs"]).exists())
            self.assertTrue(Path(summary["artifacts"]["template_text_lock"]).exists())
            self.assertIn("--pages 7-8", summary["resume_command"])
            self.assertIn("--style-lock", summary["resume_command"])
            ledger_paths = {item["path"] for item in ledger["artifacts"]}
            self.assertIn(summary["artifacts"]["page_image_pairs"], ledger_paths)
            self.assertIn(summary["artifacts"]["template_text_lock"], ledger_paths)
            self.assertIn(summary["artifacts"]["visual_style_lock"], ledger_paths)

    def test_external_script_requires_formal_stage02_gates(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            project = root / "stage2-only"
            init_project(project)
            script = root / "vendor-script.md"
            script.write_text(
                "## P01 外部脚本页面\n"
                "本页结论：外部脚本可以直接进入 Stage 02。\n"
                "组件A：输入与输出关系\n",
                encoding="utf-8",
            )

            with patch(
                "cyberppt.commands.script_audit.run_script_audit",
                return_value=(0, {"status": "passed"}),
            ):
                with self.assertRaisesRegex(FileNotFoundError, "Stage 02 handoff"):
                    run_final_script_pages(
                        project=project,
                        script=script,
                        pages_raw="1",
                        style_id=4,
                        external_script=True,
                    )

            self._approve_inputs_and_prompts(project, script)

            summary = run_final_script_pages(
                project=project,
                script=script,
                pages_raw="1",
                style_id=4,
                external_script=True,
            )

            manifest = json.loads(Path(summary["artifacts"]["page_image_pairs"]).read_text(encoding="utf-8"))
            context = json.loads(Path(summary["artifacts"]["build_context"]).read_text(encoding="utf-8"))

        self.assertEqual("external_script", summary["source_mode"])
        self.assertFalse(summary["project_created"])
        self.assertEqual("external_script", context["source_mode"])
        self.assertFalse(context["project_created"])
        self.assertEqual("stage2-only", Path(summary["project"]).name)
        self.assertEqual("external_script", manifest["source_mode"])
        self.assertEqual(summary["source_script_sha256"], manifest["source_script_sha256"])
        self.assertTrue(manifest["prompt_contract"]["approved_prompt_is_source"])
        self.assertTrue(summary["artifacts"]["compiled_deliverable_prompt"].endswith(".md"))
        self.assertNotIn("--external-script", summary["resume_command"])

    def test_uses_configured_default_style_without_explicit_style_lock(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            project = root / "client-report"
            init_project(project)
            script = root / "script-final.md"
            script.write_text("## 第7页：态势感知能力\n组件A：内容\n", encoding="utf-8")
            # Approve with the project's configured default style (10) so the
            # prompt approved here matches what the unqualified build below
            # actually resolves and validates against.
            self._approve_inputs_and_prompts(project, script, style_id=10)

            run_final_script_pages(
                project=project,
                script=script,
                pages_raw="7",
                lightweight_stage01_confirmed=True,
            )

            style_lock = json.loads(
                (project / "workbench/locks/visual_style_lock.json").read_text(
                    encoding="utf-8"
                )
            )
            self.assertEqual(10, style_lock["style"]["id"])

    def test_rejects_markdown_style_lock_with_actionable_message(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            project = root / "client-report"
            init_project(project)
            script = root / "script-final.md"
            script.write_text("## 第1页：测试\n正文\n", encoding="utf-8")
            style_lock = root / "style-lock.md"
            style_lock.write_text("# 风格确认稿\n", encoding="utf-8")
            self._approve_inputs_and_prompts(project, script)

            with self.assertRaisesRegex(
                ValueError,
                r"--style-lock must point to a valid JSON visual style lock.*--style-id/--style-name",
            ):
                run_final_script_pages(
                    project=project,
                    script=script,
                    pages_raw="1",
                    style_lock=style_lock,
                    lightweight_stage01_confirmed=True,
                )

    def test_production_build_runs_image_to_editable_svg_export(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            project = root / "client-report"
            init_project(project)
            script = root / "script-final.md"
            script.write_text("## 第1页：测试\n正文\n", encoding="utf-8")
            self._approve_inputs_and_prompts(project, script)

            expected = {
                "status": "production_ready",
                "artifacts": {"reconstruction_inventory": "inventory", "svg_output": "svg", "reconstruction_quality": "quality", "delivery_readiness": "readiness", "exported_pptx": "deck.pptx"},
                "delivery_readiness": {"tool_consumption": {}},
            }
            with (
                patch("cyberppt.commands.final_script_pages.require_generated"),
                patch(
                    "cyberppt.commands.final_script_pages.prepare_ai_graphic_text_policy",
                    return_value={"status": "complete", "path": "ai-native-text-policy.json"},
                ) as ai_policy,
                patch(
                    "cyberppt.commands.final_script_pages.prepare_clean_bases",
                    return_value={"status": "complete", "path": "clean-base-generation.json", "pages": []},
                ) as clean_bases,
                patch(
                    "cyberppt.commands.final_script_pages.prepare_ai_authored_svgs",
                    return_value={"status": "complete", "path": "ai-authored-svg.json"},
                ) as ai_svg,
                patch("cyberppt.commands.final_script_pages._run_image_to_editable_svg_build", return_value=expected) as build,
            ):
                summary = run_final_script_pages(
                    project=project,
                    script=script,
                    pages_raw="1",
                    style_id=4,
                    production_build=True,
                    lightweight_stage01_confirmed=True,
                )

        self.assertEqual("02-production-build", summary["stage"])
        self.assertEqual("production_ready", summary["status"])
        self.assertEqual("production_ready", summary["image_to_editable_svg_build"]["status"])
        build.assert_called_once()
        ai_policy.assert_called_once()
        clean_bases.assert_called_once()
        ai_svg.assert_called_once()
        self.assertEqual("complete", summary["clean_base_generation"]["status"])
        self.assertIsNone(summary["rebuild"])
        self.assertEqual({}, summary["tool_consumption"])
        self.assertEqual(expected["delivery_readiness"], summary["production_readiness"])

    def test_production_build_blocks_when_clean_base_auto_fails(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            project = root / "client-report"
            init_project(project)
            script = root / "script-final.md"
            script.write_text("## 第1页：测试\n正文\n", encoding="utf-8")
            self._approve_inputs_and_prompts(project, script)

            clean_report = {
                "status": "auto_failed",
                "path": "analysis/clean_base_generation.json",
                "pages": [{"page_number": 1, "status": "auto_failed"}],
            }
            with (
                patch("cyberppt.commands.final_script_pages.require_generated"),
                patch(
                    "cyberppt.commands.final_script_pages.prepare_ai_graphic_text_policy",
                    return_value={"status": "complete", "path": "ai-native-text-policy.json"},
                ),
                patch("cyberppt.commands.final_script_pages.prepare_clean_bases", return_value=clean_report),
                patch("cyberppt.commands.final_script_pages._run_image_to_editable_svg_build") as build,
                self.assertRaisesRegex(RuntimeError, "analysis/clean_base_generation.json"),
            ):
                run_final_script_pages(
                    project=project,
                    script=script,
                    pages_raw="1",
                    style_id=4,
                    production_build=True,
                    lightweight_stage01_confirmed=True,
                )

        build.assert_not_called()

    def test_run_rebuild_requires_editable_overlay_mode(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            project = root / "client-report"
            init_project(project)
            script = root / "script-final.md"
            script.write_text(
                """# 终稿脚本

## 第7页：态势感知能力
本页结论标题为“态势感知能力要从工具堆叠转向风险闭环”
组件A（左侧主图）——三层能力链：
数据接入、模型研判、处置反馈
""",
                encoding="utf-8",
            )
            self._approve_inputs_and_prompts(project, script)

            with self.assertRaisesRegex(ValueError, "--run-rebuild was removed"):
                run_final_script_pages(
                    project=project,
                    script=script,
                    pages_raw="7",
                    style_id=5,
                    run_rebuild=True,
                    lightweight_stage01_confirmed=True,
                )

    def test_semantic_plan_dir_requires_editable_overlay_mode(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            project = root / "client-report"
            init_project(project)
            semantic_plan_dir = root / "semantic-plans"
            semantic_plan_dir.mkdir()
            script = root / "script-final.md"
            script.write_text("## 第7页：态势感知能力\n正文\n", encoding="utf-8")
            self._approve_inputs_and_prompts(project, script)

            with self.assertRaisesRegex(ValueError, "--semantic-plan-dir was removed"):
                run_final_script_pages(
                    project=project,
                    script=script,
                    pages_raw="7",
                    style_id=5,
                    semantic_plan_dir=semantic_plan_dir,
                    lightweight_stage01_confirmed=True,
                )

    def test_removed_triple_image_mode_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            project = root / "client-report"
            init_project(project)
            script = root / "script-final.md"
            script.write_text("## 第7页：测试\n正文\n", encoding="utf-8")
            self._approve_inputs_and_prompts(project, script)

            with self.assertRaisesRegex(ValueError, "unsupported production mode"):
                run_final_script_pages(
                    project=project, script=script, pages_raw="7", style_id=4,
                    production_mode="editable-overlay-text-reference",
                    lightweight_stage01_confirmed=True,
                )

    def test_main_chain_rejects_removed_triple_image_mode(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            project = root / "client-report"
            init_project(project)
            script = root / "script-final.md"
            script.write_text("## 第7页：测试\n正文\n", encoding="utf-8")
            self._approve_inputs_and_prompts(project, script)

            with self.assertRaisesRegex(ValueError, "unsupported production mode"):
                run_final_script_pages(
                    project=project,
                    script=script,
                    pages_raw="7",
                    style_id=4,
                    production_mode="editable-overlay-text-reference",
                    generate_images=True,
                    dry_run_images=True,
                    lightweight_stage01_confirmed=True,
                )


    def test_image_dry_run_does_not_reserve_artifact_ledger_ids(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            project = root / "client-report"
            init_project(project)
            script = root / "script-final.md"
            script.write_text("## 第7页：测试\n正文\n", encoding="utf-8")
            self._approve_inputs_and_prompts(project, script)

            with (
                patch("cyberppt.commands.final_script_pages.run_codex_image"),
                patch("cyberppt.commands.final_script_pages._append_ledger") as append_ledger,
            ):
                run_final_script_pages(
                    project=project,
                    script=script,
                    pages_raw="7",
                    style_id=4,
                    generate_images=True,
                    dry_run_images=True,
                    lightweight_stage01_confirmed=True,
                )

            append_ledger.assert_not_called()

    def test_production_build_requires_audited_full_image_before_reconstruction(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            project = root / "client-report"
            init_project(project)
            script = root / "script-final.md"
            script.write_text(
                """# 终稿脚本

## 第7页：态势感知能力
本页结论标题为“态势感知能力要从工具堆叠转向风险闭环”
组件A（左侧主图）——三层能力链：
数据接入、模型研判、处置反馈
""",
                encoding="utf-8",
            )
            self._approve_inputs_and_prompts(project, script, style_id=5)

            with self.assertRaisesRegex(ValueError, "full image has no passed image-text audit"):
                run_final_script_pages(
                    project=project,
                    script=script,
                    pages_raw="7",
                    style_id=5,
                    production_build=True,
                    lightweight_stage01_confirmed=True,
                )


if __name__ == "__main__":
    unittest.main()
